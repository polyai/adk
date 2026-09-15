"""WebRTC signaling protocol for voice calls.

Pure message construction and parsing for the gateway's JSON-over-WebSocket
signaling protocol.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any

from poly.call.session import CallSession

# Path appended to the gateway base URL to open the signaling WebSocket.
SIGNALING_PATH = "/api/v1/webrtc/signal"


class SignalingMessageType(str, Enum):
    """Signaling message ``type`` discriminator."""

    OFFER = "offer"
    ANSWER = "answer"
    ICE_CANDIDATE = "ice-candidate"
    ERROR = "error"
    CLOSE = "close"


def signaling_url(gateway_ws_url: str) -> str:
    """Build the full signaling WebSocket URL from the gateway base URL."""
    return f"{gateway_ws_url.rstrip('/')}{SIGNALING_PATH}"


def build_offer_message(
    session: CallSession,
    sdp: str,
    caller: str,
    call_sid: str | None = None,
) -> dict[str, Any]:
    """Build the signaling OFFER for a draft call.

    Args:
        session: The bootstrapped call session.
        sdp: The local SDP offer produced by the peer connection.
        caller: An identifier for the caller (e.g. the user's email).
        call_sid: Optional call SID; a unique ``ADK-<uuid>`` is generated if omitted.

    Returns:
        The OFFER message as a JSON-serialisable dict.
    """
    message: dict[str, Any] = {
        "type": SignalingMessageType.OFFER.value,
        "sessionId": "",
        "data": {"type": "offer", "sdp": sdp},
        "callSid": call_sid or f"ADK-{uuid.uuid4()}",
        "caller": caller,
        "mode": session.mode,
        "authToken": session.auth_token,
        "accountId": session.account_id,
        "projectId": session.project_id,
        "agentVersionOverride": {
            "artifactVersion": session.artifact_version,
            "lambdaDeploymentVersion": session.lambda_deployment_version,
        },
    }
    # Omit variantId when empty.
    if session.variant_id:
        message["variantId"] = session.variant_id
    return message


@dataclass(frozen=True)
class AnswerMessage:
    """An SDP answer from the gateway."""

    session_id: str
    sdp: str


@dataclass(frozen=True)
class IceCandidateMessage:
    """A trickled ICE candidate from the gateway."""

    session_id: str
    candidate: dict[str, Any]


@dataclass(frozen=True)
class ErrorMessage:
    """A signaling error from the gateway."""

    session_id: str
    code: str
    message: str


@dataclass(frozen=True)
class CloseMessage:
    """A call-close notification from the gateway."""

    session_id: str


# Any inbound message the client handles.
InboundMessage = AnswerMessage | IceCandidateMessage | ErrorMessage | CloseMessage


def parse_message(raw: dict[str, Any]) -> InboundMessage:
    """Parse an inbound signaling message into a typed dataclass.

    Args:
        raw: The decoded JSON message.

    Returns:
        The typed message.

    Raises:
        ValueError: If the message type is missing or unrecognised.
    """
    msg_type = raw.get("type")
    session_id = raw.get("sessionId", "")

    if msg_type == SignalingMessageType.ANSWER.value:
        return AnswerMessage(session_id=session_id, sdp=raw["data"]["sdp"])
    if msg_type == SignalingMessageType.ICE_CANDIDATE.value:
        return IceCandidateMessage(session_id=session_id, candidate=raw["data"])
    if msg_type == SignalingMessageType.ERROR.value:
        # The gateway nests code/message under `data` (ErrorData); fall back to
        # top-level for robustness against the shape in webrtc-types.ts.
        data = raw.get("data") or {}
        return ErrorMessage(
            session_id=session_id,
            code=data.get("code", raw.get("code", "")),
            message=data.get("message", raw.get("message", "")),
        )
    if msg_type == SignalingMessageType.CLOSE.value:
        return CloseMessage(session_id=session_id)

    raise ValueError(f"Unrecognised signaling message type: {msg_type!r}")
