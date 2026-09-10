"""Client for the PolyAI Posthog tenant, used for feature flags in the PolyAI ADK CLI.

Copyright PolyAI Limited
"""

import logging
import os
import uuid
from typing import TYPE_CHECKING

POSTHOG_HOST = "https://eu.i.posthog.com"

# Public client-side project keys, safe to commit. One PostHog project per
# environment.
POSTHOG_KEY_PROD = "phc_oBh3uJGQWyQkWdoxrTAEqghjkHSgjd5FGEn5vM6CyXBp"
POSTHOG_KEY_NON_PROD = "phc_kS54QZyZRqi9T77rWEUfJ49vVYY4ADKEPnRUrJ7RNnZ6"
NON_PROD_REGIONS = frozenset({"dev", "staging"})

FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS = 1
DEFAULT_FLUSH_TIMEOUT_SECONDS = 5.0

TELEMETRY_ID_PATH = os.path.expanduser("~/.poly/telemetry_id")

logger = logging.getLogger(__name__)

# The posthog SDK logs its own warnings (e.g. a flush running out of budget)
# at WARNING level, which would otherwise leak into a user's terminal. Our
# own logger.warning calls for capture/flush failures are unaffected - only
# the third-party SDK logger is raised, and once, at import time, so it
# behaves the same regardless of which entry point (feature flags or
# capture) is used first.
logging.getLogger("posthog").setLevel(logging.ERROR)


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


def _is_truthy_flag(value: str | None) -> bool:
    """Whether an env var value means "on" (`"1"` or `"true"`, case-insensitive)."""
    return (value or "").strip().lower() in {"1", "true"}


def telemetry_disabled() -> bool:
    """Whether telemetry capture is opted out of via environment variable.

    Returns:
        bool: True if `DO_NOT_TRACK` or `POLY_NO_TELEMETRY` is set to `1`/`true`.
    """
    return _is_truthy_flag(os.environ.get("DO_NOT_TRACK")) or _is_truthy_flag(
        os.environ.get("POLY_NO_TELEMETRY")
    )


def get_anonymous_id() -> str:
    """Get (or create) a stable anonymous id for this machine's telemetry events.

    Returns:
        str: A UUID4, persisted at `~/.poly/telemetry_id` (mode 600) so it is
            stable across CLI invocations.
    """
    if os.path.isfile(TELEMETRY_ID_PATH):
        try:
            with open(TELEMETRY_ID_PATH, "r", encoding="utf-8") as f:
                existing = f.read().strip()
            if existing:
                return existing
        except OSError:
            logger.warning(f"Could not read telemetry id at {TELEMETRY_ID_PATH!r}.")

    new_id = str(uuid.uuid4())
    os.makedirs(os.path.dirname(TELEMETRY_ID_PATH), exist_ok=True)
    with open(TELEMETRY_ID_PATH, "w", encoding="utf-8") as f:
        f.write(new_id)
    os.chmod(TELEMETRY_ID_PATH, 0o600)
    return new_id


def capture_event(region: str, event: str, properties: dict, distinct_id: str) -> None:
    """Capture a telemetry event, never raising and never blocking on a slow network.

    A no-op when telemetry is disabled. Any failure to reach PostHog is
    logged at warning level and swallowed - telemetry must never break or
    slow down the command it is instrumenting.

    Args:
        region: The region the event relates to, used to pick the PostHog project.
        event: The event name.
        properties: Event properties. Must never include secrets (API keys, JWTs).
        distinct_id: The PostHog distinct id to attribute the event to.
    """
    if telemetry_disabled():
        return
    try:
        client = get_posthog_client(region)
        client.capture(distinct_id=distinct_id, event=event, properties=properties)
    except Exception as exc:
        logger.warning(f"PostHog capture failed event={event!r}", exc_info=exc)


def flush(region: str, timeout_seconds: float = DEFAULT_FLUSH_TIMEOUT_SECONDS) -> None:
    """Flush any buffered telemetry events before the process exits.

    Bounded by `timeout_seconds` so a slow or unreachable PostHog can't hang
    process exit. Any failure is logged at warning level and swallowed.

    Args:
        region: The region whose PostHog client should be flushed.
        timeout_seconds: Maximum time to wait for the flush to complete.
    """
    if telemetry_disabled():
        return
    try:
        client = get_posthog_client(region)
        client.flush(timeout_seconds=timeout_seconds)
    except Exception as exc:
        logger.warning("PostHog flush failed", exc_info=exc)


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
