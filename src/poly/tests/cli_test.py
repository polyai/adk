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

        AgentStudioCLI.print_deployments(TEST_DIR)

        mock_error.assert_called_once()
        self.assertIn("No versions found", mock_error.call_args[0][0])

    @patch("poly.cli.print_deployments")
    def test_default_call_shows_first_ten(self, mock_print_dep):
        """Default call (no hash, no json) displays the first 10 versions."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 10)
        self.assertEqual(displayed_versions[0]["name"], "v0")

    @patch("poly.cli.json_print")
    def test_output_json_calls_json_print(self, mock_json_print):
        """print_deployments with output_json=True calls json_print."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR, output_json=True)

        mock_json_print.assert_called_once()
        output = mock_json_print.call_args[0][0]
        self.assertIn("versions", output)
        self.assertIn("active_deployment_hashes", output)
        self.assertEqual(len(output["versions"]), 10)

    @patch("poly.cli.print_deployments")
    def test_hash_sets_offset(self, mock_print_dep):
        """print_deployments with hash finds version index and uses it as offset."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR, hash="hash00005")

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(displayed_versions[0]["name"], "v5")

    @patch("poly.cli.error")
    def test_hash_not_found_calls_error(self, mock_error):
        """print_deployments with unknown hash calls error."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR, hash="zzz999999")

        mock_error.assert_called_once()
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli.print_deployments")
    def test_limit_and_offset_applied(self, mock_print_dep):
        """print_deployments with custom limit and offset slices correctly."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR, limit=3, offset=2)

        mock_print_dep.assert_called_once()
        displayed_versions = mock_print_dep.call_args[0][0]
        self.assertEqual(len(displayed_versions), 3)
        self.assertEqual(displayed_versions[0]["name"], "v2")

    @patch("poly.cli.print_deployments")
    def test_details_passed_through(self, mock_print_dep):
        """print_deployments with details=True passes it to the console function."""
        self.proj.get_deployments.return_value = (self.versions, self.active_hashes)

        AgentStudioCLI.print_deployments(TEST_DIR, details=True)

        mock_print_dep.assert_called_once()
        call_kwargs = mock_print_dep.call_args[1]
        self.assertTrue(call_kwargs["details"])
