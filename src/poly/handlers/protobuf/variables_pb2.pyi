from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class VariablesMap(_message.Message):
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

class VariableReferences(_message.Message):
    __slots__ = ("functions", "delay_responses", "flow_steps", "flow_no_code_steps", "flow_functions", "topics", "behaviours", "greetings", "roles", "personalities", "sms", "start_functions", "end_functions")
    class FunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class DelayResponsesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class FlowStepsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class FlowNoCodeStepsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class FlowFunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class TopicsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class BehavioursEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class GreetingsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class RolesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class PersonalitiesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class SmsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class StartFunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class EndFunctionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    FLOW_NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    FLOW_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOURS_FIELD_NUMBER: _ClassVar[int]
    GREETINGS_FIELD_NUMBER: _ClassVar[int]
    ROLES_FIELD_NUMBER: _ClassVar[int]
    PERSONALITIES_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    START_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    END_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    functions: _containers.ScalarMap[str, bool]
    delay_responses: _containers.ScalarMap[str, bool]
    flow_steps: _containers.ScalarMap[str, bool]
    flow_no_code_steps: _containers.ScalarMap[str, bool]
    flow_functions: _containers.ScalarMap[str, bool]
    topics: _containers.ScalarMap[str, bool]
    behaviours: _containers.ScalarMap[str, bool]
    greetings: _containers.ScalarMap[str, bool]
    roles: _containers.ScalarMap[str, bool]
    personalities: _containers.ScalarMap[str, bool]
    sms: _containers.ScalarMap[str, bool]
    start_functions: _containers.ScalarMap[str, bool]
    end_functions: _containers.ScalarMap[str, bool]
    def __init__(self, functions: _Optional[_Mapping[str, bool]] = ..., delay_responses: _Optional[_Mapping[str, bool]] = ..., flow_steps: _Optional[_Mapping[str, bool]] = ..., flow_no_code_steps: _Optional[_Mapping[str, bool]] = ..., flow_functions: _Optional[_Mapping[str, bool]] = ..., topics: _Optional[_Mapping[str, bool]] = ..., behaviours: _Optional[_Mapping[str, bool]] = ..., greetings: _Optional[_Mapping[str, bool]] = ..., roles: _Optional[_Mapping[str, bool]] = ..., personalities: _Optional[_Mapping[str, bool]] = ..., sms: _Optional[_Mapping[str, bool]] = ..., start_functions: _Optional[_Mapping[str, bool]] = ..., end_functions: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Variable(_message.Message):
    __slots__ = ("id", "name", "created_by", "created_at", "updated_by", "updated_at", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    references: VariableReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., references: _Optional[_Union[VariableReferences, _Mapping]] = ...) -> None: ...

class Variables(_message.Message):
    __slots__ = ("entities",)
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    entities: _containers.RepeatedCompositeFieldContainer[Variable]
    def __init__(self, entities: _Optional[_Iterable[_Union[Variable, _Mapping]]] = ...) -> None: ...

class Variable_Create(_message.Message):
    __slots__ = ("id", "name", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    references: VariableReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., references: _Optional[_Union[VariableReferences, _Mapping]] = ...) -> None: ...

class Variable_Update(_message.Message):
    __slots__ = ("id", "name", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    references: VariableReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., references: _Optional[_Union[VariableReferences, _Mapping]] = ...) -> None: ...

class Variable_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...
