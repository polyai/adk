"""Minting an account-scoped API key from a signed-in session.

Shared by ``poly apikey`` and ``poly setup``, so both commands resolve the account,
reuse or create the key and wait for it to activate the same way. Nothing here
prints, prompts or exits: the account picker is passed in by the command, and
every failure is raised.

Copyright PolyAI Limited
"""

import time
from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from poly.handlers.interface import AgentStudioInterface
from poly.utils.api_keys import select_reusable_api_key

# The name `poly apikey` gives keys; setup reuses one when present.
DEFAULT_KEY_NAME = "cli-generated-key"
# The name `poly setup` gives keys it creates, so the backend can tell the two apart.
SETUP_KEY_NAME = "setup-key"

ACCOUNT_POLL_ATTEMPTS = 20
ACCOUNT_POLL_INTERVAL_SECONDS = 1
ACCOUNT_POLL_TIMEOUT_SECONDS = ACCOUNT_POLL_ATTEMPTS * ACCOUNT_POLL_INTERVAL_SECONDS


class MultipleAccountsError(ValueError):
    """More than one account and no way to choose one without asking.

    Carries the accounts so `--json` can list them for the caller to pick from.
    """

    def __init__(self, region: str, accounts: list[dict], sign_in_kept: bool = False):
        self.region = region
        self.accounts = [account_summary(a) for a in accounts]
        listing = ", ".join(f"{a['id']} ({a.get('name') or 'unnamed'})" for a in accounts)
        message = (
            f"Multiple accounts found for {region}: {listing}. "
            "Re-run with --account-id <id> to pick one."
        )
        if sign_in_kept:
            message += " Your sign-in is kept, so the re-run will not ask you to sign in again."
        super().__init__(message)
        self.raw_accounts = accounts


def account_summary(account: dict) -> dict:
    """The account fields worth showing someone choosing between accounts."""
    return {key: account.get(key) for key in ("id", "name", "role", "created_by")}


def key_name_for_region(base: str, region: str) -> str:
    """A key name disambiguated by region, so keys for different clusters never collide."""
    return base if region == "studio" else f"{base}-{region}"


def resolve_account_id(
    api: AgentStudioInterface,
    region: str,
    jwt_token: str,
    account_id: str | None,
    *,
    source: str,
    pick: Callable[[list[dict]], str] | None = None,
) -> str:
    """Return `account_id` unchanged, or poll for the account and choose one.

    With more than one account: call `pick` if given, otherwise choosing would be a
    guess, so raise with the list instead.

    Args:
        api: The platform API interface.
        region: The region the user signed in to.
        jwt_token: The JWT from the device flow.
        account_id: An account chosen up front (``--account-id``), returned as is.
        source: Value for the ``X-Poly-Source`` header.
        pick: How to choose between several accounts, typically a terminal picker.

    Raises:
        MultipleAccountsError: Several accounts and no `pick`.
        ValueError: No account appeared within `ACCOUNT_POLL_TIMEOUT_SECONDS`, or
            `pick` raised it (for example a cancelled picker).
    """
    if account_id is not None:
        return account_id
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        accounts = api.get_accounts_internal(region=region, jwt_token=jwt_token, source=source)
        if accounts:
            if len(accounts) == 1:
                return accounts[0]["id"]
            if pick is not None:
                return pick(accounts)
            raise MultipleAccountsError(region, accounts)
        time.sleep(ACCOUNT_POLL_INTERVAL_SECONDS)
    raise ValueError(
        f"No account appeared after {ACCOUNT_POLL_TIMEOUT_SECONDS}s. Re-run with --account-id <id>."
    )


def mint_account_key(
    api: AgentStudioInterface,
    region: str,
    jwt_token: str,
    account_id: str,
    key_name: str,
    *,
    source: str,
    also_reuse: Iterable[str] = (),
) -> tuple[str, bool, str]:
    """Reuse an active, unexpired key named `key_name` (or one of `also_reuse`), or create one.

    Args:
        api: The platform API interface.
        region: The region the key belongs to.
        jwt_token: The JWT from the device flow.
        account_id: The account to scope the key to.
        key_name: The name to look for first, and the name a new key is created with.
        source: Value for the ``X-Poly-Source`` header.
        also_reuse: Further names to accept an existing key under, in order, before
            creating one. Lets `poly setup` reuse a key `poly apikey` made.

    Returns:
        The key, whether it was reused rather than created, and the name it carries.

    Raises:
        ValueError: The create call succeeded but returned no key.
    """
    keys = api.list_account_api_keys_internal(
        region=region, jwt_token=jwt_token, account_id=account_id, source=source
    )
    now = datetime.now(timezone.utc)
    for name in (key_name, *also_reuse):
        existing_key = select_reusable_api_key(keys, name, now)
        if existing_key is not None:
            return existing_key, True, name

    response = api.create_account_api_key_internal(
        region=region,
        jwt_token=jwt_token,
        account_id=account_id,
        name=key_name,
        source=source,
    )
    api_key = response.get("key")
    if not api_key:
        raise ValueError("API key not found in response. Please contact support.")
    return api_key, False, key_name


def wait_for_key_active(api: AgentStudioInterface, region: str, api_key: str) -> bool:
    """Poll until `api_key` itself is usable.

    A newly created key can take a few seconds to activate; polling here means a
    command run immediately afterwards does not fail against a key the platform has
    not finished activating yet. Probes with `api_key` directly rather than the
    on-disk credential, which could be a different, already-active key.

    Returns:
        bool: Whether the key became active within the poll window.
    """
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        try:
            api.get_accounts_with_key(region=region, api_key=api_key)
            return True
        except Exception:
            time.sleep(ACCOUNT_POLL_INTERVAL_SECONDS)
    return False
