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
    __slots__ = ("guardrails", "updated_by", "updated_at")
    GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    guardrails: _containers.RepeatedCompositeFieldContainer[Guardrail]
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, guardrails: _Optional[_Iterable[_Union[Guardrail, _Mapping]]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Guardrails_UpdateGuardrails(_message.Message):
    __slots__ = ("guardrails",)
    GUARDRAILS_FIELD_NUMBER: _ClassVar[int]
    guardrails: _containers.RepeatedCompositeFieldContainer[Guardrail]
    def __init__(self, guardrails: _Optional[_Iterable[_Union[Guardrail, _Mapping]]] = ...) -> None: ...
