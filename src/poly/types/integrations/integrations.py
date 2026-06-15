# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


import requests
from .available_integrations.opentable import OpenTable
from .available_integrations.tripleseat import Tripleseat
from ..log_utils import ConversationLogger


__all__ = ["Integrations"]


class Integrations:
    """Integrations interface"""

    opentable: OpenTable
    tripleseat: Tripleseat

    def __init__(
        self,
        log: ConversationLogger,
        paragon_connection_ids: dict[str, str] | None = ...,
        paragon_project_id: str | None = ...,
        integration_token: str | None = ...,
    ): ...
    def proxy_request(
        self,
        integration_id: str,
        endpoint: str,
        http_method: str,
        headers: dict[str, str] | None = ...,
        params: dict[str, str] | None = ...,
        body: dict[str, any] | None = ...,
    ) -> requests.Response:
        """General method if custom integration class is not built to proxy"""
