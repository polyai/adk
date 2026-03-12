from google.protobuf import timestamp_pb2 as _timestamp_pb2
from poly.handlers.protobuf import functions_pb2 as _functions_pb2
from poly.handlers.protobuf import handoff_pb2 as _handoff_pb2
from poly.handlers.protobuf import sms_pb2 as _sms_pb2
from poly.handlers.protobuf import variant_pb2 as _variant_pb2
from poly.handlers.protobuf import entities_pb2 as _entities_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Flow(_message.Message):
    __slots__ = ("id", "name", "description", "created_at", "created_by", "updated_at", "updated_by", "start_step_id", "transition_functions", "steps", "no_code_steps", "flow_steps")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    START_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    start_step_id: str
    transition_functions: _containers.RepeatedCompositeFieldContainer[TransitionFunction]
    steps: _containers.RepeatedCompositeFieldContainer[AdvancedStep]
    no_code_steps: _containers.RepeatedCompositeFieldContainer[DefaultStep]
    flow_steps: _containers.RepeatedCompositeFieldContainer[Step]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., start_step_id: _Optional[str] = ..., transition_functions: _Optional[_Iterable[_Union[TransitionFunction, _Mapping]]] = ..., steps: _Optional[_Iterable[_Union[AdvancedStep, _Mapping]]] = ..., no_code_steps: _Optional[_Iterable[_Union[DefaultStep, _Mapping]]] = ..., flow_steps: _Optional[_Iterable[_Union[Step, _Mapping]]] = ...) -> None: ...

class Flows(_message.Message):
    __slots__ = ("flows",)
    FLOWS_FIELD_NUMBER: _ClassVar[int]
    flows: _containers.RepeatedCompositeFieldContainer[Flow]
    def __init__(self, flows: _Optional[_Iterable[_Union[Flow, _Mapping]]] = ...) -> None: ...

class AdvancedStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "created_at", "created_by", "updated_at", "updated_by", "position", "asr_biasing", "dtmf_config", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    ASR_BIASING_FIELD_NUMBER: _ClassVar[int]
    DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    position: StepPosition
    asr_biasing: StepAsrConfig
    dtmf_config: StepDtmfConfig
    references: StepReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., asr_biasing: _Optional[_Union[StepAsrConfig, _Mapping]] = ..., dtmf_config: _Optional[_Union[StepDtmfConfig, _Mapping]] = ..., references: _Optional[_Union[StepReferences, _Mapping]] = ...) -> None: ...

class DefaultStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "created_at", "created_by", "updated_at", "updated_by", "position", "references", "conditions")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    position: StepPosition
    references: NoCodeStepReferences
    conditions: _containers.RepeatedCompositeFieldContainer[Condition]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., references: _Optional[_Union[NoCodeStepReferences, _Mapping]] = ..., conditions: _Optional[_Iterable[_Union[Condition, _Mapping]]] = ...) -> None: ...

class FunctionStep(_message.Message):
    __slots__ = ("id", "name", "position", "function", "conditions", "created_at", "updated_at", "updated_by", "created_by")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    position: StepPosition
    function: FunctionStepDefinition
    conditions: _containers.RepeatedCompositeFieldContainer[Condition]
    created_at: _timestamp_pb2.Timestamp
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    created_by: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., function: _Optional[_Union[FunctionStepDefinition, _Mapping]] = ..., conditions: _Optional[_Iterable[_Union[Condition, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., created_by: _Optional[str] = ...) -> None: ...

class Step(_message.Message):
    __slots__ = ("advanced_step", "default_step", "function_step")
    ADVANCED_STEP_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_STEP_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    advanced_step: AdvancedStep
    default_step: DefaultStep
    function_step: FunctionStep
    def __init__(self, advanced_step: _Optional[_Union[AdvancedStep, _Mapping]] = ..., default_step: _Optional[_Union[DefaultStep, _Mapping]] = ..., function_step: _Optional[_Union[FunctionStep, _Mapping]] = ...) -> None: ...

class StepReferences(_message.Message):
    __slots__ = ("sms", "handoff", "attributes", "transition_functions", "global_functions", "entities", "variables")
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
    class TransitionFunctionsEntry(_message.Message):
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
    class EntitiesEntry(_message.Message):
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
    SMS_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    sms: _containers.ScalarMap[str, bool]
    handoff: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    transition_functions: _containers.ScalarMap[str, bool]
    global_functions: _containers.ScalarMap[str, bool]
    entities: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, sms: _Optional[_Mapping[str, bool]] = ..., handoff: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., transition_functions: _Optional[_Mapping[str, bool]] = ..., global_functions: _Optional[_Mapping[str, bool]] = ..., entities: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class NoCodeStepReferences(_message.Message):
    __slots__ = ("entities", "attributes", "variables", "extracted_entities")
    class EntitiesEntry(_message.Message):
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
    class VariablesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    class ExtractedEntitiesEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bool
        def __init__(self, key: _Optional[str] = ..., value: bool = ...) -> None: ...
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    EXTRACTED_ENTITIES_FIELD_NUMBER: _ClassVar[int]
    entities: _containers.ScalarMap[str, bool]
    attributes: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    extracted_entities: _containers.ScalarMap[str, bool]
    def __init__(self, entities: _Optional[_Mapping[str, bool]] = ..., attributes: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ..., extracted_entities: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class TransitionFunctionReferences(_message.Message):
    __slots__ = ("flow_steps", "variables")
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
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    flow_steps: _containers.ScalarMap[str, bool]
    variables: _containers.ScalarMap[str, bool]
    def __init__(self, flow_steps: _Optional[_Mapping[str, bool]] = ..., variables: _Optional[_Mapping[str, bool]] = ...) -> None: ...

class TransitionFunction(_message.Message):
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
    parameters: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionParameter]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    latency_control: _functions_pb2.FunctionLatencyControl
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    archived: bool
    references: TransitionFunctionReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[_functions_pb2.FunctionParameter, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[_functions_pb2.FunctionLatencyControl, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., archived: bool = ..., references: _Optional[_Union[TransitionFunctionReferences, _Mapping]] = ...) -> None: ...

class Condition(_message.Message):
    __slots__ = ("id", "exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    id: str
    exit_flow_condition: ExitFlowCondition
    step_condition: AdvancedStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, id: _Optional[str] = ..., exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[AdvancedStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class ConditionDetails(_message.Message):
    __slots__ = ("label", "description", "required_entities", "position", "ingress_position")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_ENTITIES_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    INGRESS_POSITION_FIELD_NUMBER: _ClassVar[int]
    label: str
    description: str
    required_entities: _containers.RepeatedScalarFieldContainer[str]
    position: StepPosition
    ingress_position: str
    def __init__(self, label: _Optional[str] = ..., description: _Optional[str] = ..., required_entities: _Optional[_Iterable[str]] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., ingress_position: _Optional[str] = ...) -> None: ...

class ExitFlowCondition(_message.Message):
    __slots__ = ("details", "exit_flow_position")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_POSITION_FIELD_NUMBER: _ClassVar[int]
    details: ConditionDetails
    exit_flow_position: StepPosition
    def __init__(self, details: _Optional[_Union[ConditionDetails, _Mapping]] = ..., exit_flow_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class AdvancedStepCondition(_message.Message):
    __slots__ = ("details", "child_step_id")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    details: ConditionDetails
    child_step_id: str
    def __init__(self, details: _Optional[_Union[ConditionDetails, _Mapping]] = ..., child_step_id: _Optional[str] = ...) -> None: ...

class NoCodeStepCondition(_message.Message):
    __slots__ = ("details", "child_step_id")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    details: ConditionDetails
    child_step_id: str
    def __init__(self, details: _Optional[_Union[ConditionDetails, _Mapping]] = ..., child_step_id: _Optional[str] = ...) -> None: ...

class FunctionStepCondition(_message.Message):
    __slots__ = ("details", "child_step_id")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    details: ConditionDetails
    child_step_id: str
    def __init__(self, details: _Optional[_Union[ConditionDetails, _Mapping]] = ..., child_step_id: _Optional[str] = ...) -> None: ...

class StepPosition(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class StepAsrConfig(_message.Message):
    __slots__ = ("alphanumeric", "name_spelling", "numeric", "party_size", "precise_date", "relative_date", "single_number", "time", "yes_no", "address", "custom_keywords", "is_enabled")
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    NAME_SPELLING_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    PARTY_SIZE_FIELD_NUMBER: _ClassVar[int]
    PRECISE_DATE_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    SINGLE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    YES_NO_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    alphanumeric: bool
    name_spelling: bool
    numeric: bool
    party_size: bool
    precise_date: bool
    relative_date: bool
    single_number: bool
    time: bool
    yes_no: bool
    address: bool
    custom_keywords: _containers.RepeatedScalarFieldContainer[str]
    is_enabled: bool
    def __init__(self, alphanumeric: bool = ..., name_spelling: bool = ..., numeric: bool = ..., party_size: bool = ..., precise_date: bool = ..., relative_date: bool = ..., single_number: bool = ..., time: bool = ..., yes_no: bool = ..., address: bool = ..., custom_keywords: _Optional[_Iterable[str]] = ..., is_enabled: bool = ...) -> None: ...

class StepDtmfConfig(_message.Message):
    __slots__ = ("is_enabled", "inter_digit_timeout", "max_digits", "end_key", "collect_while_agent_speaking", "is_pii")
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    INTER_DIGIT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    MAX_DIGITS_FIELD_NUMBER: _ClassVar[int]
    END_KEY_FIELD_NUMBER: _ClassVar[int]
    COLLECT_WHILE_AGENT_SPEAKING_FIELD_NUMBER: _ClassVar[int]
    IS_PII_FIELD_NUMBER: _ClassVar[int]
    is_enabled: bool
    inter_digit_timeout: int
    max_digits: int
    end_key: str
    collect_while_agent_speaking: bool
    is_pii: bool
    def __init__(self, is_enabled: bool = ..., inter_digit_timeout: _Optional[int] = ..., max_digits: _Optional[int] = ..., end_key: _Optional[str] = ..., collect_while_agent_speaking: bool = ..., is_pii: bool = ...) -> None: ...

class Flow_CreateFlow(_message.Message):
    __slots__ = ("id", "name", "description", "start_step_id", "steps", "transition_functions", "no_code_steps")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    START_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    start_step_id: str
    steps: _containers.RepeatedCompositeFieldContainer[CreateAdvancedStep]
    transition_functions: _containers.RepeatedCompositeFieldContainer[TransitionFunction_CreateTransitionFunction]
    no_code_steps: _containers.RepeatedCompositeFieldContainer[CreateNoCodeStep]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., start_step_id: _Optional[str] = ..., steps: _Optional[_Iterable[_Union[CreateAdvancedStep, _Mapping]]] = ..., transition_functions: _Optional[_Iterable[_Union[TransitionFunction_CreateTransitionFunction, _Mapping]]] = ..., no_code_steps: _Optional[_Iterable[_Union[CreateNoCodeStep, _Mapping]]] = ...) -> None: ...

class Flow_UpdateFlow(_message.Message):
    __slots__ = ("flow_id", "name", "description", "start_step_id", "old_flow_name")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    START_STEP_ID_FIELD_NUMBER: _ClassVar[int]
    OLD_FLOW_NAME_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    name: str
    description: str
    start_step_id: str
    old_flow_name: str
    def __init__(self, flow_id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., start_step_id: _Optional[str] = ..., old_flow_name: _Optional[str] = ...) -> None: ...

class Flow_DeleteFlow(_message.Message):
    __slots__ = ("flow_id",)
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    def __init__(self, flow_id: _Optional[str] = ...) -> None: ...

class Flow_ImportFlow(_message.Message):
    __slots__ = ("flow_id", "steps", "transition_functions", "global_functions", "handoffs", "sms", "attributes", "no_code_steps", "entities")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    steps: _containers.RepeatedCompositeFieldContainer[ImportFlowStep]
    transition_functions: _containers.RepeatedCompositeFieldContainer[TransitionFunction_CreateTransitionFunction]
    global_functions: _containers.RepeatedCompositeFieldContainer[_functions_pb2.Function_CreateFunction]
    handoffs: _containers.RepeatedCompositeFieldContainer[_handoff_pb2.Handoff_Create]
    sms: _containers.RepeatedCompositeFieldContainer[_sms_pb2.SMS_CreateTemplate]
    attributes: _containers.RepeatedCompositeFieldContainer[_variant_pb2.Variant_CreateAttribute]
    no_code_steps: _containers.RepeatedCompositeFieldContainer[ImportNoCodeStep]
    entities: _containers.RepeatedCompositeFieldContainer[_entities_pb2.Entity_Create]
    def __init__(self, flow_id: _Optional[str] = ..., steps: _Optional[_Iterable[_Union[ImportFlowStep, _Mapping]]] = ..., transition_functions: _Optional[_Iterable[_Union[TransitionFunction_CreateTransitionFunction, _Mapping]]] = ..., global_functions: _Optional[_Iterable[_Union[_functions_pb2.Function_CreateFunction, _Mapping]]] = ..., handoffs: _Optional[_Iterable[_Union[_handoff_pb2.Handoff_Create, _Mapping]]] = ..., sms: _Optional[_Iterable[_Union[_sms_pb2.SMS_CreateTemplate, _Mapping]]] = ..., attributes: _Optional[_Iterable[_Union[_variant_pb2.Variant_CreateAttribute, _Mapping]]] = ..., no_code_steps: _Optional[_Iterable[_Union[ImportNoCodeStep, _Mapping]]] = ..., entities: _Optional[_Iterable[_Union[_entities_pb2.Entity_Create, _Mapping]]] = ...) -> None: ...

class Flow_CreateStep(_message.Message):
    __slots__ = ("flow_id", "step")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step: CreateAdvancedStep
    def __init__(self, flow_id: _Optional[str] = ..., step: _Optional[_Union[CreateAdvancedStep, _Mapping]] = ...) -> None: ...

class Flow_UpdateStep(_message.Message):
    __slots__ = ("flow_id", "step")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step: UpdateAdvancedStep
    def __init__(self, flow_id: _Optional[str] = ..., step: _Optional[_Union[UpdateAdvancedStep, _Mapping]] = ...) -> None: ...

class Flow_DeleteStep(_message.Message):
    __slots__ = ("flow_id", "step_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ...) -> None: ...

class CreateAdvancedStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "position", "references", "asr_biasing", "dtmf_config")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    ASR_BIASING_FIELD_NUMBER: _ClassVar[int]
    DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    position: StepPosition
    references: StepReferences
    asr_biasing: StepAsrConfig
    dtmf_config: StepDtmfConfig
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., references: _Optional[_Union[StepReferences, _Mapping]] = ..., asr_biasing: _Optional[_Union[StepAsrConfig, _Mapping]] = ..., dtmf_config: _Optional[_Union[StepDtmfConfig, _Mapping]] = ...) -> None: ...

class UpdateAdvancedStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    references: StepReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., references: _Optional[_Union[StepReferences, _Mapping]] = ...) -> None: ...

class ImportFlowStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "position", "asr_biasing", "dtmf_config", "references")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    ASR_BIASING_FIELD_NUMBER: _ClassVar[int]
    DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    position: StepPosition
    asr_biasing: StepAsrConfig
    dtmf_config: StepDtmfConfig
    references: StepReferences
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., asr_biasing: _Optional[_Union[StepAsrConfig, _Mapping]] = ..., dtmf_config: _Optional[_Union[StepDtmfConfig, _Mapping]] = ..., references: _Optional[_Union[StepReferences, _Mapping]] = ...) -> None: ...

class Flow_UpdateStepAsrConfig(_message.Message):
    __slots__ = ("flow_id", "step_id", "asr_biasing")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    ASR_BIASING_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    asr_biasing: StepAsrConfigUpdate
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., asr_biasing: _Optional[_Union[StepAsrConfigUpdate, _Mapping]] = ...) -> None: ...

class StepAsrConfigUpdate(_message.Message):
    __slots__ = ("alphanumeric", "name_spelling", "numeric", "party_size", "precise_date", "relative_date", "single_number", "time", "yes_no", "address", "custom_keywords", "is_enabled")
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    NAME_SPELLING_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    PARTY_SIZE_FIELD_NUMBER: _ClassVar[int]
    PRECISE_DATE_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    SINGLE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    YES_NO_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    alphanumeric: bool
    name_spelling: bool
    numeric: bool
    party_size: bool
    precise_date: bool
    relative_date: bool
    single_number: bool
    time: bool
    yes_no: bool
    address: bool
    custom_keywords: UpdateAsrKeywords
    is_enabled: bool
    def __init__(self, alphanumeric: bool = ..., name_spelling: bool = ..., numeric: bool = ..., party_size: bool = ..., precise_date: bool = ..., relative_date: bool = ..., single_number: bool = ..., time: bool = ..., yes_no: bool = ..., address: bool = ..., custom_keywords: _Optional[_Union[UpdateAsrKeywords, _Mapping]] = ..., is_enabled: bool = ...) -> None: ...

class UpdateAsrKeywords(_message.Message):
    __slots__ = ("custom_keywords",)
    CUSTOM_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    custom_keywords: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, custom_keywords: _Optional[_Iterable[str]] = ...) -> None: ...

class Flow_UpdateStepDtmfConfig(_message.Message):
    __slots__ = ("flow_id", "step_id", "dtmf_config")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    dtmf_config: StepDtmfConfigUpdate
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., dtmf_config: _Optional[_Union[StepDtmfConfigUpdate, _Mapping]] = ...) -> None: ...

class StepDtmfConfigUpdate(_message.Message):
    __slots__ = ("is_enabled", "inter_digit_timeout", "max_digits", "end_key", "collect_while_agent_speaking", "is_pii")
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    INTER_DIGIT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    MAX_DIGITS_FIELD_NUMBER: _ClassVar[int]
    END_KEY_FIELD_NUMBER: _ClassVar[int]
    COLLECT_WHILE_AGENT_SPEAKING_FIELD_NUMBER: _ClassVar[int]
    IS_PII_FIELD_NUMBER: _ClassVar[int]
    is_enabled: bool
    inter_digit_timeout: int
    max_digits: int
    end_key: str
    collect_while_agent_speaking: bool
    is_pii: bool
    def __init__(self, is_enabled: bool = ..., inter_digit_timeout: _Optional[int] = ..., max_digits: _Optional[int] = ..., end_key: _Optional[str] = ..., collect_while_agent_speaking: bool = ..., is_pii: bool = ...) -> None: ...

class Flow_UpdateStepPosition(_message.Message):
    __slots__ = ("flow_id", "position_update")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_UPDATE_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    position_update: StepPositionUpdate
    def __init__(self, flow_id: _Optional[str] = ..., position_update: _Optional[_Union[StepPositionUpdate, _Mapping]] = ...) -> None: ...

class Flow_UpdateStepPositions(_message.Message):
    __slots__ = ("flow_id", "new_positions")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    new_positions: _containers.RepeatedCompositeFieldContainer[StepPositionUpdate]
    def __init__(self, flow_id: _Optional[str] = ..., new_positions: _Optional[_Iterable[_Union[StepPositionUpdate, _Mapping]]] = ...) -> None: ...

class StepPositionUpdate(_message.Message):
    __slots__ = ("step_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class MoveFlowComponent(_message.Message):
    __slots__ = ("flow_id", "position_detail")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_DETAIL_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    position_detail: FlowPositionDetail
    def __init__(self, flow_id: _Optional[str] = ..., position_detail: _Optional[_Union[FlowPositionDetail, _Mapping]] = ...) -> None: ...

class MoveFlowComponents(_message.Message):
    __slots__ = ("flow_id", "position_details")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_DETAILS_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    position_details: _containers.RepeatedCompositeFieldContainer[FlowPositionDetail]
    def __init__(self, flow_id: _Optional[str] = ..., position_details: _Optional[_Iterable[_Union[FlowPositionDetail, _Mapping]]] = ...) -> None: ...

class FlowPositionDetail(_message.Message):
    __slots__ = ("flow_step", "no_code_step", "no_code_step_condition", "no_code_step_condition_exit_flow", "function_step", "function_step_condition", "function_step_condition_exit_flow")
    FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_EXIT_FLOW_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_EXIT_FLOW_FIELD_NUMBER: _ClassVar[int]
    flow_step: FlowStepPositionDetails
    no_code_step: NoCodeStepPositionDetail
    no_code_step_condition: NoCodeStepConditionPositionDetail
    no_code_step_condition_exit_flow: NoCodeStepExitFlowPositionDetail
    function_step: FunctionStepPositionDetail
    function_step_condition: FunctionStepConditionPositionDetail
    function_step_condition_exit_flow: FunctionStepExitFlowPositionDetail
    def __init__(self, flow_step: _Optional[_Union[FlowStepPositionDetails, _Mapping]] = ..., no_code_step: _Optional[_Union[NoCodeStepPositionDetail, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepConditionPositionDetail, _Mapping]] = ..., no_code_step_condition_exit_flow: _Optional[_Union[NoCodeStepExitFlowPositionDetail, _Mapping]] = ..., function_step: _Optional[_Union[FunctionStepPositionDetail, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepConditionPositionDetail, _Mapping]] = ..., function_step_condition_exit_flow: _Optional[_Union[FunctionStepExitFlowPositionDetail, _Mapping]] = ...) -> None: ...

class FlowStepPositionDetails(_message.Message):
    __slots__ = ("step_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class NoCodeStepPositionDetail(_message.Message):
    __slots__ = ("step_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class NoCodeStepConditionPositionDetail(_message.Message):
    __slots__ = ("step_id", "condition_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class NoCodeStepExitFlowPositionDetail(_message.Message):
    __slots__ = ("step_id", "condition_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class FunctionStepPositionDetail(_message.Message):
    __slots__ = ("step_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class FunctionStepConditionPositionDetail(_message.Message):
    __slots__ = ("step_id", "condition_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class FunctionStepExitFlowPositionDetail(_message.Message):
    __slots__ = ("step_id", "condition_id", "new_position")
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class Flow_CreateTransitionFunction(_message.Message):
    __slots__ = ("flow_id", "transition_function")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    transition_function: TransitionFunction_CreateTransitionFunction
    def __init__(self, flow_id: _Optional[str] = ..., transition_function: _Optional[_Union[TransitionFunction_CreateTransitionFunction, _Mapping]] = ...) -> None: ...

class Flow_UpdateTransitionFunction(_message.Message):
    __slots__ = ("flow_id", "transition_function")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    transition_function: TransitionFunction_UpdateTransitionFunction
    def __init__(self, flow_id: _Optional[str] = ..., transition_function: _Optional[_Union[TransitionFunction_UpdateTransitionFunction, _Mapping]] = ...) -> None: ...

class Flow_UpdateTransitionFunctionLatencyControl(_message.Message):
    __slots__ = ("flow_id", "latency_control")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    latency_control: _functions_pb2.Function_UpdateLatencyControl
    def __init__(self, flow_id: _Optional[str] = ..., latency_control: _Optional[_Union[_functions_pb2.Function_UpdateLatencyControl, _Mapping]] = ...) -> None: ...

class Flow_DeleteTransitionFunction(_message.Message):
    __slots__ = ("flow_id", "function_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    function_id: str
    def __init__(self, flow_id: _Optional[str] = ..., function_id: _Optional[str] = ...) -> None: ...

class TransitionFunction_CreateTransitionFunction(_message.Message):
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
    parameters: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionParameterUpdate]
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    latency_control: _functions_pb2.FunctionCreateLatencyControl
    references: TransitionFunctionReferences
    archived: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[_functions_pb2.FunctionParameterUpdate, _Mapping]]] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[_functions_pb2.FunctionCreateLatencyControl, _Mapping]] = ..., references: _Optional[_Union[TransitionFunctionReferences, _Mapping]] = ..., archived: bool = ...) -> None: ...

class TransitionFunction_UpdateTransitionFunction(_message.Message):
    __slots__ = ("id", "name", "description", "parameters", "code", "errors")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    parameters: _functions_pb2.ParametersUpdate
    code: str
    errors: _functions_pb2.ErrorsUpdate
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Union[_functions_pb2.ParametersUpdate, _Mapping]] = ..., code: _Optional[str] = ..., errors: _Optional[_Union[_functions_pb2.ErrorsUpdate, _Mapping]] = ...) -> None: ...

class CreateNoCodeStep(_message.Message):
    __slots__ = ("flow_id", "step_id", "name", "prompt", "position", "references")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    name: str
    prompt: str
    position: StepPosition
    references: NoCodeStepReferences
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., references: _Optional[_Union[NoCodeStepReferences, _Mapping]] = ...) -> None: ...

class UpdateNoCodeStep(_message.Message):
    __slots__ = ("flow_id", "step_id", "name", "prompt", "position", "references")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    name: str
    prompt: str
    position: StepPosition
    references: NoCodeStepReferences
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., references: _Optional[_Union[NoCodeStepReferences, _Mapping]] = ...) -> None: ...

class DeleteNoCodeStep(_message.Message):
    __slots__ = ("flow_id", "step_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ...) -> None: ...

class UpdateNoCodeStepPosition(_message.Message):
    __slots__ = ("flow_id", "step_id", "new_position")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    new_position: StepPosition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class ImportNoCodeStep(_message.Message):
    __slots__ = ("id", "name", "prompt", "position", "references", "conditions")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    prompt: str
    position: StepPosition
    references: NoCodeStepReferences
    conditions: _containers.RepeatedCompositeFieldContainer[Condition]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., prompt: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., references: _Optional[_Union[NoCodeStepReferences, _Mapping]] = ..., conditions: _Optional[_Iterable[_Union[Condition, _Mapping]]] = ...) -> None: ...

class CreateNoCodeCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    exit_flow_condition: ExitFlowCondition
    step_condition: AdvancedStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[AdvancedStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class UpdateNoCodeCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    exit_flow_condition: ExitFlowCondition
    step_condition: AdvancedStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[AdvancedStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class DeleteNoCodeCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ...) -> None: ...

class UpdateNoCodeConditionPosition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "new_position")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class UpdateNoCodeConditionExitFlowPosition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "new_position")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class CreateStep(_message.Message):
    __slots__ = ("flow_id", "function_step")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    function_step: CreateFunctionStep
    def __init__(self, flow_id: _Optional[str] = ..., function_step: _Optional[_Union[CreateFunctionStep, _Mapping]] = ...) -> None: ...

class UpdateStep(_message.Message):
    __slots__ = ("flow_id", "step_id", "function_step")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    function_step: UpdateFunctionStep
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., function_step: _Optional[_Union[UpdateFunctionStep, _Mapping]] = ...) -> None: ...

class DeleteStep(_message.Message):
    __slots__ = ("flow_id", "step_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ...) -> None: ...

class CreateStepCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    exit_flow_condition: ExitFlowCondition
    step_condition: AdvancedStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[AdvancedStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class UpdateStepCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    exit_flow_condition: ExitFlowCondition
    step_condition: AdvancedStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[AdvancedStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class DeleteStepCondition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ...) -> None: ...

class UpdateStepConditionPosition(_message.Message):
    __slots__ = ("flow_id", "step_id", "condition_id", "new_position")
    FLOW_ID_FIELD_NUMBER: _ClassVar[int]
    STEP_ID_FIELD_NUMBER: _ClassVar[int]
    CONDITION_ID_FIELD_NUMBER: _ClassVar[int]
    NEW_POSITION_FIELD_NUMBER: _ClassVar[int]
    flow_id: str
    step_id: str
    condition_id: str
    new_position: StepPosition
    def __init__(self, flow_id: _Optional[str] = ..., step_id: _Optional[str] = ..., condition_id: _Optional[str] = ..., new_position: _Optional[_Union[StepPosition, _Mapping]] = ...) -> None: ...

class FunctionStepDefinition(_message.Message):
    __slots__ = ("id", "name", "code", "errors", "latency_control", "created_at", "created_by", "updated_at", "updated_by", "archived")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    latency_control: _functions_pb2.FunctionLatencyControl
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    archived: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[_functions_pb2.FunctionLatencyControl, _Mapping]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., archived: bool = ...) -> None: ...

class CreateFunctionStep(_message.Message):
    __slots__ = ("id", "name", "position", "function")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    position: StepPosition
    function: CreateFunctionStepDefinition
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., function: _Optional[_Union[CreateFunctionStepDefinition, _Mapping]] = ...) -> None: ...

class UpdateFunctionStep(_message.Message):
    __slots__ = ("name", "position", "function")
    NAME_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    position: StepPosition
    function: UpdateFunctionStepDefinition
    def __init__(self, name: _Optional[str] = ..., position: _Optional[_Union[StepPosition, _Mapping]] = ..., function: _Optional[_Union[UpdateFunctionStepDefinition, _Mapping]] = ...) -> None: ...

class CreateFunctionStepDefinition(_message.Message):
    __slots__ = ("id", "name", "code", "errors", "latency_control")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    code: str
    errors: _containers.RepeatedCompositeFieldContainer[_functions_pb2.FunctionError]
    latency_control: _functions_pb2.FunctionCreateLatencyControl
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., code: _Optional[str] = ..., errors: _Optional[_Iterable[_Union[_functions_pb2.FunctionError, _Mapping]]] = ..., latency_control: _Optional[_Union[_functions_pb2.FunctionCreateLatencyControl, _Mapping]] = ...) -> None: ...

class UpdateFunctionStepDefinition(_message.Message):
    __slots__ = ("description", "code", "errors", "archived", "latency_control")
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    ERRORS_FIELD_NUMBER: _ClassVar[int]
    ARCHIVED_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    description: str
    code: str
    errors: _functions_pb2.ErrorsUpdate
    archived: bool
    latency_control: _functions_pb2.FunctionCreateLatencyControl
    def __init__(self, description: _Optional[str] = ..., code: _Optional[str] = ..., errors: _Optional[_Union[_functions_pb2.ErrorsUpdate, _Mapping]] = ..., archived: bool = ..., latency_control: _Optional[_Union[_functions_pb2.FunctionCreateLatencyControl, _Mapping]] = ...) -> None: ...
