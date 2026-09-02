"""Tests for the onboarding flow: ``poly setup``, skill installation, and auth.

Covers ``poly.cli_commands.setup``, ``poly.cli_commands.skills``, and the
region/API-key-activation behaviour of ``poly.cli_commands.auth``.

Copyright PolyAI Limited
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from poly.cli import AgentStudioCLI
from poly.cli_commands.auth import (
    LoginCommand,
    _authenticate_and_save_key,
    _select_region,
    _signin,
)
from poly.cli_commands.setup import COMPLETION_MARKER, SetupCommand
from poly.cli_commands.skills import (
    SKILLS_NPX_PACKAGE,
    SKILLS_SOURCE,
    install_skills,
    node_gate_reason,
    update_skills,
)


def _parse_setup_args(argv: list[str]):
    """Parse a ``poly setup ...`` command line with the real CLI parser."""
    cli = AgentStudioCLI()
    cli.register_commands()
    return cli._create_parser().parse_args(argv)


class NodeGateReasonTest(unittest.TestCase):
    """Tests for skills.node_gate_reason, the guard around the npx skills step."""

    def test_missing_node_on_path_reports_node_not_found(self):
        """With no node binary, the reason names Node.js rather than a version."""
        with patch("poly.cli_commands.skills.shutil.which", return_value=None):
            reason = node_gate_reason()

        self.assertEqual(reason, "Node.js (with npx) was not found on your PATH")

    def test_missing_npx_on_path_reports_node_not_found(self):
        """node without npx is still unusable, so the step is gated."""
        with patch(
            "poly.cli_commands.skills.shutil.which",
            side_effect=lambda binary: "/usr/bin/node" if binary == "node" else None,
        ):
            reason = node_gate_reason()

        self.assertEqual(reason, "Node.js (with npx) was not found on your PATH")

    def test_unparseable_version_output_reports_unknown_version(self):
        """Output that is not a version string is treated as undeterminable."""
        with (
            patch("poly.cli_commands.skills.shutil.which", return_value="/usr/bin/node"),
            patch(
                "poly.cli_commands.skills.subprocess.run",
                return_value=MagicMock(stdout="not-a-version\n"),
            ),
        ):
            reason = node_gate_reason()

        self.assertEqual(reason, "the Node.js version could not be determined")

    def test_node_version_command_failure_reports_unknown_version(self):
        """A node --version that fails to run is reported as undeterminable, not raised."""
        with (
            patch("poly.cli_commands.skills.shutil.which", return_value="/usr/bin/node"),
            patch(
                "poly.cli_commands.skills.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="node", timeout=10),
            ),
        ):
            reason = node_gate_reason()

        self.assertEqual(reason, "the Node.js version could not be determined")

    def test_node_major_below_minimum_reports_too_old(self):
        """Node 16 is below the supported minimum, so the reason names the version."""
        with (
            patch("poly.cli_commands.skills.shutil.which", return_value="/usr/bin/node"),
            patch(
                "poly.cli_commands.skills.subprocess.run",
                return_value=MagicMock(stdout="v16.20.2\n"),
            ),
        ):
            reason = node_gate_reason()

        self.assertEqual(reason, "Node.js 16 is too old (Node 18+ is required)")

    def test_supported_node_version_returns_no_reason(self):
        """A modern Node install means there is nothing blocking the skills step."""
        with (
            patch("poly.cli_commands.skills.shutil.which", return_value="/usr/bin/node"),
            patch(
                "poly.cli_commands.skills.subprocess.run",
                return_value=MagicMock(stdout="v20.11.0\n"),
            ),
        ):
            reason = node_gate_reason()

        self.assertIsNone(reason)


class InstallSkillsTest(unittest.TestCase):
    """Tests for skills.install_skills command construction and failure handling."""

    def setUp(self):
        self.run_patcher = patch("poly.cli_commands.skills.subprocess.run")
        self.mock_run = self.run_patcher.start()
        self.mock_run.return_value = MagicMock(returncode=0)
        self.addCleanup(self.run_patcher.stop)

    def _command(self) -> list[str]:
        """Return the argv list passed to subprocess.run."""
        return self.mock_run.call_args[0][0]

    def test_defaults_install_published_source_into_current_project(self):
        """With no options, skills are added from the published ADK repo."""
        installed = install_skills()

        self.assertTrue(installed)
        self.assertEqual(
            self._command(),
            ["npx", "-y", SKILLS_NPX_PACKAGE, "add", SKILLS_SOURCE, "-y"],
        )

    def test_explicit_source_replaces_the_published_repo(self):
        """A local path passed as source is used instead of the published repo."""
        install_skills(source="./skills")

        self.assertEqual(
            self._command(),
            ["npx", "-y", SKILLS_NPX_PACKAGE, "add", "./skills", "-y"],
        )

    def test_global_install_adds_global_flag(self):
        """global_install=True installs user-level via the --global flag."""
        install_skills(global_install=True)

        self.assertEqual(self._command()[-1], "--global")

    def test_agents_are_passed_after_a_single_agent_flag(self):
        """Multiple agents are passed as one --agent flag followed by each name."""
        install_skills(agents=["claude-code", "cursor"])

        self.assertEqual(
            self._command(),
            ["npx", "-y", SKILLS_NPX_PACKAGE, "add", SKILLS_SOURCE, "-y", "--agent"]
            + ["claude-code", "cursor"],
        )

    def test_non_zero_exit_reports_failure(self):
        """A failing npx run returns False rather than raising."""
        self.mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(install_skills())

    def test_subprocess_error_reports_failure_without_raising(self):
        """An npx binary that cannot be executed is reported as a failed install."""
        self.mock_run.side_effect = FileNotFoundError("npx not found")

        self.assertFalse(install_skills())

    def test_timeout_reports_failure_without_raising(self):
        """A hung npx run times out and is reported as a failed install."""
        self.mock_run.side_effect = subprocess.TimeoutExpired(cmd="npx", timeout=600)

        self.assertFalse(install_skills())


class UpdateSkillsTest(unittest.TestCase):
    """Tests for skills.update_skills command construction."""

    def setUp(self):
        self.run_patcher = patch("poly.cli_commands.skills.subprocess.run")
        self.mock_run = self.run_patcher.start()
        self.mock_run.return_value = MagicMock(returncode=0)
        self.addCleanup(self.run_patcher.stop)

    def test_update_runs_npx_skills_update(self):
        """update_skills runs the pinned package's update subcommand."""
        updated = update_skills()

        self.assertTrue(updated)
        self.assertEqual(
            self.mock_run.call_args[0][0],
            ["npx", "-y", SKILLS_NPX_PACKAGE, "update", "-y"],
        )

    def test_global_only_adds_global_flag(self):
        """global_only=True restricts the update to user-level installs."""
        update_skills(global_only=True)

        self.assertEqual(self.mock_run.call_args[0][0][-1], "--global")

    def test_non_zero_exit_reports_failure(self):
        """A failing update returns False rather than raising."""
        self.mock_run.return_value = MagicMock(returncode=1)

        self.assertFalse(update_skills())


class SetupAuthStepTest(unittest.TestCase):
    """Tests for the authentication step of ``poly setup``.

    Each test runs the full setup sequence in a throwaway directory that already
    contains a project.yaml and under an unrecognised shell, so the completion,
    skills, and project steps skip themselves and only auth is exercised.
    """

    def setUp(self):
        self.base_path = tempfile.mkdtemp()
        Path(self.base_path, "project.yaml").write_text("projectId: proj-1\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.base_path, True)

        env_patcher = patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.mock_signin = patch("poly.cli_commands.setup._signin").start()
        self.mock_signin.return_value = "jwt-token"
        self.mock_save_key = patch("poly.cli_commands.setup._authenticate_and_save_key").start()
        self.mock_select_region = patch("poly.cli_commands.setup._select_region").start()
        self.mock_select_region.return_value = "studio"
        self.mock_credentials = patch("poly.cli_commands.setup.any_credentials_exist").start()
        self.mock_credentials.return_value = False
        self.addCleanup(patch.stopall)

    def _run_setup(self, **kwargs) -> None:
        """Run setup with the skills step disabled unless a test opts in."""
        kwargs.setdefault("skip_skills", True)
        SetupCommand.setup(base_path=self.base_path, **kwargs)

    def test_skip_auth_never_signs_in(self):
        """--skip-auth leaves credentials untouched even when none exist."""
        self._run_setup(skip_auth=True)

        self.mock_signin.assert_not_called()
        self.mock_save_key.assert_not_called()

    def test_existing_credentials_skip_sign_in(self):
        """Re-running setup with credentials already saved does not sign in again."""
        self.mock_credentials.return_value = True

        self._run_setup()

        self.mock_signin.assert_not_called()
        self.mock_save_key.assert_not_called()

    def test_explicit_region_is_used_without_prompting(self):
        """--region signs in to that region and skips the interactive picker."""
        self._run_setup(region="us-1")

        self.mock_select_region.assert_not_called()
        self.mock_signin.assert_called_once_with("us-1")
        self.mock_save_key.assert_called_once_with("jwt-token", region="us-1")

    def test_missing_region_is_prompted_for_and_threaded_through(self):
        """Without --region the user picks one, and that choice is used to sign in."""
        self.mock_select_region.return_value = "uk-1"

        self._run_setup()

        self.mock_select_region.assert_called_once()
        self.mock_signin.assert_called_once_with("uk-1")
        self.mock_save_key.assert_called_once_with("jwt-token", region="uk-1")


class SetupSkillsStepTest(unittest.TestCase):
    """Tests for the AI-skills step of ``poly setup``."""

    def setUp(self):
        self.base_path = tempfile.mkdtemp()
        Path(self.base_path, "project.yaml").write_text("projectId: proj-1\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.base_path, True)

        env_patcher = patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.mock_gate = patch("poly.cli_commands.setup.node_gate_reason").start()
        self.mock_gate.return_value = None
        self.mock_install = patch("poly.cli_commands.setup.install_skills").start()
        self.mock_install.return_value = True
        self.addCleanup(patch.stopall)

    def _run_setup(self, **kwargs) -> None:
        """Run setup with authentication disabled so only the skills step runs."""
        SetupCommand.setup(base_path=self.base_path, skip_auth=True, **kwargs)

    def test_skip_skills_does_not_check_node_or_install(self):
        """--skip-skills short-circuits before the Node check."""
        self._run_setup(skip_skills=True)

        self.mock_gate.assert_not_called()
        self.mock_install.assert_not_called()

    @patch("poly.output.console.warning")
    def test_blocked_node_gate_skips_install_and_warns_with_the_reason(self, mock_warning):
        """When Node is unusable, the skills step warns and installs nothing."""
        self.mock_gate.return_value = "Node.js 16 is too old (Node 18+ is required)"

        self._run_setup()

        self.mock_install.assert_not_called()
        self.assertIn("too old", mock_warning.call_args[0][0])

    def test_default_run_installs_from_the_published_source(self):
        """A plain setup installs skills from the published repo into the project."""
        self._run_setup()

        self.mock_install.assert_called_once_with(source=None, global_install=False, agents=None)

    def test_dev_installs_from_the_local_skills_directory(self):
        """--dev points the installer at the working copy's ./skills directory."""
        self._run_setup(dev=True)

        self.assertEqual(self.mock_install.call_args[1]["source"], "./skills")

    def test_agents_and_global_flags_are_forwarded_to_the_installer(self):
        """--agent and --global reach install_skills unchanged."""
        self._run_setup(agents=["claude-code"], global_install=True)

        self.mock_install.assert_called_once_with(
            source=None, global_install=True, agents=["claude-code"]
        )

    @patch("poly.output.console.warning")
    def test_failed_install_warns_but_setup_still_completes(self, mock_warning):
        """A skills failure is non-fatal: setup finishes and suggests a re-run."""
        self.mock_install.return_value = False

        self._run_setup()

        self.assertIn("Re-run 'poly setup'", mock_warning.call_args[0][0])


class SetupCompletionInstallTest(unittest.TestCase):
    """Tests for SetupCommand._install_completion against a throwaway HOME."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

    def _install_with_shell(self, shell_path: str) -> None:
        """Run the completion step as if the user's shell were shell_path.

        Sets both HOME and USERPROFILE: ``Path.expanduser`` resolves ``~`` from
        HOME on POSIX but from USERPROFILE on Windows, and the throwaway home
        must win on either platform.
        """
        env = {"HOME": self.home, "USERPROFILE": self.home, "SHELL": shell_path}
        with patch.dict(os.environ, env):
            SetupCommand._install_completion()

    def test_bash_rc_gets_the_completion_eval_appended(self):
        """A bash user gets an eval line, tagged with the setup marker."""
        rc_path = Path(self.home, ".bashrc")
        rc_path.write_text("export EDITOR=vim\n", encoding="utf-8")

        self._install_with_shell("/bin/bash")

        contents = rc_path.read_text(encoding="utf-8")
        self.assertIn("export EDITOR=vim", contents)
        self.assertIn(COMPLETION_MARKER, contents)
        self.assertIn('eval "$(poly completion bash)"', contents)

    def test_zsh_rc_is_created_when_missing(self):
        """A zsh user with no .zshrc still gets completion configured."""
        self._install_with_shell("/bin/zsh")

        contents = Path(self.home, ".zshrc").read_text(encoding="utf-8")
        self.assertIn('eval "$(poly completion zsh)"', contents)

    def test_rerunning_setup_does_not_append_completion_twice(self):
        """The marker makes the completion step idempotent across re-runs."""
        self._install_with_shell("/bin/zsh")
        self._install_with_shell("/bin/zsh")

        contents = Path(self.home, ".zshrc").read_text(encoding="utf-8")
        self.assertEqual(contents.count('eval "$(poly completion zsh)"'), 1)

    def test_manually_configured_completion_is_left_alone(self):
        """An existing 'poly completion' line counts as configured, marker or not."""
        rc_path = Path(self.home, ".zshrc")
        rc_path.write_text("source <(poly completion zsh)\n", encoding="utf-8")

        self._install_with_shell("/bin/zsh")

        self.assertEqual(rc_path.read_text(encoding="utf-8"), "source <(poly completion zsh)\n")

    def test_fish_completion_file_is_written(self):
        """A fish user gets a completions file, with its parent directories created."""
        self._install_with_shell("/usr/local/bin/fish")

        completion_path = Path(self.home, ".config", "fish", "completions", "poly.fish")
        self.assertTrue(completion_path.exists())
        self.assertIn("poly", completion_path.read_text(encoding="utf-8"))

    def test_existing_fish_completion_file_is_not_overwritten(self):
        """An existing poly.fish is left as-is so user edits survive a re-run."""
        completion_path = Path(self.home, ".config", "fish", "completions", "poly.fish")
        completion_path.parent.mkdir(parents=True)
        completion_path.write_text("# hand written\n", encoding="utf-8")

        self._install_with_shell("/usr/local/bin/fish")

        self.assertEqual(completion_path.read_text(encoding="utf-8"), "# hand written\n")

    @patch("poly.output.console.info")
    def test_unrecognised_shell_writes_nothing_and_explains(self, mock_info):
        """An unsupported shell is reported with manual instructions, not a failure."""
        self._install_with_shell("/bin/unrecognised-shell")

        self.assertEqual(os.listdir(self.home), [])
        self.assertIn("poly completion --help", mock_info.call_args[0][0])

    @patch("poly.output.console.warning")
    def test_unreadable_rc_file_warns_instead_of_raising(self, mock_warning):
        """A .zshrc that cannot be read (here, a directory) must not abort setup."""
        Path(self.home, ".zshrc").mkdir()

        self._install_with_shell("/bin/zsh")

        self.assertIn("could not install automatically", mock_warning.call_args[0][0])


class SetupProjectStepTest(unittest.TestCase):
    """Tests for SetupCommand._setup_project."""

    def setUp(self):
        self.base_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base_path, True)

        self.mock_create = patch("poly.cli_commands.setup.ProjectCommand.create_project").start()
        self.mock_init = patch("poly.cli_commands.setup.InitCommand.init_project").start()
        self.mock_select = patch("questionary.select").start()
        self.mock_stdin = patch("sys.stdin").start()
        self.mock_stdin.isatty.return_value = True
        self.addCleanup(patch.stopall)

    def test_existing_project_yaml_skips_the_project_step(self):
        """Running setup inside an ADK project does not prompt to create another."""
        Path(self.base_path, "project.yaml").write_text("projectId: proj-1\n", encoding="utf-8")

        SetupCommand._setup_project(self.base_path, region="us-1")

        self.mock_select.assert_not_called()
        self.mock_create.assert_not_called()
        self.mock_init.assert_not_called()

    @patch("poly.output.console.info")
    def test_non_interactive_terminal_skips_the_prompt(self, mock_info):
        """Piped/CI runs cannot answer a prompt, so the step explains and skips."""
        self.mock_stdin.isatty.return_value = False

        SetupCommand._setup_project(self.base_path, region="us-1")

        self.mock_select.assert_not_called()
        self.assertIn("not an interactive terminal", mock_info.call_args[0][0])

    def test_choosing_create_creates_a_project_in_the_chosen_region(self):
        """Selecting 'create' delegates to project create with the setup region."""
        self.mock_select.return_value.ask.return_value = "create"

        SetupCommand._setup_project(self.base_path, region="us-1")

        self.mock_create.assert_called_once_with(self.base_path, region="us-1")
        self.mock_init.assert_not_called()

    def test_choosing_connect_inits_an_existing_project(self):
        """Selecting 'init' delegates to project init with the setup region."""
        self.mock_select.return_value.ask.return_value = "init"

        SetupCommand._setup_project(self.base_path, region="uk-1")

        self.mock_init.assert_called_once_with(self.base_path, region="uk-1")
        self.mock_create.assert_not_called()

    def test_choosing_skip_leaves_the_directory_untouched(self):
        """Selecting 'skip' creates and connects nothing."""
        self.mock_select.return_value.ask.return_value = "skip"

        SetupCommand._setup_project(self.base_path, region="us-1")

        self.mock_create.assert_not_called()
        self.mock_init.assert_not_called()
        self.assertEqual(os.listdir(self.base_path), [])


class SetupArgumentParsingTest(unittest.TestCase):
    """Tests for the ``poly setup`` command line."""

    def test_defaults_leave_every_step_enabled(self):
        """Bare 'poly setup' runs all steps against the current directory."""
        args = _parse_setup_args(["setup"])

        self.assertIsNone(args.region)
        self.assertIsNone(args.agents)
        self.assertFalse(args.skip_auth)
        self.assertFalse(args.skip_skills)
        self.assertFalse(args.dev)
        self.assertFalse(args.global_install)

    def test_repeated_agent_flags_accumulate(self):
        """--agent is repeatable and collects into a list in order."""
        args = _parse_setup_args(["setup", "--agent", "claude-code", "--agent", "cursor"])

        self.assertEqual(args.agents, ["claude-code", "cursor"])

    def test_global_long_and_short_flags_both_set_global_install(self):
        """--global and -g are the same switch."""
        self.assertTrue(_parse_setup_args(["setup", "--global"]).global_install)
        self.assertTrue(_parse_setup_args(["setup", "-g"]).global_install)

    def test_region_choice_is_validated_against_known_regions(self):
        """A known region parses; an unknown one is rejected by the parser."""
        self.assertEqual(_parse_setup_args(["setup", "--region", "us-1"]).region, "us-1")

        with self.assertRaises(SystemExit):
            _parse_setup_args(["setup", "--region", "mars-1"])

    @patch("poly.cli_commands.setup.install_skills", return_value=True)
    @patch("poly.cli_commands.setup.node_gate_reason", return_value=None)
    def test_parsed_flags_reach_the_skills_installer(self, _mock_gate, mock_install):
        """'poly setup --dev -g --agent claude-code' installs dev skills globally."""
        base_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_path, True)
        Path(base_path, "project.yaml").write_text("projectId: proj-1\n", encoding="utf-8")
        args = _parse_setup_args(
            ["setup", "--base-path", base_path, "--skip-auth", "--dev", "-g", "--agent", "cursor"]
        )

        with patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"}):
            SetupCommand.run(args)

        mock_install.assert_called_once_with(
            source="./skills", global_install=True, agents=["cursor"]
        )


class SelectRegionTest(unittest.TestCase):
    """Tests for the shared interactive region picker."""

    @patch("questionary.select")
    def test_offers_the_studio_and_enterprise_regions_with_studio_default(self, mock_select):
        """The picker lists studio plus the enterprise regions and defaults to studio."""
        mock_select.return_value.ask.return_value = "uk-1"

        selected = _select_region()

        self.assertEqual(selected, "uk-1")
        choices = mock_select.call_args.kwargs["choices"]
        self.assertEqual([choice.value for choice in choices], ["studio", "us-1", "uk-1", "euw-1"])
        self.assertEqual(mock_select.call_args.kwargs["default"], "studio")


class AuthenticateAndSaveKeyTest(unittest.TestCase):
    """Tests for auth._authenticate_and_save_key, including the activation poll."""

    def setUp(self):
        env_patcher = patch.dict(os.environ, {})
        env_patcher.start()
        self.addCleanup(env_patcher.stop)

        self.api = patch("poly.cli_commands.auth.AgentStudioInterface").start().return_value
        self.api.get_pats.return_value = [{"key": "existing-pat"}]
        self.api.create_pat.return_value = "new-pat"
        self.api.get_accounts.return_value = {"acc-1": "Account"}
        self.mock_save = patch("poly.cli_commands.auth.save_api_key_credential_file").start()
        patch("time.sleep").start()
        self.addCleanup(patch.stopall)

    def test_existing_key_is_reused_and_saved_for_the_region(self):
        """An account with a PAT already reuses it instead of creating another."""
        _authenticate_and_save_key("jwt-token", region="us-1")

        self.api.create_pat.assert_not_called()
        self.mock_save.assert_called_once_with("existing-pat", region="us-1")

    def test_account_without_a_key_gets_a_new_one_created(self):
        """With no PATs, a fresh adk-key is created and saved."""
        self.api.get_pats.return_value = []

        _authenticate_and_save_key("jwt-token", region="us-1")

        self.api.create_pat.assert_called_once_with(
            region="us-1", jwt_token="jwt-token", name="adk-key"
        )
        self.mock_save.assert_called_once_with("new-pat", region="us-1")

    def test_malformed_key_payload_exits(self):
        """A PAT entry without a key is unusable, so the command exits."""
        self.api.get_pats.return_value = [{"name": "adk-key"}]

        with self.assertRaises(SystemExit) as ctx:
            _authenticate_and_save_key("jwt-token", region="us-1")

        self.assertEqual(ctx.exception.code, 1)
        self.mock_save.assert_not_called()

    def test_polls_until_the_new_key_activates(self):
        """A key that is not active yet is retried until the platform accepts it."""
        self.api.get_accounts.side_effect = [
            Exception("401 unauthorized"),
            Exception("401 unauthorized"),
            {"acc-1": "Account"},
        ]

        _authenticate_and_save_key("jwt-token", region="us-1")

        self.assertEqual(self.api.get_accounts.call_count, 3)

    @patch("poly.output.console.warning")
    def test_key_that_never_activates_warns_but_does_not_exit(self, mock_warning):
        """A timed-out activation poll leaves the saved key in place and only warns."""
        self.api.get_accounts.side_effect = Exception("401 unauthorized")

        _authenticate_and_save_key("jwt-token", region="us-1")

        self.mock_save.assert_called_once_with("existing-pat", region="us-1")
        self.assertIn("not active yet", mock_warning.call_args[0][0])


class SigninDeviceFlowTest(unittest.TestCase):
    """Tests for auth._signin, the browser device flow shared by setup/start/login."""

    DEVICE_RESPONSE = {
        "user_code": "ABCD-EFGH",
        "verification_uri_complete": "https://example.test/activate?code=ABCD-EFGH",
        "device_code": "device-code",
        "interval": 5,
    }

    def setUp(self):
        self.auth0 = patch("poly.cli_commands.auth.Auth0Handler").start().return_value
        self.auth0.request_device_code.return_value = dict(self.DEVICE_RESPONSE)
        self.auth0.poll_device_token.return_value = {"access_token": "jwt-token"}
        self.mock_browser = patch("webbrowser.open").start()
        patch("time.sleep").start()
        self.addCleanup(patch.stopall)

    @staticmethod
    def _device_flow_error(error_code: str) -> requests.HTTPError:
        """Build the HTTPError Auth0 returns while a device code is outstanding."""
        response = MagicMock()
        response.json.return_value = {"error": error_code}
        return requests.HTTPError(error_code, response=response)

    def test_successful_authorization_returns_the_access_token(self):
        """A completed browser sign-in returns the JWT and opens the verification page."""
        token = _signin("us-1")

        self.assertEqual(token, "jwt-token")
        self.mock_browser.assert_called_once_with(self.DEVICE_RESPONSE["verification_uri_complete"])

    def test_pending_authorization_is_polled_until_the_user_finishes(self):
        """'authorization_pending' keeps polling rather than failing the sign-in."""
        self.auth0.poll_device_token.side_effect = [
            self._device_flow_error("authorization_pending"),
            {"access_token": "jwt-token"},
        ]

        self.assertEqual(_signin("us-1"), "jwt-token")
        self.assertEqual(self.auth0.poll_device_token.call_count, 2)

    def test_slow_down_response_keeps_polling(self):
        """'slow_down' backs the polling off instead of failing the sign-in."""
        self.auth0.poll_device_token.side_effect = [
            self._device_flow_error("slow_down"),
            {"access_token": "jwt-token"},
        ]

        self.assertEqual(_signin("us-1"), "jwt-token")
        self.assertEqual(self.auth0.poll_device_token.call_count, 2)

    def test_unknown_authorization_error_exits(self):
        """An unrecognised Auth0 error ends the sign-in."""
        self.auth0.poll_device_token.side_effect = self._device_flow_error("access_denied")

        with self.assertRaises(SystemExit) as ctx:
            _signin("us-1")

        self.assertEqual(ctx.exception.code, 1)

    def test_non_json_error_response_exits(self):
        """An HTTP error with an unparseable body ends the sign-in rather than crashing."""
        response = MagicMock()
        response.json.side_effect = ValueError("not json")
        self.auth0.poll_device_token.side_effect = requests.HTTPError(
            "502 Bad Gateway", response=response
        )

        with self.assertRaises(SystemExit) as ctx:
            _signin("us-1")

        self.assertEqual(ctx.exception.code, 1)

    def test_expired_device_code_exits(self):
        """An expired device code ends the command rather than polling forever."""
        self.auth0.poll_device_token.side_effect = self._device_flow_error("expired_token")

        with self.assertRaises(SystemExit) as ctx:
            _signin("us-1")

        self.assertEqual(ctx.exception.code, 1)

    def test_failure_to_start_authorization_exits(self):
        """If the device code request fails, sign-in exits instead of opening a browser."""
        self.auth0.request_device_code.side_effect = Exception("network down")

        with self.assertRaises(SystemExit) as ctx:
            _signin("us-1")

        self.assertEqual(ctx.exception.code, 1)
        self.mock_browser.assert_not_called()


class LoginCommandRegionTest(unittest.TestCase):
    """Tests for how ``poly login`` resolves its region."""

    def setUp(self):
        self.mock_signin = patch("poly.cli_commands.auth._signin").start()
        self.mock_signin.return_value = "jwt-token"
        self.mock_save_key = patch("poly.cli_commands.auth._authenticate_and_save_key").start()
        self.mock_select_region = patch("poly.cli_commands.auth._select_region").start()
        self.mock_select_region.return_value = "studio"
        patch("questionary.press_any_key_to_continue").start()
        self.addCleanup(patch.stopall)

    def test_explicit_region_skips_the_picker(self):
        """'poly login --region us-1' logs straight in to that region."""
        LoginCommand.login(region="us-1")

        self.mock_select_region.assert_not_called()
        self.mock_signin.assert_called_once_with("us-1")
        self.mock_save_key.assert_called_once_with("jwt-token", region="us-1")

    def test_run_forwards_the_parsed_region(self):
        """'poly login --region euw-1' reaches the login handler intact."""
        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(["login", "--region", "euw-1"])

        LoginCommand.run(args)

        self.mock_signin.assert_called_once_with("euw-1")

    def test_missing_region_uses_the_shared_picker(self):
        """'poly login' asks for a region using the same picker as setup and start."""
        self.mock_select_region.return_value = "uk-1"

        LoginCommand.login()

        self.mock_select_region.assert_called_once()
        self.mock_signin.assert_called_once_with("uk-1")
        self.mock_save_key.assert_called_once_with("jwt-token", region="uk-1")


if __name__ == "__main__":
    unittest.main()
