"""Tests for the poly/las CLI.

Copyright PolyAI Limited
"""

import os
import unittest
from argparse import ArgumentParser, _SubParsersAction
from io import StringIO
from unittest.mock import MagicMock, patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.audio_cache import AudioCacheCommand
from poly.cli_commands.base import (
    BUILDER_API_GROUP,
    COMMAND_GROUP_ORDER,
    OTHER_GROUP,
    GroupedHelpFormatter,
    add_grouped_subparsers,
    group_subcommands,
)
from poly.cli_commands.branch import (
    BRANCH_INSPECT_GROUP,
    BRANCH_LIFECYCLE_GROUP,
    BRANCH_SUBCOMMAND_GROUPS,
    BranchCommand,
)
from poly.cli_commands.chat import ChatCommand
from poly.cli_commands.conversations import ConversationsCommand
from poly.cli_commands.deployments import DeploymentsCommand
from poly.cli_commands.functions import (
    FUNCTIONS_SUBCOMMAND_GROUP_ORDER,
    FUNCTIONS_SUBCOMMAND_GROUPS,
    FunctionsCommand,
)
from poly.cli_commands.project import InitCommand, ProjectCommand
from poly.cli_commands.shared import (
    compute_diff,
    require_deployment_simplification,
    resolve_project_scope,
)
from poly.cli_commands.sync import FormatCommand, RevertCommand
from poly.cli_commands.utils import CompletionCommand
from poly.project import DeploymentMode
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

    @patch("poly.cli_commands.sync.load_project")
    def test_format_check_calls_project_format_files(self, mock_load):
        """format --check calls project.format_files with check_only=True."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        FormatCommand.format(TEST_DIR, [], check_only=True)

        proj.format_files.assert_called_once()
        call_kw = proj.format_files.call_args[1]
        self.assertTrue(call_kw["check_only"])
        self.assertIsNone(call_kw["files"])

    @patch("poly.cli_commands.sync.load_project")
    def test_format_with_fix_calls_project_format_files(self, mock_load):
        """format without --check calls project.format_files with check_only=False."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        FormatCommand.format(TEST_DIR, [], check_only=False)

        proj.format_files.assert_called_once()
        call_kw = proj.format_files.call_args[1]
        self.assertFalse(call_kw["check_only"])

    @patch("poly.cli_commands.sync.load_project")
    def test_format_with_files_passes_targets_to_project(self, mock_load):
        """format with file list passes resolved absolute paths to format_files."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])

        FormatCommand.format(
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

    @patch("poly.cli_commands.sync.sys.exit")
    @patch("poly.cli_commands.sync.load_project")
    def test_format_check_exits_when_files_would_change(self, mock_load, mock_exit):
        """When check_only and format_files returns would-change paths, format exits with 1."""
        proj = mock_load.return_value
        some_path = os.path.join(TEST_DIR, "functions", "test_function.py")
        proj.format_files.return_value = ([some_path], [])

        FormatCommand.format(TEST_DIR, [], check_only=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli_commands.sync.sys.exit")
    @patch("poly.cli_commands.sync.load_project")
    def test_format_check_exits_when_format_errors(self, mock_load, mock_exit):
        """When format_files returns errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], ["path/to/file: something failed"])

        FormatCommand.format(TEST_DIR, [], check_only=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli_commands.sync.sys.exit")
    @patch("poly.cli_commands.sync.subprocess.run")
    @patch("poly.cli_commands.sync.load_project")
    def test_format_check_exits_when_ty_check_fails(self, mock_load, mock_run, mock_exit):
        """When ty check reports type errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], [])
        mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="type error")

        FormatCommand.format(TEST_DIR, [], check_only=True, run_ty=True)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli_commands.sync.sys.exit")
    @patch("poly.cli_commands.sync.load_project")
    def test_format_with_fix_exits_when_format_errors(self, mock_load, mock_exit):
        """When format (fix mode) returns errors, format exits with 1."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([], ["syntax error in file"])

        FormatCommand.format(TEST_DIR, [], check_only=False)

        mock_exit.assert_called_once_with(1)

    @patch("poly.cli_commands.sync.load_project")
    def test_format_fix_succeeds_and_reports_fixed_files(self, mock_load):
        """poly format (fix mode) reports formatted paths and success."""
        proj = mock_load.return_value
        formatted_path = os.path.join(TEST_DIR, "config", "entities.yaml")
        proj.format_files.return_value = ([formatted_path], [])

        FormatCommand.format(TEST_DIR, [], check_only=False)

        proj.format_files.assert_called_once_with(files=None, check_only=False)

    @patch("poly.cli_commands.sync.load_project")
    def test_format_identifies_issue_fixes_it_and_shows_summary(self, mock_load):
        """Format (fix mode) with affected files shows summary."""
        proj = mock_load.return_value
        proj.format_files.return_value = ([os.path.join(TEST_DIR, "functions", "f.py")], [])

        FormatCommand.format(TEST_DIR, [], check_only=False)

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
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
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
            BranchCommand.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertIn("Uncommitted changes", str(ctx.exception))
        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_not_called()
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_creates_branch_before_pulling(self):
        """The branch must exist before env state is pulled into it.

        Regression test pinning the call order explicitly: the branch is created
        first, then env resources are pulled into it, then pushed. Checking call
        counts/args alone wouldn't catch a reorder of these two calls.
        """
        manager = MagicMock()
        manager.attach_mock(self.proj.create_branch, "create_branch")
        manager.attach_mock(self.proj.pull_project_from_env, "pull_project_from_env")

        BranchCommand.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertEqual(
            [call[0] for call in manager.mock_calls],
            ["create_branch", "pull_project_from_env"],
        )

    def test_branch_create_env_force_bypasses_check(self):
        """branch create --env live --force proceeds despite local changes."""
        self.proj.get_diffs.return_value = {"file.py": "example diff"}

        BranchCommand.branch_create(TEST_DIR, "my-branch", env="live", force=True)

        self.proj.pull_project_from_env.assert_called_once()
        call_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(call_kwargs["env"], "live")
        self.assertIs(call_kwargs["format"], False)
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.push_project.assert_called_once_with(
            force=True,
            skip_validation=True,
            dry_run=False,
            format=False,
        )

    def test_branch_create_env_pulls_from_specified_env(self):
        """branch create --env pre-release pulls resources from pre-release."""
        self.proj.get_diffs.return_value = {}

        BranchCommand.branch_create(TEST_DIR, "my-branch", env="pre-release", force=False)

        self.proj.pull_project_from_env.assert_called_once()
        call_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(call_kwargs["env"], "pre-release")
        self.assertIs(call_kwargs["format"], False)
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.push_project.assert_called_once_with(
            force=True,
            skip_validation=True,
            dry_run=False,
            format=False,
        )

    def test_branch_create_env_raises_when_live_deployment_missing(self):
        """If live (or pre-release) has no active deployment, pull_project_from_env raises.

        The branch has already been created by this point (pull happens after
        creation), so the raise leaves a branch behind with no env state pushed.
        """
        self.proj.get_diffs.return_value = {}
        self.proj.pull_project_from_env.side_effect = ValueError(
            "No resources returned from environment 'live'."
        )

        with self.assertRaises(ValueError) as ctx:
            BranchCommand.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertIn("No resources returned from environment 'live'", str(ctx.exception))
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.pull_project_from_env.assert_called_once()
        pull_kwargs = self.proj.pull_project_from_env.call_args[1]
        self.assertEqual(pull_kwargs["env"], "live")
        self.assertIs(pull_kwargs["format"], False)
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_sandbox_skips_env_pull(self):
        """branch create --env sandbox behaves like normal branch create (no env pull)."""
        BranchCommand.branch_create(TEST_DIR, "my-branch", env="sandbox", force=False)

        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.push_project.assert_not_called()

    @patch("poly.output.console.error")
    def test_branch_create_surfaces_deployment_mode_rejection(self, mock_error):
        """A deployment-mode guard failure raised by the project is shown cleanly, not crashed.

        The "which branches may be created from where" rules live in
        AgentStudioProject.create_branch (they depend on the project's deployment
        mode); the CLI catches that ValueError and reports it via error()/exit(1)
        instead of letting it propagate as an unhandled exception.
        """
        self.proj.branch_id = "example-feature-branch"
        self.proj.create_branch.side_effect = ValueError(
            "Cannot create a new branch from a non-main branch in releases deployment mode."
        )

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_create(TEST_DIR, "my-branch", env=None, force=False)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("non-main branch", mock_error.call_args[0][0])
        self.proj.push_project.assert_not_called()

    @patch("poly.cli_commands.branch.json_print")
    def test_branch_create_json_mode_surfaces_deployment_mode_rejection(self, mock_json):
        """In --json mode, a deployment-mode guard failure is reported as JSON, not a crash."""
        self.proj.branch_id = "example-feature-branch"
        self.proj.create_branch.side_effect = ValueError(
            "Cannot create a new branch from a non-main branch in releases deployment mode."
        )

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_create(
                TEST_DIR, "my-branch", output_json=True, env=None, force=False
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("non-main branch", payload["error"])

    @patch("poly.output.console.success")
    def test_branch_create_reports_branch_it_was_created_from(self, mock_success):
        """The success message names the branch that was current before creation."""
        self.proj.branch_id = "branch-a-id"
        self.proj.get_current_branch.return_value = "feature-a"

        BranchCommand.branch_create(TEST_DIR, "my-branch", env=None, force=False)

        # No source branch is passed: the CLI relies on the project's own branch state.
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        message = mock_success.call_args[0][0]
        self.assertIn("my-branch", message)
        self.assertIn("feature-a", message)

    @patch("poly.cli_commands.branch.json_print")
    def test_branch_create_json_reports_base_branch_from_before_the_switch(self, mock_json):
        """JSON output describes the base branch as it was before create_branch switched."""
        self.proj.branch_id = "branch-a-id"
        self.proj.get_current_branch.return_value = "feature-a"

        def create_and_switch(_branch_name, source_branch_name=None):
            self.proj.branch_id = "new-branch-id"
            return "new-branch-id"

        self.proj.create_branch.side_effect = create_and_switch

        BranchCommand.branch_create(TEST_DIR, "my-branch", output_json=True)

        self.assertEqual(
            mock_json.call_args[0][0],
            {
                "success": True,
                "base_branch_id": "branch-a-id",
                "base_branch_name": "feature-a",
                "new_branch_id": "new-branch-id",
                "branch_name": "my-branch",
            },
        )

    def test_branch_create_env_none_behaves_like_normal(self):
        """branch create with env=None skips env pull (default behavior)."""
        BranchCommand.branch_create(TEST_DIR, "my-branch", env=None, force=False)

        self.proj.pull_project_from_env.assert_not_called()
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.push_project.assert_not_called()

    def test_branch_create_env_does_not_push_when_create_branch_fails(self):
        """After failed branch creation, neither the env pull nor push happen."""
        self.proj.get_diffs.return_value = {}
        self.proj.create_branch.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_create(TEST_DIR, "my-branch", env="live", force=False)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name=None)
        self.proj.pull_project_from_env.assert_not_called()
        self.proj.push_project.assert_not_called()


class BranchCreateFromSourceBranchTest(unittest.TestCase):
    """Tests for ``poly branch create --from <branch>``."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        # The user is on feature-a, but creates from feature-b via --from.
        self.proj.branch_id = "branch-feature-a"
        self.proj.get_current_branch.return_value = "feature-a"
        self.proj.get_diffs.return_value = {}
        self.proj.create_branch.return_value = "new-branch-id"
        self.proj.get_branches.return_value = (
            "feature-a",
            {
                "main": {"branchId": "main"},
                "feature-a": {"branchId": "branch-feature-a", "parentBranchId": "main"},
                "feature-b": {"branchId": "branch-feature-b", "parentBranchId": "main"},
            },
        )
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.success")
    def test_from_flag_is_parsed_and_forwarded_as_the_source_branch(self, _mock_success):
        """'branch create <name> --from <branch>' reaches create_branch as source_branch_name."""
        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(
            ["branch", "create", "my-branch", "--from", "feature-b"]
        )

        BranchCommand.run(args)

        self.proj.create_branch.assert_called_once_with("my-branch", source_branch_name="feature-b")

    @patch("poly.cli_commands.branch.json_print")
    def test_json_output_reports_the_source_branch_as_the_base(self, mock_json):
        """JSON base_branch_name/base_branch_id describe the --from branch, not the current one."""
        BranchCommand.branch_create(
            TEST_DIR, "my-branch", output_json=True, source_branch="feature-b"
        )

        self.assertEqual(
            mock_json.call_args[0][0],
            {
                "success": True,
                "base_branch_id": "branch-feature-b",
                "base_branch_name": "feature-b",
                "new_branch_id": "new-branch-id",
                "branch_name": "my-branch",
            },
        )

    @patch("poly.cli_commands.branch.json_print")
    def test_unknown_source_branch_is_reported_as_a_json_error(self, mock_json):
        """An unknown --from branch is rejected by the project and reported as an error."""
        self.proj.create_branch.side_effect = ValueError("Branch 'ghost' does not exist.")

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_create(
                TEST_DIR, "my-branch", output_json=True, source_branch="ghost"
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(
            mock_json.call_args[0][0],
            {"success": False, "error": "Branch 'ghost' does not exist."},
        )


class BranchDeleteTest(unittest.TestCase):
    """Tests for BranchCommand.branch_delete interactive and direct deletion flow."""

    SAMPLE_BRANCHES = {"main": "main-id", "feature-a": "branch-a-id", "feature-b": "branch-b-id"}

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_branches.return_value = ("main", dict(self.SAMPLE_BRANCHES))
        self.proj.delete_branch.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    # -- Direct deletion (branch_name provided) --

    @patch("questionary.confirm")
    @patch("poly.output.console.success")
    def test_direct_delete_existing_branch_shows_success(self, mock_success, mock_confirm):
        """Deleting an existing branch by name prints a success message."""
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR, branch_name="feature-a")

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_success.assert_called_once()
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_direct_delete_existing_branch_json_mode(self, mock_json):
        """Deleting a branch with output_json=True prints JSON with success=True."""
        BranchCommand.branch_delete(TEST_DIR, branch_name="feature-a", output_json=True)

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_json.assert_called_once_with({"success": True})

    @patch("poly.output.console.error")
    def test_direct_delete_nonexistent_branch_shows_error(self, mock_error):
        """Attempting to delete a branch that doesn't exist shows an error."""
        BranchCommand.branch_delete(TEST_DIR, branch_name="no-such-branch")

        self.proj.delete_branch.assert_not_called()
        mock_error.assert_called_once()
        self.assertIn("does not exist", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_direct_delete_nonexistent_branch_json_mode(self, mock_json):
        """Non-existent branch with output_json=True prints JSON with success=False."""
        BranchCommand.branch_delete(TEST_DIR, branch_name="no-such-branch", output_json=True)

        self.proj.delete_branch.assert_not_called()
        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("does not exist", payload["message"])

    @patch("poly.output.console.error")
    def test_direct_delete_main_branch_shows_error(self, mock_error):
        """Attempting to delete 'main' shows an error because main is not deletable."""
        BranchCommand.branch_delete(TEST_DIR, branch_name="main")

        self.proj.delete_branch.assert_not_called()
        mock_error.assert_called_once()
        self.assertIn("does not exist or cannot be deleted", mock_error.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.output.console.error")
    def test_direct_delete_when_project_raises_shows_error(self, mock_error, mock_confirm):
        """If project.delete_branch raises, the error is shown to the user and the command exits 1."""
        mock_confirm.return_value.ask.return_value = True
        self.proj.delete_branch.side_effect = ValueError("API failure")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_delete(TEST_DIR, branch_name="feature-a")

        mock_error.assert_called_once()
        self.assertIn("API failure", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_direct_delete_when_project_raises_json_mode(self, mock_json):
        """If project.delete_branch raises in JSON mode, error is printed as JSON and exits 1."""
        self.proj.delete_branch.side_effect = ValueError("API failure")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_delete(TEST_DIR, branch_name="feature-a", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("API failure", payload["message"])

    @patch("questionary.confirm")
    @patch("poly.output.console.error")
    def test_direct_delete_returns_false_shows_failure(self, mock_error, mock_confirm):
        """If project.delete_branch returns False, a failure message is shown."""
        mock_confirm.return_value.ask.return_value = True
        self.proj.delete_branch.return_value = False

        BranchCommand.branch_delete(TEST_DIR, branch_name="feature-a")

        mock_error.assert_called_once()
        self.assertIn("Failed to delete", mock_error.call_args[0][0])

    # -- Interactive mode (no branch_name) --

    @patch("poly.output.console.plain")
    def test_interactive_no_deletable_branches_shows_message(self, mock_plain):
        """When only 'main' exists, a 'no deletable branches' message is shown."""
        self.proj.get_branches.return_value = ("main", {"main": "main-id"})

        BranchCommand.branch_delete(TEST_DIR)

        mock_plain.assert_called_once()
        self.assertIn("[muted]No deletable branches found.[/muted]", mock_plain.call_args[0][0])
        self.proj.delete_branch.assert_not_called()

    @patch("questionary.checkbox")
    @patch("poly.output.console.warning")
    def test_interactive_user_selects_nothing_shows_warning(self, mock_warning, mock_checkbox):
        """When user cancels the checkbox, a warning is shown and nothing is deleted."""
        mock_checkbox.return_value.ask.return_value = []

        BranchCommand.branch_delete(TEST_DIR)

        mock_warning.assert_called_once()
        self.assertIn("No branches selected", mock_warning.call_args[0][0])
        self.proj.delete_branch.assert_not_called()

    @patch("questionary.checkbox")
    @patch("poly.output.console.warning")
    def test_interactive_user_returns_none_shows_warning(self, mock_warning, mock_checkbox):
        """When questionary returns None (Ctrl+C), a warning is shown."""
        mock_checkbox.return_value.ask.return_value = None

        BranchCommand.branch_delete(TEST_DIR)

        mock_warning.assert_called_once()
        self.proj.delete_branch.assert_not_called()

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    @patch("poly.output.console.success")
    def test_interactive_single_branch_deleted(self, mock_success, mock_checkbox, mock_confirm):
        """Selecting one branch in the checkbox deletes it and reports success."""
        mock_checkbox.return_value.ask.return_value = ["feature-a"]
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR)

        self.proj.delete_branch.assert_called_once_with("feature-a")
        mock_success.assert_called_once()
        self.assertIn("1 branch(es)", mock_success.call_args[0][0])

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    @patch("poly.output.console.success")
    def test_interactive_multiple_branches_deleted(self, mock_success, mock_checkbox, mock_confirm):
        """Selecting multiple branches deletes each and reports total count."""
        mock_checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR)

        self.assertEqual(self.proj.delete_branch.call_count, 2)
        mock_success.assert_called_once()
        self.assertIn("2 branch(es)", mock_success.call_args[0][0])

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    @patch("poly.output.console.success")
    def test_interactive_current_branch_uses_choice_value(
        self, mock_success, mock_checkbox, mock_confirm
    ):
        """Selecting the current branch calls delete_branch with the plain Choice value."""
        self.proj.get_branches.return_value = ("feature-a", dict(self.SAMPLE_BRANCHES))
        # questionary.checkbox resolves selected Choices to their .value — mocked directly here.
        mock_checkbox.return_value.ask.return_value = ["feature-a"]
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR)

        self.proj.delete_branch.assert_called_once_with("feature-a")

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    @patch("poly.cli_commands.branch.json_print")
    def test_interactive_json_mode_reports_deleted_count(
        self, mock_json, mock_checkbox, mock_confirm
    ):
        """In JSON mode, interactive deletion prints success and deleted count."""
        mock_checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR, output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["deleted"], 2)

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    @patch("poly.output.console.error")
    @patch("poly.output.console.success")
    def test_interactive_error_on_one_branch_continues_others(
        self, mock_success, mock_error, mock_checkbox, mock_confirm
    ):
        """If one branch fails to delete, others still proceed."""
        self.proj.delete_branch.side_effect = [ValueError("oops"), True]
        mock_checkbox.return_value.ask.return_value = ["feature-a", "feature-b"]
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_delete(TEST_DIR)

        self.assertEqual(self.proj.delete_branch.call_count, 2)
        mock_error.assert_called_once()
        mock_success.assert_called_once()
        self.assertIn("1 branch(es)", mock_success.call_args[0][0])


class BranchCurrentTest(unittest.TestCase):
    """Tests for BranchCommand.get_current_branch."""

    BRANCH_TREE = {
        "main": {"branchId": "main"},
        "feature-a": {"branchId": "id-a", "parentBranchId": "main"},
        "feature-b": {"branchId": "id-b", "parentBranchId": "feature-a"},
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def _set_current_branch(self, branch_name: str | None) -> None:
        self.proj.get_branches.return_value = (branch_name, dict(self.BRANCH_TREE))

    @patch("poly.output.console.plain")
    def test_does_not_show_parent_branch_when_parent_is_main(self, mock_plain):
        """A branch with a parent shows both the current and parent branch."""
        self._set_current_branch("feature-a")

        BranchCommand.get_current_branch(TEST_DIR)

        lines = [call.args[0] for call in mock_plain.call_args_list]
        self.assertTrue(any("feature-a" in line for line in lines))
        self.assertFalse(any("main" in line for line in lines))

    @patch("poly.output.console.plain")
    def test_shows_parent_branch_when_present_and_not_main(self, mock_plain):
        """A branch with a parent shows both the current and parent branch."""
        self._set_current_branch("feature-b")

        BranchCommand.get_current_branch(TEST_DIR)

        lines = [call.args[0] for call in mock_plain.call_args_list]
        self.assertTrue(any("feature-b" in line for line in lines))
        self.assertTrue(any("feature-a" in line for line in lines))

    @patch("poly.output.console.plain")
    def test_main_has_no_parent_branch_line(self, mock_plain):
        """main has no parent, so only the current branch is shown."""
        self._set_current_branch("main")

        BranchCommand.get_current_branch(TEST_DIR)

        mock_plain.assert_called_once()
        self.assertIn("main", mock_plain.call_args[0][0])

    @patch("poly.output.console.warning")
    def test_no_current_branch_shows_warning(self, mock_warning):
        """When the local branch no longer exists remotely, a warning is shown."""
        self._set_current_branch(None)

        BranchCommand.get_current_branch(TEST_DIR)

        mock_warning.assert_called_once()

    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_includes_parent_branch(self, mock_json_print):
        """JSON mode includes both current_branch and parent_branch."""
        self._set_current_branch("feature-a")

        BranchCommand.get_current_branch(TEST_DIR, output_json=True)

        mock_json_print.assert_called_once_with(
            {"current_branch": "feature-a", "parent_branch": "main"}
        )

    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_main_has_null_parent(self, mock_json_print):
        """JSON mode for main reports a null parent_branch."""
        self._set_current_branch("main")

        BranchCommand.get_current_branch(TEST_DIR, output_json=True)

        mock_json_print.assert_called_once_with({"current_branch": "main", "parent_branch": None})


class BranchSwitchInteractiveTest(unittest.TestCase):
    """Tests for BranchCommand.branch_switch's interactive picker (no branch_name given)."""

    # Branch metadata as returned by the platform: 'feature-a' was branched off 'main'.
    BRANCH_TREE = {
        "main": {"branchId": "id-main", "parentBranchId": None},
        "feature-a": {"branchId": "id-a", "parentBranchId": "id-main"},
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_branches.return_value = ("main", dict(self.BRANCH_TREE))
        self.proj.switch_branch.return_value = (True, None)
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def _choices(self, mock_select) -> list[tuple[str, str]]:
        """Return the (title, value) pairs of the choices passed to questionary.select."""
        choices = mock_select.call_args.kwargs["choices"]
        return [(choice.title, choice.value) for choice in choices]

    @patch("questionary.select")
    @patch("poly.output.console.success")
    def test_releases_branches_mode_offers_tree_indented_choices(self, mock_success, mock_select):
        """In releases_branches mode, choices show branch lineage but keep plain name values."""
        self.proj.deployment_mode = DeploymentMode.RELEASES_BRANCHES
        mock_select.return_value.ask.return_value = "feature-a"

        BranchCommand.branch_switch(TEST_DIR)

        self.assertEqual(
            self._choices(mock_select),
            [("main (current)", "main"), ("└─ feature-a", "feature-a")],
        )
        self.proj.switch_branch.assert_called_once()
        self.assertEqual(self.proj.switch_branch.call_args[0][0], "feature-a")
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("questionary.select")
    @patch("poly.output.console.success")
    def test_simple_mode_offers_flat_choices(self, mock_success, mock_select):
        """Outside releases_branches mode, choices are a flat list with no tree connectors."""
        self.proj.deployment_mode = DeploymentMode.SIMPLE
        self.proj.get_branches.return_value = (
            "main",
            {"main": "id-main", "feature-a": "id-a"},
        )
        mock_select.return_value.ask.return_value = "feature-a"

        BranchCommand.branch_switch(TEST_DIR)

        self.assertEqual(
            self._choices(mock_select),
            [("main (current)", "main"), ("feature-a", "feature-a")],
        )
        self.proj.switch_branch.assert_called_once()
        self.assertEqual(self.proj.switch_branch.call_args[0][0], "feature-a")
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("questionary.select")
    @patch("poly.output.console.warning")
    def test_nothing_selected_shows_warning_and_does_not_switch(self, mock_warning, mock_select):
        """Cancelling the picker warns the user and leaves the current branch alone."""
        self.proj.deployment_mode = DeploymentMode.RELEASES_BRANCHES
        mock_select.return_value.ask.return_value = None

        BranchCommand.branch_switch(TEST_DIR)

        self.proj.switch_branch.assert_not_called()
        mock_warning.assert_called_once()
        self.assertIn("No branch selected", mock_warning.call_args[0][0])

    @patch("poly.output.console.plain")
    def test_no_branches_shows_message_and_does_not_switch(self, mock_plain):
        """When the project has no branches, a message is shown instead of a picker."""
        self.proj.deployment_mode = DeploymentMode.RELEASES_BRANCHES
        self.proj.get_branches.return_value = (None, {})

        BranchCommand.branch_switch(TEST_DIR)

        self.proj.switch_branch.assert_not_called()
        self.assertIn("No branches found", mock_plain.call_args[0][0])


class BranchMergeTest(unittest.TestCase):
    """Tests for BranchCommand.branch_merge's deploy confirmation and success messaging."""

    # 'feature-a' sits directly under main; 'feature-a-child' sits under the 'Release 1' branch.
    BRANCH_TREE = {
        "main": {"branchId": "main", "name": "main"},
        "Release 1": {"branchId": "id-release-1", "name": "Release 1", "parentBranchId": "main"},
        "feature-a": {"branchId": "id-a", "name": "feature-a", "parentBranchId": "main"},
        "feature-a-child": {
            "branchId": "id-a-child",
            "name": "feature-a-child",
            "parentBranchId": "id-release-1",
        },
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = True
        self.proj.merge_branch.return_value = (True, [], [])
        self._set_current_branch("feature-a")
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def _set_current_branch(self, branch_name: str) -> None:
        """Make the project report the given branch as checked out."""
        self.proj.get_branches.return_value = (branch_name, dict(self.BRANCH_TREE))

    @patch("questionary.confirm")
    @patch("poly.output.console.success")
    def test_merging_into_main_merges_after_deploy_confirmation(self, mock_success, mock_confirm):
        """Merging into main warns about live deployment and proceeds once confirmed."""
        mock_confirm.return_value.ask.return_value = True

        BranchCommand.branch_merge(TEST_DIR, message="ship it")

        mock_confirm.assert_called_once()
        self.proj.merge_branch.assert_called_once_with(message="ship it", conflict_resolutions=None)
        self.assertIn("now live", mock_success.call_args[0][0])

    @patch("questionary.confirm")
    def test_declining_deploy_confirmation_aborts_without_merging(self, mock_confirm):
        """Answering no to the deployment prompt exits cleanly and leaves the branch unmerged."""
        mock_confirm.return_value.ask.return_value = False

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_merge(TEST_DIR, message="ship it")

        self.assertEqual(ctx.exception.code, 0)
        self.proj.merge_branch.assert_not_called()

    @patch("questionary.confirm")
    @patch("poly.output.console.success")
    def test_force_skips_deploy_confirmation(self, mock_success, mock_confirm):
        """--force merges into main without asking for deployment confirmation."""
        BranchCommand.branch_merge(TEST_DIR, message="ship it", force=True)

        mock_confirm.assert_not_called()
        self.proj.merge_branch.assert_called_once_with(message="ship it", conflict_resolutions=None)
        self.assertIn("now live", mock_success.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.output.console.info")
    def test_simplified_deployments_off_skips_confirmation_for_main(self, mock_info, mock_confirm):
        """With simplified deployments off, merging into main skips the deploy prompt too."""
        self.proj.using_simplified_deployments = False

        BranchCommand.branch_merge(TEST_DIR, message="ship it")

        mock_confirm.assert_not_called()
        self.proj.merge_branch.assert_called_once_with(message="ship it", conflict_resolutions=None)
        self.assertIn("main", mock_info.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.output.console.info")
    def test_merging_into_non_main_parent_skips_confirmation_and_names_parent(
        self, mock_info, mock_confirm
    ):
        """Merging into a release branch deploys nothing live, so no prompt is shown."""
        self._set_current_branch("feature-a-child")

        BranchCommand.branch_merge(TEST_DIR, message="ship it")

        mock_confirm.assert_not_called()
        self.proj.merge_branch.assert_called_once_with(message="ship it", conflict_resolutions=None)
        self.assertIn("Release 1", mock_info.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_merges_without_confirmation(self, mock_json_print, mock_confirm):
        """JSON mode is non-interactive, so it merges without prompting and reports success."""
        BranchCommand.branch_merge(TEST_DIR, message="ship it", output_json=True)

        mock_confirm.assert_not_called()
        self.proj.merge_branch.assert_called_once_with(message="ship it", conflict_resolutions=None)
        self.assertEqual(mock_json_print.call_args[0][0], {"success": True})


class BranchSyncTest(unittest.TestCase):
    """Tests for BranchCommand.branch_sync."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = True
        self.proj.get_current_branch.return_value = "feature-a"
        self.proj.sync_branch.return_value = (True, [], [])
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.error")
    def test_sync_blocked_without_simplified_deployments(self, mock_error):
        """Sync is refused locally rather than surfacing the platform's 404."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("simplified deployments", mock_error.call_args[0][0])
        self.proj.sync_branch.assert_not_called()
        self.proj.get_current_branch.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_sync_blocked_without_simplified_deployments_json(self, mock_json_print):
        """The refusal is reported as JSON when --json is set."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertFalse(mock_json_print.call_args[0][0]["success"])
        self.proj.sync_branch.assert_not_called()

    @patch("poly.output.console.success")
    def test_sync_success_reports_branch_name(self, mock_success):
        """A successful sync reports the current branch name."""
        BranchCommand.branch_sync(TEST_DIR)

        self.proj.sync_branch.assert_called_once_with(conflict_resolutions=None)
        self.assertIn("feature-a", mock_success.call_args[0][0])
        self.assertIn("synced successfully", mock_success.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_reports_success(self, mock_json_print):
        """JSON mode reports success without conflicts/errors keys."""
        BranchCommand.branch_sync(TEST_DIR, output_json=True)

        self.assertEqual(mock_json_print.call_args[0][0], {"success": True})

    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_reports_failure_and_exits(self, mock_json_print):
        """JSON mode reports conflicts/errors and exits non-zero on failure."""
        conflicts = [{"path": ["a"], "type": "modify"}]
        self.proj.sync_branch.return_value = (False, conflicts, [])

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        output = mock_json_print.call_args[0][0]
        self.assertEqual(output["success"], False)
        self.assertEqual(output["conflicts"], conflicts)

    @patch("poly.cli_commands.branch.json_print")
    def test_interactive_and_json_together_is_rejected(self, mock_json_print):
        """--interactive and --json cannot be combined."""
        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR, output_json=True, interactive=True)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.sync_branch.assert_not_called()
        self.assertFalse(mock_json_print.call_args[0][0]["success"])

    @patch("poly.output.console.error")
    def test_non_interactive_conflicts_exit_with_guidance(self, mock_error):
        """Non-interactive conflicts print guidance and exit non-zero, without merging further."""
        conflicts = [{"path": ["a"], "type": "modify"}]
        self.proj.sync_branch.return_value = (False, conflicts, [])

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.sync_branch.assert_called_once_with(conflict_resolutions=None)
        mock_error.assert_any_call("Failed to sync branch 'feature-a'.")

    @patch("poly.output.console.error")
    def test_errors_exit_before_conflict_prompt(self, mock_error):
        """A hard error (not just conflicts) exits immediately, even without --interactive."""
        self.proj.sync_branch.return_value = (
            False,
            [],
            [{"path": "x", "message": "boom"}],
        )

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_any_call("- x: boom")

    def test_invalid_resolutions_json_exits(self):
        """An unparseable --resolutions value exits with an error before syncing."""
        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_sync(TEST_DIR, resolutions_file="not-json")

        self.assertEqual(ctx.exception.code, 1)
        self.proj.sync_branch.assert_not_called()

    @patch("poly.output.console.success")
    def test_inline_resolutions_json_is_parsed_and_forwarded(self, mock_success):
        """An inline JSON array passed via --resolutions is forwarded to project.sync_branch."""
        resolutions = [{"path": ["a"], "strategy": "ours"}]

        BranchCommand.branch_sync(TEST_DIR, resolutions_file=str(resolutions).replace("'", '"'))

        self.proj.sync_branch.assert_called_once_with(conflict_resolutions=resolutions)
        mock_success.assert_called_once()


class BranchMergeConflictHelpersTest(unittest.TestCase):
    """Branch merge conflict enrichment, resolution payload, and conflict table layout."""

    def test_branch_merge_conflict_file_key(self):
        from poly.cli_commands.branch import _branch_merge_conflict_file_key

        self.assertEqual(_branch_merge_conflict_file_key([]), "")
        self.assertEqual(_branch_merge_conflict_file_key(["a"]), "a")
        self.assertEqual(_branch_merge_conflict_file_key(["a", "b", "c"]), os.path.join("a", "b"))

    def test_enrich_branch_merge_conflicts_counts_and_merged_value(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

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
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

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

    def test_enrich_dict_values_skips_merge_and_marks_not_auto_mergeable(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["entities", "TOPIC-1", "content"],
                "baseValue": {"id": 1, "name": "base"},
                "theirsValue": {"id": 1, "name": "theirs"},
                "oursValue": {"id": 1, "name": "ours"},
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])
        self.assertEqual(out[0]["visual_path"], os.path.join("entities", "TOPIC-1", "content"))

    def test_enrich_none_base_with_string_theirs_ours_auto_merges(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["user", "city"],
                "baseValue": None,
                "theirsValue": "NYC",
                "oursValue": "Boston",
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNotNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])

    def test_enrich_numeric_values_skips_merge(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["products", "0", "price"],
                "baseValue": 10,
                "theirsValue": 12,
                "oursValue": 15,
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])

    def test_enrich_array_values_skips_merge(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["tags", "list"],
                "baseValue": ["javascript", "react"],
                "theirsValue": ["javascript", "vue"],
                "oursValue": ["javascript", "typescript"],
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])

    def test_enrich_missing_base_with_string_theirs_ours_auto_merges(self):
        """Add conflicts where baseValue is absent but theirs/ours are strings."""
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["user", "name"],
                "theirsValue": "Alice",
                "oursValue": "Bob",
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNotNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])

    def test_enrich_none_base_with_non_string_theirs_ours_skips_merge(self):
        """Delete-vs-update where the surviving values are dicts, not strings."""
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["user"],
                "baseValue": {"id": 1, "name": "John"},
                "oursValue": None,
                "theirsValue": {"id": 1, "name": "John", "age": 35},
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])

    def test_enrich_mixed_string_and_non_string_conflicts(self):
        from poly.cli_commands.branch import enrich_branch_merge_conflicts

        conflicts = [
            {
                "path": ["kb", "t1", "name"],
                "baseValue": "old",
                "theirsValue": "new-theirs",
                "oursValue": "new-ours",
            },
            {
                "path": ["kb", "t1", "metadata"],
                "baseValue": {"key": "val"},
                "theirsValue": {"key": "val2"},
                "oursValue": {"key": "val3"},
            },
        ]
        out = enrich_branch_merge_conflicts(conflicts)
        self.assertIsNotNone(out[0]["merged_value"])
        self.assertFalse(out[0]["can_auto_merge"])
        self.assertIsNone(out[1]["merged_value"])
        self.assertFalse(out[1]["can_auto_merge"])
        fk = os.path.join("kb", "t1")
        self.assertEqual(out[0]["conflicts_in_resource"], 2)
        self.assertEqual(out[1]["conflicts_in_resource"], 2)
        self.assertEqual(out[0]["file_key"], fk)
        self.assertEqual(out[1]["file_key"], fk)

    def test_auto_merge_resolution_payload(self):
        from poly.cli_commands.branch import _auto_merge_resolution

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


class PollTestRunLiveTest(unittest.TestCase):
    """Tests for poll_test_run_live error resilience (used by TestingCommand.testing_run)."""

    @staticmethod
    def _completed_run(test_id: str) -> dict:
        """A fully-completed test run response for a single passing test."""
        return {
            "status": "completed",
            "testHistory": [{"testCaseId": test_id, "status": "passed"}],
            "passedCount": 1,
            "failedCount": 0,
            "errorCount": 0,
            "testCaseCount": 1,
        }

    def setUp(self):
        from collections import namedtuple

        # Minimal stand-in for the TestCase objects poll_test_run_live expects:
        # it only reads `.resource_id` and `.name`.
        FakeTest = namedtuple("FakeTest", ["resource_id", "name"])
        # All tests pass poll_interval=0 so the loop's time.sleep is a no-op
        # and tests run instantly.
        self.matched_tests = [FakeTest(resource_id="tc-1", name="My Test")]

    def test_transient_errors_then_success_returns_completed_run(self):
        """Recovers from a few consecutive transient errors and returns the run."""
        import requests

        from poly.output.console import poll_test_run_live

        completed = self._completed_run("tc-1")
        # First 2 polls fail transiently, the 3rd succeeds with a completed run.
        get_test_run = MagicMock(
            side_effect=[
                requests.exceptions.HTTPError("500 Server Error"),
                requests.exceptions.ConnectionError("connection reset"),
                completed,
            ]
        )

        result = poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=5,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 3)

    def test_error_counter_resets_after_successful_poll(self):
        """A successful poll resets the counter so later errors are tolerated again."""
        import requests

        from poly.output.console import poll_test_run_live

        completed = self._completed_run("tc-1")
        # Pattern: fail, fail, succeed(pending), fail, fail, succeed(done).
        # With max_consecutive_errors=3 this only completes if the counter
        # resets after the pending success in the middle.
        pending = {"status": "running", "testHistory": []}
        get_test_run = MagicMock(
            side_effect=[
                requests.exceptions.HTTPError("boom"),
                requests.exceptions.HTTPError("boom"),
                pending,
                requests.exceptions.HTTPError("boom"),
                requests.exceptions.HTTPError("boom"),
                completed,
            ]
        )

        result = poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=3,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 6)

    def test_persistent_errors_give_up_and_return_empty_dict(self):
        """After max_consecutive_errors failures it gives up without raising."""
        import requests

        from poly.output.console import poll_test_run_live

        get_test_run = MagicMock(side_effect=requests.exceptions.ConnectionError("platform down"))

        result = poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=2,
        )

        # No successful poll ever happened, so the abandoned run returns {}.
        self.assertEqual(result, {})
        self.assertEqual(get_test_run.call_count, 2)

    def test_happy_path_no_errors_returns_completed_run(self):
        """A clean run with no errors returns the completed response on first poll."""
        from poly.output.console import poll_test_run_live

        completed = self._completed_run("tc-1")
        get_test_run = MagicMock(return_value=completed)

        result = poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 1)


class ChatLoopTest(unittest.TestCase):
    """Tests for AgentStudioCLI._run_chat_loop.

    Covers scripted (non-interactive) message delivery, JSON output accumulation,
    slash-command handling, and HTTP error behaviour.
    """

    def setUp(self):
        self.proj = MagicMock()
        self.proj.send_message.return_value = {
            "response": "Agent reply",
            "conversation_ended": False,
        }
        self.proj.end_chat.return_value = None
        self.proj.get_conversation_url.return_value = "https://example.com/conv-123"

    def test_scripted_messages_sent_in_order(self):
        """Each scripted message is forwarded to project.send_message in order."""
        ChatCommand._run_chat_loop(
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
        restart, _ = ChatCommand._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello"],
        )

        self.assertFalse(restart)

    def test_exit_command_breaks_loop_without_sending(self):
        """/exit in scripted messages stops the loop; subsequent messages are not sent."""
        ChatCommand._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello", "/exit", "Never sent"],
        )

        self.assertEqual(self.proj.send_message.call_count, 1)

    def test_restart_command_returns_true_without_sending(self):
        """/restart returns True so the caller can create a new session."""
        restart, _ = ChatCommand._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["/restart"],
        )

        self.assertTrue(restart)
        self.proj.send_message.assert_not_called()

    def test_json_output_returns_all_turns(self):
        """output_json=True returns a conversation dict with all turns."""
        _, conversation = ChatCommand._run_chat_loop(
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
        _, conversation = ChatCommand._run_chat_loop(
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

        _, conversation = ChatCommand._run_chat_loop(
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

        ChatCommand._run_chat_loop(
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

        _, conversation = ChatCommand._run_chat_loop(
            self.proj,
            "conv-123",
            "sandbox",
            input_messages=["Hello"],
            output_json=True,
        )

        self.assertEqual(len(conversation["turns"]), 1)
        self.assertEqual(conversation["turns"][0]["input"], "Hello")
        self.assertIn("error", conversation["turns"][0])


class ChatArgumentsTest(unittest.TestCase):
    """Tests for chat-specific CLI argument parsing."""

    @patch("poly.cli_commands.chat.ChatCommand.chat")
    def test_sip_headers_are_parsed_and_forwarded(self, mock_chat):
        AgentStudioCLI().main(
            [
                "chat",
                "--sip-header",
                "X-Customer-ID=12345",
                "--sip-header",
                "X-Token=part=two",
            ]
        )

        self.assertEqual(
            mock_chat.call_args.kwargs["sip_headers"],
            {"X-Customer-ID": "12345", "X-Token": "part=two"},
        )

    def test_invalid_sip_header_is_rejected(self):
        with self.assertRaises(SystemExit):
            AgentStudioCLI().main(["chat", "--sip-header", "X-Customer-ID"])


class ChatCommandTest(unittest.TestCase):
    """Tests for ChatCommand.chat.

    Covers conversation-id shortcut, JSON session events, and scripted input threading.
    """

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.chat.load_project")
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
        ChatCommand.chat(
            TEST_DIR,
            environment="sandbox",
            conversation_id="existing-conv",
            input_messages=[],
        )

        self.proj.create_chat_session.assert_not_called()

    def test_no_conversation_id_creates_new_session(self):
        """Without conversation_id, create_chat_session is called to start a session."""
        ChatCommand.chat(
            TEST_DIR,
            environment="sandbox",
            input_messages=[],
        )

        self.proj.create_chat_session.assert_called_once()

    def test_sip_headers_are_forwarded_when_creating_session(self):
        sip_headers = {"X-Customer-ID": "12345"}

        ChatCommand.chat(
            TEST_DIR,
            environment="sandbox",
            sip_headers=sip_headers,
            input_messages=[],
        )

        self.proj.create_chat_session.assert_called_once_with(
            "sandbox",
            "chat.polyai",
            None,
            None,
            None,
            sip_headers=sip_headers,
        )

    @patch("poly.cli_commands.chat.json_print")
    def test_json_conv_id_emits_conversations_list(self, mock_json):
        """output_json + conversation_id emits one JSON object with a conversations list."""
        ChatCommand.chat(
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

    @patch("poly.cli_commands.chat.json_print")
    def test_json_no_conv_id_greeting_is_first_turn_in_conversations(self, mock_json):
        """output_json emits one object; greeting appears as turns[0] inside conversations[0]."""
        ChatCommand.chat(
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
        ChatCommand.chat(
            TEST_DIR,
            environment="sandbox",
            input_messages=["Hi", "Bye"],
        )

        self.assertEqual(self.proj.send_message.call_count, 2)

    def test_push_before_chat_calls_push_project(self):
        """push_before_chat=True calls push_project before creating the chat session."""
        self.proj.push_project.return_value = (True, "Pushed successfully", None)

        ChatCommand.chat(
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
        )
        self.proj.create_chat_session.assert_called_once()

    def test_push_failure_exits_without_starting_chat(self):
        """push_before_chat=True exits with code 1 when push fails, without creating a session."""
        self.proj.push_project.return_value = (False, "Something went wrong", None)

        with self.assertRaises(SystemExit) as ctx:
            ChatCommand.chat(
                TEST_DIR,
                environment="sandbox",
                push_before_chat=True,
                input_messages=[],
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.create_chat_session.assert_not_called()

    @patch("poly.cli_commands.chat.json_print")
    def test_push_failure_json_emits_error_and_exits(self, mock_json):
        """In JSON mode, a push failure emits an error payload before exiting."""
        self.proj.push_project.return_value = (False, "Something went wrong", None)

        with self.assertRaises(SystemExit):
            ChatCommand.chat(
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
            CompletionCommand.print_completion("bash")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_zsh_outputs_script(self):
        """poly completion zsh prints a non-empty zsh completion script."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            CompletionCommand.print_completion("zsh")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_fish_outputs_script(self):
        """poly completion fish prints a non-empty fish completion script."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            CompletionCommand.print_completion("fish")
            output = mock_out.getvalue()
        self.assertTrue(len(output) > 0)

    def test_completion_bash_references_poly(self):
        """bash completion script references the poly command."""
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            CompletionCommand.print_completion("bash")
            output = mock_out.getvalue()
        self.assertIn("poly", output)

    def test_completion_invalid_shell_rejected_by_parser(self):
        """Parser rejects shell choices outside bash/zsh/fish."""
        with self.assertRaises(SystemExit):
            AgentStudioCLI().main(sys_args=["completion", "powershell"])


class ResolveProjectScopeTest(unittest.TestCase):
    """Tests for resolve_project_scope, used by headless-friendly commands."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.shared.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.region = "us-1"
        self.proj.project_id = "local-project"
        self.proj.branch_id = "local-branch"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_all_explicit_bypasses_local_project(self):
        """When all three are given, the local project is never read."""
        result = resolve_project_scope(TEST_DIR, "eu-1", "explicit-project", "explicit-branch")

        self.assertEqual(result, ("eu-1", "explicit-project", "explicit-branch"))
        self.mock_load.assert_not_called()

    def test_none_given_falls_back_to_local_project(self):
        """With nothing explicit, falls back to the local project config."""
        result = resolve_project_scope(TEST_DIR, None, None, None)

        self.assertEqual(result, ("us-1", "local-project", "local-branch"))
        self.mock_load.assert_called_once_with(TEST_DIR, output_json=False)

    def test_partial_args_exits_with_clear_error(self):
        """Giving only some of the three exits rather than silently mixing sources."""
        with patch("poly.output.console.error") as mock_error:
            with self.assertRaises(SystemExit):
                resolve_project_scope(TEST_DIR, "eu-1", None, None)
            mock_error.assert_called_once()
        self.mock_load.assert_not_called()

    def test_partial_args_json_mode_exits_with_json_error(self):
        """The JSON-output path reports the same error as a JSON payload."""
        with patch("poly.cli_commands.shared.json_print") as mock_json:
            with self.assertRaises(SystemExit):
                resolve_project_scope(TEST_DIR, "eu-1", "explicit-project", None, output_json=True)
            mock_json.assert_called_once()
            self.assertFalse(mock_json.call_args[0][0]["success"])
        self.mock_load.assert_not_called()


class ComputeDiffTest(unittest.TestCase):
    """Tests for the _compute_diff method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.shared.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_no_before_no_after_returns_local_diffs(self):
        """Without before/after, calls get_diffs with empty file_paths."""
        expected = {"file.py": "some diff"}
        self.proj.get_diffs.return_value = expected

        result = compute_diff(TEST_DIR)

        self.proj.get_diffs.assert_called_once_with(file_paths=[])
        self.assertEqual(result, expected)

    def test_no_before_no_after_with_files(self):
        """Without before/after but with files, calls get_diffs with file_paths."""
        expected = {"file.py": "diff"}
        self.proj.get_diffs.return_value = expected

        compute_diff(TEST_DIR, files=["file.py"])

        self.proj.get_diffs.assert_called_once()
        call_kwargs = self.proj.get_diffs.call_args[1]
        self.assertEqual(len(call_kwargs["file_paths"]), 1)

    def test_only_after_finds_previous_version(self):
        """With only after, resolves to previous version and diffs remote versions."""
        versions = [
            {"version_hash": "abc123456xyz"},
            {"version_hash": "def789012xyz"},
        ]
        self.proj.get_deployments.return_value = (versions, {})

        compute_diff(TEST_DIR, after="abc123456")

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

        compute_diff(TEST_DIR, after="live")

        self.proj.diff_remote_named_versions.assert_called_once()
        call_kwargs = self.proj.diff_remote_named_versions.call_args[1]
        # after is resolved from deployment_hashes (full hash), before is truncated to [:9]
        self.assertEqual(call_kwargs["after_name"], "abc123456xyz")
        self.assertEqual(call_kwargs["before_name"], "def789012")

    @patch("poly.output.console.error")
    def test_only_after_version_not_found_returns_none(self, mock_error):
        """With only after and hash not in versions, calls error and returns None."""
        versions = [{"version_hash": "abc123456xyz"}]
        self.proj.get_deployments.return_value = (versions, {})

        result = compute_diff(TEST_DIR, after="zzz999999")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.output.console.error")
    def test_only_after_no_previous_version_returns_none(self, mock_error):
        """With only after matching the last version, returns None (no previous)."""
        versions = [{"version_hash": "abc123456xyz"}]
        self.proj.get_deployments.return_value = (versions, {})

        result = compute_diff(TEST_DIR, after="abc123456")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("No previous version", mock_error.call_args[0][0])

    @patch("poly.output.console.error")
    def test_only_after_no_versions_returns_none(self, mock_error):
        """With only after but no versions at all, calls error and returns None."""
        self.proj.get_deployments.return_value = ([], {})

        result = compute_diff(TEST_DIR, after="abc123456")

        self.assertIsNone(result)
        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    def test_only_before_sets_after_to_local(self):
        """With only before, sets after='local' and diffs remote named versions."""
        compute_diff(TEST_DIR, before="abc123456")

        self.proj.diff_remote_named_versions.assert_called_once_with(
            before_name="abc123456", after_name="local"
        )

    def test_both_before_and_after(self):
        """With both before and after, diffs between the two remote versions."""
        compute_diff(TEST_DIR, before="abc123456", after="def789012")

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

        compute_diff(TEST_DIR, after="live")

        self.proj.get_deployments.assert_called_once_with(client_env="live")


class RevertTest(unittest.TestCase):
    """Tests for the revert CLI method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.sync.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def test_revert_no_files_reverts_all(self):
        """Calling revert with no files should revert all changes (new default behaviour)."""
        self.proj.revert_changes.return_value = ["file1.yaml"]

        RevertCommand.revert(TEST_DIR, files=[])

        self.proj.revert_changes.assert_called_once_with(file_paths=[])


class PrintDeploymentsTest(unittest.TestCase):
    """Tests for the print_deployments CLI method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

        self.versions = [{"version_hash": f"hash{i:05d}xxxx", "name": f"v{i}"} for i in range(15)]
        self.active_hashes = {"sandbox": "hash00000xxxx"}

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.error")
    def test_no_versions_calls_error(self, mock_error):
        """print_deployments with no versions calls error('No versions found.')."""
        self.proj.get_deployments.return_value = ([], {})

        DeploymentsCommand.deployments_list(TEST_DIR)

        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    @patch("poly.output.console.print_deployments")
    def test_default_call_shows_all(self, mock_print_dep):
        """Default call (no hash, no json, no limit) displays all versions."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 15)
        self.assertEqual(displayed_versions[0]["name"], "v0")

    @patch("poly.output.console.print_deployments")
    def test_explicit_limit(self, mock_print_dep):
        """--limit caps the number of displayed versions."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, limit=5)

        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 5)

    @patch("poly.cli_commands.deployments.json_print")
    def test_output_json_calls_json_print(self, mock_json_print):
        """print_deployments with output_json=True calls json_print."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, output_json=True)

        mock_json_print.assert_called_once()
        output = mock_json_print.call_args[0][0]
        self.assertIn("versions", output)
        self.assertIn("active_deployment_hashes", output)
        self.assertEqual(len(output["versions"]), 15)

    @patch("poly.output.console.print_deployments")
    def test_hash_sets_offset(self, mock_print_dep):
        """print_deployments with hash finds version index and uses it as offset."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, version_hash="hash00005")

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(displayed_versions[0]["name"], "v5")

    @patch("poly.output.console.error")
    def test_hash_not_found_calls_error(self, mock_error):
        """print_deployments with unknown hash calls error."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, version_hash="zzz999999")

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.output.console.print_deployments")
    def test_limit_and_offset_applied(self, mock_print_dep):
        """print_deployments with custom limit and offset slices correctly."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, limit=3, offset=2)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 3)
        self.assertEqual(displayed_versions[0]["name"], "v2")

    @patch("poly.output.console.print_deployments")
    def test_details_passed_through(self, mock_print_dep):
        """print_deployments with details=True passes it to the console function."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        DeploymentsCommand.deployments_list(TEST_DIR, details=True)

        mock_print_dep.assert_called_once()
        call_kwargs = mock_print_dep.call_args[1]
        self.assertTrue(call_kwargs["details"])


def _make_version(index: int, env: str = "sandbox") -> dict:
    """Build a realistic deployment version dict for tests."""
    return {
        "id": f"dep-{index}",
        "version_hash": f"hash{index:05d}xxxx",
        "created_at": f"Mon, 28 Apr 2026 14:{index:02d}:00 GMT",
        "created_by": "user@example.com",
        "artifact_version": str(40 + index),
        "function_deployment_version": str(index),
        "client_env": env,
        "deployment_metadata": {
            "deployment_type": "manual",
            "deployment_message": f"Deploy {index}",
        },
    }


class DeploymentsShowTest(unittest.TestCase):
    """Tests for the deployments_show CLI method."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = False
        self.mock_load.return_value = self.proj

        # Sandbox versions: [v0(newest), v1, v2, v3, v4(oldest)]
        self.sandbox_versions = [_make_version(i) for i in range(5)]
        self.active_hashes = {"sandbox": "hash00000xxxx"}

    def tearDown(self):
        patch.stopall()

    # ── Error cases ──────────────────────────────────────────────────

    @patch("poly.output.console.error")
    def test_no_versions_calls_error(self, mock_error):
        """When the project has no versions, error is called."""
        self.proj.get_deployments.return_value = ([], {})

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00000")

        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    @patch("poly.output.console.error")
    def test_hash_not_found_calls_error(self, mock_error):
        """When the version hash doesn't match any version, error is called."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, self.active_hashes)

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="zzz999999")

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    # ── JSON output structure ────────────────────────────────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_json_output_contains_required_keys(self, mock_json):
        """JSON output includes success, deployment, active_deployment_hashes, included."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, self.active_hashes)

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00000", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertIn("deployment", payload)
        self.assertIn("active_deployment_hashes", payload)
        self.assertIn("included_deployments", payload)

    @patch("poly.cli_commands.deployments.json_print")
    def test_json_deployment_matches_target_version(self, mock_json):
        """The deployment field in JSON output matches the requested version."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, self.active_hashes)

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00002", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["deployment"]["id"], "dep-2")
        self.assertEqual(payload["deployment"]["version_hash"], "hash00002xxxx")

    # ── Sandbox included deployments ─────────────────────────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_sandbox_target_with_predecessor(self, mock_json):
        """In sandbox, included = sandbox[target:predecessor].

        sandbox: [v0, v1, v2, v3, v4]
        target = v1, predecessor = v2 (next in list)
        included = sandbox[1:2] = [v1]
        """
        self.proj.get_deployments.return_value = (self.sandbox_versions, {})

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00001", output_json=True)

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-1"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_sandbox_last_version_no_predecessor(self, mock_json):
        """The oldest sandbox version has no predecessor — included is just itself.

        sandbox: [v0, v1, v2, v3, v4]
        target = v4, no predecessor → included = sandbox[4:] = [v4]
        """
        self.proj.get_deployments.return_value = (self.sandbox_versions, {})

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00004", output_json=True)

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-4"])

    # ── Cross-env (pre-release/live) included deployments ────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_live_resolves_included_from_sandbox(self, mock_json):
        """For live, included deployments are resolved from sandbox history.

        sandbox: [v0, v1, v2, v3, v4]
        live:    [v0(promoted), v3(promoted)]
        target = v0, predecessor in live = v3
        → look up in sandbox: v0 at idx 0, v3 at idx 3
        → included = sandbox[0:3] = [v0, v1, v2]
        """
        live_versions = [
            _make_version(0, env="live"),
            _make_version(3, env="live"),
        ]
        self.proj.get_deployments.side_effect = [
            (live_versions, {"live": "hash00000xxxx"}),
            (self.sandbox_versions, {}),
        ]

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00000", environment="live", output_json=True
        )

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-0", "dep-1", "dep-2"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_live_first_deployment_includes_all_sandbox(self, mock_json):
        """First deployment in live has no predecessor — included is everything from target onward.

        sandbox: [v0, v1, v2, v3, v4]
        live:    [v2(promoted)]  (first ever live deployment)
        target = v2, no predecessor
        → included = sandbox[2:] = [v2, v3, v4]
        """
        live_versions = [_make_version(2, env="live")]
        self.proj.get_deployments.side_effect = [
            (live_versions, {"live": "hash00002xxxx"}),
            (self.sandbox_versions, {}),
        ]

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00002", environment="live", output_json=True
        )

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-2", "dep-3", "dep-4"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_live_adjacent_versions_includes_only_target(self, mock_json):
        """When live target and predecessor are adjacent in sandbox, included is just target.

        sandbox: [v0, v1, v2, v3, v4]
        live:    [v1(promoted), v2(promoted)]
        target = v1, predecessor in live = v2
        → included = sandbox[1:2] = [v1]
        """
        live_versions = [
            _make_version(1, env="live"),
            _make_version(2, env="live"),
        ]
        self.proj.get_deployments.side_effect = [
            (live_versions, {"live": "hash00001xxxx"}),
            (self.sandbox_versions, {}),
        ]

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00001", environment="live", output_json=True
        )

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-1"])

    # ── Environment routing ──────────────────────────────────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_non_sandbox_env_fetches_sandbox_separately(self, mock_json):
        """For non-sandbox envs, get_deployments is called twice: env + sandbox."""
        live_versions = [_make_version(0, env="live")]
        self.proj.get_deployments.side_effect = [
            (live_versions, {}),
            (self.sandbox_versions, {}),
        ]

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00000", environment="live", output_json=True
        )

        calls = self.proj.get_deployments.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs["client_env"], "live")
        self.assertEqual(calls[1].kwargs["client_env"], "sandbox")

    @patch("poly.cli_commands.deployments.json_print")
    def test_sandbox_env_does_not_fetch_twice(self, mock_json):
        """For sandbox, get_deployments is only called once."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, {})

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00000", environment="sandbox", output_json=True
        )

        self.proj.get_deployments.assert_called_once_with(client_env="sandbox")

    # ── Rich output path ─────────────────────────────────────────────

    @patch("poly.output.console.print_deployment_show")
    def test_rich_output_calls_print_deployment_show(self, mock_show):
        """Without output_json, the rich console function is called."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, self.active_hashes)

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="hash00000")

        mock_show.assert_called_once()
        args = mock_show.call_args[0]
        self.assertEqual(args[0]["id"], "dep-0")
        self.assertEqual(args[1], self.active_hashes)

    # ── Hash prefix truncation ───────────────────────────────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_long_hash_is_truncated_to_nine_chars(self, mock_json):
        """A hash longer than 9 characters still matches via its 9-char prefix."""
        self.proj.get_deployments.return_value = (self.sandbox_versions, {})

        DeploymentsCommand.deployments_show(
            TEST_DIR, version_hash="hash00001xxxx_extra", output_json=True
        )

        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["deployment"]["id"], "dep-1")


class DeploymentsPromoteTest(unittest.TestCase):
    """Tests for AgentStudioCLI.deployments_promote."""

    VERSIONS = [
        {
            "id": "dep-1",
            "version_hash": "abc123456xyz",
            "deployment_metadata": {"deployment_message": "initial release"},
        },
        {
            "id": "dep-2",
            "version_hash": "def789012xyz",
            "deployment_metadata": {"deployment_message": "hotfix"},
        },
    ]
    ACTIVE_HASHES = {"sandbox": "abc123456xyz", "pre-release": "def789012xyz"}

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = False
        self.proj.get_deployments.return_value = (list(self.VERSIONS), dict(self.ACTIVE_HASHES))
        self.proj.promote_deployment.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_happy_path_json(self, mock_json):
        """Promote with --json prints success and calls promote_deployment."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="abc123456",
            to_env="pre-release",
            message="ship it",
            force=True,
            output_json=True,
        )

        self.proj.promote_deployment.assert_called_once_with(
            "dep-1", "pre-release", message="ship it"
        )
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["from_hash"], "abc123456xyz")
        self.assertIn("included_deployments", payload)

    @patch("poly.output.console.success")
    def test_promote_happy_path_force(self, mock_success):
        """Promote with --force skips confirmation and prints success."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="abc123456",
            to_env="pre-release",
            message="ship it",
            force=True,
            output_json=False,
        )

        self.proj.promote_deployment.assert_called_once()
        mock_success.assert_called_once()

    def test_promote_to_live_searches_pre_release_and_sandbox(self):
        """Promoting to live fetches pre-release then sandbox for linear history."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="def789012",
            to_env="live",
            force=True,
            output_json=True,
        )

        calls = self.proj.get_deployments.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][0], ("pre-release",))
        self.assertEqual(calls[1][0], ("sandbox",))

    def test_promote_to_pre_release_searches_sandbox(self):
        """Promoting to pre-release fetches deployments from sandbox."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="abc123456",
            to_env="pre-release",
            force=True,
            output_json=True,
        )

        self.proj.get_deployments.assert_called_once_with("sandbox")

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_rollback_returns_reverted_deployments(self, mock_json):
        """Promoting to an older version returns the deployments being reverted.

        sandbox: [dep-1(newest), dep-2(oldest)]
        active pre-release = dep-1 (newer), promoting dep-2 (older)
        → rollback: included = sandbox[0:1] = [dep-1] (the version being reverted)
        """
        active = {"sandbox": "abc123456xyz", "pre-release": "abc123456xyz"}
        self.proj.get_deployments.return_value = (list(self.VERSIONS), active)

        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="def789012",
            to_env="pre-release",
            force=True,
            output_json=True,
        )

        payload = mock_json.call_args[0][0]
        included_ids = [d["id"] for d in payload["included_deployments"]]
        self.assertEqual(included_ids, ["dep-1"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_resolves_env_name_to_hash(self, mock_json):
        """Passing an env name like 'sandbox' resolves via active_deployment_hashes."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="sandbox",
            to_env="pre-release",
            force=True,
            output_json=True,
        )

        # sandbox -> abc123456xyz -> matches dep-1
        self.proj.promote_deployment.assert_called_once_with(
            "dep-1", "pre-release", message="initial release"
        )

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_not_found_json(self, mock_json):
        """Promote with unknown hash prints error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_promote(
                TEST_DIR,
                from_deployment="zzz999999",
                to_env="pre-release",
                force=True,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("not found", payload["error"])

    @patch("poly.output.console.error")
    def test_promote_not_found_rich(self, mock_error):
        """Promote with unknown hash prints error and exits."""
        with self.assertRaises(SystemExit):
            DeploymentsCommand.deployments_promote(
                TEST_DIR,
                from_deployment="zzz999999",
                to_env="pre-release",
                force=True,
                output_json=False,
            )

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_api_error_json(self, mock_json):
        """API exception during promote prints error JSON and exits."""
        self.proj.promote_deployment.side_effect = RuntimeError("API down")

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_promote(
                TEST_DIR,
                from_deployment="abc123456",
                to_env="pre-release",
                force=True,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("API down", payload["error"])

    @patch("poly.output.console.error")
    def test_promote_api_error_rich(self, mock_error):
        """API exception during promote prints error and exits."""
        self.proj.promote_deployment.side_effect = RuntimeError("API down")

        with self.assertRaises(SystemExit):
            DeploymentsCommand.deployments_promote(
                TEST_DIR,
                from_deployment="abc123456",
                to_env="pre-release",
                force=True,
                output_json=False,
            )

        mock_error.assert_called_once()
        self.assertIn("API down", mock_error.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.output.console.warning")
    def test_promote_user_aborts_confirmation(self, mock_warning, mock_confirm):
        """User declining confirmation aborts with exit 0."""
        mock_confirm.return_value.ask.return_value = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_promote(
                TEST_DIR,
                from_deployment="abc123456",
                to_env="pre-release",
                force=False,
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 0)
        mock_warning.assert_called_once()
        self.proj.promote_deployment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_uses_deployment_message_when_no_message_provided(self, mock_json):
        """When --message is not given, the existing deployment_message is used."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="abc123456",
            to_env="pre-release",
            message=None,
            force=True,
            output_json=True,
        )

        self.proj.promote_deployment.assert_called_once_with(
            "dep-1", "pre-release", message="initial release"
        )

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_custom_message_overrides_deployment_message(self, mock_json):
        """When --message is provided, it overrides the deployment_message."""
        DeploymentsCommand.deployments_promote(
            TEST_DIR,
            from_deployment="abc123456",
            to_env="pre-release",
            message="custom notes",
            force=True,
            output_json=True,
        )

        self.proj.promote_deployment.assert_called_once_with(
            "dep-1", "pre-release", message="custom notes"
        )


class DeploymentsRollbackTest(unittest.TestCase):
    """Tests for AgentStudioCLI.deployments_rollback."""

    VERSIONS = [
        {
            "id": "dep-1",
            "version_hash": "abc123456xyz",
            "deployment_metadata": {"deployment_message": "initial release"},
        },
        {
            "id": "dep-2",
            "version_hash": "def789012xyz",
            "deployment_metadata": {"deployment_message": "hotfix"},
        },
    ]
    ACTIVE_HASHES = {"sandbox": "abc123456xyz"}

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = False
        self.proj.get_deployments.return_value = (list(self.VERSIONS), dict(self.ACTIVE_HASHES))
        self.proj.rollback_deployment.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_happy_path_json(self, mock_json):
        """Rollback with --json prints success and calls rollback_deployment."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="def789012",
            message="revert",
            force=True,
            output_json=True,
        )

        self.proj.rollback_deployment.assert_called_once_with("dep-2", message="revert")
        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["target_hash"], "def789012xyz")
        self.assertEqual(payload["message"], "revert")
        self.assertIn("reverted_deployments", payload)

    @patch("poly.output.console.success")
    def test_rollback_happy_path_force(self, mock_success):
        """Rollback with --force skips confirmation and prints success."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="def789012",
            message="revert",
            force=True,
            output_json=False,
        )

        self.proj.rollback_deployment.assert_called_once()
        mock_success.assert_called_once()

    def test_rollback_always_searches_sandbox(self):
        """Rollback always fetches deployments from sandbox."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="abc123456",
            force=True,
            output_json=True,
        )

        self.proj.get_deployments.assert_called_once_with("sandbox")

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_resolves_env_name_to_hash(self, mock_json):
        """Passing 'sandbox' as deployment resolves via active_deployment_hashes."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="sandbox",
            force=True,
            output_json=True,
        )

        # sandbox -> abc123456xyz -> matches dep-1
        self.proj.rollback_deployment.assert_called_once_with("dep-1", message="initial release")

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_not_found_json(self, mock_json):
        """Rollback with unknown hash prints error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_rollback(
                TEST_DIR,
                deployment="zzz999999",
                force=True,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("not found", payload["error"])

    @patch("poly.output.console.error")
    def test_rollback_not_found_rich(self, mock_error):
        """Rollback with unknown hash prints error and exits."""
        with self.assertRaises(SystemExit):
            DeploymentsCommand.deployments_rollback(
                TEST_DIR,
                deployment="zzz999999",
                force=True,
                output_json=False,
            )

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_api_error_json(self, mock_json):
        """API exception during rollback prints error JSON and exits."""
        self.proj.rollback_deployment.side_effect = RuntimeError("timeout")

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_rollback(
                TEST_DIR,
                deployment="abc123456",
                force=True,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("timeout", payload["error"])

    @patch("poly.output.console.error")
    def test_rollback_api_error_rich(self, mock_error):
        """API exception during rollback prints error and exits."""
        self.proj.rollback_deployment.side_effect = RuntimeError("timeout")

        with self.assertRaises(SystemExit):
            DeploymentsCommand.deployments_rollback(
                TEST_DIR,
                deployment="abc123456",
                force=True,
                output_json=False,
            )

        mock_error.assert_called_once()
        self.assertIn("timeout", mock_error.call_args[0][0])

    @patch("questionary.confirm")
    @patch("poly.output.console.warning")
    def test_rollback_user_aborts_confirmation(self, mock_warning, mock_confirm):
        """User declining confirmation aborts with exit 0."""
        mock_confirm.return_value.ask.return_value = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_rollback(
                TEST_DIR,
                deployment="abc123456",
                force=False,
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 0)
        mock_warning.assert_called_once()
        self.proj.rollback_deployment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_uses_deployment_message_when_no_message_provided(self, mock_json):
        """When --message is not given, the existing deployment_message is used."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="abc123456",
            message=None,
            force=True,
            output_json=True,
        )

        self.proj.rollback_deployment.assert_called_once_with("dep-1", message="initial release")

    @patch("poly.cli_commands.deployments.json_print")
    def test_rollback_custom_message_overrides_deployment_message(self, mock_json):
        """When --message is provided, it overrides the deployment_message."""
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="abc123456",
            message="emergency fix",
            force=True,
            output_json=True,
        )

        self.proj.rollback_deployment.assert_called_once_with("dep-1", message="emergency fix")

    # ── Dry run ──────────────────────────────────────────────────────

    @patch("poly.cli_commands.deployments.json_print")
    def test_dry_run_shows_reverted_without_calling_api(self, mock_json):
        """Dry run shows reverted deployments but does not call rollback_deployment.

        versions: [dep-1(newest, active sandbox), dep-2(oldest)]
        Rolling back to dep-2 → dep-1 is reverted.
        """
        DeploymentsCommand.deployments_rollback(
            TEST_DIR,
            deployment="def789012",
            output_json=True,
            dry_run=True,
        )

        self.proj.rollback_deployment.assert_not_called()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["dry_run"])
        self.assertEqual(payload["target_hash"], "def789012xyz")
        reverted_ids = [d["id"] for d in payload["reverted_deployments"]]
        self.assertEqual(reverted_ids, ["dep-1"])


class InitProjectTest(unittest.TestCase):
    """Tests for the init_project interactive selection flow."""

    @patch("poly.cli_commands.project.AgentStudioProject.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_init_with_explicit_ids_looks_up_project_name(self, mock_iface_cls, mock_init):
        """When all IDs are provided, project name is looked up by project_id key."""
        api = mock_iface_cls.return_value
        api.get_projects.return_value = {"proj_1": "My Project"}
        mock_init.return_value = (MagicMock(), None)

        InitCommand.init_project(
            TEST_DIR, region="eu-west-1", account_id="acc_1", project_id="proj_1"
        )

        mock_init.assert_called_once()
        self.assertEqual(mock_init.call_args[1]["project_name"], "My Project")

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_init_exits_when_no_accounts(self, mock_iface_cls):
        """When get_accounts returns empty dict, init exits with error."""
        api = mock_iface_cls.return_value
        api.get_accounts.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            InitCommand.init_project(TEST_DIR, region="eu-west-1")

        self.assertEqual(ctx.exception.code, 1)

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_init_exits_when_no_projects_json_mode(self, mock_iface_cls):
        """When get_projects returns empty dict in JSON mode, init exits with error."""
        api = mock_iface_cls.return_value
        api.get_accounts.return_value = {"acc_1": "Only Account"}
        api.get_projects.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            InitCommand.init_project(
                TEST_DIR, region="eu-west-1", account_id="acc_1", output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)

    @patch("questionary.confirm")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_init_offers_create_when_no_projects(self, mock_iface_cls, mock_confirm):
        """When get_projects returns empty dict, user is offered to create a project."""
        api = mock_iface_cls.return_value
        api.get_accounts.return_value = {"acc_1": "Only Account"}
        api.get_projects.return_value = {}
        mock_confirm.return_value.ask.return_value = False

        InitCommand.init_project(TEST_DIR, region="eu-west-1")

        mock_confirm.assert_called_once()

    @patch("poly.cli_commands.project.ProjectCommand.create_project")
    @patch("questionary.confirm")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_init_delegates_to_create_project_when_accepted(
        self, mock_iface_cls, mock_confirm, mock_create
    ):
        """When user accepts create prompt, create_project is called."""
        api = mock_iface_cls.return_value
        api.get_accounts.return_value = {"acc_1": "Only Account"}
        api.get_projects.return_value = {}
        mock_confirm.return_value.ask.return_value = True

        InitCommand.init_project(TEST_DIR, region="eu-west-1")

        mock_create.assert_called_once_with(
            TEST_DIR, region="eu-west-1", account_id="acc_1", output_json=False
        )


class CreateProjectTest(unittest.TestCase):
    """Tests for the create project command."""

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_non_interactive_creates_project_and_inits(self, mock_iface_cls, mock_init):
        """create project with all args provided creates the project and inits locally."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.return_value = {"id": "proj-123", "name": "my-project"}

        ProjectCommand.create_project(
            TEST_DIR,
            region="us-1",
            account_id="acc-456",
            project_name="my-project",
            project_id="proj-123",
            output_json=False,
        )

        mock_iface.create_project.assert_called_once_with(
            "us-1",
            "acc-456",
            "my-project",
            "proj-123",
            "Hello, how can I help you?",
            None,
        )
        mock_init.assert_called_once_with(
            TEST_DIR,
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            output_json=False,
        )

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.text")
    @patch("questionary.select")
    def test_interactive_flow_selects_region_account_and_name(
        self, mock_select, mock_text, mock_iface_cls, mock_init
    ):
        """create project with no args probes regions, prompts account/name/id."""
        mock_select.return_value.ask.side_effect = ["us-1", "acc-789"]
        mock_text.return_value.ask.side_effect = ["new-project", "new-project"]

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1", "euw-1"]
        mock_iface.get_accounts.return_value = {"acc-789": "My Account", "acc-456": "Other"}
        mock_iface.create_project.return_value = {"id": "proj-001", "name": "new-project"}

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.get_accessible_regions.assert_called_once()
        mock_iface.get_accounts.assert_called_once_with("us-1")
        mock_iface.create_project.assert_called_once_with(
            "us-1",
            "acc-789",
            "new-project",
            "new-project",
            "Hello, how can I help you?",
            None,
        )
        mock_init.assert_called_once_with(
            TEST_DIR,
            region="us-1",
            account_id="acc-789",
            project_id="proj-001",
            output_json=False,
        )

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.select")
    @patch("questionary.text")
    def test_auto_selects_single_region_and_account(
        self, mock_text, mock_select, mock_iface_cls, mock_init
    ):
        """create project auto-selects when only one region and one account."""
        mock_text.return_value.ask.side_effect = ["new-project", "new-project"]

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1"]
        mock_iface.get_accounts.return_value = {"acc-789": "My Account"}
        mock_iface.create_project.return_value = {"id": "proj-001", "name": "new-project"}

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_select.assert_not_called()
        mock_iface.create_project.assert_called_once_with(
            "us-1",
            "acc-789",
            "new-project",
            "new-project",
            "Hello, how can I help you?",
            None,
        )

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_json_mode_requires_all_args(self, mock_iface_cls):
        """create project --json without all args exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.create_project(
                TEST_DIR,
                region="us-1",
                account_id=None,
                project_name=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface_cls.return_value.create_project.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.select")
    def test_user_cancels_region_selection(self, mock_select, mock_iface_cls, mock_init):
        """create project returns early when user cancels region selection."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1", "euw-1"]
        mock_select.return_value.ask.return_value = None

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.select")
    def test_user_cancels_account_selection(self, mock_select, mock_iface_cls, mock_init):
        """create project returns early when user cancels account selection."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1", "euw-1"]
        mock_iface.get_accounts.return_value = {"acc-100": "Acme Corp", "acc-200": "Other"}
        mock_select.return_value.ask.side_effect = ["us-1", None]

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.text")
    @patch("questionary.select")
    def test_user_cancels_project_name_entry(
        self, mock_select, mock_text, mock_iface_cls, mock_init
    ):
        """create project returns early when user enters empty project name."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1", "euw-1"]
        mock_iface.get_accounts.return_value = {"acc-200": "My Account", "acc-300": "Other"}
        mock_select.return_value.ask.side_effect = ["us-1", "acc-200"]
        mock_text.return_value.ask.return_value = ""

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_api_error_during_creation_reports_failure(self, mock_iface_cls, mock_init):
        """create project reports error and exits when API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.side_effect = RuntimeError("API is down")

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.create_project(
                TEST_DIR,
                region="us-1",
                account_id="acc-300",
                project_name="bad-project",
                project_id="bad-project",
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface.create_project.assert_called_once()
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_api_error_in_json_mode_returns_error_json(self, mock_iface_cls, mock_init):
        """create project --json exits with error JSON when API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.side_effect = RuntimeError("Server error")

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.create_project(
                TEST_DIR,
                region="us-1",
                account_id="acc-400",
                project_name="failing-project",
                project_id="failing-project",
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.select")
    def test_no_accounts_found_exits(self, mock_select, mock_iface_cls, mock_init):
        """create project exits when no accounts exist for the region."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1", "euw-1"]
        mock_iface.get_accounts.return_value = {}
        mock_select.return_value.ask.return_value = "us-1"

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.create_project(
                TEST_DIR,
                region=None,
                account_id=None,
                project_name=None,
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_no_project_id_in_response_does_not_init(self, mock_iface_cls, mock_init):
        """create project exits when API response has no project ID."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.return_value = {"id": None, "name": "orphan"}

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.create_project(
                TEST_DIR,
                region="us-1",
                account_id="acc-500",
                project_name="orphan",
                project_id="orphan",
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_init.assert_not_called()

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.text")
    def test_project_name_is_stripped(self, mock_text, mock_iface_cls, mock_init):
        """create project strips whitespace from interactively entered project name."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["euw-1"]
        mock_iface.get_accounts.return_value = {"acc-600": "My Account"}
        mock_iface.create_project.return_value = {"id": "proj-007", "name": "spaced-name"}
        mock_text.return_value.ask.side_effect = ["  spaced-name  ", "spaced-name"]

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_called_once_with(
            "euw-1",
            "acc-600",
            "spaced-name",
            "spaced-name",
            "Hello, how can I help you?",
            None,
        )

    @patch("poly.cli_commands.project.InitCommand.init_project")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.text")
    def test_project_id_defaults_to_slugified_name(self, mock_text, mock_iface_cls, mock_init):
        """create project ID prompt defaults to lowercase hyphenated version of the name."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accessible_regions.return_value = ["us-1"]
        mock_iface.get_accounts.return_value = {"acc-1": "Acme"}
        mock_iface.create_project.return_value = {"id": "my-new-project", "name": "My New Project"}
        mock_text.return_value.ask.side_effect = ["My New Project", "my-new-project"]

        ProjectCommand.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_called_once_with(
            "us-1",
            "acc-1",
            "My New Project",
            "my-new-project",
            "Hello, how can I help you?",
            None,
        )


class DeleteProjectTest(unittest.TestCase):
    """Tests for the delete project command."""

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_non_interactive_delete_with_force_succeeds(self, mock_iface_cls):
        """delete project with all args and force=True skips confirmation and deletes."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}

        ProjectCommand.delete_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            force=True,
            output_json=False,
        )

        mock_iface.delete_project.assert_called_once_with("us-1", "proj-123")

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_json_mode_requires_all_args(self, mock_iface_cls):
        """delete project --json without all args exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.delete_project(
                region="us-1",
                account_id=None,
                project_id=None,
                force=False,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface_cls.return_value.delete_project.assert_not_called()

    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.confirm")
    def test_interactive_confirm_false_cancels_delete(self, mock_confirm, mock_iface_cls):
        """delete project returns early when user declines confirmation prompt."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_confirm.return_value.ask.return_value = False

        ProjectCommand.delete_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            force=False,
            output_json=False,
        )

        mock_iface.delete_project.assert_not_called()

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_api_failure_surfaces_error(self, mock_iface_cls):
        """delete project exits with error when the API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_iface.delete_project.side_effect = RuntimeError("Server exploded")

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.delete_project(
                region="us-1",
                account_id="acc-456",
                project_id="proj-123",
                force=True,
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface.delete_project.assert_called_once()

    @patch("poly.cli_commands.project.json_print")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_json_mode_outputs_success_payload(self, mock_iface_cls, mock_json_print):
        """delete project --json outputs success JSON with project_id."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}

        ProjectCommand.delete_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            force=True,
            output_json=True,
        )

        mock_iface.delete_project.assert_called_once_with("us-1", "proj-123")
        mock_json_print.assert_called_with({"success": True, "project_id": "proj-123"})


class DuplicateProjectTest(unittest.TestCase):
    """Tests for the duplicate project command."""

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_non_interactive_duplicate_with_all_args_succeeds(self, mock_iface_cls):
        """duplicate project with all args provided creates the duplicate."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_iface.duplicate_project.return_value = {"id": "proj-copy", "name": "My Copy"}

        ProjectCommand.duplicate_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            new_name="My Copy",
            new_project_id="proj-copy",
            output_json=False,
        )

        mock_iface.duplicate_project.assert_called_once_with(
            "us-1", "proj-123", "My Copy", "proj-copy"
        )

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_json_mode_requires_all_args_including_name(self, mock_iface_cls):
        """duplicate project --json without --name exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.duplicate_project(
                region="us-1",
                account_id="acc-456",
                project_id="proj-123",
                new_name=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface_cls.return_value.duplicate_project.assert_not_called()

    @patch("poly.cli_commands.project.AgentStudioInterface")
    @patch("questionary.text")
    def test_interactive_flow_prompts_for_name_and_id(self, mock_text, mock_iface_cls):
        """duplicate project without name/id prompts user for both."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_iface.duplicate_project.return_value = {"id": "proj-dup", "name": "My Project (copy)"}

        # First text prompt: project name. Second: project id.
        mock_text.return_value.ask.side_effect = ["My Project (copy)", "proj-dup"]

        ProjectCommand.duplicate_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            new_name=None,
            new_project_id=None,
            output_json=False,
        )

        mock_iface.duplicate_project.assert_called_once_with(
            "us-1", "proj-123", "My Project (copy)", "proj-dup"
        )

    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_api_failure_surfaces_error(self, mock_iface_cls):
        """duplicate project exits with error when the API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_iface.duplicate_project.side_effect = RuntimeError("Timeout")

        with self.assertRaises(SystemExit) as ctx:
            ProjectCommand.duplicate_project(
                region="us-1",
                account_id="acc-456",
                project_id="proj-123",
                new_name="Copy",
                new_project_id="proj-copy",
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface.duplicate_project.assert_called_once()

    @patch("poly.cli_commands.project.json_print")
    @patch("poly.cli_commands.project.AgentStudioInterface")
    def test_json_mode_outputs_success_payload(self, mock_iface_cls, mock_json_print):
        """duplicate project --json outputs success JSON with project_id and agent_name."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.get_agents.return_value = {"proj-123": "My Project"}
        mock_iface.duplicate_project.return_value = {"id": "proj-dup", "name": "Dup Name"}

        ProjectCommand.duplicate_project(
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            new_name="Dup Name",
            new_project_id="proj-dup",
            output_json=True,
        )

        mock_iface.duplicate_project.assert_called_once_with(
            "us-1", "proj-123", "Dup Name", "proj-dup"
        )
        mock_json_print.assert_called_with(
            {"success": True, "project_id": "proj-dup", "agent_name": "Dup Name"}
        )


class ConversationsCommandTest(unittest.TestCase):
    """Tests for the conversations list/get/get-audio CLI commands."""

    # v3 shape (returned in us-1/uk-1/euw-1) - snake_case, no shortSummary/tags/
    # polyScore/note/deploymentId/direction/language. See DEVP-664.
    SAMPLE_CONVERSATIONS = {
        "conversations": [
            {
                "id": "KA-123",
                "started_at": "2026-05-26T10:00:00+00:00",
                "total_duration": 90,
                "channel": "VOICE-SIP",
                "variant_id": "Voice",
                "handoff": False,
            }
        ],
        "next_offset": None,
        "cursor": None,
    }

    SAMPLE_DETAIL = {
        "conversationId": "KA-123",
        "channel": "VOICE-SIP",
        "startedAt": "2026-05-26T10:00:00+00:00",
        "duration": 90,
        "turns": [
            {"user_input": "", "agent_response": "Hello!"},
            {"user_input": "Hi", "agent_response": "How can I help?"},
        ],
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.conversations.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.region = "us-1"
        self.proj.account_id = "test-account"
        self.proj.project_id = "test-project"
        self.proj.get_conversation_url.return_value = "https://studio.us.poly.ai/conv"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.conversations.AgentStudioInterface.list_conversations")
    @patch("poly.output.console.print_conversations")
    def test_list_calls_api_with_params(self, mock_print, mock_api):
        """conversations list passes account_id/limit/offset to the API."""
        mock_api.return_value = self.SAMPLE_CONVERSATIONS

        ConversationsCommand.conversations_list(TEST_DIR, limit=20, offset=5)

        mock_api.assert_called_once_with(
            region="us-1",
            account_id="test-account",
            project_id="test-project",
            limit=20,
            offset=5,
            cursor=None,
            channel=None,
            in_progress=None,
        )
        mock_print.assert_called_once()

    @patch("poly.cli_commands.conversations.AgentStudioInterface.list_conversations")
    @patch("poly.output.console.print_conversations")
    def test_list_passes_cursor_channel_in_progress(self, mock_print, mock_api):
        """conversations list passes --cursor/--channel/--in-progress through to the API."""
        mock_api.return_value = self.SAMPLE_CONVERSATIONS

        ConversationsCommand.conversations_list(
            TEST_DIR, cursor="abc", channel=["voice"], in_progress=True
        )

        mock_api.assert_called_once_with(
            region="us-1",
            account_id="test-account",
            project_id="test-project",
            limit=50,
            offset=0,
            cursor="abc",
            channel=["voice"],
            in_progress=True,
        )

    @patch("poly.cli_commands.conversations.AgentStudioInterface.list_conversations")
    @patch("poly.cli_commands.conversations.json_print")
    def test_list_json_outputs_raw_response(self, mock_json, mock_api):
        """conversations list --json outputs the full API response."""
        mock_api.return_value = self.SAMPLE_CONVERSATIONS

        ConversationsCommand.conversations_list(TEST_DIR, output_json=True)

        mock_json.assert_called_once_with(self.SAMPLE_CONVERSATIONS)

    @patch("poly.cli_commands.conversations.AgentStudioInterface.list_conversations")
    @patch("poly.output.console.info")
    def test_list_empty_shows_info(self, mock_info, mock_api):
        """conversations list with no results shows info message."""
        mock_api.return_value = {"conversations": [], "next_offset": None, "cursor": None}

        ConversationsCommand.conversations_list(TEST_DIR)

        mock_info.assert_called_once()

    @patch("poly.cli_commands.conversations.AgentStudioInterface.get_conversation")
    @patch("poly.output.console.print_conversation_detail")
    def test_get_calls_api_and_prints(self, mock_print, mock_api):
        """conversations get calls API with conversation_id and prints detail."""
        mock_api.return_value = self.SAMPLE_DETAIL

        ConversationsCommand.conversations_get(TEST_DIR, "KA-123")

        mock_api.assert_called_once_with(
            region="us-1", project_id="test-project", conversation_id="KA-123"
        )
        mock_print.assert_called_once()
        self.assertEqual(mock_print.call_args[1]["studio_url"], "https://studio.us.poly.ai/conv")

    @patch("poly.cli_commands.conversations.AgentStudioInterface.get_conversation")
    @patch("poly.cli_commands.conversations.json_print")
    def test_get_json_outputs_raw_response(self, mock_json, mock_api):
        """conversations get --json outputs the full API response."""
        mock_api.return_value = self.SAMPLE_DETAIL

        ConversationsCommand.conversations_get(TEST_DIR, "KA-123", output_json=True)

        mock_json.assert_called_once_with(self.SAMPLE_DETAIL)

    @patch("builtins.open", create=True)
    @patch("poly.cli_commands.conversations.AgentStudioInterface.get_conversation_audio")
    @patch("poly.output.console.success")
    def test_get_audio_writes_file(self, mock_success, mock_api, mock_open):
        """conversations get-audio downloads and writes a WAV file."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_api.return_value = b"\x00" * 2_000_000

        ConversationsCommand.conversations_get_audio(
            TEST_DIR, "KA-123", output_path="/tmp/test.wav"
        )

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            conversation_id="KA-123",
            direction="combined",
            redacted=False,
        )
        mock_success.assert_called_once()
        self.assertIn("2.0 MB", mock_success.call_args[0][0])


class StudioCommandTest(unittest.TestCase):
    """Tests for StudioCommand.open_agent_studio URL construction."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.project.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.studio_base_url = "https://studio.us.poly.ai/test_account/test_project"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.project.json_print")
    def test_json_output_url_targets_feature_branch(self, mock_json_print):
        """studio --json emits a /home URL with the feature branch id as branchId."""
        from poly.cli_commands.project import StudioCommand

        self.proj.branch_id = "BRANCH-SMOHN3M1"

        StudioCommand.open_agent_studio(base_path=TEST_DIR, output_json=True)

        url = mock_json_print.call_args[0][0]["url"]
        self.assertEqual(
            url,
            "https://studio.us.poly.ai/test_account/test_project/home?branchId=BRANCH-SMOHN3M1",
        )
        self.assertTrue(url.endswith("/home?branchId=BRANCH-SMOHN3M1"))

    @patch("poly.cli_commands.project.json_print")
    def test_json_output_url_targets_default_branch(self, mock_json_print):
        """studio --json emits a /home URL with branchId=main on the default branch."""
        from poly.cli_commands.project import StudioCommand

        self.proj.branch_id = "main"

        StudioCommand.open_agent_studio(base_path=TEST_DIR, output_json=True)

        url = mock_json_print.call_args[0][0]["url"]
        self.assertEqual(
            url,
            "https://studio.us.poly.ai/test_account/test_project/home?branchId=main",
        )
        self.assertTrue(url.endswith("/home?branchId=main"))


class BranchHistoryTest(unittest.TestCase):
    """Tests for BranchCommand.branch_history CLI handler."""

    SAMPLE_BRANCHES = {
        "main": {"branchId": "main-id"},
        "feature-a": {"branchId": "branch-a-id"},
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_branches.return_value = ("feature-a", dict(self.SAMPLE_BRANCHES))
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.print_branch_history")
    @patch("poly.output.console.plain")
    def test_defaults_to_current_branch(self, mock_plain, mock_print_history):
        """When no branch_name is given, history uses the current branch."""
        self.proj.get_branch_history.return_value = [{"mergedAt": "2026-07-01", "branchName": "x"}]

        BranchCommand.branch_history(TEST_DIR)

        self.proj.get_branch_history.assert_called_once_with("branch-a-id")
        mock_print_history.assert_called_once()

    @patch("poly.output.console.print_branch_history")
    @patch("poly.output.console.plain")
    def test_explicit_branch_name(self, mock_plain, mock_print_history):
        """An explicit branch_name looks up its ID and fetches history."""
        self.proj.get_branch_history.return_value = [{"mergedAt": "2026-07-01"}]

        BranchCommand.branch_history(TEST_DIR, branch_name="main")

        self.proj.get_branch_history.assert_called_once_with("main-id")

    @patch("poly.cli_commands.branch.json_print")
    def test_json_output(self, mock_json):
        """JSON mode outputs branch_name, branch_id, and history."""
        history = [{"mergedAt": "2026-07-01", "branchName": "feat"}]
        self.proj.get_branch_history.return_value = history

        BranchCommand.branch_history(TEST_DIR, branch_name="feature-a", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["branch_name"], "feature-a")
        self.assertEqual(payload["branch_id"], "branch-a-id")
        self.assertEqual(payload["history"], history)

    @patch("poly.output.console.plain")
    def test_empty_history_shows_message(self, mock_plain):
        """When history is empty, a 'no history found' message is shown."""
        self.proj.get_branch_history.return_value = []

        BranchCommand.branch_history(TEST_DIR, branch_name="feature-a")

        mock_plain.assert_called_once()
        self.assertIn("No history found", mock_plain.call_args[0][0])

    @patch("poly.output.console.warning")
    def test_nonexistent_branch_shows_warning(self, mock_warning):
        """A branch name not in the branches dict shows a warning."""
        BranchCommand.branch_history(TEST_DIR, branch_name="no-such-branch")

        self.proj.get_branch_history.assert_not_called()
        mock_warning.assert_called_once()
        self.assertIn("does not exist", mock_warning.call_args[0][0])

    @patch("poly.output.console.print_branch_history")
    @patch("poly.output.console.plain")
    def test_limit_truncates_history(self, mock_plain, mock_print_history):
        """--limit truncates history to the given number of entries."""
        self.proj.get_branch_history.return_value = [
            {"mergedAt": f"2026-07-{i:02d}"} for i in range(1, 21)
        ]

        BranchCommand.branch_history(TEST_DIR, branch_name="feature-a", limit=5)

        mock_print_history.assert_called_once()
        printed = mock_print_history.call_args[0][0]
        self.assertEqual(len(printed), 5)

    @patch("poly.output.console.print_branch_history")
    @patch("poly.output.console.plain")
    def test_no_limit_shows_all(self, mock_plain, mock_print_history):
        """Without --limit, all history entries are shown."""
        self.proj.get_branch_history.return_value = [
            {"mergedAt": f"2026-07-{i:02d}"} for i in range(1, 21)
        ]

        BranchCommand.branch_history(TEST_DIR, branch_name="feature-a")

        mock_print_history.assert_called_once()
        printed = mock_print_history.call_args[0][0]
        self.assertEqual(len(printed), 20)

    @patch("poly.cli_commands.branch.json_print")
    def test_limit_applies_to_json_output(self, mock_json):
        """--limit also truncates history in JSON mode."""
        self.proj.get_branch_history.return_value = [
            {"mergedAt": f"2026-07-{i:02d}"} for i in range(1, 21)
        ]

        BranchCommand.branch_history(TEST_DIR, branch_name="feature-a", output_json=True, limit=3)

        payload = mock_json.call_args[0][0]
        self.assertEqual(len(payload["history"]), 3)


class BranchRenameTest(unittest.TestCase):
    """Tests for BranchCommand.branch_rename CLI handler."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_current_branch.return_value = "feature-a"
        self.proj.rename_branch.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.success")
    def test_successful_rename(self, mock_success):
        """A successful rename prints a success message."""
        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name")

        self.proj.rename_branch.assert_called_once_with("new-name")
        mock_success.assert_called_once()
        self.assertIn("feature-a", mock_success.call_args[0][0])
        self.assertIn("new-name", mock_success.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_successful_rename_json(self, mock_json):
        """JSON mode outputs old_branch_name, new_branch_name, and success."""
        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["old_branch_name"], "feature-a")
        self.assertEqual(payload["new_branch_name"], "new-name")

    @patch("poly.output.console.error")
    def test_rename_failure_shows_error(self, mock_error):
        """When rename_branch returns False, a failure message is shown."""
        self.proj.rename_branch.return_value = False

        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name")

        mock_error.assert_called_once()
        self.assertIn("Failed to rename", mock_error.call_args[0][0])

    @patch("poly.output.console.warning")
    def test_no_current_branch_shows_warning(self, mock_warning):
        """When current branch is None, a warning is shown."""
        self.proj.get_current_branch.return_value = None

        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name")

        self.proj.rename_branch.assert_not_called()
        mock_warning.assert_called_once()
        self.assertIn("doesn't exist", mock_warning.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_no_current_branch_json(self, mock_json):
        """JSON mode outputs error when no current branch exists."""
        self.proj.get_current_branch.return_value = None

        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("doesn't exist", payload["error"])

    @patch("poly.output.console.error")
    def test_main_branch_shows_error(self, mock_error):
        """Renaming main branch shows an error."""
        self.proj.get_current_branch.return_value = "main"

        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name")

        self.proj.rename_branch.assert_not_called()
        mock_error.assert_called_once()
        self.assertIn("Cannot rename the main branch", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_main_branch_json(self, mock_json):
        """JSON mode outputs error when trying to rename main."""
        self.proj.get_current_branch.return_value = "main"

        BranchCommand.branch_rename(TEST_DIR, new_branch_name="new-name", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("Cannot rename the main branch", payload["error"])

    @patch("poly.cli_commands.branch.json_print")
    def test_no_name_json_mode(self, mock_json):
        """JSON mode outputs error when no name is provided."""
        self.proj.rename_branch.side_effect = ValueError("New branch name must be provided.")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_rename(TEST_DIR, new_branch_name=None, output_json=True)

        calls = mock_json.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertFalse(calls[0][0][0]["success"])
        self.assertIn("No new branch name provided", calls[0][0][0]["error"])
        self.assertFalse(calls[1][0][0]["success"])

    @patch("poly.output.console.error")
    def test_rename_exception_shows_error(self, mock_error):
        """When rename_branch raises, the error message is shown and the command exits 1."""
        self.proj.rename_branch.side_effect = ValueError("Branch already exists.")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_rename(TEST_DIR, new_branch_name="existing")

        mock_error.assert_called_once()
        self.assertIn("Branch already exists", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_rename_exception_json(self, mock_json):
        """JSON mode outputs the error when rename_branch raises, and exits 1."""
        self.proj.rename_branch.side_effect = ValueError("Branch already exists.")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_rename(TEST_DIR, new_branch_name="existing", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("Branch already exists", payload["error"])


class BranchListArchivedTest(unittest.TestCase):
    """Tests for BranchCommand.branch_list with --archived flag."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.print_archived_branches")
    def test_archived_flag_calls_list_archived(self, mock_print):
        """--archived delegates to list_archived_branches and prints the table."""
        archived = [
            {
                "branchId": "BRANCH-1",
                "name": "old-prompts",
                "parentBranchId": "main",
                "archivedAt": "2026-07-05",
                "daysLeft": 15,
            },
        ]
        self.proj.list_archived_branches.return_value = archived

        BranchCommand.branch_list(TEST_DIR, archived=True)

        self.proj.list_archived_branches.assert_called_once()
        mock_print.assert_called_once_with(archived, {"BRANCH-1": "old-prompts"})

    @patch("poly.output.console.plain")
    def test_archived_empty_shows_message(self, mock_plain):
        """When no archived branches exist, a 'no archived' message is shown."""
        self.proj.list_archived_branches.return_value = []

        BranchCommand.branch_list(TEST_DIR, archived=True)

        mock_plain.assert_called_once()
        self.assertIn("No archived branches", mock_plain.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_archived_json_output(self, mock_json):
        """JSON mode with --archived outputs archived_branches."""
        archived = [{"branchId": "BRANCH-1", "name": "old", "daysLeft": 30}]
        self.proj.list_archived_branches.return_value = archived

        BranchCommand.branch_list(TEST_DIR, output_json=True, archived=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["archived_branches"], archived)

    @patch("poly.output.console.print_branches")
    def test_no_archived_flag_uses_normal_list(self, mock_print):
        """Without --archived, branch_list uses the normal get_branches flow."""
        self.proj.get_branches.return_value = ("main", {"main": "main-id"})

        BranchCommand.branch_list(TEST_DIR, archived=False)

        self.proj.list_archived_branches.assert_not_called()
        self.proj.get_branches.assert_called_once()


class BranchRestoreTest(unittest.TestCase):
    """Tests for BranchCommand.branch_restore CLI handler."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.restore_branch.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.success")
    def test_successful_restore(self, mock_success):
        """A successful restore prints a success message."""
        BranchCommand.branch_restore(TEST_DIR, branch_id="old-branch")

        self.proj.restore_branch.assert_called_once_with("old-branch")
        mock_success.assert_called_once()
        self.assertIn("old-branch", mock_success.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_successful_restore_json(self, mock_json):
        """JSON mode outputs success and the branch name."""
        BranchCommand.branch_restore(TEST_DIR, branch_id="old-branch", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["branch_id"], "old-branch")

    @patch("poly.output.console.error")
    def test_restore_failure(self, mock_error):
        """When restore_branch returns False, a failure message is shown."""
        self.proj.restore_branch.return_value = False

        BranchCommand.branch_restore(TEST_DIR, branch_id="old-branch")

        mock_error.assert_called_once()
        self.assertIn("Failed to restore", mock_error.call_args[0][0])

    @patch("poly.output.console.error")
    def test_restore_not_found_shows_error(self, mock_error):
        """When the branch isn't in the archive, the ValueError is shown and the command exits 1."""
        self.proj.restore_branch.side_effect = ValueError("not found in archive")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_restore(TEST_DIR, branch_id="no-such-branch")

        mock_error.assert_called_once()
        self.assertIn("not found in archive", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_restore_not_found_json(self, mock_json):
        """JSON mode outputs the error when restore_branch raises, and exits 1."""
        self.proj.restore_branch.side_effect = ValueError("not found in archive")

        with self.assertRaises(SystemExit):
            BranchCommand.branch_restore(TEST_DIR, branch_id="no-such-branch", output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("not found in archive", payload["error"])

    @patch("poly.cli_commands.branch.json_print")
    def test_no_name_json_mode_exits(self, mock_json):
        """JSON mode without a branch name prints error and exits."""
        with self.assertRaises(SystemExit):
            BranchCommand.branch_restore(TEST_DIR, branch_id=None, output_json=True)

        mock_json.assert_called_once()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("requires a branch id", payload["error"])

    @patch("poly.output.console.plain")
    def test_no_name_empty_archive_shows_message(self, mock_plain):
        """Interactive mode with no archived branches shows a message."""
        self.proj.list_archived_branches.return_value = []

        BranchCommand.branch_restore(TEST_DIR, branch_id=None)

        mock_plain.assert_called_once()
        self.assertIn("No archived branches", mock_plain.call_args[0][0])
        self.proj.restore_branch.assert_not_called()

    @patch("questionary.select")
    @patch("poly.output.console.warning")
    def test_no_name_user_cancels_shows_warning(self, mock_warning, mock_select):
        """Interactive mode where user cancels shows a warning."""
        self.proj.list_archived_branches.return_value = [
            {"branchId": "BRANCH-1", "name": "old-branch"}
        ]
        mock_select.return_value.ask.return_value = None

        BranchCommand.branch_restore(TEST_DIR, branch_id=None)

        mock_warning.assert_called_once()
        self.assertIn("No branch selected", mock_warning.call_args[0][0])

    @patch("questionary.select")
    @patch("poly.output.console.success")
    def test_no_name_interactive_success(self, mock_success, mock_select):
        """Interactive mode selects a branch and restores it."""
        self.proj.list_archived_branches.return_value = [
            {"branchId": "BRANCH-1", "name": "old-branch", "parentBranchId": "main"},
            {"branchId": "BRANCH-2", "name": "old-branch", "parentBranchId": "BRANCH-1"},
        ]
        # BRANCH-1 is the parent and is itself archived, so the label marks it.
        mock_select.return_value.ask.return_value = (
            "old-branch (BRANCH-2) — parent: old-branch (archived)"
        )
        self.proj.restore_branch.return_value = True

        BranchCommand.branch_restore(TEST_DIR, branch_id=None)

        self.proj.restore_branch.assert_called_once_with("BRANCH-2")
        mock_success.assert_called_once()
        self.assertIn("old-branch", mock_success.call_args[0][0])

    @patch("questionary.select")
    @patch("poly.output.console.error")
    def test_no_name_interactive_restore_fails(self, mock_error, mock_select):
        """Interactive mode shows error when restore returns False."""
        self.proj.list_archived_branches.return_value = [
            {"branchId": "BRANCH-1", "name": "old-branch", "parentBranchId": "main"},
        ]
        mock_select.return_value.ask.return_value = "old-branch (BRANCH-1) — parent: main"
        self.proj.restore_branch.return_value = False

        BranchCommand.branch_restore(TEST_DIR, branch_id=None)

        mock_error.assert_called_once()
        self.assertIn("Failed to restore", mock_error.call_args[0][0])


class RequireDeploymentSimplificationTest(unittest.TestCase):
    """Tests for the require_deployment_simplification CLI gate."""

    def setUp(self):
        self.proj = MagicMock()

    @patch("poly.output.console.error")
    def test_returns_silently_when_enabled(self, mock_error):
        """An enabled project passes through without output or exit."""
        self.proj.using_simplified_deployments = True

        require_deployment_simplification(self.proj)

        mock_error.assert_not_called()

    @patch("poly.output.console.error")
    def test_exits_with_error_when_disabled(self, mock_error):
        """A disabled project is refused on stderr with exit code 1."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            require_deployment_simplification(self.proj)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("simplified deployments", mock_error.call_args[0][0])

    @patch("poly.cli_commands.shared.json_print")
    def test_reports_failure_as_json(self, mock_json_print):
        """In JSON mode the refusal is a machine-readable payload, not stderr text."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            require_deployment_simplification(self.proj, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json_print.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("simplified deployments", payload["error"])

    @patch("poly.cli_commands.shared.json_print")
    def test_json_payload_carries_no_rich_markup(self, mock_json_print):
        """The JSON error stays markup-free so consumers get plain text."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit):
            require_deployment_simplification(self.proj, output_json=True)

        self.assertNotIn("[bold]", mock_json_print.call_args[0][0]["error"])


class BranchTagTest(unittest.TestCase):
    """Tests for BranchCommand.branch_tag and branch_untag."""

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.branch.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.using_simplified_deployments = True
        self.proj.get_current_branch.return_value = "feature-a"
        self.proj.tag_branch.return_value = True
        self.proj.untag_branch.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.output.console.success")
    def test_tag_success_reports_branch_name(self, mock_success):
        """A successful tag names the branch that was staged."""
        BranchCommand.branch_tag(TEST_DIR)

        self.proj.tag_branch.assert_called_once_with()
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("poly.output.console.success")
    def test_untag_success_reports_branch_name(self, mock_success):
        """A successful untag names the branch whose tag was removed."""
        BranchCommand.branch_untag(TEST_DIR)

        self.proj.untag_branch.assert_called_once_with()
        self.assertIn("feature-a", mock_success.call_args[0][0])

    @patch("poly.output.console.error")
    def test_tag_failure_is_reported(self, mock_error):
        """A False from the project layer surfaces as an error."""
        self.proj.tag_branch.return_value = False

        BranchCommand.branch_tag(TEST_DIR)

        self.assertIn("Failed to tag", mock_error.call_args[0][0])

    @patch("poly.output.console.error")
    def test_untag_failure_is_reported(self, mock_error):
        """A False from the project layer surfaces as an error."""
        self.proj.untag_branch.return_value = False

        BranchCommand.branch_untag(TEST_DIR)

        self.assertIn("Failed to remove tag", mock_error.call_args[0][0])

    @patch("poly.cli_commands.branch.json_print")
    def test_json_mode_reports_outcome(self, mock_json_print):
        """JSON mode reports the boolean outcome for both commands."""
        BranchCommand.branch_tag(TEST_DIR, output_json=True)
        self.assertEqual(mock_json_print.call_args[0][0], {"success": True})

        self.proj.untag_branch.return_value = False
        BranchCommand.branch_untag(TEST_DIR, output_json=True)
        self.assertEqual(mock_json_print.call_args[0][0], {"success": False})

    @patch("poly.output.console.error")
    def test_tag_blocked_without_simplified_deployments(self, mock_error):
        """Staging tags only exist under simplified deployments, so tag is gated."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_tag(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("simplified deployments", mock_error.call_args[0][0])
        self.proj.tag_branch.assert_not_called()

    @patch("poly.output.console.error")
    def test_untag_blocked_without_simplified_deployments(self, mock_error):
        """Untag is gated on the same flag as tag."""
        self.proj.using_simplified_deployments = False

        with self.assertRaises(SystemExit) as ctx:
            BranchCommand.branch_untag(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("simplified deployments", mock_error.call_args[0][0])
        self.proj.untag_branch.assert_not_called()


class AudioCacheCommandTest(unittest.TestCase):
    """Tests for the audio-cache CLI commands."""

    SAMPLE_LIST = {
        "entries": [
            {
                "id": "1",
                "transcript": "Hello there",
                "cached_at": "2026-05-26T10:00:00+00:00",
                "hit_count": 3,
                "duration": 1.2,
                "regenerated": False,
                "provider": "eleven_labs",
                "provider_voice_id": "21m00Tcm4TlvDq8ikWAM",
                "audio_filename": "1.wav",
                "imported": False,
                "language_code": "en-US",
            }
        ],
        "total_count": 1,
    }

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.audio_cache.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.region = "us-1"
        self.proj.project_id = "test-project"
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.list_audio_cache")
    @patch("poly.output.console.print_audio_cache_entries")
    def test_list_calls_api_with_params(self, mock_print, mock_api):
        """audio-cache list passes limit/offset/sort to the API."""
        mock_api.return_value = self.SAMPLE_LIST

        AudioCacheCommand.audio_cache_list(TEST_DIR, limit=20, offset=5, sort="hit_count:desc")

        mock_api.assert_called_once_with(
            region="us-1", project_id="test-project", limit=20, offset=5, sort="hit_count:desc"
        )
        mock_print.assert_called_once()

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.list_audio_cache")
    @patch("poly.cli_commands.audio_cache.json_print")
    def test_list_json_outputs_raw_response(self, mock_json, mock_api):
        """audio-cache list --json outputs the full API response."""
        mock_api.return_value = self.SAMPLE_LIST

        AudioCacheCommand.audio_cache_list(TEST_DIR, output_json=True)

        mock_json.assert_called_once_with(self.SAMPLE_LIST)

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.list_audio_cache")
    @patch("poly.output.console.info")
    def test_list_empty_shows_info(self, mock_info, mock_api):
        """audio-cache list with no results shows info message."""
        mock_api.return_value = {"entries": [], "total_count": 0}

        AudioCacheCommand.audio_cache_list(TEST_DIR)

        mock_info.assert_called_once()

    @patch("builtins.open", create=True)
    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.get_audio_cache_file")
    @patch("poly.output.console.success")
    def test_get_file_writes_file(self, mock_success, mock_api, mock_open):
        """audio-cache get-file downloads and writes a WAV file."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_api.return_value = b"\x00" * 2_000_000

        AudioCacheCommand.audio_cache_get_file(TEST_DIR, "entry-1", output_path="/tmp/test.wav")

        mock_api.assert_called_once_with(
            region="us-1", project_id="test-project", entry_id="entry-1"
        )
        mock_success.assert_called_once()
        self.assertIn("2.0 MB", mock_success.call_args[0][0])

    @patch("builtins.open", create=True)
    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.update_audio_cache_file")
    @patch("poly.output.console.success")
    def test_update_file_reads_and_sends_bytes(self, mock_success, mock_api, mock_open):
        """audio-cache update-file reads the local file and sends its bytes."""
        mock_open.return_value.__enter__.return_value.read.return_value = b"RIFF-data"
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        AudioCacheCommand.audio_cache_update_file(
            TEST_DIR, "entry-1", "/tmp/replacement.wav", filename="clip.wav"
        )

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            entry_id="entry-1",
            audio_bytes=b"RIFF-data",
            filename="clip.wav",
        )
        mock_success.assert_called_once()

    @patch("builtins.open", create=True)
    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.update_audio_cache_details")
    @patch("poly.output.console.success")
    def test_update_details_parses_config_and_sends_settings(
        self, mock_success, mock_api, mock_open
    ):
        """audio-cache update-details parses --config JSON into the settings payload."""
        mock_open.return_value.__enter__.return_value.read.return_value = b"RIFF-data"
        mock_open.return_value.__exit__ = MagicMock(return_value=False)

        AudioCacheCommand.audio_cache_update_details(
            TEST_DIR, "entry-1", "/tmp/replacement.wav", "hello", '{"stability": 0.5}'
        )

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            entry_id="entry-1",
            audio_bytes=b"RIFF-data",
            settings={"text": "hello", "config": {"stability": 0.5}},
            filename="replacement.wav",
        )
        mock_success.assert_called_once()

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.update_audio_cache_details")
    @patch("poly.cli_commands.audio_cache.json_print")
    def test_update_details_invalid_config_json_exits(self, mock_json, mock_api):
        """An invalid --config JSON string exits with an error instead of calling the API."""
        with self.assertRaises(SystemExit):
            AudioCacheCommand.audio_cache_update_details(
                TEST_DIR, "entry-1", "/tmp/replacement.wav", "hello", "{not json", output_json=True
            )

        mock_api.assert_not_called()
        mock_json.assert_called_once()
        self.assertFalse(mock_json.call_args[0][0]["success"])

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.delete_audio_cache_entry")
    @patch("poly.output.console.success")
    def test_delete_calls_api(self, mock_success, mock_api):
        """audio-cache delete calls the API with the entry ID."""
        mock_api.return_value = {"success": True}

        AudioCacheCommand.audio_cache_delete(TEST_DIR, "entry-1")

        mock_api.assert_called_once_with(
            region="us-1", project_id="test-project", entry_id="entry-1"
        )
        mock_success.assert_called_once()

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.bulk_delete_audio_cache")
    @patch("poly.output.console.success")
    def test_bulk_delete_splits_comma_separated_ids(self, mock_success, mock_api):
        """audio-cache bulk-delete parses the --ids flag into a list."""
        mock_api.return_value = {"deleted": ["1", "2"], "failed": []}

        AudioCacheCommand.audio_cache_bulk_delete(TEST_DIR, "1, 2")

        mock_api.assert_called_once_with(region="us-1", project_id="test-project", ids=["1", "2"])
        mock_success.assert_called_once()

    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.bulk_delete_audio_cache")
    @patch("poly.output.console.error")
    def test_bulk_delete_reports_failures(self, mock_error, mock_api):
        """audio-cache bulk-delete reports IDs that failed to delete."""
        mock_api.return_value = {"deleted": [], "failed": ["9"]}

        AudioCacheCommand.audio_cache_bulk_delete(TEST_DIR, "9")

        mock_error.assert_called_once()

    @patch("builtins.open", create=True)
    @patch("poly.cli_commands.audio_cache.AgentStudioInterface.synthesize_audio_cache")
    @patch("poly.output.console.success")
    def test_synthesize_writes_preview_file(self, mock_success, mock_api, mock_open):
        """audio-cache synthesize downloads and writes a preview WAV file."""
        mock_open.return_value.__enter__ = MagicMock()
        mock_open.return_value.__exit__ = MagicMock(return_value=False)
        mock_api.return_value = b"\x00" * 1_000_000

        AudioCacheCommand.audio_cache_synthesize(TEST_DIR, "entry-1", "hello", "{}")

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            entry_id="entry-1",
            text="hello",
            config={},
            language=None,
        )
        mock_success.assert_called_once()
        self.assertIn("entry-1-preview.wav", mock_success.call_args[0][0])


class FunctionsCommandTest(unittest.TestCase):
    """Tests for the functions CLI commands (public Functions REST API)."""

    SAMPLE_FUNCTION = {
        "function_id": "fn-1",
        "name": "my_func",
        "description": "desc",
        "parameters": [{"name": "x", "type": "string", "description": "an x"}],
        "code": "def my_func(conv, x: str):\n    pass\n",
        "active": True,
        "usage_count": 2,
    }

    def setUp(self):
        self.mock_scope_patcher = patch("poly.cli_commands.functions.resolve_project_scope")
        self.mock_scope = self.mock_scope_patcher.start()
        self.mock_scope.return_value = ("us-1", "test-project", "branch-1")

    def tearDown(self):
        patch.stopall()

    @patch("poly.cli_commands.functions.AgentStudioInterface.execute_function")
    @patch("poly.cli_commands.functions.AgentStudioInterface.list_functions")
    def test_execute_resolves_function_id_by_name(self, mock_list, mock_api):
        """functions execute resolves a function name to its ID before calling the API."""
        mock_list.return_value = [{"id": "fn-1", "name": "my_func"}]
        mock_api.return_value = {"body": {"ok": True}, "logs": [], "runtime": 5}

        FunctionsCommand.functions_execute(TEST_DIR, "my_func", '{"x": 1}')

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            branch_id="branch-1",
            function_id="fn-1",
            args={"x": 1},
        )

    @patch("poly.cli_commands.functions.AgentStudioInterface.execute_function")
    @patch("poly.cli_commands.functions.AgentStudioInterface.list_functions")
    def test_execute_accepts_function_id_directly(self, mock_list, mock_api):
        """functions execute also accepts a raw function ID, not just a name."""
        mock_list.return_value = [{"id": "fn-1", "name": "my_func"}]
        mock_api.return_value = {"body": {"ok": True}, "logs": [], "runtime": 5}

        FunctionsCommand.functions_execute(TEST_DIR, "fn-1", '{"x": 1}')

        mock_api.assert_called_once_with(
            region="us-1",
            project_id="test-project",
            branch_id="branch-1",
            function_id="fn-1",
            args={"x": 1},
        )

    @patch("poly.cli_commands.functions.AgentStudioInterface.list_functions")
    @patch("poly.output.console.error")
    def test_execute_unknown_function_exits(self, mock_error, mock_list):
        """functions execute exits cleanly when the name/ID matches no function."""
        mock_list.return_value = [{"id": "fn-1", "name": "my_func"}]

        with self.assertRaises(SystemExit):
            FunctionsCommand.functions_execute(TEST_DIR, "not_a_function", "{}")

        mock_error.assert_called_once()

    @patch("poly.output.console.error")
    def test_execute_invalid_args_json_exits(self, mock_error):
        """functions execute rejects malformed --args JSON before resolving the function."""
        with self.assertRaises(SystemExit):
            FunctionsCommand.functions_execute(TEST_DIR, "fn-1", "{not json")

        mock_error.assert_called_once()

    @patch("poly.cli_commands.functions.AgentStudioInterface.validate_functions")
    @patch("poly.output.console.print_function_validation_issues")
    def test_validate_passes_valid_and_issues(self, mock_print, mock_api):
        """functions validate hands the valid flag and issues to the printer."""
        issues = [{"type": "syntax_error", "function_id": "fn-1"}]
        mock_api.return_value = {"valid": False, "issues": issues}

        FunctionsCommand.functions_validate(TEST_DIR)

        mock_print.assert_called_once_with(False, issues)


# argparse wraps the usage line to the terminal width, which differs between the
# Linux and Windows CI runners. Pin it so grouped-help assertions are stable.
HELP_TEST_COLUMNS = "100"


def _format_help_at_fixed_width(parser) -> str:
    """Render a parser's help text at a fixed terminal width."""
    with patch.dict(os.environ, {"COLUMNS": HELP_TEST_COLUMNS}):
        return parser.format_help()


def _help_body(help_text: str) -> str:
    """Return the help text after the usage block, which may wrap over lines."""
    _usage, _, body = help_text.partition("\n\n")
    return body


class GroupedHelpOutputTest(unittest.TestCase):
    """Tests for the grouped section headers in `poly --help`."""

    def setUp(self):
        cli = AgentStudioCLI()
        cli.register_commands()
        self.commands = cli.commands
        self.help_text = _format_help_at_fixed_width(cli._create_parser())

    def test_every_command_has_a_known_group(self):
        """A command with a typo'd group would be silently dropped from its section."""
        for command in self.commands:
            self.assertIn(command.group, COMMAND_GROUP_ORDER, msg=command.command)

    def test_every_command_is_listed_once(self):
        """No command disappears from the help output when it is regrouped."""
        for command in self.commands:
            with self.subTest(command=command.command):
                self.assertIn(f"    {command.command} ", self.help_text)

    def test_headers_appear_in_declared_order(self):
        """Sections render in COMMAND_GROUP_ORDER, not registration order."""
        positions = [
            self.help_text.index(f"\n{title}:")
            for title in COMMAND_GROUP_ORDER
            if f"\n{title}:" in self.help_text
        ]
        self.assertEqual(positions, sorted(positions))

    def test_builder_api_group_lists_api_backed_commands(self):
        """The Builder API section holds the REST-API-backed command families."""
        section = self.help_text.split(f"\n{BUILDER_API_GROUP}:")[1]
        section = section.split(f"\n{OTHER_GROUP}:")[0]

        for command in ["functions", "conversations", "audio-cache", "deployments"]:
            self.assertIn(command, section)
        self.assertNotIn("pull", section)
        # rtc/test/chat operate on local project/branch state, not pure remote
        # API calls, so they belong in Project sync instead.
        for command in ["rtc", "test", "chat"]:
            self.assertNotIn(f"    {command} ", section)

    def test_commands_are_listed_before_options(self):
        """Commands matter more than -h/-v, so they come first."""
        self.assertLess(
            self.help_text.index(f"{COMMAND_GROUP_ORDER[0]}:"),
            self.help_text.index("options:"),
        )

    def test_no_trailing_whitespace_or_blank_runs(self):
        """The header mechanism must not leave ragged whitespace behind."""
        lines = self.help_text.split("\n")
        self.assertEqual([line for line in lines if line != line.rstrip()], [])
        self.assertNotIn("\n\n\n", self.help_text)

    def test_subparsers_placeholder_line_is_hidden(self):
        """The <command> metavar belongs in the usage line, not the body."""
        self.assertIn("<command>", self.help_text.partition("\n\n")[0])
        self.assertNotIn("<command>", _help_body(self.help_text))

    def test_unknown_group_still_renders(self):
        """A subcommand with an unrecognised group is shown rather than dropped."""
        parser = ArgumentParser(formatter_class=GroupedHelpFormatter)
        subparsers = add_grouped_subparsers(parser, dest="command", metavar="<command>")
        subparsers.add_parser("known", help="A grouped command.")
        subparsers.add_parser("stray", help="A stray command.")

        group_subcommands(
            subparsers,
            {"known": BUILDER_API_GROUP, "stray": "Not A Real Group"},
            [BUILDER_API_GROUP],
        )

        help_text = parser.format_help()
        self.assertIn("stray", help_text)
        self.assertIn(f"{OTHER_GROUP}:", help_text)

    def test_unmapped_subcommand_falls_back(self):
        """A subcommand absent from the mapping still appears, under the fallback."""
        parser = ArgumentParser(formatter_class=GroupedHelpFormatter)
        subparsers = add_grouped_subparsers(parser, dest="command", metavar="<command>")
        subparsers.add_parser("forgotten", help="Never assigned a group.")

        group_subcommands(subparsers, {}, [BUILDER_API_GROUP], fallback_group="Leftovers")

        help_text = parser.format_help()
        self.assertIn("Leftovers:", help_text)
        self.assertIn("forgotten", help_text)


class GroupedBranchHelpOutputTest(unittest.TestCase):
    """Tests for the grouped section headers in `poly branch --help`."""

    def setUp(self):
        cli = AgentStudioCLI()
        cli.register_commands()
        parser = cli._create_parser()
        branch_action = [a for a in parser._actions if isinstance(a, _SubParsersAction)][0]
        self.help_text = _format_help_at_fixed_width(branch_action.choices["branch"])

    def test_every_branch_subcommand_is_grouped(self):
        """The mapping must cover every registered branch subcommand."""
        cli = AgentStudioCLI()
        cli.register_commands()
        parser = cli._create_parser()
        branch_action = [a for a in parser._actions if isinstance(a, _SubParsersAction)][0]
        branch_parser = branch_action.choices["branch"]
        registered = [a for a in branch_parser._actions if isinstance(a, _SubParsersAction)][
            0
        ].choices

        self.assertEqual(set(registered), set(BRANCH_SUBCOMMAND_GROUPS))

    def test_lifecycle_and_inspect_sections_render(self):
        """Both sections appear, lifecycle first."""
        self.assertIn(f"{BRANCH_LIFECYCLE_GROUP}:", self.help_text)
        self.assertIn(f"{BRANCH_INSPECT_GROUP}:", self.help_text)
        self.assertLess(
            self.help_text.index(f"{BRANCH_LIFECYCLE_GROUP}:"),
            self.help_text.index(f"{BRANCH_INSPECT_GROUP}:"),
        )

    def test_inspect_section_holds_read_only_subcommands(self):
        """diff/review/status are grouped as inspection, not lifecycle."""
        inspect_section = self.help_text.split(f"{BRANCH_INSPECT_GROUP}:")[1]

        for subcommand in ["diff", "review", "status"]:
            self.assertIn(subcommand, inspect_section)
        for subcommand in ["create", "switch", "merge"]:
            self.assertNotIn(f"    {subcommand} ", inspect_section)

    def test_description_examples_are_still_raw(self):
        """The hand-formatted example block must survive the grouped formatter."""
        self.assertIn("  poly branch create new-branch", self.help_text)

    def test_no_placeholder_or_ragged_whitespace(self):
        """Same cleanup guarantees as the root parser."""
        self.assertNotIn("<subcommand>", _help_body(self.help_text))
        self.assertNotIn("positional arguments:", self.help_text)
        self.assertNotIn("\n\n\n", self.help_text)
        lines = self.help_text.split("\n")
        self.assertEqual([line for line in lines if line != line.rstrip()], [])


class GroupedFunctionsHelpOutputTest(unittest.TestCase):
    """Tests for the grouped section headers in `poly functions --help`."""

    def _functions_parser(self):
        cli = AgentStudioCLI()
        cli.register_commands()
        parser = cli._create_parser()
        root = [a for a in parser._actions if isinstance(a, _SubParsersAction)][0]
        return root.choices["functions"]

    def setUp(self):
        self.help_text = _format_help_at_fixed_width(self._functions_parser())

    def test_every_functions_subcommand_is_grouped(self):
        """The mapping must cover every registered functions subcommand."""
        functions_parser = self._functions_parser()
        registered = [a for a in functions_parser._actions if isinstance(a, _SubParsersAction)][
            0
        ].choices

        self.assertEqual(set(registered), set(FUNCTIONS_SUBCOMMAND_GROUPS))

    def test_all_sections_render_in_order(self):
        """Every section appears, in the declared order."""
        positions = []
        for title in FUNCTIONS_SUBCOMMAND_GROUP_ORDER:
            self.assertIn(f"{title}:", self.help_text)
            positions.append(self.help_text.index(f"{title}:"))

        self.assertEqual(positions, sorted(positions))

    def test_description_examples_are_still_raw(self):
        """The hand-formatted example block must survive the grouped formatter."""
        self.assertIn("  poly functions validate", self.help_text)

    def test_no_placeholder_or_ragged_whitespace(self):
        """Same cleanup guarantees as the other grouped parsers."""
        self.assertNotIn("<subcommand>", _help_body(self.help_text))
        self.assertNotIn("positional arguments:", self.help_text)
        self.assertNotIn("\n\n\n", self.help_text)
        lines = self.help_text.split("\n")
        self.assertEqual([line for line in lines if line != line.rstrip()], [])


class DeploymentsSimplifiedModeTest(unittest.TestCase):
    """Deployment-mode awareness across the deployments command family.

    Under simplified deployments main deploys straight to live and sandbox is frozen
    at its pre-migration state, so these commands must target live rather than reading
    or writing the stale sandbox history. Legacy-mode behaviour is covered by the
    DeploymentsShowTest/PromoteTest/RollbackTest classes above.
    """

    VERSIONS = [
        {
            "id": "dep-1",
            "version_hash": "abc123456xyz",
            "deployment_metadata": {"deployment_message": "initial release"},
        },
        {
            "id": "dep-2",
            "version_hash": "def789012xyz",
            "deployment_metadata": {"deployment_message": "hotfix"},
        },
    ]
    ACTIVE_HASHES = {"sandbox": "abc123456xyz", "live": "abc123456xyz"}

    def setUp(self):
        self.mock_load_patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = self.mock_load_patcher.start()
        self.proj = MagicMock()
        self.proj.get_deployments.return_value = (list(self.VERSIONS), dict(self.ACTIVE_HASHES))
        self.proj.rollback_deployment.return_value = True
        self.mock_load.return_value = self.proj

    def tearDown(self):
        patch.stopall()

    def _client_envs_queried(self):
        """Every client_env passed to get_deployments, positional or keyword."""
        return [
            call.kwargs.get("client_env", call.args[0] if call.args else None)
            for call in self.proj.get_deployments.call_args_list
        ]

    # ── list ─────────────────────────────────────────────────────────

    @patch("poly.output.console.print_deployments")
    def test_list_defaults_to_live_when_simplified(self, _mock_print):
        """With no --env, a converged project lists live rather than frozen sandbox."""
        self.proj.using_simplified_deployments = True

        DeploymentsCommand.deployments_list(TEST_DIR)

        self.assertEqual(self._client_envs_queried(), ["live"])

    @patch("poly.output.console.print_deployments")
    def test_list_defaults_to_sandbox_when_not_simplified(self, _mock_print):
        """An unmigrated project keeps the legacy sandbox default."""
        self.proj.using_simplified_deployments = False

        DeploymentsCommand.deployments_list(TEST_DIR)

        self.assertEqual(self._client_envs_queried(), ["sandbox"])

    @patch("poly.output.console.print_deployments")
    def test_list_explicit_env_wins_when_simplified(self, _mock_print):
        """--env sandbox still reads the frozen pre-migration history."""
        self.proj.using_simplified_deployments = True

        DeploymentsCommand.deployments_list(TEST_DIR, environment="sandbox")

        self.assertEqual(self._client_envs_queried(), ["sandbox"])

    # ── show ─────────────────────────────────────────────────────────

    @patch("poly.output.console.print_deployment_show")
    def test_show_defaults_to_live_when_simplified(self, _mock_print):
        """show defaults to live, then reads sandbox for the included-deployment history."""
        self.proj.using_simplified_deployments = True

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="abc123456")

        self.assertEqual(self._client_envs_queried(), ["live", "sandbox"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_show_reports_no_included_deployments_for_a_post_migration_deploy(self, mock_json):
        """A live-only hash is absent from frozen sandbox, so nothing is bundled into it."""
        self.proj.using_simplified_deployments = True
        live_only = [
            {
                "id": "dep-live",
                "version_hash": "live99999xyz",
                "deployment_metadata": {"deployment_message": "merge to main"},
            }
        ]
        # live holds the merge; sandbox is frozen and never saw this hash
        self.proj.get_deployments.side_effect = [
            (live_only, {"live": "live99999xyz"}),
            (list(self.VERSIONS), dict(self.ACTIVE_HASHES)),
        ]

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="live99999", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertEqual(payload["included_deployments"], [])
        self.assertFalse(payload["is_rollback"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_show_still_resolves_included_for_a_pre_migration_deploy(self, mock_json):
        """A pre-migration promotion kept its sandbox hash, so its bundle still resolves."""
        self.proj.using_simplified_deployments = True
        promoted = [{**self.VERSIONS[0]}]
        self.proj.get_deployments.side_effect = [
            (promoted, {"live": "abc123456xyz"}),
            (list(self.VERSIONS), dict(self.ACTIVE_HASHES)),
        ]

        DeploymentsCommand.deployments_show(TEST_DIR, version_hash="abc123456", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertEqual(
            [d["version_hash"] for d in payload["included_deployments"]],
            ["abc123456xyz", "def789012xyz"],
        )

    # ── promote ──────────────────────────────────────────────────────

    @patch("poly.output.console.error")
    def test_promote_blocked_when_simplified(self, mock_error):
        """Promote is refused before any API call — the platform does not reject it."""
        self.proj.using_simplified_deployments = True

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_promote(
                TEST_DIR, from_deployment="abc123456", to_env="live", force=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.promote_deployment.assert_not_called()
        self.proj.get_deployments.assert_not_called()
        self.assertIn("simplified deployments", mock_error.call_args[0][0])

    @patch("poly.cli_commands.deployments.json_print")
    def test_promote_blocked_when_simplified_json(self, mock_json):
        """The refusal is machine-readable in --json mode."""
        self.proj.using_simplified_deployments = True

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.deployments_promote(
                TEST_DIR, from_deployment="abc123456", to_env="live", output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.promote_deployment.assert_not_called()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("simplified deployments", payload["error"])

    # ── rollback ─────────────────────────────────────────────────────

    @patch("poly.output.console.success")
    def test_rollback_targets_live_when_simplified(self, mock_success):
        """Rollback reads live candidates — the only target the platform accepts."""
        self.proj.using_simplified_deployments = True

        DeploymentsCommand.deployments_rollback(TEST_DIR, deployment="abc123456", force=True)

        self.assertEqual(self._client_envs_queried(), ["live"])
        self.proj.rollback_deployment.assert_called_once_with("dep-1", message="initial release")
        self.assertIn("Live", mock_success.call_args[0][0])
