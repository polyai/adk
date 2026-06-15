# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["OpenTable"]

import requests
from ..integration import Integration

BASE_OPENTABLE_API_URL: str
OPENTABLE_AUTH_URL: str
OPENTABLE_SECRET_NAME: str


class OpenTable(Integration):
    integration_id: str
    integration_name: str

    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        base_url: str | None = None,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, any] | None = None,
        timeout: int = ...,
    ) -> requests.Response: ...
