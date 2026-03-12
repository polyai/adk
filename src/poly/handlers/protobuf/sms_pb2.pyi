from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SMSEnvPhoneNumbers(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: str
    pre_release: str
    live: str
    def __init__(self, sandbox: _Optional[str] = ..., pre_release: _Optional[str] = ..., live: _Optional[str] = ...) -> None: ...

class SMSTemplateReferences(_message.Message):
    __slots__ = ("topics", "flow_steps", "variables")
    class TopicsEntry(_message.Message):
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
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.ScalarMap[str, bool]
    flow_steps: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, topics: _Optional[_Mapping[str, bool]] = ..., flow_steps: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class SMS(_message.Message):
    __slots__ = ("templates",)
    TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    templates: _containers.RepeatedCompositeFieldContainer[SMSTemplate]
    def __init__(self, templates: _Optional[_Iterable[_Union[SMSTemplate, _Mapping]]] = ...) -> None: ...

class SMSTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "env_phone_numbers", "references", "created_at", "created_by", "updated_at", "updated_by", "active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ENV_PHONE_NUMBERS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    env_phone_numbers: SMSEnvPhoneNumbers
    references: SMSTemplateReferences
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., env_phone_numbers: _Optional[_Union[SMSEnvPhoneNumbers, _Mapping]] = ..., references: _Optional[_Union[SMSTemplateReferences, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., active: bool = ...) -> None: ...

class SMS_CreateTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "env_phone_numbers", "references", "active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ENV_PHONE_NUMBERS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    env_phone_numbers: SMSEnvPhoneNumbers
    references: SMSTemplateReferences
    active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., env_phone_numbers: _Optional[_Union[SMSEnvPhoneNumbers, _Mapping]] = ..., references: _Optional[_Union[SMSTemplateReferences, _Mapping]] = ..., active: bool = ...) -> None: ...

class UpdateSMSEnvPhoneNumbers(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: str
    pre_release: str
    live: str
    def __init__(self, sandbox: _Optional[str] = ..., pre_release: _Optional[str] = ..., live: _Optional[str] = ...) -> None: ...

class SMS_UpdateTemplate(_message.Message):
    __slots__ = ("id", "name", "text", "env_phone_numbers", "references", "active")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    ENV_PHONE_NUMBERS_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    text: str
    env_phone_numbers: UpdateSMSEnvPhoneNumbers
    references: SMSTemplateReferences
    active: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., text: _Optional[str] = ..., env_phone_numbers: _Optional[_Union[UpdateSMSEnvPhoneNumbers, _Mapping]] = ..., references: _Optional[_Union[SMSTemplateReferences, _Mapping]] = ..., active: bool = ...) -> None: ...

class SMS_DeleteTemplate(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...
