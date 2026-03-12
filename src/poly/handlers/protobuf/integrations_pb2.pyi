from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Integrations(_message.Message):
    __slots__ = ("paragon_providers_by_name",)
    class ParagonProvidersByNameEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: ParagonProvider
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[ParagonProvider, _Mapping]] = ...) -> None: ...
    PARAGON_PROVIDERS_BY_NAME_FIELD_NUMBER: _ClassVar[int]
    paragon_providers_by_name: _containers.MessageMap[str, ParagonProvider]
    def __init__(self, paragon_providers_by_name: _Optional[_Mapping[str, ParagonProvider]] = ...) -> None: ...

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
