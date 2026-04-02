#!/usr/bin/env python
"""Sourcerer SDK for interacting with the Sourcerer API

This SDK provides a Python interface for fetching projections and sending
command batches to the Sourcerer API.

Copyright PolyAI Limited
"""

import json
import logging
import os
import uuid
import warnings
from typing import Any, Optional

import requests

from .protobuf.commands_pb2 import Command, CommandBatch

logger = logging.getLogger(__name__)

# Suppress protobuf version warnings - must be done before any protobuf imports
warnings.filterwarnings("ignore", message=".*Protobuf gencode version.*")
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf.runtime_version")


class SourcererAPIError(Exception):
    """Exception raised when the Sourcerer API returns an error"""

    pass


class SourcererSDK:
    """SDK for interacting with the Sourcerer API"""

    # Environment to base URL mapping
    ENVIRONMENT_URLS = {
        "dev": "https://api.dev.poly.ai/adk/v1",
        "us-staging": "https://api.staging.poly.ai/adk/v1",
        "euw-prod": "https://api.eu.poly.ai/adk/v1",
        "us-prod": "https://api.us.poly.ai/adk/v1",
        "uk-prod": "https://api.uk.poly.ai/adk/v1",
    }

    def __init__(
        self,
        region: str,
        environment: str,
        account_id: str,
        project_id: str,
        branch_id: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """Initialize the Sourcerer SDK

        Args:
            region: The region (e.g., 'us', 'euw', 'uk')
            environment: The environment (e.g., 'dev', 'prod', 'staging')
            account_id: The account ID
            project_id: The project ID
            branch_id: Optional branch ID. If not provided, will use the first available branch or create a new one
            base_url: Optional custom base URL. If not provided, will use the environment mapping
        """
        self.region = region
        self.environment = environment
        self.account_id = account_id
        self.project_id = project_id
        self.branch_id = branch_id

        # Set base URL
        if base_url:
            self.base_url = base_url
        else:
            env_key = f"{region}-{environment}" if environment != "dev" else "dev"
            if env_key not in self.ENVIRONMENT_URLS:
                raise ValueError(
                    f"Unknown environment: {env_key}. Available environments: {list(self.ENVIRONMENT_URLS.keys())}"
                )
            self.base_url = self.ENVIRONMENT_URLS[env_key]

        # Initialize session with auth headers
        correlation_id = f"adk-{uuid.uuid4()}"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "X-API-KEY": self._retrieve_api_key(),
                "X-PolyAI-Correlation-Id": correlation_id,
            }
        )

        # Cache for projection and sequence number
        self._projection_cache: Optional[dict[str, Any]] = None
        self._last_known_sequence: Optional[int] = None

        # Command queue for batching commands
        self._command_queue: list[Command] = []

        # Initialize branch_id if not provided
        if self.branch_id is None:
            self.branch_id = self._initialize_branch()

    def _retrieve_api_key(self) -> str:
        """Get API key from environment"""
        try:
            return os.getenv("POLY_ADK_KEY")
        except Exception:
            raise ValueError("POLY_ADK_KEY environment variable is required")

    def create_metadata(self):
        """Create metadata with the current user's email from JWT token

        Returns:
            Metadata object with created_by set to user's email and current timestamp
        """
        from google.protobuf.timestamp_pb2 import Timestamp

        from .protobuf.commands_pb2 import Metadata

        metadata = Metadata()
        metadata.created_by = "sdk-user"

        # Set current timestamp
        timestamp = Timestamp()
        timestamp.GetCurrentTime()
        metadata.created_at.CopyFrom(timestamp)

        return metadata

    def _get_projection_url(self) -> str:
        """Get the projection endpoint URL"""
        return f"{self.base_url}/accounts/{self.account_id}/projects/{self.project_id}/branches/{self.branch_id}/projection"

    def _get_deployment_projection_url(self, deployment_id: str) -> str:
        """Get the deployment projection endpoint URL"""
        return f"{self.base_url}/accounts/{self.account_id}/projects/{self.project_id}/deployments/{deployment_id}/projection"

    def _get_command_batch_url(self) -> str:
        """Get the command batch endpoint URL"""
        return f"{self.base_url}/accounts/{self.account_id}/projects/{self.project_id}/branches/{self.branch_id}/command-batch"

    def _get_branches_url(self) -> str:
        """Get the branches endpoint URL"""
        return f"{self.base_url}/accounts/{self.account_id}/projects/{self.project_id}/branches"

    def _get_branch_merge_url(self) -> str:
        """Get the branch merge endpoint URL"""
        return f"{self.base_url}/accounts/{self.account_id}/projects/{self.project_id}/branches/{self.branch_id}/merge"

    def _initialize_branch(self) -> str:
        """Initialize branch_id by fetching existing branches or creating a new one"""
        try:
            # Try to get existing branches
            branches = self.fetch_branches()
            if found_branches := branches.get("branches"):
                # Use the first branch
                return found_branches[0]["branchId"]
            else:
                # No branches exist, create a new one
                # Use expected sequence number of main branch
                self.branch_id = "main"
                self.get_project_data()
                return self.create_branch(
                    expected_main_last_known_sequence=self._last_known_sequence or 0
                )
        except SourcererAPIError:
            # If fetching branches fails, try to create a new branch
            return self.create_branch()

    def fetch_branches(self) -> dict[str, list[dict[str, Any]]]:
        """Fetch the list of branches for the project

        Returns:
            List of branch dictionaries with 'id' property

        Raises:
            SourcererAPIError: If the API request fails
        """
        try:
            response = self.session.get(self._get_branches_url())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API request failed: {e}"
            else:
                error_msg = f"Request failed: {e}"
            raise SourcererAPIError(error_msg) from e

    def create_branch(
        self,
        expected_main_last_known_sequence: int = 0,
        branch_name: Optional[str] = None,
    ) -> str:
        """Create a new branch for the project

        Args:
            expected_main_last_known_sequence: The expected sequence number from main branch
            branch_name: Optional name for the branch. If not provided, will generate a default name

        Returns:
            The ID of the created branch

        Raises:
            SourcererAPIError: If the API request fails
        """
        try:
            # Generate a default branch name if not provided
            if branch_name is None:
                branch_name = "adk-branch"

            payload = {
                "expectedMainLastKnownSequence": expected_main_last_known_sequence,
                "branchName": branch_name or f"sdk-branch-{os.urandom(4).hex()}",
            }
            response = self.session.post(self._get_branches_url(), json=payload)
            response.raise_for_status()
            branch_data = response.json()
            return branch_data["branchId"]
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API request failed: {e}"
            else:
                error_msg = f"Request failed: {e}"
            raise SourcererAPIError(error_msg) from e

    def merge_branch(
        self,
        expected_branch_last_known_sequence: int,
        deployment_message: str = "",
        conflict_resolutions: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Merge the current branch into the main branch

        This method merges changes from the current branch into the main branch.
        If conflicts are detected, they will be returned in the response for manual resolution.
        Once conflicts are resolved, call this method again with the conflict_resolutions parameter.

        Args:
            expected_branch_last_known_sequence: The expected sequence number of the branch being merged
            deployment_message: Optional message describing the deployment (default: "")
            conflict_resolutions: Optional list of conflict resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            Dictionary containing:
            - If successful:
                - sequence: The new sequence number after merge (as string)
                - message: Success message
                - testRunIds: List of test run IDs that were triggered
            - If conflicts detected:
                - hasConflicts: True
                - conflicts: List of conflict objects, each containing:
                    - path: Path to the conflicted field
                    - baseValue: Original value from base
                    - oursValue: Value from main branch
                    - theirsValue: Value from the branch being merged
                    - type: Type of conflict ("add", "modify", or "delete")

        Raises:
            SourcererAPIError: If the API request fails or sequence mismatch occurs

        Example:
            # Simple merge without conflicts
            result = sdk.merge_branch(expected_branch_last_known_sequence=5)
            if "hasConflicts" in result and result["hasConflicts"]:
                print("Conflicts detected:", result["conflicts"])
            else:
                print("Merge successful, sequence:", result["sequence"])

            # Merge with conflict resolution
            resolutions = [
                {
                    "path": ["users", "1", "name"],
                    "strategy": "ours",
                },
                {
                    "path": ["settings", "theme"],
                    "strategy": "theirs",
                }
            ]
            result = sdk.merge_branch(
                expected_branch_last_known_sequence=5,
                deployment_message="Merge feature branch",
                conflict_resolutions=resolutions
            )
        """
        try:
            payload = {
                "expectedBranchLastKnownSequence": expected_branch_last_known_sequence,
                "deploymentMessage": deployment_message,
            }

            if conflict_resolutions is not None:
                payload["conflictResolutions"] = conflict_resolutions

            logger.info(f"Merging branch {self.branch_id} to main")
            logger.debug(f"Merge payload: {payload}")

            response = self.session.post(self._get_branch_merge_url(), json=payload)

            # Handle conflict response (400 status with conflicts data)
            if response.status_code == 400:
                try:
                    response_data = response.json()
                    # Check if this is a conflict response
                    if "conflicts" in response_data or "hasConflicts" in response_data:
                        return response_data
                    # Otherwise, it's a different error
                    error_msg = f"API Error 400: {response_data}"
                    raise SourcererAPIError(error_msg)
                except (ValueError, KeyError):
                    error_msg = f"API Error 400: {response.text}"
                    raise SourcererAPIError(error_msg)

            response.raise_for_status()

            response_data = response.json()
            logger.info(f"Branch merged successfully, sequence: {response_data.get('sequence')}")

            return response_data

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API request failed: {e}"
            else:
                error_msg = f"Request failed: {e}"
            raise SourcererAPIError(error_msg) from e

    def delete_branch(self, branch_id: str) -> None:
        """Delete the current branch from the project

        Args:
            branch_id: The ID of the branch to delete

        Raises:
            SourcererAPIError: If the API request fails
        """
        try:
            url = f"{self._get_branches_url()}/{branch_id}"
            data = {"expectedBranchLastKnownSequence": self.get_last_known_sequence() or 0}
            response = self.session.delete(url, json=data)
            response.raise_for_status()
            logger.info(f"Branch {branch_id} deleted successfully")
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API request failed: {e}"
            else:
                error_msg = f"Request failed: {e}"
            raise SourcererAPIError(error_msg) from e

    def fetch_last_known_sequence_number(self) -> int:
        """Get the sequence number from the API
        Returns:
            The sequence number as an integer
        Raises:
            SourcererAPIError: If the API request fails
        """
        try:
            url = f"{self._get_branches_url()}/{self.branch_id}/sequence"
            response = self.session.get(url)
            response.raise_for_status()
            return int(response.json()["lastKnownSequence"])
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API request failed: {e}"
            else:
                error_msg = f"Request failed: {e}"
            raise SourcererAPIError(error_msg) from e

    def fetch_projection(self, force_refresh: bool = False) -> dict[str, Any]:
        """Fetch the projection from the API

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            The projection data as a dictionary

        Raises:
            SourcererAPIError: If the API request fails
        """
        if self._projection_cache is not None and not force_refresh:
            return self._projection_cache

        try:
            response = self.session.get(self._get_projection_url())
            response.raise_for_status()

            response_data = response.json()

            # Handle the response structure: { lastKnownSequence: string, projection: object }
            self._projection_cache = response_data["projection"]

            # Cache the sequence number separately
            if (
                "lastKnownSequence" in response_data
                and response_data["lastKnownSequence"] is not None
            ):
                self._last_known_sequence = int(response_data["lastKnownSequence"])
            else:
                self._last_known_sequence = None

            return self._projection_cache

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API Error {e.response.status_code}: {e.response.text}"
            else:
                error_msg = f"Request failed: {str(e)}"

            raise SourcererAPIError(error_msg) from e

    def fetch_deployment_projection(self, deployment_id: str) -> dict[str, Any]:
        """Fetch projection for a specific deployment from the API
        Returns:
            The deployment projection data as a dictionary
        Raises:
            SourcererAPIError: If the API request fails
        """
        try:
            response = self.session.get(self._get_deployment_projection_url(deployment_id))
            response.raise_for_status()

            response_data = response.json()
            return response_data["projection"]
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API Error {e.response.status_code}: {e.response.text}"
            else:
                error_msg = f"Request failed: {str(e)}"

            raise SourcererAPIError(error_msg) from e

    def add_command_to_queue(self, command: Command) -> None:
        """Add a command to the queue for batch sending

        Args:
            command: The Command protobuf message to add to the queue
        """
        self._command_queue.append(command)

    def add_commands_to_queue(self, commands: list[Command]) -> None:
        """Add multiple commands to the queue for batch sending

        Args:
            commands: List of Command protobuf messages to add to the queue
        """
        self._command_queue.extend(commands)

    def get_queue_size(self) -> int:
        """Get the number of commands currently in the queue

        Returns:
            Number of commands in the queue
        """
        return len(self._command_queue)

    def clear_queue(self) -> None:
        """Clear all commands from the queue"""
        self._command_queue.clear()

    def send_command_batch(self) -> dict[str, Any]:
        """Send all queued commands as a batch to the API

        This method:
        1. Creates a CommandBatch from all queued commands
        2. Sets the correct sequence number from current projection
        3. Sends the batch to the API
        4. Clears the queue after successful send
        5. Refetches the projection to get updated state

        Returns:
            The response data from the API

        Raises:
            SourcererAPIError: If the API request fails or no commands in queue
        """
        if not self._command_queue:
            raise SourcererAPIError("No commands in queue to send")

        try:
            # Create command batch from queued commands
            command_batch = CommandBatch()
            command_batch.commands.extend(self._command_queue)

            # Set the sequence number from cached value
            command_batch.last_known_sequence = self.get_last_known_sequence()

            # Validate the command batch before sending
            logger.debug("Command batch validation:")
            logger.debug(f"  - Commands count: {len(command_batch.commands)}")
            logger.debug(f"  - Last known sequence: {command_batch.last_known_sequence}")

            # Check each command
            for i, cmd in enumerate(command_batch.commands):
                logger.debug(f"  - Command {i}: type={cmd.type}, id={cmd.command_id}")
                if not cmd.type:
                    raise SourcererAPIError(f"Command {i} has no type")
                if not cmd.command_id:
                    raise SourcererAPIError(f"Command {i} has no command_id")

            # Serialize the protobuf message to bytes
            try:
                command_batch_bytes = command_batch.SerializeToString()
                logger.debug(f"Serialized command batch size: {len(command_batch_bytes)} bytes")
                logger.debug(f"Command batch has {len(command_batch.commands)} commands")
                logger.debug(f"Last known sequence: {command_batch.last_known_sequence}")

                # Verify we can deserialize it back
                test_batch = CommandBatch()
                test_batch.ParseFromString(command_batch_bytes)
                logger.debug("✓ Protobuf serialization/deserialization test passed")

            except Exception as e:
                logger.exception(f"✗ Protobuf serialization failed: {e}")
                raise SourcererAPIError(f"Failed to serialize command batch: {e}")

            # Update headers for protobuf content
            correlation_id = f"adk-{uuid.uuid4()}"
            headers = {
                "X-API-KEY": self._retrieve_api_key(),
                "X-PolyAI-Correlation-Id": correlation_id,
                "Content-Type": "application/octet-stream",
            }

            logger.info(f"Sending to URL: {self._get_command_batch_url()}")

            # Send the protobuf data as binary
            response = requests.post(
                self._get_command_batch_url(),
                data=command_batch_bytes,
                headers=headers,
            )
            response.raise_for_status()

            # Try to parse response as JSON, fallback to text
            try:
                response_data = response.json()
            except (ValueError, json.JSONDecodeError):
                raise SourcererAPIError(f"Failed to parse response: {response.text}")

            if response_data.get("error"):
                raise SourcererAPIError(f"Error: {response_data.get('error')}")

            # Clear the queue after successful send
            self.clear_queue()

            # Refetch projection after successful command batch
            return self.fetch_projection(force_refresh=True)

        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"API Error {e.response.status_code}: {error_detail}"
                except (ValueError, KeyError):
                    error_msg = f"API Error {e.response.status_code}: {e.response.text}"
            else:
                error_msg = f"Request failed: {str(e)}"

            raise SourcererAPIError(error_msg) from e

    def get_project_data(self) -> dict[str, Any]:
        """Get the cached projection data

        Returns:
            The cached projection data, or fetches it if not cached
        """
        if self._projection_cache is None:
            return self.fetch_projection()
        return self._projection_cache

    def clear_cache(self):
        """Clear the projection, sequence number cache, and command queue"""
        self._projection_cache = None
        self._last_known_sequence = None
        self.clear_queue()

    def get_branch_chat_info(self, branch_id: str) -> dict[str, Any]:
        """Get deployment info needed to start a draft chat on a branch.

        Uses the cached lastKnownSequence and calls the
        /branches/{branchId}/chat endpoint to prepare the deployment.

        Args:
            branch_id: The branch ID to prepare for chat

        Returns:
            dict with 'artifactVersion', 'lambdaDeploymentVersion', etc.

        Raises:
            SourcererAPIError: If the API call fails
        """
        sequence = self.get_last_known_sequence() or 0
        url = f"{self._get_branches_url()}/{branch_id}/chat"
        logger.info(f"Preparing branch deployment via {url}")
        try:
            resp = self.session.post(
                url,
                json={"expectedBranchLastKnownSequence": sequence},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise SourcererAPIError(f"Failed to get branch chat info: {e}") from e

    def get_last_known_sequence(self) -> Optional[int]:
        """Get the last known sequence number from the current projection

        Returns:
            The last known sequence number, or None if not available
        """
        # Return cached value if available
        if self._last_known_sequence is not None:
            return self._last_known_sequence

        # If no cached value, fetch projection to get it
        self._last_known_sequence = self.fetch_last_known_sequence_number()
        return self._last_known_sequence

    def get_full_projection_response(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get the full projection response including sequence number

        Args:
            force_refresh: If True, bypass cache and fetch fresh data

        Returns:
            Dictionary with 'projection' and 'last_known_sequence' keys
        """
        if force_refresh or self._projection_cache is None:
            self.fetch_projection(force_refresh=True)

        return {
            "projection": self._projection_cache,
            "last_known_sequence": self._last_known_sequence,
        }
