"""Tests for the transcripts CLI commands.

Copyright PolyAI Limited
"""

import json
import os
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.transcripts import TranscriptsCommand
from poly.output.console import console
from poly.project import AgentStudioProject

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_projects", "test_project")
with open(os.path.join(TEST_DIR, "test_project.json"), encoding="utf-8") as _f:
    PROJECT_DATA = json.load(_f)


def _search_args(**overrides) -> Namespace:
    """A Namespace with every `transcripts search` flag at its parser default."""
    base = {
        "query": "cancel my booking",
        "from_dt": None,
        "to_dt": None,
        "context": 1,
        "english": False,
        "limit": 20,
        "offset": 0,
    }
    base.update(overrides)
    return Namespace(**base)


def _http_error(status: int) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {}
    response.text = ""
    return requests.HTTPError(response=response)


class TranscriptsCommandTest(unittest.TestCase):
    """Base: a real fixture project with the mock at the HTTP boundary."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        patch("poly.cli_commands.transcripts.load_project", return_value=self.project).start()
        self.mock_request = patch(
            "poly.handlers.platform_api.PlatformAPIHandler.make_request"
        ).start()
        self.addCleanup(patch.stopall)

    def _render(self, fn, *args, **kwargs) -> str:
        with console.capture() as capture:
            fn(*args, **kwargs)
        return capture.get()


class TranscriptsSearchTest(TranscriptsCommandTest):
    """Tests for TranscriptsCommand.transcripts_search."""

    def test_builds_params_and_always_sends_project(self):
        """Flags become the Data API's query parameters; the project id is always sent."""
        self.mock_request.return_value = {
            "results": [
                {
                    "conversation_id": "conv-1",
                    "project_id": "test_project",
                    "matched_turns": [
                        {
                            "turn_index": 2,
                            "user_input": "I want to cancel my booking please",
                            "agent_response": "Sure, which booking?",
                            "context": {"before": [], "after": []},
                        }
                    ],
                }
            ],
            "total": 1,
            "limit": 50,
            "offset": 100,
        }
        args = _search_args(
            query="  cancel my booking ",
            from_dt="2026-09-01",
            to_dt="2026-09-30",
            context=2,
            limit=50,
            offset=100,
        )

        output = self._render(TranscriptsCommand.transcripts_search, TEST_DIR, args)

        region, endpoint, method = self.mock_request.call_args.args
        self.assertEqual((region, endpoint, method), ("us-1", "/api/v1/transcripts/search", "GET"))
        self.assertEqual(
            self.mock_request.call_args.kwargs["params"],
            {
                "q": "cancel my booking",
                "project_id": "test_project",
                "context_turns": 2,
                "limit": 50,
                "offset": 100,
                "from": "2026-09-01T00:00:00",
                "to": "2026-10-01T00:00:00",
            },
        )
        self.assertIn("conv-1", output)
        self.assertIn("cancel my booking", output)

    @patch("poly.cli_commands.transcripts.json_print")
    def test_short_query_fails_before_request(self, mock_json):
        """The Data API requires 3 to 300 characters; say so before calling it."""
        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search(
                TEST_DIR, _search_args(query="hi"), output_json=True
            )

        self.mock_request.assert_not_called()
        self.assertIn("3 to 300", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.transcripts.json_print")
    def test_403_names_pii_permission(self, mock_json):
        """Transcript routes need PII read outright, so a 403 names that permission."""
        self.mock_request.side_effect = _http_error(403)

        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search(TEST_DIR, _search_args(), output_json=True)

        self.assertIn("PII read", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.transcripts.json_print")
    def test_429_explains_rate_limit(self, mock_json):
        """A 429 explains the per-key limit rather than dumping the response."""
        self.mock_request.side_effect = _http_error(429)

        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search(TEST_DIR, _search_args(), output_json=True)

        self.assertIn("100 requests", mock_json.call_args[0][0]["error"])


class TranscriptsGetTest(TranscriptsCommandTest):
    """Tests for TranscriptsCommand.transcripts_get."""

    def test_fetches_for_the_project_and_prints(self):
        """The transcript is fetched with the project id and printed turn by turn."""
        self.mock_request.return_value = {
            "conversation_id": "conv-1",
            "total_turns": 1,
            "turns": [
                {
                    "turn_index": 0,
                    "user_input": "hola",
                    "english_user_input": "hello",
                    "user_input_datetime": "2026-09-30T10:00:00+00:00",
                    "agent_response": "buenos días",
                }
            ],
        }

        output = self._render(
            TranscriptsCommand.transcripts_get, TEST_DIR, "conv-1", english=True
        )

        self.mock_request.assert_called_once_with(
            "us-1",
            "/api/v1/transcripts/conversation/conv-1",
            "GET",
            params={"project_id": "test_project"},
        )
        self.assertIn("hello", output)
        self.assertIn("buenos días", output)

    @patch("poly.cli_commands.transcripts.json_print")
    def test_json_passes_result_through(self, mock_json):
        """--json emits the Data API payload untouched."""
        self.mock_request.return_value = {"conversation_id": "c1", "turns": [{"turn_index": 0}]}

        TranscriptsCommand.transcripts_get(TEST_DIR, "c1", output_json=True)

        mock_json.assert_called_once_with(self.mock_request.return_value)
