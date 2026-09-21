# Copyright PolyAI Limited
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
    "JanusProxyAuthError",
    "normalize_environment",
    "build_response",
    "JanusProxyClient",
]

DEFAULT_BASE_URL: str
DEFAULT_TIMEOUT_SECONDS: int

class JanusProxyError(Exception): ...
class JanusProxyConfigError(JanusProxyError): ...
class JanusProxySSRFBlocked(JanusProxyError): ...
class JanusProxyUpstreamError(JanusProxyError): ...
class JanusProxyTimeout(JanusProxyError): ...
class JanusProxyAuthError(JanusProxyError): ...

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
    ) -> requests.Response: ...
