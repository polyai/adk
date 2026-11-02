"""API key credential storage and retrieval.

Copyright PolyAI Limited
"""

import json
import logging
import os
from typing import Optional

from poly.constants import POLY_HOME_DIR, region_display_name

logger = logging.getLogger(__name__)

_API_KEY_ENV_VAR = "POLY_ADK_KEY"

_REGION_TO_KEY_SUFFIX: dict[str, str] = {
    "us-1": "US",
    "euw-1": "EUW",
    "uk-1": "UK",
    "studio": "STUDIO",
    "staging": "STAGING",
    "dev": "DEV",
}

CREDENTIALS_FILE_PATH = os.path.join(POLY_HOME_DIR, "credentials.json")

# Account API keys (for the PolyAI APIs and MCPs) live under this field, keyed by
# region, so they are never confused with the ADK keys stored at the top level.
ACCOUNT_KEYS_FIELD = "account_keys"


def _read_credentials_file(on_error: str) -> dict:
    """The parsed credentials file, or ``{}`` if it is absent or does not parse.

    Args:
        on_error: What the warning says will happen to an unparseable file.
    """
    if not os.path.isfile(CREDENTIALS_FILE_PATH):
        return {}
    with open(CREDENTIALS_FILE_PATH, "r", encoding="utf-8") as f:
        try:
            credentials = json.load(f)
        except json.JSONDecodeError:
            logger.warning(
                f"Could not parse credentials file at {CREDENTIALS_FILE_PATH!r}. {on_error}"
            )
            return {}
    return credentials if isinstance(credentials, dict) else {}


def _write_credentials_file(credentials: dict) -> None:
    """Write the credentials file, readable and writeable only by the user."""
    os.makedirs(os.path.dirname(CREDENTIALS_FILE_PATH), exist_ok=True)
    with open(CREDENTIALS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(credentials, f, indent=4)
    os.chmod(CREDENTIALS_FILE_PATH, 0o600)


def save_api_key_credential_file(api_key: str, region: str) -> None:
    """Save the ADK key for `region` to the credential file in the user's home directory."""
    credentials = _read_credentials_file("It will be overwritten with the new API key.")
    credentials[region] = api_key
    _write_credentials_file(credentials)


def save_account_key_credential(region: str, api_key: str, account_id: str, key_name: str) -> None:
    """Save an account API key for `region` beside the ADK keys, replacing any stored one.

    Args:
        region: The region the key belongs to.
        api_key: The account API key. Never logged.
        account_id: The account the key is scoped to.
        key_name: The name the key carries on the platform.
    """
    credentials = _read_credentials_file("It will be overwritten with the new API key.")
    account_keys = credentials.get(ACCOUNT_KEYS_FIELD)
    if not isinstance(account_keys, dict):
        account_keys = {}
    account_keys[region] = {"key": api_key, "account_id": account_id, "name": key_name}
    credentials[ACCOUNT_KEYS_FIELD] = account_keys
    _write_credentials_file(credentials)


def load_account_key_credential(region: str) -> Optional[dict]:
    """The stored account API key entry for `region`, if any.

    Returns:
        A dict with ``key``, ``account_id`` and ``name``, or None when the file has
        no usable entry for `region`. Never raises.
    """
    account_keys = _read_credentials_file("It will be ignored when looking for the API key.").get(
        ACCOUNT_KEYS_FIELD
    )
    if not isinstance(account_keys, dict):
        return None
    entry = account_keys.get(region)
    if not isinstance(entry, dict) or not entry.get("key"):
        return None
    return entry


def load_api_key_from_credential_file(region: str) -> Optional[str]:
    """Look up the API key stored for `region` in the credential file, if any.

    Unlike `retrieve_api_key`, this never falls back to an environment
    variable and never raises - it answers "is there already a stored
    credential for this region", which is all a caller deciding whether to
    overwrite one needs.

    Args:
        region: The region to look up.

    Returns:
        The stored API key, or None if the credential file has no entry for
        `region`.
    """
    if os.path.isfile(CREDENTIALS_FILE_PATH):
        with open(CREDENTIALS_FILE_PATH, "r", encoding="utf-8") as f:
            try:
                credentials = json.load(f)
                return credentials.get(region)
            except json.JSONDecodeError:
                logger.warning(
                    f"Could not parse credentials file at {CREDENTIALS_FILE_PATH!r}. "
                    "It will be ignored when looking for the API key."
                )
    return None


_ACCOUNT_API_KEY_ENV_VAR = "POLY_API_KEY"
_CREDENTIALS_FILE_DISPLAY_PATH = "~/.poly/credentials.json"


def regions_with_stored_keys() -> list[str]:
    """Regions that hold an ADK key in the credential file or a per-region env var.

    Ordered as in ``_REGION_TO_KEY_SUFFIX``. A credential file that does not
    parse contributes nothing.
    """
    stored: dict = {}
    if os.path.isfile(CREDENTIALS_FILE_PATH):
        with open(CREDENTIALS_FILE_PATH, "r", encoding="utf-8") as f:
            try:
                stored = json.load(f)
            except json.JSONDecodeError:
                stored = {}
    if not isinstance(stored, dict):
        stored = {}
    return [
        region
        for region, suffix in _REGION_TO_KEY_SUFFIX.items()
        if stored.get(region) or os.getenv(f"{_API_KEY_ENV_VAR}_{suffix}")
    ]


def _missing_key_message(region: Optional[str] = None) -> str:
    """The error shown when no ADK key resolves for ``region``.

    Plain text, no markup: it is also returned verbatim as ``error`` under
    ``--json``. Sentence order: what is missing, how to get it, what the user
    already has, what they have that does not count, the CI alternative.
    With ``region`` None the message covers any region and points at the bare
    ``poly login`` picker.
    """
    if region:
        shown = region_display_name(region)
        sentences = [
            f"No ADK key found for region '{shown}'.",
            f"ADK commands need an ADK key, which `poly login` creates and saves to"
            f" {_CREDENTIALS_FILE_DISPLAY_PATH}.",
            f"Run `poly login --region {shown}` to sign in to that region.",
        ]
        others = [region_display_name(r) for r in regions_with_stored_keys() if r != region]
        if others:
            suggestion = (
                f"`--region {others[0]}`" if len(others) == 1 else "`--region <one of those>`"
            )
            sentences.append(
                f"You already have an ADK key for: {', '.join(others)} — re-run with"
                f" {suggestion} if that is the workspace you meant."
            )
    else:
        sentences = [
            "No ADK key found.",
            f"ADK commands need an ADK key, which `poly login` creates and saves to"
            f" {_CREDENTIALS_FILE_DISPLAY_PATH}.",
            "Run `poly login` to sign in.",
        ]
    if os.getenv(_ACCOUNT_API_KEY_ENV_VAR):
        sentences.append(
            f"{_ACCOUNT_API_KEY_ENV_VAR} is set, but that is an account API key for the PolyAI"
            " APIs and the ADK does not use it."
        )
    suffix = _REGION_TO_KEY_SUFFIX.get(region) if region else None
    per_region = f"{_API_KEY_ENV_VAR}_{suffix}" if suffix else f"{_API_KEY_ENV_VAR}_<REGION>"
    sentences.append(f"(CI or scripts: set {_API_KEY_ENV_VAR} or {per_region} instead.)")
    return " ".join(sentences)


def raise_if_no_credentials() -> None:
    """Raise ``ValueError`` when no ADK key exists for any region.

    For callers that have not settled on a region yet (``poly init`` with no
    ``--region``): the message points at the bare ``poly login`` picker rather
    than a specific region.
    """
    if not any_credentials_exist():
        raise ValueError(_missing_key_message())


def retrieve_api_key(region: str) -> str:
    """Return an API key, preferring a per-region key when available.

    Resolution order:
      1. The credential file entry for *region* (written by ``poly login``)
      2. ``POLY_ADK_KEY_{REGION}`` (e.g. ``POLY_ADK_KEY_US``)
      3. ``POLY_ADK_KEY``

    Raises ``ValueError`` with a helpful message when no key is found.
    """
    api_key = load_api_key_from_credential_file(region)
    if api_key:
        return api_key

    suffix = _REGION_TO_KEY_SUFFIX.get(region)
    if suffix:
        per_region_key = os.getenv(f"{_API_KEY_ENV_VAR}_{suffix}")
        if per_region_key:
            return per_region_key

    api_key = os.getenv(_API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(_missing_key_message(region))
    return api_key


def any_credentials_exist() -> bool:
    """Check if any API key credentials are available via environment variables or credential file."""
    if os.getenv(_API_KEY_ENV_VAR):
        return True
    for region in _REGION_TO_KEY_SUFFIX.keys():
        if os.getenv(f"{_API_KEY_ENV_VAR}_{_REGION_TO_KEY_SUFFIX[region]}"):
            return True

    if os.path.isfile(CREDENTIALS_FILE_PATH):
        try:
            with open(CREDENTIALS_FILE_PATH, "r", encoding="utf-8") as f:
                credentials = json.load(f)
                if any(region in credentials for region in _REGION_TO_KEY_SUFFIX.keys()):
                    return True
        except json.JSONDecodeError:
            logger.warning(
                f"Could not parse credentials file at {CREDENTIALS_FILE_PATH!r}. "
                "It will be ignored when checking for API key credentials."
            )
    return False
