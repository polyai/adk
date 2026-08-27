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
        """The flag key, distinct_id and project group are forwarded to PostHog."""
        self.client.feature_enabled.return_value = True

        PosthogHandler.is_feature_enabled(
            region="studio",
            key="deployment-simplification",
            default=False,
            project_id="proj-1",
        )

        self.client.feature_enabled.assert_called_once_with(
            "deployment-simplification",
            distinct_id="test-user",
            groups={"cluster": "studio", "project": "proj-1"},
            send_feature_flag_events=False,
        )

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


class GetPosthogClientTest(unittest.TestCase):
    """Tests for the module-level PostHog client singleton."""

    def setUp(self):
        self.original_client = posthog_module._client
        posthog_module._client = None

    def tearDown(self):
        posthog_module._client = self.original_client

    def test_client_is_constructed_once_and_reused(self):
        """The client is built on first use and cached for subsequent calls."""
        with patch("posthog.Posthog") as mock_posthog_cls:
            first = get_posthog_client()
            second = get_posthog_client()

        self.assertIs(first, second)
        mock_posthog_cls.assert_called_once()

    def test_client_is_configured_with_a_request_timeout(self):
        """A feature-flag read is bounded so the CLI cannot hang on PostHog."""
        with patch("posthog.Posthog") as mock_posthog_cls:
            get_posthog_client()

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
