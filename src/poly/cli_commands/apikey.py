"""API key command: sign in and provision an account-scoped API key.

`poly apikey` is the narrower cousin of `poly login`: it exists to get an API key for
the PolyAI APIs and Dialog RSN into your environment, not to set up the ADK itself. It
signs a user in - via the GitHub-only Auth0 device flow for the default `studio` region, or
the standard sign-in page for any other region - creates their PolyAI account if needed,
provisions an account-scoped API key (or reuses the one already in their profile), and
writes ``POLY_API_KEY`` into their shell profile - or, on Windows, their user environment.
``--type model`` does the same with a Models-only key in ``POLY_MODEL_API_KEY``.
It never prompts when run by an agent (no terminal, or ``--json``); at a terminal it may ask
which account to use. It keeps the sign-in so a re-run does not sign in again. To set up the
ADK itself, use ``poly setup`` or ``poly login`` instead. See ``poly apikey --help`` or
``docs/docs/reference/cli/apikey.md`` for the full step-by-step behaviour.

Copyright PolyAI Limited
"""

import contextlib
import sys
import time
from argparse import ArgumentParser, Namespace, _SubParsersAction
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.cli_commands.auth import authorise_or_explain
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import REGION_CHOICES, region_type
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS, REGION_TO_AUTH_DETAILS
from poly.handlers.interface import AgentStudioInterface
from poly.handlers.platform_api import PlatformAPIError
from poly.utils import apikey_session
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    load_api_key_from_credential_file,
    save_api_key_credential_file,
)
from poly.utils.env_profile import (
    EnvVarConflict,
    ProfileTarget,
    detect_profile,
    read_env_var,
    write_env_var,
)

DEFAULT_KEY_NAME = "cli-generated-key"
# Key types, and the API groups each asks the platform for. None leaves `api_groups` out of
# the request, which gives a key for every API ("All APIs" in Agent Studio).
KEY_TYPE_API_GROUPS: dict[str, list[str] | None] = {"agent": None, "model": ["models"]}
KEY_TYPE_STUDIO_LABELS = {"agent": "All APIs", "model": "Model API"}
DEFAULT_KEY_TYPE = "agent"
# Lifetimes `--expires-in` accepts. None leaves `expires_at` out, so the key never expires.
EXPIRES_IN_DAYS: dict[str, int | None] = {"30d": 30, "90d": 90, "365d": 365, "never": None}
DEFAULT_EXPIRES_IN = "90d"
# Each type has its own profile variable, so a model key never replaces the agent key.
KEY_TYPE_ENV_VARS = {"agent": "POLY_API_KEY", "model": "POLY_MODEL_API_KEY"}
# A reused key closer than this to expiring gets a warning to replace it.
EXPIRY_WARNING_DAYS = 14
ACCOUNT_POLL_ATTEMPTS = 20
ACCOUNT_POLL_INTERVAL_SECONDS = 1
ACCOUNT_POLL_TIMEOUT_SECONDS = ACCOUNT_POLL_ATTEMPTS * ACCOUNT_POLL_INTERVAL_SECONDS
APIKEY_SOURCE = "apikey"
# Short path that docs.poly.ai redirects to the Dialog RSN 1 first-call page.
NEXT_STEP_URL = "https://docs.poly.ai/dialog-rsn-1"


class MultipleAccountsError(ValueError):
    """More than one account and no way to choose one without asking.

    Carries the accounts so `--json` can list them for the caller to pick from.
    """

    def __init__(self, region: str, accounts: list[dict], sign_in_kept: bool = False):
        self.region = region
        self.accounts = [_account_summary(a) for a in accounts]
        listing = ", ".join(f"{a['id']} ({a.get('name') or 'unnamed'})" for a in accounts)
        message = (
            f"Multiple accounts found for {region}: {listing}. "
            "Re-run with --account-id <id> to pick one."
        )
        if sign_in_kept:
            message += " Your sign-in is kept, so the re-run will not ask you to sign in again."
        super().__init__(message)
        self.raw_accounts = accounts


class ProfileKeyRefused(Exception):
    """The key in the profile isn't accepted for the chosen account and region."""

    def __init__(
        self,
        masked_key: str,
        account_id: str,
        region: str,
        path: Path,
        key_type: str = DEFAULT_KEY_TYPE,
        record: dict | None = None,
        record_lookup_ok: bool = False,
    ):
        """Build the refusal message.

        Args:
            record: The account's key-list entry for the refused key, if one was found.
            record_lookup_ok: Whether the key list was read, so a missing `record` means the
                key isn't in this account's list.
        """
        type_flag = "" if key_type == DEFAULT_KEY_TYPE else f" --type {key_type}"
        expiry = None if record is None else _key_details(record, key_type, None)[1]
        days_left = _days_left(expiry)
        where = f"{KEY_TYPE_ENV_VARS[key_type]} in {path} ({masked_key})"
        if days_left is not None and days_left < 0:
            reason = f"{where} expired on {_format_expiry(expiry)}."
        elif record is None and record_lookup_ok:
            reason = (
                f"{where} isn't accepted for account {account_id} on {region}. It isn't in"
                " the account's key list, so it was revoked or belongs to another account."
            )
        else:
            reason = (
                f"{where} isn't accepted for account {account_id} on {region}."
                " It may have expired or been revoked."
            )
        super().__init__(
            f"{reason} Re-run `poly apikey --region {region}{type_flag} --force` to create a"
            " new key and replace it."
        )


def _default_key_name(region: str, key_type: str = DEFAULT_KEY_TYPE) -> str:
    """The default API key name - disambiguated by region and type so keys never collide."""
    name = DEFAULT_KEY_NAME if region == "studio" else f"{DEFAULT_KEY_NAME}-{region}"
    return name if key_type == DEFAULT_KEY_TYPE else f"{name}-{key_type}"


def _expires_at(expires_in: str, now: datetime | None = None) -> datetime | None:
    """The absolute UTC expiry for an `--expires-in` value, or None for `never`."""
    days = EXPIRES_IN_DAYS[expires_in]
    if days is None:
        return None
    return (now or datetime.now(UTC)) + timedelta(days=days)


def _key_details(
    response: dict, key_type: str, expires_at: datetime | None
) -> tuple[str, str | None]:
    """A key's type and expiry, read from its record (a create response or a list entry).

    Falls back to `key_type` and `expires_at` when the record doesn't say.

    Returns:
        tuple[str, str | None]: The key type, and its ISO expiry (None if it never expires).
    """
    groups = response.get("api_groups", KEY_TYPE_API_GROUPS[key_type])
    # The platform reports every API as null, the same as the request leaves it out.
    type_by_groups = {tuple(g or ()): name for name, g in KEY_TYPE_API_GROUPS.items()}
    actual_type = type_by_groups.get(tuple(groups or ()), key_type)

    if response.get("never_expires") is True:
        return actual_type, None
    actual_expiry = response.get("expires_at")
    if actual_expiry is None and expires_at is not None:
        actual_expiry = expires_at.isoformat()
    return actual_type, actual_expiry


def _days_left(expires_at: str | None, now: datetime | None = None) -> int | None:
    """Whole days until `expires_at`, or None if it never expires or can't be read."""
    if expires_at is None:
        return None
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return (expiry - (now or datetime.now(UTC))).days


def _lookup_key_record(
    api: AgentStudioInterface, region: str, jwt_token: str, account_id: str, api_key: str
) -> tuple[dict | None, bool]:
    """The account's record for `api_key`, matched on the prefix and suffix the list returns.

    Best effort: the record only adds detail to the output, so a failed lookup, no match, or
    more than one match gives no record rather than an error.

    Returns:
        tuple[dict | None, bool]: The record if exactly one matched, and whether the list was
            read at all (so a missing record means the key isn't in it).
    """
    import requests

    try:
        records = api.list_account_api_keys_internal(
            region=region, jwt_token=jwt_token, account_id=account_id, source=APIKEY_SOURCE
        )
    except (requests.RequestException, ValueError):
        return None, False
    if not isinstance(records, list):
        return None, False
    matches = [
        r
        for r in records
        if isinstance(r, dict)
        and r.get("key_prefix") == api_key[:4]
        and r.get("key_suffix") == api_key[-4:]
    ]
    if len(matches) > 1:
        # Ambiguous, so say nothing about it rather than describe the wrong key.
        return None, False
    return (matches[0] if matches else None), True


def _format_expiry(expires_at: str | None) -> str:
    """A human-readable expiry date."""
    if expires_at is None:
        return "never"
    try:
        return datetime.fromisoformat(expires_at).strftime("%Y-%m-%d")
    except ValueError:
        return expires_at


def _say(output_json: bool, fn: Callable[[str], None], message: str) -> None:
    """Print via `fn` unless --json is active (stdout must then be a single JSON object)."""
    if not output_json:
        fn(message)


def _account_summary(account: dict) -> dict:
    """The account fields worth showing someone choosing between accounts."""
    return {key: account.get(key) for key in ("id", "name", "role", "created_by")}


def _pick_account(accounts: list[dict]) -> str:
    """Ask which account to use, with the same picker `poly project create` uses.

    Raises:
        ValueError: The picker was cancelled.
    """
    import questionary

    choices = [
        questionary.Choice(title=f"{a.get('name') or 'unnamed'} ({a['id']})", value=a["id"])
        for a in accounts
    ]
    chosen = questionary.select(
        "Select Account",
        choices=choices,
        use_search_filter=True,
        use_jk_keys=False,
    ).ask()
    if not chosen:
        raise ValueError("No account selected.")
    return chosen


def _fail(exc: Exception, step: str, exit_code: int, *, output_json: bool, verbose: bool) -> None:
    """Print a clean error (or re-raise under --verbose) and exit."""
    if verbose:
        raise exc
    message = str(exc)
    if isinstance(exc, EnvVarConflict):
        message = f"{exc} Re-run with --force to replace it."
    if output_json:
        from poly.output.json_output import json_print

        payload = {"success": False, "error": message, "step": step}
        if isinstance(exc, MultipleAccountsError):
            payload["accounts"] = exc.accounts
        json_print(payload)
    else:
        from poly.output.console import error

        error(message)
    sys.exit(exit_code)


def _resolve_account_id(
    api: AgentStudioInterface,
    region: str,
    jwt_token: str,
    account_id: str | None,
    *,
    interactive: bool,
) -> str:
    """Return `account_id` unchanged, or poll for the account and choose one.

    With more than one account: at a terminal (`interactive`), ask. Otherwise choosing
    would be a guess, so raise with the list instead.

    Raises:
        MultipleAccountsError: Several accounts and not interactive.
        ValueError: No account appeared within `ACCOUNT_POLL_TIMEOUT_SECONDS`, or the
            picker was cancelled.
    """
    if account_id is not None:
        return account_id
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        accounts = api.get_accounts_internal(
            region=region, jwt_token=jwt_token, source=APIKEY_SOURCE
        )
        if accounts:
            if len(accounts) == 1:
                return accounts[0]["id"]
            if interactive:
                return _pick_account(accounts)
            raise MultipleAccountsError(region, accounts)
        time.sleep(ACCOUNT_POLL_INTERVAL_SECONDS)
    raise ValueError(
        f"No account appeared after {ACCOUNT_POLL_TIMEOUT_SECONDS}s. Re-run with --account-id <id>."
    )


def _key_works_for_account(
    api: AgentStudioInterface, region: str, api_key: str, account_id: str
) -> bool:
    """Whether `api_key` is accepted on `region` and can reach `account_id`.

    Raises:
        PlatformAPIError: The check failed for any reason other than the key being refused,
            so it says nothing about the key.
    """
    try:
        return account_id in api.get_accounts_with_key(region=region, api_key=api_key)
    except PlatformAPIError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            return False
        raise


def _get_or_create_key(
    api: AgentStudioInterface,
    region: str,
    jwt_token: str,
    account_id: str,
    key_name: str,
    *,
    force: bool,
    key_type: str = DEFAULT_KEY_TYPE,
    expires_at: datetime | None = None,
) -> tuple[str, bool, dict]:
    """Reuse the key already in the profile for `key_type` if it works, or create one.

    The platform only shows a key's secret when it is created, so the profile is the one place
    an existing key can be read back from. Each type has its own variable
    (`KEY_TYPE_ENV_VARS`), so reusing or replacing one never touches the other.

    Returns:
        tuple[str, bool, dict]: The key, whether it was reused rather than created, and the
            create response (empty when reused).

    Raises:
        ProfileKeyRefused: The profile holds a key that isn't accepted for this account and
            `force` is false. Raised before creating anything, so a re-run doesn't leave
            another unused key behind.
        PlatformAPIError: The check on the profile's key failed.
        ValueError: The create call succeeded but returned no key.
    """
    from poly.output.console import mask_secret

    existing_key = None if force else read_env_var(KEY_TYPE_ENV_VARS[key_type])
    if existing_key is not None:
        if _key_works_for_account(api, region, existing_key, account_id):
            return existing_key, True, {}
        record, lookup_ok = _lookup_key_record(api, region, jwt_token, account_id, existing_key)
        raise ProfileKeyRefused(
            mask_secret(existing_key),
            account_id,
            region,
            detect_profile().path,
            key_type,
            record=record,
            record_lookup_ok=lookup_ok,
        )

    response = api.create_account_api_key_internal(
        region=region,
        jwt_token=jwt_token,
        account_id=account_id,
        name=key_name,
        source=APIKEY_SOURCE,
        api_groups=KEY_TYPE_API_GROUPS[key_type],
        expires_at=expires_at,
    )
    api_key = response.get("key")
    if not api_key:
        raise ValueError("API key not found in response. Please contact support.")
    return api_key, False, response


def _wait_for_key_active(api: AgentStudioInterface, region: str, api_key: str) -> bool:
    """Poll until `api_key` itself is usable, mirroring `poly login`'s activation wait.

    A newly created key can take a few seconds to activate; polling here means a
    command run immediately after `poly apikey` does not fail against a key the
    platform has not finished activating yet. Must probe with `api_key` directly
    rather than `get_accounts` (which authenticates via the on-disk credential) -
    when an existing credential is kept rather than overwritten, that would
    silently validate a different, already-active key instead of this one.

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


NOT_ACTIVE_WARNING = (
    "API key was saved but is not active yet. If your next command fails, wait a moment and retry."
)


def _wait_for_activation(
    api: AgentStudioInterface, region: str, api_key: str, output_json: bool
) -> bool:
    """Wait for `api_key` to activate, with a spinner at a terminal.

    Returns:
        bool: Whether the key became active within the poll window.
    """
    from poly.output.console import console

    status_ctx = (
        contextlib.nullcontext()
        if output_json
        else console.status("[info]Verifying API key is active...[/info]")
    )
    with status_ctx:
        return _wait_for_key_active(api, region, api_key)


def _save_credentials(region: str, api_key: str) -> tuple[bool, str]:
    """Save `api_key` to the credential file, unless `region` already has one.

    Returns:
        tuple[bool, str]: Whether a new credential was saved, and a summary
            of what happened, for the completion output.
    """
    if load_api_key_from_credential_file(region) is not None:
        return False, "existing credential kept"
    save_api_key_credential_file(api_key, region=region)
    return True, f"{CREDENTIALS_FILE_PATH} ({region})"


def _type_and_expiry_lines(key_type: str | None, expires_at: str | None) -> list[str]:
    """The summary lines for a key's type and expiry, or a note when they aren't known."""
    if key_type is None:
        return ["  Type:      not known (the reused key wasn't found in the account's key list)"]
    return [
        f"  Type:      {key_type} ({KEY_TYPE_STUDIO_LABELS.get(key_type, key_type)})",
        f"  Expires:   {_format_expiry(expires_at)}",
    ]


def _print_summary(
    account_id: str,
    api_key: str,
    key_name: str,
    key_reused: bool,
    credentials_summary: str | None,
    target: ProfileTarget,
    masked_line: str,
    key_type: str | None = None,
    expires_at: str | None = None,
    env_var: str = KEY_TYPE_ENV_VARS[DEFAULT_KEY_TYPE],
) -> None:
    """Print the human-readable completion summary."""
    from poly.output.console import mask_api_key, plain

    plain("")
    plain("Done.")
    plain(f"  Account:   {account_id}")
    origin = "reused from your profile" if key_reused else f"{key_name}, created"
    plain(f"  API key:   {mask_api_key(api_key)}   ({origin})")
    for line in _type_and_expiry_lines(key_type, expires_at):
        plain(line)
    if credentials_summary is None:
        plain("  Saved to:  not the ADK credential file (a model key can't run the ADK)")
    else:
        plain(f"  Saved to:  {credentials_summary}")
    plain(f"  Profile:   {target.path}  ({masked_line})")
    plain("")
    if target.shell == "powershell":
        plain(f"Open a new terminal to pick up {env_var}.")
    else:
        plain(f"Open a new terminal, or run `source {target.path}`, to pick up {env_var}.")
    plain("")
    if env_var == KEY_TYPE_ENV_VARS[DEFAULT_KEY_TYPE]:
        plain(f"Next: make your first API call ({env_var} is already set).")
    else:
        plain(f"Next: make your first realtime API call, reading the key from {env_var}.")


def _print_json(
    account_id: str,
    api_key: str,
    key_name: str,
    key_reused: bool,
    credentials_summary: str | None,
    target: ProfileTarget,
    key_active: bool,
    key_type: str | None = None,
    expires_at: str | None = None,
    env_var: str = KEY_TYPE_ENV_VARS[DEFAULT_KEY_TYPE],
    warnings: list[str] | None = None,
) -> None:
    """Print the --json completion object. The key itself is only ever masked."""
    from poly.output.console import mask_secret
    from poly.output.json_output import json_print

    json_print(
        {
            "success": True,
            "account_id": account_id,
            "key_name": None if key_reused else key_name,
            "key_reused": key_reused,
            "key_type": key_type,
            "expires_at": expires_at,
            "env_var": env_var,
            "api_key_masked": mask_secret(api_key),
            "credentials_file": credentials_summary,
            "profile_path": str(target.path),
            "profile_shell": target.shell,
            "key_active": key_active,
            "warnings": warnings or [],
            "next_step_url": NEXT_STEP_URL,
        }
    )


def _with_article(word: str) -> str:
    """`word` with "a" or "an" in front."""
    return f"{'an' if word[:1] in 'aeiou' else 'a'} {word}"


def _reused_key_warnings(
    key_details: tuple[str | None, str | None], key_type: str, expires_in: str | None
) -> list[str]:
    """What a reused key is that the caller may not expect. Nothing about it is changed."""
    found_type, found_expiry = key_details
    env_var = KEY_TYPE_ENV_VARS[key_type]
    type_flag = "" if key_type == DEFAULT_KEY_TYPE else f" --type {key_type}"
    warnings = []
    if expires_in is not None:
        warnings.append(
            "--expires-in didn't apply: the reused key keeps the expiry it was created with."
            " Re-run with --force to create a fresh key."
        )
    if found_type is not None and found_type != key_type:
        warnings.append(
            f"The key in {env_var} is {_with_article(found_type)} key, not {key_type}."
            f" Re-run with{type_flag} --force to replace it with {_with_article(key_type)} key."
        )
    days_left = _days_left(found_expiry)
    if days_left is not None and days_left <= EXPIRY_WARNING_DAYS:
        warnings.append(
            f"This key expires on {_format_expiry(found_expiry)} (in {max(days_left, 0)} days)."
            f" Re-run with{type_flag} --force to replace it."
        )
    return warnings


class ApiKeyCommand(BaseCommand):
    """Sign in, provision an account API key, and export POLY_API_KEY."""

    command = "apikey"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``apikey`` subcommand."""
        apikey_parser = subparsers.add_parser(
            "apikey",
            parents=[parents.verbose, parents.debug, parents.json],
            help="Create an account API key and export POLY_API_KEY for the PolyAI APIs.",
            description=(
                "Sign in, create an account-scoped API key (or reuse the one in your profile),"
                " and export it as"
                " POLY_API_KEY for use with the PolyAI APIs and Dialog RSN. Never prompts when"
                " run by an AI coding assistant (no terminal, or --json); at a terminal it"
                " asks which account to use if you have more than one. The sign-in is kept,"
                " so a re-run does not sign in again.\n\n"
                "To set up the ADK itself, use `poly setup` or `poly login` instead - the ADK"
                " reads its credentials from ~/.poly/credentials.json and does not need"
                " POLY_API_KEY.\n\n"
                "Examples:\n"
                "  poly apikey --region studio\n"
                "  poly apikey --region studio --account-id acc-123\n"
                "  poly apikey --region us\n"
                "  poly apikey --region studio --json\n"
                "  poly apikey --region studio --type model --expires-in 30d"
                "   # exports POLY_MODEL_API_KEY\n"
            ),
        )
        apikey_parser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            required=True,
            help=(
                "Region/cluster to create the key for. 'studio' is the self-serve cluster"
                " individual developers sign up on via GitHub; any other region uses the"
                " standard sign-in page (email/SSO), the same one `poly login` uses."
            ),
        )
        apikey_parser.add_argument(
            "--key-name",
            type=str,
            default=None,
            help=(
                f"Name for the account-scoped API key. Defaults to '{DEFAULT_KEY_NAME}' for"
                f" studio, or '{DEFAULT_KEY_NAME}-<region>' for any other region, with"
                " '-model' added for a model key."
            ),
        )
        apikey_parser.add_argument(
            "--type",
            dest="key_type",
            choices=list(KEY_TYPE_API_GROUPS),
            default=None,
            help=(
                f"Kind of key. Defaults to '{DEFAULT_KEY_TYPE}'. 'agent' can call every API,"
                " including what the ADK needs ('All APIs' in Agent Studio), and is exported"
                " as POLY_API_KEY. 'model' can call only the Models / realtime API ('Model"
                " API' in Agent Studio) and is exported as POLY_MODEL_API_KEY instead, never"
                " replacing POLY_API_KEY or the ADK credential. Each type is reused and"
                " replaced on its own, and a model key gets its own default name."
            ),
        )
        apikey_parser.add_argument(
            "--expires-in",
            choices=list(EXPIRES_IN_DAYS),
            default=None,
            help=(
                f"How long until the new key expires. Defaults to '{DEFAULT_EXPIRES_IN}'."
                " 'never' creates a key that doesn't expire. Doesn't change a key reused"
                " from your profile; use --force to create a fresh one."
            ),
        )
        apikey_parser.add_argument(
            "--account-id",
            type=str,
            default=None,
            help=(
                "Account ID to scope the key to. Skips polling for a newly created account."
                " With more than one account and no --account-id, a terminal shows a"
                " picker; otherwise the command fails listing the accounts so you can"
                " re-run with one of them."
            ),
        )
        apikey_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help=(
                "Create a new key and overwrite any POLY_API_KEY already in your profile,"
                " even one that still works."
            ),
        )
        apikey_parser.add_argument(
            "--no-session-cache",
            action="store_true",
            help=(
                "Sign in fresh and do not keep the sign-in for later runs. By default the"
                f" sign-in is kept in {apikey_session.SESSION_FILE_PATH} (readable only by"
                " you) until it expires, so a re-run does not sign in again."
            ),
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the apikey handler."""
        cls.apikey(
            region=args.region,
            key_name=args.key_name,
            key_type=args.key_type,
            expires_in=args.expires_in,
            account_id=args.account_id,
            force=args.force,
            output_json=args.json,
            verbose=args.verbose,
            no_session_cache=args.no_session_cache,
        )

    @classmethod
    def apikey(
        cls,
        region: str,
        key_name: str | None = None,
        account_id: str | None = None,
        force: bool = False,
        output_json: bool = False,
        verbose: bool = False,
        no_session_cache: bool = False,
        key_type: str | None = None,
        expires_in: str | None = None,
    ) -> None:
        """Sign in and provision an account API key for `region`, then export it.

        `expires_in` is None when not passed, so a reused key can say it was ignored only
        when it was asked for.
        """
        import requests

        from poly.output.console import err_console, info, mask_api_key, plain, success, warning

        key_type = key_type or DEFAULT_KEY_TYPE
        is_model_key = key_type == "model"
        key_name = key_name if key_name is not None else _default_key_name(region, key_type)

        step = "start"
        try:
            _say(output_json, info, "Setting up your PolyAI account and API key...")

            step = "signin"
            auth_details = (
                APIKEY_AUTH_DETAILS if region == "studio" else REGION_TO_AUTH_DETAILS[region]
            )
            sign_in_line = (
                "To sign in with GitHub, open the following link in your browser"
                if region == "studio"
                else "To sign in, open the following link in your browser"
            )

            def on_verification_url(verification_uri: str, user_code: str) -> None:
                message = (
                    f"{sign_in_line}\n"
                    "and enter the code when prompted.\n\n"
                    f"  URL:  {verification_uri}\n"
                    f"  Code: [bold]{user_code}[/bold]"
                )
                if output_json:
                    # --json only constrains stdout - an agent that can't open a
                    # browser itself still needs this to complete sign-in, so it
                    # goes to stderr rather than being dropped like every other
                    # human-readable message in this mode.
                    err_console.print(f"[info]{message}[/info]")
                else:
                    _say(output_json, info, message)

            def sign_in() -> tuple[str, apikey_session.CachedSession | None]:
                token = signin_with_device_flow(
                    auth_details, on_verification_url=on_verification_url
                )
                _say(output_json, success, "Authenticated successfully!")
                if no_session_cache:
                    return token, None
                return token, apikey_session.save(region, token)

            session = None if no_session_cache else apikey_session.load(region)
            token_reused = session is not None
            if session is not None:
                jwt_token = session.token
                minutes_ago = max(0, int(time.time() - session.saved_at) // 60)
                _say(
                    output_json,
                    info,
                    f"Reusing your sign-in from {minutes_ago} minutes ago.",
                )
            else:
                jwt_token, session = sign_in()

            api = AgentStudioInterface()
            interactive = not output_json and sys.stdin.isatty()
            while True:
                try:
                    step = "authorise"
                    _say(output_json, info, "Setting up your account...")
                    auth_response = authorise_or_explain(
                        api,
                        region,
                        jwt_token,
                        self_serve_hint="run `poly apikey --region studio`",
                    )

                    step = "account"
                    try:
                        resolved_account_id = _resolve_account_id(
                            api,
                            region,
                            jwt_token,
                            account_id,
                            interactive=interactive,
                        )
                    except MultipleAccountsError as e:
                        if session is None:
                            raise
                        raise MultipleAccountsError(
                            region, e.raw_accounts, sign_in_kept=True
                        ) from None
                    break
                except PlatformAPIError as e:
                    # A kept sign-in can be revoked before it expires: drop it and sign
                    # in once more. A fresh sign-in that is refused is a real error.
                    unauthorised = e.response is not None and e.response.status_code == 401
                    if not (token_reused and unauthorised):
                        raise
                    apikey_session.clear(region)
                    token_reused = False
                    _say(output_json, info, "Your kept sign-in was refused; signing in again.")
                    step = "signin"
                    jwt_token, session = sign_in()

            # On non-studio regions, `is_first_login` also fires for an existing user
            # who has no admin role on any account yet (enterprise auto-provisioning),
            # not just a genuinely new signup - restrict the signup event to studio,
            # the only region this tracking was asked for.
            is_signup = region == "studio" and bool(
                ((auth_response or {}).get("user") or {}).get("is_first_login")
            )
            if is_signup:
                from poly.handlers.posthog import capture_event

                capture_event(
                    region,
                    "apikey_signup",
                    {"source": APIKEY_SOURCE},
                    distinct_id=resolved_account_id,
                )

            step = "key"
            # Also returned in --json, where the printed warnings are suppressed.
            warnings: list[str] = []
            env_var = KEY_TYPE_ENV_VARS[key_type]
            requested_expiry = _expires_at(expires_in or DEFAULT_EXPIRES_IN)
            api_key, key_reused, response = _get_or_create_key(
                api,
                region,
                jwt_token,
                resolved_account_id,
                key_name,
                force=force,
                key_type=key_type,
                expires_at=requested_expiry,
            )
            if key_reused:
                where = "your profile" if not is_model_key else f"your profile ({env_var})"
                _say(
                    output_json,
                    success,
                    f"Reusing the key already in {where}: {mask_api_key(api_key)}",
                )
                record, _ = _lookup_key_record(api, region, jwt_token, resolved_account_id, api_key)
                key_details = (
                    (None, None) if record is None else _key_details(record, key_type, None)
                )
                warnings.extend(_reused_key_warnings(key_details, key_type, expires_in))
                for message in warnings:
                    _say(output_json, warning, message)
            else:
                key_details = _key_details(response, key_type, requested_expiry)
                _say(output_json, success, f"Created API key '{key_name}': {mask_api_key(api_key)}")
            found_type, found_expiry = key_details

            step = "credentials"
            if is_model_key:
                # A model key can't run the ADK, so it never becomes the ADK credential.
                credentials_summary = None
            else:
                saved, credentials_summary = _save_credentials(region, api_key)
                if saved:
                    _say(output_json, info, f"Saved to {credentials_summary}.")
                else:
                    _say(output_json, info, f"Existing ADK credential for {region} kept.")

            step = "activation"
            key_active = _wait_for_activation(api, region, api_key, output_json)
            if not key_active:
                warnings.append(NOT_ACTIVE_WARNING)
                _say(output_json, warning, NOT_ACTIVE_WARNING)

            step = "env"
            target, masked_line = write_env_var(env_var, api_key, force=force)
            _say(output_json, info, f"Wrote to {target.path}:")
            _say(output_json, plain, f"  {masked_line}")

            if output_json:
                _print_json(
                    resolved_account_id,
                    api_key,
                    key_name,
                    key_reused,
                    credentials_summary,
                    target,
                    key_active,
                    key_type=found_type,
                    expires_at=found_expiry,
                    env_var=env_var,
                    warnings=warnings,
                )
            else:
                _print_summary(
                    resolved_account_id,
                    api_key,
                    key_name,
                    key_reused,
                    credentials_summary,
                    target,
                    masked_line,
                    key_type=found_type,
                    expires_at=found_expiry,
                    env_var=env_var,
                )

        except (EnvVarConflict, ProfileKeyRefused) as e:
            _fail(e, step, exit_code=2, output_json=output_json, verbose=verbose)
        except (DeviceFlowError, requests.RequestException, PlatformAPIError, ValueError) as e:
            _fail(e, step, exit_code=1, output_json=output_json, verbose=verbose)
