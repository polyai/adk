"""Shared RFC 8628 device authorization flow, used by every command that signs a
user in via Auth0 (``poly login``, ``poly onboard``).

Copyright PolyAI Limited
"""

import logging
import time
import webbrowser
from collections.abc import Callable
from typing import Optional

import requests

from poly.handlers.auth0_handler import Auth0Handler, AuthDetails

logger = logging.getLogger(__name__)

# Ceiling for the poll interval when Auth0 repeatedly asks us to slow down, so
# a misbehaving server can't turn this into a near-infinite, ever-slower loop.
MAX_POLL_INTERVAL_SECONDS = 30


class DeviceFlowError(Exception):
    """Raised when the device authorization flow cannot complete.

    Callers decide how to surface this (e.g. print and exit for a CLI
    command); the flow itself never calls ``sys.exit``.
    """


def signin_with_device_flow(
    auth_details: AuthDetails,
    *,
    open_browser: bool = True,
    on_verification_url: Optional[Callable[[str, str], None]] = None,
) -> str:
    """Run the device authorization flow against ``auth_details`` and return a JWT.

    Args:
        auth_details: The Auth0 application (base URL + client id) to authenticate against.
        open_browser: Whether to open the verification URL in the user's default browser.
        on_verification_url: Called with ``(verification_uri, user_code)`` once the device
            code has been issued, so a caller can print its own framing. When omitted, the
            same message ``poly login`` has always shown is printed.

    Returns:
        The JWT access token.

    Raises:
        DeviceFlowError: The flow could not start, timed out, or was rejected.
    """
    from poly.output.console import console, info

    try:
        device_response = Auth0Handler.request_device_code_for(auth_details)
    except Exception as e:
        raise DeviceFlowError(f"Failed to start authorization: {e}") from e

    user_code = device_response["user_code"]
    verification_uri = device_response["verification_uri_complete"]
    device_code = device_response["device_code"]
    interval = device_response.get("interval", 5)

    if on_verification_url is not None:
        on_verification_url(verification_uri, user_code)
    else:
        info(
            "To sign in or create an account, open the following link in your browser\n"
            "and enter the code when prompted.\n\n"
            f"  URL:  {verification_uri}\n"
            f"  Code: [bold]{user_code}[/bold]"
        )

    if open_browser:
        webbrowser.open(verification_uri)

    access_token = None
    with console.status("[info]Waiting for authorization...[/info]"):
        while not access_token:
            time.sleep(interval)
            try:
                token_response = Auth0Handler.poll_device_token_for(auth_details, device_code)
                access_token = token_response.get("access_token")
            except requests.HTTPError as e:
                try:
                    body = e.response.json()
                except (ValueError, AttributeError):
                    raise DeviceFlowError(f"Authorization failed: {e}") from e
                err_code = body.get("error")
                if err_code == "authorization_pending":
                    continue
                elif err_code == "slow_down":
                    interval = min(interval + 5, MAX_POLL_INTERVAL_SECONDS)
                    continue
                elif err_code == "expired_token":
                    raise DeviceFlowError("Authorization timed out. Please try again.") from e
                else:
                    raise DeviceFlowError(
                        f"Authorization failed: {body.get('error_description', e)}"
                    ) from e

    return access_token
