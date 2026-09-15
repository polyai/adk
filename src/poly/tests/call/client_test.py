"""Tests for the WebRTC call driver's pure helpers.

Skipped unless the optional ``voice`` extra (aiortc) is installed.

Copyright PolyAI Limited
"""

import asyncio
import json
import unittest
from unittest.mock import MagicMock

import pytest

pytest.importorskip("aiortc")

from poly.call.client import (  # noqa: E402
    CallError,
    _ice_candidate_from_message,
    _run_until_done,
)
from poly.call.signaling import IceCandidateMessage  # noqa: E402


class _BlockingWs:
    """An async-iterable websocket stub that never yields a message."""

    def __aiter__(self):
        return self

    async def __anext__(self):
        await asyncio.Event().wait()  # never set → blocks forever


class _ScriptedWs:
    """An async-iterable websocket stub that yields the given raw messages."""

    def __init__(self, messages):
        self._messages = list(messages)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


class IceCandidateFromMessageTest(unittest.TestCase):
    """Tests for _ice_candidate_from_message."""

    def test_parses_a_real_candidate_line(self):
        message = IceCandidateMessage(
            session_id="s",
            candidate={
                "candidate": "candidate:1 1 udp 2130706431 192.168.1.5 54321 typ host",
                "sdpMid": "0",
                "sdpMLineIndex": 0,
            },
        )

        candidate = _ice_candidate_from_message(message)

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.ip, "192.168.1.5")
        self.assertEqual(candidate.port, 54321)
        self.assertEqual(candidate.type, "host")
        self.assertEqual(candidate.sdpMid, "0")
        self.assertEqual(candidate.sdpMLineIndex, 0)

    def test_strips_candidate_prefix_or_not(self):
        without_prefix = IceCandidateMessage(
            session_id="s",
            candidate={"candidate": "1 1 udp 2130706431 192.168.1.5 54321 typ host"},
        )
        self.assertEqual(_ice_candidate_from_message(without_prefix).ip, "192.168.1.5")

    def test_empty_candidate_returns_none(self):
        message = IceCandidateMessage(session_id="s", candidate={"candidate": ""})
        self.assertIsNone(_ice_candidate_from_message(message))


class RunUntilDoneTest(unittest.TestCase):
    """Tests for _run_until_done (signaling loop vs connection-failure race)."""

    def test_connection_failure_raises_call_error(self):
        async def scenario():
            failed = asyncio.Event()
            failed.set()  # connection already failed
            await _run_until_done(MagicMock(), _BlockingWs(), failed)

        with self.assertRaises(CallError):
            asyncio.run(scenario())

    def test_close_message_returns_normally(self):
        async def scenario():
            ws = _ScriptedWs([json.dumps({"type": "close", "sessionId": "s"})])
            await _run_until_done(MagicMock(), ws, asyncio.Event())

        asyncio.run(scenario())  # must not raise


if __name__ == "__main__":
    unittest.main()
