"""API key command: sign in and provision an account-scoped API key.

`poly apikey` is the narrower cousin of `poly login`: it exists to get an API key for
the PolyAI APIs and Dialog RSN into your environment, not to set up the ADK itself. It
signs a user in - via the GitHub-only Auth0 device flow for the default `studio` region, or
the standard sign-in page for any other region - creates their PolyAI account if needed,
provisions (or reuses) an account-scoped API key, and writes ``POLY_API_KEY`` into their
shell profile - or, on Windows, their user environment. It never prompts. To set up the
ADK itself, use ``poly setup`` or ``poly login`` instead. See ``poly apikey --help`` or
``docs/docs/reference/cli/apikey.md`` for the full step-by-step behaviour.

Copyright PolyAI Limited
"""

import contextlib
import sys
import time
import traceback
from argparse import ArgumentParser, Namespace, _SubParsersAction
from datetime import datetime, timezone
from typing import Callable

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS, REGION_TO_AUTH_DETAILS
from poly.handlers.interface import REGIONS, AgentStudioInterface
from poly.utils.api_keys import select_reusable_api_key
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    load_api_key_from_credential_file,
    save_api_key_credential_file,
)
from poly.utils.env_profile import EnvVarConflict, ProfileTarget, write_env_var

DEFAULT_KEY_NAME = "cli-generated-key"
ACCOUNT_POLL_ATTEMPTS = 20
ACCOUNT_POLL_INTERVAL_SECONDS = 1
ACCOUNT_POLL_TIMEOUT_SECONDS = ACCOUNT_POLL_ATTEMPTS * ACCOUNT_POLL_INTERVAL_SECONDS
APIKEY_SOURCE = "apikey"


def _default_key_name(region: str) -> str:
    """The default API key name - disambiguated by region so keys never collide."""
    return DEFAULT_KEY_NAME if region == "studio" else f"{DEFAULT_KEY_NAME}-{region}"


def _say(output_json: bool, fn: Callable[[str], None], message: str) -> None:
    """Print via `fn` unless --json is active (stdout must then be a single JSON object)."""
    if not output_json:
        fn(message)


def _fail(exc: Exception, step: str, exit_code: int, *, output_json: bool, verbose: bool) -> None:
    """Print a clean error (or re-raise under --verbose) and exit."""
    if verbose:
        raise exc
    message = str(exc)
    if isinstance(exc, EnvVarConflict):
        message = f"{exc} Re-run with --force to replace it."
    if output_json:
        from poly.output.json_output import json_print

        json_print(
            {
                "success": False,
                "error": message,
                "traceback": traceback.format_exc(),
                "step": step,
            }
        )
    else:
        from poly.output.console import error

        error(message)
    sys.exit(exit_code)


def _resolve_account_id(
    api: AgentStudioInterface, region: str, jwt_token: str, account_id: str | None
) -> str:
    """Return `account_id` unchanged, or poll for the account to appear.

    More than one account without an explicit `--account-id` is an error - silently
    picking one would be a guess.

    Raises:
        ValueError: No account appeared within `ACCOUNT_POLL_TIMEOUT_SECONDS`, or more
            than one account was found and `account_id` was not given.
    """
    if account_id is not None:
        return account_id
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        accounts = api.get_accounts_internal(
            region=region, jwt_token=jwt_token, source=APIKEY_SOURCE
        )
        if accounts:
            if len(accounts) > 1:
                listing = ", ".join(f"{a['id']} ({a.get('name', 'unnamed')})" for a in accounts)
                raise ValueError(
                    f"Multiple accounts found for {region}: {listing}. "
                    "Re-run with --account-id <id> to pick one."
                )
            return accounts[0]["id"]
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


def _wait_for_key_active(api: AgentStudioInterface, region: str) -> bool:
    """Poll until the saved key is usable, mirroring `poly login`'s activation wait.

    A newly created key can take a few seconds to activate; polling here means a
    command run immediately after `poly apikey` does not fail against a key the
    platform has not finished activating yet.

    Returns:
        bool: Whether the key became active within the poll window.
    """
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        try:
            api.get_accounts(region=region)
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
                " POLY_API_KEY for use with the PolyAI APIs and Dialog RSN. Non-interactive,"
                " so an AI coding assistant can run it for you.\n\n"
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
                " Required when your account has more than one - the command refuses to"
                " guess which one you mean."
            ),
        )
        apikey_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite an existing POLY_API_KEY in your profile if it holds a different value.",
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

            jwt_token = signin_with_device_flow(
                auth_details, on_verification_url=on_verification_url
            )
            _say(output_json, success, "Authenticated successfully!")

            step = "authorise"
            api = AgentStudioInterface()
            _say(output_json, info, "Setting up your account...")
            try:
                api.authorise(region=region, jwt_token=jwt_token)
            except requests.HTTPError as e:
                if region != "studio" and e.response is not None and e.response.status_code == 403:
                    raise ValueError(
                        f"No account is provisioned for you on {region}. Enterprise accounts"
                        " are set up by PolyAI - contact your PolyAI representative, or run"
                        " `poly apikey --region studio` to create a self-serve studio account."
                    ) from e
                raise

            step = "account"
            resolved_account_id = _resolve_account_id(api, region, jwt_token, account_id)

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
                key_active = _wait_for_key_active(api, region)
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
