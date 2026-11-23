"""WebRTC call driver: connects a voice call to the local microphone and speaker.

The call itself is placed through the WebRTC bridge (see ``poly.call.bridge``).
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
from collections.abc import Callable

from poly.call.bridge import BridgeError, run_bridge_call
from poly.call.media import SAMPLE_RATE, MicrophoneTrack, SpeakerPlayer
from poly.call.session import CallSession


class CallError(Exception):
    """Raised when a call cannot be placed or its connection fails."""


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


async def run_call(
    session: CallSession,
    caller: str,
    *,
    aec: bool = False,
    on_started: Callable[[str], None] | None = None,
) -> str:
    """Place a voice call and run it until it ends or an error occurs.

    Args:
        session: The bootstrapped call session (from ``create_call_session``).
        caller: An identifier for the caller (e.g. the user's email).
        aec: When True, run the mic through acoustic echo cancellation so the agent
            does not hear its own audio played through the speaker.
        on_started: Called with the conversation ID once the call is connected.

    Returns:
        The conversation ID of the call in Agent Studio.

    Raises:
        CallError: If the call cannot be placed or its connection fails.
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

    microphone = MicrophoneTrack(echo_canceller=echo_canceller, reference=reference)
    speaker = SpeakerPlayer(reference=reference)

    # Graceful termination
    with _hangup_on_signal(asyncio.get_running_loop()) as stop:
        try:
            return await run_bridge_call(
                session,
                caller,
                source=microphone,
                on_agent_track=speaker.start,
                stop=stop,
                on_started=on_started,
            )
        except BridgeError as exc:
            raise CallError(str(exc)) from exc
        finally:
            microphone.stop()
            speaker.stop()
