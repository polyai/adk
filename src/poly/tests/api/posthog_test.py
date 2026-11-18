"""Tests for the PostHog handler: feature flags and event capture.

Copyright PolyAI Limited
"""

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from poly.handlers import posthog as posthog_module
from poly.handlers.posthog import (
    TELEMETRY_OPT_OUT_ENV_VARS,
    PosthogHandler,
    get_posthog_client,
    get_user_identity,
    identify_signin,
    signup_ref,
    track,
)
from poly.utils import credentials as credentials_module
from poly.utils.credentials import (
    load_signin_identity,
    save_api_key_credential_file,
    save_signin_identity,
)


class IsFeatureEnabledTest(unittest.TestCase):
    """Tests for PosthogHandler.is_feature_enabled."""

    def setUp(self):
        self.client = MagicMock()
        self.client_patcher = patch(
            "poly.handlers.posthog.get_posthog_client", return_value=self.client
        )
        self.client_patcher.start()
        self.identity_patcher = patch(
            "poly.handlers.posthog.get_user_identity", return_value="test-user"
        )
        self.identity_patcher.start()

    def tearDown(self):
        patch.stopall()

    def test_returns_flag_value_when_evaluated(self):
        """A resolved flag is returned as-is, for both True and False."""
        for value in (True, False):
            with self.subTest(value=value):
                self.client.feature_enabled.return_value = value

                result = PosthogHandler.is_feature_enabled(
                    region="studio", key="some-flag", default=not value
                )

                self.assertEqual(result, value)

    def test_returns_default_when_flag_is_unresolved(self):
        """A None result means PostHog could not evaluate the flag, so default wins."""
        self.client.feature_enabled.return_value = None

        for default in (True, False):
            with self.subTest(default=default):
                result = PosthogHandler.is_feature_enabled(
                    region="studio", key="some-flag", default=default
                )

                self.assertEqual(result, default)

    def test_returns_default_when_evaluation_raises(self):
        """Any exception from the client is swallowed and the default returned.

        The 1s request timeout means a slow or unreachable PostHog must never
        take down a gated CLI command.
        """
        self.client.feature_enabled.side_effect = RuntimeError("connection reset")

        for default in (True, False):
            with self.subTest(default=default):
                result = PosthogHandler.is_feature_enabled(
                    region="studio", key="some-flag", default=default
                )

                self.assertEqual(result, default)

    def test_returns_default_when_client_is_unavailable(self):
        """A falsy client short-circuits to the default without evaluating."""
        with patch("poly.handlers.posthog.get_posthog_client", return_value=None):
            result = PosthogHandler.is_feature_enabled(
                region="studio", key="some-flag", default=True
            )

        self.assertTrue(result)

    def test_passes_key_identity_and_project_group(self):
        """The flag key, distinct_id and project group are forwarded to PostHog.

        The project group key is namespaced by cluster: project ids are minted
        per-cluster, and several clusters share one PostHog project, so a bare
        id matches no group. Conditions match on the properties, so those are
        sent too.
        """
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(
            region="studio",
            key="deployment-simplification",
            default=False,
            project_id="proj-1",
            account_id="acct-1",
        )

        self.client.feature_enabled.assert_called_once_with(
            "deployment-simplification",
            distinct_id="test-user",
            groups={"cluster": "plg-us-1-prod", "project": "plg-us-1-prod/proj-1"},
            group_properties={
                "cluster": {"cluster": "plg-us-1-prod", "env": "plg"},
                "project": {
                    "project_id": "proj-1",
                    "cluster": "plg-us-1-prod",
                    "env": "plg",
                    "account_id": "acct-1",
                },
            },
            send_feature_flag_events=False,
        )

    def test_omits_account_id_when_unknown(self):
        """An absent account leaves the stored property alone; an empty one fails
        an exact condition."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(
            region="studio", key="some-flag", default=False, project_id="proj-1"
        )

        project_properties = self.client.feature_enabled.call_args.kwargs["group_properties"][
            "project"
        ]
        self.assertNotIn("account_id", project_properties)

    def test_non_production_regions_send_their_own_env(self):
        """The env property separates the two deployments sharing a cluster key."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(
            region="staging", key="some-flag", default=False, project_id="proj-1"
        )

        properties = self.client.feature_enabled.call_args.kwargs["group_properties"]
        self.assertEqual(properties["cluster"]["env"], "staging")

    def test_region_is_mapped_to_cluster_env(self):
        """Studio is the PLG deployment; unlisted regions are production."""
        self.client.feature_enabled.return_value = True

        for region, expected_env in (
            ("dev", "dev"),
            ("staging", "staging"),
            ("studio", "plg"),
            ("us-1", "prod"),
        ):
            with self.subTest(region=region):
                PosthogHandler.is_feature_enabled(region=region, key="some-flag", default=False)

                self.assertEqual(
                    self.client.feature_enabled.call_args.kwargs["group_properties"]["cluster"][
                        "env"
                    ],
                    expected_env,
                )

    def test_omits_project_group_when_no_project_id(self):
        """Without a project id only the cluster group is sent."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(region="studio", key="some-flag", default=False)

        self.assertEqual(
            self.client.feature_enabled.call_args.kwargs["groups"], {"cluster": "plg-us-1-prod"}
        )

    def test_region_is_mapped_to_posthog_cluster(self):
        """Regions with a cluster alias are translated; others pass through unchanged."""
        self.client.feature_enabled.return_value = True

        for region, expected_cluster in (
            ("dev", "apollo"),
            ("staging", "staging"),
            ("studio", "plg-us-1-prod"),
            ("us-1", "us-1"),
        ):
            with self.subTest(region=region):
                PosthogHandler.is_feature_enabled(region=region, key="some-flag", default=False)

                self.assertEqual(
                    self.client.feature_enabled.call_args.kwargs["groups"]["cluster"],
                    expected_cluster,
                )


class PosthogKeyForRegionTest(unittest.TestCase):
    """Tests for which PostHog project a region's flags are read from."""

    def test_production_regions_use_the_production_project(self):
        for region in ("us-1", "uk-1", "euw-1"):
            with self.subTest(region=region):
                self.assertEqual(
                    posthog_module.posthog_key_for_region(region),
                    posthog_module.POSTHOG_KEY_PROD,
                )

    def test_non_production_regions_use_the_non_production_project(self):
        for region in ("dev", "staging"):
            with self.subTest(region=region):
                self.assertEqual(
                    posthog_module.posthog_key_for_region(region),
                    posthog_module.POSTHOG_KEY_NON_PROD,
                )

    def test_region_is_matched_case_insensitively(self):
        self.assertEqual(
            posthog_module.posthog_key_for_region("DEV"),
            posthog_module.POSTHOG_KEY_NON_PROD,
        )

    def test_an_unknown_region_uses_the_production_project(self):
        """Non-prod is the exception; anything else reads production.

        The non-production project has rollouts at 100%, so defaulting there
        would report every flag as enabled.
        """
        for region in ("", "studio", "something-new"):
            with self.subTest(region=region):
                self.assertEqual(
                    posthog_module.posthog_key_for_region(region),
                    posthog_module.POSTHOG_KEY_PROD,
                )


class GetPosthogClientTest(unittest.TestCase):
    """Tests for the per-project PostHog client cache."""

    def setUp(self):
        self.original_clients = dict(posthog_module._clients)
        posthog_module._clients.clear()

    def tearDown(self):
        posthog_module._clients.clear()
        posthog_module._clients.update(self.original_clients)

    def test_client_is_constructed_once_per_project_and_reused(self):
        """One client per PostHog project, built on first use."""
        with patch("posthog.Posthog") as mock_posthog_cls:
            first = get_posthog_client("us-1")
            second = get_posthog_client("uk-1")

        self.assertIs(first, second)
        mock_posthog_cls.assert_called_once()

    def test_regions_in_different_projects_get_different_clients(self):
        """A session touching both environments must not share one client."""
        with patch("posthog.Posthog", side_effect=lambda **kwargs: MagicMock()):
            production = get_posthog_client("us-1")
            non_production = get_posthog_client("dev")

        self.assertIsNot(production, non_production)

    def test_client_is_built_with_the_region_project_key(self):
        with patch("posthog.Posthog") as mock_posthog_cls:
            get_posthog_client("us-1")

        self.assertEqual(
            mock_posthog_cls.call_args.kwargs["project_api_key"],
            posthog_module.POSTHOG_KEY_PROD,
        )

    def test_client_is_configured_with_a_request_timeout(self):
        """A feature-flag read is bounded so the CLI cannot hang on PostHog."""
        with patch("posthog.Posthog") as mock_posthog_cls:
            get_posthog_client("us-1")

        timeout = mock_posthog_cls.call_args.kwargs["feature_flags_request_timeout_seconds"]
        self.assertEqual(timeout, posthog_module.FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS)

    def test_client_sends_events_inline_with_a_bounded_timeout(self):
        """Events are sent in the calling thread, so nothing is left to flush or hang at exit."""
        with patch("posthog.Posthog") as mock_posthog_cls:
            get_posthog_client("us-1")

        kwargs = mock_posthog_cls.call_args.kwargs
        self.assertTrue(kwargs["sync_mode"])
        self.assertEqual(kwargs["timeout"], posthog_module.CAPTURE_REQUEST_TIMEOUT_SECONDS)

    def test_library_errors_stay_out_of_the_terminal(self):
        """An offline send must not print the library's traceback on every command."""
        import logging

        with patch("posthog.Posthog"):
            get_posthog_client("us-1")

        self.assertEqual(logging.getLogger("posthog").level, logging.CRITICAL)


class GetUserIdentityTest(unittest.TestCase):
    """Tests for get_user_identity: email, then install id, then OS username."""

    def test_signed_in_email_is_the_identity(self):
        """After a sign-in the distinct id is the email the web app also uses."""
        save_signin_identity("studio", "ada@example.com", "acc-1")

        self.assertEqual(get_user_identity(), "ada@example.com")

    def test_last_sign_in_wins(self):
        """With sign-ins on two regions, the most recent one is used."""
        save_signin_identity("studio", "ada@example.com", "acc-1")
        save_signin_identity("us-1", "ada@corp.com", "corp-us")

        self.assertEqual(get_user_identity(), "ada@corp.com")

    def test_before_sign_in_the_install_id_is_used_and_kept(self):
        """No sign-in yet: a random per-machine id, the same on every call."""
        first = get_user_identity()

        self.assertTrue(first.startswith("anon:"))
        self.assertEqual(get_user_identity(), first)

    def test_username_is_the_last_fallback(self):
        """If the install id cannot be stored, the OS username is used."""
        with (
            patch.object(posthog_module, "TELEMETRY_FILE_PATH", "/nonexistent-dir/\0/t.json"),
            patch("getpass.getuser", return_value="ada"),
        ):
            self.assertEqual(get_user_identity(), "ada")

    def test_old_credentials_file_still_parses(self):
        """A file with only region keys has no identity, and its keys still load."""
        with open(credentials_module.CREDENTIALS_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"studio": "key-1"}, f)

        self.assertIsNone(load_signin_identity())
        self.assertEqual(credentials_module.load_api_key_from_credential_file("studio"), "key-1")
        self.assertTrue(get_user_identity().startswith("anon:"))

    def test_saving_an_identity_keeps_the_keys(self):
        """The identity sits beside the region keys without touching them."""
        save_api_key_credential_file("key-1", region="studio")
        save_signin_identity("studio", "ada@example.com", "acc-1")
        save_api_key_credential_file("key-2", region="us-1")

        with open(credentials_module.CREDENTIALS_FILE_PATH, encoding="utf-8") as f:
            stored = json.load(f)
        self.assertEqual(stored["studio"], "key-1")
        self.assertEqual(stored["us-1"], "key-2")
        self.assertEqual(stored["identities"]["studio"]["email"], "ada@example.com")
        self.assertEqual(oct(os.stat(credentials_module.CREDENTIALS_FILE_PATH).st_mode)[-3:], "600")


class IdentifySigninTest(unittest.TestCase):
    """Tests for identify_signin: save the identity, alias the install id once."""

    def setUp(self):
        self.client = MagicMock()
        patch("poly.handlers.posthog.get_posthog_client", return_value=self.client).start()
        self.addCleanup(patch.stopall)

    def test_first_sign_in_aliases_the_install_id(self):
        """Events sent before the first sign-in join the person."""
        install_id = get_user_identity()

        identify_signin("studio", "ada@example.com", "acc-1")

        self.client.alias.assert_called_once_with(
            previous_id=install_id, distinct_id="ada@example.com"
        )

    def test_later_sign_ins_do_not_alias_again(self):
        """Only the machine's first sign-in merges its install id."""
        identify_signin("studio", "ada@example.com")
        identify_signin("us-1", "ada@corp.com")

        self.assertEqual(self.client.alias.call_count, 1)

    def test_opt_out_saves_identity_but_sends_nothing(self):
        """The identity is local; with the opt-out set no alias is sent."""
        with patch.dict(os.environ, {"POLY_NO_TELEMETRY": "1"}):
            identify_signin("studio", "ada@example.com")

        self.client.alias.assert_not_called()
        self.assertEqual(load_signin_identity()["email"], "ada@example.com")


class TrackTest(unittest.TestCase):
    """Tests for track: person, groups and base properties on every CLI event."""

    def setUp(self):
        self.capture = patch("poly.handlers.posthog.capture_event", return_value=True).start()
        self.addCleanup(patch.stopall)

    def _sent(self) -> tuple:
        call = self.capture.call_args
        return call.args[1], call.args[2], call.args[3], call.kwargs["groups"]

    def test_signed_in_event_goes_to_the_person_with_groups(self):
        """The email is the distinct id, the account is the company group."""
        save_signin_identity("studio", "ada@example.com", "acc-1")

        track("studio", "cli_command_completed", command="pull")

        event, properties, distinct_id, groups = self._sent()
        self.assertEqual(event, "cli_command_completed")
        self.assertEqual(distinct_id, "ada@example.com")
        self.assertEqual(groups, {"company": "acc-1", "cluster": "plg-us-1-prod"})
        self.assertEqual(properties["command"], "pull")

    def test_base_properties_are_on_every_event(self):
        """OS, Python, ADK version, install method, invoking agent and TTY."""
        with patch.dict(os.environ, {"CURSOR_AGENT": "1"}):
            track(None, "e")

        _, properties, _, groups = self._sent()
        self.assertEqual(
            set(properties),
            {
                "os",
                "python_version",
                "adk_version",
                "install_method",
                "invoking_agent",
                "interactive",
            },
        )
        self.assertEqual(properties["invoking_agent"], "cursor")
        self.assertEqual(groups, {})

    def test_none_properties_are_left_out(self):
        """An unset property is not sent as null."""
        track(None, "e", ref=None, source="login")

        _, properties, _, _ = self._sent()
        self.assertNotIn("ref", properties)
        self.assertEqual(properties["source"], "login")

    def test_opt_out_builds_nothing(self):
        """With the opt-out set nothing is built or sent."""
        with patch.dict(os.environ, {"DO_NOT_TRACK": "1"}):
            self.assertFalse(track("studio", "e"))

        self.capture.assert_not_called()

    def test_a_failure_building_the_event_is_swallowed(self):
        """A broken identity lookup never fails the command."""
        with patch("poly.handlers.posthog.base_properties", side_effect=RuntimeError("boom")):
            self.assertFalse(track("studio", "e"))


class SignupRefTest(unittest.TestCase):
    """Tests for signup_ref: short tags only."""

    def test_valid_and_invalid_refs(self):
        """Tags pass; anything with spaces, slashes or over 64 characters is dropped."""
        for ref, expected in (
            ("docs", "docs"),
            ("devhome.7f3a9c2e", "devhome.7f3a9c2e"),
            ("a:b-c_d", "a:b-c_d"),
            ("has space", None),
            ("../etc", None),
            ("x" * 65, None),
            ("", None),
        ):
            with self.subTest(ref=ref):
                self.assertEqual(signup_ref(ref), expected)

    def test_environment_is_read_when_no_flag(self):
        """POLY_SIGNUP_REF is used when --ref is not passed."""
        with patch.dict(os.environ, {"POLY_SIGNUP_REF": "docs"}):
            self.assertEqual(signup_ref(None), "docs")
            self.assertEqual(signup_ref("site"), "site")


class CaptureEventTest(unittest.TestCase):
    """Tests for capture_event, the fire-and-forget analytics capture helper."""

    def setUp(self):
        self.client = MagicMock()
        self.client_patcher = patch(
            "poly.handlers.posthog.get_posthog_client", return_value=self.client
        )
        self.client_patcher.start()
        # The developer running the suite may have opted out themselves.
        env = {k: v for k, v in os.environ.items() if k not in TELEMETRY_OPT_OUT_ENV_VARS}
        patch.dict(os.environ, env, clear=True).start()

    def tearDown(self):
        patch.stopall()

    def test_sends_event_with_distinct_id_and_properties(self):
        """A capture call is forwarded to the region's client with the given fields."""
        from poly.handlers.posthog import capture_event

        sent = capture_event("studio", "apikey_signup", {"source": "apikey"}, "acc-1")

        self.assertTrue(sent)
        self.client.capture.assert_called_once_with(
            event="apikey_signup",
            distinct_id="acc-1",
            properties={"source": "apikey"},
            disable_geoip=False,
        )

    def test_groups_are_forwarded_when_given(self):
        """Groups go to the client as-is."""
        from poly.handlers.posthog import capture_event

        capture_event("studio", "e", {}, "me@x.com", groups={"company": "acc-1"})

        self.assertEqual(self.client.capture.call_args.kwargs["groups"], {"company": "acc-1"})

    def test_unknown_region_lands_in_the_production_project(self):
        """Before a region is chosen, events go to the production PostHog project."""
        from poly.handlers.posthog import capture_event

        with patch("poly.handlers.posthog.get_posthog_client") as mock_get_client:
            capture_event(None, "setup_started", {}, "anon:1")

        mock_get_client.assert_called_once_with("")

    def test_client_failure_is_swallowed_and_reported(self):
        """A slow or unreachable PostHog must never fail the caller."""
        from poly.handlers.posthog import capture_event

        self.client.capture.side_effect = RuntimeError("connection reset")

        sent = capture_event("studio", "apikey_signup", {"source": "apikey"}, "acc-1")

        self.assertFalse(sent)

    def test_opt_out_variables_suppress_the_event(self):
        """POLY_NO_TELEMETRY or DO_NOT_TRACK set to anything sends nothing."""
        from poly.handlers.posthog import capture_event

        for name in TELEMETRY_OPT_OUT_ENV_VARS:
            with self.subTest(variable=name), patch.dict(os.environ, {name: "1"}):
                sent = capture_event("studio", "apikey_signup", {"source": "apikey"}, "acc-1")

                self.assertFalse(sent)
                self.client.capture.assert_not_called()

    def test_opt_out_variable_set_to_empty_does_not_opt_out(self):
        """An empty variable is treated as unset, matching the DO_NOT_TRACK convention."""
        from poly.handlers.posthog import capture_event

        with patch.dict(os.environ, {"DO_NOT_TRACK": ""}):
            self.assertTrue(capture_event("studio", "e", {}, "acc-1"))
