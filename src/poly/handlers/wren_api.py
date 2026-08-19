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


def stream_wren_turn(
    region: str,
    api_key: str,
    prompt: str,
    context: dict[str, str],
    session_id: str | None = None,
) -> Generator[dict[str, Any], None, None]:
    """POST to the wren SSE endpoint and yield parsed events.

    Args:
        region: Project region (used to resolve the API host).
        api_key: Personal Access Token for authentication.
        prompt: The user prompt to send.
        context: Agent context dict (accountId, projectId, branchId).
        session_id: Optional session ID to continue a conversation.

    Yields:
        Parsed JSON event dicts from the SSE stream.

    Raises:
        requests.HTTPError: On non-2xx responses before the stream opens.
    """
    url = _get_wren_url(region)

    body: dict[str, Any] = {"prompt": prompt, "context": context}
    if session_id:
        body["sessionId"] = session_id

    response = requests.post(
        url,
        json=body,
        headers={
            "X-API-KEY": api_key,
            "Accept": "text/event-stream",
        },
        stream=True,
        timeout=300,
    )
    response.raise_for_status()
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
