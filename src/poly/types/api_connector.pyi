# Copyright PolyAI Limited
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from requests import PreparedRequest as PreparedRequest
from requests.auth import AuthBase

from .conversation import ApiIntegrationData as ApiIntegrationData

NORMALIZED_ENVIRONMENT_NAMES: dict[str, str]

def clear_credentials_cache() -> None: ...

class HTTPBasicAuth(AuthBase):
    username: Any
    password: Any
    def __init__(self, username: str, password: str) -> None: ...
    def __call__(self, r): ...

class HTTPAPIKeyAuth(AuthBase):
    key: Any
    value: Any
    location: Any
    def __init__(self, key: str, value: str, location: str = "header") -> None: ...
    def __call__(self, r): ...

@dataclass
class AccessToken:
    token: str
    valid_until: datetime | None = ...
    def is_valid(self) -> bool: ...

@dataclass
class OAuth2Config:
    token_url: str
    client_id: str
    client_secret: str
    credentials_location: str = ...
    grant_type: str = ...
    scope: str | None = ...

class HTTPOAuth2(AuthBase):
    should_retry: bool
    config: Any
    access_token: Any
    def __init__(self, auth_config: OAuth2Config) -> None: ...
    def __eq__(self, other): ...
    def __ne__(self, other): ...
    def invalidate_auth(self) -> None: ...
    def __call__(self, r: PreparedRequest) -> PreparedRequest: ...

class ApiConnector:
    api_name: Any
    api_id: Any
    project_id: Any
    account_id: Any
    environment: Any
    base_url: Any
    auth_type: Any
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
    @property
    def client(self) -> ApiClient: ...
    def __getattr__(self, operation_name: str): ...

class ApiIntegrations:
    environment: Any
    project_id: Any
    account_id: Any
    def __init__(
        self,
        api_configs: list[ApiIntegrationData],
        environment: str,
        project_id: str | None = None,
        api_overrides: dict[str, dict[str, list[dict]]] | None = None,
        connector_cls: type[ApiConnector] | None = None,
        account_id: str | None = None,
        janus_token: str | None = None,
        consumed: dict[str, dict[str, int]] | None = None,
    ) -> None: ...
    def get_consumed_snapshot(self) -> dict[str, dict[str, int]]: ...
    def flush_logs(self) -> None: ...
    def __getattr__(self, api_name: str) -> ApiConnector: ...

def replace_path_variables(url: str, *args, **kwargs) -> tuple[str, set[str]]: ...

class ApiClient:
    base_url: Any
    auth: Any
    def __init__(
        self, base_url: str, auth_config: dict | None = None, deferred_logger: Any | None = None
    ) -> None: ...
    @property
    def session(self): ...
    def build_request(self, method: str, path: str, **default_kwargs): ...
