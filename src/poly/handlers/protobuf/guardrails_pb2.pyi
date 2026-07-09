from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GuardrailName(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    GUARDRAIL_NAME_UNSPECIFIED: _ClassVar[GuardrailName]
    GUARDRAIL_NAME_JAILBREAK_DEFENCE: _ClassVar[GuardrailName]
    GUARDRAIL_NAME_HALLUCINATION_CONTROL: _ClassVar[GuardrailName]
    GUARDRAIL_NAME_AI_IDENTITY: _ClassVar[GuardrailName]
    GUARDRAIL_NAME_EMERGENCY_ESCALATION: _ClassVar[GuardrailName]
    GUARDRAIL_NAME_TOOL_CALL_INTEGRITY: _ClassVar[GuardrailName]
GUARDRAIL_NAME_UNSPECIFIED: GuardrailName
GUARDRAIL_NAME_JAILBREAK_DEFENCE: GuardrailName
GUARDRAIL_NAME_HALLUCINATION_CONTROL: GuardrailName
GUARDRAIL_NAME_AI_IDENTITY: GuardrailName
GUARDRAIL_NAME_EMERGENCY_ESCALATION: GuardrailName
GUARDRAIL_NAME_TOOL_CALL_INTEGRITY: GuardrailName

class Guardrail(_message.Message):
    __slots__ = ("name", "enabled")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    name: GuardrailName
    enabled: bool
    def __init__(self, name: _Optional[_Union[GuardrailName, str]] = ..., enabled: bool = ...) -> None: ...

class Guardrails(_message.Message):
    __slots__ = ("guardrails", "updated_by", "updated_at", "custom_guardrails")
    GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    guardrails: _containers.RepeatedCompositeFieldContainer[Guardrail]
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    custom_guardrails: _containers.RepeatedCompositeFieldContainer[CustomGuardrail]
    def __init__(self, guardrails: _Optional[_Iterable[_Union[Guardrail, _Mapping]]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., custom_guardrails: _Optional[_Iterable[_Union[CustomGuardrail, _Mapping]]] = ...) -> None: ...

class Guardrails_UpdateGuardrails(_message.Message):
    __slots__ = ("guardrails",)
    GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    guardrails: _containers.RepeatedCompositeFieldContainer[Guardrail]
    def __init__(self, guardrails: _Optional[_Iterable[_Union[Guardrail, _Mapping]]] = ...) -> None: ...

class CustomGuardrailReferences(_message.Message):
    __slots__ = ("sms", "handoff", "attributes", "global_functions", "variables", "translations")
    class SmsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class HandoffEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class AttributesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class GlobalFunctionsEntry(_message.Message):
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
    class TranslationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    SMS_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    sms: _containers.ScalarMap[str, bool]
    handoff: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    global_functions: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    translations: _containers.ScalarMap[str, bool]
    def __init__(self, sms: _Optional[_Mapping[str, bool]] = ..., handoff: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., global_functions: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ..., translations: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class CustomGuardrail(_message.Message):
    __slots__ = ("id", "name", "prompt", "action", "enabled", "references", "created_at", "created_by", "updated_at", "updated_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    action: str
    enabled: bool
    references: CustomGuardrailReferences
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., action: _Optional[str] = ..., enabled: bool = ..., references: _Optional[_Union[CustomGuardrailReferences, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class CustomGuardrails(_message.Message):
    __slots__ = ("custom_guardrails",)
    CUSTOM_GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    custom_guardrails: _containers.RepeatedCompositeFieldContainer[CustomGuardrail]
    def __init__(self, custom_guardrails: _Optional[_Iterable[_Union[CustomGuardrail, _Mapping]]] = ...) -> None: ...

class Guardrails_CreateCustomGuardrail(_message.Message):
    __slots__ = ("id", "name", "prompt", "action", "enabled", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    action: str
    enabled: bool
    references: CustomGuardrailReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., action: _Optional[str] = ..., enabled: bool = ..., references: _Optional[_Union[CustomGuardrailReferences, _Mapping]] = ...) -> None: ...

class Guardrails_UpdateCustomGuardrail(_message.Message):
    __slots__ = ("id", "name", "prompt", "action", "enabled", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    action: str
    enabled: bool
    references: CustomGuardrailReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., action: _Optional[str] = ..., enabled: bool = ..., references: _Optional[_Union[CustomGuardrailReferences, _Mapping]] = ...) -> None: ...

class Guardrails_DeleteCustomGuardrail(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...
