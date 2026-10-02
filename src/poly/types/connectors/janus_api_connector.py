# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

from typing import Any
from ..api_connector import ApiConnector

__all__ = ["JanusApiConnector"]


class JanusApiConnector(ApiConnector):
    api_name: Any
    api_id: Any
    project_id: Any
    account_id: Any
    environment: Any
    operations: Any

    def __init__(
        self,
        api_config: dict,
        environment: str,
        project_id: str,
        deferred_logger: Any | None = None,
        overrides: dict[str, list[dict]] | None = None,
        account_id: str | None = None,
        janus_token: str | None = None,
        consumed: dict[str, int] | None = None,
    ) -> None: ...
