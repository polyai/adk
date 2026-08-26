"""API key credential storage and retrieval.

Copyright PolyAI Limited
"""

import json
import logging
import os
from typing import Optional

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

CREDENTIALS_FILE_PATH = os.path.expanduser("~/.poly/credentials.json")


def save_api_key_credential_file(api_key: str, region: str) -> None:
    """Save the API key to a credential file in the user's home directory."""
    credentials = {}
    if os.path.isfile(CREDENTIALS_FILE_PATH):
        with open(CREDENTIALS_FILE_PATH, "r", encoding="utf-8") as f:
            try:
                credentials = json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    f"Could not parse existing credentials file at {CREDENTIALS_FILE_PATH!r}. "
                    "It will be overwritten with the new API key."
                )

    credentials[region] = api_key

    os.makedirs(os.path.dirname(CREDENTIALS_FILE_PATH), exist_ok=True)
    with open(CREDENTIALS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(credentials, f, indent=4)

    # Set file permissions to be readable/writeable only by the user
    os.chmod(CREDENTIALS_FILE_PATH, 0o600)


def _load_api_key_from_credential_file(region: str) -> Optional[str]:
    """Load the API key for the given region from the credential file, if it exists."""
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


def retrieve_api_key(region: str) -> str:
    """Return an API key, preferring a per-region key when available.

    Resolution order:
      1. ``POLY_ADK_KEY_{REGION}`` (if *region* is provided, e.g. ``POLY_ADK_KEY_US``)
      2. ``POLY_ADK_KEY``

    Raises ``ValueError`` with a helpful message when no key is found.
    """
    api_key = _load_api_key_from_credential_file(region)
    if api_key:
        return api_key

    suffix = _REGION_TO_KEY_SUFFIX.get(region)
    if suffix:
        per_region_key = os.getenv(f"{_API_KEY_ENV_VAR}_{suffix}")
        if per_region_key:
            return per_region_key

    api_key = os.getenv(_API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(
            f"{_API_KEY_ENV_VAR} environment variable is not set. "
            f"Export your API key with: export {_API_KEY_ENV_VAR}=<your-api-key>"
        )
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
