"""Tests for the PostHog feature-flag handler.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.handlers import posthog as posthog_module
from poly.handlers.posthog import PosthogHandler, get_posthog_client, get_user_identity


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
            groups={"cluster": "studio", "project": "studio/proj-1"},
            group_properties={
                "cluster": {"cluster": "studio", "env": "prod"},
                "project": {
                    "project_id": "proj-1",
                    "cluster": "studio",
                    "env": "prod",
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

        project_properties = self.client.feature_enabled.call_args.kwargs[
            "group_properties"
        ]["project"]
        self.assertNotIn("account_id", project_properties)

    def test_non_production_regions_send_their_own_env(self):
        """The env property separates the two deployments sharing a cluster key."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(
            region="staging", key="some-flag", default=False, project_id="proj-1"
        )

        properties = self.client.feature_enabled.call_args.kwargs["group_properties"]
        self.assertEqual(properties["cluster"]["env"], "staging")

    def test_omits_project_group_when_no_project_id(self):
        """Without a project id only the cluster group is sent."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(region="studio", key="some-flag", default=False)

        self.assertEqual(
            self.client.feature_enabled.call_args.kwargs["groups"], {"cluster": "studio"}
        )

    def test_region_is_mapped_to_posthog_cluster(self):
        """Regions with a cluster alias are translated; others pass through unchanged."""
        self.client.feature_enabled.return_value = True

        for region, expected_cluster in (("dev", "apollo"), ("studio", "studio")):
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


class GetUserIdentityTest(unittest.TestCase):
    """Tests for get_user_identity, the PostHog distinct_id source."""

    def test_identity_is_the_local_username(self):
        """The distinct_id is the OS username, so rollouts bucket per developer."""
        with patch("getpass.getuser", return_value="ada"):
            self.assertEqual(get_user_identity(), "ada")


if __name__ == "__main__":
    unittest.main()
