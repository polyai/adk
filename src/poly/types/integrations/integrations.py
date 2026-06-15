# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
__all__ = ["Integrations"]

import requests
from .available_integrations.opentable import OpenTable as OpenTable
from .available_integrations.tripleseat import Tripleseat as Tripleseat
from ..log_utils import ConversationLogger as ConversationLogger


class Integrations:
    opentable: OpenTable
    tripleseat: Tripleseat

    def __init__(
        self,
        log: ConversationLogger,
        paragon_connection_ids: dict[str, str] | None = None,
        paragon_project_id: str | None = None,
        integration_token: str | None = None,
    ) -> None: ...
    def proxy_request(
        self,
        integration_id: str,
        endpoint: str,
        http_method: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        body: dict[str, any] | None = None,
    ) -> requests.Response: ...
