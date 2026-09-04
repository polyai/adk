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

class GetCustomMetrics(unittest.TestCase):
    """Tests for PlatformAPIHandler.get_custom_metrics."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_returns_list_directly(self, mock_request, _mock_key):
        """When the API returns a bare list, it is returned as-is."""
        metrics = [{"name": "SCORE", "type": "int"}]
        mock_request.return_value = make_mock_response(200, json_body=metrics)

        result = PlatformAPIHandler.get_custom_metrics("studio", "acc1", "proj1")

        self.assertEqual(result, metrics)

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_extracts_from_metrics_key(self, mock_request, _mock_key):
        """When the API wraps the list in a 'metrics' key, it is unwrapped."""
        metrics = [{"name": "SCORE", "type": "int"}]
        mock_request.return_value = make_mock_response(200, json_body={"metrics": metrics})

        result = PlatformAPIHandler.get_custom_metrics("studio", "acc1", "proj1")

        self.assertEqual(result, metrics)


class CreateCustomMetric(unittest.TestCase):
    """Tests for PlatformAPIHandler.create_custom_metric."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_posts_data_to_correct_endpoint(self, mock_request, _mock_key):
        """create_custom_metric sends a POST with the metric payload."""
        mock_request.return_value = make_mock_response(200, json_body={"name": "SCORE"})

        data = {"name": "SCORE", "type": "int"}
        PlatformAPIHandler.create_custom_metric("studio", "acc1", "proj1", data)

        call_kwargs = mock_request.call_args
        self.assertEqual(call_kwargs.kwargs["method"], "POST")
        self.assertIn("/custom-metrics", call_kwargs.kwargs["url"])


class UpdateCustomMetric(unittest.TestCase):
    """Tests for PlatformAPIHandler.update_custom_metric."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_patches_correct_metric(self, mock_request, _mock_key):
        """update_custom_metric sends a PATCH to the metric-specific URL."""
        mock_request.return_value = make_mock_response(200, json_body={"name": "SCORE"})

        PlatformAPIHandler.update_custom_metric("studio", "acc1", "proj1", "SCORE", {"api": True})

        call_kwargs = mock_request.call_args
        self.assertEqual(call_kwargs.kwargs["method"], "PATCH")
        self.assertIn("/custom-metrics/SCORE", call_kwargs.kwargs["url"])


class ExportCustomMetrics(unittest.TestCase):
    """Tests for PlatformAPIHandler.export_custom_metrics."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_requests_yaml_format(self, mock_request, _mock_key):
        """export_custom_metrics hits the export endpoint with a GET."""
        yaml_body = b"SCORE:\n  type: int\n"
        mock_request.return_value = make_mock_response(200, content=yaml_body)

        PlatformAPIHandler.export_custom_metrics("studio", "acc1", "proj1")

        call_kwargs = mock_request.call_args
        self.assertEqual(call_kwargs.kwargs["method"], "GET")
        self.assertIn("/export", call_kwargs.kwargs["url"])


class ImportCustomMetrics(unittest.TestCase):
    """Tests for PlatformAPIHandler.import_custom_metrics."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_sends_multipart_upload(self, mock_request, _mock_key):
        """import_custom_metrics POSTs a multipart file upload."""
        mock_request.return_value = make_mock_response(
            200, json_body={"metadata": {"created": [], "ignored": []}}
        )

        PlatformAPIHandler.import_custom_metrics("studio", "acc1", "proj1", "SCORE:\n  type: int\n")

        call_kwargs = mock_request.call_args
        self.assertIn("/import", call_kwargs.kwargs["url"])
        self.assertIn("yaml", call_kwargs.kwargs.get("files", {}))


class PreviewMetricsImport(unittest.TestCase):
    """Tests for PlatformAPIHandler.preview_metrics_import."""

    @patch.object(PlatformAPIHandler, "get_custom_metrics")
    def test_computes_set_diff(self, mock_get):
        """Correctly partitions local vs remote metric names."""
        mock_get.return_value = [{"name": "EXISTING"}, {"name": "REMOTE_ONLY"}]

        result = PlatformAPIHandler.preview_metrics_import(
            "studio", "acc1", "proj1", {"EXISTING", "NEW_ONE"}
        )

        self.assertEqual(result["would_create"], ["NEW_ONE"])
        self.assertEqual(result["would_skip"], ["EXISTING"])
        self.assertEqual(result["remote_only"], ["REMOTE_ONLY"])

class ListFunctions(unittest.TestCase):
    """Tests for PlatformAPIHandler.list_functions."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_returns_the_raw_function_list(self, mock_request, _mock_key):
        """The endpoint returns a bare array, not a {"functions": [...]} wrapper."""
        payload = [{"id": "fn-1", "name": "my_func"}]
        mock_request.return_value = make_mock_response(200, json_body=payload)

        result = PlatformAPIHandler.list_functions("studio", "agent-1", "branch-1")

        self.assertEqual(result, payload)
        self.assertEqual(mock_request.call_args.kwargs["method"], "GET")
        url = mock_request.call_args.kwargs["url"]
        self.assertIn("/agents/agent-1/branches/branch-1/functions", url)


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


class ValidateFunctions(unittest.TestCase):
    """Tests for the functions validate endpoint."""

    @patch("poly.handlers.platform_api.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.platform_api.requests.request")
    def test_validate_returns_valid_and_issues(self, mock_request, _mock_key):
        """Validate returns the raw {"valid": ..., "issues": [...]} payload."""
        payload = {"valid": False, "issues": [{"type": "syntax_error", "function_id": "fn-1"}]}
        mock_request.return_value = make_mock_response(200, json_body=payload)

        result = PlatformAPIHandler.validate_functions("studio", "agent-1", "branch-1")

        self.assertEqual(result, payload)
        self.assertIn("/functions/validate", mock_request.call_args.kwargs["url"])


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
