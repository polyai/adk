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


class BranchCreateFromEnvTest(unittest.TestCase):
    """Tests for branch_create with --env flag.

    Test cases for the AgentStudioCLI.branch_create method when using the --env flag.

    These tests confirm correct behavior creating a branch from a specified environment:
    - Blocks creation if there are uncommitted local changes (unless --force is used).
    - Proceeds with creation if --force is specified, bypassing local changes check.
    - Pulls resources from the specified environment and creates a branch as expected.

    Additionally handles cases such as:
    - No resources are returned from the environment.
    - Skips pulling from the environment if the environment is "sandbox" or not specified.
    - Does not skip environment pull when a supported environment (e.g., "live") is specified.
    - Does not push changes if branch creation fails.

    """

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.branch_id = "main"
        self.proj.account_id = "test_account"
        self.proj.project_id = "test_project"
        self.proj.get_diffs.return_value = {}
        self.proj.pull_project_from_env = MagicMock()
        self.proj.push_project = MagicMock(return_value=(True, "Push successful", []))
        self.proj.create_branch.return_value = "new-branch-id"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_branch_create_env_blocks_on_local_changes_without_force(self):
        """branch create --env live raises ValueError if local changes exist."""
        self.proj.get_diffs.return_value = {"file.py": " diff"}

        with self.assertRaises(ValueError) as ctx:
            AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertIn("Uncommitted changes", str(ctx.exception))
        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_not_called()
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_force_bypasses_check(self):
        """branch create --env live --force proceeds despite local changes."""
        self.proj.get_diffs.return_value = {"file.py": "example diff"}

        AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="live", force=True)

        self.proj.pull_project_from_env.assert_called_once()
        call_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(call_kwargs["env"], "live")
        self.assertIs(call_kwargs["format"], False)
        self.proj.create_branch.assert_called_once_with("my-branch")
        self.proj.push_project.assert_called_once_with(
            force=True,
            skip_validation=True,
            dry_run=False,
            format=False,
            email=None,
        )

    def test_branch_create_env_pulls_from_specified_env(self):
        """branch create --env pre-release pulls resources from pre-release."""
        self.proj.get_diffs.return_value = {}

        AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="pre-release", force=False)

        self.proj.pull_project_from_env.assert_called_once()
        call_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(call_kwargs["env"], "pre-release")
        self.assertIs(call_kwargs["format"], False)
        self.proj.create_branch.assert_called_once_with("my-branch")
        self.proj.push_project.assert_called_once_with(
            force=True,
            skip_validation=True,
            dry_run=False,
            format=False,
            email=None,
        )

    def test_branch_create_env_raises_when_live_deployment_missing(self):
        """If live (or pre-release) has no active deployment, pull_project_from_env raises."""
        self.proj.get_diffs.return_value = {}
        self.proj.pull_project_from_env.side_effect = ValueError(
            "No resources returned from environment 'live'."
        )

        with self.assertRaises(ValueError) as ctx:
            AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertIn("No resources returned from environment 'live'", str(ctx.exception))
        self.proj.pull_project_from_env.assert_called_once()
        pull_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(pull_kwargs["env"], "live")
        self.assertIs(pull_kwargs["format"], False)
        self.proj.create_branch.assert_not_called()
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_sandbox_skips_env_pull(self):
        """branch create --env sandbox behaves like normal branch create (no env pull)."""
        AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="sandbox", force=False)

        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_called_once_with("my-branch")
        self.proj.push_project.assert_not_called()

    def test_branch_create_blocked_when_not_on_main(self):
        """branch create from non-main branch exits with an error."""
        self.proj.branch_id = "example-feature-branch"

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_not_called()
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_none_behaves_like_normal(self):
        """branch create with env=None skips env pull (default behavior)."""
        AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env=None, force=False)

        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_called_once_with("my-branch")
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_does_not_push_when_create_branch_fails(self):
        """After failed branch creation, push_project is not called and process exits."""
        self.proj.get_diffs.return_value = {}
        self.proj.create_branch.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.pull_project_from_env.assert_called_once()
        self.assertIs(self.proj.pull_project_from_env.call_args[1]["format"], False)
        self.proj.create_branch.assert_called_once_with("my-branch")
        self.proj.push_project.assert_not_called()


class BranchDeleteTest(unittest.TestCase):
    """Tests for AgentStudioCLI.branch_delete interactive and direct deletion flow."""

    SAMPLE_BRANCHES = {"main": "main-id", "feature-a": "branch-a-id", "feature-b": "branch-b-id"}

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_branches.return_value = ("main", dict(self.SAMPLE_BRANCHES))
        self.proj.delete_branch.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    # -- Direct deletion (branch_name provided) --

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    def test_direct_delete_existing_branch_shows_success(self, mock_success, mock_q):
        """Deleting an existing branch by name prints a success message."""
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="feature-a")

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_success.assert_called_once()
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("poly.cli.json_print")
    def test_direct_delete_existing_branch_json_mode(self, mock_json):
        """Deleting a branch with output_json=True prints JSON with success=True."""
        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="feature-a", output_json=True)

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_json.assert_called_once_with({"success": True})

    @patch("poly.cli.error")
    def test_direct_delete_nonexistent_branch_shows_error(self, mock_error):
        """Attempting to delete a branch that doesn't exist shows an error."""
        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="no-such-branch")

        self.proj.delete_branch.assert_not_called()
        mock_error.assert_called_once()
        self.assertIn("does not exist", mock_error.call_args[0][0])

    @patch("poly.cli.json_print")
    def test_direct_delete_nonexistent_branch_json_mode(self, mock_json):
        """Non-existent branch with output_json=True prints JSON with success=False."""
        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="no-such-branch", output_json=True)

        self.proj.delete_branch.assert_not_called()
        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("does not exist", payload["message"])

    @patch("poly.cli.error")
    def test_direct_delete_main_branch_shows_error(self, mock_error):
        """Attempting to delete 'main' shows an error because main is not deletable."""
        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="main")

        self.proj.delete_branch.assert_not_called()
        mock_error.assert_called_once()
        self.assertIn("does not exist or cannot be deleted", mock_error.call_args[0][0])

    @patch("poly.cli.questionary")
    @patch("poly.cli.error")
    def test_direct_delete_when_project_raises_shows_error(self, mock_error, mock_q):
        """If project.delete_branch raises, the error is shown to the user."""
        mock_q.confirm.return_value.ask.return_value = True
        self.proj.delete_branch.side_effect = ValueError("API failure")

        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="feature-a")

        mock_error.assert_called_once()
        self.assertIn("API failure", mock_error.call_args[0][0])

    @patch("poly.cli.json_print")
    def test_direct_delete_when_project_raises_json_mode(self, mock_json):
        """If project.delete_branch raises in JSON mode, error is printed as JSON."""
        self.proj.delete_branch.side_effect = ValueError("API failure")

        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="feature-a", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("API failure", payload["message"])

    @patch("poly.cli.questionary")
    @patch("poly.cli.error")
    def test_direct_delete_returns_false_shows_failure(self, mock_error, mock_q):
        """If project.delete_branch returns False, a failure message is shown."""
        mock_q.confirm.return_value.ask.return_value = True
        self.proj.delete_branch.return_value = False

        AgentStudioCLI.branch_delete(TEST_DIR, branch_name="feature-a")

        mock_error.assert_called_once()
        self.assertIn("Failed to delete", mock_error.call_args[0][0])

    # -- Interactive mode (no branch_name) --

    @patch("poly.cli.plain")
    def test_interactive_no_deletable_branches_shows_message(self, mock_plain):
        """When only 'main' exists, a 'no deletable branches' message is shown."""
        self.proj.get_branches.return_value = ("main", {"main": "main-id"})

        AgentStudioCLI.branch_delete(TEST_DIR)

        mock_plain.assert_called_once()
        self.assertIn("[muted]No deletable branches found.[/muted]", mock_plain.call_args[0][0])
        self.proj.delete_branch.assert_not_called()

    @patch("poly.cli.questionary")
    @patch("poly.cli.warning")
    def test_interactive_user_selects_nothing_shows_warning(self, mock_warning, mock_q):
        """When user cancels the checkbox, a warning is shown and nothing is deleted."""
        mock_q.checkbox.return_value.ask.return_value = []

        AgentStudioCLI.branch_delete(TEST_DIR)

        mock_warning.assert_called_once()
        self.assertIn("No branches selected", mock_warning.call_args[0][0])
        self.proj.delete_branch.assert_not_called()

    @patch("poly.cli.questionary")
    @patch("poly.cli.warning")
    def test_interactive_user_returns_none_shows_warning(self, mock_warning, mock_q):
        """When questionary returns None (Ctrl+C), a warning is shown."""
        mock_q.checkbox.return_value.ask.return_value = None

        AgentStudioCLI.branch_delete(TEST_DIR)

        mock_warning.assert_called_once()
        self.proj.delete_branch.assert_not_called()

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    def test_interactive_single_branch_deleted(self, mock_success, mock_q):
        """Selecting one branch in the checkbox deletes it and reports success."""
        mock_q.checkbox.return_value.ask.return_value = ["feature-a"]
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR)

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_success.assert_called_once()
        self.assertIn("1 branch(es)", mock_success.call_args[0][0])

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    def test_interactive_multiple_branches_deleted(self, mock_success, mock_q):
        """Selecting multiple branches deletes each and reports total count."""
        mock_q.checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR)

        self.assertEqual(self.proj.delete_branch.call_count, 2)
        mock_success.assert_called_once()
        self.assertIn("2 branch(es)", mock_success.call_args[0][0])

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    def test_interactive_current_branch_label_stripped(self, mock_success, mock_q):
        """The ' (current)' suffix is stripped from labels before calling delete_branch."""
        self.proj.get_branches.return_value = ("feature-a", dict(self.SAMPLE_BRANCHES))
        mock_q.checkbox.return_value.ask.return_value = ["feature-a (current)"]
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR)

        self.proj.delete_branch.assert_called_once_with("feature-a")

    @patch("poly.cli.questionary")
    @patch("poly.cli.json_print")
    def test_interactive_json_mode_reports_deleted_count(self, mock_json, mock_q):
        """In JSON mode, interactive deletion prints success and deleted count."""
        mock_q.checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR, output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["deleted"], 2)

    @patch("poly.cli.questionary")
    @patch("poly.cli.error")
    @patch("poly.cli.success")
    def test_interactive_error_on_one_branch_continues_others(
        self, mock_success, mock_error, mock_q
    ):
        """If one branch fails to delete, others still proceed."""
        self.proj.delete_branch.side_effect = [ValueError("oops"), True]
        mock_q.checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_q.confirm.return_value.ask.return_value = True

        AgentStudioCLI.branch_delete(TEST_DIR)

        self.assertEqual(self.proj.delete_branch.call_count, 2)
        mock_error.assert_called_once()
        mock_success.assert_called_once()
        self.assertIn("1 branch(es)", mock_success.call_args[0][0])


class BranchMergeConflictHelpersTest(unittest.TestCase):
    """Branch merge conflict enrichment, resolution payload, and conflict table layout."""

    def test_branch_merge_conflict_file_key(self):
        from poly.cli import _branch_merge_conflict_file_key

        self.assertEqual(_branch_merge_conflict_file_key([]), "")
        self.assertEqual(_branch_merge_conflict_file_key(["a"]), "a")
        self.assertEqual(_branch_merge_conflict_file_key(["a", "b", "c"]), os.path.join("a", "b"))

    def test_enrich_branch_merge_conflicts_counts_and_merged_value(self):
        from poly.cli import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["kb", "t1", "f1"],
                "baseValue": "same",
                "theirsValue": "same",
                "oursValue": "same",
            },
            {
                "path": ["kb", "t1", "f2"],
                "baseValue": "x",
                "theirsValue": "y",
                "oursValue": "z",
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        fk = os.path.join("kb", "t1")
        self.assertEqual(out[0]["visual_path"], os.path.join("kb", "t1", "f1"))
        self.assertEqual(out[0]["file_key"], fk)
        self.assertEqual(out[0]["conflicts_in_resource"], 2)
        self.assertTrue(out[0]["can_auto_merge"])
        self.assertEqual(out[0]["merged_value"], "same")
        self.assertFalse(out[1]["can_auto_merge"])

    def test_enrich_skips_timestamp_paths_without_merge_metadata(self):
        from poly.cli import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["x", "updatedAt"],
                "baseValue": "",
                "theirsValue": "",
                "oursValue": "",
            }
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertNotIn("merged_value", out[0])

    def test_auto_merge_resolution_payload(self):
        from poly.cli import _auto_merge_resolution

        path = ["topics", "actions"]
        r = _auto_merge_resolution(path, "line1\nline2\n")
        self.assertEqual(r["path"], path)
        self.assertEqual(r["value"], "line1\nline2\n")
        self.assertEqual(r["strategy"], "theirs")

    @patch("poly.output.console.console.print")
    def test_output_merge_conflict_table_one_row_per_conflict_when_show_type(self, mock_print):
        from poly.output.console import output_merge_conflict_table
        from rich.panel import Panel
        from rich.table import Table

        conflicts = [
            {
                "visual_path": os.path.join("a", "b", "f1"),
                "can_auto_merge": True,
                "conflicts_in_resource": 2,
                "path": ["a", "b", "f1"],
            },
            {
                "visual_path": os.path.join("a", "b", "f2"),
                "can_auto_merge": False,
                "conflicts_in_resource": 2,
                "path": ["a", "b", "f2"],
            },
        ]
        output_merge_conflict_table(conflicts, show_type=True)
        rendered = mock_print.call_args_list[-1][0][0]
        table = rendered.renderable if isinstance(rendered, Panel) else rendered
        self.assertIsInstance(table, Table)
        self.assertEqual(len(table.rows), 2)

    @patch("poly.output.console.console.print")
    def test_output_merge_conflict_table_without_show_type_single_column(self, mock_print):
        from poly.output.console import output_merge_conflict_table
        from rich.panel import Panel

        conflicts = [{"visual_path": "p1", "path": ["p1"]}]
        output_merge_conflict_table(conflicts, show_type=False)
        rendered = mock_print.call_args_list[-1][0][0]
        table = rendered.renderable if isinstance(rendered, Panel) else rendered
        self.assertEqual(len(table.columns), 1)
        self.assertEqual(len(table.rows), 1)


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
