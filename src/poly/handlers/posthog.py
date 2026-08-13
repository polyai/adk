"""Client for the PolyAI Posthog tenant, used for feature flags in the PolyAI ADK CLI.

Copyright PolyAI Limited
"""

import logging
from typing import TYPE_CHECKING

POSTHOG_HOST = "https://eu.i.posthog.com"
POSTHOG_KEY = "phc_kS54QZyZRqi9T77rWEUfJ49vVYY4ADKEPnRUrJ7RNnZ6"
FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS = 1
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from posthog import Posthog

_client: Posthog | None = None

region_to_posthog_cluster = {
    "dev": "apollo",
}


def get_posthog_client() -> Posthog:
    """Get a Posthog client instance.

    Returns:
        A Posthog client instance.
    """
    from posthog import Posthog

    global _client

    if _client is not None:
        return _client
    _client = Posthog(
        project_api_key=POSTHOG_KEY,
        host=POSTHOG_HOST,
        feature_flags_request_timeout_seconds=FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS,
    )
    return _client


def get_user_identity() -> str:
    """Get the user identity for Posthog feature flag evaluation.

    Returns:
        The user identity (distinct_id) for Posthog.
    """
    import getpass

    return getpass.getuser()


class PosthogHandler:
    """Handler for feature flags with the PolyAI Posthog tenant."""

    @staticmethod
    def is_feature_enabled(
        region: str,
        key: str,
        *,
        default: bool,
        project_id: str | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag against PostHog.

        Args:
            region: The region the user is in, used to determine the PostHog cluster.
            key: The PostHog feature flag key.
            default: Returned whenever the flag cannot be evaluated. Pick the
                safe state for the gated code path.
            project_id: The project ID (`project` group key). Workspace
                targeting goes through the `project` group — the workspace id
                lives on it as a group property in PostHog.

        Returns:
            The flag value, or `default` if it cannot be evaluated.
        """
        try:
            client = get_posthog_client()
            if not client:
                return default

            groups = {"cluster": region_to_posthog_cluster.get(region, region)}
            if project_id:
                groups["project"] = project_id
            result = client.feature_enabled(
                key,
                distinct_id=get_user_identity(),
                groups=groups,
                send_feature_flag_events=False,
            )
        except Exception as exc:
            logger.warning(f"PostHog flag evaluation failed key={key}", exc_info=exc)
            return default

        return default if result is None else result
