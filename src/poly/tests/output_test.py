"""Tests for the --output flag feature (json_print, commands_to_dicts, and CLI integration).

Copyright PolyAI Limited
"""

import io
import json
import unittest
from unittest.mock import patch

from google.protobuf.json_format import MessageToDict

from poly.cli import AgentStudioCLI
from poly.handlers.protobuf.commands_pb2 import Command
from poly.output import commands_to_dicts, json_print


class JsonPrintTests(unittest.TestCase):
    """Tests for the json_print helper."""

    def test_json_print_writes_valid_json_to_stdout(self):
        """json_print should write indented JSON followed by a newline."""
        data = {"key": "value", "count": 42}
        buf = io.StringIO()

        with patch("poly.output.sys.stdout", buf):
            json_print(data)

        output = buf.getvalue()
        parsed = json.loads(output)
        self.assertEqual(parsed, {"key": "value", "count": 42})

    def test_json_print_uses_indent_2(self):
        """Output should be pretty-printed with 2-space indent."""
        data = {"a": 1}
        buf = io.StringIO()

        with patch("poly.output.sys.stdout", buf):
            json_print(data)

        # The second line should start with exactly 2 spaces for the key
        lines = buf.getvalue().splitlines()
        self.assertTrue(lines[1].startswith("  "))

    def test_json_print_ends_with_newline(self):
        """Output should end with a trailing newline character."""
        buf = io.StringIO()

        with patch("poly.output.sys.stdout", buf):
            json_print({"x": 1})

        self.assertTrue(buf.getvalue().endswith("\n"))

    def test_json_print_handles_nested_data(self):
        """json_print should handle nested dicts and lists."""
        data = {"files": [{"path": "a.yaml", "diff": "+line"}]}
        buf = io.StringIO()

        with patch("poly.output.sys.stdout", buf):
            json_print(data)

        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["files"][0]["path"], "a.yaml")

    def test_json_print_uses_str_as_default_serializer(self):
        """Non-serializable values should be converted via str()."""
        from datetime import datetime

        data = {"ts": datetime(2026, 1, 1, 12, 0, 0)}
        buf = io.StringIO()

        with patch("poly.output.sys.stdout", buf):
            json_print(data)

        parsed = json.loads(buf.getvalue())
        self.assertEqual(parsed["ts"], "2026-01-01 12:00:00")


class CommandsToDictsTests(unittest.TestCase):
    """Tests for the commands_to_dicts helper."""

    def test_empty_input_returns_empty_list(self):
        """An empty command list should produce an empty output list."""
        result = commands_to_dicts([])
        self.assertEqual(result, [])

    def test_converts_single_command_to_dict(self):
        """A single Command protobuf should be converted to a dict."""
        cmd = Command()
        cmd.type = "create_topic"
        cmd.command_id = "cmd-001"

        result = commands_to_dicts([cmd])

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["type"], "create_topic")
        self.assertEqual(result[0]["command_id"], "cmd-001")

    def test_preserves_proto_field_names(self):
        """Field names should use snake_case (preserving_proto_field_name=True)."""
        cmd = Command()
        cmd.command_id = "test-id"

        result = commands_to_dicts([cmd])

        # With preserving_proto_field_name=True, we get "command_id" not "commandId"
        self.assertIn("command_id", result[0])
        self.assertNotIn("commandId", result[0])

    def test_converts_multiple_commands(self):
        """Multiple Command protobufs should each be converted."""
        cmd1 = Command()
        cmd1.type = "create_topic"
        cmd2 = Command()
        cmd2.type = "delete_topic"

        result = commands_to_dicts([cmd1, cmd2])

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "create_topic")
        self.assertEqual(result[1]["type"], "delete_topic")

    def test_result_matches_direct_message_to_dict(self):
        """Each dict should match calling MessageToDict directly on the command."""
        cmd = Command()
        cmd.type = "update_function"
        cmd.command_id = "abc"

        result = commands_to_dicts([cmd])
        expected = MessageToDict(cmd, preserving_proto_field_name=True)

        self.assertEqual(result[0], expected)


class StatusOutputJsonTests(unittest.TestCase):
    """Tests for poly status with --output json."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_status_json_returns_valid_json_with_expected_keys(self, mock_load):
        """status(output='json') should print JSON with branch, conflicts, new, modified, deleted."""
        project = mock_load.return_value
        project.root_path = "/fake/project"
        project.project_status.return_value = (
            ["/fake/project/conflicts/a.yaml"],
            ["/fake/project/functions/modified.py"],
            ["/fake/project/flows/new_flow/config.yaml"],
            ["/fake/project/topics/deleted.yaml"],
        )
        project.get_current_branch.return_value = "feature-branch"

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.status("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertEqual(output["branch"], "feature-branch")
        self.assertEqual(output["conflicts"], ["conflicts/a.yaml"])
        self.assertEqual(output["new"], ["flows/new_flow/config.yaml"])
        self.assertEqual(output["modified"], ["functions/modified.py"])
        self.assertEqual(output["deleted"], ["topics/deleted.yaml"])

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_status_json_empty_changes_returns_empty_lists(self, mock_load):
        """status(output='json') with no changes should return empty lists."""
        project = mock_load.return_value
        project.root_path = "/fake/project"
        project.project_status.return_value = ([], [], [], [])
        project.get_current_branch.return_value = "main"

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.status("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertEqual(output["conflicts"], [])
        self.assertEqual(output["new"], [])
        self.assertEqual(output["modified"], [])
        self.assertEqual(output["deleted"], [])

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_status_json_branch_is_none_when_not_on_branch(self, mock_load):
        """status(output='json') should include null branch when not on a branch."""
        project = mock_load.return_value
        project.root_path = "/fake/project"
        project.project_status.return_value = ([], [], [], [])
        project.get_current_branch.return_value = None

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.status("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertIsNone(output["branch"])


class StatusOutputCommandsTests(unittest.TestCase):
    """Tests for poly status with --output commands."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_status_commands_outputs_commands_key(self, mock_load):
        """status(output='commands') should print JSON with a 'commands' key."""
        project = mock_load.return_value
        cmd = Command()
        cmd.type = "create_topic"
        project.generate_push_commands.return_value = [cmd]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.status("/fake/project", output="commands")

        output = json.loads(buf.getvalue())
        self.assertIn("commands", output)
        self.assertEqual(len(output["commands"]), 1)
        self.assertEqual(output["commands"][0]["type"], "create_topic")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_status_commands_empty_when_no_changes(self, mock_load):
        """status(output='commands') with no changes should return empty commands list."""
        project = mock_load.return_value
        project.generate_push_commands.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.status("/fake/project", output="commands")

        output = json.loads(buf.getvalue())
        self.assertEqual(output["commands"], [])


class DiffOutputJsonTests(unittest.TestCase):
    """Tests for poly diff with --output json."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    @patch("poly.cli.AgentStudioCLI._diff")
    def test_diff_json_returns_files_array(self, mock_diff, mock_load):
        """diff(output='json') should print JSON with a 'files' array containing path and diff."""
        project = mock_load.return_value
        project.root_path = "/fake/project"
        mock_diff.return_value = {
            "/fake/project/topics/greeting.yaml": "- old\n+ new",
            "/fake/project/functions/helper.py": "- removed\n+ added",
        }

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.diff("/fake/project", files=[], output="json")

        output = json.loads(buf.getvalue())
        self.assertIn("files", output)
        self.assertEqual(len(output["files"]), 2)

        paths = [f["path"] for f in output["files"]]
        self.assertIn("topics/greeting.yaml", paths)
        self.assertIn("functions/helper.py", paths)

        # Verify diff content is included
        for f in output["files"]:
            self.assertIn("diff", f)
            self.assertTrue(len(f["diff"]) > 0)

    @patch("poly.cli.AgentStudioCLI._load_project")
    @patch("poly.cli.AgentStudioCLI._diff")
    def test_diff_json_empty_diffs_returns_empty_files(self, mock_diff, mock_load):
        """diff(output='json') with no changes should return empty files array."""
        project = mock_load.return_value
        project.root_path = "/fake/project"
        mock_diff.return_value = None  # _diff returns None when no changes

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.diff("/fake/project", files=[], output="json")

        output = json.loads(buf.getvalue())
        self.assertEqual(output["files"], [])


class DiffOutputCommandsTests(unittest.TestCase):
    """Tests for poly diff with --output commands."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_diff_commands_outputs_commands_key(self, mock_load):
        """diff(output='commands') should print JSON with a 'commands' key."""
        project = mock_load.return_value
        cmd = Command()
        cmd.type = "update_function"
        project.generate_push_commands.return_value = [cmd]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.diff("/fake/project", files=[], output="commands")

        output = json.loads(buf.getvalue())
        self.assertIn("commands", output)
        self.assertEqual(output["commands"][0]["type"], "update_function")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_diff_commands_does_not_call_diff(self, mock_load):
        """diff(output='commands') should skip _diff entirely and use generate_push_commands."""
        project = mock_load.return_value
        project.generate_push_commands.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.diff("/fake/project", files=[], output="commands")

        project.generate_push_commands.assert_called_once_with(skip_validation=True)
        project.get_diffs.assert_not_called()


class ValidateOutputJsonTests(unittest.TestCase):
    """Tests for poly validate with --output json."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_json_valid_project(self, mock_load):
        """validate(output='json') on valid project should return valid=true, errors=[]."""
        project = mock_load.return_value
        project.validate_project.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.validate_project("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertTrue(output["valid"])
        self.assertEqual(output["errors"], [])

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_json_invalid_project_exits_1(self, mock_load, mock_exit):
        """validate(output='json') on invalid project should exit with code 1."""
        project = mock_load.return_value
        project.validate_project.return_value = [
            "Validation error in flows/main/config.yaml: Missing required field 'name'"
        ]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.validate_project("/fake/project", output="json")

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_json_invalid_project_returns_errors(self, mock_load, mock_exit):
        """validate(output='json') on invalid project should include parsed error details."""
        project = mock_load.return_value
        project.validate_project.return_value = [
            "Validation error in flows/main/config.yaml: Missing required field 'name'",
            "Some other error without file path",
        ]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.validate_project("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertFalse(output["valid"])
        self.assertEqual(len(output["errors"]), 2)

        # First error has a parsed file path
        self.assertEqual(output["errors"][0]["file"], "flows/main/config.yaml")
        self.assertIn("Missing required field", output["errors"][0]["message"])

        # Second error has no file path
        self.assertIsNone(output["errors"][1]["file"])
        self.assertEqual(output["errors"][1]["message"], "Some other error without file path")


class ValidateOutputCommandsTests(unittest.TestCase):
    """Tests for poly validate with --output commands."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_commands_outputs_commands_key(self, mock_load):
        """validate(output='commands') should print JSON with a 'commands' key."""
        project = mock_load.return_value
        cmd = Command()
        cmd.type = "create_flow"
        project.generate_push_commands.return_value = [cmd]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.validate_project("/fake/project", output="commands")

        output = json.loads(buf.getvalue())
        self.assertIn("commands", output)
        self.assertEqual(output["commands"][0]["type"], "create_flow")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_commands_skips_validation(self, mock_load):
        """validate(output='commands') should call generate_push_commands with skip_validation=True."""
        project = mock_load.return_value
        project.generate_push_commands.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.validate_project("/fake/project", output="commands")

        project.generate_push_commands.assert_called_once_with(skip_validation=True)
        # validate_project() should NOT be called when output is "commands"
        project.validate_project.assert_not_called()

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_validate_commands_does_not_exit_on_empty(self, mock_load):
        """validate(output='commands') with no commands should not call sys.exit."""
        project = mock_load.return_value
        project.generate_push_commands.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf), patch("poly.cli.sys.exit") as mock_exit:
            AgentStudioCLI.validate_project("/fake/project", output="commands")

        mock_exit.assert_not_called()


class PushOutputJsonTests(unittest.TestCase):
    """Tests for poly push with --output json."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_push_json_success(self, mock_load):
        """push(output='json') on success should emit JSON with success=true."""
        project = mock_load.return_value
        project.push_project.return_value = (True, "Resources pushed successfully.")

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.push("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertTrue(output["success"])
        self.assertEqual(output["message"], "Resources pushed successfully.")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_push_json_failure_exits(self, mock_load):
        """push(output='json') on failure should emit JSON with success=false and exit 1."""
        project = mock_load.return_value
        project.push_project.return_value = (False, "Validation errors detected")

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf), patch("poly.cli.sys.exit") as mock_exit:
            AgentStudioCLI.push("/fake/project", output="json")

        output = json.loads(buf.getvalue())
        self.assertFalse(output["success"])
        mock_exit.assert_called_once_with(1)


class PushOutputCommandsTests(unittest.TestCase):
    """Tests for poly push with --output commands."""

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_push_commands_outputs_commands_key(self, mock_load):
        """push(output='commands') should print JSON with a 'commands' key."""
        project = mock_load.return_value
        cmd = Command()
        cmd.type = "create_topic"
        project.generate_push_commands.return_value = [cmd]

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.push("/fake/project", output="commands")

        output = json.loads(buf.getvalue())
        self.assertIn("commands", output)
        self.assertEqual(output["commands"][0]["type"], "create_topic")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_push_commands_does_not_actually_push(self, mock_load):
        """push(output='commands') should not call push_project."""
        project = mock_load.return_value
        project.generate_push_commands.return_value = []

        buf = io.StringIO()
        with patch("poly.output.sys.stdout", buf):
            AgentStudioCLI.push("/fake/project", output="commands")

        project.push_project.assert_not_called()
