"""WebRTC bridge transport: the call path Agent Studio's own call panel uses.

The bridge terminates media at an SFU and proxies SDP over HTTPS; a WebSocket carries
only control events. The exchange is:

1. ``POST /api/v1/call`` with the studio token provisions the call and returns its id
   and credentials. Every credential URL is a path on the bridge, and the short-lived
   call token authenticates each of them.
2. A complete (non-trickle) SDP offer is posted to the connect URL; the answer brings
   up the caller's audio.
3. Once connected, the pull URL returns a renegotiation offer that adds the agent's
   audio; its answer is posted to the renegotiate URL.
4. The events socket asks for step 3 again (``repull``) whenever the agent's track
   moves, and closing it ends the call.
5. ``DELETE /api/v1/call/{id}`` tears the call down.

Copyright PolyAI Limited
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urlsplit

import requests
import websockets
from aiortc import (
    RTCConfiguration,
    RTCIceServer,
    RTCPeerConnection,
    RTCSessionDescription,
)
from aiortc.mediastreams import MediaStreamTrack

from poly.call.session import CallSession

logger = logging.getLogger(__name__)

PROVISION_PATH = "/api/v1/call"
# The mode that runs the project's agent (the bridge's other mode only echoes audio).
BRIDGE_CALL_MODE = "voice-agent"
CALL_TOKEN_HEADER = "X-Call-Token"

_HTTP_TIMEOUT_SECONDS = 15
_CONNECT_TIMEOUT_SECONDS = 15
_FALLBACK_ICE_SERVERS = [{"urls": "stun:stun.cloudflare.com:3478"}]


class BridgeError(Exception):
    """Raised when the bridge refuses or fails a step of the call."""


@dataclass(frozen=True)
class BridgeCredentials:
    """What the bridge returns for one provisioned call.

    Attributes:
        call_id: The call's id, which is also its conversation ID in Agent Studio.
        token: The short-lived token that authenticates this call's requests.
        connect_url: Where the first SDP offer is posted.
        pull_url: Where the agent's audio is requested.
        renegotiate_url: Where the answer to a pull is posted.
        events_url: The control events socket.
        ice_servers: ICE servers to use for this call.
    """

    call_id: str
    token: str
    connect_url: str
    pull_url: str
    renegotiate_url: str
    events_url: str
    ice_servers: list[dict[str, Any]] = field(default_factory=list)


def resolve_bridge_url(path: str, bridge_url: str) -> str:
    """Resolve a path the bridge returned against the bridge's own origin.

    Call credentials are only ever sent back to the bridge, so anything that is not a
    plain path on it is refused.

    Args:
        path: A path from the bridge's credentials, such as ``/api/v1/call/x/sdp``.
        bridge_url: The bridge base URL.

    Returns:
        The absolute URL on the bridge.

    Raises:
        BridgeError: If the path is not a plain absolute path.
    """
    if not path.startswith("/") or path.startswith("//") or any(c in path for c in "?#@\\"):
        raise BridgeError("The call service returned an unusable credential URL")
    return f"{bridge_url.rstrip('/')}{path}"


def events_socket_url(path: str, bridge_url: str) -> str:
    """Build the events WebSocket URL from the bridge base URL."""
    url = resolve_bridge_url(path, bridge_url)
    scheme = "wss" if urlsplit(url).scheme == "https" else "ws"
    return f"{scheme}://{url.split('://', 1)[1]}"


def build_provision_body(session: CallSession, caller: str) -> dict[str, Any]:
    """Build the provisioning request body.

    The account, project and build come from the studio token, so only the call mode,
    the variant and a caller label are sent.
    """
    body: dict[str, Any] = {"mode": BRIDGE_CALL_MODE}
    if session.variant_id:
        body["variantId"] = session.variant_id
    if caller:
        body["caller"] = caller
    return body


def parse_provision_response(payload: dict[str, Any]) -> BridgeCredentials:
    """Read the provisioning response into credentials.

    Raises:
        BridgeError: If a field the call cannot run without is missing.
    """
    creds = payload.get("creds") or {}
    extra = creds.get("extra") or {}
    fields = {
        "callId": payload.get("callId"),
        "connectUrl": creds.get("connectUrl"),
        "pullUrl": extra.get("pullUrl"),
        "renegotiateUrl": extra.get("renegotiateUrl"),
        "eventsUrl": extra.get("eventsUrl"),
    }
    missing = [name for name, value in fields.items() if not value]
    if missing:
        raise BridgeError(f"Incomplete call credentials; missing field(s): {', '.join(missing)}")
    return BridgeCredentials(
        call_id=fields["callId"],
        token=creds.get("token") or "",
        connect_url=fields["connectUrl"],
        pull_url=fields["pullUrl"],
        renegotiate_url=fields["renegotiateUrl"],
        events_url=fields["eventsUrl"],
        ice_servers=list(creds.get("iceServers") or []),
    )


def ice_configuration(ice_servers: list[dict[str, Any]]) -> RTCConfiguration:
    """Build the peer connection configuration from the bridge's ICE servers."""
    servers = [
        RTCIceServer(
            urls=server["urls"],
            username=server.get("username"),
            credential=server.get("credential"),
        )
        for server in (ice_servers or _FALLBACK_ICE_SERVERS)
        if server.get("urls")
    ]
    return RTCConfiguration(iceServers=servers)


def _is_unsupported_agent(response: requests.Response) -> bool:
    """Whether a refused provision says the bridge does not serve this agent."""
    try:
        return bool(response.json().get("fallback"))
    except ValueError:
        return False


def _provision(session: CallSession, caller: str) -> BridgeCredentials:
    response = requests.post(
        f"{session.bridge_url.rstrip('/')}{PROVISION_PATH}",
        headers={"Authorization": f"Bearer {session.auth_token}"},
        json=build_provision_body(session, caller),
        timeout=_HTTP_TIMEOUT_SECONDS,
        allow_redirects=False,
    )
    if not response.ok:
        if _is_unsupported_agent(response):
            raise BridgeError(
                "This agent's voice setup can't be called from the ADK yet. "
                "Call it from Agent Studio instead."
            )
        raise BridgeError(f"Could not start the call ({response.status_code})")
    return parse_provision_response(response.json())


def _signaling_post(url: str, token: str, body: dict[str, Any], step: str) -> dict[str, Any]:
    """Post one signalling step, authenticated with the call token."""
    response = requests.post(
        url,
        headers={CALL_TOKEN_HEADER: token} if token else {},
        json={**({"token": token} if token else {}), **body},
        timeout=_HTTP_TIMEOUT_SECONDS,
        allow_redirects=False,
    )
    if not response.ok:
        raise BridgeError(f"The call service rejected the {step} step ({response.status_code})")
    return response.json() if response.content else {}


def _delete_call(session: CallSession, creds: BridgeCredentials) -> None:
    """Tear the call down. The bridge also reaps it when the events socket drops."""
    with contextlib.suppress(requests.RequestException):
        requests.delete(
            f"{session.bridge_url.rstrip('/')}{PROVISION_PATH}/{quote(creds.call_id, safe='')}",
            headers={CALL_TOKEN_HEADER: creds.token} if creds.token else {},
            timeout=_HTTP_TIMEOUT_SECONDS,
            allow_redirects=False,
        )


def _caller_mid(pc: RTCPeerConnection, track: MediaStreamTrack) -> str:
    """The mid of the m-line that carries the caller's audio."""
    for transceiver in pc.getTransceivers():
        if transceiver.sender.track is track and transceiver.mid is not None:
            return transceiver.mid
    return "0"


async def _pull_agent_audio(
    pc: RTCPeerConnection, session: CallSession, creds: BridgeCredentials
) -> None:
    """Ask for the agent's audio and answer the renegotiation offer that adds it."""
    pull = await asyncio.to_thread(
        _signaling_post,
        resolve_bridge_url(creds.pull_url, session.bridge_url),
        creds.token,
        {},
        "audio request",
    )
    sdp = pull.get("sdp")
    if not sdp:
        return  # nothing to pull yet; a later repull event retries
    await pc.setRemoteDescription(RTCSessionDescription(sdp=sdp, type="offer"))
    await pc.setLocalDescription(await pc.createAnswer())
    await asyncio.to_thread(
        _signaling_post,
        resolve_bridge_url(creds.renegotiate_url, session.bridge_url),
        creds.token,
        {"sdp": pc.localDescription.sdp},
        "audio setup",
    )


async def _run_events(
    ws, pc: RTCPeerConnection, session: CallSession, creds: BridgeCredentials
) -> None:
    """Follow control events until the bridge closes the socket, which ends the call."""
    async for raw in ws:
        try:
            event = json.loads(raw).get("event")
        except (ValueError, AttributeError):
            continue
        if event == "repull":
            # Awaited in line so two renegotiations never interleave on one connection.
            await _pull_agent_audio(pc, session, creds)


async def run_bridge_call(
    session: CallSession,
    caller: str,
    *,
    source: MediaStreamTrack,
    on_agent_track: Callable[[MediaStreamTrack], None],
    stop: asyncio.Event,
    on_started: Callable[[str], None] | None = None,
) -> str:
    """Place a call through the bridge and run it until it ends.

    Args:
        session: The bootstrapped call session.
        caller: A label for the caller, shown on the conversation.
        source: The caller's audio.
        on_agent_track: Called with each audio track the agent's side adds.
        stop: Set to hang up.
        on_started: Called with the call id once audio is flowing both ways.

    Returns:
        The call id, which is the conversation ID in Agent Studio.

    Raises:
        BridgeError: If any step of the call fails.
    """
    try:
        creds = await asyncio.to_thread(_provision, session, caller)
    except requests.RequestException as exc:
        raise BridgeError(f"Could not reach the call service: {exc}") from exc

    pc = RTCPeerConnection(ice_configuration(creds.ice_servers))
    pc.addTrack(source)
    connected = asyncio.Event()
    failed = asyncio.Event()

    @pc.on("track")
    def on_track(track: MediaStreamTrack) -> None:
        if track.kind == "audio":
            on_agent_track(track)

    @pc.on("connectionstatechange")
    async def on_state_change() -> None:
        logger.info("Connection state: %s", pc.connectionState)
        if pc.connectionState == "connected":
            connected.set()
        elif pc.connectionState == "failed":
            failed.set()

    try:
        # aiortc gathers every candidate before the local description settles, so the
        # offer is already complete (the bridge does not take trickled candidates).
        await pc.setLocalDescription(await pc.createOffer())
        answer = await asyncio.to_thread(
            _signaling_post,
            resolve_bridge_url(creds.connect_url, session.bridge_url),
            creds.token,
            {"sdp": pc.localDescription.sdp, "mid": _caller_mid(pc, source)},
            "connect",
        )
        if not answer.get("sdp"):
            raise BridgeError("The call service returned no answer")
        await pc.setRemoteDescription(RTCSessionDescription(sdp=answer["sdp"], type="answer"))
        try:
            await asyncio.wait_for(connected.wait(), timeout=_CONNECT_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            raise BridgeError("Timed out connecting the call's audio") from exc

        await _pull_agent_audio(pc, session, creds)

        events_url = events_socket_url(creds.events_url, session.bridge_url)
        async with websockets.connect(events_url) as ws:
            # The socket stays unauthenticated until this first frame arrives.
            await ws.send(json.dumps({"type": "auth", "token": creds.token}))
            if on_started is not None:
                on_started(creds.call_id)
            events = asyncio.ensure_future(_run_events(ws, pc, session, creds))
            waiters = {
                events,
                asyncio.ensure_future(failed.wait()),
                asyncio.ensure_future(stop.wait()),
            }
            done, pending = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            if events in done:
                with contextlib.suppress(websockets.ConnectionClosed):
                    events.result()  # re-raise a failed repull
            elif not stop.is_set():
                raise BridgeError("Connection failed")
    except requests.RequestException as exc:
        raise BridgeError(f"Lost contact with the call service: {exc}") from exc
    finally:
        await asyncio.to_thread(_delete_call, session, creds)
        await pc.close()
    return creds.call_id
