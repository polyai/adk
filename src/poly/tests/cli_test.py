"""Tests for the poly/las CLI.

Copyright PolyAI Limited
"""

import os
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from poly.cli import AgentStudioCLI
from poly.tests.project_test import TEST_DIR


def _run_result(returncode: int, stdout: str = "", stderr: str = ""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


class FormatCommandTest(unittest.TestCase):
    """Tests for the format command (uses project.format_files and resources)."""

    CLI_COMMANDS = {
        "test_format_check_calls_project_format_files": "poly format --check --path <project>",
        "test_format_with_fix_calls_project_format_files": "poly format --path <project>",
        "test_format_with_files_passes_targets_to_project": (
            "poly format --check --path <project> functions/test_function.py config/entities.yaml"
        ),
        "test_format_check_exits_when_files_would_change": "poly format --check --path <project>",
        "test_format_check_exits_when_format_errors": "poly format --check --path <project>",
        "test_format_check_exits_when_ty_check_fails": "poly format --check --ty --path <project>",
        "test_format_with_fix_exits_when_format_errors": "poly format --path <project>",
        "test_format_fix_succeeds_and_reports_fixed_files": "poly format --path <project>",
        "test_format_identifies_issue_fixes_it_and_shows_summary": "poly format --path <project>",
    }

    def setUp(self):
        cmd = self.CLI_COMMANDS.get(self._testMethodName, "")
        print("\n" + "─" * 60 + f"\n  {self._testMethodName}\n  $ {cmd}\n" + "─" * 60)

    def tearDown(self):
        print("─" * 60 + "\n")

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_check_calls_project_format_files(self, mock_load):
        """format --check calls project.format_files with check_only=True."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        AgentStudioCLI.format(TEST_DIR, [], check_only=True)

        proj.format_files.assert_called_once()
        call_kw = proj.format_files.call_args[1]
        self.assertTrue(call_kw["check_only"])
        self.assertIsNone(call_kw["files"])

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_with_fix_calls_project_format_files(self, mock_load):
        """format without --check calls project.format_files with check_only=False."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        AgentStudioCLI.format(TEST_DIR, [], check_only=False)

        proj.format_files.assert_called_once()
        call_kw = proj.format_files.call_args[1]
        self.assertFalse(call_kw["check_only"])

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_with_files_passes_targets_to_project(self, mock_load):
        """format with file list passes resolved absolute paths to format_files."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        AgentStudioCLI.format(
            TEST_DIR,
            ["functions/test_function.py", "config/entities.yaml"],
            check_only=True,
        )

        proj.format_files.assert_called_once()
        files_arg = proj.format_files.call_args[1]["files"]
        self.assertIsNotNone(files_arg)
        self.assertEqual(len(files_arg), 2)
        self.assertIn("test_function.py", files_arg[0])
        self.assertIn("entities.yaml", files_arg[1])
        self.assertTrue(os.path.isabs(files_arg[0]))

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_check_exits_when_files_would_change(self, mock_load, mock_exit):
        """When check_only and format_files returns would-change paths, format exits with 1."""
        proj = mock_load.return_value
        some_path = os.path.join(TEST_DIR, "functions", "test_function.py")
        proj.format_files.return_value = ([some_path], [])

        AgentStudioCLI.format(TEST_DIR, [], check_only=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_check_exits_when_format_errors(self, mock_load, mock_exit):
        """When format_files returns errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], ["path/to/file: something failed"])

        AgentStudioCLI.format(TEST_DIR, [], check_only=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.subprocess.run")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_check_exits_when_ty_check_fails(self, mock_load, mock_run, mock_exit):
        """When ty check reports type errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="type error")

        AgentStudioCLI.format(TEST_DIR, [], check_only=True, run_ty=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli.sys.exit")
    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_with_fix_exits_when_format_errors(self, mock_load, mock_exit):
        """When format (fix mode) returns errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], ["syntax error in file"])

        AgentStudioCLI.format(TEST_DIR, [], check_only=False)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_fix_succeeds_and_reports_fixed_files(self, mock_load):
        """poly format (fix mode) reports formatted paths and success."""
        proj = mock_load.return_value
        formatted_path = os.path.join(TEST_DIR, "config", "entities.yaml")
        proj.format_files.return_value = ([formatted_path], [])

        AgentStudioCLI.format(TEST_DIR, [], check_only=False)

        proj.format_files.assert_called_once_with(files=None, check_only=False)

    @patch("poly.cli.AgentStudioCLI._load_project")
    def test_format_identifies_issue_fixes_it_and_shows_summary(self, mock_load):
        """Format (fix mode) with affected files shows summary."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([os.path.join(TEST_DIR, "functions", "f.py")], [])

        AgentStudioCLI.format(TEST_DIR, [], check_only=False)

        proj.format_files.assert_called_once_with(files=None, check_only=False)


class CompletionCommandTest(unittest.TestCase):
    """Tests for the completion command."""

    def test_completion_bash_outputs_script(self):
        """poly completion bash prints a non-empty bash completion script."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            AgentStudioCLI.print_completion("bash")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_zsh_outputs_script(self):
        """poly completion zsh prints a non-empty zsh completion script."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            AgentStudioCLI.print_completion("zsh")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_fish_outputs_script(self):
        """poly completion fish prints a non-empty fish completion script."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            AgentStudioCLI.print_completion("fish")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_bash_references_poly(self):
        """bash completion script references the poly command."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            AgentStudioCLI.print_completion("bash")
            output = mock_out.getvalue()
        self.assertIn("poly", output)

    def test_completion_invalid_shell_rejected_by_parser(self):
        """Parser rejects shell choices outside bash/zsh/fish."""
        with self.assertRaises(SystemExit):
            AgentStudioCLI.main(sys_args=["completion", "powershell"])
