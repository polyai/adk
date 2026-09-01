"""Sync client for Agent Studio content management

Copyright PolyAI Limited
"""

import logging
import uuid
from copy import deepcopy
from typing import Any, Optional

from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererAPIError, SourcererSDK

logger = logging.getLogger(__name__)


class SyncClientHandler:
    """Sync client for Agent Studio content management"""

    _sdk: Optional[SourcererSDK] = None
    region: str
    account_id: str
    project_id: str

    @property
    def branch_id(self) -> str:
        """Get the current branch ID."""
        return self._sdk.branch_id

    def __init__(
        self,
        region: str,
        account_id: Optional[str] = None,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ):
        if region not in SourcererSDK.ENVIRONMENT_URLS:
            raise ValueError(
                f"Invalid region '{region}'. Valid regions are: {list(SourcererSDK.ENVIRONMENT_URLS.keys())}"
            )

        self.region = region
        self.account_id = account_id
        self.project_id = project_id

        self._sdk = SourcererSDK(
            region=region,
            account_id=account_id,
            project_id=project_id,
            branch_id=branch_id,
        )

    @property
    def sdk(self) -> SourcererSDK:
        """Get the Sourcerer SDK instance."""
        return self._sdk

    def assert_branch_exists(self) -> str:
        """Assert that the branch exists and switch to 'main' if it doesn't."""
        if self.branch_id != "main":
            found_branches = self._sdk.fetch_branches().get("branches", [])
            branch = next((b for b in found_branches if b.get("branchId") == self.branch_id), None)
            if not branch:
                logger.info(
                    f"Branch ID:'{self.branch_id}' does not exist. Switching to 'main' branch."
                )
                self._sdk.branch_id = "main"
        return self.branch_id

    def list_template_projects(self) -> list[dict[str, Any]]:
        """List available template projects.

        Returns:
            list[dict[str, Any]]: A list of template project summaries.
        """
        return self.sdk.list_template_projects()

    def get_template_project_projection(self, template_id: str) -> dict[str, Any]:
        """Get the full projection for a template project.

        The template API returns a different shape to the sourcerer projection.
        This method fetches and normalises it so
        ``load_resources_from_projection`` can consume it.

        Args:
            template_id: The template project ID.

        Returns:
            dict[str, Any]: The projection in sourcerer-compatible format.
        """
        return self.sdk.get_template_project_projection(template_id)

    def pull_deployment_projection(self, deployment_id: str) -> dict[str, Any]:
        """Fetch the raw projection for a specific deployment.

        Args:
            deployment_id: The deployment ID.

        Returns:
            The raw projection dict.
        """
        logger.info(
            f"Fetching project data for project {self.project_id} for deployment {deployment_id}"
        )
        self.assert_branch_exists()
        projection = self.sdk.fetch_deployment_projection(deployment_id=deployment_id)
        logger.info(
            f"Successfully fetched project data for project {self.project_id} "
            f"for deployment {deployment_id}"
        )
        return projection

    def pull_branch_projection(
        self, branch_id: str, at_sequence: Optional[int] = None
    ) -> dict[str, Any]:
        """Fetch projection for a specific branch, optionally at a historical sequence.

        Args:
            branch_id: The branch whose projection to fetch.
            at_sequence: When provided, fetches the projection at this sequence number.

        Returns:
            The raw projection dict for the branch.
        """
        logger.info(
            f"Fetching projection for branch {branch_id}"
            + (f" at sequence {at_sequence}" if at_sequence is not None else "")
        )
        projection = self.sdk.fetch_projection(
            force_refresh=True, branch_id=branch_id, at_sequence=at_sequence
        )
        return projection

    def pull_projection(self) -> dict[str, Any]:
        """Fetch the raw projection for the current branch.

        Returns:
            The raw projection dict.
        """
        self.assert_branch_exists()
        projection = self.pull_branch_projection(branch_id=self.sdk.branch_id)
        logger.debug(f"Projection: {projection}")
        logger.info(
            f"Successfully fetched project data for project {self.project_id} "
            f"on branch {self.sdk.branch_id}"
        )
        return projection

    def queue_command(self, command: Command) -> None:
        """Add a single command to the queue.
        Sets the command ID and metadata before adding to the queue.

        Args:
            command (Command): The Command protobuf message to add to the queue.
        """
        command.metadata.CopyFrom(self.sdk.create_metadata())
        command.command_id = str(uuid.uuid4())
        self.sdk.add_command_to_queue(command)
        logger.info("Queued command")
        logger.debug(f"Command: {command!r}")
        return command

    def send_queued_commands(self) -> bool:
        """Send all queued commands as a batch and clear the queue.

        Returns:
            bool: True if the commands were sent successfully, False otherwise
        """
        if self.sdk.get_queue_size() == 0:
            logger.info("No commands to send")
            return True

        self.assert_branch_exists()

        # Creates branch and switches to it
        if self.sdk.branch_id == "main":
            self.create_branch()

        try:
            logger.info(f"Sending {len(self.sdk._command_queue)} commands to {self.sdk.branch_id}")
            self.sdk.send_command_batch()
            return True
        except SourcererAPIError as e:
            logger.error(f"Failed to send commands: {e}")
            return False

    def clear_command_queue(self) -> None:
        """Clear all queued commands without sending."""
        logger.info(f"Clearing {len(self.sdk._command_queue)} commands")
        self.sdk.clear_queue()

    def get_queued_commands(self) -> list[Command]:
        """Get all queued commands.

        Returns:
            list[Command]: A list of queued Command protobuf messages.
        """
        return deepcopy(self.sdk._command_queue)

    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different branch within the same project.

        Args:
            branch_id (str): The ID of the branch to switch to

        Returns:
            bool: True if the switch was successful, False otherwise
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == branch_id:
            logger.info(f"Already on branch ID:'{branch_id}'")
            return True

        if branch_id == "main":
            self.sdk.branch_id = "main"
            self.sdk.get_project_data()
            logger.info(f"Switched to branch ID:'{branch_id}'")
            return True

        if found_branches := self.sdk.fetch_branches().get("branches"):
            branch = next((b for b in found_branches if b.get("branchId") == branch_id), None)
            if branch:
                self.sdk.branch_id = branch_id
                # Re-fetch project data to ensure the SDK is up-to-date
                self.sdk.clear_cache()
                self.sdk.get_project_data()
                logger.info(f"Switched to branch ID:'{branch_id}'")
                return True
            else:
                logger.error(f"Branch ID:'{branch_id}' does not exist.")
                return False
        return False

    def create_branch(
        self, branch_name: Optional[str] = None, source_branch_id: Optional[str] = None
    ) -> str:
        """Create a new branch for the project

        Args:
            branch_name: Optional name for the new branch. If not provided, a default name will be used.

        Returns:
            The ID of the created branch
        """
        sequence_number = self.sdk.fetch_last_known_sequence_number(
            branch_id=source_branch_id or "main"
        )

        if branch_name is None:
            metadata = self.sdk.create_metadata()
            time_suffix = f"{metadata.created_at.seconds % 100000:05d}"
            random_suffix = uuid.uuid4().hex[:4]
            suffix = f"{time_suffix}-{random_suffix}"  # to avoid duplicate names
            branch_name = f"ADK-{suffix}"

        logger.info(
            f"Creating new branch '{branch_name}' from branch '{source_branch_id or 'main'}'"
        )

        self.sdk.branch_id = self.sdk.create_branch(
            expected_main_last_known_sequence=sequence_number,
            branch_name=branch_name,
            source_branch_id=source_branch_id,
        )
        logger.info(
            f"Created and switched to new branch. Name:'{branch_name}' ID:'{self.sdk.branch_id}'"
        )
        return self.sdk.branch_id

    def get_branches(self) -> dict[str, dict[str, Any]]:
        """Get a list of all branches in the project.

        Returns:
            A dictionary mapping branch names to their full metadata dicts.
            Each value contains at least ``branchId``, ``parentBranchId``,
            ``parentSequence``, ``isDiverged``, etc.  The ``main`` entry is
            synthetic with ``branchId="main"`` and no parent info.
        """
        branches: dict[str, dict[str, Any]] = {
            "main": {"branchId": "main", "name": "main"},
        }
        logger.info(f"Fetching branches for project {self.account_id}/{self.project_id}")
        for branch in self.sdk.fetch_branches().get("branches", []):
            branches[branch.get("name")] = branch
        logger.info(f"Fetched {len(branches)} branches")
        return branches

    def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch in the project.

        Args:
            branch_id (str): The ID of the branch to delete

        Returns:
            bool: True if the branch was deleted successfully.

        Raises:
            SourcererAPIError: If the API request fails.
        """
        if branch_id == "main":
            logger.error("Cannot delete 'main' branch.")
            return False

        logger.info(f"Deleting branch ID:'{branch_id}'")

        try:
            self.sdk.delete_branch(branch_id=branch_id)
        except SourcererAPIError as e:
            logger.debug(f"Failed to delete branch ID:'{branch_id}': {e}")
            raise

        logger.info(f"Successfully deleted branch ID:'{branch_id}'")
        return True

    def merge_branch(
        self, message: Optional[str], conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the current branch into its parent branch.

        Args:
            message (Optional[str]): The merge commit message
            conflict_resolutions (Optional[list[dict[str, Any]]]): A list of conflict resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            success (bool): True if the merge was successful, False otherwise
            list[dict[str, str]]: A list of conflict information if the merge failed, empty list if successful
            list[dict[str, str]]: A list of error information if the merge failed, empty list if successful
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == "main":
            logger.error("Cannot merge 'main' branch into itself.")
            return False, [], []

        logger.info(f"Merging branch '{self.sdk.branch_id}' into its parent branch")

        try:
            result = self.sdk.merge_branch(
                deployment_message=message,
                conflict_resolutions=conflict_resolutions,
            )
        except SourcererAPIError as e:
            logger.error(
                f"Failed to merge branch '{self.sdk.branch_id}' into its parent branch: {e}"
            )
            return False, [], [{"path": [], "message": str(e)}]

        if result.get("hasConflicts", False) or result.get("errors", []):
            logger.info(
                f"Failed to merge branch '{self.sdk.branch_id}' into its parent branch due to {len(result.get('conflicts', []))} conflicts and {len(result.get('errors', []))} errors"
            )
            conflicts = result.get("conflicts", [])
            errors = result.get("errors", [])
            return False, conflicts, errors

        logger.info(f"Successfully merged branch '{self.sdk.branch_id}' into its parent branch")
        return True, [], []

    def sync_branch(
        self, conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the parent branch into the current branch.

        Args:
            conflict_resolutions (list[dict[str, Any]]): A list of conflict resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            success (bool): True if the sync was successful, False otherwise
            list[dict[str, str]]: A list of conflict information if the merge failed, empty list if successful
            list[dict[str, str]]: A list of error information if the merge failed, empty list if successful
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == "main":
            logger.error("Cannot sync 'main' branch — it has no parent to sync from.")
            return False, [], []

        logger.info(f"Merging parent into '{self.sdk.branch_id}'")

        try:
            result = self.sdk.sync_branch(
                conflict_resolutions=conflict_resolutions,
            )
        except SourcererAPIError as e:
            logger.error(f"Failed to sync branch '{self.sdk.branch_id}': {e}")
            return False, [], [{"path": [], "message": str(e)}]

        if result.get("hasConflicts", False) or result.get("errors", []):
            logger.info(
                f"Failed to sync branch '{self.sdk.branch_id}' to {len(result.get('conflicts', []))} conflicts and {len(result.get('errors', []))} errors"
            )
            conflicts = result.get("conflicts", [])
            errors = result.get("errors", [])
            return False, conflicts, errors

        logger.info(f"Successfully synced branch '{self.sdk.branch_id}'")
        return True, [], []

    def get_branch_chat_info(self, branch_id: str) -> dict[str, Any]:
        """Get deployment info needed to start a draft chat on a branch."""
        self.assert_branch_exists()
        return self.sdk.get_branch_chat_info(branch_id)

    def get_branch_history(self, branch_id: str) -> list[dict[str, Any]]:
        """Get the history of a specific branch.

        Args:
            branch_id (str): The ID of the branch to retrieve history for.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing commit information for the branch.
        """
        logger.info(f"Fetching history for branch ID:'{branch_id}'")
        history = self.sdk.get_branch_history(branch_id)
        logger.info(f"Fetched {len(history)} commits for branch ID:'{branch_id}'")
        return history

    def rename_branch(self, new_branch_name: str) -> bool:
        """Rename the current branch.

        Args:
            new_branch_name (str): The new name for the current branch.

        Returns:
            bool: True if the rename was successful, False otherwise.
        """
        self.assert_branch_exists()

        if self.sdk.branch_id == "main":
            logger.error("Cannot rename 'main' branch.")
            return False

        logger.info(f"Renaming branch ID:'{self.sdk.branch_id}' to '{new_branch_name}'")

        try:
            self.sdk.rename_branch(new_branch_name=new_branch_name)
        except SourcererAPIError as e:
            logger.error(f"Failed to rename branch ID:'{self.sdk.branch_id}': {e}")
            return False

        logger.info(f"Successfully renamed branch ID:'{self.sdk.branch_id}' to '{new_branch_name}'")
        return True

    def list_archived_branches(self) -> list[dict[str, Any]]:
        """List soft-deleted (archived) branches for the project.

        Returns:
            list[dict[str, Any]]: A list of dictionaries containing archived branch information.
        """
        logger.info("Fetching archived branches")
        branches = self.sdk.list_archived_branches()
        logger.info(f"Fetched {len(branches)} archived branches")
        return branches

    def restore_branch(self, branch_id: str) -> bool:
        """Restore a soft-deleted branch from the archive.

        Args:
            branch_id (str): The ID of the branch to restore.

        Returns:
            bool: True if the restore was successful, False otherwise.
        """
        logger.info(f"Restoring branch ID:'{branch_id}'")

        try:
            self.sdk.restore_branch(branch_id)
        except SourcererAPIError as e:
            logger.error(f"Failed to restore branch ID:'{branch_id}': {e}")
            return False

        logger.info(f"Successfully restored branch ID:'{branch_id}'")
        return True

    def tag_branch(self, branch_id: str) -> bool:
        """Tag a branch with staging tag

        Args:
            branch_id (str): The ID of the branch to tag.
        Returns:
            bool: True if the tagging was successful, False otherwise.
        """
        logger.info(f"Tagging branch ID:'{branch_id}' with staging tag")

        try:
            self.sdk.tag_branch(branch_id)
        except SourcererAPIError as e:
            logger.error(f"Failed to tag branch ID:'{branch_id}': {e}")
            return False

        logger.info(f"Successfully tagged branch ID:'{branch_id}' with staging tag")
        return True

    def untag_branch(self, branch_id: str) -> bool:
        """Remove staging tag from a branch

        Args:
            branch_id (str): The ID of the branch to untag.
        Returns:
            bool: True if the untagging was successful, False otherwise.
        """
        logger.info(f"Removing staging tag from branch ID:'{branch_id}'")

        try:
            self.sdk.untag_branch(branch_id)
        except SourcererAPIError as e:
            logger.error(f"Failed to remove staging tag from branch ID:'{branch_id}': {e}")
            return False

        logger.info(f"Successfully removed staging tag from branch ID:'{branch_id}'")
        return True
