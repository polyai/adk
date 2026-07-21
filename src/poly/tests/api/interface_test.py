"""Tests for the AgentStudioInterface

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.handlers.interface import AgentStudioInterface
from poly.handlers.sdk import SourcererAPIError
from poly.tests.testing_utils import make_mock_response


def _http_error_with_code(error_code):
    """Build a requests.HTTPError whose response body carries an error_code."""
    response = make_mock_response(403, json_body={"error_code": error_code})
    return requests.HTTPError("failed", response=response)


class ExtractErrorCode(unittest.TestCase):
    """Tests for AgentStudioInterface._extract_error_code."""

    def test_code_read_from_response_on_exception(self):
        """The error_code is read from the exception's own response body."""
        error = _http_error_with_code("FORBIDDEN")

        self.assertEqual(AgentStudioInterface._extract_error_code(error), "FORBIDDEN")

    def test_code_read_from_cause_response(self):
        """The error_code is read from the response on the chained __cause__."""
        cause = _http_error_with_code("DEPLOYMENT_NOT_FOUND")
        wrapper = SourcererAPIError("wrapped")
        wrapper.__cause__ = cause

        self.assertEqual(AgentStudioInterface._extract_error_code(wrapper), "DEPLOYMENT_NOT_FOUND")

    def test_missing_response_returns_none(self):
        """An exception with no response and no cause yields None."""
        self.assertIsNone(AgentStudioInterface._extract_error_code(ValueError("plain")))

    def test_malformed_json_body_returns_none(self):
        """A response whose body is not valid JSON yields None."""
        response = make_mock_response(500, json_body=None, content=b"<html>")
        error = requests.HTTPError("failed", response=response)

        self.assertIsNone(AgentStudioInterface._extract_error_code(error))


class HandleApiError(unittest.TestCase):
    """Tests for AgentStudioInterface._handle_api_error message mapping."""

    def setUp(self):
        self.interface = AgentStudioInterface()
        self.interface.project_id = "proj-1"
        self.interface.account_id = "acc-1"

    def test_forbidden_gives_permission_message(self):
        """A FORBIDDEN error code maps to a permission-denied message."""
        error = _http_error_with_code("FORBIDDEN")

        with self.assertRaises(ValueError) as ctx:
            self.interface._handle_api_error(error)

        self.assertIn("Forbidden", str(ctx.exception))
        self.assertIn("proj-1", str(ctx.exception))

    def test_deployment_not_found_gives_not_found_message(self):
        """A DEPLOYMENT_NOT_FOUND error code maps to a project-not-found message."""
        error = _http_error_with_code("DEPLOYMENT_NOT_FOUND")

        with self.assertRaises(ValueError) as ctx:
            self.interface._handle_api_error(error)

        self.assertIn("not found", str(ctx.exception))
        self.assertIn("proj-1", str(ctx.exception))

    def test_unknown_code_gives_generic_message(self):
        """An unrecognised error code falls back to a generic API error message."""
        error = _http_error_with_code("SOMETHING_ELSE")

        with self.assertRaises(ValueError) as ctx:
            self.interface._handle_api_error(error)

        self.assertIn("API error", str(ctx.exception))


class WrapperErrorTranslation(unittest.TestCase):
    """Tests that interface wrappers translate API errors into ValueError."""

    def setUp(self):
        self.interface = AgentStudioInterface()
        self.interface.sync_client = MagicMock()

    def test_pull_resources_translates_http_error(self):
        """pull_resources converts a requests.HTTPError into a ValueError."""
        self.interface.sync_client.pull_resources.side_effect = requests.HTTPError("boom")

        with self.assertRaises(ValueError):
            self.interface.pull_resources()

    def test_pull_resources_translates_sourcerer_error(self):
        """pull_resources converts a SourcererAPIError into a ValueError."""
        self.interface.sync_client.pull_resources.side_effect = SourcererAPIError("boom")

        with self.assertRaises(ValueError):
            self.interface.pull_resources()

    def test_queue_command_translates_sourcerer_error(self):
        """queue_command converts a SourcererAPIError into a ValueError."""
        self.interface.sync_client.queue_command.side_effect = SourcererAPIError("boom")

        with self.assertRaises(ValueError):
            self.interface.queue_command(MagicMock())


class PullResourcesWithProjection(unittest.TestCase):
    """Tests for pull_resources when a projection is supplied directly."""

    @patch("poly.handlers.interface.SyncClientHandler.load_resources_from_projection")
    def test_projection_json_skips_api_and_uses_loader(self, mock_loader):
        """Passing projection_json bypasses the sync client and loads locally."""
        interface = AgentStudioInterface()
        interface.sync_client = MagicMock()
        mock_loader.return_value = {"loaded": "resources"}
        projection = {"knowledgeBase": {}}

        resources, returned_projection = interface.pull_resources(projection_json=projection)

        self.assertEqual(resources, {"loaded": "resources"})
        self.assertIs(returned_projection, projection)
        mock_loader.assert_called_once_with(projection)
        interface.sync_client.pull_resources.assert_not_called()


if __name__ == "__main__":
    unittest.main()
