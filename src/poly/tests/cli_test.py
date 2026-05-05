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
        from rich.panel import Panel
        from rich.table import Table

        from poly.output.console import output_merge_conflict_table

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
        from rich.panel import Panel

        from poly.output.console import output_merge_conflict_table

        conflicts = [{"visual_path": "p1", "path": ["p1"]}]
        output_merge_conflict_table(conflicts, show_type=False)
        rendered = mock_print.call_args_list[-1][0][0]
        table = rendered.renderable if isinstance(rendered, Panel) else rendered
        self.assertEqual(len(table.columns), 1)
        self.assertEqual(len(table.rows), 1)
class ChatLoopTest(unittest.TestCase):
    """Tests for AgentStudioCLI._run_chat_loop.

    Covers scripted (non-interactive) message delivery, JSON output accumulation,
    slash-command handling, and HTTP error behaviour.
    """

    def setUp(self):
        self.proj = MagicMock()
        self.proj.send_message.return_value = {"response": "Agent reply", "conversation_ended": False}
        self.proj.end_chat.return_value = None
        self.proj.get_conversation_url.return_value = "https://example.com/conv-123"

    def test_scripted_messages_sent_in_order(self):
        """Each scripted message is forwarded to project.send_message in order."""
        AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello", "Goodbye"],
        )

        self.assertEqual(self.proj.send_message.call_count, 2)
        self.assertEqual(self.proj.send_message.call_args_list[0][0][1], "Hello")
        self.assertEqual(self.proj.send_message.call_args_list[1][0][1], "Goodbye")

    def test_scripted_messages_exits_cleanly_when_exhausted(self):
        """Loop returns restart=False once all scripted messages are consumed."""
        restart, _ = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello"],
        )

        self.assertFalse(restart)

    def test_exit_command_breaks_loop_without_sending(self):
        """/exit in scripted messages stops the loop; subsequent messages are not sent."""
        AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello", "/exit", "Never sent"],
        )

        self.assertEqual(self.proj.send_message.call_count, 1)

    def test_restart_command_returns_true_without_sending(self):
        """/restart returns True so the caller can create a new session."""
        restart, _ = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["/restart"],
        )

        self.assertTrue(restart)
        self.proj.send_message.assert_not_called()

    def test_json_output_returns_all_turns(self):
        """output_json=True returns a conversation dict with all turns."""
        _, conversation = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello", "Goodbye"],
            output_json=True,
        )

        self.assertEqual(len(conversation["turns"]), 2)
        self.assertEqual(conversation["turns"][0]["input"], "Hello")
        self.assertEqual(conversation["turns"][1]["input"], "Goodbye")

    def test_json_output_includes_conversation_id_and_url(self):
        """The returned conversation dict includes conversation_id and url."""
        _, conversation = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=[],
            output_json=True,
        )

        self.assertEqual(conversation["conversation_id"], "conv-123")
        self.assertIn("url", conversation)

    def test_json_output_initial_response_is_first_turn(self):
        """initial_response is prepended as the first turn with input=None."""
        initial = {"response": "Welcome!", "conversation_ended": False}

        _, conversation = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello"],
            output_json=True,
            initial_response=initial,
        )

        self.assertEqual(len(conversation["turns"]), 2)
        self.assertIsNone(conversation["turns"][0]["input"])
        self.assertEqual(conversation["turns"][0]["response"], "Welcome!")
        self.assertEqual(conversation["turns"][1]["input"], "Hello")

    def test_http_error_is_skipped_and_loop_continues(self):
        """An HTTPError on one turn is absorbed; the next message still sends."""
        import requests

        self.proj.send_message.side_effect = [
            requests.HTTPError("500"),
            {"response": "Fine now", "conversation_ended": False},
        ]

        AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Bad", "Good"],
        )

        self.assertEqual(self.proj.send_message.call_count, 2)

    def test_json_output_records_error_turn(self):
        """HTTPErrors in JSON mode are stored as turns with an 'error' key."""
        import requests

        self.proj.send_message.side_effect = requests.HTTPError("500 Internal Server Error")

        _, conversation = AgentStudioCLI._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello"],
            output_json=True,
        )

        self.assertEqual(len(conversation["turns"]), 1)
        self.assertEqual(conversation["turns"][0]["input"], "Hello")
        self.assertIn("error", conversation["turns"][0])


class ChatCommandTest(unittest.TestCase):
    """Tests for AgentStudioCLI.chat.

    Covers conversation-id shortcut, JSON session events, and scripted input threading.
    """

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.branch_id = "main"
        self.proj.account_id = "test_account"
        self.proj.project_id = "test_project"
        self.proj.create_chat_session.return_value = {
            "conversation_id": "conv-123",
            "response": "Hello!",
            "conversation_ended": False,
        }
        self.proj.send_message.return_value = {"response": "Reply", "conversation_ended": False}
        self.proj.end_chat.return_value = None
        self.proj.get_conversation_url.return_value = "https://example.com/conv-123"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_conversation_id_skips_session_creation(self):
        """When conversation_id is provided, create_chat_session is not called."""
        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            conversation_id="existing-conv",
            input_messages=[],
        )

        self.proj.create_chat_session.assert_not_called()

    def test_no_conversation_id_creates_new_session(self):
        """Without conversation_id, create_chat_session is called to start a session."""
        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            input_messages=[],
        )

        self.proj.create_chat_session.assert_called_once()

    @patch("poly.cli.json_print")
    def test_json_conv_id_emits_conversations_list(self, mock_json):
        """output_json + conversation_id emits one JSON object with a conversations list."""
        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            conversation_id="existing-conv",
            input_messages=[],
            output_json=True,
        )

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertIn("conversations", payload)
        self.assertEqual(len(payload["conversations"]), 1)
        self.assertEqual(payload["conversations"][0]["conversation_id"], "existing-conv")

    @patch("poly.cli.json_print")
    def test_json_no_conv_id_greeting_is_first_turn_in_conversations(self, mock_json):
        """output_json emits one object; greeting appears as turns[0] inside conversations[0]."""
        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            input_messages=[],
            output_json=True,
        )

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        conv = payload["conversations"][0]
        self.assertEqual(conv["conversation_id"], "conv-123")
        self.assertIsNone(conv["turns"][0]["input"])
        self.assertEqual(conv["turns"][0]["response"], "Hello!")

    def test_scripted_messages_forwarded_to_loop(self):
        """input_messages are forwarded and each one is sent via project.send_message."""
        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            input_messages=["Hi", "Bye"],
        )

        self.assertEqual(self.proj.send_message.call_count, 2)

    def test_push_before_chat_calls_push_project(self):
        """push_before_chat=True calls push_project before creating the chat session."""
        self.proj.push_project.return_value = (True, "Pushed successfully", None)

        AgentStudioCLI.chat(
            TEST_DIR,
            environment="sandbox",
            push_before_chat=True,
            input_messages=[],
        )

        self.proj.push_project.assert_called_once_with(
            force=False,
            skip_validation=False,
            dry_run=False,
            format=False,
            email=None,
        )
        self.proj.create_chat_session.assert_called_once()

    def test_push_failure_exits_without_starting_chat(self):
        """push_before_chat=True exits with code 1 when push fails, without creating a session."""
        self.proj.push_project.return_value = (False, "Something went wrong", None)

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.chat(
                TEST_DIR,
                environment="sandbox",
                push_before_chat=True,
                input_messages=[],
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.create_chat_session.assert_not_called()

    @patch("poly.cli.json_print")
    def test_push_failure_json_emits_error_and_exits(self, mock_json):
        """In JSON mode, a push failure emits an error payload before exiting."""
        self.proj.push_project.return_value = (False, "Something went wrong", None)

        with self.assertRaises(SystemExit):
            AgentStudioCLI.chat(
                TEST_DIR,
                environment="sandbox",
                push_before_chat=True,
                input_messages=[],
                output_json=True,
            )

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["push"]["success"], False)
        self.assertIn("error", payload["push"])


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


class ComputeDiffTest(unittest.TestCase):
    """Tests for the _compute_diff method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_no_before_no_after_returns_local_diffs(self):
        """Without before/after, calls get_diffs with all_files=True."""
        expected = {"file.py": "some diff"}
        self.proj.get_diffs.return_value = expected

        result = AgentStudioCLI._compute_diff(TEST_DIR)

        self.proj.get_diffs.assert_called_once_with(all_files=True, files=[])
        self.assertEqual(result, expected)

    def test_no_before_no_after_with_files(self):
        """Without before/after but with files, calls get_diffs with all_files=False."""
        expected = {"file.py": "diff"}
        self.proj.get_diffs.return_value = expected

        AgentStudioCLI._compute_diff(TEST_DIR, files=["file.py"])

        self.proj.get_diffs.assert_called_once()
        call_kwargs = self.proj.get_diffs.call_args[1]
        self.assertFalse(call_kwargs["all_files"])
        self.assertEqual(len(call_kwargs["files"]), 1)

    def test_only_after_finds_previous_version(self):
        """With only after, resolves to previous version and diffs remote versions."""
        versions = [
            {"version_hash": "abc123456xyz"},
            {"version_hash": "def789012xyz"},
        ]
        self.proj.get_deployments.return_value = (versions, {})

        AgentStudioCLI._compute_diff(TEST_DIR, after="abc123456")

        self.proj.diff_remote_named_versions.assert_called_once_with(
            before_name="def789012", after_name="abc123456"
        )
        # before is truncated to [:9], after is passed as given by the caller

    def test_only_after_resolves_deployment_hash(self):
        """With only after matching a deployment key, resolves to its hash value."""
        versions = [
            {"version_hash": "abc123456xyz"},
            {"version_hash": "def789012xyz"},
        ]
        deployment_hashes = {"live": "abc123456xyz"}
        self.proj.get_deployments.return_value = (versions, deployment_hashes)

        AgentStudioCLI._compute_diff(TEST_DIR, after="live")

        self.proj.diff_remote_named_versions.assert_called_once()
        call_kwargs = self.proj.diff_remote_named_versions.call_args[1]
        # after is resolved from deployment_hashes (full hash), before is truncated to [:9]
        self.assertEqual(call_kwargs["after_name"], "abc123456xyz")
        self.assertEqual(call_kwargs["before_name"], "def789012")

    @patch("poly.cli.error")
    def test_only_after_version_not_found_returns_none(self, mock_error):
        """With only after and hash not in versions, calls error and returns None."""
        versions = [{"version_hash": "abc123456xyz"}]
        self.proj.get_deployments.return_value = (versions, {})

        result = AgentStudioCLI._compute_diff(TEST_DIR, after="zzz999999")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli.error")
    def test_only_after_no_previous_version_returns_none(self, mock_error):
        """With only after matching the last version, returns None (no previous)."""
        versions = [{"version_hash": "abc123456xyz"}]
        self.proj.get_deployments.return_value = (versions, {})

        result = AgentStudioCLI._compute_diff(TEST_DIR, after="abc123456")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("No previous version", mock_error.call_args[0][0])

    @patch("poly.cli.error")
    def test_only_after_no_versions_returns_none(self, mock_error):
        """With only after but no versions at all, calls error and returns None."""
        self.proj.get_deployments.return_value = ([], {})

        result = AgentStudioCLI._compute_diff(TEST_DIR, after="abc123456")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    def test_only_before_sets_after_to_local(self):
        """With only before, sets after='local' and diffs remote named versions."""
        AgentStudioCLI._compute_diff(TEST_DIR, before="abc123456")

        self.proj.diff_remote_named_versions.assert_called_once_with(
            before_name="abc123456", after_name="local"
        )

    def test_both_before_and_after(self):
        """With both before and after, diffs between the two remote versions."""
        AgentStudioCLI._compute_diff(TEST_DIR, before="abc123456", after="def789012")

        self.proj.diff_remote_named_versions.assert_called_once_with(
            before_name="abc123456", after_name="def789012"
        )

    def test_only_after_environment_name_queries_correct_env(self):
        """after='live' should fetch deployments for the live environment, not sandbox."""
        versions = [
            {"version_hash": "abc123456xyz"},
            {"version_hash": "def789012xyz"},
        ]
        deployment_hashes = {"live": "abc123456xyz"}
        self.proj.get_deployments.return_value = (versions, deployment_hashes)

        AgentStudioCLI._compute_diff(TEST_DIR, after="live")

        self.proj.get_deployments.assert_called_once_with(client_env="live")


class RevertTest(unittest.TestCase):
    """Tests for the revert CLI method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_revert_no_files_reverts_all(self):
        """Calling revert with no files should revert all changes (new default behaviour)."""
        self.proj.revert_changes.return_value = ["file1.yaml"]

        AgentStudioCLI.revert(TEST_DIR, files=[])

        self.proj.revert_changes.assert_called_once_with(files=[])


class PrintDeploymentsTest(unittest.TestCase):
    """Tests for the print_deployments CLI method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

        self.versions = [{"version_hash": f"hash{i:05d}xxxx", "name": f"v{i}"} for i in range(15)]
        self.active_hashes = {"sandbox": "hash00000xxxx"}

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli.error")
    def test_no_versions_calls_error(self, mock_error):
        """print_deployments with no versions calls error('No versions found.')."""
        self.proj.get_deployments.return_value = ([], {})

        AgentStudioCLI.deployments_list(TEST_DIR)

        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    @patch("poly.cli.print_deployments")
    def test_default_call_shows_first_ten(self, mock_print_dep):
        """Default call (no hash, no json) displays the first 10 versions."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 10)
        self.assertEqual(displayed_versions[0]["name"], "v0")

    @patch("poly.cli.json_print")
    def test_output_json_calls_json_print(self, mock_json_print):
        """print_deployments with output_json=True calls json_print."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR, output_json=True)

        mock_json_print.assert_called_once()
        output = mock_json_print.call_args[0][0]
        self.assertIn("versions", output)
        self.assertIn("active_deployment_hashes", output)
        self.assertEqual(len(output["versions"]), 10)

    @patch("poly.cli.print_deployments")
    def test_hash_sets_offset(self, mock_print_dep):
        """print_deployments with hash finds version index and uses it as offset."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR, version_hash="hash00005")

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(displayed_versions[0]["name"], "v5")

    @patch("poly.cli.error")
    def test_hash_not_found_calls_error(self, mock_error):
        """print_deployments with unknown hash calls error."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR, version_hash="zzz999999")

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli.print_deployments")
    def test_limit_and_offset_applied(self, mock_print_dep):
        """print_deployments with custom limit and offset slices correctly."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR, limit=3, offset=2)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 3)
        self.assertEqual(displayed_versions[0]["name"], "v2")

    @patch("poly.cli.print_deployments")
    def test_details_passed_through(self, mock_print_dep):
        """print_deployments with details=True passes it to the console function."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.deployments_list(TEST_DIR, details=True)

        mock_print_dep.assert_called_once()
        call_kwargs = mock_print_dep.call_args[1]
        self.assertTrue(call_kwargs["details"])


class PlatformAPIGetAccountsTest(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_accounts and get_projects dict orientation."""

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_get_accounts_returns_id_to_name_and_preserves_duplicates(self, mock_request):
        """get_accounts keys by ID so duplicate names don't collide."""
        from poly.handlers.platform_api import PlatformAPIHandler

        mock_request.return_value = [
            {"id": "acc_1", "name": "Same Name", "active": True},
            {"id": "acc_2", "name": "Same Name", "active": True},
            {"id": "acc_3", "name": "Inactive", "active": False},
        ]

        result = PlatformAPIHandler.get_accounts("eu-west-1")

        self.assertEqual(result, {"acc_1": "Same Name", "acc_2": "Same Name"})

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_get_projects_returns_id_to_name_and_preserves_duplicates(self, mock_request):
        """get_projects keys by ID so duplicate names don't collide."""
        from poly.handlers.platform_api import PlatformAPIHandler

        mock_request.return_value = {
            "projects": [
                {"id": "proj_1", "name": "Same Name"},
                {"id": "proj_2", "name": "Same Name"},
            ]
        }

        result = PlatformAPIHandler.get_projects("eu-west-1", "acc_1")

        self.assertEqual(result, {"proj_1": "Same Name", "proj_2": "Same Name"})


class InitProjectTest(unittest.TestCase):
    """Tests for the init_project interactive selection flow."""

    @patch("poly.cli.AgentStudioProject.init_project")
    @patch("poly.cli.AgentStudioInterface")
    def test_init_with_explicit_ids_looks_up_project_name(self, mock_iface_cls, mock_init):
        """When all IDs are provided, project name is looked up by project_id key."""
        api = mock_iface_cls.return_value
        api.get_projects.return_value = {"proj_1": "My Project"}
        mock_init.return_value = (MagicMock(), None)

        AgentStudioCLI.init_project(
            TEST_DIR, region="eu-west-1", account_id="acc_1", project_id="proj_1"
        )

        mock_init.assert_called_once()
        self.assertEqual(mock_init.call_args[1]["project_name"], "My Project")
