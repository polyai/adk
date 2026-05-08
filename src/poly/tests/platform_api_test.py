"""Tests for PlatformAPIHandler

Copyright PolyAI Limited
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.constants import DEFAULT_VOICE_ID_FALLBACK, DEFAULT_VOICE_IDS
from poly.handlers.platform_api import PlatformAPIHandler


class MakeRequestTest(unittest.TestCase):
    """Tests for PlatformAPIHandler.make_request."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_uses_default_base_url_when_none_provided(self, mock_request, _mock_key):
        """make_request uses get_base_url when base_url is not specified."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_request.return_value = mock_response

        with patch.object(
            PlatformAPIHandler, "get_base_url", return_value="https://default.api"
        ) as mock_base:
            PlatformAPIHandler.make_request("us-1", "/test")

        mock_base.assert_called_once_with("us-1")
        assert mock_request.call_args.kwargs["url"] == "https://default.api/test"

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_uses_custom_base_url_when_provided(self, mock_request, _mock_key):
        """make_request uses the provided base_url instead of the default."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_request.return_value = mock_response

        PlatformAPIHandler.make_request("us-1", "/test", base_url="https://custom.api")

        assert mock_request.call_args.kwargs["url"] == "https://custom.api/test"

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_posts_json_body(self, mock_request, _mock_key):
        """make_request serialises data as JSON for POST requests."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"created": True}
        mock_request.return_value = mock_response

        PlatformAPIHandler.make_request(
            "us-1", "/items", "POST", data={"name": "x"}, base_url="https://api"
        )

        assert mock_request.call_args.kwargs["method"] == "POST"
        assert mock_request.call_args.kwargs["data"] == json.dumps({"name": "x"})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_raises_http_error_on_failure(self, mock_request, _mock_key):
        """make_request propagates HTTPError on non-2xx responses."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError("Forbidden")
        mock_request.return_value = mock_response

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.make_request("us-1", "/secret", base_url="https://api")


class CreateProjectTest(unittest.TestCase):
    """Tests for PlatformAPIHandler.create_project."""

    @patch.object(PlatformAPIHandler, "make_request")
    @patch.object(
        PlatformAPIHandler, "get_agents_api_url", return_value="https://agents.api"
    )
    def test_calls_make_request_with_agents_api_url(self, _mock_url, mock_make):
        """create_project delegates to make_request with the agents API base URL."""
        mock_make.return_value = {"agentId": "my-proj", "agentName": "My Proj"}

        result = PlatformAPIHandler.create_project("us-1", "acct-1", "My Proj", "my-proj")

        mock_make.assert_called_once()
        call_kwargs = mock_make.call_args
        assert call_kwargs.kwargs["base_url"] == "https://agents.api"
        assert call_kwargs.args[1] == "/accounts/acct-1/agents"
        assert call_kwargs.args[2] == "POST"
        assert result == {"id": "my-proj", "name": "My Proj"}

    @patch.object(PlatformAPIHandler, "make_request")
    @patch.object(
        PlatformAPIHandler, "get_agents_api_url", return_value="https://agents.api"
    )
    def test_slugifies_project_name_when_id_not_provided(self, _mock_url, mock_make):
        """create_project generates a slug from the name when project_id is omitted."""
        mock_make.return_value = {"agentId": "my-project", "agentName": "My Project"}

        PlatformAPIHandler.create_project("us-1", "acct-1", "My Project")

        data = mock_make.call_args.kwargs["data"]
        assert data["agentId"] == "my-project"

    @patch.object(PlatformAPIHandler, "make_request")
    @patch.object(
        PlatformAPIHandler, "get_agents_api_url", return_value="https://agents.api"
    )
    def test_uses_region_voice_id(self, _mock_url, mock_make):
        """create_project uses the voice ID mapped to the given region."""
        mock_make.return_value = {"agentId": "p", "agentName": "P"}

        PlatformAPIHandler.create_project("euw-1", "acct-1", "P", "p")

        data = mock_make.call_args.kwargs["data"]
        assert data["voiceSettings"]["voiceId"] == DEFAULT_VOICE_IDS["euw-1"]

    @patch.object(PlatformAPIHandler, "make_request")
    @patch.object(
        PlatformAPIHandler, "get_agents_api_url", return_value="https://agents.api"
    )
    def test_uses_fallback_voice_id_for_unknown_region(self, _mock_url, mock_make):
        """create_project falls back to DEFAULT_VOICE_ID_FALLBACK for unmapped regions."""
        mock_make.return_value = {"agentId": "p", "agentName": "P"}

        PlatformAPIHandler.create_project("unknown-region", "acct-1", "P", "p")

        data = mock_make.call_args.kwargs["data"]
        assert data["voiceSettings"]["voiceId"] == DEFAULT_VOICE_ID_FALLBACK
