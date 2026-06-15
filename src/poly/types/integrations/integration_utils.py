# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any
import requests

VALID_HTTP_METHODS: Any
PROXY_BASE_URL: str
DEFAULT_REQUEST_TIMEOUT_SECONDS: int


def proxy_integration_request_to_paragon(
    paragon_connection_id: str,
    paragon_project_id: str,
    integration_token: str,
    integration_id: str,
    endpoint: str,
    http_method: str,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    body: dict[str, any] | None = None,
    request_timeout_seconds: int = ...,
) -> requests.Response: ...
