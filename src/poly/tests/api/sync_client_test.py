"""Tests for the SyncClientHandler command queue and batch sending.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererAPIError, SourcererSDK
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


class GetBranchHistory(unittest.TestCase):
    """Tests for SyncClientHandler.get_branch_history."""

    def test_returns_history_from_sdk(self):
        """The handler delegates to sdk.get_branch_history and returns its result."""
        handler = build_handler()
        expected = [{"commit_id": "c1", "message": "initial"}]
        handler._sdk.get_branch_history.return_value = expected

        result = handler.get_branch_history("branch-1")

        self.assertEqual(result, expected)
        handler._sdk.get_branch_history.assert_called_once_with("branch-1")

    def test_returns_empty_list_when_no_history(self):
        """An empty history list is returned as-is."""
        handler = build_handler()
        handler._sdk.get_branch_history.return_value = []

        result = handler.get_branch_history("branch-1")

        self.assertEqual(result, [])


class RenameBranch(unittest.TestCase):
    """Tests for SyncClientHandler.rename_branch."""

    def test_successful_rename_returns_true(self):
        """A successful SDK rename call returns True."""
        handler = build_handler()
        handler._sdk.branch_id = "branch-1"
        handler._sdk.fetch_branches.return_value = {"branches": [{"branchId": "branch-1"}]}

        result = handler.rename_branch("new-name")

        self.assertTrue(result)
        handler._sdk.rename_branch.assert_called_once_with(new_branch_name="new-name")

    def test_main_branch_returns_false(self):
        """Renaming the main branch returns False without calling the SDK."""
        handler = build_handler()
        handler._sdk.branch_id = "main"
        handler._sdk.fetch_branches.return_value = {"branches": [{"branchId": "main"}]}

        result = handler.rename_branch("new-name")

        self.assertFalse(result)
        handler._sdk.rename_branch.assert_not_called()

    def test_api_error_returns_false(self):
        """A SourcererAPIError during rename returns False."""
        handler = build_handler()
        handler._sdk.branch_id = "branch-1"
        handler._sdk.fetch_branches.return_value = {"branches": [{"branchId": "branch-1"}]}
        handler._sdk.rename_branch.side_effect = SourcererAPIError("rename failed")

        result = handler.rename_branch("new-name")

        self.assertFalse(result)


class ListArchivedBranches(unittest.TestCase):
    """Tests for SyncClientHandler.list_archived_branches."""

    def test_returns_archived_branches_from_sdk(self):
        """The handler delegates to sdk.list_archived_branches and returns its result."""
        handler = build_handler()
        expected = [{"branchId": "b-1", "name": "old-branch", "archivedAt": "2026-07-01"}]
        handler._sdk.list_archived_branches.return_value = expected

        result = handler.list_archived_branches()

        self.assertEqual(result, expected)
        handler._sdk.list_archived_branches.assert_called_once()

    def test_returns_empty_list_when_no_archived_branches(self):
        """An empty list is returned as-is."""
        handler = build_handler()
        handler._sdk.list_archived_branches.return_value = []

        result = handler.list_archived_branches()

        self.assertEqual(result, [])


class RestoreBranch(unittest.TestCase):
    """Tests for SyncClientHandler.restore_branch."""

    def test_successful_restore_returns_true(self):
        """A successful SDK restore call returns True."""
        handler = build_handler()

        result = handler.restore_branch("branch-1")

        self.assertTrue(result)
        handler._sdk.restore_branch.assert_called_once_with("branch-1")

    def test_api_error_returns_false(self):
        """A SourcererAPIError during restore returns False."""
        handler = build_handler()
        handler._sdk.restore_branch.side_effect = SourcererAPIError("restore failed")

        result = handler.restore_branch("branch-1")

        self.assertFalse(result)


class TagBranch(unittest.TestCase):
    """Tests for SyncClientHandler.tag_branch."""

    def test_successful_tag_returns_true(self):
        """A successful SDK tag call returns True."""
        handler = build_handler()

        result = handler.tag_branch("branch-1")

        self.assertTrue(result)
        handler._sdk.tag_branch.assert_called_once_with("branch-1")

    def test_api_error_returns_false(self):
        """A SourcererAPIError during tagging returns False rather than propagating."""
        handler = build_handler()
        handler._sdk.tag_branch.side_effect = SourcererAPIError("tag failed")

        result = handler.tag_branch("branch-1")

        self.assertFalse(result)


class UntagBranch(unittest.TestCase):
    """Tests for SyncClientHandler.untag_branch."""

    def test_successful_untag_returns_true(self):
        """A successful SDK untag call returns True."""
        handler = build_handler()

        result = handler.untag_branch("branch-1")

        self.assertTrue(result)
        handler._sdk.untag_branch.assert_called_once_with("branch-1")

    def test_api_error_returns_false(self):
        """A SourcererAPIError during untagging returns False rather than propagating."""
        handler = build_handler()
        handler._sdk.untag_branch.side_effect = SourcererAPIError("untag failed")

        result = handler.untag_branch("branch-1")

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
