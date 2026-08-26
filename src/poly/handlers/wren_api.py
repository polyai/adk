"""SSE client for the Wren (glot) endpoint.

Copyright PolyAI Limited
"""

import json
import logging
from typing import Any, Generator

import requests

from poly.handlers.platform_api import PlatformAPIHandler

logger = logging.getLogger(__name__)

WREN_TURN_PATH = "/v1/studio-assistant/turn"

TERMINAL_EVENT_TYPES = frozenset({"complete", "error", "aborted", "user_input_required"})


def _get_wren_url(region: str) -> str:
    """Resolve the full SSE endpoint URL for the given region."""
    base_url = PlatformAPIHandler.get_base_url(region)
    return f"{base_url}{WREN_TURN_PATH}"


def _extract_error_detail(response: requests.Response) -> str | None:
    """Pull the server's validation detail out of an error response body."""
    try:
        body = response.json()
    except Exception:
        # Best-effort only: a body that isn't readable JSON (truncated,
        # wrong content-type, decode error) must not mask the HTTP error.
        return None
    if isinstance(body, dict):
        detail = body.get("error")
        if isinstance(detail, str) and detail:
            return detail
    return None


def _stream_client_message(
    region: str,
    api_key: str,
    message: dict[str, Any],
) -> Generator[dict[str, Any], None, None]:
    """POST a client message to the wren SSE endpoint and yield parsed events.

    Args:
        region: Project region (used to resolve the API host).
        api_key: Personal Access Token for authentication.
        message: A full client message dict (type "prompt" or "input_response").

    Yields:
        Parsed JSON event dicts from the SSE stream.

    Raises:
        requests.HTTPError: On non-2xx responses before the stream opens. The
            error message carries the server's validation detail when present
            (e.g. "Invalid request: context.projectId: ...").
    """
    url = _get_wren_url(region)

    response = requests.post(
        url,
        json=message,
        headers={
            "X-API-KEY": api_key,
            "Accept": "text/event-stream",
        },
        stream=True,
        timeout=300,
    )
    if not response.ok:
        detail = _extract_error_detail(response)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            if detail:
                raise requests.HTTPError(detail, response=response) from e
            raise
    # requests defaults text/event-stream to ISO-8859-1; the stream is UTF-8.
    response.encoding = "utf-8"

    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line or line.startswith(":"):
                continue
            if not line.startswith("data: "):
                continue

            raw = line[len("data: ") :]
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Skipping non-JSON SSE frame: %s", raw[:100])
                continue

            yield event

            event_type = event.get("type")
            if event_type not in TERMINAL_EVENT_TYPES:
                continue
            # Mid-chain completes: the run suspended into a subagent (or a
            # nested frame finished) and continues server-side on this stream.
            if event_type == "complete" and (
                event.get("suspended") or (event.get("depth") or 0) > 0
            ):
                continue
            # Auto-flagged gates are informational — auto mode answers them
            # itself in the same tick and the run continues.
            if event_type == "user_input_required" and event.get("auto"):
                continue
            return
    finally:
        response.close()


def stream_wren_turn(
    region: str,
    api_key: str,
    prompt: str,
    context: dict[str, str],
    session_id: str | None = None,
    agent_name: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Send a prompt message to the wren SSE endpoint and yield parsed events.

    Args:
        region: Project region (used to resolve the API host).
        api_key: Personal Access Token for authentication.
        prompt: The user prompt to send.
        context: Agent context dict (accountId, projectId, branchId, mode).
        session_id: Optional session ID to continue a conversation.
        agent_name: Optional top-level agent override (server default:
            "orchestrator").

    Yields:
        Parsed JSON event dicts from the SSE stream.

    Raises:
        requests.HTTPError: On non-2xx responses before the stream opens.
    """
    message: dict[str, Any] = {"type": "prompt", "content": prompt, "context": context}
    if session_id:
        message["sessionId"] = session_id
    if agent_name:
        message["agentName"] = agent_name
    yield from _stream_client_message(region, api_key, message)


def stream_wren_input_response(
    region: str,
    api_key: str,
    request_id: str,
    answer: dict[str, Any],
    context: dict[str, str],
    session_id: str,
) -> Generator[dict[str, Any], None, None]:
    """Answer a pending user-input gate, resuming the run on a fresh SSE stream.

    Args:
        region: Project region (used to resolve the API host).
        api_key: Personal Access Token for authentication.
        request_id: The requestId from the user_input_required event.
        answer: Typed answer dict: {"inputKind": ..., "value": ...}.
        context: Agent context dict (accountId, projectId, branchId).
        session_id: Session ID of the paused run (required by the server).

    Yields:
        Parsed JSON event dicts from the SSE stream.

    Raises:
        requests.HTTPError: On non-2xx responses before the stream opens.
    """
    message: dict[str, Any] = {
        "type": "input_response",
        "sessionId": session_id,
        "context": context,
        "requestId": request_id,
        "answer": answer,
    }
    yield from _stream_client_message(region, api_key, message)
