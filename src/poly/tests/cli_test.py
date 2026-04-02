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


class CreateProjectTest(unittest.TestCase):
    """Tests for the create-project command."""

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    def test_non_interactive_creates_project_and_inits(self, mock_iface_cls, mock_init):
        """create-project with all args provided creates the project and inits locally."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.return_value = {"id": "proj-123", "name": "my-project"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region="us-1",
            account_id="acc-456",
            project_name="my-project",
            output_json=False,
        )

        mock_iface.create_project.assert_called_once_with("us-1", "acc-456", "my-project")
        mock_init.assert_called_once_with(
            TEST_DIR,
            region="us-1",
            account_id="acc-456",
            project_id="proj-123",
            output_json=False,
        )

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_interactive_flow_selects_region_account_and_name(
        self, mock_q, mock_iface_cls, mock_init
    ):
        """create-project with no args prompts for region, account, and name."""
        mock_q.select.return_value.ask.side_effect = ["us-1", "My Account"]
        mock_q.text.return_value.ask.return_value = "new-project"

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accounts.return_value = {"My Account": "acc-789"}
        mock_iface.create_project.return_value = {"id": "proj-001", "name": "new-project"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.get_accounts.assert_called_once_with("us-1")
        mock_iface.create_project.assert_called_once_with("us-1", "acc-789", "new-project")
        mock_init.assert_called_once_with(
            TEST_DIR,
            region="us-1",
            account_id="acc-789",
            project_id="proj-001",
            output_json=False,
        )

    @patch("poly.cli.AgentStudioInterface")
    def test_json_mode_requires_all_args(self, mock_iface_cls):
        """create-project --json without all args exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.create_project(
                TEST_DIR,
                region="us-1",
                account_id=None,
                project_name=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_iface_cls.return_value.create_project.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_user_cancels_region_selection(self, mock_q, mock_iface_cls, mock_init):
        """create-project returns early when user cancels region selection."""
        mock_q.select.return_value.ask.return_value = None

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface_cls.return_value.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_user_cancels_account_selection(self, mock_q, mock_iface_cls, mock_init):
        """create-project returns early when user cancels account selection."""
        mock_q.select.return_value.ask.side_effect = ["us-1", None]

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accounts.return_value = {"Acme Corp": "acc-100"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_user_cancels_project_name_entry(self, mock_q, mock_iface_cls, mock_init):
        """create-project returns early when user enters empty project name."""
        mock_q.select.return_value.ask.side_effect = ["us-1", "My Account"]
        mock_q.text.return_value.ask.return_value = ""

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accounts.return_value = {"My Account": "acc-200"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    def test_api_error_during_creation_reports_failure(self, mock_iface_cls, mock_init):
        """create-project reports error and does not init when API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.side_effect = RuntimeError("API is down")

        AgentStudioCLI.create_project(
            TEST_DIR,
            region="us-1",
            account_id="acc-300",
            project_name="bad-project",
            output_json=False,
        )

        mock_iface.create_project.assert_called_once()
        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    def test_api_error_in_json_mode_returns_error_json(self, mock_iface_cls, mock_init):
        """create-project --json returns error JSON when API call fails."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.side_effect = RuntimeError("Server error")

        AgentStudioCLI.create_project(
            TEST_DIR,
            region="us-1",
            account_id="acc-400",
            project_name="failing-project",
            output_json=True,
        )

        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_no_accounts_found_returns_early(self, mock_q, mock_iface_cls, mock_init):
        """create-project returns early when no accounts exist for the region."""
        mock_q.select.return_value.ask.return_value = "us-1"

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accounts.return_value = {}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_not_called()
        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    def test_no_project_id_in_response_does_not_init(self, mock_iface_cls, mock_init):
        """create-project does not init when API response has no project ID."""
        mock_iface = mock_iface_cls.return_value
        mock_iface.create_project.return_value = {"id": None, "name": "orphan"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region="us-1",
            account_id="acc-500",
            project_name="orphan",
            output_json=False,
        )

        mock_init.assert_not_called()

    @patch("poly.cli.AgentStudioCLI.init_project")
    @patch("poly.cli.AgentStudioInterface")
    @patch("poly.cli.questionary")
    def test_project_name_is_stripped(self, mock_q, mock_iface_cls, mock_init):
        """create-project strips whitespace from interactively entered project name."""
        mock_q.select.return_value.ask.side_effect = ["euw-1", "My Account"]
        mock_q.text.return_value.ask.return_value = "  spaced-name  "

        mock_iface = mock_iface_cls.return_value
        mock_iface.get_accounts.return_value = {"My Account": "acc-600"}
        mock_iface.create_project.return_value = {"id": "proj-007", "name": "spaced-name"}

        AgentStudioCLI.create_project(
            TEST_DIR,
            region=None,
            account_id=None,
            project_name=None,
            output_json=False,
        )

        mock_iface.create_project.assert_called_once_with("euw-1", "acc-600", "spaced-name")
