"""Onboard command: one-shot GitHub sign-in and account API key setup.

`poly onboard` signs a user in via the GitHub-only Auth0 device flow, creates
their PolyAI account if needed, provisions (or reuses) an account-scoped API
key, and writes ``POLY_API_KEY`` into their shell profile - or, on Windows,
their user environment. It never prompts. See ``poly onboard --help`` or
``docs/docs/reference/cli/onboard.md`` for the full step-by-step behaviour.

Copyright PolyAI Limited
"""

import logging
import platform
import sys
import time
import traceback
from argparse import ArgumentParser, Namespace, _SubParsersAction
from datetime import datetime, timezone
from importlib.metadata import version as get_package_version
from typing import Callable

import requests

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.handlers.auth0_handler import ONBOARD_AUTH_DETAILS
from poly.handlers.interface import AgentStudioInterface
from poly.handlers.posthog import (
    capture_event,
    flush,
    get_anonymous_id,
    get_posthog_client,
    telemetry_disabled,
)
from poly.utils.api_keys import select_reusable_api_key
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    load_api_key_from_credential_file,
    save_api_key_credential_file,
)
from poly.utils.env_profile import EnvVarConflict, ProfileTarget, detect_profile, write_env_var

logger = logging.getLogger(__name__)

# `poly onboard` always targets the PLG/studio cluster - it is the only
# cluster the onboarding Auth0 client (GitHub-only login) is registered
# against, so unlike `login` there is no --region choice here.
ONBOARD_REGION = "studio"

DEFAULT_KEY_NAME = "onboard-key"
ACCOUNT_POLL_ATTEMPTS = 20
ACCOUNT_POLL_INTERVAL_SECONDS = 1
ACCOUNT_POLL_TIMEOUT_SECONDS = ACCOUNT_POLL_ATTEMPTS * ACCOUNT_POLL_INTERVAL_SECONDS
POSTHOG_SOURCE = "onboard"


def _adk_version() -> str:
    """The installed ADK version, or "unknown" if it cannot be determined."""
    try:
        return get_package_version("polyai-adk")
    except Exception:
        return "unknown"


class _Reporter:
    """Quiet-when-json printing and telemetry, tied to the flow's distinct id.

    A small stateful object rather than closures, since the distinct id
    changes partway through the flow (from an anonymous id to the resolved
    account id) and every step after that needs to see the new value.
    """

    def __init__(self, output_json: bool, base_properties: dict[str, str]):
        self.output_json = output_json
        self.base_properties = base_properties
        # Skip creating ~/.poly/telemetry_id entirely when telemetry is off,
        # rather than writing it and then never using it.
        self.distinct_id = "disabled" if telemetry_disabled() else get_anonymous_id()

    def say(self, fn: Callable[[str], None], message: str) -> None:
        """Print via `fn`, unless --json is active - its output must be the only thing on stdout."""
        if not self.output_json:
            fn(message)

    def emit(self, event: str, **extra: object) -> None:
        """Capture a telemetry event tagged with the current distinct id."""
        capture_event(ONBOARD_REGION, event, {**self.base_properties, **extra}, self.distinct_id)

    def fail(self, exc: Exception, step: str, exit_code: int, *, verbose: bool) -> None:
        """Report a failure - telemetry, then a clean message or a full traceback - and exit."""
        self.emit("onboard_failed", step=step, error_class=type(exc).__name__)
        flush(ONBOARD_REGION)
        if verbose:
            raise exc
        message = str(exc)
        if isinstance(exc, EnvVarConflict):
            message = f"{exc} Re-run with --force to replace it."
        if self.output_json:
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


def _resolve_account_id(api: AgentStudioInterface, jwt_token: str, account_id: str | None) -> str:
    """Return `account_id` unchanged, or poll for the first account to appear.

    Raises:
        ValueError: No account appeared within `ACCOUNT_POLL_TIMEOUT_SECONDS`.
    """
    if account_id is not None:
        return account_id
    for _ in range(ACCOUNT_POLL_ATTEMPTS):
        accounts = api.get_accounts_internal(
            region=ONBOARD_REGION, jwt_token=jwt_token, source=POSTHOG_SOURCE
        )
        if accounts:
            return accounts[0]["id"]
        time.sleep(ACCOUNT_POLL_INTERVAL_SECONDS)
    raise ValueError(
        f"No account appeared after {ACCOUNT_POLL_TIMEOUT_SECONDS}s. Re-run with --account-id <id>."
    )


def _get_or_create_key(
    api: AgentStudioInterface, jwt_token: str, account_id: str, key_name: str
) -> tuple[str, bool]:
    """Reuse an active, unexpired key named `key_name`, or create one.

    Returns:
        tuple[str, bool]: The key, and whether it was reused rather than created.

    Raises:
        ValueError: The create call succeeded but returned no key.
    """
    keys = api.list_account_api_keys_internal(
        region=ONBOARD_REGION, jwt_token=jwt_token, account_id=account_id, source=POSTHOG_SOURCE
    )
    existing_key = select_reusable_api_key(keys, key_name, datetime.now(timezone.utc))
    if existing_key is not None:
        return existing_key, True

    response = api.create_account_api_key_internal(
        region=ONBOARD_REGION,
        jwt_token=jwt_token,
        account_id=account_id,
        name=key_name,
        source=POSTHOG_SOURCE,
    )
    api_key = response.get("key")
    if not api_key:
        raise ValueError("API key not found in response. Please contact support.")
    return api_key, False


def _save_credentials(api_key: str) -> tuple[bool, str]:
    """Save `api_key` to the credential file, unless studio already has one.

    Returns:
        tuple[bool, str]: Whether a new credential was saved, and a summary
            of what happened, for the completion output.
    """
    if load_api_key_from_credential_file(ONBOARD_REGION) is not None:
        return False, "existing credential kept"
    save_api_key_credential_file(api_key, region=ONBOARD_REGION)
    return True, f"{CREDENTIALS_FILE_PATH} ({ONBOARD_REGION})"


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
        }
    )


class OnboardCommand(BaseCommand):
    """One-shot GitHub sign-in, account API key, and POLY_API_KEY setup."""

    command = "onboard"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``onboard`` subcommand."""
        onboard_parser = subparsers.add_parser(
            "onboard",
            parents=[parents.verbose, parents.debug, parents.json],
            help="One-shot setup for AI coding assistants.",
            description=(
                "One-shot setup: GitHub sign-in, account API key, POLY_API_KEY in your"
                " environment.\n\n"
                "Never prompts. Designed to be run by an AI coding assistant; fine to run"
                " yourself.\n\n"
                "To sign in interactively instead, use `poly login`.\n\n"
                "Examples:\n"
                "  poly onboard\n"
                "  poly onboard --account-id acc-123\n"
            ),
        )
        onboard_parser.add_argument(
            "--key-name",
            type=str,
            default=DEFAULT_KEY_NAME,
            help=f"Name for the account-scoped API key. Defaults to '{DEFAULT_KEY_NAME}'.",
        )
        onboard_parser.add_argument(
            "--account-id",
            type=str,
            default=None,
            help="Account ID to scope the key to. Skips polling for a newly created account.",
        )
        onboard_parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite an existing POLY_API_KEY in your profile if it holds a different value.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the onboard handler."""
        cls.onboard(
            key_name=args.key_name,
            account_id=args.account_id,
            force=args.force,
            output_json=args.json,
            verbose=args.verbose,
        )

    @classmethod
    def onboard(
        cls,
        key_name: str = DEFAULT_KEY_NAME,
        account_id: str | None = None,
        force: bool = False,
        output_json: bool = False,
        verbose: bool = False,
    ) -> None:
        """Sign in via GitHub, provision an account API key, and export it."""
        from poly.output.console import err_console, info, mask_api_key, plain, success

        reporter = _Reporter(
            output_json,
            {
                "source": POSTHOG_SOURCE,
                "adk_version": _adk_version(),
                "os": platform.system(),
                "shell": detect_profile().shell,
            },
        )

        step = "start"
        try:
            reporter.emit("onboard_started")
            reporter.say(info, "Setting up your PolyAI account and API key...")

            step = "signin"

            def on_verification_url(verification_uri: str, user_code: str) -> None:
                message = (
                    "To sign in with GitHub, open the following link in your browser\n"
                    "and enter the code when prompted.\n\n"
                    f"  URL:  {verification_uri}\n"
                    f"  Code: [bold]{user_code}[/bold]"
                )
                if reporter.output_json:
                    # --json only constrains stdout - an agent that can't open a
                    # browser itself still needs this to complete sign-in, so it
                    # goes to stderr rather than being dropped like every other
                    # human-readable message in this mode.
                    err_console.print(f"[info]{message}[/info]")
                else:
                    reporter.say(info, message)
                reporter.emit("onboard_device_code_issued")

            jwt_token = signin_with_device_flow(
                ONBOARD_AUTH_DETAILS, on_verification_url=on_verification_url
            )
            reporter.emit("onboard_authenticated")
            reporter.say(success, "Authenticated successfully!")

            step = "authorise"
            api = AgentStudioInterface()
            reporter.say(info, "Setting up your account...")
            api.authorise(region=ONBOARD_REGION, jwt_token=jwt_token)

            step = "account"
            resolved_account_id = _resolve_account_id(api, jwt_token, account_id)
            reporter.emit("onboard_account_resolved", account_id=resolved_account_id)
            _alias_to_account(reporter.distinct_id, resolved_account_id)
            reporter.distinct_id = resolved_account_id

            step = "key"
            api_key, key_reused = _get_or_create_key(api, jwt_token, resolved_account_id, key_name)
            if key_reused:
                reporter.say(success, f"Reusing existing '{key_name}' key: {mask_api_key(api_key)}")
                reporter.emit(
                    "onboard_key_reused", account_id=resolved_account_id, key_name=key_name
                )
            else:
                reporter.say(success, f"Created API key '{key_name}': {mask_api_key(api_key)}")
                reporter.emit(
                    "onboard_key_created", account_id=resolved_account_id, key_name=key_name
                )

            step = "credentials"
            saved, credentials_summary = _save_credentials(api_key)
            if saved:
                reporter.say(info, f"Saved to {credentials_summary}.")
            else:
                reporter.say(info, f"Existing ADK credential for {ONBOARD_REGION} kept.")

            step = "env"
            target, masked_line = write_env_var("POLY_API_KEY", api_key, force=force)
            reporter.say(info, f"Wrote to {target.path}:")
            reporter.say(plain, f"  {masked_line}")
            reporter.emit(
                "onboard_env_written", account_id=resolved_account_id, profile_shell=target.shell
            )

            reporter.emit(
                "onboard_completed", account_id=resolved_account_id, key_reused=key_reused
            )
            flush(ONBOARD_REGION)

            if output_json:
                _print_json(
                    resolved_account_id, api_key, key_name, key_reused, credentials_summary, target
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
            reporter.fail(e, step, exit_code=2, verbose=verbose)
        except (DeviceFlowError, requests.HTTPError, ValueError) as e:
            reporter.fail(e, step, exit_code=1, verbose=verbose)


def _alias_to_account(anonymous_id: str, account_id: str) -> None:
    """Link the anonymous telemetry id to the resolved account, once.

    Never raises: a failure here must not interrupt onboarding.
    """
    if telemetry_disabled():
        return
    try:
        get_posthog_client(ONBOARD_REGION).alias(previous_id=anonymous_id, distinct_id=account_id)
    except Exception:
        logger.warning("PostHog alias failed", exc_info=True)
