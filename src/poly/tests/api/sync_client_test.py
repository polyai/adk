"""Tests for the SyncClientHandler command queue and batch sending.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererSDK
from poly.handlers.sync_client import SyncClientHandler


def build_handler():
    """Build a SyncClientHandler with a mocked SDK, bypassing SDK construction.

    The region validity check reads ``SourcererSDK.ENVIRONMENT_URLS``, so the real
    class attribute is preserved while the constructor call is replaced.
    """
    with patch("poly.handlers.sync_client.SourcererSDK") as mock_sdk_cls:
        mock_sdk_cls.ENVIRONMENT_URLS = SourcererSDK.ENVIRONMENT_URLS
        handler = SyncClientHandler("studio", "acc-1", "proj-1", branch_id="branch-1")
    handler._sdk = MagicMock()
    return handler


class QueueCommand(unittest.TestCase):
    """Tests for SyncClientHandler.queue_command."""

    def test_sets_metadata_and_uuid_before_queueing(self):
        """A single command is stamped with metadata and a command id, then queued."""
        handler = build_handler()
        handler._sdk.create_metadata.return_value = Command().metadata
        command = Command(type="entity_create")

        handler.queue_command(command)

        self.assertTrue(command.command_id)  # a UUID was assigned
        handler._sdk.add_command_to_queue.assert_called_once_with(command)


class SendQueuedCommands(unittest.TestCase):
    """Tests for SyncClientHandler.send_queued_commands."""

    def test_empty_queue_returns_true_without_sending(self):
        """With nothing queued, the send is a no-op that reports success."""
        handler = build_handler()
        handler._sdk.get_queue_size.return_value = 0

        self.assertTrue(handler.send_queued_commands())
        handler._sdk.send_command_batch.assert_not_called()

    def test_successful_send_returns_true(self):
        """A successful batch send on a non-main branch reports success."""
        handler = build_handler()
        handler._sdk.get_queue_size.return_value = 2
        handler._sdk.branch_id = "branch-1"
        handler._sdk._command_queue = [Command(), Command()]
        # The branch must exist remotely, or the handler falls back to main and
        # tries to create a new branch before sending
        handler._sdk.fetch_branches.return_value = {"branches": [{"branchId": "branch-1"}]}

        self.assertTrue(handler.send_queued_commands())
        handler._sdk.send_command_batch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
