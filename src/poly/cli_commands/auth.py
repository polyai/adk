"""Auth command family: login.

Copyright PolyAI Limited
"""

import os
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.handlers.auth0_handler import Auth0Handler
from poly.handlers.interface import REGIONS, AgentStudioInterface
from poly.utils import (
    CREDENTIALS_FILE_PATH,
    save_api_key_credential_file,
)


def _select_region() -> str:
    """Interactively select a region."""
    import questionary

    return questionary.select(
        "Select your region:",
        choices=[
            questionary.Choice("Studio", value="studio"),
            questionary.Choice("US (us-1) — Enterprise", value="us-1"),
            questionary.Choice("UK (uk-1) — Enterprise", value="uk-1"),
            questionary.Choice("EU West (euw-1) — Enterprise", value="euw-1"),
        ],
        default="studio",
    ).ask()


def _authenticate_and_save_key(jwt_access_token: str, region: str) -> None:
    """Authorise the user, fetch or create a PAT, and save it to the credential file.

    Waits for the key to become active before returning, so a command run
    immediately afterwards (e.g. project creation) does not fail against a key
    the platform has not finished activating.
    """
    import time

    from poly.output.console import console, error, info, mask_api_key, plain, success, warning

    api_handler = AgentStudioInterface()

    info("Setting up your account...")
    api_handler.authorise(region=region, jwt_token=jwt_access_token)

    info("Fetching API key...")
    user_pats = api_handler.get_pats(region=region, jwt_token=jwt_access_token)
    if user_pats:
        pat = user_pats[0].get("key")
        if not pat:
            error("API key not found in account data. Please contact support.")
            sys.exit(1)
        os.environ["POLY_ADK_KEY"] = pat
        success(f"Found existing API Token: {mask_api_key(pat)}")
    else:
        info("No existing API key found in your account.")
        ctx = console.status("[info]Creating a new API key...[/info]")
        with ctx:
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


def _signin(region: str) -> str:
    """Sign in via the Auth0 device authorization flow and return a JWT access token."""
    import time
    import webbrowser

    import requests

    from poly.output.console import console, error, info, success

    auth0_handler = Auth0Handler()

    try:
        device_response = auth0_handler.request_device_code(region)
    except Exception as e:
        error(f"Failed to start authorization: {e}")
        sys.exit(1)

    user_code = device_response["user_code"]
    verification_uri = device_response["verification_uri_complete"]
    device_code = device_response["device_code"]
    interval = device_response.get("interval", 5)

    info(
        "To sign in or create an account, open the following link in your browser\n"
        "and enter the code when prompted.\n\n"
        f"  URL:  {verification_uri}\n"
        f"  Code: [bold]{user_code}[/bold]"
    )
    webbrowser.open(verification_uri)

    access_token = None
    with console.status("[info]Waiting for authorization...[/info]"):
        while not access_token:
            time.sleep(interval)
            try:
                token_response = auth0_handler.poll_device_token(region, device_code)
                access_token = token_response.get("access_token")
            except requests.HTTPError as e:
                try:
                    body = e.response.json()
                except (ValueError, AttributeError):
                    error(f"Authorization failed: {e}")
                    sys.exit(1)
                err_code = body.get("error")
                if err_code == "authorization_pending":
                    continue
                elif err_code == "slow_down":
                    interval += 5
                    continue
                elif err_code == "expired_token":
                    error("Authorization timed out. Please try again.")
                    sys.exit(1)
                else:
                    error(f"Authorization failed: {body.get('error_description', e)}")
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
                "  poly login --region us-1\n"
            ),
        )
        login_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
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
