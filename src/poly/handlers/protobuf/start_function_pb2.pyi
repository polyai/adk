from google.protobuf import timestamp_pb2 as _timestamp_pb2
from poly.handlers.protobuf import functions_pb2 as _functions_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class StartFunctionReferences(_message.Message):
    __slots__ = ("variables",)
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class StartFunction(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors", "created_at", "created_by", "updated_at", "updated_by", "archived", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionParameter]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    archived: bool
    references: StartFunctionReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[_functions_pb2.FunctionParameter, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., archived: bool = ..., references: _Optional[_Union[StartFunctionReferences, _Mapping]] = ...) -> None: ...

class StartFunction_Create(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors", "archived", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionParameter]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    archived: bool
    references: StartFunctionReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[_functions_pb2.FunctionParameter, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., archived: bool = ..., references: _Optional[_Union[StartFunctionReferences, _Mapping]] = ...) -> None: ...

class StartFunction_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class StartFunction_Update(_message.Message):
    __slots__ = ("id", "description", "code", "errors", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    description: str
    code: str
    errors: _functions_pb2.ErrorsUpdate
    references: StartFunctionReferences
    def __init__(self, id: _Optional[str] = ..., description: _Optional[str] = ..., code: _Optional[str] = ..., errors: _Optional[_Union[_functions_pb2.ErrorsUpdate, _Mapping]] = ..., references: _Optional[_Union[StartFunctionReferences, _Mapping]] = ...) -> None: ...
