"""Client for the PolyAI Posthog tenant: feature flags and analytics events for the ADK CLI.

Copyright PolyAI Limited
"""

import json
import logging
import os
import platform
import re
import sys
import uuid
from typing import TYPE_CHECKING

POSTHOG_HOST = "https://eu.i.posthog.com"

# Public client-side project keys, safe to commit. One PostHog project per
# environment.
POSTHOG_KEY_PROD = "phc_oBh3uJGQWyQkWdoxrTAEqghjkHSgjd5FGEn5vM6CyXBp"
POSTHOG_KEY_NON_PROD = "phc_kS54QZyZRqi9T77rWEUfJ49vVYY4ADKEPnRUrJ7RNnZ6"
NON_PROD_REGIONS = frozenset({"dev", "staging"})

FEATURE_FLAGS_REQUEST_TIMEOUT_SECONDS = 1
# Events are sent inline (sync mode), so this bounds how long a command waits on one.
# Every command sends one on exit, so an offline run must not stall on it.
CAPTURE_REQUEST_TIMEOUT_SECONDS = 1
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
        # The library logs a full traceback when it cannot connect (and resets its
        # logger's level when built). Every command sends an event, so keep that out
        # of an offline user's terminal unless they asked for --debug.
        if not logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.getLogger("posthog").setLevel(logging.CRITICAL)
        _clients[project_api_key] = client
    return client


def telemetry_disabled() -> bool:
    """Whether the user has opted out of analytics events via the environment.

    Feature flags are unaffected: they read configuration, they do not report usage.
    """
    return any(os.environ.get(name) for name in TELEMETRY_OPT_OUT_ENV_VARS)


def capture_event(
    region: str | None,
    event: str,
    properties: dict,
    distinct_id: str,
    groups: dict | None = None,
) -> bool:
    """Send an analytics event to PostHog. Fire-and-forget: never raises.

    Args:
        region: The region whose PostHog project the event should land in. ``None``
            (region not chosen yet) lands in the production project.
        event: The event name.
        properties: Event properties.
        distinct_id: The PostHog distinct id to attach the event to.
        groups: PostHog groups (``company``, ``cluster``) to attach, if any.

    Returns:
        True if the event was handed to the client, False if it was suppressed by
        the opt-out or the client raised. Callers can use a False to stop sending
        further events in a run rather than wait on every timeout.
    """
    if telemetry_disabled():
        logger.debug("Telemetry opt-out set; not sending event=%s", event)
        return False
    try:
        extra = {"groups": groups} if groups else {}
        get_posthog_client(region or "").capture(
            event=event,
            distinct_id=distinct_id,
            properties=properties,
            # Sent from the developer's own machine, so the IP gives their country.
            disable_geoip=False,
            **extra,
        )
    except Exception as exc:
        logger.warning(f"PostHog event capture failed event={event}", exc_info=exc)
        return False
    return True


# Holds the install id: a random id per machine, used until someone signs in.
TELEMETRY_FILE_PATH = os.path.join(os.path.expanduser("~/.poly"), "telemetry.json")
_INSTALL_ID_PREFIX = "anon:"

# Environment variables a coding agent sets in the processes it spawns.
AGENT_ENV_MARKERS = {
    "CLAUDECODE": "claude-code",
    "CURSOR_AGENT": "cursor",
    "CODEX_SANDBOX": "codex",
}

# Where a sign-up came from (the copied prompt, a docs page). Analytics only, so
# anything that does not look like a short tag is dropped rather than rejected.
SIGNUP_REF_ENV_VAR = "POLY_SIGNUP_REF"
_REF_PATTERN = re.compile(r"[A-Za-z0-9._:-]{1,64}")


def invoking_agent() -> str:
    """Name the coding agent that spawned this process, or ``"none"``."""
    return next((a for var, a in AGENT_ENV_MARKERS.items() if os.environ.get(var)), "none")


def signup_ref(ref: str | None = None) -> str | None:
    """The sign-up ref from ``--ref`` or ``POLY_SIGNUP_REF``, if it is a valid tag."""
    value = ref if ref is not None else os.environ.get(SIGNUP_REF_ENV_VAR)
    if value and _REF_PATTERN.fullmatch(value):
        return value
    return None


def _install_method() -> str:
    """How the CLI was installed, as ``poly update`` detects it. Best effort."""
    try:
        from poly.cli_commands.update import UpdateCommand

        return UpdateCommand._detect_install_method()
    except Exception:
        return "unknown"


def base_properties() -> dict:
    """Diagnostic properties sent on every CLI event."""
    from poly.cli_commands.shared import get_package_version

    return {
        "os": platform.system().lower(),
        "python_version": platform.python_version(),
        "adk_version": get_package_version(),
        "install_method": _install_method(),
        "invoking_agent": invoking_agent(),
        "interactive": sys.stdin.isatty(),
    }


def _install_id() -> str | None:
    """The machine's install id, created on first use. None if it cannot be stored."""
    try:
        with open(TELEMETRY_FILE_PATH, "r", encoding="utf-8") as f:
            install_id = json.load(f).get("install_id")
        if isinstance(install_id, str) and install_id.startswith(_INSTALL_ID_PREFIX):
            return install_id
    except (OSError, ValueError, AttributeError):
        pass
    install_id = f"{_INSTALL_ID_PREFIX}{uuid.uuid4()}"
    try:
        os.makedirs(os.path.dirname(TELEMETRY_FILE_PATH), exist_ok=True)
        with open(TELEMETRY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump({"install_id": install_id}, f, indent=4)
    except OSError:
        return None
    return install_id


def get_user_identity() -> str:
    """The PostHog distinct id for this person.

    In order: the email of the last sign-in (the same id the web app uses), the
    machine's install id, then the OS username if neither can be found or stored.
    """
    from poly.utils.credentials import load_signin_identity

    identity = load_signin_identity()
    if identity:
        return identity["email"]
    install_id = _install_id()
    if install_id:
        return install_id
    import getpass

    return getpass.getuser()


def _identity_groups(region: str | None) -> dict:
    """PostHog groups for the signed-in account and the region's cluster."""
    from poly.utils.credentials import load_signin_identity

    groups = {}
    identity = load_signin_identity()
    if identity and identity.get("account_id"):
        groups["company"] = identity["account_id"]
    if region:
        groups["cluster"] = region_to_posthog_cluster.get(region, region)
    return groups


# Extra properties a command adds to its own ``cli_command_completed`` event,
# such as the step it failed on. Reset at the start of every command.
_command_properties: dict = {}


def add_command_properties(**properties: object) -> None:
    """Attach properties to the running command's ``cli_command_completed`` event."""
    _command_properties.update({k: v for k, v in properties.items() if v is not None})


def command_properties() -> dict:
    """The properties added so far for the running command."""
    return dict(_command_properties)


def drop_command_properties(*keys: str) -> None:
    """Remove properties a nested step added but its caller recovered from."""
    for key in keys:
        _command_properties.pop(key, None)


def reset_command_properties() -> None:
    """Forget the properties added for the previous command."""
    _command_properties.clear()


def track(region: str | None, event: str, **properties: object) -> bool:
    """Send a CLI event for the current person, with the base properties and groups.

    Returns:
        What ``capture_event`` returns; False if building the event failed.
    """
    if telemetry_disabled():
        return False
    try:
        payload = {**base_properties(), **{k: v for k, v in properties.items() if v is not None}}
        distinct_id = get_user_identity()
        groups = _identity_groups(region)
    except Exception as exc:
        logger.warning(f"Could not build PostHog event={event}", exc_info=exc)
        return False
    return capture_event(region, event, payload, distinct_id, groups=groups)


def identify_signin(region: str, email: str, account_id: str | None = None) -> None:
    """Record a sign-in and join this machine's earlier events to the person.

    Saves the identity next to the keys, then, the first time this machine signs
    in, aliases its install id to the email so events sent before sign-in join
    the person. Never raises.
    """
    from poly.utils.credentials import load_signin_identity, save_signin_identity

    first_signin = load_signin_identity() is None
    save_signin_identity(region, email, account_id)
    if not first_signin or telemetry_disabled():
        return
    install_id = _install_id()
    if not install_id:
        return
    try:
        get_posthog_client(region).alias(previous_id=install_id, distinct_id=email)
    except Exception as exc:
        logger.warning("PostHog alias failed", exc_info=exc)


def report_signin(
    region: str,
    auth_response: dict | None,
    *,
    source: str,
    ref: str | None = None,
    account_id: str | None = None,
) -> None:
    """Record a CLI sign-in and send ``cli_signup`` if it created the person's account.

    Only studio counts as a sign-up: on enterprise regions ``is_first_login`` is
    also true for a user invited into an existing account. Never raises.

    Args:
        region: The region signed in to.
        auth_response: The ``/authorise`` response (``{"user": {"email", ...}}``).
        source: The command the sign-up came through: apikey, login or setup.
        ref: Where the sign-up started, from ``--ref`` or ``POLY_SIGNUP_REF``.
        account_id: The account the sign-in resolved to, when known.
    """
    try:
        user = (auth_response or {}).get("user") or {}
        email = user.get("email")
        if not isinstance(email, str) or not email:
            return
        identify_signin(region, email, account_id)
        if region == "studio" and user.get("is_first_login"):
            properties = {
                "source": source,
                "ref": signup_ref(ref),
                "auth_provider": user.get("auth_provider"),
            }
            track(region, "cli_signup", **properties)
    except Exception as exc:
        logger.warning("Could not report the sign-in", exc_info=exc)


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
