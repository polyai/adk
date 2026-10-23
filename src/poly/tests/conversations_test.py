"""Tests for the conversations CLI commands backed by the Data API.

Copyright PolyAI Limited
"""

import json
import os
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.conversations import ConversationsCommand
from poly.output.console import console
from poly.project import AgentStudioProject

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_projects", "test_project")
with open(os.path.join(TEST_DIR, "test_project.json"), encoding="utf-8") as _f:
    PROJECT_DATA = json.load(_f)


def _search_args(**overrides) -> Namespace:
    """A Namespace with every `conversations search` flag at its parser default."""
    base = {
        "from_dt": None,
        "to_dt": None,
        "filter": None,
        "any": False,
        "channel": None,
        "env": None,
        "field": None,
        "sort": None,
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


class ConversationsSearchTest(unittest.TestCase):
    """Tests for ConversationsCommand.conversations_search on the fixture project."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        patch("poly.cli_commands.conversations.load_project", return_value=self.project).start()
        self.mock_request = patch(
            "poly.handlers.platform_api.PlatformAPIHandler.make_request"
        ).start()
        self.addCleanup(patch.stopall)

    def _render(self, args: Namespace) -> str:
        with console.capture() as capture:
            ConversationsCommand.conversations_search(TEST_DIR, args, output_json=False)
        return capture.get()

    def test_every_flag_reaches_the_request_body(self):
        """Flags map onto the search body under the Data API's field names."""
        self.mock_request.return_value = {
            "conversations": [
                {
                    "conversation_id": "conv-1",
                    "started_at": "2026-09-30T10:00:00+00:00",
                    "duration_seconds": 95,
                    "metrics": {"poly_score": 4.5, "handoff": True},
                }
            ],
            "total": 1,
            "limit": 5,
            "offset": 10,
        }
        args = _search_args(
            from_dt="2026-09-01",
            to_dt="2026-09-30",
            filter=[["poly_score", "gte", "80"], ["call_summary", "contains", "refund"]],
            any=True,
            channel=["VOICE-SIP"],
            env=["live"],
            field=["poly_score", "handoff"],
            sort="duration:desc",
            limit=5,
            offset=10,
        )

        output = self._render(args)

        region, endpoint, method = self.mock_request.call_args.args
        self.assertEqual((region, endpoint, method), ("us-1", "/api/v1/conversations/search", "POST"))
        self.assertEqual(
            self.mock_request.call_args.kwargs["data"],
            {
                "project_id": "test_project",
                "limit": 5,
                "offset": 10,
                "from": "2026-09-01T00:00:00",
                "to": "2026-10-01T00:00:00",
                "filters": [
                    {"metric": "poly_score", "op": "gte", "value": 80},
                    {"metric": "call_summary", "op": "contains", "value": "refund"},
                ],
                "filter_operator": "or",
                "channel": ["VOICE-SIP"],
                "client_env": ["live"],
                "fields": ["poly_score", "handoff"],
                "sort": {"field": "duration", "order": "desc"},
            },
        )
        self.assertIn("conv-1", output)
        self.assertIn("4.50", output)

    @patch("poly.cli_commands.conversations.json_print")
    def test_defaults_fields_and_sends_no_nulls(self, mock_json):
        """With no flags the body carries the project, default fields and paging only."""
        self.mock_request.return_value = {"conversations": [], "total": 0}

        ConversationsCommand.conversations_search(TEST_DIR, _search_args(), output_json=True)

        self.assertEqual(
            self.mock_request.call_args.kwargs["data"],
            {
                "project_id": "test_project",
                "limit": 20,
                "offset": 0,
                "fields": ["poly_score", "duration", "channel"],
            },
        )
        mock_json.assert_called_once_with({"conversations": [], "total": 0})

    @patch("poly.cli_commands.conversations.json_print")
    def test_bad_sort_field_fails_before_request(self, mock_json):
        """A sort field the Data API does not accept is rejected locally."""
        with self.assertRaises(SystemExit):
            ConversationsCommand.conversations_search(
                TEST_DIR, _search_args(sort="poly_score"), output_json=True
            )

        self.mock_request.assert_not_called()
        self.assertIn("started_at", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.conversations.json_print")
    def test_http_error_is_explained(self, mock_json):
        """A 403 is reported as a permission problem on the key."""
        self.mock_request.side_effect = _http_error(403)

        with self.assertRaises(SystemExit):
            ConversationsCommand.conversations_search(TEST_DIR, _search_args(), output_json=True)

        self.assertIn("permission", mock_json.call_args[0][0]["error"])
