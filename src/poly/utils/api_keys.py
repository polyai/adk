"""Selection logic for reusing an existing account-scoped API key.

Copyright PolyAI Limited
"""

from datetime import datetime
from typing import Optional

from dateutil import parser as date_parser


def _is_active_and_unexpired(key: dict, now: datetime) -> bool:
    """Whether a key record is active and either has no expiry or expires after `now`."""
    if key.get("active") is not True:
        return False

    expires_at = key.get("expires_at")
    if not expires_at:
        return True

    return date_parser.isoparse(expires_at) > now


def _policy_name(key: dict) -> str:
    """The name a key was created with.

    The name passed at creation does not land on the key's own `name` field
    (which comes back empty) - it lands on `policies[0].name`.
    """
    policies = key.get("policies") or [{}]
    return policies[0].get("name") or ""


def select_reusable_api_key(keys: list[dict], name: str, now: datetime) -> Optional[str]:
    """Pick the newest active, unexpired API key named `name`, if one exists.

    Args:
        keys: Raw API key records, as returned by the accounts API.
        name: The key name to match (compared against `policies[0].name`).
        now: The current time, used to evaluate `expires_at`. Must be
            timezone-aware (e.g. `datetime.now(timezone.utc)`), since
            `expires_at` values are timezone-aware ISO 8601 timestamps.

    Returns:
        The matching key's secret, or `None` if no key qualifies.
    """
    matching = [
        key for key in keys if _is_active_and_unexpired(key, now) and _policy_name(key) == name
    ]
    if not matching:
        return None

    newest = max(matching, key=lambda key: key.get("created_at") or "")
    return newest.get("key")
