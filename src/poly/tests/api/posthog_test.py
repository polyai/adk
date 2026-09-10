"""Tests for the PostHog feature-flag handler.

Copyright PolyAI Limited
"""

import importlib
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from poly.handlers import posthog as posthog_module
from poly.handlers.posthog import (
    PosthogHandler,
    capture_event,
    flush,
    get_anonymous_id,
    get_posthog_client,
    get_user_identity,
    telemetry_disabled,
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

    def test_posthog_sdk_logger_is_raised_to_error_at_import(self):
        """Importing the module silences the third-party posthog logger.

        It must happen at import time (not inside get_posthog_client), so the
        feature-flag path and the capture path behave the same regardless of
        which runs first. Reloading the module re-triggers that import-time
        side effect, which is what this test actually exercises.
        """
        posthog_logger = logging.getLogger("posthog")
        original_level = posthog_logger.level
        posthog_logger.setLevel(logging.WARNING)
        try:
            importlib.reload(posthog_module)
            self.assertEqual(posthog_logger.level, logging.ERROR)
        finally:
            posthog_logger.setLevel(original_level)
            importlib.reload(posthog_module)


class GetUserIdentityTest(unittest.TestCase):
    """Tests for get_user_identity, the PostHog distinct_id source."""

    def test_identity_is_the_local_username(self):
        """The distinct_id is the OS username, so rollouts bucket per developer."""
        with patch("getpass.getuser", return_value="ada"):
            self.assertEqual(get_user_identity(), "ada")


class TelemetryDisabledTest(unittest.TestCase):
    """Tests for telemetry_disabled's env var handling."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        os.environ.pop("DO_NOT_TRACK", None)
        os.environ.pop("POLY_NO_TELEMETRY", None)

    def tearDown(self):
        self._env_patch.stop()

    def test_disabled_by_default(self):
        """With neither env var set, telemetry is enabled."""
        self.assertFalse(telemetry_disabled())

    def test_do_not_track_disables_telemetry(self):
        """DO_NOT_TRACK=1 or =true disables telemetry, case-insensitively."""
        for value in ("1", "true", "True", "TRUE"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"DO_NOT_TRACK": value}):
                    self.assertTrue(telemetry_disabled())

    def test_poly_telemetry_disables_telemetry(self):
        """POLY_NO_TELEMETRY=1 or =true disables telemetry, case-insensitively."""
        for value in ("1", "true", "True"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"POLY_NO_TELEMETRY": value}):
                    self.assertTrue(telemetry_disabled())

    def test_other_values_do_not_disable_telemetry(self):
        """A falsy or unrelated value leaves telemetry enabled."""
        for value in ("0", "false", "no", ""):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"DO_NOT_TRACK": value}):
                    self.assertFalse(telemetry_disabled())


class GetAnonymousIdTest(unittest.TestCase):
    """Tests for get_anonymous_id's persisted UUID."""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._path_patch = patch.object(
            posthog_module, "TELEMETRY_ID_PATH", str(Path(self._tmp_dir.name) / "telemetry_id")
        )
        self._path_patch.start()

    def tearDown(self):
        self._path_patch.stop()
        self._tmp_dir.cleanup()

    def test_creates_and_persists_a_uuid(self):
        """A missing telemetry id file is created with a UUID, mode 600."""
        first = get_anonymous_id()

        path = Path(posthog_module.TELEMETRY_ID_PATH)
        self.assertTrue(path.is_file())
        if os.name != "nt":
            # Windows doesn't enforce POSIX mode bits - chmod only toggles read-only.
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_text(encoding="utf-8"), first)

    def test_reuses_existing_id(self):
        """A second call returns the same id as the first, rather than a new one."""
        first = get_anonymous_id()
        second = get_anonymous_id()

        self.assertEqual(first, second)


class CaptureEventTest(unittest.TestCase):
    """Tests for capture_event's telemetry-opt-out and failure handling."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        os.environ.pop("DO_NOT_TRACK", None)
        os.environ.pop("POLY_NO_TELEMETRY", None)

    def tearDown(self):
        self._env_patch.stop()

    def test_disabled_env_var_means_no_client_call(self):
        """When telemetry is disabled, get_posthog_client is never even reached."""
        with (
            patch.dict(os.environ, {"DO_NOT_TRACK": "1"}),
            patch("poly.handlers.posthog.get_posthog_client") as mock_get_client,
        ):
            capture_event("studio", "apikey_started", {}, "anon-1")

        mock_get_client.assert_not_called()

    def test_forwards_event_and_properties_unchanged(self):
        """capture_event passes distinct_id/event/properties straight through."""
        mock_client = MagicMock()
        properties = {"source": "apikey", "account_id": "acc-1"}
        with patch("poly.handlers.posthog.get_posthog_client", return_value=mock_client):
            capture_event("studio", "apikey_account_resolved", properties, "anon-1")

        mock_client.capture.assert_called_once_with(
            distinct_id="anon-1", event="apikey_account_resolved", properties=properties
        )
        # No accidental secret leakage: only what the caller passed is sent.
        sent_properties = mock_client.capture.call_args.kwargs["properties"]
        self.assertNotIn("key", sent_properties)
        self.assertNotIn("token", sent_properties)

    def test_client_exception_is_swallowed(self):
        """A PostHog failure never propagates out of capture_event."""
        mock_client = MagicMock()
        mock_client.capture.side_effect = RuntimeError("connection reset")
        with patch("poly.handlers.posthog.get_posthog_client", return_value=mock_client):
            capture_event("studio", "apikey_started", {}, "anon-1")  # must not raise

    def test_client_lookup_exception_is_swallowed(self):
        """A failure building the client never propagates out of capture_event."""
        with patch(
            "poly.handlers.posthog.get_posthog_client", side_effect=RuntimeError("boom")
        ):
            capture_event("studio", "apikey_started", {}, "anon-1")  # must not raise


class FlushTest(unittest.TestCase):
    """Tests for flush's telemetry-opt-out and failure handling."""

    def setUp(self):
        self._env_patch = patch.dict(os.environ, {}, clear=False)
        self._env_patch.start()
        os.environ.pop("DO_NOT_TRACK", None)
        os.environ.pop("POLY_NO_TELEMETRY", None)

    def tearDown(self):
        self._env_patch.stop()

    def test_disabled_env_var_means_no_client_call(self):
        """When telemetry is disabled, flush never reaches the client."""
        with (
            patch.dict(os.environ, {"DO_NOT_TRACK": "1"}),
            patch("poly.handlers.posthog.get_posthog_client") as mock_get_client,
        ):
            flush("studio")

        mock_get_client.assert_not_called()

    def test_flushes_with_the_given_timeout(self):
        """flush forwards the timeout to the underlying client."""
        mock_client = MagicMock()
        with patch("poly.handlers.posthog.get_posthog_client", return_value=mock_client):
            flush("studio", timeout_seconds=5.0)

        mock_client.flush.assert_called_once_with(timeout_seconds=5.0)

    def test_default_timeout_is_five_seconds(self):
        """The default flush budget is 5s, not the SDK's own default."""
        mock_client = MagicMock()
        with patch("poly.handlers.posthog.get_posthog_client", return_value=mock_client):
            flush("studio")

        mock_client.flush.assert_called_once_with(timeout_seconds=5.0)
        self.assertEqual(posthog_module.DEFAULT_FLUSH_TIMEOUT_SECONDS, 5.0)

    def test_client_exception_is_swallowed(self):
        """A PostHog failure never propagates out of flush."""
        mock_client = MagicMock()
        mock_client.flush.side_effect = RuntimeError("connection reset")
        with patch("poly.handlers.posthog.get_posthog_client", return_value=mock_client):
            flush("studio")  # must not raise


if __name__ == "__main__":
    unittest.main()
