"""API Handler Interface for Agent Studio

Copyright PolyAI Limited"""

import json
from typing import Any, NoReturn, Optional

import requests
from google.protobuf.message import Message

from poly.handlers.platform_api import PlatformAPIHandler
from poly.handlers.sdk import SourcererAPIError
from poly.handlers.sync_client import SyncClientHandler
from poly.resources import BaseResource, Resource

REGIONS = [
    "us-1",
    "euw-1",
    "uk-1",
    "studio",
    "staging",
    "dev",
]


class AgentStudioInterface:
    """Interface for the Agent Studio API"""

    region: Optional[str] = None
    account_id: Optional[str] = None
    project_id: Optional[str] = None
    sync_client: Optional[SyncClientHandler] = None

    @staticmethod
    def _extract_error_code(e: Exception) -> Optional[str]:
        """Extract the error_code field from an API error response body.

        Args:
            e: The exception to inspect

        Returns:
            str | None: The error_code value, or None if not present
        """
        response = getattr(e, "response", None)
        if response is None and e.__cause__ is not None:
            response = getattr(e.__cause__, "response", None)
        if response is not None:
            try:
                return response.json().get("error_code")
            except (json.JSONDecodeError, ValueError, AttributeError):
                pass
        return None

    def _handle_api_error(self, e: Exception) -> NoReturn:
        """Translate an API HTTP error into a user-facing ValueError.

        Extracts the error_code from the response body and raises a ValueError
        with a descriptive message. Always raises.

        Args:
            e: The HTTPError or SourcererAPIError to translate

        Raises:
            ValueError: Always raised with a user-facing message
        """
        error_code = self._extract_error_code(e)

        if error_code == "FORBIDDEN":
            raise ValueError(
                f"Forbidden: you do not have permission to access "
                f"project '{self.project_id}' in account '{self.account_id}'."
            ) from e
        elif error_code == "DEPLOYMENT_NOT_FOUND":
            raise ValueError(
                f"Project '{self.project_id}' not found in account '{self.account_id}'."
            ) from e
        else:
            raise ValueError(f"API error: {e}") from e

    @property
    def branch_id(self) -> Optional[str]:
        """Get the current branch ID."""
        if not self.sync_client:
            return None
        return self.sync_client.branch_id

    def __init__(
        self,
        region: Optional[str] = None,
        account_id: Optional[str] = None,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ):
        self.region = region
        self.account_id = account_id
        self.project_id = project_id
        if region and account_id and project_id:
            self.sync_client = SyncClientHandler(region, account_id, project_id, branch_id)

    @staticmethod
    def get_accessible_regions() -> list[str]:
        """Get the regions accessible to the current API key.

        Returns:
            list[str]: Region names the user has access to.
        """
        return PlatformAPIHandler.get_accessible_regions(REGIONS)

    @staticmethod
    def get_accounts(region: str) -> dict[str, str]:
        """Get the accounts for a given region.

        Args:
            region (str): The region name

        Returns:
            dict[str, str]: A dictionary mapping account ids to account names
        """
        return PlatformAPIHandler.get_accounts(region)

    @staticmethod
    def get_projects(region: str, account_id: str) -> dict[str, str]:
        """Get the projects for a given account.

        Args:
            region (str): The region name
            account_id (str): The account ID

        Returns:
            dict[str, str]: A dictionary mapping project IDs to project names
        """
        return PlatformAPIHandler.get_projects(region, account_id)

    @staticmethod
    def create_project(
        region: str,
        account_id: str,
        project_name: str,
        project_id: str = None,
    ) -> dict[str, str]:
        """Create a new project in an account.

        Args:
            region (str): The region name
            account_id (str): The account ID
            project_name (str): The display name for the new project
            project_id (str | None): Optional slug/ID for the project

        Returns:
            dict[str, str]: A dictionary with the created project's 'id' and 'name'
        """
        return PlatformAPIHandler.create_project(region, account_id, project_name, project_id)

    @staticmethod
    def get_deployments(
        region: str, account_id: str, project_id: str, client_env: str = "sandbox"
    ) -> list[dict[str, Any]]:
        """Get the deployments for a given project and client environment.

        Args:
            region (str): The region name
            account_id (str): The account ID
            project_id (str): The project ID
            client_env (str): The client environment (sandbox, pre-release, live)
                defaults to sandbox

        Returns:
            list[dict[str, Any]]: A list of deployment records from the API
        """
        return PlatformAPIHandler.get_deployments(region, account_id, project_id, client_env)

    @staticmethod
    def get_active_deployments(
        region: str, account_id: str, project_id: str
    ) -> dict[str, dict[str, str]]:
        """Get the active deployments for a given project.
        Args:
            region (str): The region name
            account_id (str): The account ID
            project_id (str): The project ID
        Returns:
            dict[str, dict[str, str]]: A dictionary mapping environments to deployment info
        """
        return PlatformAPIHandler.get_active_deployments(region, account_id, project_id)

    def pull_deployment_resources(
        self, deployment_id: str
    ) -> dict[type[Resource], dict[str, Resource]]:
        """Fetch all resources for a specific deployment of a project.
        Args:
            deployment_id (str): The deployment ID
        Returns:
            dict[type[Resource], dict[str, Resource]]: A dictionary mapping resource types to
                their resources
        """
        try:
            return self.sync_client.pull_deployment_resources(deployment_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def pull_resources(
        self, projection_json: Optional[dict[str, Any]] = None
    ) -> tuple[dict[type[Resource], dict[str, Resource]], dict[str, Any]]:
        """Fetch all resources for the specific project.

        Args:
            projection_json (Optional[dict[str, Any]]): A dictionary containing the projection.
                If provided, the projection will be used instead of fetching it from the API.

        Returns:
            dict[type[Resource], dict[str, Resource]]: A dictionary mapping resource types to
                their resources
            dict[str, Any]: The projection data
        """
        if projection_json is not None:
            return SyncClientHandler.load_resources_from_projection(
                projection_json
            ), projection_json
        try:
            return self.sync_client.pull_resources()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def push_resources(
        self,
        deleted_resources: dict[type[BaseResource], dict[str, BaseResource]],
        new_resources: dict[type[BaseResource], dict[str, BaseResource]],
        updated_resources: dict[type[BaseResource], dict[str, BaseResource]],
        dry_run: bool = False,
        queue_pushes: bool = False,
        email: Optional[str] = None,
    ) -> bool:
        """Upload multiple resources for the specific project.

        Args:
            new_resources (dict[type[BaseResource], dict[str, BaseResource]]): New resources to upload
            deleted_resources (dict[type[BaseResource], dict[str, BaseResource]]): Resources to delete
            updated_resources (dict[type[BaseResource], dict[str, BaseResource]]): Updated resources to upload
            dry_run (bool): If True, only log the upload actions without actually
                uploading
            queue_pushes (bool): If True, queue the resources for pushing.
            email (str): Email to use for metadata creation.
                If None, use the email of the current user.

        Returns:
            bool: True if the resources were pushed successfully, False otherwise
        """
        self.queue_resources(
            deleted_resources=deleted_resources,
            new_resources=new_resources,
            updated_resources=updated_resources,
            email=email,
        )

        if queue_pushes:
            return True

        if dry_run:
            self.clear_command_queue()
            return True

        return self.send_queued_commands()

    def queue_resources(
        self,
        deleted_resources: dict[type[BaseResource], dict[str, BaseResource]],
        new_resources: dict[type[BaseResource], dict[str, BaseResource]],
        updated_resources: dict[type[BaseResource], dict[str, BaseResource]],
        email: Optional[str] = None,
    ) -> list[Message]:
        """Queue multiple resources for the specific project.

        Args:
            deleted_resources (dict[type[BaseResource], dict[str, BaseResource]]): Resources to delete
            new_resources (dict[type[BaseResource], dict[str, BaseResource]]): New resources to upload
            updated_resources (dict[type[BaseResource], dict[str, BaseResource]]): Updated resources to upload
            email (str): Email to use for metadata creation.
                If None, use the email of the current user.

        Returns:
            list[Message]: A list of queued Command protobuf messages.
        """
        try:
            return self.sync_client.queue_resources(
                deleted_resources=deleted_resources,
                new_resources=new_resources,
                updated_resources=updated_resources,
                email=email,
            )
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def send_queued_commands(self) -> bool:
        """Send all queued commands as a batch and clear the queue.

        Returns:
            bool: True if the commands were sent successfully, False otherwise
        """
        try:
            return self.sync_client.send_queued_commands()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def clear_command_queue(self) -> None:
        """Clear all queued commands without sending."""
        try:
            self.sync_client.clear_command_queue()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def get_queued_commands(self) -> list[Message]:
        """Get all queued commands.

        Returns:
            list[Message]: A list of queued Command protobuf messages.
        """
        try:
            return self.sync_client.get_queued_commands()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def get_branches(self) -> dict[str, str]:
        """Get a list of branches.

        Args:
            branch_name (str): The name of the branch

        Returns:
            dict[str, str]: A dictionary mapping branch names to branch IDs
        """
        try:
            return self.sync_client.get_branches()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def create_branch(self, branch_name: Optional[str] = None) -> str:
        """Create a new branch in the project.

        Args:
            branch_name (str): The name of the new branch

        Returns:
            str: The ID of the newly created branch
        """
        try:
            return self.sync_client.create_branch(branch_name)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def switch_branch(self, branch_id: str) -> bool:
        """Switch to a different branch in the project.

        Args:
            branch_name (str): The name of the branch to switch to

        Returns:
            bool: True if the branch was switched successfully, False otherwise
        """
        try:
            return self.sync_client.switch_branch(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def merge_branch(
        self, message: str, conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the current branch into main.

        Args:
            message (str): The merge commit message
            conflict_resolutions (list[dict[str, Any]]): A list of conflict resolutions. Each resolution should have:
                - path: List of strings representing the path to the conflicted field (e.g., ["users", "1", "name"])
                - strategy: Resolution strategy - "ours", "theirs", or "base"
                - value: Optional custom value (only used with custom strategy)

        Returns:
            success (bool): True if the merge was successful, False otherwise
            list[dict[str, str]]: A list of conflict information if the merge failed, empty list if successful
            list[dict[str, str]]: A list of error information if the merge failed, empty list if successful
        """
        try:
            return self.sync_client.merge_branch(message, conflict_resolutions)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch in the project.

        Args:
            branch_name (str): The name of the branch to delete

        Returns:
            bool: True if the branch was deleted successfully, False otherwise
        """
        try:
            return self.sync_client.delete_branch(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    @staticmethod
    def create_chat(
        region: str,
        account_id: str,
        project_id: str,
        environment: str = "sandbox",
        variant_id: Optional[str] = None,
        channel: str = "chat.polyai",
        input_lang: Optional[str] = None,
        output_lang: Optional[str] = None,
    ) -> dict:
        """Create a new chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            environment: The environment to chat against (sandbox, pre-release, live)
            variant_id: Optional variant ID (e.g. 'Voice')
            channel: The channel identifier (e.g. 'chat.polyai', 'webchat.polyai')

        Returns:
            dict: The API response containing the conversation ID and initial greeting
        """
        return PlatformAPIHandler.create_chat(
            region,
            account_id,
            project_id,
            environment,
            variant_id,
            channel,
            input_lang=input_lang,
            output_lang=output_lang,
        )

    @staticmethod
    def send_chat_message(
        region: str,
        account_id: str,
        project_id: str,
        conversation_id: str,
        text: str,
        environment: str = "sandbox",
        input_lang: str = None,
        output_lang: str = None,
    ) -> dict:
        """Send a message to an existing chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            conversation_id: The conversation ID
            text: The user message text
            environment: The environment (sandbox, pre-release, live)

        Returns:
            dict: The API response containing the assistant's reply
        """
        return PlatformAPIHandler.send_chat_message(
            region,
            account_id,
            project_id,
            conversation_id,
            text,
            environment,
            input_lang=input_lang,
            output_lang=output_lang,
        )

    def get_branch_chat_info(self, branch_id: str) -> dict:
        """Get deployment versions needed to start a draft chat on a branch.

        Fetches the branch projection sequence from sourcerer, then
        prepares the deployment to obtain artifactVersion and
        lambdaDeploymentVersion.

        Args:
            branch_id: The branch ID

        Returns:
            dict with 'artifactVersion', 'lambdaDeploymentVersion', etc.
        """
        try:
            return self.sync_client.get_branch_chat_info(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    @staticmethod
    def create_draft_chat(
        region: str,
        account_id: str,
        project_id: str,
        artifact_version: str,
        lambda_deployment_version: str,
        channel: str = "chat.polyai",
        variant_id: Optional[str] = None,
        input_lang: str = None,
        output_lang: str = None,
    ) -> dict:
        """Create a new chat conversation against a branch deployment.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            artifact_version: Branch artifact version from sourcerer
            lambda_deployment_version: Branch lambda version from sourcerer
            channel: The channel identifier (e.g. 'chat.polyai', 'webchat.polyai')
            variant_id: Optional variant ID (e.g. 'Voice')

        Returns:
            dict: The API response containing the conversation ID and initial greeting
        """
        return PlatformAPIHandler.create_draft_chat(
            region,
            account_id,
            project_id,
            artifact_version,
            lambda_deployment_version,
            channel,
            variant_id,
            input_lang=input_lang,
            output_lang=output_lang,
        )

    @staticmethod
    def send_draft_chat_message(
        region: str,
        account_id: str,
        project_id: str,
        conversation_id: str,
        text: str,
        input_lang: str = None,
        output_lang: str = None,
    ) -> dict:
        """Send a message to an existing draft chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            conversation_id: The conversation ID
            text: The user message text

        Returns:
            dict: The API response containing the assistant's reply
        """
        return PlatformAPIHandler.send_draft_chat_message(
            region,
            account_id,
            project_id,
            conversation_id,
            text,
            input_lang=input_lang,
            output_lang=output_lang,
        )

    @staticmethod
    def end_chat(
        region: str,
        account_id: str,
        project_id: str,
        conversation_id: str,
        environment: str = "sandbox",
    ) -> dict:
        """End a chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            conversation_id: The conversation ID
            environment: The environment (sandbox, pre-release, live)

        Returns:
            dict: The API response
        """
        return PlatformAPIHandler.end_chat(
            region, account_id, project_id, conversation_id, environment
        )

    @staticmethod
    def promote_deployment(
        region: str, project_id: str, deployment_id: str, target_env: str, message: str
    ) -> dict:
        """Promote a deployment to the next environment.

        Args:
            region: The region name
            project_id: The project ID
            deployment_id: The deployment ID
            target_env: The target environment to promote to (pre-release or live)
            message: Message to include with the promotion

        Returns:
            dict: The API response
        """
        return PlatformAPIHandler.promote_deployment(
            region, project_id, deployment_id, target_env, message
        )

    @staticmethod
    def rollback_deployment(region: str, project_id: str, deployment_id: str, message: str) -> dict:
        """Rollback a deployment to the previous environment.

        Args:
            region: The region name
            project_id: The project ID
            deployment_id: The deployment ID
            message: Message to include with the rollback

        Returns:
            dict: The API response
        """
        return PlatformAPIHandler.rollback_deployment(region, project_id, deployment_id, message)
