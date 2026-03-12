from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HandoffReferences(_message.Message):
    __slots__ = ("topics", "flow_steps")
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
    TOPICS_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    topics: _containers.ScalarMap[str, bool]
    flow_steps: _containers.ScalarMap[str, bool]
    def __init__(self, topics: _Optional[_Mapping[str, bool]] = ..., flow_steps: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class SipConfig(_message.Message):
    __slots__ = ("invite", "refer", "bye")
    INVITE_FIELD_NUMBER: _ClassVar[int]
    REFER_FIELD_NUMBER: _ClassVar[int]
    BYE_FIELD_NUMBER: _ClassVar[int]
    invite: SipInviteHandoffConfig
    refer: SipReferHandoffConfig
    bye: SipByeHandoffConfig
    def __init__(self, invite: _Optional[_Union[SipInviteHandoffConfig, _Mapping]] = ..., refer: _Optional[_Union[SipReferHandoffConfig, _Mapping]] = ..., bye: _Optional[_Union[SipByeHandoffConfig, _Mapping]] = ...) -> None: ...

class SipInviteHandoffConfig(_message.Message):
    __slots__ = ("phone_number", "outbound_endpoint", "outbound_encryption")
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    OUTBOUND_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    OUTBOUND_ENCRYPTION_FIELD_NUMBER: _ClassVar[int]
    phone_number: str
    outbound_endpoint: str
    outbound_encryption: str
    def __init__(self, phone_number: _Optional[str] = ..., outbound_endpoint: _Optional[str] = ..., outbound_encryption: _Optional[str] = ...) -> None: ...

class SipReferHandoffConfig(_message.Message):
    __slots__ = ("phone_number",)
    PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    phone_number: str
    def __init__(self, phone_number: _Optional[str] = ...) -> None: ...

class SipByeHandoffConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SipHeaders(_message.Message):
    __slots__ = ("headers",)
    HEADERS_FIELD_NUMBER: _ClassVar[int]
    headers: _containers.RepeatedCompositeFieldContainer[SipHeader]
    def __init__(self, headers: _Optional[_Iterable[_Union[SipHeader, _Mapping]]] = ...) -> None: ...

class SipHeader(_message.Message):
    __slots__ = ("key", "value")
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    key: str
    value: str
    def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class Handoffs(_message.Message):
    __slots__ = ("handoffs",)
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    handoffs: _containers.RepeatedCompositeFieldContainer[HandoffConfig]
    def __init__(self, handoffs: _Optional[_Iterable[_Union[HandoffConfig, _Mapping]]] = ...) -> None: ...

class HandoffConfig(_message.Message):
    __slots__ = ("id", "name", "created_by", "created_at", "description", "sip_config", "sip_headers", "active", "updated_by", "updated_at", "references", "is_default")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    references: HandoffReferences
    is_default: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ..., is_default: bool = ...) -> None: ...

class Handoff_Create(_message.Message):
    __slots__ = ("id", "name", "description", "sip_config", "sip_headers", "active", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    references: HandoffReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ...) -> None: ...

class Handoff_Update(_message.Message):
    __slots__ = ("id", "name", "description", "sip_config", "sip_headers", "active", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    references: HandoffReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ...) -> None: ...

class Handoff_SetDefault(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Handoff_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class Handoff_ResetHandoffConfigs(_message.Message):
    __slots__ = ("sip_config", "sip_headers")
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    sip_config: SipConfig
    sip_headers: SipHeaders
    def __init__(self, sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ...) -> None: ...
