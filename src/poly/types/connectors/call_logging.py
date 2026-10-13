# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

import requests
from collections.abc import Iterable, Mapping
from ..log_utils import ConversationLogger
from typing import Any

__all__ = [
    "REDACTED",
    "MAX_LOGGED_BODY_CHARS",
    "MAX_DECODED_BODY_BYTES",
    "redact_headers",
    "normalise_pii_fields",
    "redact_fields",
    "redact_body",
    "redact_query",
    "truncate_body",
    "response_body",
    "log_connector_call",
]

REDACTED: str = ...
MAX_LOGGED_BODY_CHARS: int = ...
MAX_DECODED_BODY_BYTES: Any = ...


def redact_headers(headers: Mapping[str, Any] | None) -> dict[str, Any] | None: ...
def normalise_pii_fields(fields: Iterable[str] | None, kwarg: str) -> frozenset[str]: ...
def redact_fields(value: Any, fields: frozenset[str]) -> Any: ...
def redact_body(value: Any, fields: frozenset[str], kwarg: str) -> Any: ...
def redact_query(value: Any, fields: frozenset[str]) -> Any: ...
def truncate_body(value: Any, limit: int = ...) -> Any: ...
def response_body(
    response: requests.Response, fields: frozenset[str] = ..., limit: int = ...
) -> Any: ...
def log_connector_call(
    logger: ConversationLogger,
    *,
    connector: str,
    operation: str,
    method: str,
    path: str,
    request: dict[str, Any],
    elapsed_ms: float,
    response: requests.Response | None = None,
    error: BaseException | None = None,
    mocked: bool = False,
    request_pii: frozenset[str] = ...,
    response_pii: frozenset[str] = ...,
) -> None: ...
