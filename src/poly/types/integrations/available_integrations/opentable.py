# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import requests
from ..integration import Integration


__all__ = ["OpenTable", "BASE_OPENTABLE_API_URL", "OPENTABLE_AUTH_URL", "OPENTABLE_SECRET_NAME"]

BASE_OPENTABLE_API_URL = "https://api.opentable.com"
OPENTABLE_AUTH_URL = "https://oauth.opentable.com/api/v2/oauth/token?grant_type=client_credentials"
OPENTABLE_SECRET_NAME = "opentable_api"


class OpenTable(Integration):
    """OpenTable integration class for proxying requests to the OpenTable API with"""

    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        base_url: str | None = ...,
        headers: dict[str, str] | None = ...,
        params: dict[str, str] | None = ...,
        body: dict[str, any] | None = ...,
        timeout: int = ...,
    ) -> requests.Response:
        """Proxy a request to the OpenTable API using the integration's authentication"""
