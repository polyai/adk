"""Tests for the `poly onboard` command.

Copyright PolyAI Limited
"""

import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from poly.cli_commands.base import GETTING_STARTED_GROUP
from poly.cli_commands.onboard import OnboardCommand
from poly.utils.env_profile import EnvVarConflict, ProfileTarget

FAKE_JWT = "jwt-1"
FAKE_KEY = "sk-newkey1234567890"
FAKE_ACCOUNT = "acc-1"
FAKE_ANON_ID = "anon-fixed"


class OnboardTestCase(unittest.TestCase):
    """Base class wiring up the standard set of onboard collaborator mocks."""

    def setUp(self):
        # Never touch the real ~/.poly or depend on the host's $SHELL.
        os.environ.pop("DO_NOT_TRACK", None)
        os.environ.pop("POLY_NO_TELEMETRY", None)
        patchers = {
            "signin": patch(
                "poly.cli_commands.onboard.signin_with_device_flow", return_value=FAKE_JWT
            ),
            "authorise": patch(
                "poly.cli_commands.onboard.AgentStudioInterface.authorise"
            ),
            "get_accounts": patch(
                "poly.cli_commands.onboard.AgentStudioInterface.get_accounts_internal",
                return_value=[{"id": FAKE_ACCOUNT}],
            ),
            "list_keys": patch(
                "poly.cli_commands.onboard.AgentStudioInterface.list_account_api_keys_internal",
                return_value=[],
            ),
            "create_key": patch(
                "poly.cli_commands.onboard.AgentStudioInterface.create_account_api_key_internal",
                return_value={"key": FAKE_KEY},
            ),
            "load_cred": patch(
                "poly.cli_commands.onboard.load_api_key_from_credential_file",
                return_value=None,
            ),
            "save_cred": patch("poly.cli_commands.onboard.save_api_key_credential_file"),
            "write_env": patch(
                "poly.cli_commands.onboard.write_env_var",
                return_value=(
                    ProfileTarget(path=Path("/home/user/.zshrc"), shell="zsh"),
                    'export POLY_API_KEY="sk-n****7890"',
                ),
            ),
            "get_anonymous_id": patch(
                "poly.cli_commands.onboard.get_anonymous_id", return_value=FAKE_ANON_ID
            ),
            "detect_profile": patch(
                "poly.cli_commands.onboard.detect_profile",
                return_value=ProfileTarget(path=Path("/home/user/.zshrc"), shell="zsh"),
            ),
            "capture_event": patch("poly.cli_commands.onboard.capture_event"),
            "flush": patch("poly.cli_commands.onboard.flush"),
            "alias": patch("poly.cli_commands.onboard._alias_to_account"),
            "sleep": patch("poly.cli_commands.onboard.time.sleep"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

    def _failed_events(self):
        """The properties dict of every onboard_failed capture_event call."""
        return [
            call.args[2]
            for call in self.mocks["capture_event"].call_args_list
            if call.args[1] == "onboard_failed"
        ]

    def _event_names(self):
        return [call.args[1] for call in self.mocks["capture_event"].call_args_list]


class HappyPath(OnboardTestCase):
    """Tests for the successful onboard flow."""

    def test_creates_key_and_writes_env(self):
        """No existing key: a new one is created and POLY_API_KEY is written."""
        OnboardCommand.onboard()

        self.mocks["create_key"].assert_called_once()
        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=False)
        self.assertIn("onboard_key_created", self._event_names())
        self.assertIn("onboard_completed", self._event_names())

    def test_existing_studio_credential_is_not_overwritten(self):
        """An existing credential-file entry for studio is left untouched."""
        self.mocks["load_cred"].return_value = "already-there"

        OnboardCommand.onboard()

        self.mocks["save_cred"].assert_not_called()

    def test_reuse_path_emits_key_reused(self):
        """A matching existing key is reused instead of creating a new one."""
        with patch(
            "poly.cli_commands.onboard.select_reusable_api_key", return_value="sk-existing"
        ):
            OnboardCommand.onboard()

        self.mocks["create_key"].assert_not_called()
        self.assertIn("onboard_key_reused", self._event_names())

    def test_account_id_flag_skips_the_poll(self):
        """--account-id bypasses polling GET /jupiter/v2/accounts entirely."""
        OnboardCommand.onboard(account_id="acc-given")

        self.mocks["get_accounts"].assert_not_called()
        account_resolved = next(
            call.args[2]
            for call in self.mocks["capture_event"].call_args_list
            if call.args[1] == "onboard_account_resolved"
        )
        self.assertEqual(account_resolved["account_id"], "acc-given")

    def test_key_value_never_appears_in_stdout(self):
        """The real API key is never printed, masked or otherwise, in plain output."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            OnboardCommand.onboard()

        self.assertNotIn(FAKE_KEY, buffer.getvalue())

    def test_anonymous_id_not_created_when_telemetry_disabled(self):
        """DO_NOT_TRACK=1 skips get_anonymous_id entirely - no ~/.poly/telemetry_id touched."""
        with patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            OnboardCommand.onboard()

        self.mocks["get_anonymous_id"].assert_not_called()

    def test_json_output_has_expected_keys_and_masked_value(self):
        """--json prints one object with the documented fields and a masked key only."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            OnboardCommand.onboard(output_json=True)

        payload = json.loads(buffer.getvalue())
        self.assertTrue(payload["success"])
        for key in (
            "account_id",
            "key_name",
            "key_reused",
            "api_key_masked",
            "credentials_file",
            "profile_path",
            "profile_shell",
        ):
            self.assertIn(key, payload)
        self.assertNotIn(FAKE_KEY, buffer.getvalue())

    def test_json_output_has_no_rich_markup(self):
        """The masked key in --json output is plain text, not `[yellow]...[/yellow]` markup."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            OnboardCommand.onboard(output_json=True)

        self.assertNotIn("[", buffer.getvalue())


class AccountPollFailure(OnboardTestCase):
    """Tests for the no-account-appeared failure path."""

    def test_empty_accounts_after_20_tries_fails_with_exit_1(self):
        """20 empty polls without --account-id exits 1 with an onboard_failed(step=account)."""
        self.mocks["get_accounts"].return_value = []

        with self.assertRaises(SystemExit) as ctx:
            OnboardCommand.onboard()

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(self.mocks["get_accounts"].call_count, 20)
        failed = self._failed_events()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["step"], "account")


class EnvConflict(OnboardTestCase):
    """Tests for the POLY_API_KEY conflict path."""

    def test_conflict_exits_2_without_force(self):
        """A conflicting existing value exits 2 and reports the env step."""
        self.mocks["write_env"].side_effect = EnvVarConflict(
            "old****", "new****", Path("/home/user/.zshrc")
        )

        with self.assertRaises(SystemExit) as ctx:
            OnboardCommand.onboard()

        self.assertEqual(ctx.exception.code, 2)
        failed = self._failed_events()
        self.assertEqual(failed[0]["step"], "env")
        self.assertEqual(failed[0]["error_class"], "EnvVarConflict")

    def test_json_error_matches_the_documented_contract(self):
        """--json failures include success/error/traceback/step, with no Rich markup."""
        self.mocks["write_env"].side_effect = EnvVarConflict(
            "old****", "new****", Path("/home/user/.zshrc")
        )
        buffer = io.StringIO()

        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                OnboardCommand.onboard(output_json=True)

        payload = json.loads(buffer.getvalue())
        self.assertFalse(payload["success"])
        self.assertEqual(payload["step"], "env")
        self.assertIn("traceback", payload)
        self.assertTrue(payload["traceback"])
        self.assertNotIn("[", buffer.getvalue())

    def test_force_is_forwarded_to_write_env_var(self):
        """--force is passed straight through to write_env_var."""
        OnboardCommand.onboard(force=True)

        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=True)


class Verbose(OnboardTestCase):
    """Tests for --verbose re-raising instead of exiting cleanly."""

    def test_verbose_reraises_instead_of_exiting(self):
        """With verbose=True, the original exception propagates (for a full traceback)."""
        self.mocks["get_accounts"].return_value = []

        with self.assertRaises(ValueError):
            OnboardCommand.onboard(verbose=True)


class CommandRegistration(unittest.TestCase):
    """Tests that the command is wired into the CLI's Getting started group."""

    def test_command_name_and_group(self):
        self.assertEqual(OnboardCommand.command, "onboard")
        self.assertEqual(OnboardCommand.group, GETTING_STARTED_GROUP)

    def test_registered_in_cli_commands(self):
        from poly.cli import COMMANDS

        self.assertIn(OnboardCommand, COMMANDS)


if __name__ == "__main__":
    unittest.main()
