"""Tests for the Auth0Handler

Copyright PolyAI Limited
"""

import json
import unittest
from unittest.mock import patch

import requests

from poly.handlers.auth0_handler import REGION_TO_AUTH_DETAILS, Auth0Handler
from poly.tests.testing_utils import make_mock_response


class MakeRequest(unittest.TestCase):
    """Tests for Auth0Handler.make_request logging and error handling."""

    @patch("poly.handlers.auth0_handler.requests.request")
    def test_sensitive_fields_are_redacted_in_logs(self, mock_request):
        """password, client_id, and device_code are replaced with <redacted> in logs."""
        mock_request.return_value = make_mock_response(200, json_body={"ok": True})
        data = {"password": "hunter2", "client_id": "abc", "device_code": "xyz", "scope": "openid"}

        with self.assertLogs("poly.handlers.auth0_handler", level="DEBUG") as logs:
            Auth0Handler.make_request("https://login.test", "/oauth/token", "POST", data=data)

        log_output = "\n".join(logs.output)
        self.assertNotIn("hunter2", log_output)
        self.assertNotIn("xyz", log_output)
        self.assertEqual(log_output.count("<redacted>"), 3)
        self.assertIn("openid", log_output)  # non-sensitive fields are preserved

    @patch("poly.handlers.auth0_handler.requests.request")
    def test_http_error_propagates(self, mock_request):
        """A failing request propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(403, json_body={"error": "denied"})

        with self.assertRaises(requests.HTTPError):
            Auth0Handler.make_request("https://login.test", "/oauth/token", "POST")


class RequestDeviceCode(unittest.TestCase):
    """Tests for Auth0Handler.request_device_code."""

    @patch("poly.handlers.auth0_handler.requests.request")
    def test_sends_expected_payload_and_returns_body(self, mock_request):
        """The device code request carries the region's client id and returns the parsed body."""
        mock_request.return_value = make_mock_response(
            200, json_body={"device_code": "dc-1", "user_code": "ABCD"}
        )

        result = Auth0Handler.request_device_code("studio")

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(sent["client_id"], REGION_TO_AUTH_DETAILS["studio"].device_client_id)
        self.assertEqual(sent["audience"], "https://platform.polyai.app/api")
        self.assertEqual(result, {"device_code": "dc-1", "user_code": "ABCD"})

    def test_unknown_region_raises_value_error(self):
        """An unknown region raises ValueError before any request is made."""
        with self.assertRaises(ValueError):
            Auth0Handler.request_device_code("mars-1")


class PollDeviceToken(unittest.TestCase):
    """Tests for Auth0Handler.poll_device_token."""

    @patch("poly.handlers.auth0_handler.requests.request")
    def test_sends_device_code_grant_and_returns_token(self, mock_request):
        """The poll request uses the device_code grant and returns the parsed token body."""
        mock_request.return_value = make_mock_response(
            200, json_body={"access_token": "tok-1", "id_token": "id-1"}
        )

        result = Auth0Handler.poll_device_token("studio", "dc-1")

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(sent["grant_type"], "urn:ietf:params:oauth:grant-type:device_code")
        self.assertEqual(sent["device_code"], "dc-1")
        self.assertEqual(result, {"access_token": "tok-1", "id_token": "id-1"})

    def test_unknown_region_raises_value_error(self):
        """An unknown region raises ValueError before any request is made."""
        with self.assertRaises(ValueError):
            Auth0Handler.poll_device_token("mars-1", "dc-1")


if __name__ == "__main__":
    unittest.main()
