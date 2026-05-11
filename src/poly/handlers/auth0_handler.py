"""Client for the PolyAI Auth0 tenant, used for authentication in the PolyAI ADK CLI.

Copyright PolyAI Limited
"""

import json
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://login.studio.poly.ai"
DEVICE_CLIENT_ID = "6uLCbsn6UxXJlnGKE4ypqwQqt3UqTUnd"
STUDIO_CLIENT_ID = "v7NO1stPOf28i9FCdbuhs5WSUbOHTVtG"
STUDIO_CONNECTION = "Self-Serve-Signup-Headless"


class Auth0Handler:
    """Handler for authentication with the PolyAI Auth0 tenant."""

    @staticmethod
    def make_request(
        endpoint: str, method: str, data: Optional[dict] = None, params: Optional[dict] = None
    ) -> dict:
        """Make a request to the Auth0 API."""
        url = BASE_URL + endpoint

        headers = {"Content-Type": "application/json"}

        api_response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            allow_redirects=False,
            data=json.dumps(data) if data else None,
        )

        cleaned_data = {
            k: ("<redacted>" if k in {"password", "client_id"} else v)
            for k, v in (data or {}).items()
        }

        try:
            api_response.raise_for_status()
            logger.debug(
                f"Request/response url={url!r} body={cleaned_data!r}"
                f" status_code={api_response.status_code!r} response={api_response.text!r}"
            )
        except requests.HTTPError:
            logger.debug(
                f"Error in request url={url!r} body={cleaned_data!r}"
                f" status_code={api_response.status_code!r} response={api_response.text!r}"
            )
            raise

        try:
            api_response = api_response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")

        logger.info(f"Request to {url} successful")
        return api_response

    @classmethod
    def register_user(cls, email: str, password: str, name: str) -> dict:
        """Register a new user with the Auth0 tenant."""
        data = {
            "client_id": STUDIO_CLIENT_ID,
            "connection": STUDIO_CONNECTION,
            "email": email,
            "password": password,
            "name": name,
            "user_metadata": {
                "terms_accepted_via_api": "on",
            },
        }
        return cls.make_request("/dbconnections/signup", method="POST", data=data)

    @classmethod
    def request_device_code(cls) -> dict:
        """Start the device authorization flow.

        Returns:
            Dict containing device_code, user_code, verification_uri,
            verification_uri_complete, expires_in, and interval.
        """
        data = {
            "client_id": DEVICE_CLIENT_ID,
            "scope": "openid profile email",
            "audience": "https://platform.polyai.app/api",
        }
        return cls.make_request("/oauth/device/code", method="POST", data=data)

    @classmethod
    def poll_device_token(cls, device_code: str) -> dict:
        """Poll for a token after the user has authorized the device.

        Args:
            device_code: The device_code from request_device_code.

        Returns:
            Dict containing access_token, id_token, etc. on success.

        Raises:
            requests.HTTPError: 403 with 'authorization_pending' or 'slow_down'
                while the user hasn't authorized yet.
        """
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": DEVICE_CLIENT_ID,
            "device_code": device_code,
        }
        return cls.make_request("/oauth/token", method="POST", data=data)
