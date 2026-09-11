"""Tests for the wren command module.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.cli_commands.wren import (
    _format_change_summary,
    _parse_apply_changes,
    _stream_turn,
)


def _make_project() -> MagicMock:
    """Create a mock AgentStudioProject."""
    project = MagicMock()
    project.region = "studio"
    project.account_id = "test-account"
    project.project_id = "test-project"
    project.branch_id = "main"
    project.get_branches.return_value = ("main", {"main": "main", "dev": "BRANCH-123"})
    return project


def _events(*types: dict) -> list[dict]:
    """Shorthand to build an event list."""
    return list(types)


class ParseApplyChangesTests(unittest.TestCase):
    """Tests for _parse_apply_changes."""

    def test_parse_from_details_changes(self) -> None:
        """Parse changes from result.details.changes list."""
        result = {
            "details": {
                "changes": [
                    {"changeType": "ADDED", "path": "/flows/new.yaml"},
                    {"changeType": "MODIFIED", "path": "/flows/main.yaml"},
                    {"changeType": "DELETED", "path": "/flows/old.yaml"},
                ]
            }
        }
        counts = _parse_apply_changes(result)
        self.assertEqual(counts, {"modified": 1, "added": 1, "deleted": 1})

    def test_parse_from_text_fallback(self) -> None:
        """Parse changes from content text format."""
        result = {
            "content": [
                {
                    "text": (
                        "Modified:\n"
                        "  flows/main.yaml\n"
                        "  flows/other.yaml\n"
                        "Added:\n"
                        "  flows/new.yaml\n"
                    )
                }
            ]
        }
        counts = _parse_apply_changes(result)
        self.assertEqual(counts, {"modified": 2, "added": 1, "deleted": 0})

    def test_parse_empty_result(self) -> None:
        """Empty result returns zero counts."""
        counts = _parse_apply_changes({})
        self.assertEqual(counts, {"modified": 0, "added": 0, "deleted": 0})

    def test_parse_none_result(self) -> None:
        """None result returns zero counts."""
        counts = _parse_apply_changes(None)
        self.assertEqual(counts, {"modified": 0, "added": 0, "deleted": 0})

    def test_parse_string_content(self) -> None:
        """Parse when content items are plain strings."""
        result = {"content": ["Modified:\n  a.yaml\nAdded:\n  b.yaml\n  c.yaml"]}
        counts = _parse_apply_changes(result)
        self.assertEqual(counts, {"modified": 1, "added": 2, "deleted": 0})


class FormatChangeSummaryTests(unittest.TestCase):
    """Tests for _format_change_summary."""

    def test_format_mixed(self) -> None:
        """Format a mixed change summary."""
        result = _format_change_summary({"modified": 2, "added": 1, "deleted": 0})
        self.assertEqual(result, "✔ Applied 3 changes to the branch (2 modified, 1 added)")

    def test_format_single(self) -> None:
        """Format a single change."""
        result = _format_change_summary({"modified": 1, "added": 0, "deleted": 0})
        self.assertEqual(result, "✔ Applied 1 change to the branch (1 modified)")

    def test_format_zero(self) -> None:
        """Zero changes returns empty string."""
        result = _format_change_summary({"modified": 0, "added": 0, "deleted": 0})
        self.assertEqual(result, "")


class ToolActivityTests(unittest.TestCase):
    """Tests for _tool_activity spinner descriptions."""

    def test_prefers_ui_description(self) -> None:
        """ui_description from tool arguments wins over tool names."""
        from poly.cli_commands.wren import _tool_activity

        message = {
            "content": [
                {
                    "type": "toolCall",
                    "name": "plan",
                    "arguments": {"ui_description": "Planning 10 hotel FAQ topics"},
                }
            ]
        }
        self.assertEqual(_tool_activity(message), "Planning 10 hotel FAQ topics…")

    def test_falls_back_to_tool_names(self) -> None:
        """Without descriptions, tool names are shown."""
        from poly.cli_commands.wren import _tool_activity

        message = {
            "content": [
                {"type": "toolCall", "name": "read", "arguments": {}},
                {"type": "toolCall", "name": "write", "arguments": {}},
            ]
        }
        self.assertEqual(_tool_activity(message), "Running: read, write…")

    def test_no_tools_returns_none(self) -> None:
        """Text-only messages yield no activity."""
        from poly.cli_commands.wren import _tool_activity

        self.assertIsNone(_tool_activity({"content": [{"type": "text", "text": "hi"}]}))
        self.assertIsNone(_tool_activity({}))
        self.assertIsNone(_tool_activity(None))


class StreamTurnTests(unittest.TestCase):
    """Tests for _stream_turn event handling."""

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_complete_is_not_fatal(self, mock_stream: MagicMock) -> None:
        """A complete event should not set fatal — the REPL continues."""
        mock_stream.return_value = iter(
            [
                {"type": "session_init", "sessionId": "sess-1"},
                {"type": "complete", "totalSteps": 2, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertFalse(result.fatal)
        self.assertEqual(result.session_id, "sess-1")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_multi_turn_session_preserved(self, mock_stream: MagicMock) -> None:
        """Session ID should be preserved across turns."""
        mock_stream.return_value = iter(
            [
                {"type": "session_init", "sessionId": "sess-abc"},
                {"type": "message_start", "message": {"role": "assistant", "content": []}},
                {"type": "message_delta", "delta": "Hi"},
                {"type": "message_end", "message": {"role": "assistant", "content": []}},
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertEqual(result.session_id, "sess-abc")
        self.assertEqual(result.messages, ["Hi"])

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_apply_sets_changes_applied(self, mock_stream: MagicMock) -> None:
        """A successful apply tool should set changes_applied."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "tool_execution_end",
                    "toolCallId": "tc-1",
                    "toolName": "apply",
                    "isError": False,
                    "result": {
                        "details": {"changes": [{"changeType": "MODIFIED", "path": "a.yaml"}]}
                    },
                },
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "do stuff", None, json_mode=True)
        self.assertTrue(result.changes_applied)
        self.assertEqual(result.changes, {"modified": 1, "added": 0, "deleted": 0})

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_apply_zero_changes_not_flagged(self, mock_stream: MagicMock) -> None:
        """Apply with no actual changes should not set changes_applied."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "tool_execution_end",
                    "toolCallId": "tc-1",
                    "toolName": "apply",
                    "isError": False,
                    "result": {"details": {"changes": []}},
                },
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "do stuff", None, json_mode=True)
        self.assertFalse(result.changes_applied)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_error_not_fatal_after_first_turn(self, mock_stream: MagicMock) -> None:
        """Error events should not be fatal (user can retry)."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "error",
                    "errorCode": "llm_rate_limited",
                    "message": "Rate limited",
                },
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True, first_turn=False)
        self.assertFalse(result.fatal)
        self.assertIsNotNone(result.error)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_unauthorized_fatal_on_first_turn(self, mock_stream: MagicMock) -> None:
        """Unauthorized on first turn should be fatal."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "error",
                    "errorCode": "unauthorized",
                    "message": "Not authorized",
                },
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True, first_turn=True)
        self.assertTrue(result.fatal)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_aborted_not_fatal(self, mock_stream: MagicMock) -> None:
        """Aborted events should not be fatal."""
        mock_stream.return_value = iter([{"type": "aborted", "reason": "user_aborted"}])
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertFalse(result.fatal)
        self.assertEqual(result.error["code"], "aborted")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_unknown_events_ignored(self, mock_stream: MagicMock) -> None:
        """Unknown event types should be silently ignored."""
        mock_stream.return_value = iter(
            [
                {"type": "some_future_event", "data": "foo"},
                {"type": "complete", "totalSteps": 0, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertFalse(result.fatal)
        self.assertIsNone(result.error)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_branch_change_switches_project(self, mock_stream: MagicMock) -> None:
        """Branch change event should switch the project's branch."""
        mock_stream.return_value = iter(
            [
                {"type": "branch_change", "branch": "BRANCH-NEW", "action": "create"},
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        project.get_branches.return_value = (
            "main",
            {"main": "main", "my-branch": "BRANCH-NEW"},
        )
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        project.api_handler.switch_branch.assert_called_once_with("BRANCH-NEW")
        self.assertEqual(project.branch_id, "BRANCH-NEW")
        self.assertIsNotNone(result.branch_info)
        self.assertEqual(result.branch_info["id"], "BRANCH-NEW")
        self.assertEqual(result.branch_info["name"], "my-branch")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_branch_name_lookup_failure_uses_id(self, mock_stream: MagicMock) -> None:
        """If branch name lookup fails, should use ID only."""
        mock_stream.return_value = iter(
            [
                {"type": "branch_change", "branch": "BRANCH-UNKNOWN", "action": "create"},
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        project.get_branches.side_effect = Exception("API error")
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertIsNotNone(result.branch_info)
        self.assertEqual(result.branch_info["id"], "BRANCH-UNKNOWN")
        self.assertNotIn("name", result.branch_info)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_user_input_required_captured(self, mock_stream: MagicMock) -> None:
        """A non-auto user_input_required should be captured as pending_input."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "user_input_required",
                    "requestId": "req-1",
                    "inputKind": "question",
                    "questions": [{"question": "Which language?"}],
                },
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertIsNotNone(result.pending_input)
        self.assertEqual(result.pending_input["inputKind"], "question")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_auto_gate_is_not_pending_input(self, mock_stream: MagicMock) -> None:
        """An auto-flagged gate is informational — the run continues without us."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "user_input_required",
                    "requestId": "req-1",
                    "inputKind": "question",
                    "auto": True,
                    "questions": [{"question": "Proceed?"}],
                },
                {
                    "type": "user_input_answered",
                    "requestId": "req-1",
                    "inputKind": "question",
                    "auto": True,
                    "value": {"answers": [{"selected": ["Yes"]}]},
                },
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertIsNone(result.pending_input)
        self.assertIsNone(result.error)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_http_401_is_fatal(self, mock_stream: MagicMock) -> None:
        """HTTP 401 should set fatal=True."""
        import requests

        response = MagicMock()
        response.status_code = 401
        mock_stream.side_effect = requests.HTTPError(response=response)
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertTrue(result.fatal)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_connection_error_is_fatal(self, mock_stream: MagicMock) -> None:
        """ConnectionError should set fatal=True."""
        import requests

        mock_stream.side_effect = requests.ConnectionError("refused")
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertTrue(result.fatal)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_http_409_is_run_in_progress_not_fatal(self, mock_stream: MagicMock) -> None:
        """HTTP 409 should map to run_in_progress and not be fatal."""
        import requests

        response = MagicMock()
        response.status_code = 409
        mock_stream.side_effect = requests.HTTPError(response=response)
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertFalse(result.fatal)
        self.assertEqual(result.error["code"], "run_in_progress")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_suspended_complete_captured(self, mock_stream: MagicMock) -> None:
        """A complete event with suspended=true should set result.suspended."""
        mock_stream.return_value = iter(
            [{"type": "complete", "totalSteps": 3, "usageByAgent": {}, "suspended": True}]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertTrue(result.suspended)
        self.assertFalse(result.fatal)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_subagent_messages_not_accumulated(self, mock_stream: MagicMock) -> None:
        """Message text from depth > 0 (subagents) should not be accumulated."""
        mock_stream.return_value = iter(
            [
                {"type": "message_start", "depth": 1, "message": {}},
                {"type": "message_delta", "depth": 1, "delta": "subagent text"},
                {"type": "message_end", "depth": 1, "message": {}},
                {"type": "message_start", "depth": 0, "message": {}},
                {"type": "message_delta", "depth": 0, "delta": "top-level text"},
                {"type": "message_end", "depth": 0, "message": {}},
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertEqual(result.messages, ["top-level text"])

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_empty_messages_not_accumulated(self, mock_stream: MagicMock) -> None:
        """Tool-only messages (no text deltas) should not produce entries."""
        mock_stream.return_value = iter(
            [
                {"type": "message_start", "depth": 0, "message": {}},
                {"type": "message_end", "depth": 0, "message": {}},
                {"type": "message_start", "depth": 0, "message": {}},
                {"type": "message_delta", "depth": 0, "delta": "real text"},
                {"type": "message_end", "depth": 0, "message": {}},
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertEqual(result.messages, ["real text"])


def _fake_sse_response(events: list[dict]) -> MagicMock:
    """Build a fake requests response streaming the given events as SSE lines."""
    import json

    response = MagicMock()
    response.iter_lines.return_value = iter([f"data: {json.dumps(e)}" for e in events])
    response.raise_for_status.return_value = None
    return response


class StreamWrenTurnTests(unittest.TestCase):
    """Tests for the SSE client's terminal-event semantics."""

    @patch("poly.handlers.wren_api.requests.post")
    def test_continues_past_mid_chain_completes(self, mock_post: MagicMock) -> None:
        """Suspended and depth>0 completes must not end the stream."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response(
            [
                {"type": "complete", "depth": 0, "suspended": True},
                {"type": "message_delta", "depth": 1, "delta": "subagent"},
                {"type": "complete", "depth": 1},
                {"type": "complete", "depth": 0},
                {"type": "message_delta", "depth": 0, "delta": "after terminal"},
            ]
        )
        events = list(stream_wren_turn("studio", "key", "hi", {"accountId": "a"}))
        types = [(e.get("type"), e.get("depth")) for e in events]
        # Stops at the depth-0 non-suspended complete; the late frame is not read.
        self.assertEqual(
            types,
            [
                ("complete", 0),
                ("message_delta", 1),
                ("complete", 1),
                ("complete", 0),
            ],
        )

    @patch("poly.handlers.wren_api.requests.post")
    def test_continues_past_auto_gate(self, mock_post: MagicMock) -> None:
        """Auto-flagged user_input_required must not end the stream."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response(
            [
                {"type": "user_input_required", "auto": True, "inputKind": "question"},
                {"type": "message_delta", "depth": 0, "delta": "continuing"},
                {"type": "complete", "depth": 0},
            ]
        )
        events = list(stream_wren_turn("studio", "key", "hi", {"accountId": "a"}))
        self.assertEqual(len(events), 3)

    @patch("poly.handlers.wren_api.requests.post")
    def test_non_auto_gate_is_terminal(self, mock_post: MagicMock) -> None:
        """A non-auto user_input_required still ends the stream."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response(
            [
                {"type": "user_input_required", "inputKind": "question"},
                {"type": "message_delta", "depth": 0, "delta": "should not arrive"},
            ]
        )
        events = list(stream_wren_turn("studio", "key", "hi", {"accountId": "a"}))
        self.assertEqual(len(events), 1)


class ReportAndPlanTests(unittest.TestCase):
    """Tests for submit_report capture and subagent failure quieting."""

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_submit_report_captured(self, mock_stream: MagicMock) -> None:
        """The submit_report result should be captured on TurnResult.report."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "tool_execution_end",
                    "depth": 0,
                    "toolName": "submit_report",
                    "isError": False,
                    "result": {
                        "content": [{"type": "text", "text": "## Summary\n\nBuilt a quiz flow."}],
                        "details": {"title": "Quiz flow built"},
                    },
                },
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertEqual(result.report["title"], "Quiz flow built")
        self.assertIn("quiz flow", result.report["text"])

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_subagent_tool_failure_not_recorded_as_error(self, mock_stream: MagicMock) -> None:
        """A depth>0 tool failure is agent-internal — no TurnResult error."""
        mock_stream.return_value = iter(
            [
                {
                    "type": "tool_execution_end",
                    "depth": 2,
                    "toolName": "read",
                    "isError": True,
                    "result": {"content": [{"type": "text", "text": "ENOENT"}]},
                },
                {"type": "complete", "totalSteps": 1, "usageByAgent": {}},
            ]
        )
        project = _make_project()
        result = _stream_turn(project, "key", "hello", None, json_mode=True)
        self.assertIsNone(result.error)
        self.assertEqual(result.tool_calls, [{"toolName": "read", "isError": True}])


class MermaidLinkTests(unittest.TestCase):
    """Tests for mermaid.live link generation."""

    def test_url_round_trips_the_diagram(self) -> None:
        """The pako URL should decode back to the diagram source."""
        import base64
        import json
        import zlib

        from poly.cli_commands.wren import _mermaid_live_url

        code = "graph TD\n  A --> B"
        url = _mermaid_live_url(code)
        self.assertTrue(url.startswith("https://mermaid.live/view#pako:"))
        encoded = url.split("#pako:", 1)[1]
        state = json.loads(zlib.decompress(base64.urlsafe_b64decode(encoded)))
        self.assertEqual(state["code"], code)


class ReplayAdapterTests(unittest.TestCase):
    """Tests for the persisted → streaming event adapter."""

    def test_turn_end_synthesizes_stream(self) -> None:
        """A persisted turn_end becomes message events + tool_execution_ends."""
        from poly.cli_commands.wren_replay import synthesize_turn_events

        turn_end = {
            "type": "turn_end",
            "depth": 0,
            "sessionId": "sess-1",
            "message": {
                "role": "assistant",
                "depth": 0,
                "content": [
                    {"type": "thinking", "thinking": "hmm"},
                    {"type": "text", "text": "Hello there"},
                    {"type": "toolCall", "name": "apply", "id": "tc-1", "arguments": {}},
                ],
            },
            "toolResults": [
                {
                    "toolCallId": "tc-1",
                    "toolName": "apply",
                    "isError": False,
                    "content": [{"type": "text", "text": "Applied changes"}],
                    "details": {"changes": [{"changeType": "ADDED", "path": "a.yaml"}]},
                }
            ],
        }
        events = list(synthesize_turn_events(turn_end))
        types = [e["type"] for e in events]
        self.assertEqual(types[0], "message_start")
        self.assertEqual(types[-2], "message_end")
        self.assertEqual(types[-1], "tool_execution_end")
        deltas = "".join(e["delta"] for e in events if e["type"] == "message_delta")
        self.assertEqual(deltas, "Hello there")
        tool_end = events[-1]
        self.assertEqual(tool_end["toolName"], "apply")
        self.assertEqual(tool_end["result"]["details"]["changes"][0]["changeType"], "ADDED")

    def test_segments_split_on_user_messages(self) -> None:
        """Conversation splits into per-user-prompt segments."""
        from poly.cli_commands.wren_replay import replay_segments

        conv = {
            "messages": [
                {"type": "auto_pull", "message": {"type": "auto_pull", "reason": "initial"}},
                {"type": "user", "message": {"content": "first"}},
                {"type": "complete", "message": {"type": "complete"}},
                {"type": "user", "message": {"content": "second"}},
                {"type": "aborted", "message": {"type": "aborted", "reason": "user_aborted"}},
            ]
        }
        segments = list(replay_segments(conv))
        self.assertEqual(len(segments), 3)
        self.assertIsNone(segments[0][0])  # leading system events, no prompt
        self.assertEqual(segments[1][0], "first")
        self.assertEqual(segments[2][0], "second")

    def test_replayed_conv_renders_through_real_renderer(self) -> None:
        """A minimal conversation renders via _render_events without errors."""
        from poly.cli_commands.wren import TurnResult, _render_events, _TurnDisplay
        from poly.cli_commands.wren_replay import replay_segments, segment_events

        conv = {
            "messages": [
                {"type": "user", "message": {"content": "hi"}},
                {
                    "type": "turn_end",
                    "message": {
                        "type": "turn_end",
                        "depth": 0,
                        "sessionId": "s",
                        "message": {
                            "role": "assistant",
                            "depth": 0,
                            "content": [{"type": "text", "text": "**bold** reply"}],
                        },
                        "toolResults": [],
                    },
                },
                {
                    "type": "complete",
                    "message": {"type": "complete", "depth": 0, "totalSteps": 1},
                },
            ]
        }
        for prompt, segment in replay_segments(conv):
            result = TurnResult()
            display = _TurnDisplay(enabled=False)
            _render_events(segment_events(segment), result, display)
        self.assertEqual(result.messages, ["**bold** reply"])
        self.assertFalse(result.suspended)


class TurnWithRetryTests(unittest.TestCase):
    """Tests for the run_in_progress wait-and-retry wrapper."""

    @patch("poly.cli_commands.wren._stream_turn")
    def test_retries_while_busy(self, mock_turn: MagicMock) -> None:
        """run_in_progress results should be retried until the turn succeeds."""
        from poly.cli_commands.wren import TurnResult, _turn_with_retry

        busy = TurnResult(error={"code": "run_in_progress", "message": "busy"})
        done = TurnResult(session_id="sess-1")
        mock_turn.side_effect = [busy, busy, done]
        with patch("time.sleep"):
            result = _turn_with_retry(_make_project(), "key", "hi", None, json_mode=True)
        self.assertIsNone(result.error)
        self.assertEqual(result.session_id, "sess-1")
        self.assertEqual(mock_turn.call_count, 3)

    @patch("poly.cli_commands.wren._stream_turn")
    def test_no_retry_on_other_errors(self, mock_turn: MagicMock) -> None:
        """Non-busy errors should be returned immediately."""
        from poly.cli_commands.wren import TurnResult, _turn_with_retry

        failed = TurnResult(error={"code": "llm_internal", "message": "boom"})
        mock_turn.return_value = failed
        result = _turn_with_retry(_make_project(), "key", "hi", None, json_mode=True)
        self.assertEqual(result.error["code"], "llm_internal")
        self.assertEqual(mock_turn.call_count, 1)


class BuildContextTests(unittest.TestCase):
    """Tests for _build_context."""

    def test_context_without_mode_omits_mode_key(self) -> None:
        """No mode argument means no "mode" in the context sent to the server."""
        from poly.cli_commands.wren import _build_context

        context = _build_context(_make_project())
        self.assertEqual(
            context,
            {"accountId": "test-account", "projectId": "test-project", "branchId": "main"},
        )

    def test_context_with_mode_includes_mode_key(self) -> None:
        """A mode argument is pinned explicitly into the context."""
        from poly.cli_commands.wren import _build_context

        context = _build_context(_make_project(), mode="interactive")
        self.assertEqual(context["mode"], "interactive")


class ClientMessageBodyTests(unittest.TestCase):
    """Tests for the JSON bodies POSTed to the wren endpoint."""

    @patch("poly.handlers.wren_api.requests.post")
    def test_prompt_body_is_schema_first(self, mock_post: MagicMock) -> None:
        """A plain prompt sends type/content/context and nothing else."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response([{"type": "complete", "depth": 0}])
        list(stream_wren_turn("studio", "key", "hi", {"accountId": "a"}))
        self.assertEqual(
            mock_post.call_args.kwargs["json"],
            {"type": "prompt", "content": "hi", "context": {"accountId": "a"}},
        )

    @patch("poly.handlers.wren_api.requests.post")
    def test_prompt_body_includes_session_and_agent_when_given(self, mock_post: MagicMock) -> None:
        """Session ID and agent name are added when provided."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response([{"type": "complete", "depth": 0}])
        list(
            stream_wren_turn(
                "studio",
                "key",
                "hi",
                {"accountId": "a"},
                session_id="sess-1",
                agent_name="planner",
            )
        )
        body = mock_post.call_args.kwargs["json"]
        self.assertEqual(body["sessionId"], "sess-1")
        self.assertEqual(body["agentName"], "planner")

    @patch("poly.handlers.wren_api.requests.post")
    def test_empty_session_and_agent_are_omitted(self, mock_post: MagicMock) -> None:
        """Falsy session ID and agent name must not be sent as empty strings."""
        from poly.handlers.wren_api import stream_wren_turn

        mock_post.return_value = _fake_sse_response([{"type": "complete", "depth": 0}])
        list(stream_wren_turn("studio", "key", "hi", {"accountId": "a"}, "", ""))
        body = mock_post.call_args.kwargs["json"]
        self.assertNotIn("sessionId", body)
        self.assertNotIn("agentName", body)

    @patch("poly.handlers.wren_api.requests.post")
    def test_input_response_body(self, mock_post: MagicMock) -> None:
        """Answering a gate sends an input_response message with requestId and answer."""
        from poly.handlers.wren_api import stream_wren_input_response

        mock_post.return_value = _fake_sse_response([{"type": "complete", "depth": 0}])
        answer = {"inputKind": "plan", "value": {"approved": True}}
        list(
            stream_wren_input_response(
                "studio", "key", "req-1", answer, {"accountId": "a"}, "sess-1"
            )
        )
        self.assertEqual(
            mock_post.call_args.kwargs["json"],
            {
                "type": "input_response",
                "sessionId": "sess-1",
                "context": {"accountId": "a"},
                "requestId": "req-1",
                "answer": answer,
            },
        )


class InputResponseStreamTests(unittest.TestCase):
    """Tests for terminal-event semantics on a resumed input_response stream."""

    @patch("poly.handlers.wren_api.requests.post")
    def test_stops_at_top_level_complete(self, mock_post: MagicMock) -> None:
        """A depth-0 non-suspended complete ends the resumed stream."""
        from poly.handlers.wren_api import stream_wren_input_response

        mock_post.return_value = _fake_sse_response(
            [
                {"type": "message_delta", "depth": 0, "delta": "resuming"},
                {"type": "complete", "depth": 0},
                {"type": "message_delta", "depth": 0, "delta": "should not arrive"},
            ]
        )
        events = list(
            stream_wren_input_response("studio", "key", "req-1", {}, {"accountId": "a"}, "sess-1")
        )
        self.assertEqual([e["type"] for e in events], ["message_delta", "complete"])

    @patch("poly.handlers.wren_api.requests.post")
    def test_continues_past_suspended_complete(self, mock_post: MagicMock) -> None:
        """A suspended complete is mid-chain — the resumed stream keeps going."""
        from poly.handlers.wren_api import stream_wren_input_response

        mock_post.return_value = _fake_sse_response(
            [
                {"type": "complete", "depth": 0, "suspended": True},
                {"type": "message_delta", "depth": 0, "delta": "still going"},
                {"type": "complete", "depth": 0},
            ]
        )
        events = list(
            stream_wren_input_response("studio", "key", "req-1", {}, {"accountId": "a"}, "sess-1")
        )
        self.assertEqual(len(events), 3)


def _fake_error_response(body: dict | ValueError) -> MagicMock:
    """Build a fake 400 response whose json() returns body (or raises it)."""
    import requests

    response = MagicMock()
    response.ok = False
    response.status_code = 400
    if isinstance(body, ValueError):
        response.json.side_effect = body
    else:
        response.json.return_value = body
    response.raise_for_status.side_effect = requests.HTTPError(response=response)
    return response


class ValidationErrorDetailTests(unittest.TestCase):
    """Tests for surfacing the server's 400 validation detail."""

    @patch("poly.handlers.wren_api.requests.post")
    def test_error_detail_becomes_the_exception_message(self, mock_post: MagicMock) -> None:
        """A JSON error body is raised as the HTTPError message."""
        import requests

        from poly.handlers.wren_api import stream_wren_turn

        detail = "Invalid request: context.projectId: Required"
        mock_post.return_value = _fake_error_response({"error": detail})
        with self.assertRaises(requests.HTTPError) as ctx:
            list(stream_wren_turn("studio", "key", "hi", {}))
        self.assertEqual(str(ctx.exception), detail)

    @patch("poly.handlers.wren_api.requests.post")
    def test_non_json_body_propagates_original_error(self, mock_post: MagicMock) -> None:
        """When the body isn't JSON, raise_for_status's own error propagates."""
        import requests

        from poly.handlers.wren_api import stream_wren_turn

        response = _fake_error_response(ValueError("not json"))
        original = response.raise_for_status.side_effect
        mock_post.return_value = response
        with self.assertRaises(requests.HTTPError) as ctx:
            list(stream_wren_turn("studio", "key", "hi", {}))
        self.assertIs(ctx.exception, original)


class CollectUserInputTests(unittest.TestCase):
    """Tests for _collect_user_input's typed answer shapes."""

    @patch("questionary.select")
    def test_single_select_question(self, mock_select: MagicMock) -> None:
        """Picking one option yields a single-entry selected list."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Blue"
        event = {
            "inputKind": "question",
            "questions": [{"question": "Favourite colour?", "options": ["Blue", "Red"]}],
        }
        self.assertEqual(
            _collect_user_input(event),
            {"inputKind": "question", "value": {"answers": [{"selected": ["Blue"]}]}},
        )

    @patch("questionary.checkbox")
    def test_multi_select_question_uses_checkbox(self, mock_checkbox: MagicMock) -> None:
        """allowMultiple questions collect every checked option."""
        from poly.cli_commands.wren import _collect_user_input

        mock_checkbox.return_value.ask.return_value = ["Blue", "Red"]
        event = {
            "inputKind": "question",
            "questions": [
                {
                    "question": "Which colours?",
                    "options": ["Blue", "Red", "Green"],
                    "allowMultiple": True,
                }
            ],
        }
        answer = _collect_user_input(event)
        self.assertEqual(answer["value"]["answers"], [{"selected": ["Blue", "Red"]}])

    @patch("questionary.text")
    @patch("questionary.select")
    def test_other_choice_falls_through_to_freeform(
        self, mock_select: MagicMock, mock_text: MagicMock
    ) -> None:
        """Choosing "Other" prompts for text and records it as freeform."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Other (type an answer)"
        mock_text.return_value.ask.return_value = "typed text"
        event = {
            "inputKind": "question",
            "questions": [{"question": "Favourite colour?", "options": ["Blue"]}],
        }
        answer = _collect_user_input(event)
        self.assertEqual(answer["value"]["answers"], [{"selected": [], "freeform": "typed text"}])

    @patch("questionary.select")
    def test_freeform_disabled_hides_other_choice(self, mock_select: MagicMock) -> None:
        """allowFreeform=False offers only the server's options."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Blue"
        event = {
            "inputKind": "question",
            "questions": [
                {"question": "Favourite colour?", "options": ["Blue", "Red"], "allowFreeform": False}
            ],
        }
        _collect_user_input(event)
        self.assertEqual(mock_select.call_args.kwargs["choices"], ["Blue", "Red"])

    @patch("questionary.text")
    def test_question_without_options_prompts_for_text(self, mock_text: MagicMock) -> None:
        """An option-less question is answered entirely as freeform."""
        from poly.cli_commands.wren import _collect_user_input

        mock_text.return_value.ask.return_value = "Because I like it"
        event = {"inputKind": "question", "questions": [{"question": "Why?"}]}
        answer = _collect_user_input(event)
        self.assertEqual(
            answer["value"]["answers"], [{"selected": [], "freeform": "Because I like it"}]
        )

    @patch("questionary.select")
    def test_cancelled_question_returns_none(self, mock_select: MagicMock) -> None:
        """Ctrl-C at the prompt (ask() -> None) leaves the gate unanswered."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = None
        event = {
            "inputKind": "question",
            "questions": [{"question": "Favourite colour?", "options": ["Blue"]}],
        }
        self.assertIsNone(_collect_user_input(event))

    @patch("questionary.select")
    def test_plan_approved(self, mock_select: MagicMock) -> None:
        """Approving a plan yields approved=True."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Approve"
        answer = _collect_user_input({"inputKind": "plan", "title": "Plan", "content": "# Steps"})
        self.assertEqual(answer, {"inputKind": "plan", "value": {"approved": True}})

    @patch("questionary.text")
    @patch("questionary.select")
    def test_plan_feedback(self, mock_select: MagicMock, mock_text: MagicMock) -> None:
        """Giving feedback yields approved=False plus the feedback text."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Give feedback"
        mock_text.return_value.ask.return_value = "Add error handling"
        answer = _collect_user_input({"inputKind": "plan", "content": "# Steps"})
        self.assertEqual(
            answer,
            {"inputKind": "plan", "value": {"approved": False, "feedback": "Add error handling"}},
        )

    @patch("questionary.select")
    def test_plan_cancelled_returns_none(self, mock_select: MagicMock) -> None:
        """Cancelling a plan gate leaves the run paused."""
        from poly.cli_commands.wren import _collect_user_input

        mock_select.return_value.ask.return_value = "Cancel"
        self.assertIsNone(_collect_user_input({"inputKind": "plan", "content": "# Steps"}))

    def test_secret_gate_is_declined(self) -> None:
        """Secret creation can't be done from the CLI, so it's declined."""
        from poly.cli_commands.wren import _collect_user_input

        self.assertEqual(
            _collect_user_input({"inputKind": "secret", "name": "API_KEY"}),
            {"inputKind": "secret", "value": {"created": False, "reason": "cancelled"}},
        )

    def test_edit_secret_gate_is_declined(self) -> None:
        """Editing a secret declines with updated=False."""
        from poly.cli_commands.wren import _collect_user_input

        self.assertEqual(
            _collect_user_input({"inputKind": "edit-secret"}),
            {"inputKind": "edit-secret", "value": {"updated": False, "reason": "cancelled"}},
        )

    def test_delete_secret_gate_is_declined(self) -> None:
        """Deleting a secret declines with deleted=False."""
        from poly.cli_commands.wren import _collect_user_input

        self.assertEqual(
            _collect_user_input({"inputKind": "delete-secret"}),
            {"inputKind": "delete-secret", "value": {"deleted": False, "reason": "cancelled"}},
        )

    def test_unknown_kind_returns_none(self) -> None:
        """An unrecognised gate kind can't be answered."""
        from poly.cli_commands.wren import _collect_user_input

        self.assertIsNone(_collect_user_input({"inputKind": "some_future_gate"}))


class AnswerAsPromptTests(unittest.TestCase):
    """Tests for _answer_as_prompt, the prose fallback for typed answers."""

    def test_plan_approval_becomes_go_ahead(self) -> None:
        """An approved plan flattens to a plain go-ahead."""
        from poly.cli_commands.wren import _answer_as_prompt

        answer = {"inputKind": "plan", "value": {"approved": True}}
        self.assertEqual(_answer_as_prompt({}, answer), "Approved, go ahead.")

    def test_plan_feedback_becomes_the_feedback_text(self) -> None:
        """Plan feedback is sent verbatim as the prompt."""
        from poly.cli_commands.wren import _answer_as_prompt

        answer = {"inputKind": "plan", "value": {"approved": False, "feedback": "Use webhooks"}}
        self.assertEqual(_answer_as_prompt({}, answer), "Use webhooks")

    def test_plan_rejection_without_feedback_is_none(self) -> None:
        """A rejection with no feedback has no prose to send."""
        from poly.cli_commands.wren import _answer_as_prompt

        self.assertIsNone(_answer_as_prompt({}, {"inputKind": "plan", "value": {"approved": False}}))

    def test_questions_become_question_answer_lines(self) -> None:
        """Each question pairs with its answer as one "Q: A" line."""
        from poly.cli_commands.wren import _answer_as_prompt

        event = {"questions": [{"question": "Colour?"}, {"question": "Sizes?"}]}
        answer = {
            "inputKind": "question",
            "value": {
                "answers": [
                    {"selected": [], "freeform": "Blue"},
                    {"selected": ["S", "M"]},
                ]
            },
        }
        self.assertEqual(_answer_as_prompt(event, answer), "Colour?: Blue\nSizes?: S, M")

    def test_empty_answers_return_none(self) -> None:
        """Nothing selected and nothing typed means no prompt to send."""
        from poly.cli_commands.wren import _answer_as_prompt

        event = {"questions": [{"question": "Colour?"}]}
        answer = {"inputKind": "question", "value": {"answers": [{"selected": [], "freeform": ""}]}}
        self.assertIsNone(_answer_as_prompt(event, answer))

    def test_unknown_kind_returns_none(self) -> None:
        """An unrecognised answer kind has no prose form."""
        from poly.cli_commands.wren import _answer_as_prompt

        self.assertIsNone(_answer_as_prompt({}, {"inputKind": "secret", "value": {}}))


class StreamTurnRoutingTests(unittest.TestCase):
    """Tests for how _stream_turn chooses between prompt and input_response."""

    @patch("poly.cli_commands.wren.stream_wren_input_response")
    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_mode_reaches_the_prompt_context(
        self, mock_turn: MagicMock, mock_input_response: MagicMock
    ) -> None:
        """The mode kwarg is pinned into the context sent with a prompt."""
        mock_turn.return_value = iter([{"type": "complete", "totalSteps": 1, "usageByAgent": {}}])
        _stream_turn(_make_project(), "key", "hi", None, json_mode=True, mode="interactive")
        mock_input_response.assert_not_called()
        self.assertEqual(mock_turn.call_args.kwargs["context"]["mode"], "interactive")

    @patch("poly.cli_commands.wren.stream_wren_input_response")
    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_agent_name_forwarded(
        self, mock_turn: MagicMock, mock_input_response: MagicMock
    ) -> None:
        """An agent_name override is forwarded to the SSE client."""
        mock_turn.return_value = iter([{"type": "complete", "totalSteps": 1, "usageByAgent": {}}])
        _stream_turn(_make_project(), "key", "hi", None, json_mode=True, agent_name="planner")
        self.assertEqual(mock_turn.call_args.kwargs["agent_name"], "planner")

    @patch("poly.cli_commands.wren.stream_wren_input_response")
    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_input_response_resumes_paused_run(
        self, mock_turn: MagicMock, mock_input_response: MagicMock
    ) -> None:
        """With a session and a pending answer, the run resumes over input_response."""
        mock_input_response.return_value = iter(
            [{"type": "complete", "totalSteps": 1, "usageByAgent": {}}]
        )
        answer = {"inputKind": "plan", "value": {"approved": True}}
        _stream_turn(
            _make_project(),
            "key",
            "",
            "sess-1",
            json_mode=True,
            mode="interactive",
            input_response=("req-1", answer),
        )
        mock_turn.assert_not_called()
        kwargs = mock_input_response.call_args.kwargs
        self.assertEqual(kwargs["request_id"], "req-1")
        self.assertEqual(kwargs["answer"], answer)
        self.assertEqual(kwargs["session_id"], "sess-1")
        # The resumed run keeps the mode it was started with, so none is sent.
        self.assertNotIn("mode", kwargs["context"])

    @patch("poly.cli_commands.wren.stream_wren_input_response")
    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_input_response_without_session_falls_back_to_prompt(
        self, mock_turn: MagicMock, mock_input_response: MagicMock
    ) -> None:
        """Without a session ID there's no run to resume, so a prompt is sent."""
        mock_turn.return_value = iter([{"type": "complete", "totalSteps": 1, "usageByAgent": {}}])
        _stream_turn(
            _make_project(),
            "key",
            "Approved, go ahead.",
            None,
            json_mode=True,
            input_response=("req-1", {"inputKind": "plan", "value": {"approved": True}}),
        )
        mock_input_response.assert_not_called()
        self.assertEqual(mock_turn.call_args.kwargs["prompt"], "Approved, go ahead.")


class ErrorCodeMappingTests(unittest.TestCase):
    """Tests that newly added server error codes are recorded on the result."""

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_invalid_request_recorded(self, mock_stream: MagicMock) -> None:
        """An invalid_request error is surfaced without being fatal."""
        mock_stream.return_value = iter(
            [{"type": "error", "errorCode": "invalid_request", "message": "bad body"}]
        )
        result = _stream_turn(_make_project(), "key", "hi", None, json_mode=True)
        self.assertEqual(result.error["code"], "invalid_request")
        self.assertFalse(result.fatal)

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_conversation_not_found_recorded(self, mock_stream: MagicMock) -> None:
        """A stale --session-id surfaces as conversation_not_found."""
        mock_stream.return_value = iter(
            [{"type": "error", "errorCode": "conversation_not_found", "message": "gone"}]
        )
        result = _stream_turn(_make_project(), "key", "hi", None, json_mode=True)
        self.assertEqual(result.error["code"], "conversation_not_found")

    @patch("poly.cli_commands.wren.stream_wren_turn")
    def test_stream_interrupted_recorded(self, mock_stream: MagicMock) -> None:
        """A dropped model stream is retryable, not fatal."""
        mock_stream.return_value = iter(
            [{"type": "error", "errorCode": "llm_stream_interrupted", "message": "dropped"}]
        )
        result = _stream_turn(_make_project(), "key", "hi", None, json_mode=True, first_turn=True)
        self.assertEqual(result.error["code"], "llm_stream_interrupted")
        self.assertFalse(result.fatal)

    def test_new_codes_all_have_friendly_messages(self) -> None:
        """Every newly added code maps to a human-readable message."""
        from poly.cli_commands.wren import _ERROR_MESSAGES

        for code in (
            "llm_stream_interrupted",
            "llm_invalid_request",
            "file_resolution_failed",
            "usage_tracking_failed",
            "conversation_not_found",
            "invalid_request",
            "internal",
        ):
            with self.subTest(code=code):
                self.assertTrue(_ERROR_MESSAGES.get(code))


if __name__ == "__main__":
    unittest.main()
