"""Write API integration credentials through the existing Studio secrets API.

Copyright PolyAI Limited
"""

import json
from urllib.parse import quote

from poly.handlers.platform_api import PlatformAPIHandler


class IntegrationCredentialsHandler:
    """Keep secret requests out of the general request/response debug logger."""

    @staticmethod
    def _request(region: str, token: str, account_id: str, method: str, **kwargs):
        return PlatformAPIHandler.make_request(
            region,
            f"/jupiter/v1/accounts/{quote(account_id, safe='')}/api_secrets",
            method,
            headers=PlatformAPIHandler._jwt_headers(token),
            use_jupiter_api=True,
            sensitive=True,
            data=kwargs.get("json"),
            params=kwargs.get("params"),
        )

    @classmethod
    def set_credentials(
        cls,
        region: str,
        token: str,
        account_id: str,
        project_id: str,
        integration_id: str,
        environment: str,
        credentials: dict,
    ) -> None:
        """Replace one environment, preserving the secret's other values and metadata."""
        if environment not in {"sandbox", "pre-release", "live"}:
            raise ValueError("Environment must be sandbox, pre-release or live.")
        name = f"api-integration-{project_id}-{integration_id}"
        secrets = cls._request(region, token, account_id, "GET", params={"name": name})
        if not isinstance(secrets, list) or len(secrets) > 1:
            raise ValueError("Studio returned an unexpected secrets response; no changes made.")
        existing = secrets[0] if secrets else None
        if secrets and (
            not isinstance(existing, dict)
            or existing.get("display_name") != name
            or existing.get("value_type") != "key-value"
            or not isinstance(existing.get("secret_value"), dict)
        ):
            raise ValueError(
                "Existing integration secret has an unexpected format; no changes made."
            )
        values = dict(existing["secret_value"]) if existing else {}
        storage_key = "pre_release" if environment == "pre-release" else environment
        if storage_key == "pre_release":
            values.pop("pre-release", None)
        values[storage_key] = json.dumps(credentials)
        cls._request(
            region,
            token,
            account_id,
            "PUT" if existing else "POST",
            json={
                "display_name": name,
                "description": existing.get("description", "")
                if existing
                else f"Authentication credentials for {integration_id} api integration",
                "value_type": "key-value",
                "access_config": existing.get("access_config", [project_id])
                if existing
                else [project_id],
                "secret_value": values,
            },
        )
