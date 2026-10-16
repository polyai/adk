"""API key command: sign in and provision an account-scoped API key.

`poly apikey` is the narrower cousin of `poly login`: it exists to get an API key for
the PolyAI APIs and Dialog RSN into your environment, not to set up the ADK itself. It
signs a user in - via the GitHub-only Auth0 device flow for the default `studio` region, or
the standard sign-in page for any other region - creates their PolyAI account if needed,
provisions (or reuses) an account-scoped API key, and writes ``POLY_API_KEY`` into their
shell profile - or, on Windows, their user environment. It never prompts when run by an
agent (no terminal, or ``--json``); at a terminal it may ask which account to use. It keeps
the sign-in so a re-run does not sign in again. To set up the ADK itself,
use ``poly setup`` or ``poly login`` instead. See ``poly apikey --help`` or
``docs/docs/reference/cli/apikey.md`` for the full step-by-step behaviour.

Copyright PolyAI Limited
"""

import contextlib
import sys
import time
from argparse import ArgumentParser, Namespace, _SubParsersAction
from datetime import datetime, timezone
from typing import Callable

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.cli_commands.auth import authorise_or_explain
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS, REGION_TO_AUTH_DETAILS
from poly.handlers.interface import REGIONS, AgentStudioInterface
from poly.utils import apikey_session
from poly.utils.api_keys import select_reusable_api_key
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    load_api_key_from_credential_file,
    save_api_key_credential_file,
)
from poly.utils.env_profile import EnvVarConflict, ProfileTarget, write_env_var
from poly.utils.installs import shadow_json_field

DEFAULT_KEY_NAME = "cli-generated-key"
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


def _default_key_name(region: str) -> str:
    """The default API key name - disambiguated by region so keys never collide."""
    return DEFAULT_KEY_NAME if region == "studio" else f"{DEFAULT_KEY_NAME}-{region}"


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
        payload.update(shadow_json_field())
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


def _get_or_create_key(
    api: AgentStudioInterface, region: str, jwt_token: str, account_id: str, key_name: str
) -> tuple[str, bool]:
    """Reuse an active, unexpired key named `key_name`, or create one.

    Returns:
        tuple[str, bool]: The key, and whether it was reused rather than created.

    Raises:
        ValueError: The create call succeeded but returned no key.
    """
    keys = api.list_account_api_keys_internal(
        region=region, jwt_token=jwt_token, account_id=account_id, source=APIKEY_SOURCE
    )
    existing_key = select_reusable_api_key(keys, key_name, datetime.now(timezone.utc))
    if existing_key is not None:
        return existing_key, True

    response = api.create_account_api_key_internal(
        region=region,
        jwt_token=jwt_token,
        account_id=account_id,
        name=key_name,
        source=APIKEY_SOURCE,
    )
    api_key = response.get("key")
    if not api_key:
        raise ValueError("API key not found in response. Please contact support.")
    return api_key, False


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


def _print_summary(
    account_id: str,
    api_key: str,
    key_name: str,
    key_reused: bool,
    credentials_summary: str,
    target: ProfileTarget,
    masked_line: str,
) -> None:
    """Print the human-readable completion summary."""
    from poly.output.console import mask_api_key, plain

    plain("")
    plain("Done.")
    plain(f"  Account:   {account_id}")
    plain(
        f"  API key:   {mask_api_key(api_key)}   "
        f"({key_name}, {'reused' if key_reused else 'created'})"
    )
    plain(f"  Saved to:  {credentials_summary}")
    plain(f"  Profile:   {target.path}  ({masked_line})")
    plain("")
    if target.shell == "powershell":
        plain("Open a new terminal to pick up POLY_API_KEY.")
    else:
        plain(f"Open a new terminal, or run `source {target.path}`, to pick up POLY_API_KEY.")
    plain("")
    plain("Next: make your first API call (POLY_API_KEY is already set).")


def _print_json(
    account_id: str,
    api_key: str,
    key_name: str,
    key_reused: bool,
    credentials_summary: str,
    target: ProfileTarget,
    key_active: bool,
) -> None:
    """Print the --json completion object."""
    from poly.output.console import mask_secret
    from poly.output.json_output import json_print

    json_print(
        {
            "success": True,
            "account_id": account_id,
            "key_name": key_name,
            "key_reused": key_reused,
            "api_key_masked": mask_secret(api_key),
            "credentials_file": credentials_summary,
            "profile_path": str(target.path),
            "profile_shell": target.shell,
            "key_active": key_active,
            "next_step_url": NEXT_STEP_URL,
            **shadow_json_field(),
        }
    )


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
                "Sign in, create (or reuse) an account-scoped API key, and export it as"
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
                "  poly apikey --region us-1\n"
                "  poly apikey --region studio --json\n"
            ),
        )
        apikey_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
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
                f" studio, or '{DEFAULT_KEY_NAME}-<region>' for any other region."
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
            help="Overwrite an existing POLY_API_KEY in your profile if it holds a different value.",
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
    ) -> None:
        """Sign in and provision an account API key for `region`, then export it."""
        import requests

        from poly.output.console import err_console, info, mask_api_key, plain, success

        key_name = key_name if key_name is not None else _default_key_name(region)

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
                except requests.HTTPError as e:
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
            api_key, key_reused = _get_or_create_key(
                api, region, jwt_token, resolved_account_id, key_name
            )
            if key_reused:
                _say(
                    output_json,
                    success,
                    f"Reusing existing '{key_name}' key: {mask_api_key(api_key)}",
                )
            else:
                _say(output_json, success, f"Created API key '{key_name}': {mask_api_key(api_key)}")

            step = "credentials"
            saved, credentials_summary = _save_credentials(region, api_key)
            if saved:
                _say(output_json, info, f"Saved to {credentials_summary}.")
            else:
                _say(output_json, info, f"Existing ADK credential for {region} kept.")

            step = "activation"
            from poly.output.console import console, warning

            status_ctx = (
                contextlib.nullcontext()
                if output_json
                else console.status("[info]Verifying API key is active...[/info]")
            )
            with status_ctx:
                key_active = _wait_for_key_active(api, region, api_key)
            if not key_active:
                _say(
                    output_json,
                    warning,
                    "API key was saved but is not active yet."
                    " If your next command fails, wait a moment and retry.",
                )

            step = "env"
            target, masked_line = write_env_var("POLY_API_KEY", api_key, force=force)
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
                )

        except EnvVarConflict as e:
            _fail(e, step, exit_code=2, output_json=output_json, verbose=verbose)
        except (DeviceFlowError, requests.HTTPError, ValueError) as e:
            _fail(e, step, exit_code=1, output_json=output_json, verbose=verbose)
