from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ApiIntegrations(_message.Message):
    __slots__ = ("api_integrations",)
    API_INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    api_integrations: _containers.RepeatedCompositeFieldContainer[ApiIntegration]
    def __init__(self, api_integrations: _Optional[_Iterable[_Union[ApiIntegration, _Mapping]]] = ...) -> None: ...

class ApiIntegration(_message.Message):
    __slots__ = ("id", "name", "description", "environments", "created_at", "created_by", "updated_at", "updated_by", "operations")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENTS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    environments: Environments
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    operations: _containers.RepeatedCompositeFieldContainer[ApiIntegrationOperation]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., environments: _Optional[_Union[Environments, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., operations: _Optional[_Iterable[_Union[ApiIntegrationOperation, _Mapping]]] = ...) -> None: ...

class Environments(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: ApiIntegrationConfig
    pre_release: ApiIntegrationConfig
    live: ApiIntegrationConfig
    def __init__(self, sandbox: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ..., pre_release: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ..., live: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ...) -> None: ...

class ApiIntegrationConfig(_message.Message):
    __slots__ = ("base_url", "auth_type")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    AUTH_TYPE_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    auth_type: str
    def __init__(self, base_url: _Optional[str] = ..., auth_type: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation(_message.Message):
    __slots__ = ("id", "name", "method", "resource", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    method: str
    resource: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class ApiIntegration_Create(_message.Message):
    __slots__ = ("id", "name", "description", "environments")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENTS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    environments: Environments
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., environments: _Optional[_Union[Environments, _Mapping]] = ...) -> None: ...

class ApiIntegration_Update(_message.Message):
    __slots__ = ("id", "name", "description")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class ApiIntegration_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class ApiIntegrationConfig_Update(_message.Message):
    __slots__ = ("id", "environment", "base_url", "auth_type")
    ID_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENT_FIELD_NUMBER: _ClassVar[int]
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    AUTH_TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    environment: str
    base_url: str
    auth_type: str
    def __init__(self, id: _Optional[str] = ..., environment: _Optional[str] = ..., base_url: _Optional[str] = ..., auth_type: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation_Create(_message.Message):
    __slots__ = ("name", "method", "resource", "integration_id", "id")
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    name: str
    method: str
    resource: str
    integration_id: str
    id: str
    def __init__(self, name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., integration_id: _Optional[str] = ..., id: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation_Update(_message.Message):
    __slots__ = ("id", "name", "method", "resource", "integration_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    method: str
    resource: str
    integration_id: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., integration_id: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation_Delete(_message.Message):
    __slots__ = ("id", "integration_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    integration_id: str
    def __init__(self, id: _Optional[str] = ..., integration_id: _Optional[str] = ...) -> None: ...
