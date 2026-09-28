"""WebRTC call driver: peer connection + signaling transport.

Orchestrates a voice call end to end: builds the local SDP offer, opens the
signaling WebSocket to the gateway, completes the offer/answer + ICE exchange,
and bridges audio to the local microphone/speaker.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import signal

import websockets
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription
from aiortc.mediastreams import MediaStreamTrack
from aiortc.sdp import candidate_from_sdp

from poly.call.media import SAMPLE_RATE, MicrophoneTrack, SpeakerPlayer
from poly.call.session import CallSession
from poly.call.signaling import (
    AnswerMessage,
    CloseMessage,
    ErrorMessage,
    IceCandidateMessage,
    build_offer_message,
    parse_message,
    signaling_url,
)

logger = logging.getLogger(__name__)


class CallError(Exception):
    """Raised when the gateway reports a signaling error."""


def _ice_candidate_from_message(msg: IceCandidateMessage) -> RTCIceCandidate | None:
    """Build an aiortc ICE candidate from a trickled candidate message.

    Returns None for an empty/end-of-candidates signal.
    """
    raw = msg.candidate.get("candidate", "")
    if not raw:
        return None
    # candidate_from_sdp wants the value without the leading "candidate:".
    candidate = candidate_from_sdp(raw.split(":", 1)[1] if raw.startswith("candidate:") else raw)
    candidate.sdpMid = msg.candidate.get("sdpMid")
    candidate.sdpMLineIndex = msg.candidate.get("sdpMLineIndex")
    return candidate


@contextlib.contextmanager
def _hangup_on_signal(loop: asyncio.AbstractEventLoop):
    """Bridge Ctrl+C to a stop event for the duration of a call."""
    stop = asyncio.Event()
    installed = []
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
            installed.append(sig)
        except (NotImplementedError, RuntimeError):
            # Unsupported (e.g. on Windows);
            # Let CLI's KeyboardInterrupt handle.
            pass
    try:
        yield stop
    finally:
        for sig in installed:
            with contextlib.suppress(NotImplementedError, RuntimeError):
                loop.remove_signal_handler(sig)


async def run_call(session: CallSession, caller: str, *, aec: bool = False, call_sid: str) -> None:
    """Place a voice call and run it until the gateway closes or an error occurs.

    Args:
        session: The bootstrapped call session (from ``create_call_session``).
        caller: An identifier for the caller (e.g. the user's email).
        aec: When True, run the mic through acoustic echo cancellation so the agent
            does not hear its own audio played through the speaker.
        call_sid: The call SID.

    Raises:
        CallError: If the gateway returns a signaling error.
        RuntimeError: If ``aec`` is set but the WebRTC APM (pywebrtc-audio) can't load.
    """
    echo_canceller = None
    reference = None
    if aec:
        # Constructed first so a missing dependency fails before any device is opened.
        from poly.call.aec import EchoCanceller, FarEndReference

        echo_canceller = EchoCanceller(SAMPLE_RATE)
        # Cap the reference at ~1 s to bound worst-case latency; steady-state depth
        # self-regulates and the APM's delay estimator aligns near/far.
        reference = FarEndReference(max_samples=SAMPLE_RATE)

    pc = RTCPeerConnection()
    microphone = MicrophoneTrack(echo_canceller=echo_canceller, reference=reference)
    speaker = SpeakerPlayer(reference=reference)
    pc.addTrack(microphone)
    connection_failed = asyncio.Event()

    @pc.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        if track.kind == "audio":
            logger.info("Receiving agent audio")
            speaker.start(track)

    @pc.on("connectionstatechange")
    async def on_state_change() -> None:
        logger.info("Connection state: %s", pc.connectionState)
        # "failed" is terminal; wake the call so it ends instead of hanging on
        # the signaling socket. ("closed" follows our own pc.close() teardown.)
        if pc.connectionState == "failed":
            connection_failed.set()

    await pc.setLocalDescription(await pc.createOffer())

    # Graceful termination
    with _hangup_on_signal(asyncio.get_running_loop()) as stop:
        try:
            async with websockets.connect(signaling_url(session.gateway_ws_url)) as ws:
                offer = build_offer_message(
                    session, pc.localDescription.sdp, caller, call_sid=call_sid
                )
                await ws.send(json.dumps(offer))
                await _run_until_done(pc, ws, connection_failed, stop)
        finally:
            microphone.stop()
            speaker.stop()
            await pc.close()


async def _run_until_done(
    pc: RTCPeerConnection,
    ws,
    connection_failed: asyncio.Event,
    stop: asyncio.Event,
) -> None:
    """Run the signaling loop until it ends or the connection fails.

    Races the signaling loop against the connection-failed event so a terminal
    ICE/DTLS failure ends the call rather than hanging on the socket.

    Raises:
        CallError: If the gateway errors or the connection fails.
    """
    signaling = asyncio.ensure_future(_run_signaling_loop(pc, ws))
    failure = asyncio.ensure_future(connection_failed.wait())
    stopped = asyncio.ensure_future(stop.wait())
    done, pending = await asyncio.wait(
        {signaling, failure, stopped}, return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    if signaling in done:
        signaling.result()  # normal return, or re-raise a CallError from the loop
    elif stopped in done:
        return  # user hung up
    else:
        raise CallError("Connection failed")


async def _run_signaling_loop(pc: RTCPeerConnection, ws) -> None:
    """Dispatch inbound signaling messages until the call ends.

    Raises:
        CallError: If the gateway returns an error message.
    """
    async for raw in ws:
        message = parse_message(json.loads(raw))

        if isinstance(message, AnswerMessage):
            await pc.setRemoteDescription(RTCSessionDescription(sdp=message.sdp, type="answer"))
        elif isinstance(message, IceCandidateMessage):
            candidate = _ice_candidate_from_message(message)
            if candidate is not None:
                await pc.addIceCandidate(candidate)
        elif isinstance(message, ErrorMessage):
            raise CallError(f"{message.code}: {message.message}")
        elif isinstance(message, CloseMessage):
            logger.info("Gateway closed the call")
            return
