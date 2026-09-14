"""Client for the PolyAI Posthog tenant, used for feature flags in the PolyAI ADK CLI.

Copyright PolyAI Limited
"""

import logging
from typing import TYPE_CHECKING

POSTHOG_HOST = "https://eu.i.posthog.com"

# Public client-side project keys, safe to commit. One PostHog project per
# environment.
POSTHOG_KEY_PROD = "phc_oBh3uJGQWyQkWdoxrTAEqghjkHSgjd5FGEn5vM6CyXBp"
POSTHOG_KEY_NON_PROD = "phc_kS54QZyZRqi9T77rWEUfJ49vVYY4ADKEPnRUrJ7RNnZ6"
NON_PROD_REGIONS = frozenset({"dev", "staging"})

FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS = 1
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from posthog import Posthog

# Keyed by project api key: a session can touch more than one region.
_clients: dict[str, Posthog] = {}

region_to_posthog_cluster = {
    "dev": "apollo",
}

# Anything unlisted is production.
region_to_cluster_env = {
    "dev": "dev",
    "staging": "staging",
}


def posthog_key_for_region(region: str) -> str:
    """The PostHog project a region's flags live in."""
    return POSTHOG_KEY_NON_PROD if (region or "").lower() in NON_PROD_REGIONS else POSTHOG_KEY_PROD


def get_posthog_client(region: str) -> Posthog:
    """Get a Posthog client for the region's PostHog project.

    Args:
        region (str): The region whose flags are being read.

    Returns:
        A Posthog client instance, cached per PostHog project.
    """
    from posthog import Posthog

    project_api_key = posthog_key_for_region(region)
    client = _clients.get(project_api_key)
    if client is None:
        client = Posthog(
            project_api_key=project_api_key,
            host=POSTHOG_HOST,
            feature_flags_request_timeout_seconds=FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS,
        )
        _clients[project_api_key] = client
    return client


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
        account_id: str | None = None,
    ) -> bool:
        """Evaluate a boolean feature flag against PostHog.

        Args:
            region: The region the user is in, used to determine the PostHog
                project and cluster.
            key: The PostHog feature flag key.
            default: Returned whenever the flag cannot be evaluated. Pick the
                safe state for the gated code path.
            project_id: The project ID. Namespaced by cluster to form the
                `project` group key, because project ids are minted per-cluster
                and several clusters share one PostHog project.
            account_id: The account ID, sent as a group property so
                account-scoped conditions can match. Omitted when unknown
                rather than sent empty, which would fail an exact condition.

        Returns:
            The flag value, or `default` if it cannot be evaluated.
        """
        try:
            client = get_posthog_client(region)
            if not client:
                return default

            cluster = region_to_posthog_cluster.get(region, region)
            env = region_to_cluster_env.get(region, "prod")

            groups = {"cluster": cluster}
            group_properties = {"cluster": {"cluster": cluster, "env": env}}
            if project_id:
                groups["project"] = f"{cluster}/{project_id}"
                group_properties["project"] = {
                    "project_id": project_id,
                    "cluster": cluster,
                    "env": env,
                }
                if account_id:
                    group_properties["project"]["account_id"] = account_id

            result = client.feature_enabled(
                key,
                distinct_id=get_user_identity(),
                groups=groups,
                group_properties=group_properties,
                send_feature_flag_events=False,
            )
        except Exception as exc:
            logger.warning(f"PostHog flag evaluation failed key={key}", exc_info=exc)
            return default

        return default if result is None else result
