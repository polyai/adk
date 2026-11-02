"""Client for the PolyAI Posthog tenant: feature flags and analytics events for the ADK CLI.

Copyright PolyAI Limited
"""

import logging
import os
from typing import TYPE_CHECKING

POSTHOG_HOST = "https://eu.i.posthog.com"

# Public client-side project keys, safe to commit. One PostHog project per
# environment.
POSTHOG_KEY_PROD = "phc_oBh3uJGQWyQkWdoxrTAEqghjkHSgjd5FGEn5vM6CyXBp"
POSTHOG_KEY_NON_PROD = "phc_kS54QZyZRqi9T77rWEUfJ49vVYY4ADKEPnRUrJ7RNnZ6"
NON_PROD_REGIONS = frozenset({"dev", "staging"})

FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS = 1
# Events are sent inline (sync mode), so this bounds how long a command waits on one.
CAPTURE_REQUEST_TIMEOUT_SECONDS = 3
# Either variable set to anything suppresses every analytics event. DO_NOT_TRACK is the
# cross-tool convention (https://consoledonottrack.com); POLY_NO_TELEMETRY is ours.
TELEMETRY_OPT_OUT_ENV_VARS = ("POLY_NO_TELEMETRY", "DO_NOT_TRACK")
logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from posthog import Posthog

# Keyed by project api key: a session can touch more than one region.
_clients: dict[str, Posthog] = {}

region_to_posthog_cluster = {
    "dev": "apollo",
    "studio": "plg-us-1-prod",
}

# Anything unlisted is production.
region_to_cluster_env = {
    "dev": "dev",
    "staging": "staging",
    "studio": "plg",
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
            timeout=CAPTURE_REQUEST_TIMEOUT_SECONDS,
            sync_mode=True,
        )
        _clients[project_api_key] = client
    return client


def telemetry_disabled() -> bool:
    """Whether the user has opted out of analytics events via the environment.

    Feature flags are unaffected: they read configuration, they do not report usage.
    """
    return any(os.environ.get(name) for name in TELEMETRY_OPT_OUT_ENV_VARS)


def capture_event(region: str | None, event: str, properties: dict, distinct_id: str) -> bool:
    """Send an analytics event to PostHog. Fire-and-forget: never raises.

    Args:
        region: The region whose PostHog project the event should land in. ``None``
            (region not chosen yet) lands in the production project.
        event: The event name.
        properties: Event properties.
        distinct_id: The PostHog distinct id to attach the event to.

    Returns:
        True if the event was handed to the client, False if it was suppressed by
        the opt-out or the client raised. Callers can use a False to stop sending
        further events in a run rather than wait on every timeout.
    """
    if telemetry_disabled():
        logger.debug("Telemetry opt-out set; not sending event=%s", event)
        return False
    try:
        get_posthog_client(region or "").capture(
            event=event, distinct_id=distinct_id, properties=properties
        )
    except Exception as exc:
        logger.warning(f"PostHog event capture failed event={event}", exc_info=exc)
        return False
    return True


def alias_identity(region: str | None, anonymous_id: str, distinct_id: str) -> bool:
    """Link an anonymous id to a known identity in PostHog. Fire-and-forget: never raises.

    Events sent under ``anonymous_id`` before sign-in then count towards
    ``distinct_id`` (the account id) in funnels.

    Returns:
        True if the alias was handed to the client, False otherwise.
    """
    if telemetry_disabled():
        return False
    try:
        get_posthog_client(region or "").alias(previous_id=anonymous_id, distinct_id=distinct_id)
    except Exception as exc:
        logger.warning("PostHog alias failed", exc_info=exc)
        return False
    return True


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
