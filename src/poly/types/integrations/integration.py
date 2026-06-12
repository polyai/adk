# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any

from ..log_utils import ConversationLogger

__all__ = ["Integration"]


class Integration:
    """Base class for all integrations"""

    integration_id: str
    integration_name: str

    def __init__(self, log: ConversationLogger, proxy_request: Any): ...
    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        headers: dict[str, str] | None = ...,
        params: dict[str, str] | None = ...,
        body: dict[str, Any] | None = ...,
    ) -> Any:
        """Proxy a request to the integration's API using the integration's authentication."""
