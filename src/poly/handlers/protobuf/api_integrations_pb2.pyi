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
    __slots__ = ("id", "name", "description", "environments", "created_at", "created_by", "updated_at", "updated_by", "operations", "operation_groups")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENTS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    OPERATION_GROUPS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    environments: Environments
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    operations: _containers.RepeatedCompositeFieldContainer[ApiIntegrationOperation]
    operation_groups: OperationGroups
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., environments: _Optional[_Union[Environments, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., operations: _Optional[_Iterable[_Union[ApiIntegrationOperation, _Mapping]]] = ..., operation_groups: _Optional[_Union[OperationGroups, _Mapping]] = ...) -> None: ...

class OperationGroups(_message.Message):
    __slots__ = ("groups",)
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[OperationGroup]
    def __init__(self, groups: _Optional[_Iterable[_Union[OperationGroup, _Mapping]]] = ...) -> None: ...

class OperationGroup(_message.Message):
    __slots__ = ("id", "name", "operation_ids")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    OPERATION_IDS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    operation_ids: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., operation_ids: _Optional[_Iterable[str]] = ...) -> None: ...

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
    __slots__ = ("id", "name", "method", "resource", "created_at", "created_by", "updated_at", "updated_by", "headers", "description")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    method: str
    resource: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    headers: _containers.ScalarMap[str, str]
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., description: _Optional[str] = ...) -> None: ...

class OperationHeaders(_message.Message):
    __slots__ = ("entries",)
    class EntriesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    entries: _containers.ScalarMap[str, str]
    def __init__(self, entries: _Optional[_Mapping[str, str]] = ...) -> None: ...

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
    __slots__ = ("id", "name", "description", "old_name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    OLD_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    old_name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., old_name: _Optional[str] = ...) -> None: ...

class ApiIntegration_Delete(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

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
    __slots__ = ("name", "method", "resource", "integration_id", "id", "headers", "description")
    class HeadersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    method: str
    resource: str
    integration_id: str
    id: str
    headers: _containers.ScalarMap[str, str]
    description: str
    def __init__(self, name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., integration_id: _Optional[str] = ..., id: _Optional[str] = ..., headers: _Optional[_Mapping[str, str]] = ..., description: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation_Update(_message.Message):
    __slots__ = ("id", "name", "method", "resource", "integration_id", "integration_name", "old_name", "headers", "description")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_NAME_FIELD_NUMBER: _ClassVar[int]
    OLD_NAME_FIELD_NUMBER: _ClassVar[int]
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    method: str
    resource: str
    integration_id: str
    integration_name: str
    old_name: str
    headers: OperationHeaders
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ..., integration_id: _Optional[str] = ..., integration_name: _Optional[str] = ..., old_name: _Optional[str] = ..., headers: _Optional[_Union[OperationHeaders, _Mapping]] = ..., description: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation_Delete(_message.Message):
    __slots__ = ("id", "integration_id", "integration_name", "operation_name")
    ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    INTEGRATION_NAME_FIELD_NUMBER: _ClassVar[int]
    OPERATION_NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    integration_id: str
    integration_name: str
    operation_name: str
    def __init__(self, id: _Optional[str] = ..., integration_id: _Optional[str] = ..., integration_name: _Optional[str] = ..., operation_name: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperationGroups_Set(_message.Message):
    __slots__ = ("integration_id", "groups")
    INTEGRATION_ID_FIELD_NUMBER: _ClassVar[int]
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    integration_id: str
    groups: _containers.RepeatedCompositeFieldContainer[OperationGroup]
    def __init__(self, integration_id: _Optional[str] = ..., groups: _Optional[_Iterable[_Union[OperationGroup, _Mapping]]] = ...) -> None: ...
