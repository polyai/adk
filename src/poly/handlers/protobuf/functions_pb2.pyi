from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FunctionParameter(_message.Message):
    __slots__ = ("id", "name", "description", "type", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    type: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., type: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class FunctionError(_message.Message):
    __slots__ = ("lineno", "message", "text")
    LINENO_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    lineno: int
    message: str
    text: str
    def __init__(self, lineno: _Optional[int] = ..., message: _Optional[str] = ..., text: _Optional[str] = ...) -> None: ...

class FunctionDelayResponseReferences(_message.Message):
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

class FunctionDelayResponse(_message.Message):
    __slots__ = ("id", "message", "duration", "created_at", "created_by", "updated_at", "updated_by", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    message: str
    duration: int
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    references: FunctionDelayResponseReferences
    def __init__(self, id: _Optional[str] = ..., message: _Optional[str] = ..., duration: _Optional[int] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., references: _Optional[_Union[FunctionDelayResponseReferences, _Mapping]] = ...) -> None: ...

class FunctionLatencyControl(_message.Message):
    __slots__ = ("enabled", "delay_responses", "initial_delay", "interval", "created_at", "created_by", "updated_at", "updated_by")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    INITIAL_DELAY_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    delay_responses: _containers.RepeatedCompositeFieldContainer[FunctionDelayResponse]
    initial_delay: int
    interval: int
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, enabled: bool = ..., delay_responses: _Optional[_Iterable[_Union[FunctionDelayResponse, _Mapping]]] = ..., initial_delay: _Optional[int] = ..., interval: _Optional[int] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class FunctionReferences(_message.Message):
    __slots__ = ("flow_steps", "topics", "stop_keywords", "behaviour", "variables")
    class FlowStepsEntry(_message.Message):
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
    class StopKeywordsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class BehaviourEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOUR_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    flow_steps: _containers.ScalarMap[str, bool]
    topics: _containers.ScalarMap[str, bool]
    stop_keywords: _containers.ScalarMap[str, bool]
    behaviour: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, flow_steps: _Optional[_Mapping[str, bool]] = ..., topics: _Optional[_Mapping[str, bool]] = ..., stop_keywords: _Optional[_Mapping[str, bool]] = ..., behaviour: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class Function(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors", "latency_control", "created_at", "created_by", "updated_at", "updated_by", "archived", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: _containers.RepeatedCompositeFieldContainer[FunctionParameter]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[FunctionError]
    latency_control: FunctionLatencyControl
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    archived: bool
    references: FunctionReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[FunctionParameter, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[FunctionLatencyControl, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., archived: bool = ..., references: _Optional[_Union[FunctionReferences, _Mapping]] = ...) -> None: ...

class Functions(_message.Message):
    __slots__ = ("functions",)
    FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    functions: _containers.RepeatedCompositeFieldContainer[Function]
    def __init__(self, functions: _Optional[_Iterable[_Union[Function, _Mapping]]] = ...) -> None: ...

class FunctionParameterUpdate(_message.Message):
    __slots__ = ("id", "name", "description", "type")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    type: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., type: _Optional[str] = ...) -> None: ...

class FunctionCreateLatencyControl(_message.Message):
    __slots__ = ("enabled", "delay_responses", "initial_delay", "interval")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    INITIAL_DELAY_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    delay_responses: _containers.RepeatedCompositeFieldContainer[FunctionDelayResponse]
    initial_delay: int
    interval: int
    def __init__(self, enabled: bool = ..., delay_responses: _Optional[_Iterable[_Union[FunctionDelayResponse, _Mapping]]] = ..., initial_delay: _Optional[int] = ..., interval: _Optional[int] = ...) -> None: ...

class Function_CreateFunction(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors", "latency_control", "references", "archived")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: _containers.RepeatedCompositeFieldContainer[FunctionParameterUpdate]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[FunctionError]
    latency_control: FunctionCreateLatencyControl
    references: FunctionReferences
    archived: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[FunctionParameterUpdate, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[FunctionCreateLatencyControl, _Mapping]] = ..., references: _Optional[_Union[FunctionReferences, _Mapping]] = ..., archived: bool = ...) -> None: ...

class ParametersUpdate(_message.Message):
    __slots__ = ("parameters",)
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    parameters: _containers.RepeatedCompositeFieldContainer[FunctionParameterUpdate]
    def __init__(self, parameters: _Optional[_Iterable[_Union[FunctionParameterUpdate, _Mapping]]] = ...) -> None: ...

class ErrorsUpdate(_message.Message):
    __slots__ = ("errors",)
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    errors: _containers.RepeatedCompositeFieldContainer[FunctionError]
    def __init__(self, errors: _Optional[_Iterable[_Union[FunctionError, _Mapping]]] = ...) -> None: ...

class Function_UpdateFunction(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors", "references", "archived")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: ParametersUpdate
    code: str
    errors: ErrorsUpdate
    references: FunctionReferences
    archived: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Union[ParametersUpdate, _Mapping]] = ..., code: _Optional[str] = ..., errors: _Optional[_Union[ErrorsUpdate, _Mapping]] = ..., references: _Optional[_Union[FunctionReferences, _Mapping]] = ..., archived: bool = ...) -> None: ...

class Function_DeleteFunction(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DelayResponseUpdate(_message.Message):
    __slots__ = ("id", "message", "duration", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    message: str
    duration: int
    references: FunctionDelayResponseReferences
    def __init__(self, id: _Optional[str] = ..., message: _Optional[str] = ..., duration: _Optional[int] = ..., references: _Optional[_Union[FunctionDelayResponseReferences, _Mapping]] = ...) -> None: ...

class DelayResponsesUpdate(_message.Message):
    __slots__ = ("delay_responses",)
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    delay_responses: _containers.RepeatedCompositeFieldContainer[DelayResponseUpdate]
    def __init__(self, delay_responses: _Optional[_Iterable[_Union[DelayResponseUpdate, _Mapping]]] = ...) -> None: ...

class Function_UpdateLatencyControl(_message.Message):
    __slots__ = ("function_id", "enabled", "delay_responses", "initial_delay", "interval")
    FUNCTION_ID_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    INITIAL_DELAY_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    function_id: str
    enabled: bool
    delay_responses: DelayResponsesUpdate
    initial_delay: int
    interval: int
    def __init__(self, function_id: _Optional[str] = ..., enabled: bool = ..., delay_responses: _Optional[_Union[DelayResponsesUpdate, _Mapping]] = ..., initial_delay: _Optional[int] = ..., interval: _Optional[int] = ...) -> None: ...
