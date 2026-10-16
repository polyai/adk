"""Client for Wren's streaming turn endpoint.

Copyright PolyAI Limited
"""

from typing import Any, Generator

from poly.handlers.platform_api import PlatformAPIHandler

WREN_TURN_PATH = "/v1/studio-assistant/turn"

TERMINAL_EVENT_TYPES = frozenset({"complete", "error", "aborted", "user_input_required"})


def _stream_client_message(
    region: str, message: dict[str, Any]
) -> Generator[dict[str, Any], None, None]:
    """POST a client message to Wren and yield events until the run stops.

    Args:
        region: Project region (used to resolve the API host).
        message: A full client message ("prompt" or "input_response").

    Yields:
        Parsed event dicts, up to and including the one that ends the run.

    Raises:
        requests.HTTPError: On a non-2xx response before the stream opens.
    """
    for event in PlatformAPIHandler.stream_events(region, WREN_TURN_PATH, message):
        yield event

        event_type = event.get("type")
        if event_type not in TERMINAL_EVENT_TYPES:
            continue
        # A suspended or nested complete means the run handed off to a subagent
        # (or a nested frame finished); it carries on server-side on this stream.
        if event_type == "complete" and (event.get("suspended") or (event.get("depth") or 0) > 0):
            continue
        # Auto mode answers auto-flagged gates itself, in the same tick.
        if event_type == "user_input_required" and event.get("auto"):
            continue
        return


def stream_wren_turn(
    region: str,
    prompt: str,
    context: dict[str, str],
    session_id: str | None = None,
    agent_name: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Send a prompt to Wren and yield the run's events.

    Args:
        region: Project region (used to resolve the API host).
        prompt: The user prompt to send.
        context: Agent context (accountId, projectId, branchId, mode).
        session_id: Session to continue, or None to start a new one.
        agent_name: Top-level agent to run. The server defaults to "orchestrator".

    Yields:
        Parsed event dicts.

    Raises:
        requests.HTTPError: On a non-2xx response before the stream opens.
    """
    message: dict[str, Any] = {"type": "prompt", "content": prompt, "context": context}
    if session_id:
        message["sessionId"] = session_id
    if agent_name:
        message["agentName"] = agent_name
    yield from _stream_client_message(region, message)


def stream_wren_input_response(
    region: str,
    request_id: str,
    answer: dict[str, Any],
    context: dict[str, str],
    session_id: str,
) -> Generator[dict[str, Any], None, None]:
    """Answer a question Wren is waiting on, and yield the resumed run's events.

    Args:
        region: Project region (used to resolve the API host).
        request_id: The requestId from the user_input_required event.
        answer: Typed answer: {"inputKind": ..., "value": ...}.
        context: Agent context (accountId, projectId, branchId).
        session_id: Session of the paused run.

    Yields:
        Parsed event dicts.

    Raises:
        requests.HTTPError: On a non-2xx response before the stream opens.
    """
    message: dict[str, Any] = {
        "type": "input_response",
        "sessionId": session_id,
        "context": context,
        "requestId": request_id,
        "answer": answer,
    }
    yield from _stream_client_message(region, message)
