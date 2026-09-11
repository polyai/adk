"""Tests for the shared device authorization flow.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.auth.device_flow import DeviceFlowError, signin_with_device_flow
from poly.handlers.auth0_handler import AuthDetails

AUTH_DETAILS = AuthDetails(base_url="https://login.test", device_client_id="test-client-id")

DEVICE_CODE_RESPONSE = {
    "device_code": "dc-1",
    "user_code": "ABCD-EFGH",
    "verification_uri_complete": "https://login.test/activate?user_code=ABCD-EFGH",
    "interval": 0,
}


def _http_error(error_code: str, description: str | None = None) -> requests.HTTPError:
    """Build an HTTPError shaped like Auth0's device-flow poll error responses."""
    body = {"error": error_code}
    if description is not None:
        body["error_description"] = description
    response = MagicMock()
    response.json.return_value = body
    err = requests.HTTPError(response=response)
    return err


class SigninWithDeviceFlow(unittest.TestCase):
    """Tests for signin_with_device_flow."""

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_success_on_first_poll(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """Returns the access token as soon as the first poll succeeds."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.return_value = {"access_token": "tok-1"}

        token = signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(token, "tok-1")
        mock_open.assert_called_once_with(DEVICE_CODE_RESPONSE["verification_uri_complete"])
        mock_poll.assert_called_once_with(AUTH_DETAILS, "dc-1")

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_pending_then_success(self, mock_open, mock_request_code, mock_poll, mock_sleep):
        """authorization_pending is retried until the token comes back."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.side_effect = [
            _http_error("authorization_pending"),
            _http_error("authorization_pending"),
            {"access_token": "tok-1"},
        ]

        token = signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(token, "tok-1")
        self.assertEqual(mock_poll.call_count, 3)

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_slow_down_increases_interval_up_to_cap(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """slow_down increases the poll interval by 5s each time, capped at 30s."""
        mock_request_code.return_value = {**DEVICE_CODE_RESPONSE, "interval": 28}
        mock_poll.side_effect = [
            _http_error("slow_down"),
            _http_error("slow_down"),
            {"access_token": "tok-1"},
        ]

        token = signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(token, "tok-1")
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        # Starts at 28s, then capped at 30s after the first slow_down (28+5=33 -> 30).
        self.assertEqual(sleep_calls, [28, 30, 30])

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_expired_token_raises_device_flow_error(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """expired_token raises DeviceFlowError with a user-facing retry message."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.side_effect = _http_error("expired_token")

        with self.assertRaises(DeviceFlowError) as ctx:
            signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(str(ctx.exception), "Authorization timed out. Please try again.")

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_unknown_error_raises_with_description(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """An unrecognized error code raises DeviceFlowError with its description."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.side_effect = _http_error("invalid_grant", description="Something went wrong")

        with self.assertRaises(DeviceFlowError) as ctx:
            signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(str(ctx.exception), "Authorization failed: Something went wrong")

    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_request_device_code_failure_raises_device_flow_error(
        self, mock_open, mock_request_code
    ):
        """A failure starting the flow raises DeviceFlowError rather than propagating."""
        mock_request_code.side_effect = ValueError("boom")

        with self.assertRaises(DeviceFlowError) as ctx:
            signin_with_device_flow(AUTH_DETAILS)

        self.assertEqual(str(ctx.exception), "Failed to start authorization: boom")
        mock_open.assert_not_called()

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_open_browser_false_does_not_open_browser(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """open_browser=False never launches a browser, even on success."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.return_value = {"access_token": "tok-1"}

        signin_with_device_flow(AUTH_DETAILS, open_browser=False)

        mock_open.assert_not_called()

    @patch("poly.auth.device_flow.time.sleep")
    @patch("poly.auth.device_flow.Auth0Handler.poll_device_token_for")
    @patch("poly.auth.device_flow.Auth0Handler.request_device_code_for")
    @patch("poly.auth.device_flow.webbrowser.open")
    def test_on_verification_url_callback_used_instead_of_default_message(
        self, mock_open, mock_request_code, mock_poll, mock_sleep
    ):
        """When given, on_verification_url is called instead of printing the default message."""
        mock_request_code.return_value = DEVICE_CODE_RESPONSE
        mock_poll.return_value = {"access_token": "tok-1"}
        callback = MagicMock()

        signin_with_device_flow(AUTH_DETAILS, on_verification_url=callback)

        callback.assert_called_once_with(
            DEVICE_CODE_RESPONSE["verification_uri_complete"],
            DEVICE_CODE_RESPONSE["user_code"],
        )


if __name__ == "__main__":
    unittest.main()
