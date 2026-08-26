# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any

from ..integration import Integration

__all__ = ["OpenTable"]


class OpenTable(Integration):
    """OpenTable integration class for proxying requests to the OpenTable API"""

    integration_id: str
    integration_name: str

    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        base_url: str | None = ...,
        headers: dict[str, str] | None = ...,
        params: dict[str, str] | None = ...,
        body: dict[str, Any] | None = ...,
        timeout: int = ...,
    ) -> Any:
        """Proxy a request to the OpenTable API using the integration's authentication."""
