"""Tests for the `poly apikey` command.

Copyright PolyAI Limited
"""

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from poly.auth.device_flow import DeviceFlowError
from poly.cli_commands.apikey import NEXT_STEP_URL, ApiKeyCommand
from poly.cli_commands.base import GETTING_STARTED_GROUP
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS, REGION_TO_AUTH_DETAILS
from poly.utils.apikey_session import CachedSession
from poly.utils.env_profile import EnvVarConflict, ProfileTarget

# Distinctive, so a test can assert it never reaches any output.
FAKE_JWT = "jwt-fresh-5e1f0c7a"
CACHED_JWT = "jwt-cached-9b2d4e61"
FAKE_KEY = "sk-newkey1234567890"
FAKE_ACCOUNT = "acc-1"
ME = "me@x.com"


def _http_error(status: int) -> requests.HTTPError:
    """Build the HTTPError the platform handler raises for `status`."""
    response = MagicMock()
    response.status_code = status
    return requests.HTTPError(f"{status} Client Error", response=response)


def _cached(token: str = CACHED_JWT) -> CachedSession:
    """A cached sign-in saved 5 minutes ago that is good for another 55."""
    import time

    now = int(time.time())
    return CachedSession(token, now + 55 * 60, now - 5 * 60)


class ApiKeyTestCase(unittest.TestCase):
    """Base class wiring up the standard set of apikey collaborator mocks."""

    def setUp(self):
        # Never touch the real ~/.poly or depend on the host's $SHELL.
        patchers = {
            "signin": patch(
                "poly.cli_commands.apikey.signin_with_device_flow", return_value=FAKE_JWT
            ),
            "authorise": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.authorise",
                return_value={"user": {"is_first_login": False, "email": ME}},
            ),
            "capture_event": patch("poly.handlers.posthog.capture_event"),
            "get_accounts": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.get_accounts_internal",
                return_value=[{"id": FAKE_ACCOUNT}],
            ),
            "get_accounts_with_key": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.get_accounts_with_key",
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
            "sleep": patch("poly.cli_commands.apikey.time.sleep"),
            # Non-interactive by default: no test may block on a real prompt.
            "stdin": patch("poly.cli_commands.apikey.sys.stdin"),
            "select": patch("questionary.select"),
            # Nothing cached, and never touch the real ~/.poly/apikey_session.json.
            "session_load": patch(
                "poly.cli_commands.apikey.apikey_session.load", return_value=None
            ),
            "session_save": patch(
                "poly.cli_commands.apikey.apikey_session.save",
                side_effect=lambda region, token: _cached(token),
            ),
            "session_clear": patch("poly.cli_commands.apikey.apikey_session.clear"),
        }
        self.mocks = {name: p.start() for name, p in patchers.items()}
        for p in patchers.values():
            self.addCleanup(p.stop)
        self.mocks["stdin"].isatty.return_value = False

    def run_apikey(self, **kwargs) -> tuple[str, str, int | None]:
        """Run apikey and return (stdout, stderr, exit code or None)."""
        stdout, stderr = io.StringIO(), io.StringIO()
        code = None
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                ApiKeyCommand.apikey(**kwargs)
            except SystemExit as e:
                code = e.code
        return stdout.getvalue(), stderr.getvalue(), code


class HappyPath(ApiKeyTestCase):
    """Tests for the successful apikey flow."""

    def test_creates_key_and_writes_env(self):
        """No existing key: a new one is created and POLY_API_KEY is written."""
        ApiKeyCommand.apikey(region="studio")

        self.mocks["create_key"].assert_called_once()
        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=False)

    def test_existing_studio_credential_is_not_overwritten(self):
        """An existing credential-file entry for studio is left untouched."""
        self.mocks["load_cred"].return_value = "already-there"

        ApiKeyCommand.apikey(region="studio")

        self.mocks["save_cred"].assert_not_called()

    def test_reuse_path_does_not_create_new_key(self):
        """A matching existing key is reused instead of creating a new one."""
        with patch("poly.cli_commands.apikey.select_reusable_api_key", return_value="sk-existing"):
            ApiKeyCommand.apikey(region="studio")

        self.mocks["create_key"].assert_not_called()

    def test_account_id_flag_skips_the_poll(self):
        """--account-id bypasses polling GET /jupiter/v2/accounts entirely."""
        ApiKeyCommand.apikey(region="studio", account_id="acc-given")

        self.mocks["get_accounts"].assert_not_called()
        self.mocks["create_key"].assert_called_once_with(
            region="studio",
            jwt_token=FAKE_JWT,
            account_id="acc-given",
            name="cli-generated-key",
            source="apikey",
        )

    def test_key_value_never_appears_in_stdout(self):
        """The real API key is never printed, masked or otherwise, in plain output."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey(region="studio")

        self.assertNotIn(FAKE_KEY, buffer.getvalue())

    def test_json_output_has_expected_keys_and_masked_value(self):
        """--json prints one object with the documented fields and a masked key only."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey(region="studio", output_json=True)

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
            "key_active",
            "cli_version",
            "cli_path",
            "next_step_url",
        ):
            self.assertIn(key, payload)
        self.assertIs(payload["key_active"], True)
        self.assertNotIn(FAKE_KEY, buffer.getvalue())

    def test_json_output_has_no_rich_markup(self):
        """The masked key in --json output is plain text, not `[yellow]...[/yellow]` markup."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey(region="studio", output_json=True)

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
            ApiKeyCommand.apikey(region="studio", output_json=True)

        self.assertIn(verification_uri, stderr.getvalue())
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["success"])


class RegionSelection(ApiKeyTestCase):
    """Tests for --region's effect on sign-in, key naming, and region threading."""

    def test_studio_region_signs_in_via_github_only_client(self):
        """With --region studio, sign-in uses the studio GitHub-only client."""
        ApiKeyCommand.apikey(region="studio")

        auth_details = self.mocks["signin"].call_args.args[0]
        self.assertIs(auth_details, APIKEY_AUTH_DETAILS)

    def test_non_studio_region_signs_in_via_standard_client(self):
        """--region us-1 uses the same Auth0 app `poly login --region us-1` uses."""
        ApiKeyCommand.apikey(region="us-1")

        auth_details = self.mocks["signin"].call_args.args[0]
        self.assertIs(auth_details, REGION_TO_AUTH_DETAILS["us-1"])

    def test_default_key_name_for_studio(self):
        """The default key name for studio is unchanged."""
        ApiKeyCommand.apikey(region="studio")

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

    def _sign_in_message(self, **kwargs) -> str:
        """Run apikey and return the verification message printed to stdout."""

        def fake_signin(auth_details, *, on_verification_url=None, **_kwargs):
            on_verification_url("https://example.test/activate", "ABCD-EFGH")
            return FAKE_JWT

        self.mocks["signin"].side_effect = fake_signin
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            ApiKeyCommand.apikey(**kwargs)
        return buffer.getvalue()

    def test_studio_sign_in_message_names_github(self):
        """Studio's sign-in line still names GitHub explicitly."""
        message = self._sign_in_message(region="studio")

        self.assertIn("To sign in with GitHub, open the following link", message)

    def test_non_studio_sign_in_message_has_no_redundant_browser_mention(self):
        """A non-studio region's sign-in line doesn't say 'with your browser open ... in your browser'."""
        message = self._sign_in_message(region="us-1")

        self.assertIn("To sign in, open the following link", message)
        self.assertNotIn("with your browser", message)


class SignupEvent(ApiKeyTestCase):
    """Tests for the apikey_signup PostHog event fired on genuine first-time signup."""

    def test_studio_first_login_emits_signup(self):
        """A first login on studio fires apikey_signup for the resolved account."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": True}}

        ApiKeyCommand.apikey(region="studio")

        self.mocks["capture_event"].assert_called_once_with(
            "studio", "apikey_signup", {"source": "apikey"}, distinct_id=FAKE_ACCOUNT
        )

    def test_studio_returning_user_does_not_emit_signup(self):
        """A returning user on studio (is_first_login False) does not fire the event."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": False}}

        ApiKeyCommand.apikey(region="studio")

        self.mocks["capture_event"].assert_not_called()

    def test_studio_missing_is_first_login_key_does_not_emit_signup(self):
        """A response with no is_first_login key at all is treated as not-a-signup."""
        self.mocks["authorise"].return_value = {"user": {}}

        ApiKeyCommand.apikey(region="studio")

        self.mocks["capture_event"].assert_not_called()

    def test_non_studio_first_login_does_not_emit_signup(self):
        """is_first_login on a non-studio region does not fire the event.

        On enterprise regions is_first_login also covers an existing user with no
        admin role on any account yet, not just a genuine new signup.
        """
        self.mocks["authorise"].return_value = {"user": {"is_first_login": True}}

        ApiKeyCommand.apikey(region="us-1")

        self.mocks["capture_event"].assert_not_called()

    def test_none_auth_response_does_not_crash_or_emit_signup(self):
        """A None authorise response is handled defensively, not treated as a signup."""
        self.mocks["authorise"].return_value = None

        ApiKeyCommand.apikey(region="studio")

        self.mocks["capture_event"].assert_not_called()

    def test_auth_response_missing_user_key_does_not_crash_or_emit_signup(self):
        """An authorise response with no "user" key is handled defensively."""
        self.mocks["authorise"].return_value = {}

        ApiKeyCommand.apikey(region="studio")

        self.mocks["capture_event"].assert_not_called()


class AccountPollFailure(ApiKeyTestCase):
    """Tests for the no-account-appeared failure path."""

    def test_empty_accounts_after_20_tries_fails_with_exit_1(self):
        """20 empty polls without --account-id exits 1 reporting the account step."""
        self.mocks["get_accounts"].return_value = []

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as ctx:
                ApiKeyCommand.apikey(region="studio", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertEqual(self.mocks["get_accounts"].call_count, 20)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["step"], "account")


class MultipleAccounts(ApiKeyTestCase):
    """Choosing among several accounts: picker at a terminal, own workspace or a listed error otherwise."""

    TWO_ACCOUNTS = [
        {"id": "acc-1", "name": "Account One", "role": "Member", "created_by": "boss@x.com"},
        {"id": "acc-2", "name": "Account Two", "role": "Member", "created_by": None},
    ]
    ONE_OWN = [
        {"id": "acc-team", "name": "Team", "role": "Member", "created_by": "boss@x.com"},
        {"id": "acc-mine", "name": "Mine", "role": "Admin", "created_by": "Me@X.com"},
    ]

    def _tty(self) -> None:
        self.mocks["stdin"].isatty.return_value = True

    def test_tty_two_accounts_shows_picker_and_uses_choice(self):
        """At a terminal, the picker lists every account, defaults to your own, and its choice is used."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.ONE_OWN
        self.mocks["select"].return_value.ask.return_value = "acc-team"

        self.run_apikey(region="studio")

        self.mocks["signin"].assert_called_once()
        kwargs = self.mocks["select"].call_args.kwargs
        titles = [c.title for c in kwargs["choices"]]
        self.assertEqual(titles, ["Team (acc-team)", "Mine (acc-mine)"])
        self.assertEqual(kwargs["default"], "acc-mine")
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["account_id"], "acc-team")
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["jwt_token"], FAKE_JWT)

    def test_tty_picker_defaults_to_first_without_own_account(self):
        """With no account of your own, the picker defaults to the first one."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS
        self.mocks["select"].return_value.ask.return_value = "acc-2"

        self.run_apikey(region="studio")

        self.assertEqual(self.mocks["select"].call_args.kwargs["default"], "acc-1")

    def test_tty_picker_cancel_exits_1_account_step(self):
        """Cancelling the picker exits 1 at the account step without creating a key."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS
        self.mocks["select"].return_value.ask.return_value = None

        _, stderr, code = self.run_apikey(region="studio")

        self.assertEqual(code, 1)
        self.assertIn("No account selected", stderr)
        self.mocks["create_key"].assert_not_called()

    def test_non_tty_two_accounts_one_own_auto_selects(self):
        """Without a terminal, the one account you created is used, and the output says so."""
        self.mocks["get_accounts"].return_value = self.ONE_OWN

        stdout, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.mocks["select"].assert_not_called()
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["account_id"], "acc-mine")
        self.assertIn("Auto-selected your workspace Mine (acc-mine)", stdout)

    def test_non_tty_two_accounts_none_own_errors_with_accounts_json(self):
        """None of them yours: exit 1 at the account step, listing them in text and in `accounts`."""
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        stdout, _, code = self.run_apikey(region="us-1", output_json=True)

        self.assertEqual(code, 1)
        payload = json.loads(stdout)
        self.assertEqual(payload["step"], "account")
        for text in ("acc-1", "Account One", "acc-2", "Account Two", "--account-id"):
            self.assertIn(text, payload["error"])
        self.assertEqual(
            payload["accounts"],
            [
                {
                    "id": "acc-1",
                    "name": "Account One",
                    "role": "Member",
                    "created_by": "boss@x.com",
                },
                {"id": "acc-2", "name": "Account Two", "role": "Member", "created_by": None},
            ],
        )
        self.mocks["create_key"].assert_not_called()

    def test_error_says_the_sign_in_is_kept(self):
        """When the sign-in was cached, the error says the re-run won't sign in again."""
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        stdout, _, _ = self.run_apikey(region="studio", output_json=True)

        self.assertIn("will not ask you to sign in again", json.loads(stdout)["error"])

    def test_error_does_not_promise_reuse_with_no_session_cache(self):
        """With --no-session-cache nothing is kept, so the error doesn't claim it is."""
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        stdout, _, _ = self.run_apikey(region="studio", output_json=True, no_session_cache=True)

        self.assertNotIn("sign in again", json.loads(stdout)["error"])

    def test_non_tty_two_accounts_two_own_errors(self):
        """Two accounts you created is still a guess, so it is an error."""
        self.mocks["get_accounts"].return_value = [
            {"id": "acc-a", "name": "A", "role": "Admin", "created_by": ME},
            {"id": "acc-b", "name": "B", "role": "Admin", "created_by": ME},
        ]

        stdout, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 1)
        self.assertEqual([a["id"] for a in json.loads(stdout)["accounts"]], ["acc-a", "acc-b"])

    def test_empty_created_by_never_matches(self):
        """An account with an empty creator is never treated as yours, even with no email known."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": False}}
        self.mocks["get_accounts"].return_value = [
            {"id": "acc-a", "name": "A", "created_by": ""},
            {"id": "acc-b", "name": "B", "created_by": ""},
        ]

        _, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 1)

    def test_email_falls_back_to_the_token_claim(self):
        """With no email in authorise's user record, the token's email claim is used."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": False}}
        self.mocks["get_accounts"].return_value = self.ONE_OWN

        with patch(
            "poly.cli_commands.apikey.apikey_session.token_claims",
            return_value={"email": "me@x.com"},
        ):
            _, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["account_id"], "acc-mine")

    def test_json_two_accounts_never_prompts_even_at_tty(self):
        """--json never shows the picker, even with a terminal attached."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        _, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 1)
        self.mocks["select"].assert_not_called()

    def test_account_id_flag_wins_over_several_accounts(self):
        """--account-id skips the list, the picker and the auto-select."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.ONE_OWN

        self.run_apikey(region="studio", account_id="acc-team")

        self.mocks["get_accounts"].assert_not_called()
        self.mocks["select"].assert_not_called()

    def test_non_studio_with_one_account_proceeds(self):
        """A single account on an enterprise region resolves without --account-id."""
        self.mocks["get_accounts"].return_value = [{"id": "acc-solo", "name": "Solo"}]

        ApiKeyCommand.apikey(region="us-1")

        self.mocks["create_key"].assert_called_once_with(
            region="us-1",
            jwt_token=FAKE_JWT,
            account_id="acc-solo",
            name="cli-generated-key-us-1",
            source="apikey",
        )


class SessionCache(ApiKeyTestCase):
    """Reusing the sign-in across runs."""

    def test_cached_token_skips_signin(self):
        """A cached sign-in is used for authorise, and no new sign-in happens."""
        self.mocks["session_load"].return_value = _cached()

        stdout, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.mocks["signin"].assert_not_called()
        self.mocks["session_save"].assert_not_called()
        self.mocks["authorise"].assert_called_once_with(region="studio", jwt_token=CACHED_JWT)
        self.assertIn("Reusing your sign-in from 5 minutes ago", stdout)

    def test_expired_cache_signs_in_and_saves(self):
        """Nothing usable cached (load returns None for expired): sign in and save the token."""
        self.mocks["session_load"].return_value = None

        self.run_apikey(region="studio")

        self.mocks["signin"].assert_called_once()
        self.mocks["session_save"].assert_called_once_with("studio", FAKE_JWT)

    def test_cached_token_401_clears_and_signs_in_once(self):
        """A refused cached sign-in is dropped, and one fresh sign-in completes the run."""
        self.mocks["session_load"].return_value = _cached()
        self.mocks["authorise"].side_effect = [
            _http_error(401),
            {"user": {"is_first_login": False, "email": ME}},
        ]

        _, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.mocks["session_clear"].assert_called_once_with("studio")
        self.mocks["signin"].assert_called_once()
        self.assertEqual(self.mocks["authorise"].call_args.kwargs["jwt_token"], FAKE_JWT)
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["jwt_token"], FAKE_JWT)

    def test_cached_token_401_on_accounts_also_retries(self):
        """A 401 listing accounts with a cached sign-in is retried the same way."""
        self.mocks["session_load"].return_value = _cached()
        self.mocks["get_accounts"].side_effect = [_http_error(401), [{"id": FAKE_ACCOUNT}]]

        _, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.mocks["session_clear"].assert_called_once_with("studio")
        self.mocks["signin"].assert_called_once()

    def test_401_after_fresh_sign_in_is_not_retried(self):
        """A fresh sign-in that is refused is a real error: no loop, exit 1 at authorise."""
        self.mocks["session_load"].return_value = _cached()
        self.mocks["authorise"].side_effect = _http_error(401)

        stdout, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 1)
        self.assertEqual(self.mocks["signin"].call_count, 1)
        self.assertEqual(self.mocks["authorise"].call_count, 2)
        self.assertEqual(json.loads(stdout)["step"], "authorise")

    def test_401_without_cache_is_not_retried(self):
        """With a fresh token from the start, a 401 surfaces as before."""
        self.mocks["authorise"].side_effect = _http_error(401)

        _, _, code = self.run_apikey(region="studio")

        self.assertEqual(code, 1)
        self.mocks["session_clear"].assert_not_called()
        self.assertEqual(self.mocks["signin"].call_count, 1)

    def test_no_session_cache_flag_skips_load_and_save(self):
        """--no-session-cache neither reads nor writes the cache."""
        self.run_apikey(region="studio", no_session_cache=True)

        self.mocks["session_load"].assert_not_called()
        self.mocks["session_save"].assert_not_called()
        self.mocks["signin"].assert_called_once()

    def test_no_session_cache_flag_is_parsed(self):
        """The flag reaches the handler from the command line."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(
            ["apikey", "--region", "studio", "--no-session-cache"]
        )

        self.assertTrue(args.no_session_cache)


class TokenNeverInOutput(ApiKeyTestCase):
    """The sign-in token never reaches stdout or stderr, on any path."""

    def _failure_setups(self):
        """Each failure path, as (name, mutation of self.mocks, run kwargs)."""

        def set_(name, attr, value):
            return lambda: setattr(self.mocks[name], attr, value)

        two = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        return [
            ("device flow", set_("signin", "side_effect", DeviceFlowError("expired")), {}),
            ("authorise 500", set_("authorise", "side_effect", _http_error(500)), {}),
            (
                "authorise 403",
                set_("authorise", "side_effect", _http_error(403)),
                {"region": "us-1"},
            ),
            ("authorise 401", set_("authorise", "side_effect", _http_error(401)), {}),
            ("no account", set_("get_accounts", "return_value", []), {}),
            ("several accounts", set_("get_accounts", "return_value", two), {}),
            ("accounts 500", set_("get_accounts", "side_effect", _http_error(500)), {}),
            ("no key", set_("create_key", "return_value", {}), {}),
            ("list keys 500", set_("list_keys", "side_effect", _http_error(500)), {}),
            (
                "env conflict",
                set_("write_env", "side_effect", EnvVarConflict("o", "n", Path("/p"))),
                {},
            ),
        ]

    def test_token_never_in_output_on_any_failure(self):
        """Every failure path, plain and --json, fresh and cached sign-in, prints no token."""
        for cached in (False, True):
            for output_json in (False, True):
                for name, mutate, kwargs in self._failure_setups():
                    if cached and name == "device flow":
                        continue  # a cached sign-in never reaches the device flow
                    with self.subTest(path=name, json=output_json, cached=cached):
                        self.setUp()
                        if cached:
                            self.mocks["session_load"].return_value = _cached()
                        mutate()
                        stdout, stderr, code = self.run_apikey(
                            **{"region": "studio", "output_json": output_json, **kwargs}
                        )
                        self.assertIsNotNone(code)
                        for token in (FAKE_JWT, CACHED_JWT):
                            self.assertNotIn(token, stdout)
                            self.assertNotIn(token, stderr)

    def test_token_never_in_output_on_success(self):
        """Success, plain and --json, prints no token."""
        for output_json in (False, True):
            stdout, stderr, _ = self.run_apikey(region="studio", output_json=output_json)
            self.assertNotIn(FAKE_JWT, stdout + stderr)


class VersionAndNextStep(ApiKeyTestCase):
    """The running poly is named first, and the run ends with the next step."""

    # Absolute on the host, so the expectation holds on Windows too.
    CLI_PATH = os.path.abspath("/opt/tools/bin/poly")

    def setUp(self):
        super().setUp()
        for p in (
            patch("poly.cli_commands.apikey.get_package_version", return_value="9.9.9"),
            patch.object(sys, "argv", [self.CLI_PATH, "apikey"]),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_first_line_names_version_and_path(self):
        """The first line of plain output is `poly <version> (<path>)`."""
        stdout, _, _ = self.run_apikey(region="studio")

        self.assertEqual(stdout.splitlines()[0], f"poly 9.9.9 ({self.CLI_PATH})")

    def test_json_has_cli_version_and_path(self):
        """--json carries cli_version and cli_path, on success and on failure."""
        stdout, _, _ = self.run_apikey(region="studio", output_json=True)
        payload = json.loads(stdout)
        self.assertEqual(payload["cli_version"], "9.9.9")
        self.assertEqual(payload["cli_path"], self.CLI_PATH)

        self.mocks["get_accounts"].return_value = []
        stdout, _, _ = self.run_apikey(region="studio", output_json=True)
        payload = json.loads(stdout)
        self.assertFalse(payload["success"])
        self.assertEqual(payload["cli_version"], "9.9.9")

    def test_summary_and_json_carry_next_step_url(self):
        """The plain summary ends with the next step; --json has next_step_url."""
        stdout, _, _ = self.run_apikey(region="studio")
        self.assertIn(f"Next: make your first Dialog RSN 1 call -- {NEXT_STEP_URL}", stdout)
        self.assertEqual(NEXT_STEP_URL, "https://docs.poly.ai/dialog-rsn-1")

        stdout, _, _ = self.run_apikey(region="studio", output_json=True)
        self.assertEqual(json.loads(stdout)["next_step_url"], NEXT_STEP_URL)


class UnprovisionedEnterpriseUser(ApiKeyTestCase):
    """Tests for the friendly-403 rewrite when authorise fails on an enterprise region."""

    @staticmethod
    def _forbidden_error() -> requests.HTTPError:
        """Build the HTTPError authorise raises for an unprovisioned enterprise user."""
        response = MagicMock()
        response.status_code = 403
        return requests.HTTPError("403 Client Error: Forbidden", response=response)

    def test_403_on_enterprise_region_is_rewritten(self):
        """A 403 from authorise on us-1 becomes the friendly provisioning message."""
        self.mocks["authorise"].side_effect = self._forbidden_error()

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as ctx:
                ApiKeyCommand.apikey(region="us-1", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["step"], "authorise")
        self.assertIn("No account is provisioned for you on us-1", payload["error"])
        self.assertIn("poly apikey", payload["error"])

    def test_403_on_studio_is_not_rewritten(self):
        """A 403 from authorise on studio is a genuine auth error and surfaces as-is."""
        self.mocks["authorise"].side_effect = self._forbidden_error()

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit) as ctx:
                ApiKeyCommand.apikey(region="studio", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = json.loads(buffer.getvalue())
        self.assertEqual(payload["step"], "authorise")
        self.assertNotIn("No account is provisioned", payload["error"])
        self.assertIn("403", payload["error"])


class KeyActivationWait(ApiKeyTestCase):
    """Tests for the post-credentials key-activation poll."""

    def test_activates_on_third_poll(self):
        """The command completes normally once the key activates partway through the poll."""
        self.mocks["get_accounts_with_key"].side_effect = [
            Exception("not active"),
            Exception("not active"),
            {FAKE_ACCOUNT: "Account One"},
        ]

        with contextlib.redirect_stdout(io.StringIO()):
            ApiKeyCommand.apikey(region="studio")

        self.assertEqual(self.mocks["get_accounts_with_key"].call_count, 3)
        self.mocks["write_env"].assert_called_once()

    def test_never_activates_still_completes_and_warns(self):
        """20 failed polls print a warning but do not fail the command."""
        self.mocks["get_accounts_with_key"].side_effect = Exception("not active")

        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ApiKeyCommand.apikey(region="studio")

        self.assertEqual(self.mocks["get_accounts_with_key"].call_count, 20)
        self.mocks["write_env"].assert_called_once()
        self.assertIn("not active yet", stdout.getvalue())

    def test_probes_the_actual_key_not_the_on_disk_credential(self):
        """The activation check is called with the key this run produced.

        Regression test for the bug James found in review: when an existing
        credential is kept rather than overwritten, the old check
        (`get_accounts`, authenticated via the on-disk credential) would
        silently validate a different, already-active key instead of the one
        actually being exported.
        """
        self.mocks["load_cred"].return_value = "some-other-on-disk-key"

        with contextlib.redirect_stdout(io.StringIO()):
            ApiKeyCommand.apikey(region="studio")

        self.mocks["get_accounts_with_key"].assert_called_with(region="studio", api_key=FAKE_KEY)


class EnvConflict(ApiKeyTestCase):
    """Tests for the POLY_API_KEY conflict path."""

    def test_conflict_exits_2_without_force(self):
        """A conflicting existing value exits 2 with a --force hint."""
        self.mocks["write_env"].side_effect = EnvVarConflict(
            "old****", "new****", Path("/home/user/.zshrc")
        )

        stderr = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                ApiKeyCommand.apikey(region="studio")

        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("Re-run with --force", stderr.getvalue())

    def test_json_error_matches_the_documented_contract(self):
        """--json failures include success/error/step, with no Rich markup.

        No traceback: that's what --verbose is for, and the human-readable path
        already omits one without it - --json shouldn't be more verbose by default.
        """
        self.mocks["write_env"].side_effect = EnvVarConflict(
            "old****", "new****", Path("/home/user/.zshrc")
        )
        buffer = io.StringIO()

        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(SystemExit):
                ApiKeyCommand.apikey(region="studio", output_json=True)

        payload = json.loads(buffer.getvalue())
        self.assertFalse(payload["success"])
        self.assertEqual(payload["step"], "env")
        self.assertNotIn("traceback", payload)
        self.assertNotIn("[", buffer.getvalue())

    def test_force_is_forwarded_to_write_env_var(self):
        """--force is passed straight through to write_env_var."""
        ApiKeyCommand.apikey(region="studio", force=True)

        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=True)


class Verbose(ApiKeyTestCase):
    """Tests for --verbose re-raising instead of exiting cleanly."""

    def test_verbose_reraises_instead_of_exiting(self):
        """With verbose=True, the original exception propagates (for a full traceback)."""
        self.mocks["get_accounts"].return_value = []

        with self.assertRaises(ValueError):
            ApiKeyCommand.apikey(region="studio", verbose=True)


class ArgParsing(unittest.TestCase):
    """Tests for apikey's own argparse wiring."""

    def test_force_short_alias(self):
        """-f is accepted as a short alias for --force, matching other commands."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(["apikey", "-f", "--region", "studio"])

        self.assertTrue(args.force)

    def test_region_is_required(self):
        """Omitting --region is an argparse error (exit code 2)."""
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        parser = cli._create_parser()

        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                parser.parse_args(["apikey"])

        self.assertEqual(ctx.exception.code, 2)

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
