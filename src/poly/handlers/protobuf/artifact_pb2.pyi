from agent_v2 import agent_pb2 as _agent_pb2
from agent_v3.genai.proto.integrations import integrations_pb2 as _integrations_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CoreArtifact(_message.Message):
    __slots__ = ("name", "last_updated", "functions_deployment", "conversation_limits", "voice", "asr", "model", "assistant_config", "knowledge_base", "functions", "start_function", "handoffs", "voice_tuning_settings", "sms_templates", "flows", "intro_message", "stop_keywords", "variants", "variant_attributes", "end_function", "deployed_voices", "entities", "api_integrations", "variables", "disclaimers", "agent_voices", "multilingual_agent_settings", "multilingual_translations", "channels", "integrations")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATED_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONS_DEPLOYMENT_FIELD_NUMBER: _ClassVar[int]
    CONVERSATION_LIMITS_FIELD_NUMBER: _ClassVar[int]
    VOICE_FIELD_NUMBER: _ClassVar[int]
    ASR_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    ASSISTANT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    KNOWLEDGE_BASE_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    VOICE_TUNING_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    SMS_TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    FLOWS_FIELD_NUMBER: _ClassVar[int]
    INTRO_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    VARIANTS_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DEPLOYED_VOICES_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    API_INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMERS_FIELD_NUMBER: _ClassVar[int]
    AGENT_VOICES_FIELD_NUMBER: _ClassVar[int]
    MULTILINGUAL_AGENT_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    MULTILINGUAL_TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    name: str
    last_updated: _timestamp_pb2.Timestamp
    functions_deployment: FunctionsDeployment
    conversation_limits: ConversationLimits
    voice: Voice
    asr: Asr
    model: Model
    assistant_config: AssistantConfig
    knowledge_base: KnowledgeBase
    functions: _containers.RepeatedCompositeFieldContainer[Function]
    start_function: Function
    handoffs: _containers.RepeatedCompositeFieldContainer[Handoff]
    voice_tuning_settings: _containers.RepeatedCompositeFieldContainer[VoiceTuningSettings]
    sms_templates: _containers.RepeatedCompositeFieldContainer[SMSTemplate]
    flows: Flows
    intro_message: IntroMessage
    stop_keywords: _containers.RepeatedCompositeFieldContainer[StopKeywords]
    variants: _containers.RepeatedCompositeFieldContainer[Variant]
    variant_attributes: _containers.RepeatedCompositeFieldContainer[VariantAttribute]
    end_function: Function
    deployed_voices: DeployedVoices
    entities: Entities
    api_integrations: ApiIntegrations
    variables: Variables
    disclaimers: _containers.RepeatedCompositeFieldContainer[IntroMessage]
    agent_voices: _containers.RepeatedCompositeFieldContainer[DeployedVoices]
    multilingual_agent_settings: MultilingualAgentSettings
    multilingual_translations: MultilingualTranslations
    channels: Channels
    integrations: _integrations_pb2.Integrations
    def __init__(self, name: _Optional[str] = ..., last_updated: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., functions_deployment: _Optional[_Union[FunctionsDeployment, _Mapping]] = ..., conversation_limits: _Optional[_Union[ConversationLimits, _Mapping]] = ..., voice: _Optional[_Union[Voice, _Mapping]] = ..., asr: _Optional[_Union[Asr, _Mapping]] = ..., model: _Optional[_Union[Model, _Mapping]] = ..., assistant_config: _Optional[_Union[AssistantConfig, _Mapping]] = ..., knowledge_base: _Optional[_Union[KnowledgeBase, _Mapping]] = ..., functions: _Optional[_Iterable[_Union[Function, _Mapping]]] = ..., start_function: _Optional[_Union[Function, _Mapping]] = ..., handoffs: _Optional[_Iterable[_Union[Handoff, _Mapping]]] = ..., voice_tuning_settings: _Optional[_Iterable[_Union[VoiceTuningSettings, _Mapping]]] = ..., sms_templates: _Optional[_Iterable[_Union[SMSTemplate, _Mapping]]] = ..., flows: _Optional[_Union[Flows, _Mapping]] = ..., intro_message: _Optional[_Union[IntroMessage, _Mapping]] = ..., stop_keywords: _Optional[_Iterable[_Union[StopKeywords, _Mapping]]] = ..., variants: _Optional[_Iterable[_Union[Variant, _Mapping]]] = ..., variant_attributes: _Optional[_Iterable[_Union[VariantAttribute, _Mapping]]] = ..., end_function: _Optional[_Union[Function, _Mapping]] = ..., deployed_voices: _Optional[_Union[DeployedVoices, _Mapping]] = ..., entities: _Optional[_Union[Entities, _Mapping]] = ..., api_integrations: _Optional[_Union[ApiIntegrations, _Mapping]] = ..., variables: _Optional[_Union[Variables, _Mapping]] = ..., disclaimers: _Optional[_Iterable[_Union[IntroMessage, _Mapping]]] = ..., agent_voices: _Optional[_Iterable[_Union[DeployedVoices, _Mapping]]] = ..., multilingual_agent_settings: _Optional[_Union[MultilingualAgentSettings, _Mapping]] = ..., multilingual_translations: _Optional[_Union[MultilingualTranslations, _Mapping]] = ..., channels: _Optional[_Union[Channels, _Mapping]] = ..., integrations: _Optional[_Union[_integrations_pb2.Integrations, _Mapping]] = ...) -> None: ...

class VoiceWithProbability(_message.Message):
    __slots__ = ("voice", "probability", "voice_tuning_settings")
    VOICE_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    VOICE_TUNING_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    voice: Voice
    probability: float
    voice_tuning_settings: VoiceTuningSettings
    def __init__(self, voice: _Optional[_Union[Voice, _Mapping]] = ..., probability: _Optional[float] = ..., voice_tuning_settings: _Optional[_Union[VoiceTuningSettings, _Mapping]] = ...) -> None: ...

class Entities(_message.Message):
    __slots__ = ("entities",)
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    entities: _containers.RepeatedCompositeFieldContainer[Entity]
    def __init__(self, entities: _Optional[_Iterable[_Union[Entity, _Mapping]]] = ...) -> None: ...

class Entity(_message.Message):
    __slots__ = ("name", "description", "type", "id", "alphanumeric_config", "number_config", "date_config", "time_config", "phone_number_config", "name_config", "address_config", "free_text_config", "multiple_options_config")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    ALPHANUMERIC_CONFIG_FIELD_NUMBER: _ClassVar[int]
    NUMBER_CONFIG_FIELD_NUMBER: _ClassVar[int]
    DATE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    TIME_CONFIG_FIELD_NUMBER: _ClassVar[int]
    PHONE_NUMBER_CONFIG_FIELD_NUMBER: _ClassVar[int]
    NAME_CONFIG_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_CONFIG_FIELD_NUMBER: _ClassVar[int]
    FREE_TEXT_CONFIG_FIELD_NUMBER: _ClassVar[int]
    MULTIPLE_OPTIONS_CONFIG_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    type: str
    id: str
    alphanumeric_config: AlphanumericEntityConfig
    number_config: NumberEntityConfig
    date_config: DateEntityConfig
    time_config: TimeEntityConfig
    phone_number_config: PhoneNumberEntityConfig
    name_config: NameEntityConfig
    address_config: AddressEntityConfig
    free_text_config: FreeTextEntityConfig
    multiple_options_config: MultipleOptionsEntityConfig
    def __init__(self, name: _Optional[str] = ..., description: _Optional[str] = ..., type: _Optional[str] = ..., id: _Optional[str] = ..., alphanumeric_config: _Optional[_Union[AlphanumericEntityConfig, _Mapping]] = ..., number_config: _Optional[_Union[NumberEntityConfig, _Mapping]] = ..., date_config: _Optional[_Union[DateEntityConfig, _Mapping]] = ..., time_config: _Optional[_Union[TimeEntityConfig, _Mapping]] = ..., phone_number_config: _Optional[_Union[PhoneNumberEntityConfig, _Mapping]] = ..., name_config: _Optional[_Union[NameEntityConfig, _Mapping]] = ..., address_config: _Optional[_Union[AddressEntityConfig, _Mapping]] = ..., free_text_config: _Optional[_Union[FreeTextEntityConfig, _Mapping]] = ..., multiple_options_config: _Optional[_Union[MultipleOptionsEntityConfig, _Mapping]] = ...) -> None: ...

class Variables(_message.Message):
    __slots__ = ("variables",)
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    variables: _containers.RepeatedCompositeFieldContainer[Variable]
    def __init__(self, variables: _Optional[_Iterable[_Union[Variable, _Mapping]]] = ...) -> None: ...

class Variable(_message.Message):
    __slots__ = ("id", "name", "created_by", "created_at", "updated_by", "updated_at")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class NumberEntityConfig(_message.Message):
    __slots__ = ("min", "max", "numeric_type")
    MIN_FIELD_NUMBER: _ClassVar[int]
    MAX_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_TYPE_FIELD_NUMBER: _ClassVar[int]
    min: float
    max: float
    numeric_type: str
    def __init__(self, min: _Optional[float] = ..., max: _Optional[float] = ..., numeric_type: _Optional[str] = ...) -> None: ...

class AlphanumericEntityConfig(_message.Message):
    __slots__ = ("regex",)
    REGEX_FIELD_NUMBER: _ClassVar[int]
    regex: str
    def __init__(self, regex: _Optional[str] = ...) -> None: ...

class MultipleOptionsEntityConfig(_message.Message):
    __slots__ = ("options",)
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    options: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, options: _Optional[_Iterable[str]] = ...) -> None: ...

class DateEntityConfig(_message.Message):
    __slots__ = ("day_first", "start_date", "end_date")
    DAY_FIRST_FIELD_NUMBER: _ClassVar[int]
    START_DATE_FIELD_NUMBER: _ClassVar[int]
    END_DATE_FIELD_NUMBER: _ClassVar[int]
    day_first: bool
    start_date: str
    end_date: str
    def __init__(self, day_first: bool = ..., start_date: _Optional[str] = ..., end_date: _Optional[str] = ...) -> None: ...

class PhoneNumberEntityConfig(_message.Message):
    __slots__ = ("country_codes",)
    COUNTRY_CODES_FIELD_NUMBER: _ClassVar[int]
    country_codes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, country_codes: _Optional[_Iterable[str]] = ...) -> None: ...

class TimeEntityConfig(_message.Message):
    __slots__ = ("start_time", "end_time")
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    END_TIME_FIELD_NUMBER: _ClassVar[int]
    start_time: str
    end_time: str
    def __init__(self, start_time: _Optional[str] = ..., end_time: _Optional[str] = ...) -> None: ...

class NameEntityConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class AddressEntityConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class FreeTextEntityConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class DeployedVoices(_message.Message):
    __slots__ = ("voices_with_proba", "language_code")
    VOICES_WITH_PROBA_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    voices_with_proba: _containers.RepeatedCompositeFieldContainer[VoiceWithProbability]
    language_code: str
    def __init__(self, voices_with_proba: _Optional[_Iterable[_Union[VoiceWithProbability, _Mapping]]] = ..., language_code: _Optional[str] = ...) -> None: ...

class ConversationLimits(_message.Message):
    __slots__ = ("call_duration_limit", "chat_turn_limit")
    CALL_DURATION_LIMIT_FIELD_NUMBER: _ClassVar[int]
    CHAT_TURN_LIMIT_FIELD_NUMBER: _ClassVar[int]
    call_duration_limit: int
    chat_turn_limit: int
    def __init__(self, call_duration_limit: _Optional[int] = ..., chat_turn_limit: _Optional[int] = ...) -> None: ...

class Voice(_message.Message):
    __slots__ = ("provider_voice_id", "provider", "config")
    PROVIDER_VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    provider_voice_id: str
    provider: str
    config: _struct_pb2.Struct
    def __init__(self, provider_voice_id: _Optional[str] = ..., provider: _Optional[str] = ..., config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Asr(_message.Message):
    __slots__ = ("provider_id", "model_id", "language", "config")
    PROVIDER_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    provider_id: str
    model_id: str
    language: str
    config: _struct_pb2.Struct
    def __init__(self, provider_id: _Optional[str] = ..., model_id: _Optional[str] = ..., language: _Optional[str] = ..., config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class TTSRule(_message.Message):
    __slots__ = ("regex", "replacement", "case_sensitive", "language_code")
    REGEX_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    CASE_SENSITIVE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    regex: str
    replacement: str
    case_sensitive: bool
    language_code: str
    def __init__(self, regex: _Optional[str] = ..., replacement: _Optional[str] = ..., case_sensitive: bool = ..., language_code: _Optional[str] = ...) -> None: ...

class Model(_message.Message):
    __slots__ = ("provider_model_id", "config")
    PROVIDER_MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    provider_model_id: str
    config: _struct_pb2.Struct
    def __init__(self, provider_model_id: _Optional[str] = ..., config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class AssistantConfig(_message.Message):
    __slots__ = ("updated_at", "updated_by", "default_handoff_id", "model_id", "voice_id", "config", "asr_id", "tts_rules", "content_filter", "barge_in_config", "latency_config", "asr_keyphrases", "asr_corrections", "languages")
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_HANDOFF_ID_FIELD_NUMBER: _ClassVar[int]
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    ASR_ID_FIELD_NUMBER: _ClassVar[int]
    TTS_RULES_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FILTER_FIELD_NUMBER: _ClassVar[int]
    BARGE_IN_CONFIG_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    ASR_KEYPHRASES_FIELD_NUMBER: _ClassVar[int]
    ASR_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    default_handoff_id: str
    model_id: str
    voice_id: str
    config: _struct_pb2.Struct
    asr_id: str
    tts_rules: _containers.RepeatedCompositeFieldContainer[TTSRule]
    content_filter: ContentFilter
    barge_in_config: BargeInConfig
    latency_config: LatencyConfig
    asr_keyphrases: _containers.RepeatedCompositeFieldContainer[AsrKeyphrase]
    asr_corrections: _containers.RepeatedCompositeFieldContainer[AsrCorrection]
    languages: Languages
    def __init__(self, updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., default_handoff_id: _Optional[str] = ..., model_id: _Optional[str] = ..., voice_id: _Optional[str] = ..., config: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., asr_id: _Optional[str] = ..., tts_rules: _Optional[_Iterable[_Union[TTSRule, _Mapping]]] = ..., content_filter: _Optional[_Union[ContentFilter, _Mapping]] = ..., barge_in_config: _Optional[_Union[BargeInConfig, _Mapping]] = ..., latency_config: _Optional[_Union[LatencyConfig, _Mapping]] = ..., asr_keyphrases: _Optional[_Iterable[_Union[AsrKeyphrase, _Mapping]]] = ..., asr_corrections: _Optional[_Iterable[_Union[AsrCorrection, _Mapping]]] = ..., languages: _Optional[_Union[Languages, _Mapping]] = ...) -> None: ...

class Rules(_message.Message):
    __slots__ = ("behaviour", "system_prompt", "functions", "handoffs", "sms_templates", "variant_attributes")
    BEHAVIOUR_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    SMS_TEMPLATES_FIELD_NUMBER: _ClassVar[int]
    VARIANT_ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    behaviour: str
    system_prompt: str
    functions: _containers.RepeatedScalarFieldContainer[str]
    handoffs: _containers.RepeatedScalarFieldContainer[str]
    sms_templates: _containers.RepeatedScalarFieldContainer[str]
    variant_attributes: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, behaviour: _Optional[str] = ..., system_prompt: _Optional[str] = ..., functions: _Optional[_Iterable[str]] = ..., handoffs: _Optional[_Iterable[str]] = ..., sms_templates: _Optional[_Iterable[str]] = ..., variant_attributes: _Optional[_Iterable[str]] = ...) -> None: ...

class Personality(_message.Message):
    __slots__ = ("adjectives", "custom", "adjectives_dict")
    ADJECTIVES_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    ADJECTIVES_DICT_FIELD_NUMBER: _ClassVar[int]
    adjectives: _containers.RepeatedScalarFieldContainer[str]
    custom: str
    adjectives_dict: _struct_pb2.Struct
    def __init__(self, adjectives: _Optional[_Iterable[str]] = ..., custom: _Optional[str] = ..., adjectives_dict: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Role(_message.Message):
    __slots__ = ("value", "additional_info", "custom")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_INFO_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_FIELD_NUMBER: _ClassVar[int]
    value: str
    additional_info: str
    custom: str
    def __init__(self, value: _Optional[str] = ..., additional_info: _Optional[str] = ..., custom: _Optional[str] = ...) -> None: ...

class KnowledgeBaseMetadata(_message.Message):
    __slots__ = ("rules", "personality", "role")
    RULES_FIELD_NUMBER: _ClassVar[int]
    PERSONALITY_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    rules: Rules
    personality: Personality
    role: Role
    def __init__(self, rules: _Optional[_Union[Rules, _Mapping]] = ..., personality: _Optional[_Union[Personality, _Mapping]] = ..., role: _Optional[_Union[Role, _Mapping]] = ...) -> None: ...

class KnowledgeBase(_message.Message):
    __slots__ = ("updated_at", "updated_by", "welcome_message", "knowledge_base", "additional_context", "system_prompt")
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    WELCOME_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    KNOWLEDGE_BASE_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_PROMPT_FIELD_NUMBER: _ClassVar[int]
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    welcome_message: str
    knowledge_base: KnowledgeBaseMetadata
    additional_context: _struct_pb2.Struct
    system_prompt: str
    def __init__(self, updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., welcome_message: _Optional[str] = ..., knowledge_base: _Optional[_Union[KnowledgeBaseMetadata, _Mapping]] = ..., additional_context: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., system_prompt: _Optional[str] = ...) -> None: ...

class FunctionParameter(_message.Message):
    __slots__ = ("name", "type", "description")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: str
    description: str
    def __init__(self, name: _Optional[str] = ..., type: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class DelayResponse(_message.Message):
    __slots__ = ("message", "duration")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DURATION_FIELD_NUMBER: _ClassVar[int]
    message: str
    duration: int
    def __init__(self, message: _Optional[str] = ..., duration: _Optional[int] = ...) -> None: ...

class LatencyControl(_message.Message):
    __slots__ = ("initial_delay", "interval", "delay_responses")
    INITIAL_DELAY_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_FIELD_NUMBER: _ClassVar[int]
    DELAY_RESPONSES_FIELD_NUMBER: _ClassVar[int]
    initial_delay: int
    interval: int
    delay_responses: _containers.RepeatedCompositeFieldContainer[DelayResponse]
    def __init__(self, initial_delay: _Optional[int] = ..., interval: _Optional[int] = ..., delay_responses: _Optional[_Iterable[_Union[DelayResponse, _Mapping]]] = ...) -> None: ...

class Function(_message.Message):
    __slots__ = ("id", "function_id", "name", "description", "parameters", "associated_flow", "latency_control", "prefix_path")
    ID_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATED_FLOW_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    PREFIX_PATH_FIELD_NUMBER: _ClassVar[int]
    id: str
    function_id: str
    name: str
    description: str
    parameters: _containers.RepeatedCompositeFieldContainer[FunctionParameter]
    associated_flow: str
    latency_control: LatencyControl
    prefix_path: str
    def __init__(self, id: _Optional[str] = ..., function_id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., parameters: _Optional[_Iterable[_Union[FunctionParameter, _Mapping]]] = ..., associated_flow: _Optional[str] = ..., latency_control: _Optional[_Union[LatencyControl, _Mapping]] = ..., prefix_path: _Optional[str] = ...) -> None: ...

class FunctionsDeployment(_message.Message):
    __slots__ = ("id", "deployment_version")
    ID_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    id: str
    deployment_version: str
    def __init__(self, id: _Optional[str] = ..., deployment_version: _Optional[str] = ...) -> None: ...

class Handoff(_message.Message):
    __slots__ = ("id", "name", "created_at", "created_by", "updated_at", "updated_by", "description", "extension", "invite", "refer", "bye")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    EXTENSION_FIELD_NUMBER: _ClassVar[int]
    INVITE_FIELD_NUMBER: _ClassVar[int]
    REFER_FIELD_NUMBER: _ClassVar[int]
    BYE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    description: str
    extension: str
    invite: _agent_pb2.InviteHandoff
    refer: _agent_pb2.ReferHandoff
    bye: _agent_pb2.ByeHandoff
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., description: _Optional[str] = ..., extension: _Optional[str] = ..., invite: _Optional[_Union[_agent_pb2.InviteHandoff, _Mapping]] = ..., refer: _Optional[_Union[_agent_pb2.ReferHandoff, _Mapping]] = ..., bye: _Optional[_Union[_agent_pb2.ByeHandoff, _Mapping]] = ...) -> None: ...

class VoiceTuningSettings(_message.Message):
    __slots__ = ("genai_project_id", "voice_config_id", "settings", "created_by", "created_at", "updated_by", "updated_at")
    GENAI_PROJECT_ID_FIELD_NUMBER: _ClassVar[int]
    VOICE_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    SETTINGS_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    genai_project_id: str
    voice_config_id: str
    settings: _struct_pb2.Struct
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, genai_project_id: _Optional[str] = ..., voice_config_id: _Optional[str] = ..., settings: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class SMSEnvNumbers(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: str
    pre_release: str
    live: str
    def __init__(self, sandbox: _Optional[str] = ..., pre_release: _Optional[str] = ..., live: _Optional[str] = ...) -> None: ...

class SMSTemplate(_message.Message):
    __slots__ = ("id", "template_name", "template_text", "created_at", "created_by", "updated_at", "updated_by", "sms_numbers")
    ID_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_TEXT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    SMS_NUMBERS_FIELD_NUMBER: _ClassVar[int]
    id: str
    template_name: str
    template_text: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    sms_numbers: SMSEnvNumbers
    def __init__(self, id: _Optional[str] = ..., template_name: _Optional[str] = ..., template_text: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., sms_numbers: _Optional[_Union[SMSEnvNumbers, _Mapping]] = ...) -> None: ...

class FunctionReference(_message.Message):
    __slots__ = ("function_id", "resource_id")
    FUNCTION_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_ID_FIELD_NUMBER: _ClassVar[int]
    function_id: str
    resource_id: str
    def __init__(self, function_id: _Optional[str] = ..., resource_id: _Optional[str] = ...) -> None: ...

class StepLayout(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class FlowStep(_message.Message):
    __slots__ = ("name", "content", "functions_referenced", "layout", "asr_biasing_config", "dtmf_config", "initial_timeout")
    NAME_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    FUNCTIONS_REFERENCED_FIELD_NUMBER: _ClassVar[int]
    LAYOUT_FIELD_NUMBER: _ClassVar[int]
    ASR_BIASING_CONFIG_FIELD_NUMBER: _ClassVar[int]
    DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    INITIAL_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    name: str
    content: str
    functions_referenced: _containers.RepeatedCompositeFieldContainer[FunctionReference]
    layout: StepLayout
    asr_biasing_config: StepAsrBiasingConfig
    dtmf_config: StepDTMFConfig
    initial_timeout: _duration_pb2.Duration
    def __init__(self, name: _Optional[str] = ..., content: _Optional[str] = ..., functions_referenced: _Optional[_Iterable[_Union[FunctionReference, _Mapping]]] = ..., layout: _Optional[_Union[StepLayout, _Mapping]] = ..., asr_biasing_config: _Optional[_Union[StepAsrBiasingConfig, _Mapping]] = ..., dtmf_config: _Optional[_Union[StepDTMFConfig, _Mapping]] = ..., initial_timeout: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ...) -> None: ...

class FunctionStep(_message.Message):
    __slots__ = ("name", "function_reference")
    NAME_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    name: str
    function_reference: FunctionReference
    def __init__(self, name: _Optional[str] = ..., function_reference: _Optional[_Union[FunctionReference, _Mapping]] = ...) -> None: ...

class FlowStartStep(_message.Message):
    __slots__ = ("advanced_step", "no_code_step", "function_step")
    ADVANCED_STEP_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    advanced_step: FlowStep
    no_code_step: NoCodeStep
    function_step: FunctionStep
    def __init__(self, advanced_step: _Optional[_Union[FlowStep, _Mapping]] = ..., no_code_step: _Optional[_Union[NoCodeStep, _Mapping]] = ..., function_step: _Optional[_Union[FunctionStep, _Mapping]] = ...) -> None: ...

class Step(_message.Message):
    __slots__ = ("advanced_step", "no_code_step", "function_step")
    ADVANCED_STEP_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_FIELD_NUMBER: _ClassVar[int]
    advanced_step: FlowStep
    no_code_step: NoCodeStep
    function_step: FunctionStep
    def __init__(self, advanced_step: _Optional[_Union[FlowStep, _Mapping]] = ..., no_code_step: _Optional[_Union[NoCodeStep, _Mapping]] = ..., function_step: _Optional[_Union[FunctionStep, _Mapping]] = ...) -> None: ...

class NoCodeStepConditionDetails(_message.Message):
    __slots__ = ("label", "description", "required_entities")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_ENTITIES_FIELD_NUMBER: _ClassVar[int]
    label: str
    description: str
    required_entities: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, label: _Optional[str] = ..., description: _Optional[str] = ..., required_entities: _Optional[_Iterable[str]] = ...) -> None: ...

class NoCodeStepReferences(_message.Message):
    __slots__ = ("details",)
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    details: NoCodeStepConditionDetails
    def __init__(self, details: _Optional[_Union[NoCodeStepConditionDetails, _Mapping]] = ...) -> None: ...

class ExitFlowCondition(_message.Message):
    __slots__ = ("details",)
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    details: NoCodeStepConditionDetails
    def __init__(self, details: _Optional[_Union[NoCodeStepConditionDetails, _Mapping]] = ...) -> None: ...

class FunctionStepConditionDetails(_message.Message):
    __slots__ = ("label", "description")
    LABEL_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    label: str
    description: str
    def __init__(self, label: _Optional[str] = ..., description: _Optional[str] = ...) -> None: ...

class FlowStepCondition(_message.Message):
    __slots__ = ("details", "child_step_name")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_NAME_FIELD_NUMBER: _ClassVar[int]
    details: NoCodeStepConditionDetails
    child_step_name: str
    def __init__(self, details: _Optional[_Union[NoCodeStepConditionDetails, _Mapping]] = ..., child_step_name: _Optional[str] = ...) -> None: ...

class NoCodeStepCondition(_message.Message):
    __slots__ = ("details", "child_step_name")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_NAME_FIELD_NUMBER: _ClassVar[int]
    details: NoCodeStepConditionDetails
    child_step_name: str
    def __init__(self, details: _Optional[_Union[NoCodeStepConditionDetails, _Mapping]] = ..., child_step_name: _Optional[str] = ...) -> None: ...

class FunctionStepCondition(_message.Message):
    __slots__ = ("details", "child_step_name")
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    CHILD_STEP_NAME_FIELD_NUMBER: _ClassVar[int]
    details: FunctionStepConditionDetails
    child_step_name: str
    def __init__(self, details: _Optional[_Union[FunctionStepConditionDetails, _Mapping]] = ..., child_step_name: _Optional[str] = ...) -> None: ...

class Condition(_message.Message):
    __slots__ = ("exit_flow_condition", "step_condition", "no_code_step_condition", "function_step_condition")
    EXIT_FLOW_CONDITION_FIELD_NUMBER: _ClassVar[int]
    STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    exit_flow_condition: ExitFlowCondition
    step_condition: FlowStepCondition
    no_code_step_condition: NoCodeStepCondition
    function_step_condition: FunctionStepCondition
    def __init__(self, exit_flow_condition: _Optional[_Union[ExitFlowCondition, _Mapping]] = ..., step_condition: _Optional[_Union[FlowStepCondition, _Mapping]] = ..., no_code_step_condition: _Optional[_Union[NoCodeStepCondition, _Mapping]] = ..., function_step_condition: _Optional[_Union[FunctionStepCondition, _Mapping]] = ...) -> None: ...

class NoCodeStep(_message.Message):
    __slots__ = ("name", "prompt", "entity_references", "conditions")
    NAME_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    ENTITY_REFERENCES_FIELD_NUMBER: _ClassVar[int]
    CONDITIONS_FIELD_NUMBER: _ClassVar[int]
    name: str
    prompt: str
    entity_references: _containers.RepeatedScalarFieldContainer[str]
    conditions: _containers.RepeatedCompositeFieldContainer[Condition]
    def __init__(self, name: _Optional[str] = ..., prompt: _Optional[str] = ..., entity_references: _Optional[_Iterable[str]] = ..., conditions: _Optional[_Iterable[_Union[Condition, _Mapping]]] = ...) -> None: ...

class StepAsrBiasingConfig(_message.Message):
    __slots__ = ("alphanumeric", "name_spelling", "numeric", "party_size", "precise_date", "relative_date", "single_number", "time", "yes_no", "custom_keywords", "address", "is_enabled")
    ALPHANUMERIC_FIELD_NUMBER: _ClassVar[int]
    NAME_SPELLING_FIELD_NUMBER: _ClassVar[int]
    NUMERIC_FIELD_NUMBER: _ClassVar[int]
    PARTY_SIZE_FIELD_NUMBER: _ClassVar[int]
    PRECISE_DATE_FIELD_NUMBER: _ClassVar[int]
    RELATIVE_DATE_FIELD_NUMBER: _ClassVar[int]
    SINGLE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    TIME_FIELD_NUMBER: _ClassVar[int]
    YES_NO_FIELD_NUMBER: _ClassVar[int]
    CUSTOM_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
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
    custom_keywords: _containers.RepeatedScalarFieldContainer[str]
    address: bool
    is_enabled: bool
    def __init__(self, alphanumeric: bool = ..., name_spelling: bool = ..., numeric: bool = ..., party_size: bool = ..., precise_date: bool = ..., relative_date: bool = ..., single_number: bool = ..., time: bool = ..., yes_no: bool = ..., custom_keywords: _Optional[_Iterable[str]] = ..., address: bool = ..., is_enabled: bool = ...) -> None: ...

class StepDTMFConfig(_message.Message):
    __slots__ = ("is_enabled", "inter_digit_timeout", "max_digits", "end_key", "collect_while_agent_speaking", "is_pii")
    IS_ENABLED_FIELD_NUMBER: _ClassVar[int]
    INTER_DIGIT_TIMEOUT_FIELD_NUMBER: _ClassVar[int]
    MAX_DIGITS_FIELD_NUMBER: _ClassVar[int]
    END_KEY_FIELD_NUMBER: _ClassVar[int]
    COLLECT_WHILE_AGENT_SPEAKING_FIELD_NUMBER: _ClassVar[int]
    IS_PII_FIELD_NUMBER: _ClassVar[int]
    is_enabled: bool
    inter_digit_timeout: _duration_pb2.Duration
    max_digits: int
    end_key: str
    collect_while_agent_speaking: bool
    is_pii: bool
    def __init__(self, is_enabled: bool = ..., inter_digit_timeout: _Optional[_Union[_duration_pb2.Duration, _Mapping]] = ..., max_digits: _Optional[int] = ..., end_key: _Optional[str] = ..., collect_while_agent_speaking: bool = ..., is_pii: bool = ...) -> None: ...

class Flow(_message.Message):
    __slots__ = ("id", "name", "description", "start_step", "steps", "created_at", "created_by", "updated_at", "updated_by", "no_code_start_step", "no_code_steps", "flow_start_step", "flow_steps")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    START_STEP_FIELD_NUMBER: _ClassVar[int]
    STEPS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_START_STEP_FIELD_NUMBER: _ClassVar[int]
    NO_CODE_STEPS_FIELD_NUMBER: _ClassVar[int]
    FLOW_START_STEP_FIELD_NUMBER: _ClassVar[int]
    FLOW_STEPS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    start_step: FlowStep
    steps: _containers.RepeatedCompositeFieldContainer[FlowStep]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    no_code_start_step: NoCodeStep
    no_code_steps: _containers.RepeatedCompositeFieldContainer[NoCodeStep]
    flow_start_step: FlowStartStep
    flow_steps: _containers.RepeatedCompositeFieldContainer[Step]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., start_step: _Optional[_Union[FlowStep, _Mapping]] = ..., steps: _Optional[_Iterable[_Union[FlowStep, _Mapping]]] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., no_code_start_step: _Optional[_Union[NoCodeStep, _Mapping]] = ..., no_code_steps: _Optional[_Iterable[_Union[NoCodeStep, _Mapping]]] = ..., flow_start_step: _Optional[_Union[FlowStartStep, _Mapping]] = ..., flow_steps: _Optional[_Iterable[_Union[Step, _Mapping]]] = ...) -> None: ...

class Flows(_message.Message):
    __slots__ = ("flow_list",)
    FLOW_LIST_FIELD_NUMBER: _ClassVar[int]
    flow_list: _containers.RepeatedCompositeFieldContainer[Flow]
    def __init__(self, flow_list: _Optional[_Iterable[_Union[Flow, _Mapping]]] = ...) -> None: ...

class AudioToPlay(_message.Message):
    __slots__ = ("s3_path", "original_filename")
    S3_PATH_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_FILENAME_FIELD_NUMBER: _ClassVar[int]
    s3_path: str
    original_filename: str
    def __init__(self, s3_path: _Optional[str] = ..., original_filename: _Optional[str] = ...) -> None: ...

class IntroMessage(_message.Message):
    __slots__ = ("disclaimer_enabled", "disclaimer_message", "disclaimer_voice", "disclaimer_voice_id", "disclaimer_voice_tuning_settings", "ringing_tone", "language_code")
    DISCLAIMER_ENABLED_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_VOICE_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_VOICE_TUNING_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    RINGING_TONE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    disclaimer_enabled: bool
    disclaimer_message: str
    disclaimer_voice: Voice
    disclaimer_voice_id: str
    disclaimer_voice_tuning_settings: _containers.RepeatedCompositeFieldContainer[VoiceTuningSettings]
    ringing_tone: AudioToPlay
    language_code: str
    def __init__(self, disclaimer_enabled: bool = ..., disclaimer_message: _Optional[str] = ..., disclaimer_voice: _Optional[_Union[Voice, _Mapping]] = ..., disclaimer_voice_id: _Optional[str] = ..., disclaimer_voice_tuning_settings: _Optional[_Iterable[_Union[VoiceTuningSettings, _Mapping]]] = ..., ringing_tone: _Optional[_Union[AudioToPlay, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class AzureContentFilterCategory(_message.Message):
    __slots__ = ("is_active", "precision")
    IS_ACTIVE_FIELD_NUMBER: _ClassVar[int]
    PRECISION_FIELD_NUMBER: _ClassVar[int]
    is_active: bool
    precision: str
    def __init__(self, is_active: bool = ..., precision: _Optional[str] = ...) -> None: ...

class AzureContentFilter(_message.Message):
    __slots__ = ("violence", "hate", "sexual", "self_harm")
    VIOLENCE_FIELD_NUMBER: _ClassVar[int]
    HATE_FIELD_NUMBER: _ClassVar[int]
    SEXUAL_FIELD_NUMBER: _ClassVar[int]
    SELF_HARM_FIELD_NUMBER: _ClassVar[int]
    violence: AzureContentFilterCategory
    hate: AzureContentFilterCategory
    sexual: AzureContentFilterCategory
    self_harm: AzureContentFilterCategory
    def __init__(self, violence: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., hate: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., sexual: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ..., self_harm: _Optional[_Union[AzureContentFilterCategory, _Mapping]] = ...) -> None: ...

class ContentFilter(_message.Message):
    __slots__ = ("type", "azure_config", "disabled")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    AZURE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    DISABLED_FIELD_NUMBER: _ClassVar[int]
    type: str
    azure_config: AzureContentFilter
    disabled: bool
    def __init__(self, type: _Optional[str] = ..., azure_config: _Optional[_Union[AzureContentFilter, _Mapping]] = ..., disabled: bool = ...) -> None: ...

class LatencyConfig(_message.Message):
    __slots__ = ("interaction_type",)
    INTERACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    interaction_type: str
    def __init__(self, interaction_type: _Optional[str] = ...) -> None: ...

class BargeInConfig(_message.Message):
    __slots__ = ("enabled",)
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    def __init__(self, enabled: bool = ...) -> None: ...

class StopKeywords(_message.Message):
    __slots__ = ("id", "created_by", "created_at", "updated_by", "updated_at", "title", "description", "regular_expressions", "say_phrase", "function_id", "language_code")
    ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    SAY_PHRASE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    id: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    title: str
    description: str
    regular_expressions: _containers.RepeatedScalarFieldContainer[str]
    say_phrase: bool
    function_id: str
    language_code: str
    def __init__(self, id: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[str]] = ..., say_phrase: bool = ..., function_id: _Optional[str] = ..., language_code: _Optional[str] = ...) -> None: ...

class AsrKeyphrase(_message.Message):
    __slots__ = ("keyphrase", "level")
    KEYPHRASE_FIELD_NUMBER: _ClassVar[int]
    LEVEL_FIELD_NUMBER: _ClassVar[int]
    keyphrase: str
    level: str
    def __init__(self, keyphrase: _Optional[str] = ..., level: _Optional[str] = ...) -> None: ...

class Variant(_message.Message):
    __slots__ = ("id", "name", "created_by", "created_at", "updated_by", "updated_at", "is_default")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    is_default: bool
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., is_default: bool = ...) -> None: ...

class VariantAttribute(_message.Message):
    __slots__ = ("id", "name", "attribute_type", "created_by", "created_at", "updated_by", "updated_at", "values")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    attribute_type: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    values: _struct_pb2.Struct
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., attribute_type: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., values: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class AsrCorrection(_message.Message):
    __slots__ = ("id", "name", "description", "regular_expressions")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REGULAR_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    regular_expressions: _containers.RepeatedCompositeFieldContainer[AsrCorrectionRegularExpressions]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., regular_expressions: _Optional[_Iterable[_Union[AsrCorrectionRegularExpressions, _Mapping]]] = ...) -> None: ...

class AsrCorrectionRegularExpressions(_message.Message):
    __slots__ = ("regular_expression", "replacement", "replacement_type")
    REGULAR_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    regular_expression: str
    replacement: str
    replacement_type: str
    def __init__(self, regular_expression: _Optional[str] = ..., replacement: _Optional[str] = ..., replacement_type: _Optional[str] = ...) -> None: ...

class ApiIntegrations(_message.Message):
    __slots__ = ("api_integrations",)
    API_INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    api_integrations: _containers.RepeatedCompositeFieldContainer[ApiIntegration]
    def __init__(self, api_integrations: _Optional[_Iterable[_Union[ApiIntegration, _Mapping]]] = ...) -> None: ...

class ApiIntegration(_message.Message):
    __slots__ = ("id", "name", "description", "environments", "operations")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    ENVIRONMENTS_FIELD_NUMBER: _ClassVar[int]
    OPERATIONS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    description: str
    environments: Environments
    operations: _containers.RepeatedCompositeFieldContainer[ApiIntegrationOperation]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., environments: _Optional[_Union[Environments, _Mapping]] = ..., operations: _Optional[_Iterable[_Union[ApiIntegrationOperation, _Mapping]]] = ...) -> None: ...

class Environments(_message.Message):
    __slots__ = ("sandbox", "pre_release", "live")
    SANDBOX_FIELD_NUMBER: _ClassVar[int]
    PRE_RELEASE_FIELD_NUMBER: _ClassVar[int]
    LIVE_FIELD_NUMBER: _ClassVar[int]
    sandbox: ApiIntegrationConfig
    pre_release: ApiIntegrationConfig
    live: ApiIntegrationConfig
    def __init__(self, sandbox: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ..., pre_release: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ..., live: _Optional[_Union[ApiIntegrationConfig, _Mapping]] = ...) -> None: ...

class ApiIntegrationConfig(_message.Message):
    __slots__ = ("base_url", "auth_type")
    BASE_URL_FIELD_NUMBER: _ClassVar[int]
    AUTH_TYPE_FIELD_NUMBER: _ClassVar[int]
    base_url: str
    auth_type: str
    def __init__(self, base_url: _Optional[str] = ..., auth_type: _Optional[str] = ...) -> None: ...

class ApiIntegrationOperation(_message.Message):
    __slots__ = ("id", "name", "method", "resource")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    METHOD_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    method: str
    resource: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., method: _Optional[str] = ..., resource: _Optional[str] = ...) -> None: ...

class Language(_message.Message):
    __slots__ = ("code",)
    CODE_FIELD_NUMBER: _ClassVar[int]
    code: str
    def __init__(self, code: _Optional[str] = ...) -> None: ...

class Languages(_message.Message):
    __slots__ = ("default_language", "additional_languages")
    DEFAULT_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    default_language: Language
    additional_languages: _containers.RepeatedCompositeFieldContainer[Language]
    def __init__(self, default_language: _Optional[_Union[Language, _Mapping]] = ..., additional_languages: _Optional[_Iterable[_Union[Language, _Mapping]]] = ...) -> None: ...

class LanguageBehavior(_message.Message):
    __slots__ = ("behavior_prompt", "language_code")
    BEHAVIOR_PROMPT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    behavior_prompt: str
    language_code: str
    def __init__(self, behavior_prompt: _Optional[str] = ..., language_code: _Optional[str] = ...) -> None: ...

class Greeting(_message.Message):
    __slots__ = ("welcome_message", "language_code")
    WELCOME_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    welcome_message: str
    language_code: str
    def __init__(self, welcome_message: _Optional[str] = ..., language_code: _Optional[str] = ...) -> None: ...

class MultilingualAgentSettings(_message.Message):
    __slots__ = ("language_behaviors", "greetings")
    class LanguageBehaviorsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: LanguageBehavior
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[LanguageBehavior, _Mapping]] = ...) -> None: ...
    class GreetingsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: Greeting
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[Greeting, _Mapping]] = ...) -> None: ...
    LANGUAGE_BEHAVIORS_FIELD_NUMBER: _ClassVar[int]
    GREETINGS_FIELD_NUMBER: _ClassVar[int]
    language_behaviors: _containers.MessageMap[str, LanguageBehavior]
    greetings: _containers.MessageMap[str, Greeting]
    def __init__(self, language_behaviors: _Optional[_Mapping[str, LanguageBehavior]] = ..., greetings: _Optional[_Mapping[str, Greeting]] = ...) -> None: ...

class LocalizedText(_message.Message):
    __slots__ = ("text",)
    TEXT_FIELD_NUMBER: _ClassVar[int]
    text: str
    def __init__(self, text: _Optional[str] = ...) -> None: ...

class TranslationEntry(_message.Message):
    __slots__ = ("language_key", "translations", "id")
    class TranslationsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: LocalizedText
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[LocalizedText, _Mapping]] = ...) -> None: ...
    LANGUAGE_KEY_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    language_key: str
    translations: _containers.MessageMap[str, LocalizedText]
    id: str
    def __init__(self, language_key: _Optional[str] = ..., translations: _Optional[_Mapping[str, LocalizedText]] = ..., id: _Optional[str] = ...) -> None: ...

class MultilingualTranslations(_message.Message):
    __slots__ = ("translations",)
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    translations: _containers.RepeatedCompositeFieldContainer[TranslationEntry]
    def __init__(self, translations: _Optional[_Iterable[_Union[TranslationEntry, _Mapping]]] = ...) -> None: ...

class StylePrompt(_message.Message):
    __slots__ = ("prompt",)
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    prompt: str
    def __init__(self, prompt: _Optional[str] = ...) -> None: ...

class ChannelConfig(_message.Message):
    __slots__ = ("model_id", "style_prompt", "greeting", "safety_filters")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    GREETING_FIELD_NUMBER: _ClassVar[int]
    SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    style_prompt: StylePrompt
    greeting: Greeting
    safety_filters: ContentFilter
    def __init__(self, model_id: _Optional[str] = ..., style_prompt: _Optional[_Union[StylePrompt, _Mapping]] = ..., greeting: _Optional[_Union[Greeting, _Mapping]] = ..., safety_filters: _Optional[_Union[ContentFilter, _Mapping]] = ...) -> None: ...

class VoiceChannel(_message.Message):
    __slots__ = ("enabled", "config", "barge_in_config", "latency_config", "disclaimer")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    BARGE_IN_CONFIG_FIELD_NUMBER: _ClassVar[int]
    LATENCY_CONFIG_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    config: ChannelConfig
    barge_in_config: BargeInConfig
    latency_config: LatencyConfig
    disclaimer: IntroMessage
    def __init__(self, enabled: bool = ..., config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., barge_in_config: _Optional[_Union[BargeInConfig, _Mapping]] = ..., latency_config: _Optional[_Union[LatencyConfig, _Mapping]] = ..., disclaimer: _Optional[_Union[IntroMessage, _Mapping]] = ...) -> None: ...

class WebChatChannel(_message.Message):
    __slots__ = ("enabled", "config")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    config: ChannelConfig
    def __init__(self, enabled: bool = ..., config: _Optional[_Union[ChannelConfig, _Mapping]] = ...) -> None: ...

class Channels(_message.Message):
    __slots__ = ("voice", "web_chat")
    VOICE_FIELD_NUMBER: _ClassVar[int]
    WEB_CHAT_FIELD_NUMBER: _ClassVar[int]
    voice: VoiceChannel
    web_chat: WebChatChannel
    def __init__(self, voice: _Optional[_Union[VoiceChannel, _Mapping]] = ..., web_chat: _Optional[_Union[WebChatChannel, _Mapping]] = ...) -> None: ...
