from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class HandoffChannel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HANDOFF_CHANNEL_UNSPECIFIED: _ClassVar[HandoffChannel]
    HANDOFF_CHANNEL_CALL: _ClassVar[HandoffChannel]
    HANDOFF_CHANNEL_CHAT: _ClassVar[HandoffChannel]

class HandoffReasonAvailability(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    HANDOFF_REASON_AVAILABILITY_ALWAYS: _ClassVar[HandoffReasonAvailability]
    HANDOFF_REASON_AVAILABILITY_RETRIEVED: _ClassVar[HandoffReasonAvailability]
HANDOFF_CHANNEL_UNSPECIFIED: HandoffChannel
HANDOFF_CHANNEL_CALL: HandoffChannel
HANDOFF_CHANNEL_CHAT: HandoffChannel
HANDOFF_REASON_AVAILABILITY_ALWAYS: HandoffReasonAvailability
HANDOFF_REASON_AVAILABILITY_RETRIEVED: HandoffReasonAvailability

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

class HandoffTransferOutcome(_message.Message):
    __slots__ = ("destination_id", "wording")
    DESTINATION_ID_FIELD_NUMBER: _ClassVar[int]
    WORDING_FIELD_NUMBER: _ClassVar[int]
    destination_id: str
    wording: str
    def __init__(self, destination_id: _Optional[str] = ..., wording: _Optional[str] = ...) -> None: ...

class HandoffMessageOutcome(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class HandoffNotOfferedOutcome(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HandoffReasonOutcome(_message.Message):
    __slots__ = ("transfer", "message", "not_offered")
    TRANSFER_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    NOT_OFFERED_FIELD_NUMBER: _ClassVar[int]
    transfer: HandoffTransferOutcome
    message: HandoffMessageOutcome
    not_offered: HandoffNotOfferedOutcome
    def __init__(self, transfer: _Optional[_Union[HandoffTransferOutcome, _Mapping]] = ..., message: _Optional[_Union[HandoffMessageOutcome, _Mapping]] = ..., not_offered: _Optional[_Union[HandoffNotOfferedOutcome, _Mapping]] = ...) -> None: ...

class HandoffReasonOutcomes(_message.Message):
    __slots__ = ("call", "chat")
    CALL_FIELD_NUMBER: _ClassVar[int]
    CHAT_FIELD_NUMBER: _ClassVar[int]
    call: HandoffReasonOutcome
    chat: HandoffReasonOutcome
    def __init__(self, call: _Optional[_Union[HandoffReasonOutcome, _Mapping]] = ..., chat: _Optional[_Union[HandoffReasonOutcome, _Mapping]] = ...) -> None: ...

class Handoffs(_message.Message):
    __slots__ = ("handoffs", "reasons", "settings")
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    REASONS_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    handoffs: _containers.RepeatedCompositeFieldContainer[HandoffConfig]
    reasons: _containers.RepeatedCompositeFieldContainer[HandoffReason]
    settings: HandoffSettings
    def __init__(self, handoffs: _Optional[_Iterable[_Union[HandoffConfig, _Mapping]]] = ..., reasons: _Optional[_Iterable[_Union[HandoffReason, _Mapping]]] = ..., settings: _Optional[_Union[HandoffSettings, _Mapping]] = ...) -> None: ...

class HandoffReason(_message.Message):
    __slots__ = ("id", "key", "name", "description", "availability", "example_phrases", "outcomes", "active", "created_by", "created_at", "updated_by", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    EXAMPLE_PHRASES_FIELD_NUMBER: _ClassVar[int]
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    key: str
    name: str
    description: str
    availability: HandoffReasonAvailability
    example_phrases: _containers.RepeatedScalarFieldContainer[str]
    outcomes: HandoffReasonOutcomes
    active: bool
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., key: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., availability: _Optional[_Union[HandoffReasonAvailability, str]] = ..., example_phrases: _Optional[_Iterable[str]] = ..., outcomes: _Optional[_Union[HandoffReasonOutcomes, _Mapping]] = ..., active: bool = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class HandoffSettings(_message.Message):
    __slots__ = ("call_transfer_message", "chat_transfer_message", "seed_default_reasons")
    CALL_TRANSFER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CHAT_TRANSFER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SEED_DEFAULT_REASONS_FIELD_NUMBER: _ClassVar[int]
    call_transfer_message: str
    chat_transfer_message: str
    seed_default_reasons: bool
    def __init__(self, call_transfer_message: _Optional[str] = ..., chat_transfer_message: _Optional[str] = ..., seed_default_reasons: bool = ...) -> None: ...

class HandoffConfig(_message.Message):
    __slots__ = ("id", "name", "created_by", "created_at", "description", "sip_config", "sip_headers", "active", "updated_by", "updated_at", "references", "is_default", "skip_test_call_transfers")
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
    SKIP_TEST_CALL_TRANSFERS_FIELD_NUMBER: _ClassVar[int]
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
    skip_test_call_transfers: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ..., is_default: bool = ..., skip_test_call_transfers: bool = ...) -> None: ...

class Handoff_Create(_message.Message):
    __slots__ = ("id", "name", "description", "sip_config", "sip_headers", "active", "references", "skip_test_call_transfers")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    SKIP_TEST_CALL_TRANSFERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    references: HandoffReferences
    skip_test_call_transfers: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ..., skip_test_call_transfers: bool = ...) -> None: ...

class Handoff_Update(_message.Message):
    __slots__ = ("id", "name", "description", "sip_config", "sip_headers", "active", "references", "skip_test_call_transfers")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    SKIP_TEST_CALL_TRANSFERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    references: HandoffReferences
    skip_test_call_transfers: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ..., skip_test_call_transfers: bool = ...) -> None: ...

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

class HandoffReason_Create(_message.Message):
    __slots__ = ("id", "name", "key", "description", "availability", "outcomes")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    KEY_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    key: str
    description: str
    availability: HandoffReasonAvailability
    outcomes: HandoffReasonOutcomes
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., key: _Optional[str] = ..., description: _Optional[str] = ..., availability: _Optional[_Union[HandoffReasonAvailability, str]] = ..., outcomes: _Optional[_Union[HandoffReasonOutcomes, _Mapping]] = ...) -> None: ...

class HandoffReason_Update(_message.Message):
    __slots__ = ("id", "name", "description", "outcomes", "availability")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    OUTCOMES_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    outcomes: HandoffReasonOutcomes
    availability: HandoffReasonAvailability
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., outcomes: _Optional[_Union[HandoffReasonOutcomes, _Mapping]] = ..., availability: _Optional[_Union[HandoffReasonAvailability, str]] = ...) -> None: ...

class HandoffReason_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class HandoffSettings_SetTransferMessage(_message.Message):
    __slots__ = ("channel", "message")
    CHANNEL_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    channel: HandoffChannel
    message: str
    def __init__(self, channel: _Optional[_Union[HandoffChannel, str]] = ..., message: _Optional[str] = ...) -> None: ...

class Handoff_Duplicate(_message.Message):
    __slots__ = ("id", "name", "description", "sip_config", "sip_headers", "active", "references", "source_handoff_id", "skip_test_call_transfers")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    SIP_CONFIG_FIELD_NUMBER: _ClassVar[int]
    SIP_HEADERS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    SOURCE_HANDOFF_ID_FIELD_NUMBER: _ClassVar[int]
    SKIP_TEST_CALL_TRANSFERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    sip_config: SipConfig
    sip_headers: SipHeaders
    active: bool
    references: HandoffReferences
    source_handoff_id: str
    skip_test_call_transfers: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., sip_config: _Optional[_Union[SipConfig, _Mapping]] = ..., sip_headers: _Optional[_Union[SipHeaders, _Mapping]] = ..., active: bool = ..., references: _Optional[_Union[HandoffReferences, _Mapping]] = ..., source_handoff_id: _Optional[str] = ..., skip_test_call_transfers: bool = ...) -> None: ...
