# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["Integration"]

import requests
from ..log_utils import ConversationLogger as ConversationLogger


class Integration:
    integration_id: str
    integration_name: str

    def __init_subclass__(cls, **kwargs) -> None: ...
    def __init__(self, log: ConversationLogger, proxy_request) -> None: ...
    def proxy_request(
        self,
        endpoint: str,
        http_method: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, any] | None = None,
    ) -> requests.Response: ...
