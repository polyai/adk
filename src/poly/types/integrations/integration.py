# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import requests
from ..log_utils import ConversationLogger


__all__ = ["Integration"]


class Integration:
    """Base class for all integrations"""

    integration_id: str
    integration_name: str

    def __init_subclass__(cls, **kwargs):
        """Register integration subclasses in the registry"""

    def __init__(self, log: ConversationLogger, proxy_request): ...
    def __str__(self):
        """Return the integration name when the object is printed"""

    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        headers: dict[str, str] | None = ...,
        params: dict[str, str] | None = ...,
        body: dict[str, any] | None = ...,
    ) -> requests.Response:
        """Proxy a request to the integration's API using the integration's authentication."""
