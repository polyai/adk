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


if __name__ == "__main__":
    unittest.main()
