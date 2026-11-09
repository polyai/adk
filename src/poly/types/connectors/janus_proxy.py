# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
from __future__ import annotations

from typing import Any
import requests

__all__ = [
    "DEFAULT_BASE_URL",
    "DEFAULT_TIMEOUT_SECONDS",
    "JanusProxyError",
    "JanusProxyConfigError",
    "JanusProxySSRFBlocked",
    "JanusProxyUpstreamError",
    "JanusProxyTimeout",
    "JanusProxyRateLimited",
    "JanusProxyAuthError",
    "JanusProxyPathForbidden",
    "janus_base_url",
    "normalize_environment",
    "build_response",
    "JanusProxyClient",
]

DEFAULT_BASE_URL: str = ...
DEFAULT_TIMEOUT_SECONDS: int = ...


class JanusProxyError(Exception):
    error_code: Any
    status_code: Any

    def __init__(
        self, *args: object, error_code: str | None = None, status_code: int | None = None
    ) -> None: ...


class JanusProxyConfigError(JanusProxyError): ...


class JanusProxySSRFBlocked(JanusProxyError): ...


class JanusProxyUpstreamError(JanusProxyError): ...


class JanusProxyTimeout(JanusProxyError): ...


class JanusProxyRateLimited(JanusProxyError): ...


class JanusProxyAuthError(JanusProxyError): ...


class JanusProxyPathForbidden(JanusProxyError): ...


def janus_base_url() -> str: ...
def normalize_environment(environment: str | None) -> str: ...
def build_response(
    status_code: int,
    body: str | bytes,
    content_type: str = ...,
    headers: dict[str, str] | None = None,
) -> requests.Response: ...


class JanusProxyClient:
    account_id: Any
    project_id: Any
    environment: Any
    base_url: Any
    timeout: Any

    def __init__(
        self,
        account_id: str | None,
        project_id: str,
        environment: str,
        token: str | None = None,
        base_url: str = ...,
        timeout: int = ...,
    ) -> None: ...
    @property
    def url(self) -> str: ...
    def request(
        self,
        integration: str,
        method: str,
        path: str,
        query: dict | None = None,
        headers: dict[str, str] | None = None,
        body: dict | None = None,
        form: dict | None = None,
        timeout: float | None = None,
    ) -> requests.Response: ...
