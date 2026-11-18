"""Tests for the `poly apikey` command.

Copyright PolyAI Limited
"""

import contextlib
import io
import json
import os
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

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
PROFILE_KEY = "sk-profile0987654321"
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
            "read_env": patch("poly.cli_commands.apikey.read_env_var", return_value=None),
            "create_key": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.create_account_api_key_internal",
                return_value={"key": FAKE_KEY},
            ),
            "list_keys": patch(
                "poly.cli_commands.apikey.AgentStudioInterface.list_account_api_keys_internal",
                return_value=[],
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
            # Nothing cached, and never touch the real ~/.poly/apikey_session.
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
            api_groups=None,
            expires_at=ANY,
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

        self.assertNotRegex(buffer.getvalue(), r"\[/?[a-z ]+\]")  # no Rich tags

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
            api_groups=None,
            expires_at=ANY,
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
            api_groups=None,
            expires_at=ANY,
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
            api_groups=None,
            expires_at=ANY,
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
    """Tests for the cli_signup event and the identity saved at sign-in."""

    def _events(self, name: str) -> list:
        """(properties, distinct_id, groups) of each captured `name` event."""
        return [
            (call.args[2], call.args[3], call.kwargs.get("groups"))
            for call in self.mocks["capture_event"].call_args_list
            if call.args[1] == name
        ]

    def test_studio_first_login_emits_signup_for_the_person(self):
        """A first login on studio sends cli_signup under the email, account as group."""
        self.mocks["authorise"].return_value = {
            "user": {"is_first_login": True, "email": ME, "auth_provider": "github"}
        }

        ApiKeyCommand.apikey(region="studio", ref="devhome.7f3a")

        [(properties, distinct_id, groups)] = self._events("cli_signup")
        self.assertEqual(distinct_id, ME)
        self.assertEqual(groups["company"], FAKE_ACCOUNT)
        self.assertEqual(properties["source"], "apikey")
        self.assertEqual(properties["ref"], "devhome.7f3a")
        self.assertEqual(properties["auth_provider"], "github")
        self.assertEqual(self._events("apikey_signup"), [])

    def test_setup_passes_its_own_source(self):
        """When poly setup runs this, the sign-up is counted as setup."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": True, "email": ME}}

        ApiKeyCommand.apikey(region="studio", source="setup")

        [(properties, _, _)] = self._events("cli_signup")
        self.assertEqual(properties["source"], "setup")
        self.assertNotIn("ref", properties)

    def test_ref_from_the_environment_is_used(self):
        """POLY_SIGNUP_REF stands in for --ref."""
        self.mocks["authorise"].return_value = {"user": {"is_first_login": True, "email": ME}}

        with patch.dict(os.environ, {"POLY_SIGNUP_REF": "docs"}):
            ApiKeyCommand.apikey(region="studio")

        [(properties, _, _)] = self._events("cli_signup")
        self.assertEqual(properties["ref"], "docs")

    def test_studio_returning_user_does_not_emit_signup(self):
        """A returning user on studio (is_first_login False) does not fire the event."""
        ApiKeyCommand.apikey(region="studio")

        self.assertEqual(self._events("cli_signup"), [])

    def test_non_studio_first_login_does_not_emit_signup(self):
        """is_first_login on a non-studio region does not fire the event.

        On enterprise regions is_first_login also covers an existing user with no
        admin role on any account yet, not just a genuine new signup.
        """
        self.mocks["authorise"].return_value = {"user": {"is_first_login": True, "email": ME}}

        ApiKeyCommand.apikey(region="us-1")

        self.assertEqual(self._events("cli_signup"), [])

    def test_malformed_auth_responses_do_not_crash_or_emit_signup(self):
        """None, no user, or a user with no email are handled defensively."""
        for response in (None, {}, {"user": {}}, {"user": {"is_first_login": True}}):
            with self.subTest(response=response):
                self.mocks["capture_event"].reset_mock()
                self.mocks["authorise"].return_value = response

                ApiKeyCommand.apikey(region="studio")

                self.assertEqual(self._events("cli_signup"), [])

    def test_sign_in_saves_the_identity_for_later_events(self):
        """After sign-in, events are sent as the email with the account group."""
        from poly.handlers.posthog import get_user_identity
        from poly.utils.credentials import load_signin_identity

        ApiKeyCommand.apikey(region="studio")

        self.assertEqual(
            load_signin_identity(),
            {"email": ME, "account_id": FAKE_ACCOUNT, "region": "studio"},
        )
        self.assertEqual(get_user_identity(), ME)

    def test_milestones_are_reported_in_order(self):
        """apikey_step goes signed_in, account_ready, key_ready, env_written."""
        ApiKeyCommand.apikey(region="studio", ref="docs")

        steps = self._events("apikey_step")
        self.assertEqual(
            [properties["step"] for properties, _, _ in steps],
            ["signed_in", "account_ready", "key_ready", "env_written"],
        )
        self.assertTrue(all(p["ref"] == "docs" and p["source"] == "apikey" for p, _, _ in steps))
        self.assertIs(steps[0][0]["session_reused"], False)
        self.assertIs(steps[2][0]["key_reused"], False)

    def test_failure_names_the_step_for_the_command_event(self):
        """A failed run records the step and error class for cli_command_completed."""
        from poly.handlers.posthog import command_properties, reset_command_properties

        reset_command_properties()
        self.mocks["authorise"].side_effect = _http_error(500)

        with self.assertRaises(SystemExit):
            ApiKeyCommand.apikey(region="studio")

        self.assertEqual(
            command_properties(),
            {"failed_step": "authorise", "error_type": "HTTPError", "http_status": 500},
        )


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
    """Choosing among several accounts: a picker at a terminal, a listed error otherwise."""

    TWO_ACCOUNTS = [
        {"id": "acc-1", "name": "Account One", "role": "Member", "created_by": "boss@x.com"},
        {"id": "acc-2", "name": "Account Two", "role": "Member", "created_by": None},
    ]

    def _tty(self) -> None:
        self.mocks["stdin"].isatty.return_value = True

    def test_tty_two_accounts_shows_picker_and_uses_choice(self):
        """At a terminal, the picker lists every account and its choice is used with the same sign-in."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS
        self.mocks["select"].return_value.ask.return_value = "acc-2"

        self.run_apikey(region="studio")

        self.mocks["signin"].assert_called_once()
        kwargs = self.mocks["select"].call_args.kwargs
        titles = [c.title for c in kwargs["choices"]]
        self.assertEqual(titles, ["Account One (acc-1)", "Account Two (acc-2)"])
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["account_id"], "acc-2")
        self.assertEqual(self.mocks["create_key"].call_args.kwargs["jwt_token"], FAKE_JWT)

    def test_tty_picker_cancel_exits_1_account_step(self):
        """Cancelling the picker exits 1 at the account step without creating a key."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS
        self.mocks["select"].return_value.ask.return_value = None

        _, stderr, code = self.run_apikey(region="studio")

        self.assertEqual(code, 1)
        self.assertIn("No account selected", stderr)
        self.mocks["create_key"].assert_not_called()

    def test_non_tty_two_accounts_errors_with_accounts_json(self):
        """Without a terminal: exit 1 at the account step, listing them in text and in `accounts`."""
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        stdout, _, code = self.run_apikey(region="us-1", output_json=True)

        self.assertEqual(code, 1)
        self.mocks["select"].assert_not_called()
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

    def test_non_tty_plain_output_lists_the_accounts(self):
        """Without --json the error on stderr still names every account."""
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        _, stderr, code = self.run_apikey(region="studio")

        self.assertEqual(code, 1)
        for text in ("acc-1", "Account One", "acc-2", "Account Two", "--account-id"):
            self.assertIn(text, " ".join(stderr.split()))  # the console wraps long lines

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

    def test_json_two_accounts_never_prompts_even_at_tty(self):
        """--json never shows the picker, even with a terminal attached."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        _, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 1)
        self.mocks["select"].assert_not_called()

    def test_account_id_flag_wins_over_several_accounts(self):
        """--account-id skips the list and the picker."""
        self._tty()
        self.mocks["get_accounts"].return_value = self.TWO_ACCOUNTS

        self.run_apikey(region="studio", account_id="acc-1")

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
            api_groups=None,
            expires_at=ANY,
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
            ("create key 500", set_("create_key", "side_effect", _http_error(500)), {}),
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


class NextStep(ApiKeyTestCase):
    """The run ends with the next step."""

    def test_summary_and_json_carry_next_step_url(self):
        """The plain summary ends with the next step; only --json carries next_step_url."""
        stdout, _, _ = self.run_apikey(region="studio")
        self.assertIn("Next: make your first API call (POLY_API_KEY is already set).", stdout)
        self.assertNotIn(NEXT_STEP_URL, stdout)
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


class ProfileKeyReuse(ApiKeyTestCase):
    """Reusing the POLY_API_KEY already in the profile."""

    def test_working_profile_key_is_reused_without_creating_one(self):
        """A profile key accepted for the chosen account is kept and nothing is created."""
        self.mocks["read_env"].return_value = PROFILE_KEY

        stdout, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertIsNone(code)
        self.mocks["create_key"].assert_not_called()
        self.mocks["get_accounts_with_key"].assert_called_with(region="studio", api_key=PROFILE_KEY)
        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", PROFILE_KEY, force=False)
        payload = json.loads(stdout)
        self.assertTrue(payload["key_reused"])
        self.assertIsNone(payload["key_name"])
        self.assertNotIn(PROFILE_KEY, stdout)

    def _assert_stops_before_creating(self) -> None:
        stdout, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(code, 2)
        self.mocks["create_key"].assert_not_called()
        self.mocks["write_env"].assert_not_called()
        payload = json.loads(stdout)
        self.assertEqual(payload["step"], "key")
        self.assertIn(f"isn't accepted for account {FAKE_ACCOUNT} on studio", payload["error"])
        self.assertIn("--force", payload["error"])
        self.assertNotIn("different value", payload["error"])
        self.assertNotIn(PROFILE_KEY, stdout)

    def test_refused_profile_key_stops_before_creating_one(self):
        """A refused key may be good on another region, so it needs --force to replace."""
        for status in (401, 403):
            with self.subTest(status=status):
                self.setUp()
                self.mocks["read_env"].return_value = PROFILE_KEY
                self.mocks["get_accounts_with_key"].side_effect = _http_error(status)

                self._assert_stops_before_creating()

    def test_profile_key_for_another_account_stops_before_creating_one(self):
        """A key that can't reach the chosen account isn't reused or silently replaced."""
        self.mocks["read_env"].return_value = PROFILE_KEY
        self.mocks["get_accounts_with_key"].return_value = {"acc-other": "Other"}

        self._assert_stops_before_creating()

    def test_failed_check_is_a_real_error(self):
        """A check that says nothing about the key exits 1 and doesn't suggest --force."""
        failures = {
            "server error": _http_error(503),
            "connection": requests.ConnectionError("connection dropped"),
            "timeout": requests.Timeout("timed out"),
        }
        for name, failure in failures.items():
            with self.subTest(failure=name):
                self.setUp()
                self.mocks["read_env"].return_value = PROFILE_KEY
                self.mocks["get_accounts_with_key"].side_effect = failure

                stdout, _, code = self.run_apikey(region="studio", output_json=True)

                self.assertEqual(code, 1)
                self.mocks["create_key"].assert_not_called()
                self.mocks["write_env"].assert_not_called()
                payload = json.loads(stdout)
                self.assertEqual(payload["step"], "key")
                self.assertNotIn("--force", payload["error"])

    def test_force_creates_a_new_key_without_reading_the_profile(self):
        """--force replaces the profile key, even a working one."""
        self.mocks["read_env"].return_value = PROFILE_KEY

        ApiKeyCommand.apikey(region="studio", force=True)

        self.mocks["read_env"].assert_not_called()
        self.mocks["create_key"].assert_called_once()
        self.mocks["write_env"].assert_called_once_with("POLY_API_KEY", FAKE_KEY, force=True)


class KeyTypeAndExpiry(ApiKeyTestCase):
    """`--type` and `--expires-in`: what is asked for, and how it is reported."""

    def _create_kwargs(self) -> dict:
        self.mocks["create_key"].assert_called_once()
        return self.mocks["create_key"].call_args.kwargs

    def test_default_is_an_agent_key_expiring_in_90_days(self):
        """No flags: every API (api_groups left out) and a 90-day expiry."""
        before = datetime.now(UTC)

        self.run_apikey(region="studio")

        kwargs = self._create_kwargs()
        self.assertIsNone(kwargs["api_groups"])
        self.assertEqual(kwargs["name"], "cli-generated-key")
        delta = kwargs["expires_at"] - before
        self.assertTrue(timedelta(days=90) <= delta < timedelta(days=90, minutes=1))
        self.assertEqual(kwargs["expires_at"].utcoffset(), timedelta(0))

    def test_model_type_asks_for_the_models_group(self):
        """--type model sends api_groups ["models"]."""
        self.run_apikey(region="studio", key_type="model")

        self.assertEqual(self._create_kwargs()["api_groups"], ["models"])

    def test_explicit_agent_type_leaves_api_groups_out(self):
        """--type agent is the same request as the default."""
        self.run_apikey(region="studio", key_type="agent")

        self.assertIsNone(self._create_kwargs()["api_groups"])

    def test_each_expires_in_value(self):
        """30d / 90d / 365d become an absolute UTC expiry; never leaves it out."""
        for value, days in (("30d", 30), ("90d", 90), ("365d", 365), ("never", None)):
            with self.subTest(expires_in=value):
                self.setUp()
                before = datetime.now(UTC)

                self.run_apikey(region="studio", expires_in=value)

                expires_at = self._create_kwargs()["expires_at"]
                if days is None:
                    self.assertIsNone(expires_at)
                else:
                    delta = expires_at - before
                    self.assertTrue(timedelta(days=days) <= delta < timedelta(days=days, minutes=1))

    def test_model_key_gets_its_own_default_name(self):
        """A model key never collides with the agent key's default name."""
        for region, name in (
            ("studio", "cli-generated-key-model"),
            ("us-1", "cli-generated-key-us-1-model"),
        ):
            with self.subTest(region=region):
                self.setUp()
                self.run_apikey(region=region, key_type="model")

                self.assertEqual(self._create_kwargs()["name"], name)

    def test_key_name_overrides_the_model_default(self):
        """--key-name still wins for a model key."""
        self.run_apikey(region="studio", key_type="model", key_name="my-model-key")

        self.assertEqual(self._create_kwargs()["name"], "my-model-key")

    def test_human_output_shows_type_and_expiry(self):
        """The summary names the type, its Studio label and the expiry date."""
        self.mocks["create_key"].return_value = {
            "key": FAKE_KEY,
            "api_groups": None,
            "never_expires": False,
            "expires_at": "2027-02-13T10:00:00+00:00",
        }

        stdout, _, _ = self.run_apikey(region="studio")

        self.assertIn("agent (All APIs)", stdout)
        self.assertIn("Expires:   2027-02-13", stdout)

    def test_human_output_says_never_for_a_never_expiring_key(self):
        self.mocks["create_key"].return_value = {"key": FAKE_KEY, "never_expires": True}

        stdout, _, _ = self.run_apikey(region="studio", expires_in="never")

        self.assertIn("Expires:   never", stdout)

    def test_json_type_and_expiry_come_from_the_response(self):
        """key_type / expires_at are read from what the platform says it created."""
        self.mocks["create_key"].return_value = {
            "key": FAKE_KEY,
            "api_groups": ["models"],
            "never_expires": False,
            "expires_at": "2027-02-13T10:00:00+00:00",
        }

        stdout, _, _ = self.run_apikey(region="studio", key_type="model", output_json=True)

        payload = json.loads(stdout)
        self.assertEqual(payload["key_type"], "model")
        self.assertEqual(payload["expires_at"], "2027-02-13T10:00:00+00:00")

    def test_json_falls_back_to_what_was_asked_for(self):
        """With a bare response, key_type / expires_at are the requested values."""
        stdout, _, _ = self.run_apikey(region="studio", expires_in="30d", output_json=True)

        payload = json.loads(stdout)
        self.assertEqual(payload["key_type"], "agent")
        requested = self.mocks["create_key"].call_args.kwargs["expires_at"]
        self.assertEqual(payload["expires_at"], requested.isoformat())

    def test_json_never_expiring_key_has_null_expiry(self):
        self.mocks["create_key"].return_value = {"key": FAKE_KEY, "never_expires": True}

        stdout, _, _ = self.run_apikey(region="studio", expires_in="never", output_json=True)

        self.assertIsNone(json.loads(stdout)["expires_at"])

    def test_json_reused_key_has_null_type_and_expiry(self):
        """A reused key not in the account's key list has null type and expiry, not a guess."""
        self.mocks["read_env"].return_value = PROFILE_KEY

        stdout, _, _ = self.run_apikey(region="studio", output_json=True)

        payload = json.loads(stdout)
        self.assertIsNone(payload["key_type"])
        self.assertIsNone(payload["expires_at"])


def _record(key: str, groups: list[str] | None = None, **fields) -> dict:
    """A key-list entry for `key`: no secret, only its prefix and suffix."""
    return {
        "key_prefix": key[:4],
        "key_suffix": key[-4:],
        "api_groups": groups,
        "never_expires": False,
        **fields,
    }


class ModelKeyHasItsOwnVariable(ApiKeyTestCase):
    """A model key lives in POLY_MODEL_API_KEY and never touches the agent key."""

    def test_model_key_is_written_to_its_own_variable_only(self):
        stdout, _, code = self.run_apikey(region="studio", key_type="model")

        self.assertIsNone(code)
        self.mocks["write_env"].assert_called_once_with(
            "POLY_MODEL_API_KEY", FAKE_KEY, force=False
        )
        self.mocks["save_cred"].assert_not_called()
        self.mocks["load_cred"].assert_not_called()
        self.assertNotIn(FAKE_KEY, stdout)

    def test_model_key_reads_and_reuses_only_its_own_variable(self):
        self.mocks["read_env"].side_effect = {
            "POLY_API_KEY": PROFILE_KEY,
            "POLY_MODEL_API_KEY": "sk-model-in-profile-1",
        }.get

        _, _, code = self.run_apikey(region="studio", key_type="model")

        self.assertIsNone(code)
        self.mocks["read_env"].assert_called_once_with("POLY_MODEL_API_KEY")
        self.mocks["create_key"].assert_not_called()
        self.mocks["write_env"].assert_called_once_with(
            "POLY_MODEL_API_KEY", "sk-model-in-profile-1", force=False
        )

    def test_agent_key_reads_only_poly_api_key(self):
        self.run_apikey(region="studio")

        self.mocks["read_env"].assert_called_once_with("POLY_API_KEY")

    def test_refused_model_key_names_its_variable_and_rerun(self):
        self.mocks["read_env"].return_value = PROFILE_KEY
        self.mocks["get_accounts_with_key"].side_effect = _http_error(401)

        stdout, _, code = self.run_apikey(region="studio", key_type="model", output_json=True)

        self.assertEqual(code, 2)
        error = json.loads(stdout)["error"]
        self.assertIn("POLY_MODEL_API_KEY in", error)
        self.assertIn("poly apikey --region studio --type model --force", error)
        self.mocks["create_key"].assert_not_called()

    def test_model_key_force_replaces_only_its_own_variable(self):
        self.run_apikey(region="studio", key_type="model", force=True)

        self.mocks["read_env"].assert_not_called()
        self.mocks["write_env"].assert_called_once_with("POLY_MODEL_API_KEY", FAKE_KEY, force=True)
        self.mocks["save_cred"].assert_not_called()

    def test_model_key_json_is_masked_and_names_the_variable(self):
        stdout, _, _ = self.run_apikey(region="studio", key_type="model", output_json=True)

        payload = json.loads(stdout)
        self.assertTrue(payload["success"])
        self.assertNotIn(FAKE_KEY, stdout)
        self.assertNotIn("api_key", payload)
        self.assertEqual(payload["env_var"], "POLY_MODEL_API_KEY")
        self.assertEqual(payload["key_type"], "model")
        self.assertIsNone(payload["credentials_file"])
        self.assertEqual(payload["profile_path"], str(Path("/home/user/.zshrc")))
        self.assertIs(payload["key_active"], True)

    def test_model_key_summary_points_at_its_variable(self):
        stdout, _, _ = self.run_apikey(region="studio", key_type="model")

        text = " ".join(stdout.split())  # Rich wraps long lines
        self.assertIn("to pick up POLY_MODEL_API_KEY", text)
        self.assertIn("reading the key from POLY_MODEL_API_KEY", text)
        self.assertIn("a model key can't run the ADK", text)

    def test_model_key_waits_for_activation_with_the_model_key(self):
        self.run_apikey(region="studio", key_type="model")

        self.mocks["get_accounts_with_key"].assert_called_with(region="studio", api_key=FAKE_KEY)

    def test_agent_json_names_poly_api_key(self):
        stdout, _, _ = self.run_apikey(region="studio", output_json=True)

        self.assertEqual(json.loads(stdout)["env_var"], "POLY_API_KEY")


class ReusedKeyDetails(ApiKeyTestCase):
    """A reused key's type and expiry come from the account's key list."""

    def setUp(self):
        super().setUp()
        self.mocks["read_env"].return_value = PROFILE_KEY

    def _in(self, days: float) -> str:
        return (datetime.now(UTC) + timedelta(days=days)).isoformat()

    def test_matched_record_fills_type_and_expiry(self):
        expiry = self._in(60)
        self.mocks["list_keys"].return_value = [
            _record("sk-otherkey00000000"),
            _record(PROFILE_KEY, expires_at=expiry),
        ]

        stdout, _, _ = self.run_apikey(region="studio", output_json=True)

        payload = json.loads(stdout)
        self.assertEqual(payload["key_type"], "agent")
        self.assertEqual(payload["expires_at"], expiry)
        self.mocks["list_keys"].assert_called_once_with(
            region="studio", jwt_token=FAKE_JWT, account_id=FAKE_ACCOUNT, source="apikey"
        )

    def test_matched_record_shows_in_the_summary(self):
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, never_expires=True)]

        stdout, _, _ = self.run_apikey(region="studio")

        self.assertIn("agent (All APIs)", stdout)
        self.assertIn("Expires:   never", stdout)

    def test_no_match_or_several_matches_leave_them_null(self):
        for records in ([], [_record(PROFILE_KEY), _record(PROFILE_KEY)]):
            with self.subTest(matches=len(records)):
                self.setUp()
                self.mocks["list_keys"].return_value = records

                stdout, _, code = self.run_apikey(region="studio", output_json=True)

                self.assertIsNone(code)
                payload = json.loads(stdout)
                self.assertIsNone(payload["key_type"])
                self.assertIsNone(payload["expires_at"])

    def test_failed_lookup_does_not_fail_the_command(self):
        for failure in (_http_error(500), requests.ConnectionError("down")):
            with self.subTest(failure=type(failure).__name__):
                self.setUp()
                self.mocks["list_keys"].side_effect = failure

                stdout, _, code = self.run_apikey(region="studio", output_json=True)

                self.assertIsNone(code)
                self.assertTrue(json.loads(stdout)["success"])

    def test_a_created_key_skips_the_lookup(self):
        self.mocks["read_env"].return_value = None

        self.run_apikey(region="studio")

        self.mocks["list_keys"].assert_not_called()

    def test_warns_when_the_reused_key_expires_soon(self):
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, expires_at=self._in(9.5))]

        stdout, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        text = " ".join(stdout.split())  # Rich wraps long lines
        self.assertIn("(in 9 days)", text)
        self.assertIn("Re-run with --force to replace it", text)

    def test_no_expiry_warning_with_time_left(self):
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, expires_at=self._in(30))]

        stdout, _, _ = self.run_apikey(region="studio")

        self.assertNotIn("expires on", stdout)

    def test_warns_when_the_reused_key_is_the_other_type(self):
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, groups=["models"])]

        stdout, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.mocks["create_key"].assert_not_called()
        text = " ".join(stdout.split())  # Rich wraps long lines
        self.assertIn("The key in POLY_API_KEY is a model key, not agent", text)
        self.assertIn("replace it with an agent key", text)

    def test_expires_in_with_a_reused_key_says_it_did_not_apply(self):
        stdout, _, code = self.run_apikey(region="studio", expires_in="30d")

        self.assertIsNone(code)
        self.mocks["create_key"].assert_not_called()
        self.assertIn("--expires-in didn't apply", stdout)
        self.assertIn("--force", stdout)

    def test_no_notice_without_expires_in(self):
        for kwargs in ({}, {"key_type": "agent"}):
            with self.subTest(kwargs=kwargs):
                self.setUp()
                stdout, _, _ = self.run_apikey(region="studio", **kwargs)

                self.assertNotIn("didn't apply", stdout)

    def test_force_mints_with_the_flags(self):
        self.run_apikey(region="studio", expires_in="30d", force=True)

        self.mocks["create_key"].assert_called_once()
        self.assertIsNotNone(self.mocks["create_key"].call_args.kwargs["expires_at"])


class ExpiredProfileKey(ApiKeyTestCase):
    """The refusal says why the profile key was refused when the key list shows it."""

    def setUp(self):
        super().setUp()
        self.mocks["read_env"].return_value = PROFILE_KEY
        self.mocks["get_accounts_with_key"].side_effect = _http_error(401)

    def _error(self, **kwargs) -> str:
        stdout, _, code = self.run_apikey(region="studio", output_json=True, **kwargs)
        self.assertEqual(code, 2)
        self.mocks["create_key"].assert_not_called()
        return json.loads(stdout)["error"]

    def test_expired_key_says_when_it_expired(self):
        self.mocks["list_keys"].return_value = [
            _record(PROFILE_KEY, expires_at="2026-11-01T10:00:00+00:00")
        ]

        error = self._error()

        self.assertIn("POLY_API_KEY in", error)
        self.assertIn("expired on 2026-11-01", error)
        self.assertIn("poly apikey --region studio --force", error)
        self.assertEqual(error.count("--force"), 1)

    def test_key_missing_from_the_list_was_revoked_or_is_another_accounts(self):
        error = self._error()

        self.assertIn("revoked or belongs to another account", error)
        self.assertIn("poly apikey --region studio --force", error)

    def test_failed_lookup_keeps_the_general_message(self):
        self.mocks["list_keys"].side_effect = _http_error(500)

        error = self._error()

        self.assertIn("may have expired or been revoked", error)
        self.assertIn("poly apikey --region studio --force", error)

    def test_listed_unexpired_key_keeps_the_general_message(self):
        future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, expires_at=future)]

        self.assertIn("may have expired or been revoked", self._error())

    def test_expired_model_key_names_its_variable_and_type_flag(self):
        self.mocks["list_keys"].return_value = [
            _record(PROFILE_KEY, groups=["models"], expires_at="2026-11-01T10:00:00+00:00")
        ]

        error = self._error(key_type="model")

        self.assertIn("POLY_MODEL_API_KEY in", error)
        self.assertIn("expired on 2026-11-01", error)
        self.assertIn("poly apikey --region studio --type model --force", error)


class ExpiryAndLookupFallbacks(ApiKeyTestCase):
    """Odd platform data degrades to less detail, never to a failure."""

    def setUp(self):
        super().setUp()
        self.mocks["read_env"].return_value = PROFILE_KEY

    def test_unreadable_expiry_is_shown_as_given_without_a_warning(self):
        self.mocks["list_keys"].return_value = [_record(PROFILE_KEY, expires_at="soon")]

        stdout, _, code = self.run_apikey(region="studio")

        self.assertIsNone(code)
        self.assertIn("Expires:   soon", stdout)
        self.assertNotIn("expires on", stdout)

    def test_expiry_without_a_timezone_is_read_as_utc(self):
        naive = (datetime.now(UTC) + timedelta(days=3, hours=1)).replace(tzinfo=None)
        self.mocks["list_keys"].return_value = [
            _record(PROFILE_KEY, expires_at=naive.isoformat())
        ]

        stdout, _, _ = self.run_apikey(region="studio")

        self.assertIn("(in 3 days)", " ".join(stdout.split()))

    def test_a_non_list_response_is_ignored(self):
        self.mocks["list_keys"].return_value = {"unexpected": "shape"}

        stdout, _, code = self.run_apikey(region="studio", output_json=True)

        self.assertIsNone(code)
        self.assertIsNone(json.loads(stdout)["key_type"])

    def test_powershell_summary_names_the_variable(self):
        self.mocks["write_env"].return_value = (
            ProfileTarget(path=Path("HKCU/Environment"), shell="powershell"),
            "POLY_MODEL_API_KEY=sk-n****7890",
        )

        stdout, _, _ = self.run_apikey(region="studio", key_type="model")

        self.assertIn("Open a new terminal to pick up POLY_MODEL_API_KEY.", stdout)


class JsonWarnings(ApiKeyTestCase):
    """--json suppresses printed warnings, so it carries them in `warnings`."""

    def _payload(self, **kwargs) -> dict:
        stdout, _, code = self.run_apikey(region="studio", output_json=True, **kwargs)
        self.assertIsNone(code)
        return json.loads(stdout)

    def test_no_warnings_is_an_empty_list(self):
        self.assertEqual(self._payload()["warnings"], [])

    def test_reused_key_warnings_are_listed(self):
        self.mocks["read_env"].return_value = PROFILE_KEY
        soon = (datetime.now(UTC) + timedelta(days=5, hours=1)).isoformat()
        self.mocks["list_keys"].return_value = [
            _record(PROFILE_KEY, groups=["models"], expires_at=soon)
        ]

        warnings = self._payload(expires_in="30d")["warnings"]

        self.assertEqual(len(warnings), 3)
        self.assertIn("--expires-in didn't apply", warnings[0])
        self.assertIn("is a model key, not agent", warnings[1])
        self.assertIn("(in 5 days)", warnings[2])

    def test_not_active_warning_is_listed(self):
        self.mocks["get_accounts_with_key"].side_effect = Exception("not active")

        payload = self._payload()

        self.assertIs(payload["key_active"], False)
        self.assertEqual(
            payload["warnings"],
            [
                "API key was saved but is not active yet."
                " If your next command fails, wait a moment and retry."
            ],
        )


class OriginalWording(ApiKeyTestCase):
    """Messages an agent key user already knows stay as they were."""

    def test_reused_agent_key_line(self):
        self.mocks["read_env"].return_value = PROFILE_KEY

        stdout, _, _ = self.run_apikey(region="studio")

        self.assertIn("Reusing the key already in your profile: ", stdout)

    def test_reused_model_key_line_names_its_variable(self):
        self.mocks["read_env"].return_value = PROFILE_KEY

        stdout, _, _ = self.run_apikey(region="studio", key_type="model")

        text = " ".join(stdout.split())  # Rich wraps long lines
        self.assertIn("Reusing the key already in your profile (POLY_MODEL_API_KEY): ", text)


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


class TypeAndExpiryArgs(unittest.TestCase):
    """argparse wiring for --type and --expires-in."""

    def _parse(self, *argv: str):
        from poly.cli import AgentStudioCLI

        cli = AgentStudioCLI()
        cli.register_commands()
        return cli._create_parser().parse_args(["apikey", "--region", "studio", *argv])

    def test_unset_flags_parse_as_none(self):
        """None, not the default, so a reused key can tell whether they were asked for."""
        args = self._parse()

        self.assertIsNone(args.key_type)
        self.assertIsNone(args.expires_in)

    def test_flags_parse(self):
        args = self._parse("--type", "model", "--expires-in", "365d")

        self.assertEqual(args.key_type, "model")
        self.assertEqual(args.expires_in, "365d")

    def test_invalid_values_are_rejected(self):
        for argv in (("--type", "data"), ("--expires-in", "7d")):
            with self.subTest(argv=argv):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as ctx:
                        self._parse(*argv)
                self.assertEqual(ctx.exception.code, 2)

    def test_run_passes_the_flags_through(self):
        args = self._parse("--type", "model", "--expires-in", "never")

        with patch.object(ApiKeyCommand, "apikey") as apikey:
            ApiKeyCommand.run(args)

        self.assertEqual(apikey.call_args.kwargs["key_type"], "model")
        self.assertEqual(apikey.call_args.kwargs["expires_in"], "never")


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
