"""Client for the Agent Studio Platform API

Copyright PolyAI Limited
"""

import json
import logging
import os
import typing as ty
import uuid

import requests

logger = logging.getLogger(__name__)

ACCOUNTS_URL = "/adk/v1/accounts"
PROJECTS_URL = "/adk/v1/accounts/{account_id}/projects"
DEPLOYMENTS_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/deployments"
ACTIVE_DEPLOYMENTS_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/deployments/active"
CHAT_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/chat"
CHAT_CONVERSATION_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/chat/{conversation_id}"
DRAFT_CHAT_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/draft/chat"
DRAFT_CHAT_CONVERSATION_URL = (
    "/adk/v1/accounts/{account_id}/projects/{project_id}/draft/chat/{conversation_id}"
)
CHAT_END_URL = "/adk/v1/accounts/{account_id}/projects/{project_id}/chat/{conversation_id}/end"
PROMOTE_URL = "/v1/agents/{project_id}/deployments/{deploymentId}/promote"
ROLLBACK_URL = "/v1/agents/{project_id}/deployments/{deploymentId}/rollback"


class PlatformAPIHandler:
    """Class for interacting with the Platform API"""

    region_to_base_url = {
        "dev": "https://api.dev.poly.ai",
        "staging": "https://api.staging.poly.ai",
        "euw-1": "https://api.eu.poly.ai",
        "uk-1": "https://api.uk.poly.ai",
        "us-1": "https://api.us.poly.ai",
    }

    @staticmethod
    def get_base_url(region: str) -> str:
        """Get the base URL for the Platform API based on the region.

        Args:
            region (str): The region name
        Returns:
            str: The base URL for the Platform API
        """
        if base_url := PlatformAPIHandler.region_to_base_url.get(region):
            return base_url
        raise ValueError(f"Unknown region: {region}")

    @staticmethod
    def _retrieve_api_key() -> str:
        """Get API key from environment"""
        try:
            return os.getenv("POLY_ADK_KEY")
        except Exception:
            raise ValueError("POLY_ADK_KEY environment variable is required")

    @staticmethod
    def make_request(
        region: str,
        endpoint: str,
        method: str = "GET",
        data: ty.Optional[dict] = None,
        params: ty.Optional[dict] = None,
    ) -> dict:
        """Make a request to the Platform API.

        Args:
            region (str): The region name
            endpoint (str): The API endpoint
            method (str): The HTTP method
            data (dict | None): The request body for POST/PUT requests
            params (dict | None): Query string parameters

        Returns:
            dict: The response JSON
        """
        url = PlatformAPIHandler.get_base_url(region) + endpoint
        correlation_id = f"adk-{uuid.uuid4()}"

        headers = {
            "X-API-KEY": PlatformAPIHandler._retrieve_api_key(),
            "X-PolyAI-Correlation-Id": correlation_id,
            "Content-Type": "application/json",
        }

        logger.info(f"Making {method} request to {url}")

        # Use requests.request() to handle all HTTP methods uniformly
        api_response = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            allow_redirects=False,
            data=json.dumps(data) if data else None,
        )

        logger.debug(
            f"Request/response url={url!r} body={data!r}"
            f" status_code={api_response.status_code!r} response={api_response.text!r}"
        )

        try:
            api_response.raise_for_status()
        except requests.HTTPError:
            logger.debug(
                f"Error in request status_code={api_response.status_code!r} response={api_response.text!r}"
            )
            raise

        try:
            api_response = api_response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")

        logger.info(f"Request to {url} successful")
        return api_response

    @staticmethod
    def get_accounts(region: str) -> dict[str, str]:
        """Get the accounts for a given region.

        Args:
            region (str): The region name

        Returns:
            dict[str, str]: A dictionary mapping account names to account IDs
        """
        accounts = {}
        accounts_data = PlatformAPIHandler.make_request(region, ACCOUNTS_URL, "GET")

        if not isinstance(accounts_data, list):
            raise ValueError("Expected a list of accounts")

        for account in accounts_data:
            if account.get("active", False) and account.get("id") and account.get("name"):
                accounts[account.get("name")] = account.get("id")

        return accounts

    @staticmethod
    def get_projects(region: str, account_id: str) -> dict[str, str]:
        """Get the projects for a given account.

        Args:
            region (str): The region name
            account_id (str): The account ID

        Returns:
            dict[str, str]: A dictionary mapping project names to project IDs
        """
        projects = {}
        endpoint = PROJECTS_URL.format(account_id=account_id)
        projects_data = PlatformAPIHandler.make_request(region, endpoint, "GET")
        projects_list = projects_data.get("projects", [])

        if not isinstance(projects_list, list):
            raise ValueError("Expected a list of projects")

        for project in projects_list:
            if project.get("id") and project.get("name"):
                projects[project.get("name")] = project.get("id")

        return projects

    @staticmethod
    def get_deployments(
        region: str, account_id: str, project_id: str, client_env: str = "sandbox"
    ) -> list[dict[str, ty.Any]]:
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
        endpoint = DEPLOYMENTS_URL.format(account_id=account_id, project_id=project_id)

        deployments_data = PlatformAPIHandler.make_request(
            region, endpoint, "GET", data=None, params={"client_env": client_env}
        )
        deployments_list = deployments_data.get("deployments", [])

        return deployments_list

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
        endpoint = ACTIVE_DEPLOYMENTS_URL.format(account_id=account_id, project_id=project_id)

        deployments_data = PlatformAPIHandler.make_request(region, endpoint, "GET")

        return deployments_data

    @staticmethod
    def create_chat(
        region: str,
        account_id: str,
        project_id: str,
        environment: str = "sandbox",
        variant_id: ty.Optional[str] = None,
        channel: str = "chat.polyai",
        input_lang: ty.Optional[str] = None,
        output_lang: ty.Optional[str] = None,
    ) -> dict:
        """Create a new chat conversation.

        Args:
            region: The region name
            account_id: The account ID
            project_id: The project ID
            environment: The environment to chat against (sandbox, pre-release, live)
            variant_id: Optional variant ID (e.g. 'Voice')
            channel: The channel identifier (e.g. 'chat.polyai', 'webchat.polyai')
            input_lang: Optional language code of the input message, e.g. "en-GB" or "fr-FR"
            output_lang: Optional language code for the agent's response,

        Returns:
            dict: The API response containing the conversation ID
        """
        endpoint = CHAT_URL.format(account_id=account_id, project_id=project_id)
        data = {
            "client_env": environment,
            "channel": channel,
        }
        if variant_id:
            data["variant_id"] = variant_id
        if input_lang:
            data["asr_lang_code"] = input_lang
        if output_lang:
            data["tts_lang_code"] = output_lang
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

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
            input_lang: Optional language code of the input message, e.g. "en-GB" or "fr-FR"
            output_lang: Optional language code for the agent's response, e.g. "en-

        Returns:
            dict: The API response containing the assistant's reply
        """
        endpoint = CHAT_CONVERSATION_URL.format(
            account_id=account_id,
            project_id=project_id,
            conversation_id=conversation_id,
        )
        data = {"message": text, "client_env": environment}
        if input_lang:
            data["asr_lang_code"] = input_lang
        if output_lang:
            data["tts_lang_code"] = output_lang
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

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
        endpoint = CHAT_END_URL.format(
            account_id=account_id,
            project_id=project_id,
            conversation_id=conversation_id,
        )
        return PlatformAPIHandler.make_request(
            region, endpoint, "POST", data={"client_env": environment}
        )

    @staticmethod
    def create_draft_chat(
        region: str,
        account_id: str,
        project_id: str,
        artifact_version: str,
        lambda_deployment_version: str,
        channel: str = "chat.polyai",
        variant_id: ty.Optional[str] = None,
        input_lang: ty.Optional[str] = None,
        output_lang: ty.Optional[str] = None,
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
            input_lang: Optional language code of the input message, e.g. "en-GB" or "fr-FR"
            output_lang: Optional language code for the agent's response, e.g. "en-

        Returns:
            dict: The API response containing the conversation ID
        """
        endpoint = DRAFT_CHAT_URL.format(account_id=account_id, project_id=project_id)
        data = {
            "artifact_version": artifact_version,
            "lambda_deployment_version": lambda_deployment_version,
            "channel": channel,
        }
        if variant_id:
            data["variant_id"] = variant_id
        if input_lang:
            data["asr_lang_code"] = input_lang
        if output_lang:
            data["tts_lang_code"] = output_lang
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

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
            input_lang: Optional language code of the input message, e.g. "en-GB" or "fr-FR"
            output_lang: Optional language code for the agent's response, e.g. "en-

        Returns:
            dict: The API response containing the assistant's reply
        """
        endpoint = DRAFT_CHAT_CONVERSATION_URL.format(
            account_id=account_id,
            project_id=project_id,
            conversation_id=conversation_id,
        )
        data = {"message": text}
        if input_lang:
            data["asr_lang_code"] = input_lang
        if output_lang:
            data["tts_lang_code"] = output_lang
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=data)

    @staticmethod
    def promote_deployment(
        region: str,
        project_id: str,
        deployment_id: str,
        target_env: str,
        message: str,
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
        endpoint = PROMOTE_URL.format(project_id=project_id, deploymentId=deployment_id)
        target_env = "ERROR"
        body = {
            "targetEnvironment": target_env,
            "deploymentMessage": message,
        }
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=body)

    @staticmethod
    def rollback_deployment(
        region: str,
        project_id: str,
        deployment_id: str,
        message: str,
    ) -> dict:
        """Rollback sandbox to a previous deployment.

        Args:
            region: The region name
            project_id: The project ID
            deployment_id: The deployment ID
            message: Message to include with the rollback

        Returns:
            dict: The API response
        """
        endpoint = ROLLBACK_URL.format(project_id=project_id, deploymentId=deployment_id)
        body = {"deploymentMessage": message}
        return PlatformAPIHandler.make_request(region, endpoint, "POST", data=body)
