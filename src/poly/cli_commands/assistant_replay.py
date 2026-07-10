"""Replay downloaded Studio Assistant conversations through the CLI renderer.

Converts the persisted conversation-export shape (as downloaded from Studio)
back into the synthetic streaming events the live SSE path produces, so the
assistant UX can be exercised offline against real conversations.

Copyright PolyAI Limited
"""

import json
import time
from typing import Any, Iterator

_CHUNK_SIZE = 64


def load_conversation(path: str) -> dict[str, Any]:
    """Load and validate a conversation export JSON file."""
    with open(path, encoding="utf-8") as f:
        conv = json.load(f)
    if not isinstance(conv, dict) or not isinstance(conv.get("messages"), list):
        raise ValueError(
            "Not a conversation export: expected a JSON object with a 'messages' list."
        )
    return conv


def _chunks(text: str, size: int = _CHUNK_SIZE) -> Iterator[str]:
    for i in range(0, len(text), size):
        yield text[i : i + size]


def synthesize_turn_events(
    turn_end: dict[str, Any], delay_s: float = 0.0
) -> Iterator[dict[str, Any]]:
    """Convert one persisted turn_end event into synthetic streaming events.

    Persisted turns carry the whole assistant message plus its tool results;
    the live stream delivers message_start/delta/end followed by one
    tool_execution_end per tool result. Text is re-chunked so the streaming
    renderer (live markdown) is exercised the same way as a live session.
    """
    inner = turn_end.get("message") or {}
    depth = inner.get("depth", turn_end.get("depth", 0)) or 0
    session_id = turn_end.get("sessionId", "")

    texts = [
        c.get("text", "")
        for c in inner.get("content") or []
        if isinstance(c, dict) and c.get("type") == "text" and c.get("text")
    ]
    yield {
        "type": "message_start",
        "depth": depth,
        "sessionId": session_id,
        "message": {"role": "assistant", "content": []},
    }
    for chunk in _chunks("\n\n".join(texts)):
        if delay_s:
            time.sleep(delay_s)
        yield {
            "type": "message_delta",
            "depth": depth,
            "sessionId": session_id,
            "delta": chunk,
        }
    yield {"type": "message_end", "depth": depth, "sessionId": session_id, "message": inner}

    for tool_result in turn_end.get("toolResults") or []:
        yield {
            "type": "tool_execution_end",
            "depth": depth,
            "sessionId": session_id,
            "toolCallId": tool_result.get("toolCallId", ""),
            "toolName": tool_result.get("toolName", ""),
            "isError": bool(tool_result.get("isError")),
            "result": {
                "content": tool_result.get("content") or [],
                "details": tool_result.get("details") or {},
            },
        }


def replay_segments(
    conv: dict[str, Any],
) -> Iterator[tuple[str | None, list[dict[str, Any]]]]:
    """Split the conversation into (user_prompt, following_messages) segments.

    The first segment's prompt may be None if the export starts with system
    events (e.g. the initial auto_pull) before any user turn.
    """
    prompt: str | None = None
    segment: list[dict[str, Any]] = []
    started = False
    for m in conv.get("messages", []):
        if m.get("type") == "user":
            if started or segment:
                yield prompt, segment
            prompt = (m.get("message") or {}).get("content", "")
            segment = []
            started = True
        else:
            segment.append(m)
    if started or segment:
        yield prompt, segment


def segment_events(
    messages: list[dict[str, Any]], delay_s: float = 0.0
) -> Iterator[dict[str, Any]]:
    """Convert one segment of persisted messages into streaming events."""
    for m in messages:
        event = m.get("message") or {}
        if m.get("type") == "turn_end":
            yield from synthesize_turn_events(event, delay_s)
        elif event.get("type"):
            # Already the streaming shape (complete, branch_change, auto_pull,
            # user_input_required/answered, session_rename, aborted, resume…).
            yield event
