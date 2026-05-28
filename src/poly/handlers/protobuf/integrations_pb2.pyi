from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Integrations(_message.Message):
    __slots__ = ("paragon_providers_by_name", "mcp")
    class ParagonProvidersByNameEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ParagonProvider
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ParagonProvider, _Mapping]] = ...) -> None: ...
    PARAGON_PROVIDERS_BY_NAME_FIELD_NUMBER: _ClassVar[int]
    MCP_FIELD_NUMBER: _ClassVar[int]
    paragon_providers_by_name: _containers.MessageMap[str, ParagonProvider]
    mcp: MCPConfiguration
    def __init__(self, paragon_providers_by_name: _Optional[_Mapping[str, ParagonProvider]] = ..., mcp: _Optional[_Union[MCPConfiguration, _Mapping]] = ...) -> None: ...

class MCPConfiguration(_message.Message):
    __slots__ = ("servers_by_id", "profiles")
    class ServersByIdEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: MCPServer
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[MCPServer, _Mapping]] = ...) -> None: ...
    class ProfilesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: MCPProfile
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[MCPProfile, _Mapping]] = ...) -> None: ...
    SERVERS_BY_ID_FIELD_NUMBER: _ClassVar[int]
    PROFILES_FIELD_NUMBER: _ClassVar[int]
    servers_by_id: _containers.MessageMap[str, MCPServer]
    profiles: _containers.MessageMap[str, MCPProfile]
    def __init__(self, servers_by_id: _Optional[_Mapping[str, MCPServer]] = ..., profiles: _Optional[_Mapping[str, MCPProfile]] = ...) -> None: ...

class MCPServer(_message.Message):
    __slots__ = ("id", "provider_id", "url", "auth", "timeout", "enabled_functions", "last_discovered_at", "last_discovered_tool_count")
    ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    AUTH_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    LAST_DISCOVERED_AT_FIELD_NUMBER: _ClassVar[int]
    LAST_DISCOVERED_TOOL_COUNT_FIELD_NUMBER: _ClassVar[int]
    id: str
    provider_id: str
    url: str
    auth: MCPAuth
    timeout: int
    enabled_functions: MCPEnabledFunctions
    last_discovered_at: str
    last_discovered_tool_count: int
    def __init__(self, id: _Optional[str] = ..., provider_id: _Optional[str] = ..., url: _Optional[str] = ..., auth: _Optional[_Union[MCPAuth, _Mapping]] = ..., timeout: _Optional[int] = ..., enabled_functions: _Optional[_Union[MCPEnabledFunctions, _Mapping]] = ..., last_discovered_at: _Optional[str] = ..., last_discovered_tool_count: _Optional[int] = ...) -> None: ...

class MCPProfile(_message.Message):
    __slots__ = ("provider_id", "url", "auth", "timeout")
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    AUTH_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    url: str
    auth: MCPAuth
    timeout: int
    def __init__(self, provider_id: _Optional[str] = ..., url: _Optional[str] = ..., auth: _Optional[_Union[MCPAuth, _Mapping]] = ..., timeout: _Optional[int] = ...) -> None: ...

class MCPAuth(_message.Message):
    __slots__ = ("header", "query_param", "oauth", "secret_name")
    HEADER_FIELD_NUMBER: _ClassVar[int]
    QUERY_PARAM_FIELD_NUMBER: _ClassVar[int]
    OAUTH_FIELD_NUMBER: _ClassVar[int]
    SECRET_NAME_FIELD_NUMBER: _ClassVar[int]
    header: str
    query_param: str
    oauth: MCPOAuth
    secret_name: str
    def __init__(self, header: _Optional[str] = ..., query_param: _Optional[str] = ..., oauth: _Optional[_Union[MCPOAuth, _Mapping]] = ..., secret_name: _Optional[str] = ...) -> None: ...

class MCPOAuth(_message.Message):
    __slots__ = ("client_id", "client_secret_name", "token_url", "audience", "scope")
    CLIENT_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_SECRET_NAME_FIELD_NUMBER: _ClassVar[int]
    TOKEN_URL_FIELD_NUMBER: _ClassVar[int]
    AUDIENCE_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    client_id: str
    client_secret_name: str
    token_url: str
    audience: str
    scope: str
    def __init__(self, client_id: _Optional[str] = ..., client_secret_name: _Optional[str] = ..., token_url: _Optional[str] = ..., audience: _Optional[str] = ..., scope: _Optional[str] = ...) -> None: ...

class MCPEnabledFunctions(_message.Message):
    __slots__ = ("names",)
    NAMES_FIELD_NUMBER: _ClassVar[int]
    names: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, names: _Optional[_Iterable[str]] = ...) -> None: ...

class ParagonProvider(_message.Message):
    __slots__ = ("provider_id", "available_functions", "timeout", "env_integrations", "integrations_by_id")
    class IntegrationsByIdEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ParagonIntegration
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ParagonIntegration, _Mapping]] = ...) -> None: ...
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    ENV_INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    INTEGRATIONS_BY_ID_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    available_functions: _containers.RepeatedScalarFieldContainer[str]
    timeout: int
    env_integrations: EnvironmentIntegrationRefs
    integrations_by_id: _containers.MessageMap[str, ParagonIntegration]
    def __init__(self, provider_id: _Optional[str] = ..., available_functions: _Optional[_Iterable[str]] = ..., timeout: _Optional[int] = ..., env_integrations: _Optional[_Union[EnvironmentIntegrationRefs, _Mapping]] = ..., integrations_by_id: _Optional[_Mapping[str, ParagonIntegration]] = ...) -> None: ...

class EnvironmentIntegrationRefs(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: str
    pre_release: str
    live: str
    def __init__(self, sandbox: _Optional[str] = ..., pre_release: _Optional[str] = ..., live: _Optional[str] = ...) -> None: ...

class ParagonIntegration(_message.Message):
    __slots__ = ("paragon_connection_id", "paragon_user_id", "metadata", "created_at", "created_by", "updated_at", "updated_by")
    PARAGON_CONNECTION_ID_FIELD_NUMBER: _ClassVar[int]
    PARAGON_USER_ID_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    paragon_connection_id: str
    paragon_user_id: str
    metadata: _struct_pb2.Struct
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, paragon_connection_id: _Optional[str] = ..., paragon_user_id: _Optional[str] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class Integration_Connect(_message.Message):
    __slots__ = ("provider", "paragon_connection_id", "paragon_user_id", "client_env", "metadata")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    PARAGON_CONNECTION_ID_FIELD_NUMBER: _ClassVar[int]
    PARAGON_USER_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    provider: str
    paragon_connection_id: str
    paragon_user_id: str
    client_env: str
    metadata: _struct_pb2.Struct
    def __init__(self, provider: _Optional[str] = ..., paragon_connection_id: _Optional[str] = ..., paragon_user_id: _Optional[str] = ..., client_env: _Optional[str] = ..., metadata: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Integration_Enable(_message.Message):
    __slots__ = ("provider", "paragon_connection_id", "client_env")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    PARAGON_CONNECTION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    provider: str
    paragon_connection_id: str
    client_env: str
    def __init__(self, provider: _Optional[str] = ..., paragon_connection_id: _Optional[str] = ..., client_env: _Optional[str] = ...) -> None: ...

class Integration_Disable(_message.Message):
    __slots__ = ("provider", "paragon_connection_id", "client_env")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    PARAGON_CONNECTION_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    provider: str
    paragon_connection_id: str
    client_env: str
    def __init__(self, provider: _Optional[str] = ..., paragon_connection_id: _Optional[str] = ..., client_env: _Optional[str] = ...) -> None: ...

class Integration_UpdateFunctions(_message.Message):
    __slots__ = ("provider", "available_functions")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    provider: str
    available_functions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, provider: _Optional[str] = ..., available_functions: _Optional[_Iterable[str]] = ...) -> None: ...

class Integration_Disconnect(_message.Message):
    __slots__ = ("provider", "paragon_connection_id")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    PARAGON_CONNECTION_ID_FIELD_NUMBER: _ClassVar[int]
    provider: str
    paragon_connection_id: str
    def __init__(self, provider: _Optional[str] = ..., paragon_connection_id: _Optional[str] = ...) -> None: ...

class MCPConfig_Update(_message.Message):
    __slots__ = ("config",)
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    config: MCPConfiguration
    def __init__(self, config: _Optional[_Union[MCPConfiguration, _Mapping]] = ...) -> None: ...

class MCPServer_Upsert(_message.Message):
    __slots__ = ("server",)
    SERVER_FIELD_NUMBER: _ClassVar[int]
    server: MCPServer
    def __init__(self, server: _Optional[_Union[MCPServer, _Mapping]] = ...) -> None: ...

class MCPServer_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class MCPProfile_Upsert(_message.Message):
    __slots__ = ("profile",)
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    profile: MCPProfile
    def __init__(self, profile: _Optional[_Union[MCPProfile, _Mapping]] = ...) -> None: ...

class MCPProfile_Delete(_message.Message):
    __slots__ = ("provider_id",)
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    def __init__(self, provider_id: _Optional[str] = ...) -> None: ...
