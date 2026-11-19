"""Auth command family: login.

Copyright PolyAI Limited
"""

import os
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import REGION_CHOICES, region_type
from poly.handlers.auth0_handler import REGION_TO_AUTH_DETAILS, AuthDetails
from poly.handlers.interface import AgentStudioInterface
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    load_api_key_from_credential_file,
    matching_key_records,
    save_api_key_credential_file,
)

# Agent Studio refuses to create a PAT for a user who already holds this many.
MAX_PATS_PER_USER = 2


def _select_region() -> str:
    """Interactively select a region."""
    import questionary

    return questionary.select(
        "Select your region:",
        choices=[
            questionary.Choice("Studio", value="studio"),
            questionary.Choice("US — Enterprise", value="us-1"),
            questionary.Choice("UK — Enterprise", value="uk-1"),
            questionary.Choice("EU West — Enterprise", value="euw-1"),
        ],
        default="studio",
    ).ask()


def authorise_or_explain(
    api: AgentStudioInterface, region: str, jwt_token: str, *, self_serve_hint: str
) -> dict:
    """Authorise the signed-in user on ``region``, explaining the one expected failure.

    On an enterprise region (anything but ``studio``) the authorise endpoint only
    auto-provisions PolyAI staff; anyone else who signs in at that region's Auth0
    tenant without having been invited into an account gets a 403. Turn that into a
    ValueError that says what to do, and let every other error propagate.

    Args:
        api: The platform API interface.
        region: The region the user signed in to.
        jwt_token: The JWT from the device flow.
        self_serve_hint: How to reach the self-serve studio region from this command,
            e.g. "run `poly apikey --region studio`".
    """
    import requests

    try:
        return api.authorise(region=region, jwt_token=jwt_token)
    except requests.HTTPError as e:
        if region != "studio" and e.response is not None and e.response.status_code == 403:
            raise ValueError(
                f"No account is provisioned for you on {region}. Enterprise accounts are"
                " set up by PolyAI - contact your PolyAI representative, or"
                f" {self_serve_hint} to create a self-serve studio account."
            ) from e
        raise


def _is_own_pat(key: str, user_pats: list[dict]) -> bool:
    """Whether `key` is one of the signed-in user's PATs.

    Every PAT in the list is the user's own, so more than one match still means yes.
    """
    return bool(matching_key_records(key, user_pats))


def _authenticate_and_save_key(jwt_access_token: str, region: str) -> None:
    """Authorise the user, then keep their saved PAT or create one and save it.

    The saved PAT for `region` is kept when it is still one of the signed-in user's PATs.
    Otherwise a new one is created, since the platform only shows a PAT's secret once. A
    user already at the PAT limit is told to delete one in Agent Studio first.
    Waits for a new key to become active before returning, so a command run
    immediately afterwards (e.g. project creation) does not fail against a key
    the platform has not finished activating.
    """
    import time

    from poly.output.console import console, error, info, mask_api_key, plain, success, warning

    api_handler = AgentStudioInterface()

    info("Setting up your account...")
    try:
        authorise_or_explain(
            api_handler,
            region,
            jwt_access_token,
            self_serve_hint="run `poly login --region studio`",
        )
    except ValueError as e:
        error(str(e))
        sys.exit(1)

    info("Fetching API key...")
    user_pats = api_handler.get_pats(region=region, jwt_token=jwt_access_token)
    saved_key = load_api_key_from_credential_file(region)
    if saved_key and _is_own_pat(saved_key, user_pats):
        os.environ["POLY_ADK_KEY"] = saved_key
        success(f"Using the API key already saved for {region}: {mask_api_key(saved_key)}")
        info(f"Credential file path: {CREDENTIALS_FILE_PATH}")
        plain("")
        return

    if len(user_pats) >= MAX_PATS_PER_USER:
        error(
            f"You already have {len(user_pats)} personal access tokens on {region}, the"
            " maximum. Delete one in Agent Studio (your account's Personal Access Token tab),"
            " then run this command again."
        )
        sys.exit(1)

    with console.status("[info]Creating a new API key...[/info]"):
        pat = api_handler.create_pat(region=region, jwt_token=jwt_access_token, name="adk-key")
    os.environ["POLY_ADK_KEY"] = pat
    success(f"Created a new API Key: {mask_api_key(pat)}")

    save_api_key_credential_file(pat, region=region)
    plain("API key has been saved to your credential file for future use.")
    info(f"Credential file path: {CREDENTIALS_FILE_PATH}")
    plain("")

    # A newly created PAT can take a few seconds to activate. Wait here so that
    # 'poly login' and 'poly setup' hand back a key that actually works.
    with console.status("[info]Verifying API key is active...[/info]"):
        for _ in range(20):
            try:
                api_handler.get_accounts(region=region)
                break
            except Exception:
                time.sleep(1)
        else:
            warning(
                "API key was saved but is not active yet."
                " If your next command fails, wait a moment and retry."
            )


def _signin(region: str, auth_details: AuthDetails | None = None) -> str:
    """Sign in via the Auth0 device authorization flow and return a JWT access token.

    Args:
        region: The region to sign in to; picks the Auth0 client unless overridden.
        auth_details: An Auth0 client to use instead of the region's default.
    """
    from poly.output.console import error, success

    auth_details = auth_details or REGION_TO_AUTH_DETAILS.get(region)
    if auth_details is None:
        error(
            f"Failed to start authorization: Unknown region '{region}'. "
            f"Valid regions: {', '.join(REGION_TO_AUTH_DETAILS)}"
        )
        sys.exit(1)

    try:
        access_token = signin_with_device_flow(auth_details)
    except DeviceFlowError as e:
        error(str(e))
        sys.exit(1)

    success("Authenticated successfully!")
    return access_token


class LoginCommand(BaseCommand):
    """Log in to an existing Agent Studio account and save API key credentials."""

    command = "login"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``login`` subcommand."""
        login_parser = subparsers.add_parser(
            "login",
            parents=[parents.verbose, parents.debug],
            help="Log in to an existing Agent Studio account",
            description=(
                "Log in to your existing Agent Studio account and save API key credentials"
                " for CLI access.\n\n"
                "This command will open a browser window for you to authenticate and authorize"
                " the CLI. After successful authentication, the necessary API key credentials"
                " will be saved to a local credential file for future CLI commands.\n\n"
                "Examples:\n"
                "  poly login\n"
                "  poly login --region us\n"
            ),
        )
        login_parser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            default=None,
            help="Region to log in to. If omitted, you will be prompted to select one.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the login handler."""
        cls.login(region=args.region)

    @classmethod
    def login(cls, region: str | None = None) -> None:
        """Log in to an existing Agent Studio account and save API key credentials."""
        import questionary

        from poly.output.console import plain, print_welcome_message, success

        print_welcome_message()
        plain(
            "This will guide you through logging in to your Agent Studio account"
            " and setting up your API key for use with the ADK."
        )
        questionary.press_any_key_to_continue("Press any key to continue...").ask()

        if region is None:
            region = _select_region()

        jwt_access_token = _signin(region)
        _authenticate_and_save_key(jwt_access_token, region=region)
        success("Logged in successfully!")
