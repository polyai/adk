# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any

from .available_integrations.opentable import OpenTable
from .available_integrations.tripleseat import Tripleseat

__all__ = ["Integrations"]


class Integrations:
    """Integrations interface"""

    opentable: OpenTable
    tripleseat: Tripleseat

    def __init__(
        self,
        log: Any,
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
        body: dict[str, Any] | None = ...,
    ) -> Any:
        """General method to proxy request through Paragon."""
