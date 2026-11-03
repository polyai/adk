"""Tests for the onboarding flow: ``poly setup``, skill installation, auth, and telemetry.

Covers ``poly.cli_commands.setup``, ``poly.cli_commands.skills``, the
region/API-key-activation behaviour of ``poly.cli_commands.auth``, and the
``poly.setup`` modules (caller detection and the setup events).

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
)
from poly.cli_commands.setup import COMPLETION_MARKER, SetupCommand
from poly.cli_commands.skills import (
    SKILLS_NPX_PACKAGE,
    SKILLS_SOURCE,
    install_skills,
    node_gate_reason,
    update_skills,
)
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS
from poly.setup.agents import (
    detect_entry,
    detect_installed_agents,
    detect_invoking_agent,
)
from poly.setup.telemetry import SetupRun, StepResult, detect_mode
from poly.utils.apikey_session import CachedSession
from poly.utils.env_profile import EnvVarConflict, ProfileTarget


def _parse_setup_args(argv: list[str]):
    """Parse a ``poly setup ...`` command line with the real CLI parser."""
    cli = AgentStudioCLI()
    cli.register_commands()
    return cli._create_parser().parse_args(argv)


def _silence_telemetry(test: unittest.TestCase) -> MagicMock:
    """Keep a full ``setup()`` run off the network; returns the capture mock."""
    capture = patch("poly.setup.telemetry.capture_event", return_value=True).start()
    patch("poly.setup.telemetry.alias_identity", return_value=True).start()
    test.addCleanup(patch.stopall)
    return capture


def _events(capture: MagicMock, name: str) -> list[dict]:
    """The properties of every captured event called ``name``, in order."""
    return [call.args[2] for call in capture.call_args_list if call.args[1] == name]


JWT = "jwt-token"
CACHED_JWT = "jwt-cached"
STORED_ACCOUNT = {"key": "sk-stored", "account_id": "acc-stored", "name": "setup-key"}
PROFILE = ProfileTarget(path=Path("/home/u/.zshrc"), shell="zsh")


def _cached_session(token: str = CACHED_JWT) -> CachedSession:
    import time

    now = int(time.time())
    return CachedSession(token, now + 55 * 60, now - 5 * 60)


def _mock_auth(test: unittest.TestCase) -> dict[str, MagicMock]:
    """Patch every collaborator of the setup auth and environment steps.

    The default state is a machine with no credentials, no kept sign-in, one
    account and no existing keys, at a terminal. Tests adjust the mocks for the
    other fixtures: ADK key only, account key only, both.
    """
    api = MagicMock()
    api.get_accounts_internal.return_value = [{"id": "acc-1", "name": "Acme"}]
    api.list_account_api_keys_internal.return_value = []
    api.create_account_api_key_internal.return_value = {"key": "sk-minted"}
    api.get_accounts_with_key.return_value = {"acc-1": "Acme"}
    api.get_projects_with_key.return_value = {"proj-1": "Agent One", "proj-2": "Agent Two"}
    prefix = "poly.cli_commands.setup."
    patchers = {
        "retrieve_api_key": patch(prefix + "retrieve_api_key", side_effect=ValueError("none")),
        "stored_regions": patch(prefix + "regions_with_stored_keys", return_value=[]),
        "load_account": patch(prefix + "load_account_key_credential", return_value=None),
        "save_account": patch(prefix + "save_account_key_credential"),
        "session_load": patch(prefix + "apikey_session.load", return_value=None),
        "session_save": patch(prefix + "apikey_session.save"),
        "session_clear": patch(prefix + "apikey_session.clear"),
        "signin": patch(prefix + "_signin", return_value=JWT),
        "select_region": patch(prefix + "_select_region", return_value="studio"),
        "save_key": patch(prefix + "_authenticate_and_save_key", return_value={"acc-1": "Acme"}),
        "authorise": patch(prefix + "authorise_or_explain"),
        "interface": patch(prefix + "AgentStudioInterface", return_value=api),
        "any_credentials": patch(prefix + "any_credentials_exist", return_value=False),
        "detect_profile": patch(prefix + "detect_profile", return_value=PROFILE),
        "read_env": patch(prefix + "read_env_var", return_value=None),
        "write_env": patch(
            prefix + "write_env_var", return_value=(PROFILE, 'export POLY_API_KEY="sk-m****nted"')
        ),
        "confirm": patch("questionary.confirm"),
        "pick_account": patch(prefix + "pick_account", return_value="acc-picked"),
        "stdin": patch("sys.stdin"),
    }
    mocks = {name: p.start() for name, p in patchers.items()}
    mocks["api"] = api
    mocks["confirm"].return_value.ask.return_value = True
    mocks["stdin"].isatty.return_value = True
    test.addCleanup(patch.stopall)
    return mocks


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
    """Tests for the authentication step of ``poly setup``: one sign-in, both credentials.

    Each test runs the full setup sequence in a throwaway directory that already
    contains a project.yaml and under an unrecognised shell, so the completion,
    skills, and project steps skip themselves and only auth (and the
    POLY_API_KEY export it feeds) is exercised.
    """

    def setUp(self):
        self.base_path = tempfile.mkdtemp()
        Path(self.base_path, "project.yaml").write_text("projectId: proj-1\n", encoding="utf-8")
        self.addCleanup(shutil.rmtree, self.base_path, True)
        patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"}).start()
        self.m = _mock_auth(self)
        self.capture = _silence_telemetry(self)
        self.alias = patch("poly.setup.telemetry.alias_identity", return_value=True).start()

    def _run_setup(self, **kwargs) -> None:
        """Run setup with the skills step disabled unless a test opts in."""
        kwargs.setdefault("skip_skills", True)
        SetupCommand.setup(base_path=self.base_path, **kwargs)

    def _have_adk_key(self, region: str = "studio") -> None:
        self.m["retrieve_api_key"].side_effect = None
        self.m["retrieve_api_key"].return_value = "adk-key"
        self.m["stored_regions"].return_value = [region]
        self.m["any_credentials"].return_value = True

    def _have_account_key(self) -> None:
        self.m["load_account"].return_value = dict(STORED_ACCOUNT)

    def test_skip_auth_never_signs_in_or_exports(self):
        """--skip-auth leaves credentials untouched and has no key to export."""
        self._run_setup(skip_auth=True)

        self.m["signin"].assert_not_called()
        self.m["save_key"].assert_not_called()
        self.m["api"].create_account_api_key_internal.assert_not_called()
        self.m["write_env"].assert_not_called()

    def test_no_credentials_signs_in_once_and_mints_both(self):
        """A clean machine ends with an ADK key and a setup-key account key."""
        self._run_setup(region="studio")

        self.m["signin"].assert_called_once_with("studio", auth_details=APIKEY_AUTH_DETAILS)
        self.m["session_save"].assert_called_once_with("studio", JWT)
        self.m["save_key"].assert_called_once_with(JWT, region="studio")
        self.m["api"].create_account_api_key_internal.assert_called_once_with(
            region="studio", jwt_token=JWT, account_id="acc-1", name="setup-key", source="setup"
        )
        self.m["save_account"].assert_called_once_with("studio", "sk-minted", "acc-1", "setup-key")
        self.m["write_env"].assert_called_once_with("POLY_API_KEY", "sk-minted")
        self.alias.assert_called_once()
        self.assertEqual(self.alias.call_args.args[2], "acc-1")

    def test_adk_key_only_gains_the_account_key_without_a_new_sign_in(self):
        """A kept sign-in is enough: no browser, no PAT work, just the account key."""
        self._have_adk_key()
        self.m["session_load"].return_value = _cached_session()

        self._run_setup()

        self.m["signin"].assert_not_called()
        self.m["save_key"].assert_not_called()
        self.m["authorise"].assert_called_once()
        self.assertEqual(self.m["authorise"].call_args.args[2], CACHED_JWT)
        self.m["api"].create_account_api_key_internal.assert_called_once()
        self.m["save_account"].assert_called_once_with("studio", "sk-minted", "acc-1", "setup-key")

    def test_adk_key_only_without_a_kept_sign_in_signs_in_once(self):
        self._have_adk_key()

        self._run_setup()

        self.m["signin"].assert_called_once()
        self.m["save_key"].assert_not_called()
        self.m["api"].create_account_api_key_internal.assert_called_once()

    def test_account_key_only_signs_in_and_adds_the_adk_key(self):
        """The stored account key is kept and exported; only the PAT is minted."""
        self._have_account_key()

        self._run_setup(region="studio")

        self.m["signin"].assert_called_once()
        self.m["save_key"].assert_called_once_with(JWT, region="studio")
        self.m["api"].create_account_api_key_internal.assert_not_called()
        self.m["save_account"].assert_not_called()
        self.m["write_env"].assert_called_once_with("POLY_API_KEY", "sk-stored")
        self.assertEqual(self.alias.call_args.args[2], "acc-stored")

    def test_both_credentials_skip_sign_in_and_still_export(self):
        """A configured machine signs in for nothing and keeps its identity."""
        self._have_adk_key()
        self._have_account_key()

        self._run_setup()

        self.m["signin"].assert_not_called()
        self.m["authorise"].assert_not_called()
        self.m["save_key"].assert_not_called()
        self.m["api"].list_account_api_keys_internal.assert_not_called()
        self.m["write_env"].assert_called_once_with("POLY_API_KEY", "sk-stored")
        self.assertEqual(self.alias.call_args.args[2], "acc-stored")

    def test_region_is_inferred_from_the_single_stored_adk_key(self):
        self._have_adk_key("uk-1")

        self._run_setup()

        self.m["select_region"].assert_not_called()
        self.m["signin"].assert_called_once_with("uk-1", auth_details=None)

    def test_several_stored_regions_prompt_for_one(self):
        self._have_adk_key()
        self.m["stored_regions"].return_value = ["studio", "us-1"]
        self.m["select_region"].return_value = "us-1"

        self._run_setup()

        self.m["select_region"].assert_called_once()
        self.m["signin"].assert_called_once_with("us-1", auth_details=None)

    def test_explicit_region_is_used_without_prompting(self):
        """--region signs in to that region on its standard client and skips the picker."""
        self._run_setup(region="us-1")

        self.m["select_region"].assert_not_called()
        self.m["signin"].assert_called_once_with("us-1", auth_details=None)
        self.m["save_key"].assert_called_once_with(JWT, region="us-1")
        self.m["api"].create_account_api_key_internal.assert_called_once()
        self.assertEqual(
            self.m["api"].create_account_api_key_internal.call_args.kwargs["name"], "setup-key-us-1"
        )

    def test_missing_region_is_prompted_for_and_threaded_through(self):
        """Without --region the user picks one, and that choice is used to sign in."""
        self.m["select_region"].return_value = "uk-1"

        self._run_setup()

        self.m["select_region"].assert_called_once()
        self.m["signin"].assert_called_once_with("uk-1", auth_details=None)
        self.m["save_key"].assert_called_once_with(JWT, region="uk-1")

    def test_existing_cli_generated_key_is_reused_instead_of_created(self):
        self.m["api"].list_account_api_keys_internal.return_value = [
            {"key": "sk-cli", "active": True, "policies": [{"name": "cli-generated-key"}]}
        ]

        self._run_setup(region="studio")

        self.m["api"].create_account_api_key_internal.assert_not_called()
        self.m["save_account"].assert_called_once_with(
            "studio", "sk-cli", "acc-1", "cli-generated-key"
        )

    def test_account_id_flag_skips_the_account_lookup(self):
        self._run_setup(region="studio", account_id="acc-flag")

        self.m["api"].get_accounts_internal.assert_not_called()
        self.m["save_account"].assert_called_once_with(
            "studio", "sk-minted", "acc-flag", "setup-key"
        )

    def test_several_accounts_at_a_terminal_use_the_picker(self):
        self.m["api"].get_accounts_internal.return_value = [{"id": "acc-1"}, {"id": "acc-2"}]

        self._run_setup(region="studio")

        self.m["pick_account"].assert_called_once()
        self.m["save_account"].assert_called_once_with(
            "studio", "sk-minted", "acc-picked", "setup-key"
        )

    @patch("poly.output.console.error")
    def test_several_accounts_without_a_terminal_stop_and_list_them(self, mock_error):
        self.m["api"].get_accounts_internal.return_value = [{"id": "acc-1"}, {"id": "acc-2"}]
        self.m["stdin"].isatty.return_value = False

        with self.assertRaises(SystemExit) as ctx:
            self._run_setup(region="studio")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("--account-id", mock_error.call_args[0][0])
        self.m["pick_account"].assert_not_called()
        self.m["save_account"].assert_not_called()

    def test_refused_kept_sign_in_is_cleared_and_signed_in_again(self):
        """A revoked cached token costs one extra sign-in, not a failed run."""
        import requests

        self._have_adk_key()
        self.m["session_load"].return_value = _cached_session()
        response = MagicMock(status_code=401)
        self.m["authorise"].side_effect = [requests.HTTPError(response=response), {}]

        self._run_setup()

        self.m["session_clear"].assert_called_once_with("studio")
        self.m["signin"].assert_called_once()
        self.assertEqual(self.m["authorise"].call_args.args[2], JWT)
        self.m["api"].create_account_api_key_internal.assert_called_once()

    def test_refused_fresh_sign_in_propagates(self):
        import requests

        self._have_adk_key()
        response = MagicMock(status_code=401)
        self.m["authorise"].side_effect = requests.HTTPError(response=response)

        with self.assertRaises(requests.HTTPError):
            self._run_setup()

        self.m["session_clear"].assert_not_called()

    @patch("poly.output.console.error")
    def test_unprovisioned_enterprise_user_exits_with_the_message(self, mock_error):
        self._have_adk_key("us-1")
        self.m["authorise"].side_effect = ValueError("No account is provisioned for you on us-1.")

        with self.assertRaises(SystemExit):
            self._run_setup()

        self.assertIn("No account is provisioned", mock_error.call_args[0][0])

    @patch("poly.output.console.warning")
    def test_key_that_never_activates_warns_but_setup_continues(self, mock_warning):
        self.m["api"].get_accounts_with_key.side_effect = RuntimeError("401")
        with patch("poly.auth.account_key.time.sleep"):
            self._run_setup(region="studio")

        self.assertIn("not active yet", mock_warning.call_args[0][0])
        self.m["write_env"].assert_called_once()


def _unauthorized() -> requests.HTTPError:
    """The error make_request raises when the gateway answers 401."""
    response = requests.Response()
    response.status_code = 401
    return requests.HTTPError("401 Client Error: Unauthorized", response=response)


class SetupVerifyStepTest(unittest.TestCase):
    """Tests for SetupCommand._verify, the one call that proves the account key."""

    def setUp(self):
        self.m = _mock_auth(self)
        self.step = StepResult()

    def _verify(self, api_key="sk-minted", account_id="acc-1", skip_verify=False):
        return SetupCommand._verify(api_key, "studio", account_id, skip_verify, self.step)

    @patch("poly.output.console.success")
    def test_calls_the_public_api_with_the_key_and_reports_the_account(self, mock_success):
        self.assertTrue(self._verify())

        self.m["api"].get_projects_with_key.assert_called_once_with("studio", "sk-minted", "acc-1")
        message = mock_success.call_args[0][0]
        self.assertIn("acc-1", message)
        self.assertIn("2 agents", message)
        self.assertRegex(message, r"\d+ ms")
        self.assertEqual(self.step.outcome, "done")

    @patch("poly.output.console.success")
    def test_one_agent_is_singular(self, mock_success):
        self.m["api"].get_projects_with_key.return_value = {"proj-1": "Agent One"}

        self._verify()

        self.assertIn("1 agent,", mock_success.call_args[0][0])

    def test_skip_flag_makes_no_call(self):
        self.assertIsNone(self._verify(skip_verify=True))

        self.m["api"].get_projects_with_key.assert_not_called()
        self.assertEqual(self.step.outcome, "skipped")

    def test_no_key_makes_no_call(self):
        self.assertIsNone(self._verify(api_key=None))

        self.m["api"].get_projects_with_key.assert_not_called()
        self.assertEqual(self.step.outcome, "skipped")

    @patch("poly.output.console.error")
    def test_refused_key_ends_the_run_before_any_write(self, mock_error):
        self.m["api"].get_projects_with_key.side_effect = RuntimeError("401 Unauthorized")

        with self.assertRaises(SystemExit) as ctx:
            self._verify()

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("poly apikey --region studio", mock_error.call_args[0][0])
        self.assertNotIn("sk-minted", mock_error.call_args[0][0])
        self.assertEqual((self.step.outcome, self.step.error_class), ("failed", "RuntimeError"))

    @patch("poly.cli_commands.setup.time.sleep")
    @patch("poly.output.console.info")
    @patch("poly.output.console.success")
    def test_a_key_not_active_yet_is_retried_until_the_gateway_accepts_it(
        self, mock_success, mock_info, mock_sleep
    ):
        """The gateway can take a few seconds to know a freshly minted key."""
        self.m["api"].get_projects_with_key.side_effect = [
            _unauthorized(),
            _unauthorized(),
            {"proj-1": "Agent One"},
        ]

        self.assertTrue(self._verify())

        self.assertEqual(self.m["api"].get_projects_with_key.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        notices = [c[0][0] for c in mock_info.call_args_list if "not active yet" in c[0][0]]
        self.assertEqual(len(notices), 1)
        self.assertIn("1 agent,", mock_success.call_args[0][0])
        self.assertEqual(self.step.outcome, "done")

    @patch("poly.cli_commands.setup.time.sleep")
    @patch("poly.output.console.error")
    def test_a_key_still_refused_after_the_retry_window_ends_the_run(self, mock_error, mock_sleep):
        self.m["api"].get_projects_with_key.side_effect = _unauthorized()
        clock = iter(range(0, 100, 5))  # one tick per monotonic() read, past the window
        with patch("poly.cli_commands.setup.time.monotonic", side_effect=lambda: next(clock)):
            with self.assertRaises(SystemExit) as ctx:
                self._verify()

        self.assertEqual(ctx.exception.code, 1)
        self.assertGreater(self.m["api"].get_projects_with_key.call_count, 1)
        self.assertIn("refused", mock_error.call_args[0][0])

    @patch("poly.cli_commands.setup.time.sleep")
    def test_a_non_auth_error_is_not_retried(self, mock_sleep):
        self.m["api"].get_projects_with_key.side_effect = RuntimeError("connection reset")

        with patch("poly.output.console.error"), self.assertRaises(SystemExit):
            self._verify()

        self.m["api"].get_projects_with_key.assert_called_once()
        mock_sleep.assert_not_called()

    @patch("poly.output.console.error")
    def test_refused_key_in_a_full_run_writes_nothing_and_records_failed(self, mock_error):
        """The profile and later steps are never reached with a key that does not work."""
        base_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_path, True)
        patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"}).start()
        capture = _silence_telemetry(self)
        self.m["api"].get_projects_with_key.side_effect = RuntimeError("401 Unauthorized")

        with self.assertRaises(SystemExit):
            SetupCommand.setup(base_path=base_path, region="studio", skip_skills=True)

        self.m["write_env"].assert_not_called()
        steps = [(e["step"], e["outcome"]) for e in _events(capture, "setup_step")]
        self.assertEqual(steps[-1], ("verify", "failed"))
        # The cause, not the SystemExit that ended the run, is what the funnel sees.
        self.assertEqual(_events(capture, "setup_step")[-1]["error_class"], "RuntimeError")
        self.assertEqual(_events(capture, "setup_completed"), [])

    def test_skip_verify_flag_is_parsed_and_forwarded(self):
        args = _parse_setup_args(["setup", "--skip-verify"])

        self.assertTrue(args.skip_verify)
        with patch.object(SetupCommand, "setup") as mock_setup:
            SetupCommand.run(args)
        self.assertTrue(mock_setup.call_args.kwargs["skip_verify"])


class SetupEnvironmentStepTest(unittest.TestCase):
    """Tests for SetupCommand._export_account_key, the confirmed POLY_API_KEY write."""

    def setUp(self):
        self.m = _mock_auth(self)
        self.step = StepResult()

    def _export(self, api_key="sk-minted"):
        SetupCommand._export_account_key(api_key, "studio", self.step)

    def test_no_key_skips_without_touching_the_profile(self):
        self._export(None)

        self.assertEqual(self.step.outcome, "skipped")
        self.m["read_env"].assert_not_called()
        self.m["confirm"].assert_not_called()

    def test_value_already_in_the_profile_skips_without_asking(self):
        self.m["read_env"].return_value = "sk-minted"

        self._export()

        self.assertEqual(self.step.outcome, "skipped")
        self.m["confirm"].assert_not_called()
        self.m["write_env"].assert_not_called()

    @patch("poly.output.console.info")
    def test_no_terminal_skips_and_names_the_later_command(self, mock_info):
        self.m["stdin"].isatty.return_value = False

        self._export()

        self.assertEqual(self.step.outcome, "skipped")
        self.assertIn("poly apikey --region studio", mock_info.call_args[0][0])
        self.m["write_env"].assert_not_called()

    def test_confirmation_names_the_profile_and_writes_on_yes(self):
        self._export()

        self.assertIn(str(PROFILE.path), self.m["confirm"].call_args.args[0])
        self.m["write_env"].assert_called_once_with("POLY_API_KEY", "sk-minted")
        self.assertEqual(self.step.outcome, "done")

    def test_declining_writes_nothing(self):
        self.m["confirm"].return_value.ask.return_value = False

        self._export()

        self.m["write_env"].assert_not_called()
        self.assertEqual(self.step.outcome, "declined")

    @patch("poly.output.console.warning")
    def test_conflicting_value_fails_the_step_with_the_force_hint(self, mock_warning):
        self.m["write_env"].side_effect = EnvVarConflict("sk-o****ld", "sk-m****ted", PROFILE.path)

        self._export()

        self.assertEqual((self.step.outcome, self.step.error_class), ("failed", "EnvVarConflict"))
        self.assertIn("--force", mock_warning.call_args[0][0])


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
        self.capture = _silence_telemetry(self)

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

    def test_status_file_without_project_yaml_skips_the_project_step(self):
        """A checkout reconstructable from the status file alone is a project too."""
        status_path = Path(self.base_path, "_gen", ".agent_studio_config")
        status_path.parent.mkdir()
        status_path.write_bytes(b"eyJwcm9qZWN0X2lkIjogInByb2otMSJ9")

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


class SetupTelemetryWiringTest(unittest.TestCase):
    """Tests that a ``poly setup`` run emits the started, per-step and completed events.

    Runs the full sequence in a throwaway directory under an unrecognised shell
    with the skills step skipped, so the outcomes are deterministic.
    """

    def setUp(self):
        self.base_path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.base_path, True)
        patch.dict(os.environ, {"SHELL": "/bin/unrecognised-shell"}).start()
        self.m = _mock_auth(self)
        self.mock_signin = self.m["signin"]
        self.mock_select = patch("questionary.select").start()
        self.mock_select.return_value.ask.return_value = "skip"
        patch("poly.setup.telemetry.detect_installed_agents", return_value=["cursor"]).start()
        patch("poly.setup.telemetry.has_node", return_value=False).start()
        # The suite itself may run under a coding agent; pin the caller facts.
        patch("poly.setup.telemetry.detect_invoking_agent", return_value="none").start()
        self.capture = _silence_telemetry(self)
        self.alias = patch("poly.setup.telemetry.alias_identity", return_value=True).start()

    def _run_setup(self, **kwargs) -> None:
        kwargs.setdefault("skip_skills", True)
        kwargs.setdefault("region", "studio")
        SetupCommand.setup(base_path=self.base_path, **kwargs)

    def test_started_event_carries_the_machine_facts_and_no_arguments(self):
        """setup_started names the entry, OS, version, agents and prior state only."""
        self._run_setup()

        [started] = _events(self.capture, "setup_started")
        self.assertEqual(
            set(started),
            {
                "entry",
                "os",
                "adk_version",
                "invoking_agent",
                "agents_detected",
                "had_credentials",
                "has_node",
                "mode",
            },
        )
        self.assertEqual(started["agents_detected"], ["cursor"])
        self.assertFalse(started["had_credentials"])
        self.assertFalse(started["has_node"])
        self.assertEqual(started["mode"], "human")

    def test_every_step_reports_an_outcome_in_order(self):
        """A fresh sign-in with everything else skipped or declined records each step."""
        self._run_setup()

        steps = [(e["step"], e["outcome"]) for e in _events(self.capture, "setup_step")]
        self.assertEqual(
            steps,
            [
                ("signin", "done"),
                ("credentials", "done"),
                ("verify", "done"),
                ("environment", "done"),
                ("completion", "skipped"),
                ("skills", "skipped"),
                ("project", "declined"),
            ],
        )
        for event in _events(self.capture, "setup_step"):
            self.assertIsInstance(event["duration_ms"], int)
            self.assertNotIn("error_class", event)

    def test_existing_credentials_report_both_auth_steps_as_skipped(self):
        """The auth skip still records signin and credentials, so funnels stay comparable."""
        self.m["any_credentials"].return_value = True
        self.m["retrieve_api_key"].side_effect = None
        self.m["retrieve_api_key"].return_value = "adk-key"
        self.m["load_account"].return_value = dict(STORED_ACCOUNT)

        self._run_setup()

        steps = [(e["step"], e["outcome"]) for e in _events(self.capture, "setup_step")]
        self.assertEqual(steps[:2], [("signin", "skipped"), ("credentials", "skipped")])
        [started] = _events(self.capture, "setup_started")
        self.assertTrue(started["had_credentials"])
        self.assertEqual(self.capture.call_args.args[3], "acc-stored")

    def test_single_account_sign_in_switches_identity_to_the_account(self):
        """Events before sign-in use an anonymous id; after it, the account id, aliased."""
        self._run_setup()

        distinct_ids = [call.args[3] for call in self.capture.call_args_list]
        self.assertTrue(distinct_ids[0].startswith("anon:"))
        self.assertEqual(distinct_ids[-1], "acc-1")
        self.alias.assert_called_once_with("studio", distinct_ids[0], "acc-1")

    def test_picked_account_becomes_the_identity(self):
        """With several accounts, the one chosen at the picker keys the run."""
        self.m["api"].get_accounts_internal.return_value = [{"id": "acc-1"}, {"id": "acc-2"}]

        self._run_setup()

        self.alias.assert_called_once()
        self.assertEqual(self.alias.call_args.args[2], "acc-picked")
        self.assertEqual(self.capture.call_args.args[3], "acc-picked")

    def test_completed_event_lists_done_steps_and_the_project_choice(self):
        """setup_completed summarises the run for the funnel's last tile."""
        self._run_setup()

        [completed] = _events(self.capture, "setup_completed")
        self.assertEqual(
            completed["steps_done"], ["signin", "credentials", "verify", "environment"]
        )
        self.assertEqual(completed["project"], "declined")
        self.assertTrue(completed["verify_ok"])
        self.assertIsInstance(completed["duration_ms"], int)

    def test_created_project_is_reported_as_created(self):
        """Choosing 'create' marks the project step done with the created detail."""
        self.mock_select.return_value.ask.return_value = "create"
        with patch("poly.cli_commands.setup.ProjectCommand.create_project"):
            self._run_setup()

        [completed] = _events(self.capture, "setup_completed")
        self.assertEqual(completed["project"], "created")
        self.assertIn("project", completed["steps_done"])

    def test_sign_in_failure_records_the_step_as_failed_and_propagates(self):
        """A failing step is reported with its error class; no completed event follows."""
        self.mock_signin.side_effect = RuntimeError("device flow timed out")

        with self.assertRaises(RuntimeError):
            self._run_setup()

        [signin] = _events(self.capture, "setup_step")
        self.assertEqual(signin["outcome"], "failed")
        self.assertEqual(signin["error_class"], "RuntimeError")
        self.assertEqual(_events(self.capture, "setup_completed"), [])

    def test_no_event_carries_a_key_value_or_a_path(self):
        """Key values, file paths and command arguments must never leave the machine."""
        self._run_setup()

        for call in self.capture.call_args_list:
            flat = str(call.args[2])
            self.assertNotIn(self.base_path, flat)
            self.assertNotIn("jwt", flat)
            self.assertNotIn("sk-", flat)
            self.assertNotIn(str(PROFILE.path), flat)


class DetectInvokingAgentTest(unittest.TestCase):
    """Tests for agents.detect_invoking_agent, the env-marker lookup."""

    def test_no_marker_means_no_agent(self):
        self.assertEqual(detect_invoking_agent({}), "none")

    def test_each_marker_names_its_agent(self):
        """Every known marker maps to its canonical agent name."""
        cases = {"CLAUDECODE": "claude-code", "CURSOR_AGENT": "cursor", "CODEX_SANDBOX": "codex"}
        for marker, agent in cases.items():
            with self.subTest(marker=marker):
                self.assertEqual(detect_invoking_agent({marker: "1"}), agent)

    def test_empty_marker_counts_as_unset(self):
        self.assertEqual(detect_invoking_agent({"CLAUDECODE": ""}), "none")


class DetectInstalledAgentsTest(unittest.TestCase):
    """Tests for agents.detect_installed_agents, which looks for config directories."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, True)
        patch("poly.setup.agents.shutil.which", return_value=None).start()
        patch("poly.setup.agents.platform.system", return_value="Linux").start()
        self.addCleanup(patch.stopall)

    def test_empty_home_finds_nothing(self):
        self.assertEqual(detect_installed_agents(self.home), [])

    def test_config_directories_identify_agents_in_a_fixed_order(self):
        """Directories are reported in one order whatever order they were created in."""
        (self.home / ".codex").mkdir()
        (self.home / ".claude").mkdir()
        (self.home / ".config" / "Claude").mkdir(parents=True)

        self.assertEqual(
            detect_installed_agents(self.home), ["claude-code", "codex", "claude-desktop"]
        )

    def test_claude_binary_on_path_counts_without_a_directory(self):
        with patch("poly.setup.agents.shutil.which", return_value="/usr/local/bin/claude"):
            self.assertEqual(detect_installed_agents(self.home), ["claude-code"])

    def test_claude_desktop_uses_the_macos_application_support_directory(self):
        (self.home / "Library" / "Application Support" / "Claude").mkdir(parents=True)
        with patch("poly.setup.agents.platform.system", return_value="Darwin"):
            self.assertEqual(detect_installed_agents(self.home), ["claude-desktop"])


class DetectEntryTest(unittest.TestCase):
    """Tests for agents.detect_entry, which tells a uvx run from an installed poly."""

    def test_uv_cache_prefix_is_uvx(self):
        with patch("poly.setup.agents.sys.prefix", "/home/u/.cache/uv/archive-v0/abc123"):
            self.assertEqual(detect_entry(), "uvx")

    def test_windows_uv_cache_prefix_is_uvx(self):
        prefix = "C:\\Users\\u\\AppData\\Local\\uv\\cache\\archive-v0\\abc123"
        with patch("poly.setup.agents.sys.prefix", prefix):
            self.assertEqual(detect_entry(), "uvx")

    def test_tool_install_prefix_is_poly(self):
        with patch("poly.setup.agents.sys.prefix", "/home/u/.local/share/uv/tools/polyai-adk"):
            self.assertEqual(detect_entry(), "poly")


class DetectModeTest(unittest.TestCase):
    """Tests for telemetry.detect_mode."""

    def test_terminal_without_agent_marker_is_human(self):
        with (
            patch("poly.setup.telemetry.detect_invoking_agent", return_value="none"),
            patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = True
            self.assertEqual(detect_mode(), "human")

    def test_agent_marker_is_agent_even_on_a_terminal(self):
        with (
            patch("poly.setup.telemetry.detect_invoking_agent", return_value="claude-code"),
            patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = True
            self.assertEqual(detect_mode(), "agent")

    def test_piped_stdin_is_agent(self):
        with (
            patch("poly.setup.telemetry.detect_invoking_agent", return_value="none"),
            patch("sys.stdin") as stdin,
        ):
            stdin.isatty.return_value = False
            self.assertEqual(detect_mode(), "agent")


class SetupRunTest(unittest.TestCase):
    """Tests for telemetry.SetupRun, the per-invocation event recorder."""

    def setUp(self):
        self.capture = patch("poly.setup.telemetry.capture_event", return_value=True).start()
        self.alias = patch("poly.setup.telemetry.alias_identity", return_value=True).start()
        self.addCleanup(patch.stopall)
        self.run = SetupRun(region="studio", mode="agent")

    def test_step_defaults_to_done_and_times_the_block(self):
        with self.run.step("verify"):
            pass

        [event] = _events(self.capture, "setup_step")
        self.assertEqual(event["step"], "verify")
        self.assertEqual(event["outcome"], "done")
        self.assertGreaterEqual(event["duration_ms"], 0)

    def test_step_records_skipped_declined_and_explicit_failures(self):
        """The block fills in the outcome; explicit failures carry their class."""
        with self.run.step("a") as step:
            step.skipped()
        with self.run.step("b") as step:
            step.declined()
        with self.run.step("c") as step:
            step.failed("npx_failed")

        outcomes = [(e["step"], e["outcome"]) for e in _events(self.capture, "setup_step")]
        self.assertEqual(outcomes, [("a", "skipped"), ("b", "declined"), ("c", "failed")])
        self.assertEqual(_events(self.capture, "setup_step")[2]["error_class"], "npx_failed")

    def test_system_exit_inside_a_step_is_recorded_and_re_raised(self):
        """Commands exit with sys.exit(1) on failure; that must still be a failed step."""
        with self.assertRaises(SystemExit):
            with self.run.step("credentials"):
                raise SystemExit(1)

        [event] = _events(self.capture, "setup_step")
        self.assertEqual(event["outcome"], "failed")
        self.assertEqual(event["error_class"], "SystemExit")

    def test_identify_aliases_once_and_switches_the_distinct_id(self):
        anonymous = self.run.distinct_id

        self.run.identify("acc-1")
        self.run.identify("acc-1")
        with self.run.step("x"):
            pass

        self.alias.assert_called_once_with("studio", anonymous, "acc-1")
        self.assertEqual(self.capture.call_args.args[3], "acc-1")

    def test_identify_with_no_account_is_a_no_op(self):
        anonymous = self.run.distinct_id

        self.run.identify("")

        self.alias.assert_not_called()
        self.assertEqual(self.run.distinct_id, anonymous)

    def test_first_failed_send_disables_the_rest_of_the_run(self):
        """One timeout must not become one per event on a bad network."""
        self.capture.return_value = False

        with self.run.step("a"):
            pass
        with self.run.step("b"):
            pass
        self.run.completed()

        self.assertEqual(self.capture.call_count, 1)

    def test_completed_reports_done_steps_and_the_project_detail(self):
        with self.run.step("signin"):
            pass
        with self.run.step("skills") as step:
            step.skipped()
        with self.run.step("project") as step:
            step.done("connected")

        self.run.completed()

        [completed] = _events(self.capture, "setup_completed")
        self.assertEqual(completed["steps_done"], ["signin", "project"])
        self.assertEqual(completed["project"], "connected")

    def test_completed_omits_project_when_the_step_had_no_detail(self):
        with self.run.step("project") as step:
            step.skipped()

        self.run.completed()

        [completed] = _events(self.capture, "setup_completed")
        self.assertNotIn("project", completed)

    def test_helpers_without_a_step_record_still_work(self):
        """The setup helpers accept no record when called on their own."""
        result = StepResult()
        result.skipped("because")
        self.assertEqual((result.outcome, result.detail), ("skipped", "because"))


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

        _silence_telemetry(self)
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
