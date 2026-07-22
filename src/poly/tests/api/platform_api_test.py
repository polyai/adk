"""Tests for the PlatformAPIHandler

Copyright PolyAI Limited
"""

import json
import unittest
from unittest.mock import patch

import requests

from poly.handlers.platform_api import ACCOUNTS_URL, PlatformAPIHandler
from poly.tests.testing_utils import make_mock_response


class GetBaseUrl(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_base_url region mapping."""

    def test_standard_regions_map_to_expected_urls(self):
        """Each known region resolves to its standard API base URL."""
        expected = {
            "dev": "https://api.dev.poly.ai",
            "staging": "https://api.staging.poly.ai",
            "euw-1": "https://api.eu.poly.ai",
            "uk-1": "https://api.uk.poly.ai",
            "us-1": "https://api.us.poly.ai",
            "studio": "https://api.studio.poly.ai",
        }
        for region, url in expected.items():
            self.assertEqual(PlatformAPIHandler.get_base_url(region), url)

    def test_jupiter_regions_map_to_expected_urls(self):
        """Each known region resolves to its Jupiter API base URL."""
        expected = {
            "euw-1": "https://jupiter-api.euw-1.platform.polyai.app",
            "uk-1": "https://jupiter-api.uk-1.platform.polyai.app",
            "us-1": "https://jupiter-api.us-1.platform.polyai.app",
            "dev": "https://jupiter-api.dev.polyai.app",
            "staging": "https://jupiter-api.staging.us-1.platform.polyai.app",
            "studio": "https://jupiter-api.plg-us-1-prod.polyai.app",
        }
        for region, url in expected.items():
            self.assertEqual(PlatformAPIHandler.get_base_url(region, use_jupiter_api=True), url)

    def test_unknown_region_raises_value_error(self):
        """An unrecognised region raises ValueError."""
        with self.assertRaises(ValueError):
            PlatformAPIHandler.get_base_url("mars-1")

    def test_unknown_jupiter_region_raises_value_error(self):
        """An unrecognised region raises ValueError even for the Jupiter map."""
        with self.assertRaises(ValueError):
            PlatformAPIHandler.get_base_url("mars-1", use_jupiter_api=True)


class MakeRequest(unittest.TestCase):
    """Tests for PlatformAPIHandler.make_request HTTP behaviour."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_default_headers_include_api_key_and_adk_metadata(self, mock_request, _mock_key):
        """Default headers carry the API key, an adk correlation id, and the source."""
        mock_request.return_value = make_mock_response(200, json_body={"ok": True})

        PlatformAPIHandler.make_request("studio", "/adk/v1/accounts")

        headers = mock_request.call_args.kwargs["headers"]
        self.assertEqual(headers["X-API-KEY"], "secret-key")
        self.assertTrue(headers["X-PolyAI-Correlation-Id"].startswith("adk-"))
        self.assertEqual(headers["X-Poly-Source"], "adk")
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_post_body_is_json_encoded(self, mock_request, _mock_key):
        """POST data is serialised to a JSON string in the request body."""
        mock_request.return_value = make_mock_response(200, json_body={})

        PlatformAPIHandler.make_request("studio", "/x", method="POST", data={"name": "abc"})

        sent = mock_request.call_args.kwargs["data"]
        self.assertEqual(json.loads(sent), {"name": "abc"})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_204_returns_empty_dict(self, mock_request, _mock_key):
        """A 204 No Content response returns an empty dict without parsing JSON."""
        mock_request.return_value = make_mock_response(204)

        self.assertEqual(PlatformAPIHandler.make_request("studio", "/x"), {})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_client_error_raises_http_error(self, mock_request, _mock_key):
        """A 4xx response propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(404, json_body={"error": "nope"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.make_request("studio", "/x")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_server_error_raises_http_error(self, mock_request, _mock_key):
        """A 5xx response propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(500, json_body={"error": "boom"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.make_request("studio", "/x")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_undecodable_json_raises_value_error(self, mock_request, _mock_key):
        """A 200 response with an unparseable body raises ValueError."""
        mock_request.return_value = make_mock_response(200, json_body=None, content=b"<html>")

        with self.assertRaises(ValueError):
            PlatformAPIHandler.make_request("studio", "/x")


class GetAccessibleRegions(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_accessible_regions."""

    @patch("poly.handlers.platform_api.any_credentials_exist", return_value=True)
    @patch("poly.handlers.platform_api.PlatformAPIHandler.get_accounts")
    def test_returns_accessible_regions_in_input_order(self, mock_get_accounts, _mock_creds):
        """Regions returning accounts are kept; exceptions are swallowed; order preserved."""

        def fake_get_accounts(region):
            if region == "us-1":
                return {"acc-1": "Account One"}
            if region == "uk-1":
                raise requests.HTTPError("forbidden")
            if region == "euw-1":
                return {"acc-2": "Account Two"}
            return {}  # region with no accounts is not accessible

        mock_get_accounts.side_effect = fake_get_accounts

        result = PlatformAPIHandler.get_accessible_regions(["us-1", "uk-1", "euw-1", "studio"])

        self.assertEqual(result, ["us-1", "euw-1"])

    @patch("poly.handlers.platform_api.any_credentials_exist", return_value=False)
    @patch(
        "poly.handlers.platform_api.retrieve_api_key",
        side_effect=ValueError("No API key configured"),
    )
    def test_missing_credentials_raises_value_error(self, _mock_key, _mock_creds):
        """When no credentials exist, the probe raises a ValueError with setup guidance."""
        with self.assertRaises(ValueError):
            PlatformAPIHandler.get_accessible_regions(["studio"])


class GetAccounts(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_accounts."""

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_only_active_accounts_with_id_and_name_are_returned(self, mock_make_request):
        """Inactive accounts and accounts missing id/name are filtered out."""
        mock_make_request.return_value = [
            {"id": "a1", "name": "Active One", "active": True},
            {"id": "a2", "name": "Inactive", "active": False},
            {"id": "a3", "active": True},  # missing name
            {"name": "No Id", "active": True},  # missing id
        ]

        accounts = PlatformAPIHandler.get_accounts("studio")

        self.assertEqual(accounts, {"a1": "Active One"})
        mock_make_request.assert_called_once_with("studio", ACCOUNTS_URL, "GET")

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_non_list_response_raises_value_error(self, mock_make_request):
        """A response that is not a list raises ValueError."""
        mock_make_request.return_value = {"unexpected": "shape"}

        with self.assertRaises(ValueError):
            PlatformAPIHandler.get_accounts("studio")


class GetProjects(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_projects."""

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_returns_id_to_name_mapping(self, mock_make_request):
        """Projects with an id and name are mapped id -> name."""
        mock_make_request.return_value = {
            "projects": [
                {"id": "p1", "name": "Project One"},
                {"id": "p2", "name": "Project Two"},
                {"id": "p3"},  # missing name is skipped
            ]
        }

        projects = PlatformAPIHandler.get_projects("studio", "acc-1")

        self.assertEqual(projects, {"p1": "Project One", "p2": "Project Two"})


class GetConversationAudio(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_conversation_audio."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.get")
    def test_returns_raw_audio_bytes(self, mock_get, _mock_key):
        """The raw response content is returned as bytes."""
        mock_get.return_value = make_mock_response(200, content=b"RIFF-audio-data")

        audio = PlatformAPIHandler.get_conversation_audio("studio", "agent-1", "conv-1")

        self.assertEqual(audio, b"RIFF-audio-data")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.get")
    def test_error_status_raises_http_error(self, mock_get, _mock_key):
        """A failing audio request propagates as requests.HTTPError."""
        mock_get.return_value = make_mock_response(404, content=b"not found")

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.get_conversation_audio("studio", "agent-1", "conv-1")


if __name__ == "__main__":
    unittest.main()
