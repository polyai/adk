"""Tests for the `poly apikey` command.

Copyright PolyAI Limited
"""

import contextlib
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from poly.cli_commands.apikey import ApiKeyCommand
from poly.cli_commands.base import GETTING_STARTED_GROUP
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS, REGION_TO_AUTH_DETAILS
from poly.utils.env_profile import EnvVarConflict, ProfileTarget

FAKE_JWT = "jwt-1"
FAKE_KEY = "sk-newkey1234567890"
FAKE_ACCOUNT = "acc-1"
FAKE_ANON_ID = "anon-fixed"


class ApiKeyTestCase(unittest.TestCase):
    """Base class wiring up the standard set of apikey collaborator mocks."""

    def setUp(self):
        # Never touch the real ~/.poly or depend on the host's $SHELL.
        os.environ.pop("DO_NOT_TRACK", None)
        os.environ.pop("POLY_NO_TELEMETRY", None)
        patchers = {
            "signin": patch(
                "poly.cli_commands.apikey.signin_with_device_flow", return_value=FAKE_JWT
            ),
            "authorise": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.authorise"
            ),
            "get_accounts": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.get_accounts_internal",
                return_value=[{"id": FAKE_ACCOUNT}],
            ),
            "get_accounts_static": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.get_accounts",
                return_value={FAKE_ACCOUNT: "Account One"},
            ),
            "list_keys": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.list_account_api_keys_internal",
                return_value=[],
            ),
            "create_key": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.create_account_api_key_internal",
                return_value={"key": FAKE_KEY},
            ),
            "load_cred": patch(
                "poly.cli_commands.apikey.load_api_key_from_credential_file",
                return_value=None,
            ),
            "save_cred": patch("poly.cli_commands.apikey.save_api_key_credential_file"),
            "write_env": patch(
                "poly.cli_commands.apikey.write_env_var",
                return_value=(
                    ProfileTarget(path=Path("/home/user/.zshrc"), shell="zsh"),
                    'export POLY_API_KEY="sk-n****7890"',
                ),
            ),
            "get_anonymous_id": patch(
                "poly.handlers.posthog.get_anonymous_id", return_value=FAKE_ANON_ID
            ),
            "detect_profile": patch(
                "poly.cli_commands.apikey.detect_profile",
                return_value=ProfileTarget(path=Path("/home/user/.zshrc"), shell="zsh"),
            ),
            "capture_event": patch("poly.handlers.posthog.capture_event"),
            "flush": patch("poly.handlers.posthog.flush"),
            "alias": patch("poly.cli_commands.apikey._alias_to_account"),
            "sleep": patch("poly.cli_commands.apikey.time.sleep"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)

    def _failed_events(self):
        """The properties dict of every apikey_failed capture_event call."""
        return [
            call.args[2]
            for call in self.mocks["capture_event"].call_args_list
            if call.args[1] == "apikey_failed"
        ]

    def _event_names(self):
        return [call.args[1] for call in self.mocks["capture_event"].call_args_list]


class HappyPath(ApiKeyTestCase):
    """Tests for the successful apikey flow."""

    def test_creates_key_and_writes_env(self):
        """No existing key: a new one is created and POLY_API_KEY is written."""
        ApiKeyCommand.apikey()

        self.mocks["create_key"].assert_called_once()
        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=False)
        self.assertIn("apikey_key_created", self._event_names())
        self.assertIn("apikey_completed", self._event_names())

    def test_existing_studio_credential_is_not_overwritten(self):
        """An existing credential-file entry for studio is left untouched."""
        self.mocks["load_cred"].return_value = "already-there"

        ApiKeyCommand.apikey()

        self.mocks["save_cred"].assert_not_called()

    def test_reuse_path_emits_key_reused(self):
        """A matching existing key is reused instead of creating a new one."""
        with patch(
            "poly.cli_commands.apikey.select_reusable_api_key", return_value="sk-existing"
        ):
            ApiKeyCommand.apikey()

        self.mocks["create_key"].assert_not_called()
        self.assertIn("apikey_key_reused", self._event_names())

    def test_account_id_flag_skips_the_poll(self):
        """--account-id bypasses polling GET /jupiter/v2/accounts entirely."""
        ApiKeyCommand.apikey(account_id="acc-given")

        self.mocks["get_accounts"].assert_not_called()
        account_resolved = next(
            call.args[2]
            for call in self.mocks["capture_event"].call_args_list
            if call.args[1] == "apikey_account_resolved"
        )
        self.assertEqual(account_resolved["account_id"], "acc-given")

    def test_key_value_never_appears_in_stdout(self):
        """The real API key is never printed, masked or otherwise, in plain output."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey()

        self.assertNotIn(FAKE_KEY, buffer.getvalue())

    def test_anonymous_id_not_created_when_telemetry_disabled(self):
        """DO_NOT_TRACK=1 skips get_anonymous_id entirely - no ~/.poly/telemetry_id touched."""
        with patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            ApiKeyCommand.apikey()

        self.mocks["get_anonymous_id"].assert_not_called()

    def test_json_output_has_expected_keys_and_masked_value(self):
        """--json prints one object with the documented fields and a masked key only."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey(output_json=True)

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
            ApiKeyCommand.apikey(output_json=True)

        self.assertNotIn("[", buffer.getvalue())

    def test_json_mode_prints_verification_url_to_stderr(self):
        """--json still surfaces the sign-in URL/code - on stderr, since stdout is JSON-only."""
        verification_uri = "https://login.studio.poly.ai/activate?user_code=ABCD-EFGH"

        def fake_signin(auth_details, *, on_verification_url=None, **kwargs):
            on_verification_url(verification_uri, "ABCD-EFGH")
            return FAKE_JWT

        self.mocks["signin"].side_effect = fake_signin

        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            ApiKeyCommand.apikey(output_json=True)

        self.assertIn(verification_uri, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["success"])


class RegionSelection(ApiKeyTestCase):
    """Tests for --region's effect on sign-in, key naming, and region threading."""

    def test_default_region_signs_in_via_github_only_client(self):
        """With no --region, sign-in uses the studio GitHub-only client."""
        ApiKeyCommand.apikey()

        auth_details = self.mocks["signin"].call_args.args[0]
        self.assertIs(auth_details, APIKEY_AUTH_DETAILS)

    def test_non_studio_region_signs_in_via_standard_client(self):
        """--region us-1 uses the same Auth0 app `poly login --region us-1` uses."""
        ApiKeyCommand.apikey(region="us-1")

        auth_details = self.mocks["signin"].call_args.args[0]
        self.assertIs(auth_details, REGION_TO_AUTH_DETAILS["us-1"])

    def test_default_key_name_for_studio(self):
        """The default key name for studio is unchanged."""
        ApiKeyCommand.apikey()

        self.mocks["create_key"].assert_called_once_with(
            region="studio",
            jwt_token=FAKE_JWT,
            account_id=FAKE_ACCOUNT,
            name="cli-generated-key",
            source="apikey",
        )

    def test_default_key_name_for_other_region_is_suffixed(self):
        """The default key name for a non-studio region is disambiguated by region."""
        ApiKeyCommand.apikey(region="us-1")

        self.mocks["create_key"].assert_called_once_with(
            region="us-1",
            jwt_token=FAKE_JWT,
            account_id=FAKE_ACCOUNT,
            name="cli-generated-key-us-1",
            source="apikey",
        )

    def test_explicit_key_name_overrides_the_region_default(self):
        """--key-name wins over the region-based default regardless of region."""
        ApiKeyCommand.apikey(region="us-1", key_name="my-key")

        self.mocks["create_key"].assert_called_once_with(
            region="us-1",
            jwt_token=FAKE_JWT,
            account_id=FAKE_ACCOUNT,
            name="my-key",
            source="apikey",
        )

    def test_region_is_threaded_into_account_and_credentials_calls(self):
        """The chosen region reaches get_accounts_internal and the credentials file."""
        ApiKeyCommand.apikey(region="us-1")

        self.mocks["get_accounts"].assert_called_once_with(
            region="us-1", jwt_token=FAKE_JWT, source="apikey"
        )
        self.mocks["save_cred"].assert_called_once_with(FAKE_KEY, region="us-1")

    def test_region_is_threaded_into_telemetry(self):
        """capture_event receives the chosen region, not a hardcoded 'studio'."""
        ApiKeyCommand.apikey(region="us-1")

        regions = {call.args[0] for call in self.mocks["capture_event"].call_args_list}
        self.assertEqual(regions, {"us-1"})


class AccountPollFailure(ApiKeyTestCase):
    """Tests for the no-account-appeared failure path."""

    def test_empty_accounts_after_20_tries_fails_with_exit_1(self):
        """20 empty polls without --account-id exits 1 with an apikey_failed(step=account)."""
        self.mocks["get_accounts"].return_value = []

        with self.assertRaises(SystemExit) as ctx:
            ApiKeyCommand.apikey()

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(self.mocks["get_accounts"].call_count, 20)
        failed = self._failed_events()
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]["step"], "account")


class KeyActivationWait(ApiKeyTestCase):
    """Tests for the post-credentials key-activation poll."""

    def test_activates_on_third_poll(self):
        """The command completes normally once the key activates partway through the poll."""
        self.mocks["get_accounts_static"].side_effect = [
            Exception("not active"),
            Exception("not active"),
            {FAKE_ACCOUNT: "Account One"},
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            ApiKeyCommand.apikey()

        self.assertEqual(self.mocks["get_accounts_static"].call_count, 3)
        self.mocks["write_env"].assert_called_once()

    def test_never_activates_still_completes_and_warns(self):
        """20 failed polls print a warning but do not fail the command or emit telemetry."""
        self.mocks["get_accounts_static"].side_effect = Exception("not active")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ApiKeyCommand.apikey()

        self.assertEqual(self.mocks["get_accounts_static"].call_count, 20)
        self.mocks["write_env"].assert_called_once()
        self.assertIn("not active yet", stdout.getvalue())
        self.assertNotIn("apikey_failed", self._event_names())


class EnvConflict(ApiKeyTestCase):
    """Tests for the POLY_API_KEY conflict path."""

    def test_conflict_exits_2_without_force(self):
        """A conflicting existing value exits 2 and reports the env step."""
        self.mocks["write_env"].side_effect = EnvVarConflict(
            "old****", "new****", Path("/home/user/.zshrc")
        )

        with self.assertRaises(SystemExit) as ctx:
            ApiKeyCommand.apikey()

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
                ApiKeyCommand.apikey(output_json=True)

        payload = json.loads(buffer.getvalue())
        self.assertFalse(payload["success"])
        self.assertEqual(payload["step"], "env")
        self.assertIn("traceback", payload)
        self.assertTrue(payload["traceback"])
        self.assertNotIn("[", buffer.getvalue())

    def test_force_is_forwarded_to_write_env_var(self):
        """--force is passed straight through to write_env_var."""
        ApiKeyCommand.apikey(force=True)

        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=True)


class Verbose(ApiKeyTestCase):
    """Tests for --verbose re-raising instead of exiting cleanly."""

    def test_verbose_reraises_instead_of_exiting(self):
        """With verbose=True, the original exception propagates (for a full traceback)."""
        self.mocks["get_accounts"].return_value = []

        with self.assertRaises(ValueError):
            ApiKeyCommand.apikey(verbose=True)


class ArgParsing(unittest.TestCase):
    """Tests for apikey's own argparse wiring."""

    def test_force_short_alias(self):
        """-f is accepted as a short alias for --force, matching other commands."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(["apikey", "-f"])

        self.assertTrue(args.force)

    def test_region_defaults_to_studio(self):
        """With no --region flag, args.region is 'studio' - the individual-dev path."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(["apikey"])

        self.assertEqual(args.region, "studio")

    def test_region_accepts_a_production_region(self):
        """--region us-1 is accepted, matching poly login's region choices."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(["apikey", "--region", "us-1"])

        self.assertEqual(args.region, "us-1")


class CommandRegistration(unittest.TestCase):
    """Tests that the command is wired into the CLI's Getting started group."""

    def test_command_name_and_group(self):
        self.assertEqual(ApiKeyCommand.command, "apikey")
        self.assertEqual(ApiKeyCommand.group, GETTING_STARTED_GROUP)

    def test_registered_in_cli_commands(self):
        from poly.cli import COMMANDS

        self.assertIn(ApiKeyCommand, COMMANDS)


if __name__ == "__main__":
    unittest.main()
