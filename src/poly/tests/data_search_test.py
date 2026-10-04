"""Tests for poly conversations search and poly transcripts search|get.

Copyright PolyAI Limited
"""

import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.conversations import ConversationsCommand
from poly.cli_commands.transcripts import TranscriptsCommand


def _search_args(**overrides) -> Namespace:
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


def _transcript_args(**overrides) -> Namespace:
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


def _http_error(status: int, detail: str | None = None) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {"detail": detail} if detail else {}
    response.text = detail or ""
    return requests.HTTPError(response=response)


def _project() -> MagicMock:
    project = MagicMock(region="uk-1", project_id="proj1")
    project.get_conversation_url.side_effect = lambda cid: f"https://studio/{cid}"
    return project


class ConversationsSearchTest(unittest.TestCase):
    """Tests for ConversationsCommand.conversations_search."""

    @patch("poly.output.console.print_conversation_search")
    @patch("poly.cli_commands.conversations.AgentStudioInterface.search_conversations")
    @patch("poly.cli_commands.conversations.load_project")
    def test_builds_full_body(self, mock_load, mock_api, mock_print):
        """Every flag lands in the request body under the gateway's field name."""
        mock_load.return_value = _project()
        mock_api.return_value = {
            "conversations": [{"conversation_id": "c1", "metrics": {"poly_score": 4}}],
            "total": 1,
            "limit": 5,
            "offset": 0,
        }
        args = _search_args(
            from_dt="2026-09-01",
            to_dt="2026-09-30",
            filter=[["poly_score", "gte", "80"], ["channel", "in", "CHAT,SMS"]],
            any=True,
            channel=["VOICE-SIP"],
            env=["live"],
            field=["poly_score", "handoff"],
            sort="duration:desc",
            limit=5,
            offset=10,
        )

        ConversationsCommand.conversations_search("/tmp/p", args, output_json=False)

        self.assertEqual(mock_api.call_args.kwargs["region"], "uk-1")
        body = mock_api.call_args.kwargs["body"]
        self.assertEqual(
            body,
            {
                "fields": ["poly_score", "handoff"],
                "limit": 5,
                "offset": 10,
                "from_datetime": "2026-09-01T00:00:00",
                "to_datetime": "2026-10-01T00:00:00",
                "filters": [
                    {"metric": "poly_score", "op": "gte", "value": 80},
                    {"metric": "channel", "op": "in", "value": ["CHAT", "SMS"]},
                ],
                "channel": ["VOICE-SIP"],
                "client_env": ["live"],
                "sort": {"field": "duration", "order": "desc"},
                "filter_operator": "or",
                "project_id": "proj1",
            },
        )
        mock_print.assert_called_once()
        self.assertEqual(mock_print.call_args.kwargs["fields"], ["poly_score", "handoff"])

    @patch("poly.cli_commands.conversations.json_print")
    @patch("poly.cli_commands.conversations.AgentStudioInterface.search_conversations")
    @patch("poly.cli_commands.conversations.load_project")
    def test_defaults_fields_and_sends_no_nulls(self, mock_load, mock_api, mock_json):
        """With no flags the body carries the default fields and paging only."""
        mock_load.return_value = _project()
        mock_api.return_value = {"conversations": [], "total": 0}

        ConversationsCommand.conversations_search("/tmp/p", _search_args(), output_json=True)

        self.assertEqual(
            mock_api.call_args.kwargs["body"],
            {
                "fields": ["poly_score", "duration", "channel"],
                "limit": 20,
                "offset": 0,
                "project_id": "proj1",
            },
        )
        mock_json.assert_called_once_with({"conversations": [], "total": 0})

    @patch("poly.cli_commands.conversations.json_print")
    @patch("poly.cli_commands.conversations.load_project")
    def test_bad_sort_field_fails_before_request(self, mock_load, mock_json):
        """A sort field the gateway does not accept is rejected locally."""
        with self.assertRaises(SystemExit):
            ConversationsCommand.conversations_search(
                "/tmp/p", _search_args(sort="poly_score"), output_json=True
            )
        mock_load.assert_not_called()
        self.assertIn("started_at", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.conversations.json_print")
    @patch("poly.cli_commands.conversations.AgentStudioInterface.search_conversations")
    @patch("poly.cli_commands.conversations.load_project")
    def test_http_error_is_explained(self, mock_load, mock_api, mock_json):
        """A 403 is reported as a permission problem on the key."""
        mock_load.return_value = _project()
        mock_api.side_effect = _http_error(403)
        with self.assertRaises(SystemExit):
            ConversationsCommand.conversations_search("/tmp/p", _search_args(), output_json=True)
        self.assertIn("permission", mock_json.call_args[0][0]["error"])


class TranscriptsSearchTest(unittest.TestCase):
    """Tests for TranscriptsCommand.transcripts_search."""

    @patch("poly.output.console.print_transcript_matches")
    @patch("poly.cli_commands.transcripts.AgentStudioInterface.search_transcripts")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_builds_params_and_always_sends_project(self, mock_load, mock_api, mock_print):
        """Query flags become the gateway's query parameters; project_id is always set."""
        mock_load.return_value = _project()
        mock_api.return_value = {
            "results": [{"conversation_id": "c1", "project_id": "proj1", "matched_turns": []}],
            "total": 1,
        }
        args = _transcript_args(
            query="  cancel my booking ", from_dt="2026-09-01", to_dt="2026-09-30", context=2,
            limit=50, offset=100,
        )

        TranscriptsCommand.transcripts_search("/tmp/p", args, output_json=False)

        self.assertEqual(mock_api.call_args.kwargs["region"], "uk-1")
        self.assertEqual(
            mock_api.call_args.kwargs["params"],
            {
                "q": "cancel my booking",
                "context_turns": 2,
                "limit": 50,
                "offset": 100,
                "from": "2026-09-01T00:00:00",
                "to": "2026-10-01T00:00:00",
                "project_id": "proj1",
            },
        )
        mock_print.assert_called_once()
        self.assertEqual(mock_print.call_args[0][1], "  cancel my booking ")

    @patch("poly.cli_commands.transcripts.json_print")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_short_query_fails_before_request(self, mock_load, mock_json):
        """The gateway requires 3 to 300 characters; say so before calling it."""
        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search(
                "/tmp/p", _transcript_args(query="hi"), output_json=True
            )
        mock_load.assert_not_called()
        self.assertIn("3 to 300", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.transcripts.json_print")
    @patch("poly.cli_commands.transcripts.AgentStudioInterface.search_transcripts")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_403_names_pii_permission(self, mock_load, mock_api, mock_json):
        """Transcript routes need PII read outright, so a 403 names that permission."""
        mock_load.return_value = _project()
        mock_api.side_effect = _http_error(403)
        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search("/tmp/p", _transcript_args(), output_json=True)
        self.assertIn("PII read", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.transcripts.json_print")
    @patch("poly.cli_commands.transcripts.AgentStudioInterface.search_transcripts")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_429_explains_rate_limit(self, mock_load, mock_api, mock_json):
        """A 429 explains the per-key limit rather than dumping the response."""
        mock_load.return_value = _project()
        mock_api.side_effect = _http_error(429)
        with self.assertRaises(SystemExit):
            TranscriptsCommand.transcripts_search("/tmp/p", _transcript_args(), output_json=True)
        self.assertIn("100 requests", mock_json.call_args[0][0]["error"])


class TranscriptsGetTest(unittest.TestCase):
    """Tests for TranscriptsCommand.transcripts_get."""

    @patch("poly.output.console.print_transcript")
    @patch("poly.cli_commands.transcripts.AgentStudioInterface.get_transcript")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_fetches_with_project_and_prints(self, mock_load, mock_api, mock_print):
        """The transcript is fetched for the loaded project and printed with a Studio link."""
        mock_load.return_value = _project()
        mock_api.return_value = {"conversation_id": "c1", "turns": [], "total_turns": 0}

        TranscriptsCommand.transcripts_get("/tmp/p", "c1", english=True, output_json=False)

        mock_api.assert_called_once_with(region="uk-1", conversation_id="c1", project_id="proj1")
        self.assertEqual(mock_print.call_args.kwargs["english"], True)
        self.assertEqual(mock_print.call_args.kwargs["studio_url"], "https://studio/c1")

    @patch("poly.cli_commands.transcripts.json_print")
    @patch("poly.cli_commands.transcripts.AgentStudioInterface.get_transcript")
    @patch("poly.cli_commands.transcripts.load_project")
    def test_json_passes_result_through(self, mock_load, mock_api, mock_json):
        """--json emits the gateway payload untouched."""
        mock_load.return_value = _project()
        mock_api.return_value = {"conversation_id": "c1", "turns": [{"turn_index": 0}]}
        TranscriptsCommand.transcripts_get("/tmp/p", "c1", output_json=True)
        mock_json.assert_called_once_with(mock_api.return_value)


class ConsolePrintersTest(unittest.TestCase):
    """Smoke tests for the search and transcript printers."""

    def _capture(self, fn, *args, **kwargs) -> str:
        from io import StringIO

        from rich.console import Console

        from poly.output import console as console_module

        buffer = StringIO()
        with patch.object(console_module, "console", Console(file=buffer, width=160, force_terminal=False)):
            fn(*args, **kwargs)
        return buffer.getvalue()

    def test_conversation_search_table_has_metric_columns_and_pii_warning(self):
        """Requested fields become columns; missing PII fields produce a warning."""
        from poly.output.console import print_conversation_search

        result = {
            "conversations": [
                {
                    "conversation_id": "conv-1",
                    "started_at": "2026-09-30T10:00:00+00:00",
                    "duration_seconds": 95,
                    "metrics": {"poly_score": 4.5, "channel": "CHAT"},
                }
            ],
            "total": 30,
            "limit": 1,
            "offset": 0,
        }
        with patch("poly.output.console.warning") as mock_warning:
            out = self._capture(
                print_conversation_search,
                result,
                fields=["poly_score", "duration", "channel", "call_summary"],
            )
        self.assertIn("conv-1", out)
        self.assertIn("poly_score", out)
        self.assertIn("4.50", out)
        self.assertIn("CHAT", out)
        self.assertEqual(out.lower().split("\n")[0].count("duration"), 1)  # no duplicate column
        self.assertIn("--offset 1", out)
        self.assertIn("call_summary", mock_warning.call_args[0][0])

    def test_transcript_matches_show_context_and_highlight(self):
        """Matched turns are printed between their context turns with the query highlighted."""
        from poly.output.console import print_transcript_matches

        result = {
            "results": [
                {
                    "conversation_id": "conv-1",
                    "project_id": "proj1",
                    "matched_turns": [
                        {
                            "turn_index": 2,
                            "user_input": "I want to cancel my booking please",
                            "user_input_datetime": "2026-09-30T10:00:05+00:00",
                            "agent_response": "Sure, which booking?",
                            "context": {
                                "before": [{"turn_index": 1, "user_input": "hello", "agent_response": "hi"}],
                                "after": [{"turn_index": 3, "user_input": "the one on friday"}],
                            },
                        }
                    ],
                }
            ],
            "total": 1,
            "limit": 20,
            "offset": 0,
        }
        out = self._capture(print_transcript_matches, result, "cancel my booking")
        self.assertIn("conv-1", out)
        self.assertIn("1 match", out)
        self.assertIn("hello", out)
        self.assertIn("cancel my booking", out)
        self.assertIn("the one on friday", out)
        self.assertLess(out.index("hello"), out.index("cancel my booking"))
        self.assertLess(out.index("cancel my booking"), out.index("the one on friday"))

    def test_transcript_prefers_english_when_asked(self):
        """--english swaps in the translated text where it exists."""
        from poly.output.console import print_transcript

        transcript = {
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
        original = self._capture(print_transcript, transcript)
        english = self._capture(print_transcript, transcript, english=True)
        self.assertIn("hola", original)
        self.assertIn("hello", english)
        self.assertIn("buenos días", english)  # no translation given, falls back
        self.assertIn("1 turns", english)
