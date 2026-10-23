"""Sign-in reuse for `poly apikey` and API integration configuration.

Keeps the device-flow access token from the last `poly apikey` run, per region, so a
re-run (for example with `--account-id` after a "Multiple accounts found" error) does
not send the user back through the browser sign-in. The file sits next to the
credentials file, is readable only by the user, and each entry is honoured only until
the token's own expiry. Studio sessions use a `studio:` prefix on their region key
so their tokens cannot be confused with the API-key login's separate auth tenant.
The token is never printed or logged.

Copyright PolyAI Limited
"""

import base64
import binascii
import json
import logging
import os
import time
from typing import NamedTuple, Optional

from poly.constants import POLY_HOME_DIR

logger = logging.getLogger(__name__)

SESSION_FILE_PATH = os.path.join(POLY_HOME_DIR, "apikey_session")

# Treat a token as expired this many seconds early, so it doesn't lapse mid-run.
EXPIRY_MARGIN_SECONDS = 60
# Used when the token carries no readable `exp` claim.
DEFAULT_LIFETIME_SECONDS = 3600


class CachedSession(NamedTuple):
    """A reusable sign-in: the token, when it expires, and when it was saved (epoch seconds)."""

    token: str
    exp: int
    saved_at: int


def token_claims(token: str) -> dict:
    """Decode a JWT's payload without verifying it, or {} if it is not a readable JWT."""
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
    except (IndexError, ValueError, binascii.Error, AttributeError):
        return {}
    return claims if isinstance(claims, dict) else {}


def _token_exp(token: str) -> Optional[int]:
    """Read the `exp` claim from a JWT, or None if it has no usable one."""
    exp = token_claims(token).get("exp")
    return int(exp) if isinstance(exp, (int, float)) else None


def _read() -> dict:
    """Return the whole session file, or {} if it is missing or unreadable."""
    if not os.path.isfile(SESSION_FILE_PATH):
        return {}
    try:
        with open(SESSION_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        logger.warning(f"Could not read {SESSION_FILE_PATH!r}; ignoring it.")
        return {}
    return data if isinstance(data, dict) else {}


def _write(data: dict) -> None:
    """Write the whole session file, readable and writable only by the user."""
    os.makedirs(os.path.dirname(SESSION_FILE_PATH), exist_ok=True)
    # Create with 0600 from the start so the token is never briefly world-readable.
    fd = os.open(SESSION_FILE_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.chmod(SESSION_FILE_PATH, 0o600)


def load(region: str) -> Optional[CachedSession]:
    """Return the cached sign-in for `region` if it is still valid, else None."""
    entry = _read().get(region)
    if not isinstance(entry, dict):
        return None
    token, exp, saved_at = entry.get("token"), entry.get("exp"), entry.get("saved_at")
    if not isinstance(token, str) or not token or not isinstance(exp, int):
        return None
    if exp - EXPIRY_MARGIN_SECONDS <= time.time():
        return None
    return CachedSession(token, exp, saved_at if isinstance(saved_at, int) else exp)


def save(region: str, token: str) -> CachedSession:
    """Cache `token` for `region` until its `exp` claim (or an hour, if it has none)."""
    now = int(time.time())
    exp = _token_exp(token) or now + DEFAULT_LIFETIME_SECONDS
    data = _read()
    data[region] = {"token": token, "exp": exp, "saved_at": now}
    _write(data)
    return CachedSession(token, exp, now)


def clear(region: str) -> None:
    """Drop the cached sign-in for `region`, if any."""
    data = _read()
    if region in data:
        del data[region]
        _write(data)
