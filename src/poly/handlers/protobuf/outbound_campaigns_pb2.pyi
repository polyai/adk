from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OutboundCampaign(_message.Message):
    __slots__ = ("id", "name", "nodes", "archived", "created_by", "created_at", "updated_by", "updated_at", "status", "settings", "published_nodes", "description")
    class NodesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: OutboundCampaignNode
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[OutboundCampaignNode, _Mapping]] = ...) -> None: ...
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    NODES_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    PUBLISHED_NODES_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    nodes: _containers.MessageMap[str, OutboundCampaignNode]
    archived: bool
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    status: str
    settings: OutboundCampaignSettings
    published_nodes: PublishedNodes
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., nodes: _Optional[_Mapping[str, OutboundCampaignNode]] = ..., archived: bool = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., status: _Optional[str] = ..., settings: _Optional[_Union[OutboundCampaignSettings, _Mapping]] = ..., published_nodes: _Optional[_Union[PublishedNodes, _Mapping]] = ..., description: _Optional[str] = ...) -> None: ...

class PublishedNodes(_message.Message):
    __slots__ = ("nodes",)
    class NodesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: OutboundCampaignNode
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[OutboundCampaignNode, _Mapping]] = ...) -> None: ...
    NODES_FIELD_NUMBER: _ClassVar[int]
    nodes: _containers.MessageMap[str, OutboundCampaignNode]
    def __init__(self, nodes: _Optional[_Mapping[str, OutboundCampaignNode]] = ...) -> None: ...

class DispatchLimits(_message.Message):
    __slots__ = ("max_concurrent", "per_hour", "per_day")
    MAX_CONCURRENT_FIELD_NUMBER: _ClassVar[int]
    PER_HOUR_FIELD_NUMBER: _ClassVar[int]
    PER_DAY_FIELD_NUMBER: _ClassVar[int]
    max_concurrent: int
    per_hour: int
    per_day: int
    def __init__(self, max_concurrent: _Optional[int] = ..., per_hour: _Optional[int] = ..., per_day: _Optional[int] = ...) -> None: ...

class ContactWindow(_message.Message):
    __slots__ = ("days_of_week", "start_time", "end_time")
    DAYS_OF_WEEK_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    days_of_week: _containers.RepeatedScalarFieldContainer[str]
    start_time: str
    end_time: str
    def __init__(self, days_of_week: _Optional[_Iterable[str]] = ..., start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class OutboundCampaignSettings(_message.Message):
    __slots__ = ("start_date", "end_date", "from_number", "sms_from_number", "default_variant_id", "daily_contact_limit", "default_timezone", "voice_dispatch_limits", "sms_dispatch_limits", "contact_window", "country", "use_case")
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    FROM_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SMS_FROM_NUMBER_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_VARIANT_ID_FIELD_NUMBER: _ClassVar[int]
    DAILY_CONTACT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_TIMEZONE_FIELD_NUMBER: _ClassVar[int]
    VOICE_DISPATCH_LIMITS_FIELD_NUMBER: _ClassVar[int]
    SMS_DISPATCH_LIMITS_FIELD_NUMBER: _ClassVar[int]
    CONTACT_WINDOW_FIELD_NUMBER: _ClassVar[int]
    COUNTRY_FIELD_NUMBER: _ClassVar[int]
    USE_CASE_FIELD_NUMBER: _ClassVar[int]
    start_date: str
    end_date: str
    from_number: str
    sms_from_number: str
    default_variant_id: str
    daily_contact_limit: int
    default_timezone: str
    voice_dispatch_limits: DispatchLimits
    sms_dispatch_limits: DispatchLimits
    contact_window: ContactWindow
    country: str
    use_case: str
    def __init__(self, start_date: _Optional[str] = ..., end_date: _Optional[str] = ..., from_number: _Optional[str] = ..., sms_from_number: _Optional[str] = ..., default_variant_id: _Optional[str] = ..., daily_contact_limit: _Optional[int] = ..., default_timezone: _Optional[str] = ..., voice_dispatch_limits: _Optional[_Union[DispatchLimits, _Mapping]] = ..., sms_dispatch_limits: _Optional[_Union[DispatchLimits, _Mapping]] = ..., contact_window: _Optional[_Union[ContactWindow, _Mapping]] = ..., country: _Optional[str] = ..., use_case: _Optional[str] = ...) -> None: ...

class OutboundCampaignNode(_message.Message):
    __slots__ = ("id", "position", "label", "trigger", "call", "sms", "conditional", "wait", "writeback", "end")
    ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    CALL_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_FIELD_NUMBER: _ClassVar[int]
    WAIT_FIELD_NUMBER: _ClassVar[int]
    WRITEBACK_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    id: str
    position: Position
    label: str
    trigger: TriggerNodeData
    call: CallNodeData
    sms: SmsNodeData
    conditional: ConditionalNodeData
    wait: WaitNodeData
    writeback: WritebackNodeData
    end: EndNodeData
    def __init__(self, id: _Optional[str] = ..., position: _Optional[_Union[Position, _Mapping]] = ..., label: _Optional[str] = ..., trigger: _Optional[_Union[TriggerNodeData, _Mapping]] = ..., call: _Optional[_Union[CallNodeData, _Mapping]] = ..., sms: _Optional[_Union[SmsNodeData, _Mapping]] = ..., conditional: _Optional[_Union[ConditionalNodeData, _Mapping]] = ..., wait: _Optional[_Union[WaitNodeData, _Mapping]] = ..., writeback: _Optional[_Union[WritebackNodeData, _Mapping]] = ..., end: _Optional[_Union[EndNodeData, _Mapping]] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class RouteEdge(_message.Message):
    __slots__ = ("target_node_id", "outcome")
    TARGET_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    OUTCOME_FIELD_NUMBER: _ClassVar[int]
    target_node_id: str
    outcome: str
    def __init__(self, target_node_id: _Optional[str] = ..., outcome: _Optional[str] = ...) -> None: ...

class CampaignFunctionParameter(_message.Message):
    __slots__ = ("id", "name", "description", "type", "created_by", "created_at", "updated_by", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    type: str
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., type: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[str] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...

class CampaignNodeFunction(_message.Message):
    __slots__ = ("name", "description", "code", "parameters")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    code: str
    parameters: _containers.RepeatedCompositeFieldContainer[CampaignFunctionParameter]
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., code: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[CampaignFunctionParameter, _Mapping]]] = ...) -> None: ...

class TriggerNodeData(_message.Message):
    __slots__ = ("function", "routes", "campaign_function", "source_type", "ingest_interval")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    ROUTES_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    INGEST_INTERVAL_FIELD_NUMBER: _ClassVar[int]
    function: str
    routes: _containers.RepeatedCompositeFieldContainer[RouteEdge]
    campaign_function: CampaignNodeFunction
    source_type: str
    ingest_interval: str
    def __init__(self, function: _Optional[str] = ..., routes: _Optional[_Iterable[_Union[RouteEdge, _Mapping]]] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ..., source_type: _Optional[str] = ..., ingest_interval: _Optional[str] = ...) -> None: ...

class CallNodeData(_message.Message):
    __slots__ = ("flow_name", "function", "greeting", "voicemail_enabled", "voicemail_script", "voicemail_when", "max_attempts", "backoff", "backoff_unit", "routes", "default_route", "campaign_function", "amd_flow_name")
    FLOW_NAME_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    GREETING_FIELD_NUMBER: _ClassVar[int]
    VOICEMAIL_ENABLED_FIELD_NUMBER: _ClassVar[int]
    VOICEMAIL_SCRIPT_FIELD_NUMBER: _ClassVar[int]
    VOICEMAIL_WHEN_FIELD_NUMBER: _ClassVar[int]
    MAX_ATTEMPTS_FIELD_NUMBER: _ClassVar[int]
    BACKOFF_FIELD_NUMBER: _ClassVar[int]
    BACKOFF_UNIT_FIELD_NUMBER: _ClassVar[int]
    ROUTES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ROUTE_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    AMD_FLOW_NAME_FIELD_NUMBER: _ClassVar[int]
    flow_name: str
    function: str
    greeting: str
    voicemail_enabled: bool
    voicemail_script: str
    voicemail_when: str
    max_attempts: int
    backoff: int
    backoff_unit: str
    routes: _containers.RepeatedCompositeFieldContainer[RouteEdge]
    default_route: str
    campaign_function: CampaignNodeFunction
    amd_flow_name: str
    def __init__(self, flow_name: _Optional[str] = ..., function: _Optional[str] = ..., greeting: _Optional[str] = ..., voicemail_enabled: bool = ..., voicemail_script: _Optional[str] = ..., voicemail_when: _Optional[str] = ..., max_attempts: _Optional[int] = ..., backoff: _Optional[int] = ..., backoff_unit: _Optional[str] = ..., routes: _Optional[_Iterable[_Union[RouteEdge, _Mapping]]] = ..., default_route: _Optional[str] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ..., amd_flow_name: _Optional[str] = ...) -> None: ...

class SmsNodeData(_message.Message):
    __slots__ = ("function", "message_template", "reply_flow_name", "reply_timeout_value", "reply_timeout_unit", "routes", "default_route", "campaign_function")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    REPLY_FLOW_NAME_FIELD_NUMBER: _ClassVar[int]
    REPLY_TIMEOUT_VALUE_FIELD_NUMBER: _ClassVar[int]
    REPLY_TIMEOUT_UNIT_FIELD_NUMBER: _ClassVar[int]
    ROUTES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ROUTE_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    function: str
    message_template: str
    reply_flow_name: str
    reply_timeout_value: int
    reply_timeout_unit: str
    routes: _containers.RepeatedCompositeFieldContainer[RouteEdge]
    default_route: str
    campaign_function: CampaignNodeFunction
    def __init__(self, function: _Optional[str] = ..., message_template: _Optional[str] = ..., reply_flow_name: _Optional[str] = ..., reply_timeout_value: _Optional[int] = ..., reply_timeout_unit: _Optional[str] = ..., routes: _Optional[_Iterable[_Union[RouteEdge, _Mapping]]] = ..., default_route: _Optional[str] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ...) -> None: ...

class ConditionalBranch(_message.Message):
    __slots__ = ("id", "variable", "target_node_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    TARGET_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    variable: str
    target_node_id: str
    def __init__(self, id: _Optional[str] = ..., variable: _Optional[str] = ..., target_node_id: _Optional[str] = ...) -> None: ...

class ConditionalNodeData(_message.Message):
    __slots__ = ("function", "branches", "default_target_node_id", "campaign_function")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    BRANCHES_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_TARGET_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    function: str
    branches: _containers.RepeatedCompositeFieldContainer[ConditionalBranch]
    default_target_node_id: str
    campaign_function: CampaignNodeFunction
    def __init__(self, function: _Optional[str] = ..., branches: _Optional[_Iterable[_Union[ConditionalBranch, _Mapping]]] = ..., default_target_node_id: _Optional[str] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ...) -> None: ...

class WaitNodeData(_message.Message):
    __slots__ = ("amount", "unit", "target_node_id")
    AMOUNT_FIELD_NUMBER: _ClassVar[int]
    UNIT_FIELD_NUMBER: _ClassVar[int]
    TARGET_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    amount: int
    unit: str
    target_node_id: str
    def __init__(self, amount: _Optional[int] = ..., unit: _Optional[str] = ..., target_node_id: _Optional[str] = ...) -> None: ...

class WritebackNodeData(_message.Message):
    __slots__ = ("target", "function", "target_node_id", "campaign_function")
    TARGET_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    TARGET_NODE_ID_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    target: str
    function: str
    target_node_id: str
    campaign_function: CampaignNodeFunction
    def __init__(self, target: _Optional[str] = ..., function: _Optional[str] = ..., target_node_id: _Optional[str] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ...) -> None: ...

class EndNodeData(_message.Message):
    __slots__ = ("exit_reason", "writeback_enabled", "function", "campaign_function")
    EXIT_REASON_FIELD_NUMBER: _ClassVar[int]
    WRITEBACK_ENABLED_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CAMPAIGN_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    exit_reason: str
    writeback_enabled: bool
    function: str
    campaign_function: CampaignNodeFunction
    def __init__(self, exit_reason: _Optional[str] = ..., writeback_enabled: bool = ..., function: _Optional[str] = ..., campaign_function: _Optional[_Union[CampaignNodeFunction, _Mapping]] = ...) -> None: ...

class OutboundCampaigns(_message.Message):
    __slots__ = ("outbound_campaigns",)
    OUTBOUND_CAMPAIGNS_FIELD_NUMBER: _ClassVar[int]
    outbound_campaigns: _containers.RepeatedCompositeFieldContainer[OutboundCampaign]
    def __init__(self, outbound_campaigns: _Optional[_Iterable[_Union[OutboundCampaign, _Mapping]]] = ...) -> None: ...

class OutboundCampaign_Create(_message.Message):
    __slots__ = ("id", "name", "description")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class OutboundCampaign_Update(_message.Message):
    __slots__ = ("id", "name", "description", "clear_description")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CLEAR_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    clear_description: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., clear_description: bool = ...) -> None: ...

class OutboundCampaign_Delete(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_ArchiveDefinition(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_UpdateSettings(_message.Message):
    __slots__ = ("id", "settings")
    ID_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    id: str
    settings: OutboundCampaignSettings
    def __init__(self, id: _Optional[str] = ..., settings: _Optional[_Union[OutboundCampaignSettings, _Mapping]] = ...) -> None: ...

class OutboundCampaign_Publish(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_Pause(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_Resume(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_Validate(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class OutboundCampaign_CreateNode(_message.Message):
    __slots__ = ("outbound_campaign_id", "node")
    OUTBOUND_CAMPAIGN_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    outbound_campaign_id: str
    node: OutboundCampaignNode
    def __init__(self, outbound_campaign_id: _Optional[str] = ..., node: _Optional[_Union[OutboundCampaignNode, _Mapping]] = ...) -> None: ...

class OutboundCampaign_UpdateNode(_message.Message):
    __slots__ = ("outbound_campaign_id", "node_id", "data", "position", "label")
    OUTBOUND_CAMPAIGN_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    outbound_campaign_id: str
    node_id: str
    data: OutboundCampaignNodeData
    position: Position
    label: str
    def __init__(self, outbound_campaign_id: _Optional[str] = ..., node_id: _Optional[str] = ..., data: _Optional[_Union[OutboundCampaignNodeData, _Mapping]] = ..., position: _Optional[_Union[Position, _Mapping]] = ..., label: _Optional[str] = ...) -> None: ...

class OutboundCampaign_DeleteNode(_message.Message):
    __slots__ = ("outbound_campaign_id", "node_id")
    OUTBOUND_CAMPAIGN_ID_FIELD_NUMBER: _ClassVar[int]
    NODE_ID_FIELD_NUMBER: _ClassVar[int]
    outbound_campaign_id: str
    node_id: str
    def __init__(self, outbound_campaign_id: _Optional[str] = ..., node_id: _Optional[str] = ...) -> None: ...

class OutboundCampaignNodeData(_message.Message):
    __slots__ = ("trigger", "call", "sms", "conditional", "wait", "writeback", "end")
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    CALL_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_FIELD_NUMBER: _ClassVar[int]
    WAIT_FIELD_NUMBER: _ClassVar[int]
    WRITEBACK_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    trigger: TriggerNodeData
    call: CallNodeData
    sms: SmsNodeData
    conditional: ConditionalNodeData
    wait: WaitNodeData
    writeback: WritebackNodeData
    end: EndNodeData
    def __init__(self, trigger: _Optional[_Union[TriggerNodeData, _Mapping]] = ..., call: _Optional[_Union[CallNodeData, _Mapping]] = ..., sms: _Optional[_Union[SmsNodeData, _Mapping]] = ..., conditional: _Optional[_Union[ConditionalNodeData, _Mapping]] = ..., wait: _Optional[_Union[WaitNodeData, _Mapping]] = ..., writeback: _Optional[_Union[WritebackNodeData, _Mapping]] = ..., end: _Optional[_Union[EndNodeData, _Mapping]] = ...) -> None: ...
