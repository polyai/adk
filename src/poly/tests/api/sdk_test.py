"""Tests for the SourcererSDK

Copyright PolyAI Limited
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from poly.handlers.protobuf.commands_pb2 import Command, CommandBatch
from poly.handlers.sdk import SourcererAPIError, SourcererSDK
from poly.tests.testing_utils import make_mock_response


def build_sdk(branch_id="branch-1"):
    """Build an SDK with an explicit base_url and branch to avoid network on init."""
    return SourcererSDK(
        region="studio",
        account_id="acc-1",
        project_id="proj-1",
        branch_id=branch_id,
        base_url="https://sourcerer.test",
    )


class Init(unittest.TestCase):
    """Tests for SourcererSDK construction."""

    def test_unknown_region_without_base_url_raises(self):
        """An unknown region with no explicit base_url raises ValueError."""
        with self.assertRaises(ValueError):
            SourcererSDK(
                region="mars-1",
                account_id="acc-1",
                project_id="proj-1",
                branch_id="branch-1",
            )

    def test_command_user_override_sets_email(self):
        """The ADK_COMMAND_USER_OVERRIDE env var populates the email field."""
        with patch.dict(os.environ, {"ADK_COMMAND_USER_OVERRIDE": "dev@poly.ai"}):
            sdk = build_sdk()

        self.assertEqual(sdk.email, "dev@poly.ai")


class FetchProjection(unittest.TestCase):
    """Tests for SourcererSDK.fetch_projection caching and errors."""

    def test_fetches_and_caches_projection_and_sequence(self):
        """A successful fetch caches the projection body and last known sequence."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {"topics": {}}, "lastKnownSequence": "42"}
        )
        sdk._session = session

        projection = sdk.fetch_projection()

        self.assertEqual(projection, {"topics": {}})
        self.assertEqual(sdk._last_known_sequence, 42)
        expected_url = (
            "https://sourcerer.test/accounts/acc-1/projects/proj-1/branches/branch-1/projection"
        )
        session.get.assert_called_once_with(expected_url, params=None)

    def test_cached_projection_returned_without_refetch(self):
        """A second call returns the cache without hitting the session again."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {"a": 1}, "lastKnownSequence": "1"}
        )
        sdk._session = session

        sdk.fetch_projection()
        sdk.fetch_projection()

        session.get.assert_called_once()

    def test_force_refresh_bypasses_cache(self):
        """force_refresh re-fetches even when a cached projection exists."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {"a": 1}, "lastKnownSequence": "1"}
        )
        sdk._session = session

        sdk.fetch_projection()
        sdk.fetch_projection(force_refresh=True)

        self.assertEqual(session.get.call_count, 2)

    def test_include_api_mocks_sends_api_mock_editor_param(self):
        """include_api_mocks=True asks the platform for test case api_mocks."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {}, "lastKnownSequence": "1"}
        )
        sdk._session = session

        sdk.fetch_projection(include_api_mocks=True)

        self.assertEqual(session.get.call_args.kwargs["params"], {"apiMockEditor": True})

    def test_api_mock_editor_param_omitted_when_api_mocks_not_requested(self):
        """The apiMockEditor param is left off entirely rather than sent as False."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {}, "lastKnownSequence": "1"}
        )
        sdk._session = session

        sdk.fetch_projection(at_sequence=7, include_api_mocks=False)

        self.assertEqual(session.get.call_args.kwargs["params"], {"atSequence": 7})

    def test_request_failure_raises_sourcerer_error(self):
        """A failing projection request raises SourcererAPIError."""
        sdk = build_sdk()
        session = MagicMock()
        session.get.return_value = make_mock_response(500, json_body={"error": "boom"})
        sdk._session = session

        with self.assertRaises(SourcererAPIError):
            sdk.fetch_projection()


class CreateBranch(unittest.TestCase):
    """Tests for the payload SourcererSDK.create_branch posts."""

    def setUp(self):
        self.sdk = build_sdk()
        self.session = MagicMock()
        self.session.post.return_value = make_mock_response(
            200, json_body={"branchId": "new-branch-id"}
        )
        self.sdk._session = self.session

    def _posted_payload(self):
        """The JSON body sent to the branches endpoint."""
        return self.session.post.call_args.kwargs["json"]

    def test_returns_new_branch_id_from_response(self):
        """The branchId from the API response is returned."""
        branch_id = self.sdk.create_branch(branch_name="my-feature")

        self.assertEqual(branch_id, "new-branch-id")

    def test_payload_carries_branch_name_and_expected_sequence(self):
        """The branch name and expected sequence number are always sent."""
        self.sdk.create_branch(expected_main_last_known_sequence=12, branch_name="my-feature")

        payload = self._posted_payload()
        self.assertEqual(payload["branchName"], "my-feature")
        self.assertEqual(payload["expectedMainLastKnownSequence"], 12)

    def test_non_main_source_branch_is_sent(self):
        """A source branch other than main is sent as sourceBranchId."""
        self.sdk.create_branch(branch_name="my-feature", source_branch_id="branch-parent")

        self.assertEqual(self._posted_payload()["sourceBranchId"], "branch-parent")

    def test_source_branch_omitted_when_not_specified(self):
        """With no source branch the payload has no sourceBranchId key at all."""
        self.sdk.create_branch(branch_name="my-feature")

        self.assertNotIn("sourceBranchId", self._posted_payload())

    def test_source_branch_omitted_when_source_is_main(self):
        """Main is the server-side default, so it is not sent explicitly."""
        self.sdk.create_branch(branch_name="my-feature", source_branch_id="main")

        self.assertNotIn("sourceBranchId", self._posted_payload())

    def test_request_failure_raises_sourcerer_error(self):
        """A failing create request raises SourcererAPIError."""
        self.session.post.return_value = make_mock_response(409, json_body={"error": "conflict"})

        with self.assertRaises(SourcererAPIError):
            self.sdk.create_branch(branch_name="my-feature")


class SendCommandBatch(unittest.TestCase):
    """Tests for SourcererSDK.send_command_batch serialization and lifecycle."""

    def _queued_command(self):
        return Command(type="entity_create", command_id="cmd-1")

    @patch("poly.handlers.sdk.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.sdk.requests.post")
    def test_batch_serialized_with_sequence_and_octet_stream(self, mock_post, _mock_key):
        """The batch is sent as serialized protobuf with the cached sequence."""
        sdk = build_sdk()
        sdk._last_known_sequence = 7
        sdk.add_command_to_queue(self._queued_command())
        # send_command_batch refetches the projection at the end; stub the session get.
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {}, "lastKnownSequence": "8"}
        )
        sdk._session = session
        mock_post.return_value = make_mock_response(200, json_body={"status": "ok"})

        sdk.send_command_batch()

        sent_bytes = mock_post.call_args.kwargs["data"]
        headers = mock_post.call_args.kwargs["headers"]
        self.assertEqual(headers["Content-Type"], "application/octet-stream")

        # Real protobuf round-trip: the queued command survives serialization.
        parsed = CommandBatch()
        parsed.ParseFromString(sent_bytes)
        self.assertEqual(parsed.last_known_sequence, 7)
        self.assertEqual(len(parsed.commands), 1)
        self.assertEqual(parsed.commands[0].command_id, "cmd-1")

    @patch("poly.handlers.sdk.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.sdk.requests.post")
    def test_queue_cleared_on_success(self, mock_post, _mock_key):
        """A successful send clears the command queue."""
        sdk = build_sdk()
        sdk._last_known_sequence = 1
        sdk.add_command_to_queue(self._queued_command())
        session = MagicMock()
        session.get.return_value = make_mock_response(
            200, json_body={"projection": {}, "lastKnownSequence": "2"}
        )
        sdk._session = session
        mock_post.return_value = make_mock_response(200, json_body={"status": "ok"})

        sdk.send_command_batch()

        self.assertEqual(sdk.get_queue_size(), 0)

    def test_empty_queue_raises_sourcerer_error(self):
        """Sending with an empty queue raises SourcererAPIError."""
        sdk = build_sdk()

        with self.assertRaises(SourcererAPIError):
            sdk.send_command_batch()

    @patch("poly.handlers.sdk.retrieve_api_key", return_value="secret-key")
    @patch("poly.handlers.sdk.requests.post")
    def test_request_failure_raises_sourcerer_error(self, mock_post, _mock_key):
        """A failing batch POST raises SourcererAPIError."""
        sdk = build_sdk()
        sdk._last_known_sequence = 1
        sdk.add_command_to_queue(self._queued_command())
        mock_post.return_value = make_mock_response(500, json_body={"error": "boom"})

        with self.assertRaises(SourcererAPIError):
            sdk.send_command_batch()


if __name__ == "__main__":
    unittest.main()
