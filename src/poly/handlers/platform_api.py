"""Client for the Agent Studio Platform API

Copyright PolyAI Limited
"""

import json
import logging
import typing as ty
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from poly.utils import retrieve_api_key

logger = logging.getLogger(__name__)
ACCOUNTS_URL = "/accounts"
PROJECTS_URL = "/accounts/{account_id}/projects"
DEPLOYMENTS_URL = "/accounts/{account_id}/projects/{project_id}/deployments"
ACTIVE_DEPLOYMENTS_URL = "/accounts/{account_id}/projects/{project_id}/deployments/active"
CHAT_URL = "/accounts/{account_id}/projects/{project_id}/chat"
CHAT_CONVERSATION_URL = "/accounts/{account_id}/projects/{project_id}/chat/{conversation_id}"
DRAFT_CHAT_URL = "/accounts/{account_id}/projects/{project_id}/draft/chat"
DRAFT_CHAT_CONVERSATION_URL = (
    "/accounts/{account_id}/projects/{project_id}/draft/chat/{conversation_id}"
)
CHAT_END_URL = "/accounts/{account_id}/projects/{project_id}/chat/{conversation_id}/end"


class PlatformAPIHandler:
    """Class for interacting with the Platform API"""

    region_to_base_url = {
        "dev": "https://api.dev.poly.ai/adk/v1",
        "staging": "https://api.staging.poly.ai/adk/v1",
        "euw-1": "https://api.eu.poly.ai/adk/v1",
        "uk-1": "https://api.uk.poly.ai/adk/v1",
        "us-1": "https://api.us.poly.ai/adk/v1",
        "studio": "https://api.studio.poly.ai/adk/v1",
    }

    region_to_agents_api_url = {
        "dev": "https://api.dev.poly.ai/v1",
        "staging": "https://api.staging.poly.ai/v1",
        "euw-1": "https://api.eu.poly.ai/v1",
        "uk-1": "https://api.uk.poly.ai/v1",
        "us-1": "https://api.us.poly.ai/v1",
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
    def get_agents_api_url(region: str) -> str:
        """Get the Agents API base URL for the given region.

        Args:
            region (str): The region name
        Returns:
            str: The Agents API base URL
        """
        if base_url := PlatformAPIHandler.region_to_agents_api_url.get(region):
            return base_url
        raise ValueError(f"Unknown region: {region}")

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
            "X-API-KEY": retrieve_api_key(region),
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
                f"Error in request. url={url!r} body={data!r}"
                f" status_code={api_response.status_code!r} response={api_response.text!r}"
            )
            raise

        try:
            api_response = api_response.json()
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")

        logger.info(f"Request to {url} successful")
        return api_response

    @staticmethod
    def get_accessible_regions(regions: list[str]) -> list[str]:
        """Return the subset of regions the current API key can access.

        Probes each region concurrently by calling get_accounts. A region is
        considered accessible if the call succeeds and returns at least one
        account.

        Args:
            regions (list[str]): The full list of region names to probe.

        Returns:
            list[str]: Regions that returned at least one account, preserving
                the original ordering.
        """

        retrieve_api_key()

        accessible: set[str] = set()

        def _probe(region: str) -> str | None:
            try:
                accounts = PlatformAPIHandler.get_accounts(region)
                if accounts:
                    return region
            except Exception:
                logger.debug(f"Region {region} is not accessible for this API key")
            return None

        with ThreadPoolExecutor(max_workers=len(regions)) as executor:
            futures = {executor.submit(_probe, r): r for r in regions}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    accessible.add(result)

        return [r for r in regions if r in accessible]

    @staticmethod
    def get_accounts(region: str) -> dict[str, str]:
        """Get the accounts for a given region.

        Args:
            region (str): The region name

        Returns:
            dict[str, str]: A dictionary mapping account ids to account names
        """
        accounts = {}
        accounts_data = PlatformAPIHandler.make_request(region, ACCOUNTS_URL, "GET")

        if not isinstance(accounts_data, list):
            raise ValueError("Expected a list of accounts")

        for account in accounts_data:
            if account.get("active", False) and account.get("id") and account.get("name"):
                accounts[account.get("id")] = account.get("name")

        return accounts

    @staticmethod
    def get_projects(region: str, account_id: str) -> dict[str, str]:
        """Get the projects for a given account.

        Args:
            region (str): The region name
            account_id (str): The account ID

        Returns:
            dict[str, str]: A dictionary mapping project IDs to project names
        """
        projects = {}
        endpoint = PROJECTS_URL.format(account_id=account_id)
        projects_data = PlatformAPIHandler.make_request(region, endpoint, "GET")
        projects_list = projects_data.get("projects", [])

        if not isinstance(projects_list, list):
            raise ValueError("Expected a list of projects")

        for project in projects_list:
            if project.get("id") and project.get("name"):
                projects[project.get("id")] = project.get("name")

        return projects

    @staticmethod
    def create_project(
        region: str,
        account_id: str,
        project_name: str,
        project_id: str = None,
    ) -> dict[str, str]:
        """Create a new project (agent) via the Agents API.

        Args:
            region (str): The region name
            account_id (str): The account ID
            project_name (str): The display name for the new project
            project_id (str | None): Optional slug/ID for the project.
                Defaults to a slugified version of the project name.

        Returns:
            dict[str, str]: A dictionary with the created project's 'id' and 'name'
        """
        if not project_id:
            project_id = project_name.lower().replace(" ", "-")

        region_to_voice_id = {
            "us-1": "VOICE-afe2b8e8",
            "euw-1": "VOICE-7def3647",
            "uk-1": "VOICE-37966683",
            "dev": "VOICE-86f7b4cf",
            "staging": "VOICE-86f7b4cf",
        }
        voice_id = region_to_voice_id.get(region, "VOICE-afe2b8e8")

        url = PlatformAPIHandler.get_agents_api_url(region) + f"/accounts/{account_id}/agents"
        data = {
            "name": project_name,
            "agentId": project_id,
            "responseSettings": {
                "greeting": "Hello, how can I help you?",
            },
            "voiceSettings": {
                "voiceId": voice_id,
            },
        }

        correlation_id = f"adk-{uuid.uuid4()}"
        headers = {
            "X-API-KEY": retrieve_api_key(region),
            "X-PolyAI-Correlation-Id": correlation_id,
            "Content-Type": "application/json",
        }

        logger.info(f"Creating project at {url}")
        response = requests.request(
            method="POST",
            url=url,
            headers=headers,
            allow_redirects=False,
            data=json.dumps(data),
        )

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            logger.debug(
                f"Error creating project. url={url!r} status_code={response.status_code!r}"
                f" response={response.text!r}"
            )
            try:
                body = response.json()
                message = body.get("error_message") or body.get("message") or body.get("error")
            except (json.JSONDecodeError, KeyError, ValueError):
                message = None
            raise ValueError(message or f"{response.status_code} {response.reason}") from e

        logger.info(f"Request to {url} successful")
        result = response.json()
        return {"id": result.get("agentId"), "name": result.get("agentName")}

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
            region,
            endpoint,
            "GET",
            data=None,
            params={"client_env": client_env},
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
            region,
            endpoint,
            "POST",
            data={"client_env": environment},
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
