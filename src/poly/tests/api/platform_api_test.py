"""Tests for the PlatformAPIHandler

Copyright PolyAI Limited
"""

import json
import os
import unittest
from unittest.mock import patch

import requests

from poly.handlers.platform_api import (
    ACCOUNTS_URL,
    FunctionConflictError,
    PlatformAPIHandler,
)
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


class CreateChat(unittest.TestCase):
    """Tests for chat creation request payloads."""

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_standard_chat_includes_sip_headers(self, mock_make_request):
        sip_headers = {"X-Customer-ID": "12345"}

        PlatformAPIHandler.create_chat(
            "uk-1",
            "ACCOUNT-123",
            "PROJECT-123",
            sip_headers=sip_headers,
        )

        self.assertEqual(mock_make_request.call_args.kwargs["data"]["sip_headers"], sip_headers)

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_draft_chat_includes_sip_headers(self, mock_make_request):
        sip_headers = {"X-Customer-ID": "12345"}

        PlatformAPIHandler.create_draft_chat(
            "uk-1",
            "ACCOUNT-123",
            "PROJECT-123",
            "artifact-version",
            "lambda-version",
            sip_headers=sip_headers,
        )

        self.assertEqual(mock_make_request.call_args.kwargs["data"]["sip_headers"], sip_headers)


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


class ListAudioCache(unittest.TestCase):
    """Tests for PlatformAPIHandler.list_audio_cache."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_limit_offset_and_sort_params(self, mock_request, _mock_key):
        """limit/offset/sort are forwarded as query params when provided."""
        mock_request.return_value = make_mock_response(
            200, json_body={"entries": [], "total_count": 0}
        )

        PlatformAPIHandler.list_audio_cache(
            "studio", "agent-1", limit=20, offset=5, sort="hit_count:desc"
        )

        params = mock_request.call_args.kwargs["params"]
        self.assertEqual(params, {"limit": 20, "offset": 5, "sort": "hit_count:desc"})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_omits_sort_when_not_provided(self, mock_request, _mock_key):
        """sort is left out of the query params entirely when None."""
        mock_request.return_value = make_mock_response(
            200, json_body={"entries": [], "total_count": 0}
        )

        PlatformAPIHandler.list_audio_cache("studio", "agent-1")

        params = mock_request.call_args.kwargs["params"]
        self.assertNotIn("sort", params)


class GetAudioCacheFile(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_audio_cache_file."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.get")
    def test_returns_raw_audio_bytes(self, mock_get, _mock_key):
        """The raw response content is returned as bytes."""
        mock_get.return_value = make_mock_response(200, content=b"RIFF-audio-data")

        audio = PlatformAPIHandler.get_audio_cache_file("studio", "agent-1", "entry-1")

        self.assertEqual(audio, b"RIFF-audio-data")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.get")
    def test_error_status_raises_http_error(self, mock_get, _mock_key):
        """A failing file request propagates as requests.HTTPError."""
        mock_get.return_value = make_mock_response(404, content=b"not found")

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.get_audio_cache_file("studio", "agent-1", "entry-1")


class UpdateAudioCacheFile(unittest.TestCase):
    """Tests for PlatformAPIHandler.update_audio_cache_file."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_raw_bytes_with_wav_content_type(self, mock_request, _mock_key):
        """The raw audio bytes are sent as the body with a WAV content type."""
        mock_request.return_value = make_mock_response(204)

        PlatformAPIHandler.update_audio_cache_file(
            "studio", "agent-1", "entry-1", b"RIFF-new-audio", filename="clip.wav"
        )

        call = mock_request.call_args
        self.assertEqual(call.kwargs["method"], "PATCH")
        self.assertEqual(call.kwargs["data"], b"RIFF-new-audio")
        self.assertEqual(call.kwargs["headers"]["Content-Type"], "audio/wav")
        self.assertEqual(call.kwargs["headers"]["X-Filename"], "clip.wav")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_omits_filename_header_when_not_provided(self, mock_request, _mock_key):
        """X-Filename is left out of headers entirely when no filename is given."""
        mock_request.return_value = make_mock_response(204)

        PlatformAPIHandler.update_audio_cache_file("studio", "agent-1", "entry-1", b"data")

        self.assertNotIn("X-Filename", mock_request.call_args.kwargs["headers"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_error_status_raises_http_error(self, mock_request, _mock_key):
        """A failing update propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(400, json_body={"error": "too big"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.update_audio_cache_file("studio", "agent-1", "entry-1", b"data")


class UpdateAudioCacheDetails(unittest.TestCase):
    """Tests for PlatformAPIHandler.update_audio_cache_details."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_multipart_file_and_settings(self, mock_request, _mock_key):
        """The audio bytes and JSON-encoded settings are sent as multipart form data."""
        mock_request.return_value = make_mock_response(204)

        PlatformAPIHandler.update_audio_cache_details(
            "studio",
            "agent-1",
            "entry-1",
            b"RIFF-new-audio",
            {"text": "hello", "config": {"stability": 0.5}},
            filename="clip.wav",
        )

        call = mock_request.call_args
        self.assertEqual(call.kwargs["method"], "PUT")
        self.assertEqual(call.kwargs["files"]["file"][0], "clip.wav")
        self.assertEqual(call.kwargs["files"]["file"][1], b"RIFF-new-audio")
        sent_settings = json.loads(call.kwargs["data"]["settings"])
        self.assertEqual(sent_settings, {"text": "hello", "config": {"stability": 0.5}})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_error_status_raises_http_error(self, mock_request, _mock_key):
        """A failing update propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(400, json_body={"error": "bad settings"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.update_audio_cache_details(
                "studio", "agent-1", "entry-1", b"data", {"text": "hi", "config": {}}
            )


class DeleteAudioCacheEntry(unittest.TestCase):
    """Tests for PlatformAPIHandler.delete_audio_cache_entry."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_delete_to_entry_endpoint(self, mock_request, _mock_key):
        """DELETE is sent to the entry-specific endpoint."""
        mock_request.return_value = make_mock_response(200, json_body={"success": True})

        result = PlatformAPIHandler.delete_audio_cache_entry("studio", "agent-1", "entry-1")

        self.assertEqual(mock_request.call_args.kwargs["method"], "DELETE")
        self.assertIn("/agents/agent-1/audio-cache/entry-1", mock_request.call_args.kwargs["url"])
        self.assertEqual(result, {"success": True})


class BulkDeleteAudioCache(unittest.TestCase):
    """Tests for PlatformAPIHandler.bulk_delete_audio_cache."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_ids_in_body(self, mock_request, _mock_key):
        """The list of IDs is JSON-encoded into the request body."""
        mock_request.return_value = make_mock_response(
            200, json_body={"deleted": ["1", "2"], "failed": []}
        )

        result = PlatformAPIHandler.bulk_delete_audio_cache("studio", "agent-1", ["1", "2"])

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(sent, {"ids": ["1", "2"]})
        self.assertEqual(result, {"deleted": ["1", "2"], "failed": []})


class SynthesizeAudioCache(unittest.TestCase):
    """Tests for PlatformAPIHandler.synthesize_audio_cache."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_returns_raw_audio_bytes(self, mock_request, _mock_key):
        """The raw response content is returned as bytes."""
        mock_request.return_value = make_mock_response(200, content=b"RIFF-preview-audio")

        audio = PlatformAPIHandler.synthesize_audio_cache(
            "studio", "agent-1", "entry-1", "hello there", {"stability": 0.5}
        )

        self.assertEqual(audio, b"RIFF-preview-audio")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_includes_language_when_provided(self, mock_request, _mock_key):
        """language is included in the JSON body only when provided."""
        mock_request.return_value = make_mock_response(200, content=b"audio")

        PlatformAPIHandler.synthesize_audio_cache(
            "studio", "agent-1", "entry-1", "hi", {}, language="en-US"
        )

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(sent["language"], "en-US")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_error_status_raises_http_error(self, mock_request, _mock_key):
        """A failing synthesis request propagates as requests.HTTPError."""
        mock_request.return_value = make_mock_response(422, json_body={"error": "bad text"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.synthesize_audio_cache("studio", "agent-1", "entry-1", "hi", {})


SAMPLE_FUNCTION = {
    "function_id": "fn-1",
    "name": "my_func",
    "description": "desc",
    "parameters": [{"name": "x", "type": "string", "description": "an x"}],
    "code": "def my_func(conv, x: str):\n    pass\n",
    "active": True,
    "usage_count": 2,
}


class ListFunctions(unittest.TestCase):
    """Tests for PlatformAPIHandler.list_functions."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_calls_branch_scoped_endpoint(self, mock_request, _mock_key):
        """The request is a GET against the branch-scoped functions endpoint."""
        mock_request.return_value = make_mock_response(
            200, json_body={"functions": [SAMPLE_FUNCTION]}
        )

        result = PlatformAPIHandler.list_functions("studio", "agent-1", "branch-1")

        self.assertEqual(result, {"functions": [SAMPLE_FUNCTION]})
        self.assertEqual(mock_request.call_args.kwargs["method"], "GET")
        self.assertIn(
            "/v1/agents/agent-1/branches/branch-1/functions",
            mock_request.call_args.kwargs["url"],
        )

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_passes_pagination_params(self, mock_request, _mock_key):
        """limit and offset are sent as query parameters."""
        mock_request.return_value = make_mock_response(200, json_body={"functions": []})

        PlatformAPIHandler.list_functions("studio", "agent-1", "branch-1", limit=50, offset=10)

        self.assertEqual(mock_request.call_args.kwargs["params"], {"limit": 50, "offset": 10})


class GetFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_returns_function_payload(self, mock_request, _mock_key):
        """The function payload is returned unchanged."""
        mock_request.return_value = make_mock_response(200, json_body=SAMPLE_FUNCTION)

        result = PlatformAPIHandler.get_function("studio", "agent-1", "branch-1", "fn-1")

        self.assertEqual(result, SAMPLE_FUNCTION)
        self.assertIn(
            "/v1/agents/agent-1/branches/branch-1/functions/fn-1",
            mock_request.call_args.kwargs["url"],
        )


class CreateFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.create_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_posts_function_body(self, mock_request, _mock_key):
        """name, description, code and parameters are sent in the body."""
        mock_request.return_value = make_mock_response(201, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.create_function(
            "studio", "agent-1", "branch-1", "my_func", "desc", "code", parameters=[{"name": "x"}]
        )

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(mock_request.call_args.kwargs["method"], "POST")
        self.assertEqual(
            sent,
            {
                "name": "my_func",
                "description": "desc",
                "code": "code",
                "parameters": [{"name": "x"}],
            },
        )

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_omits_delay_control_when_not_given(self, mock_request, _mock_key):
        """delay_control is only sent when provided."""
        mock_request.return_value = make_mock_response(201, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.create_function("studio", "agent-1", "branch-1", "f", "d", "code")

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertNotIn("delay_control", sent)

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_name_collision_raises_conflict(self, mock_request, _mock_key):
        """A 409 name collision is translated into FunctionConflictError."""
        mock_request.return_value = make_mock_response(
            409, json_body={"message": "Name already exists", "orphaned_references": []}
        )

        with self.assertRaises(FunctionConflictError) as ctx:
            PlatformAPIHandler.create_function("studio", "agent-1", "branch-1", "dup", "d", "code")

        self.assertEqual(str(ctx.exception), "Name already exists")
        self.assertEqual(ctx.exception.orphaned_references, [])


class UpdateFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.update_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_patches_only_supplied_updates(self, mock_request, _mock_key):
        """Only the supplied fields are sent, and force is omitted by default."""
        mock_request.return_value = make_mock_response(200, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.update_function(
            "studio", "agent-1", "branch-1", "fn-1", {"description": "new"}
        )

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(mock_request.call_args.kwargs["method"], "PATCH")
        self.assertEqual(sent, {"description": "new"})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_force_is_sent_in_body(self, mock_request, _mock_key):
        """force=True is added to the request body."""
        mock_request.return_value = make_mock_response(200, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.update_function(
            "studio", "agent-1", "branch-1", "fn-1", {"name": "renamed"}, force=True
        )

        sent = json.loads(mock_request.call_args.kwargs["data"])
        self.assertEqual(sent, {"name": "renamed", "force": True})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_orphaned_reference_conflict_carries_references(self, mock_request, _mock_key):
        """A 409 exposes the orphaned flow-step references to the caller."""
        references = [{"flow_id": "flow-1", "flow_name": "Main", "step_name": "step-1"}]
        mock_request.return_value = make_mock_response(
            409, json_body={"message": "Orphaned references", "orphaned_references": references}
        )

        with self.assertRaises(FunctionConflictError) as ctx:
            PlatformAPIHandler.update_function(
                "studio", "agent-1", "branch-1", "fn-1", {"name": "renamed"}
            )

        self.assertEqual(ctx.exception.orphaned_references, references)

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_conflict_without_json_body_still_raises(self, mock_request, _mock_key):
        """A 409 with an unparseable body falls back to a generic conflict message."""
        mock_request.return_value = make_mock_response(409)

        with self.assertRaises(FunctionConflictError) as ctx:
            PlatformAPIHandler.update_function(
                "studio", "agent-1", "branch-1", "fn-1", {"name": "renamed"}
            )

        self.assertEqual(str(ctx.exception), "Conflict")
        self.assertEqual(ctx.exception.orphaned_references, [])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_non_conflict_error_propagates_as_http_error(self, mock_request, _mock_key):
        """Non-409 failures are left as requests.HTTPError."""
        mock_request.return_value = make_mock_response(500, json_body={"error": "boom"})

        with self.assertRaises(requests.HTTPError):
            PlatformAPIHandler.update_function(
                "studio", "agent-1", "branch-1", "fn-1", {"name": "renamed"}
            )


class DeleteFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.delete_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_empty_204_body_returns_empty_dict(self, mock_request, _mock_key):
        """A 204 No Content delete does not raise a JSON decode error."""
        mock_request.return_value = make_mock_response(204)

        result = PlatformAPIHandler.delete_function("studio", "agent-1", "branch-1", "fn-1")

        self.assertEqual(result, {})
        self.assertEqual(mock_request.call_args.kwargs["method"], "DELETE")

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_omits_body_when_force_not_given(self, mock_request, _mock_key):
        """Without force=True, no body is sent (matching other DELETE calls)."""
        mock_request.return_value = make_mock_response(204)

        PlatformAPIHandler.delete_function("studio", "agent-1", "branch-1", "fn-1")

        self.assertIsNone(mock_request.call_args.kwargs["data"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_force_flag(self, mock_request, _mock_key):
        """force=True is sent in the delete body."""
        mock_request.return_value = make_mock_response(204)

        PlatformAPIHandler.delete_function("studio", "agent-1", "branch-1", "fn-1", force=True)

        self.assertEqual(json.loads(mock_request.call_args.kwargs["data"]), {"force": True})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_conflict_raises_function_conflict_error(self, mock_request, _mock_key):
        """Deleting a referenced function without --force raises a conflict."""
        references = [{"flow_id": "flow-1", "flow_name": "Main", "step_name": "step-1"}]
        mock_request.return_value = make_mock_response(
            409, json_body={"message": "Still referenced", "orphaned_references": references}
        )

        with self.assertRaises(FunctionConflictError) as ctx:
            PlatformAPIHandler.delete_function("studio", "agent-1", "branch-1", "fn-1")

        self.assertEqual(ctx.exception.orphaned_references, references)


class ExecuteFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.execute_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_wraps_args_in_body_and_returns_result(self, mock_request, _mock_key):
        """Arguments are wrapped in an "args" object and the result is returned."""
        payload = {"body": {"ok": True}, "logs": ["line"], "runtime": 12}
        mock_request.return_value = make_mock_response(200, json_body=payload)

        result = PlatformAPIHandler.execute_function(
            "studio", "agent-1", "branch-1", "fn-1", {"x": 1}
        )

        self.assertEqual(result, payload)
        self.assertEqual(json.loads(mock_request.call_args.kwargs["data"]), {"args": {"x": 1}})
        self.assertIn("/functions/fn-1/execute", mock_request.call_args.kwargs["url"])


class DuplicateFunction(unittest.TestCase):
    """Tests for PlatformAPIHandler.duplicate_function."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_omits_body_when_no_name_given(self, mock_request, _mock_key):
        """Without an explicit name the server generates one, so no body is sent."""
        mock_request.return_value = make_mock_response(201, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.duplicate_function("studio", "agent-1", "branch-1", "fn-1")

        self.assertIsNone(mock_request.call_args.kwargs["data"])
        self.assertIn("/functions/fn-1/duplicate", mock_request.call_args.kwargs["url"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_name_collision_raises_conflict(self, mock_request, _mock_key):
        """A 409 on an explicit-name collision is translated, not left as an HTTPError."""
        mock_request.return_value = make_mock_response(
            409, json_body={"message": "Name already exists", "orphaned_references": []}
        )

        with self.assertRaises(FunctionConflictError):
            PlatformAPIHandler.duplicate_function(
                "studio", "agent-1", "branch-1", "fn-1", name="taken"
            )

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_body_for_explicit_empty_name(self, mock_request, _mock_key):
        """An explicit empty-string name is distinct from omitting the argument."""
        mock_request.return_value = make_mock_response(201, json_body=SAMPLE_FUNCTION)

        PlatformAPIHandler.duplicate_function("studio", "agent-1", "branch-1", "fn-1", name="")

        self.assertEqual(json.loads(mock_request.call_args.kwargs["data"]), {"name": ""})


class DeployAndValidateFunctions(unittest.TestCase):
    """Tests for the functions deploy/validate/deployments endpoints."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_deploy_posts_to_deploy_endpoint(self, mock_request, _mock_key):
        """Deploy is a POST returning the new deployment record."""
        payload = {"deployment_version": "v3", "function_ids": ["fn-1"], "deployed_at": "now"}
        mock_request.return_value = make_mock_response(200, json_body=payload)

        result = PlatformAPIHandler.deploy_functions("studio", "agent-1", "branch-1")

        self.assertEqual(result, payload)
        self.assertEqual(mock_request.call_args.kwargs["method"], "POST")
        self.assertIn("/functions/deploy", mock_request.call_args.kwargs["url"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_validate_returns_valid_and_issues(self, mock_request, _mock_key):
        """Validate returns the raw {"valid": ..., "issues": [...]} payload."""
        payload = {"valid": False, "issues": [{"type": "syntax_error", "function_id": "fn-1"}]}
        mock_request.return_value = make_mock_response(200, json_body=payload)

        result = PlatformAPIHandler.validate_functions("studio", "agent-1", "branch-1")

        self.assertEqual(result, payload)
        self.assertIn("/functions/validate", mock_request.call_args.kwargs["url"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_list_deployments_uses_deployments_endpoint(self, mock_request, _mock_key):
        """Deployment history is a GET against the deployments endpoint."""
        mock_request.return_value = make_mock_response(200, json_body={"deployments": []})

        PlatformAPIHandler.list_function_deployments("studio", "agent-1", "branch-1")

        self.assertEqual(mock_request.call_args.kwargs["method"], "GET")
        self.assertIn("/functions/deployments", mock_request.call_args.kwargs["url"])


class FunctionReferencesAndTypeDefinitions(unittest.TestCase):
    """Tests for the function references and type-definitions endpoints."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_references_endpoint(self, mock_request, _mock_key):
        """References are fetched from the per-function references endpoint."""
        mock_request.return_value = make_mock_response(200, json_body={"references": []})

        PlatformAPIHandler.get_function_references("studio", "agent-1", "branch-1", "fn-1")

        self.assertIn("/functions/fn-1/references", mock_request.call_args.kwargs["url"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_type_definitions_endpoint(self, mock_request, _mock_key):
        """Type stubs are fetched from the per-function type_definitions endpoint."""
        mock_request.return_value = make_mock_response(200, json_body={"code": "class Conv: ..."})

        result = PlatformAPIHandler.get_function_type_definitions(
            "studio", "agent-1", "branch-1", "fn-1"
        )

        self.assertEqual(result, {"code": "class Conv: ..."})
        self.assertIn("/functions/fn-1/type_definitions", mock_request.call_args.kwargs["url"])


class StartAndEndFunctions(unittest.TestCase):
    """Tests for the branch start_function/end_function endpoints."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_get_start_function(self, mock_request, _mock_key):
        """start_function is fetched with a GET."""
        mock_request.return_value = make_mock_response(
            200, json_body={"code": "pass", "version": "1"}
        )

        result = PlatformAPIHandler.get_start_function("studio", "agent-1", "branch-1")

        self.assertEqual(result["code"], "pass")
        self.assertEqual(mock_request.call_args.kwargs["method"], "GET")
        self.assertIn("/functions/start", mock_request.call_args.kwargs["url"])

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_update_start_function_puts_code(self, mock_request, _mock_key):
        """start_function is replaced with a PUT carrying the new code."""
        mock_request.return_value = make_mock_response(200, json_body={"code": "new"})

        PlatformAPIHandler.update_start_function("studio", "agent-1", "branch-1", "new")

        self.assertEqual(mock_request.call_args.kwargs["method"], "PUT")
        self.assertEqual(json.loads(mock_request.call_args.kwargs["data"]), {"code": "new"})

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_update_end_function_puts_code(self, mock_request, _mock_key):
        """end_function is replaced with a PUT against the end endpoint."""
        mock_request.return_value = make_mock_response(200, json_body={"code": "new"})

        PlatformAPIHandler.update_end_function("studio", "agent-1", "branch-1", "new")

        self.assertEqual(mock_request.call_args.kwargs["method"], "PUT")
        self.assertIn("/functions/end", mock_request.call_args.kwargs["url"])


def _make_request_headers() -> dict:
    """Call make_request with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.request") as mock_request,
    ):
        mock_request.return_value = make_mock_response(200, json_body={})
        PlatformAPIHandler.make_request("studio", "/adk/v1/accounts")
        return mock_request.call_args.kwargs["headers"]


def _get_conversation_audio_headers() -> dict:
    """Call get_conversation_audio with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.get") as mock_get,
    ):
        mock_get.return_value = make_mock_response(200, content=b"audio")
        PlatformAPIHandler.get_conversation_audio("studio", "agent-1", "conv-1")
        return mock_get.call_args.kwargs["headers"]


def _get_audio_cache_file_headers() -> dict:
    """Call get_audio_cache_file with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.get") as mock_get,
    ):
        mock_get.return_value = make_mock_response(200, content=b"audio")
        PlatformAPIHandler.get_audio_cache_file("studio", "agent-1", "entry-1")
        return mock_get.call_args.kwargs["headers"]


def _update_audio_cache_file_headers() -> dict:
    """Call update_audio_cache_file with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.request") as mock_request,
    ):
        mock_request.return_value = make_mock_response(204)
        PlatformAPIHandler.update_audio_cache_file("studio", "agent-1", "entry-1", b"audio")
        return mock_request.call_args.kwargs["headers"]


def _update_audio_cache_details_headers() -> dict:
    """Call update_audio_cache_details with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.request") as mock_request,
    ):
        mock_request.return_value = make_mock_response(204)
        PlatformAPIHandler.update_audio_cache_details(
            "studio", "agent-1", "entry-1", b"audio", {"text": "hi", "config": {}}
        )
        return mock_request.call_args.kwargs["headers"]


def _synthesize_audio_cache_headers() -> dict:
    """Call synthesize_audio_cache with the network mocked and return the headers it sent."""
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key"),
        patch("poly.handlers.platform_api.requests.request") as mock_request,
    ):
        mock_request.return_value = make_mock_response(200, content=b"audio")
        PlatformAPIHandler.synthesize_audio_cache("studio", "agent-1", "entry-1", "hi", {})
        return mock_request.call_args.kwargs["headers"]


# Every handler method that builds its own request headers, mapped to a helper that
# invokes it against a mocked transport and hands back the headers it tried to send.
HEADER_BUILDING_METHODS = {
    "make_request": _make_request_headers,
    "get_conversation_audio": _get_conversation_audio_headers,
    "get_audio_cache_file": _get_audio_cache_file_headers,
    "update_audio_cache_file": _update_audio_cache_file_headers,
    "update_audio_cache_details": _update_audio_cache_details_headers,
    "synthesize_audio_cache": _synthesize_audio_cache_headers,
}


class UserEmailHeader(unittest.TestCase):
    """Tests that ADK_COMMAND_USER_OVERRIDE is forwarded as the X-PolyAI-Email header."""

    def test_override_email_is_sent_by_every_request(self):
        """Every method that builds headers attributes the request to the override email."""
        for method_name, send_request in HEADER_BUILDING_METHODS.items():
            with (
                self.subTest(method=method_name),
                patch.dict(os.environ, {"ADK_COMMAND_USER_OVERRIDE": "dev@poly.ai"}),
            ):
                self.assertEqual(send_request()["X-PolyAI-Email"], "dev@poly.ai")

    def test_email_header_omitted_when_override_unset(self):
        """With no override set, no method sends an X-PolyAI-Email header at all."""
        for method_name, send_request in HEADER_BUILDING_METHODS.items():
            with (
                self.subTest(method=method_name),
                patch.dict(os.environ, {}, clear=True),
            ):
                self.assertNotIn("X-PolyAI-Email", send_request())


if __name__ == "__main__":
    unittest.main()
