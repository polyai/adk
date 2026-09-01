"""API Handler Interface for Agent Studio

Copyright PolyAI Limited"""

import json
import uuid
from typing import Any, NoReturn, Optional

import requests
from google.protobuf.message import Message

from poly.handlers.platform_api import PlatformAPIHandler
from poly.handlers.posthog import PosthogHandler
from poly.handlers.protobuf.commands_pb2 import Command
from poly.handlers.sdk import SourcererAPIError
from poly.handlers.sync_client import SyncClientHandler
from poly.resources import (
    ApiIntegration,
    BaseResource,
    Condition,
    Entity,
    FlowConfig,
    FlowStep,
    Function,
    FunctionStep,
    Handoff,
    ResourceMap,
    ResourceMapping,
    SMSTemplate,
    Variable,
    Variant,
    VariantAttribute,
)

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
    def get_project(region: str, account_id: str, project_id: str) -> dict[str, Any]:
        """Get the details of a specific project.

        Args:
            region (str): The region name
            account_id (str): The account ID
            project_id (str): The project ID

        Returns:
            dict[str, Any]: A dictionary containing the project's details
        """
        return PlatformAPIHandler.get_project(region, account_id, project_id)

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
        greeting: str = "Hello, how can I help you?",
        voice_id: str | None = None,
    ) -> dict[str, str]:
        """Create a new project in an account.

        Args:
            region (str): The region name
            account_id (str): The account ID
            project_name (str): The display name for the new project
            project_id (str | None): Optional slug/ID for the project
            greeting (str): The initial greeting message for the agent.
            voice_id (str | None): The voice ID to use.

        Returns:
            dict[str, str]: A dictionary with the created project's 'id' and 'name'
        """
        return PlatformAPIHandler.create_project(
            region, account_id, project_name, project_id, greeting, voice_id
        )

    @staticmethod
    def get_agents(region: str, account_id: str) -> dict[str, str]:
        """Get agents for an account via the public Agents API.

        Args:
            region (str): The region name
            account_id (str): The account ID

        Returns:
            dict[str, str]: A dictionary mapping agent IDs (slugs) to agent names
        """
        return PlatformAPIHandler.get_agents(region, account_id)

    @staticmethod
    def list_agents(region: str, account_id: str) -> list[dict[str, Any]]:
        """List agents for an account via the public Agents API.

        Args:
            region (str): The region name
            account_id (str): The account ID

        Returns:
            list[dict[str, Any]]: Raw agent records from the API.
        """
        return PlatformAPIHandler.list_agents(region, account_id)

    @staticmethod
    def delete_project(region: str, project_id: str) -> None:
        """Delete a project (agent).

        Args:
            region (str): The region name
            project_id (str): The project ID (slug) to delete
        """
        PlatformAPIHandler.delete_project(region, project_id)

    @staticmethod
    def duplicate_project(
        region: str,
        project_id: str,
        new_name: str,
        new_id: str | None = None,
    ) -> dict[str, str]:
        """Duplicate a project (agent).

        Args:
            region (str): The region name
            project_id (str): The project ID (slug) to duplicate
            new_name (str): The display name for the new project
            new_id (str | None): Optional slug/ID for the new project.
                When omitted the platform generates one automatically.

        Returns:
            dict[str, str]: A dictionary with the new project's 'id' and 'name'
        """
        return PlatformAPIHandler.duplicate_project(region, project_id, new_name, new_id)

    @staticmethod
    def list_template_projects(region: str) -> list[dict[str, Any]]:
        """List available template projects.

        Args:
            region: The region to query.

        Returns:
            list[dict[str, Any]]: A list of template project summaries.
        """
        return SyncClientHandler(region=region).list_template_projects()

    @staticmethod
    def get_template_resources(
        template_id: str, region: str
    ) -> tuple[ResourceMap, list[ResourceMapping]]:
        """Fetch a template and return its resources.

        Combines projection fetching and resource conversion in one call.

        Args:
            template_id: The template project ID.
            region: The region to query.

        Returns:
            tuple[ResourceMap, list[ResourceMapping]]: A tuple containing:
                1. A dictionary mapping resource types to their resources.
                2. A list of slim resources.
        """
        from poly.resources.resource import load_resources_from_projection

        projection = SyncClientHandler(region=region).get_template_project_projection(template_id)
        return load_resources_from_projection(projection)

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
    ) -> tuple[ResourceMap, list[ResourceMapping]]:
        """Fetch all resources for a specific deployment of a project.

        Args:
            deployment_id (str): The deployment ID

        Returns:
            tuple[ResourceMap, list[ResourceMapping]]: A tuple containing:
                1. A dictionary mapping resource types to their resources.
                2. A list of slim resources.

        """
        from poly.resources.resource import load_resources_from_projection

        try:
            projection = self.sync_client.pull_deployment_projection(deployment_id)
            return load_resources_from_projection(projection)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def pull_resources(
        self, projection_json: Optional[dict[str, Any]] = None
    ) -> tuple[ResourceMap, list[ResourceMapping], dict[str, Any]]:
        """Fetch all resources for the specific project.

        Args:
            projection_json (Optional[dict[str, Any]]): A dictionary containing the projection.
                If provided, the projection will be used instead of fetching it from the API.

        Returns:
            tuple[ResourceMap, list[ResourceMapping], dict[str, Any]]: A tuple containing:
                1. A dictionary mapping resource types to their resources.
                2. A list of slim resources.
                3. The projection JSON.
        """
        from poly.resources.resource import load_resources_from_projection

        if projection_json is not None:
            resources, slim_resources = load_resources_from_projection(projection_json)
            return resources, slim_resources, projection_json
        try:
            projection = self.sync_client.pull_projection()
            resources, slim_resources = load_resources_from_projection(projection)
            return resources, slim_resources, projection
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def push_resources(
        self,
        deleted_resources: dict[type[BaseResource], dict[str, BaseResource]],
        new_resources: dict[type[BaseResource], dict[str, BaseResource]],
        updated_resources: dict[type[BaseResource], dict[str, BaseResource]],
        dry_run: bool = False,
        queue_pushes: bool = False,
    ) -> bool:
        """Upload multiple resources for the specific project.

        Args:
            new_resources (dict[type[BaseResource], dict[str, BaseResource]]): New resources to upload
            deleted_resources (dict[type[BaseResource], dict[str, BaseResource]]): Resources to delete
            updated_resources (dict[type[BaseResource], dict[str, BaseResource]]): Updated resources to upload
            dry_run (bool): If True, only log the upload actions without actually
                uploading
            queue_pushes (bool): If True, queue the resources for pushing.

        Returns:
            bool: True if the resources were pushed successfully, False otherwise
        """
        self.queue_resources(
            deleted_resources=deleted_resources,
            new_resources=new_resources,
            updated_resources=updated_resources,
        )

        if queue_pushes:
            return True

        if dry_run:
            self.clear_command_queue()
            return True

        return self.send_queued_commands()

    # Types that should be created first as they are referenced by other resources
    PRIORITY_CREATE_TYPES = [
        Variable,
        Entity,
        Variant,
        VariantAttribute,
        SMSTemplate,
        Handoff,
        Function,
        FlowConfig,
        FunctionStep,
        FlowStep,
        Condition,
        ApiIntegration,
    ]

    PRIORITY_DELETE_TYPES = [
        Variable,
        Condition,
    ]

    PRIORITY_UPDATE_TYPES = [
        Variable,
    ]

    @staticmethod
    def _prioritised(
        resources: dict[type[BaseResource], dict[str, BaseResource]],
        priority: list[type[BaseResource]],
    ) -> list[type[BaseResource]]:
        """Return resource types ordered by priority list, then remaining types."""
        ordered = [rt for rt in priority if rt in resources]
        ordered.extend(rt for rt in resources if rt not in priority)
        return ordered

    def queue_resources(
        self,
        deleted_resources: dict[type[BaseResource], dict[str, BaseResource]],
        new_resources: dict[type[BaseResource], dict[str, BaseResource]],
        updated_resources: dict[type[BaseResource], dict[str, BaseResource]],
    ) -> list[Message]:
        """Build and queue protobuf commands from resource dicts.

        Produces commands in order: delete, create, update — each respecting
        priority ordering so that referenced resources are created first and
        dependents are deleted first.

        Args:
            deleted_resources: Resources to delete.
            new_resources: New resources to create.
            updated_resources: Updated resources to upload.

        Returns:
            list[Message]: A list of queued Command protobuf messages.
        """
        try:
            metadata = self.sync_client.sdk.create_metadata()
            commands: list[Command] = []

            for resource_type in self._prioritised(deleted_resources, self.PRIORITY_DELETE_TYPES):
                for resource in deleted_resources.get(resource_type, {}).values():
                    delete_type = resource.delete_command_type
                    commands.append(
                        Command(
                            type=delete_type,
                            command_id=str(uuid.uuid4()),
                            metadata=metadata,
                            **{delete_type: resource.build_delete_proto()},
                        )
                    )

            for resource_type in self._prioritised(new_resources, self.PRIORITY_CREATE_TYPES):
                for resource in new_resources.get(resource_type, {}).values():
                    create_type = resource.create_command_type
                    commands.append(
                        Command(
                            type=create_type,
                            command_id=str(uuid.uuid4()),
                            metadata=metadata,
                            **{create_type: resource.build_create_proto()},
                        )
                    )

            for resource_type in self._prioritised(updated_resources, self.PRIORITY_UPDATE_TYPES):
                for resource in updated_resources.get(resource_type, {}).values():
                    update_type = resource.update_command_type
                    commands.append(
                        Command(
                            type=update_type,
                            command_id=str(uuid.uuid4()),
                            metadata=metadata,
                            **{update_type: resource.build_update_proto()},
                        )
                    )

            for command in commands:
                self.sync_client.sdk.add_command_to_queue(command)

            return commands
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def queue_command(self, command: Message) -> None:
        """Queue a single command for the specific project.

        Args:
            command (Message): The Command protobuf message to queue
        """
        try:
            self.sync_client.queue_command(command)
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

    def get_branches(self) -> dict[str, dict[str, Any]]:
        """Get a list of branches with full metadata.

        Returns:
            A dictionary mapping branch names to their metadata dicts.
            Each value contains at least ``branchId``, and may include
            ``parentBranchId``, ``parentSequence``, ``isDiverged``, etc.
        """
        try:
            return self.sync_client.get_branches()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def create_branch(
        self, branch_name: Optional[str] = None, source_branch_id: Optional[str] = None
    ) -> str:
        """Create a new branch in the project.

        Args:
            branch_name (str): The name of the new branch
            source_branch_id (str): The ID of the source branch to create the new branch from. Defaults to 'main' if not provided.

        Returns:
            str: The ID of the newly created branch
        """
        try:
            return self.sync_client.create_branch(branch_name, source_branch_id=source_branch_id)
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
        self, message: Optional[str], conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Merge the current branch into main.

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
        try:
            return self.sync_client.merge_branch(message, conflict_resolutions)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def sync_branch(
        self, conflict_resolutions: Optional[list[dict[str, Any]]] = None
    ) -> tuple[bool, list[dict[str, str]], list[dict[str, str]]]:
        """Sync the current branch with it's parent.

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
        try:
            return self.sync_client.sync_branch(conflict_resolutions)
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

    def pull_branch_resources(
        self, branch_id: str, at_sequence: Optional[int] = None
    ) -> tuple[ResourceMap, list[ResourceMapping]]:
        """Fetch resources for a branch, optionally at a historical sequence.

        Args:
            branch_id: The branch whose projection to fetch.
            at_sequence: When provided, fetches the projection at this sequence number.

        Returns:
            tuple[ResourceMap, list[ResourceMapping]]: A tuple containing:
                1. A dictionary mapping resource types to their resources.
                2. A list of slim resources.
        """
        from poly.resources.resource import load_resources_from_projection

        try:
            projection = self.sync_client.pull_branch_projection(branch_id, at_sequence)
            return load_resources_from_projection(projection)
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
        sip_headers: Optional[dict[str, str]] = None,
    ) -> dict:
        """Create a new chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            environment: The environment to chat against (sandbox, pre-release, live)
            variant_id: Optional variant ID (e.g. 'Voice')
            channel: The channel identifier (e.g. 'chat.polyai', 'webchat.polyai')
            sip_headers: Optional simulated SIP headers exposed through conv.sip_headers

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
            sip_headers=sip_headers,
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
        sip_headers: Optional[dict[str, str]] = None,
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
            sip_headers: Optional simulated SIP headers exposed through conv.sip_headers

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
            sip_headers=sip_headers,
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

    @staticmethod
    def create_ab_test(
        region: str,
        account_id: str,
        project_id: str,
        name: str,
        variant_deployment_id: str,
        traffic_percentage: int,
    ) -> dict:
        """Create a new A/B test.

        Args:
            region: The region name.
            account_id: The account ID.
            project_id: The project ID.
            name: Display name for the A/B test.
            variant_deployment_id: ID of the pre-release variant deployment.
            traffic_percentage: Percentage of traffic routed to variant (0-100).

        Returns:
            dict: The created A/B test record.
        """
        return PlatformAPIHandler.create_ab_test(
            region, account_id, project_id, name, variant_deployment_id, traffic_percentage
        )

    @staticmethod
    def list_ab_tests(
        region: str,
        account_id: str,
        project_id: str,
        limit: Optional[int] = None,
    ) -> dict:
        """List A/B tests for a project.

        Args:
            region: The region name.
            account_id: The account ID.
            project_id: The project ID.
            limit: Maximum number of tests to return.

        Returns:
            dict: Response containing an ``ab_tests`` list.
        """
        return PlatformAPIHandler.list_ab_tests(region, account_id, project_id, limit)

    @staticmethod
    def get_active_ab_test(
        region: str,
        account_id: str,
        project_id: str,
    ) -> dict:
        """Get the active A/B test for a project.

        Args:
            region: The region name.
            account_id: The account ID.
            project_id: The project ID.

        Returns:
            dict: The active A/B test record, or empty dict if none.
        """
        return PlatformAPIHandler.get_active_ab_test(region, account_id, project_id)

    @staticmethod
    def end_ab_test(
        region: str,
        account_id: str,
        project_id: str,
        ab_test_id: str,
        chosen_deployment_id: str,
    ) -> dict:
        """End an A/B test and choose a winner.

        Args:
            region: The region name.
            account_id: The account ID.
            project_id: The project ID.
            ab_test_id: The A/B test ID.
            chosen_deployment_id: Deployment ID to keep (control or variant).

        Returns:
            dict: The ended A/B test record.
        """
        return PlatformAPIHandler.end_ab_test(
            region, account_id, project_id, ab_test_id, chosen_deployment_id
        )

    @staticmethod
    def update_ab_test(
        region: str,
        account_id: str,
        project_id: str,
        ab_test_id: str,
        traffic_percentage: int,
    ) -> dict:
        """Update traffic percentage for an A/B test.

        Args:
            region: The region name.
            account_id: The account ID.
            project_id: The project ID.
            ab_test_id: The A/B test ID.
            traffic_percentage: New traffic percentage (0-100).

        Returns:
            dict: The updated A/B test record.
        """
        return PlatformAPIHandler.update_ab_test(
            region, account_id, project_id, ab_test_id, traffic_percentage
        )

    @staticmethod
    def authorise(region: str, jwt_token: str) -> dict:
        """Authorise the user via JWT, creating their account if needed.

        Args:
            region: The region name.
            jwt_token: A valid JWT access token.

        Returns:
            dict: The user record.
        """
        return PlatformAPIHandler.authorise(region, jwt_token)

    @staticmethod
    def get_pats(region: str, jwt_token: str) -> list[dict]:
        """Get all Personal Access Tokens for the authenticated user.

        Args:
            region: The region name
            jwt_token: The user's JWT access token

        Returns:
            list[dict]: List of PAT records.
        """
        return PlatformAPIHandler.get_pats_internal(region, jwt_token)

    @staticmethod
    def create_pat(region: str, jwt_token: str, name: str) -> str:
        """Create a new Personal Access Token (PAT) for the user.

        Args:
            region: The region name
            jwt_token: The user's JWT access token
            name: A name for the new PAT

        Returns:
            str: The newly created PAT token
        """
        return PlatformAPIHandler.create_pat_internal(region, jwt_token, name)

    @staticmethod
    def list_conversations(
        region: str,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """List conversations for a project.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            limit: Max number of conversations to return.
            offset: Number of conversations to skip.

        Returns:
            dict: The API response with conversations, count, limit, offset.
        """
        return PlatformAPIHandler.list_conversations(region, project_id, limit, offset)

    @staticmethod
    def get_conversation(
        region: str,
        project_id: str,
        conversation_id: str,
    ) -> dict:
        """Get a conversation by ID.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            conversation_id: The conversation ID.

        Returns:
            dict: The conversation detail response.
        """
        return PlatformAPIHandler.get_conversation(region, project_id, conversation_id)

    @staticmethod
    def get_conversation_audio(
        region: str,
        project_id: str,
        conversation_id: str,
        direction: str = "combined",
        redacted: bool = False,
    ) -> bytes:
        """Get audio recording for a conversation.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            conversation_id: The conversation ID.
            direction: Audio direction — combined, user, or agent.
            redacted: Whether to return redacted audio.

        Returns:
            bytes: The raw WAV audio data.
        """
        return PlatformAPIHandler.get_conversation_audio(
            region, project_id, conversation_id, direction, redacted
        )

    @staticmethod
    def list_audio_cache(
        region: str,
        project_id: str,
        limit: int = 50,
        offset: int = 0,
        sort: Optional[str] = None,
    ) -> dict:
        """List cached TTS audio entries for an agent.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            limit: Max entries to return (1-200).
            offset: Pagination offset.
            sort: Optional sort expression, e.g. "hit_count:desc".

        Returns:
            dict: The API response with entries and total_count.
        """
        return PlatformAPIHandler.list_audio_cache(region, project_id, limit, offset, sort)

    @staticmethod
    def get_audio_cache_file(region: str, project_id: str, entry_id: str) -> bytes:
        """Download the cached audio file for an audio cache entry.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            entry_id: The audio cache entry ID.

        Returns:
            bytes: The raw WAV audio data.
        """
        return PlatformAPIHandler.get_audio_cache_file(region, project_id, entry_id)

    @staticmethod
    def update_audio_cache_file(
        region: str,
        project_id: str,
        entry_id: str,
        audio_bytes: bytes,
        filename: Optional[str] = None,
    ) -> None:
        """Replace the audio file for an existing cache entry.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            entry_id: The audio cache entry ID.
            audio_bytes: Raw WAV audio bytes (max 6MB).
            filename: Optional filename, sent via the X-Filename header.
        """
        PlatformAPIHandler.update_audio_cache_file(
            region, project_id, entry_id, audio_bytes, filename
        )

    @staticmethod
    def update_audio_cache_details(
        region: str,
        project_id: str,
        entry_id: str,
        audio_bytes: bytes,
        settings: dict,
        filename: str = "audio.wav",
    ) -> None:
        """Replace both the audio file and voice tuning settings for a cache entry.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            entry_id: The audio cache entry ID.
            audio_bytes: Raw WAV audio bytes (max 6MB).
            settings: Dict with "text" and "config" keys (voice tuning settings).
            filename: Filename to use for the multipart file part.
        """
        PlatformAPIHandler.update_audio_cache_details(
            region, project_id, entry_id, audio_bytes, settings, filename
        )

    @staticmethod
    def delete_audio_cache_entry(region: str, project_id: str, entry_id: str) -> dict:
        """Delete a cached audio entry and its associated audio file.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            entry_id: The audio cache entry ID.

        Returns:
            dict: The API response, e.g. {"success": True}.
        """
        return PlatformAPIHandler.delete_audio_cache_entry(region, project_id, entry_id)

    @staticmethod
    def bulk_delete_audio_cache(region: str, project_id: str, ids: list[str]) -> dict:
        """Delete multiple audio cache entries by ID in a single request.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            ids: List of audio cache entry IDs to delete (max 20).

        Returns:
            dict: The API response with "deleted" and "failed" ID lists.
        """
        return PlatformAPIHandler.bulk_delete_audio_cache(region, project_id, ids)

    @staticmethod
    def synthesize_audio_cache(
        region: str,
        project_id: str,
        entry_id: str,
        text: str,
        config: dict,
        language: Optional[str] = None,
    ) -> bytes:
        """Generate a TTS audio preview using an existing cache entry's voice config.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            entry_id: The audio cache entry ID whose voice/provider config to use.
            text: Text to synthesize.
            config: Provider-specific voice tuning settings.
            language: Optional BCP-47 language tag, e.g. "en-US".

        Returns:
            bytes: The raw WAV audio data (preview only, not saved to cache).
        """
        return PlatformAPIHandler.synthesize_audio_cache(
            region, project_id, entry_id, text, config, language
        )

    @staticmethod
    def list_test_runs(
        region: str,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
        test_set_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> dict:
        """List test runs for a project.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            limit: Max number of test runs to return.
            offset: Number of test runs to skip.
            test_set_id: Optional filter by test set ID.
            branch_id: Optional filter by branch ID.

        Returns:
            dict: The API response with test runs.
        """
        return PlatformAPIHandler.list_test_runs(
            region, project_id, limit, offset, test_set_id, branch_id
        )

    @staticmethod
    def get_test_run(
        region: str,
        project_id: str,
        test_run_id: str,
    ) -> dict:
        """Get a single test run by ID, including nested test history.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            test_run_id: The test run ID.

        Returns:
            dict: The test run detail response.
        """
        return PlatformAPIHandler.get_test_run(region, project_id, test_run_id)

    @staticmethod
    def list_test_history(
        region: str,
        project_id: str,
        limit: int = 100,
        offset: int = 0,
        test_case_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> dict:
        """List test execution history for a project.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            limit: Max number of history entries to return.
            offset: Number of history entries to skip.
            test_case_id: Optional filter by test case ID.
            branch_id: Optional filter by branch ID.

        Returns:
            dict: The API response with test history.
        """
        return PlatformAPIHandler.list_test_history(
            region, project_id, limit, offset, test_case_id, branch_id
        )

    @staticmethod
    def trigger_test_run(
        region: str,
        project_id: str,
        test_case_ids: list[str],
        branch_id: str,
    ) -> dict:
        """Trigger a test run for a project.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            test_case_ids: List of test case IDs to run.
            branch_id: The branch ID to run tests against.

        Returns:
            dict: The created test run response.
        """
        return PlatformAPIHandler.trigger_test_run(region, project_id, test_case_ids, branch_id)

    @staticmethod
    def list_rtc_configs(
        region: str,
        project_id: str,
    ) -> dict:
        """List all RTC config pages for a project.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).

        Returns:
            dict: The API response with all RTC configs.
        """
        return PlatformAPIHandler.list_rtc_configs(region, project_id)

    @staticmethod
    def get_rtc_config(
        region: str,
        project_id: str,
        client_env: str,
    ) -> dict:
        """Get RTC config for a specific environment.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            client_env: The environment (sandbox, pre-release, live).

        Returns:
            dict: The RTC config with schema, variables, clientEnv, lastUpdated.
        """
        return PlatformAPIHandler.get_rtc_config(region, project_id, client_env)

    @staticmethod
    def put_rtc_schema(
        region: str,
        project_id: str,
        client_env: str,
        schema: dict,
    ) -> dict:
        """Update the RTC schema for an environment.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            client_env: The environment (sandbox, pre-release, live).
            schema: The JSON Schema Draft 7 object.

        Returns:
            dict: The updated RTC config.
        """
        return PlatformAPIHandler.put_rtc_schema(region, project_id, client_env, schema)

    @staticmethod
    def patch_rtc_variables(
        region: str,
        project_id: str,
        client_env: str,
        variables: dict,
    ) -> dict:
        """Update the RTC variables (data) for an environment.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            client_env: The environment (sandbox, pre-release, live).
            variables: The config variables object.

        Returns:
            dict: The updated RTC config.
        """
        return PlatformAPIHandler.patch_rtc_variables(region, project_id, client_env, variables)

    # -- Functions API ------------------------------------------------------
    # Public REST API for managing/executing user-defined Functions. Distinct
    # from the local-file/decorator Functions synced via push/pull.

    @staticmethod
    def list_functions(region: str, project_id: str, branch_id: str) -> list[dict]:
        """List a branch's active functions.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            branch_id: The branch ID.

        Returns:
            list[dict]: The branch's active functions, each with "id" and "name".
        """
        return PlatformAPIHandler.list_functions(region, project_id, branch_id)

    @staticmethod
    def execute_function(
        region: str,
        project_id: str,
        branch_id: str,
        function_id: str,
        args: dict,
    ) -> dict:
        """Execute a function with the given arguments.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            branch_id: The branch ID.
            function_id: The function ID.
            args: The arguments to pass to the function.

        Returns:
            dict: {"body": ..., "logs": [...], "runtime": ...}.
        """
        return PlatformAPIHandler.execute_function(region, project_id, branch_id, function_id, args)

    @staticmethod
    def validate_functions(region: str, project_id: str, branch_id: str) -> dict:
        """Validate all functions on a branch.

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            branch_id: The branch ID.

        Returns:
            dict: {"valid": bool, "issues": [...]}.
        """
        return PlatformAPIHandler.validate_functions(region, project_id, branch_id)

    def get_branch_history(self, branch_id: str) -> list[dict[str, Any]]:
        """Get the history of a specific branch.

        Args:
            branch_id (str): The ID of the branch

        Returns:
            list[dict[str, Any]]: A list of commit history entries for the branch
        """
        try:
            return self.sync_client.get_branch_history(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def rename_branch(self, new_branch_name: str) -> bool:
        """Rename the current branch to a new name.

        Args:
            new_branch_name (str): The new name for the current branch

        Returns:
            bool: True if the branch was renamed successfully, False otherwise
        """
        try:
            return self.sync_client.rename_branch(new_branch_name)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def list_archived_branches(self) -> list[dict[str, Any]]:
        """List soft-deleted (archived) branches for the project.

        Returns:
            list[dict[str, Any]]: A list of archived branch entries.
        """
        try:
            return self.sync_client.list_archived_branches()
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def restore_branch(self, branch_id: str) -> bool:
        """Restore a soft-deleted branch from the archive.

        Args:
            branch_id (str): The ID of the branch to restore.

        Returns:
            bool: True if the branch was restored successfully, False otherwise.
        """
        try:
            return self.sync_client.restore_branch(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def tag_branch(self, branch_id: str) -> bool:
        """Tag the current branch with a specific tag name.

        Args:
            branch_id (str): The ID of the branch to tag.

        Returns:
            bool: True if the branch was tagged successfully, False otherwise.
        """
        try:
            return self.sync_client.tag_branch(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def untag_branch(self, branch_id: str) -> bool:
        """Remove a specific tag from the current branch.

        Args:
            branch_id (str): The ID of the branch to untag.

        Returns:
            bool: True if the branch was untagged successfully, False otherwise.
        """
        try:
            return self.sync_client.untag_branch(branch_id)
        except (requests.HTTPError, SourcererAPIError) as e:
            self._handle_api_error(e)

    def feature_flag_enabled(
        self,
        key: str,
        identity: Optional[str] = None,
        region: Optional[str] = None,
        project_id: Optional[str] = None,
        default: bool = False,
    ) -> bool:
        """Check if a feature flag is enabled for a given identity.

        Args:
            key (str): The feature flag key to check.
            identity (Optional[str]): The unique identifier for the user or entity.
            region (Optional[str]): The region name for grouping.
            project_id (Optional[str]): The project ID for grouping.
            default (bool): The default value to return if the flag cannot be evaluated.

        Returns:
            bool: True if the feature flag is enabled, False otherwise.
        """
        return PosthogHandler.is_feature_enabled(
            region=region,
            key=key,
            default=default,
            project_id=project_id,
        )
