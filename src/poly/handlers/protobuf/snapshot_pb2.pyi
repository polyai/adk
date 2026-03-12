from poly.handlers.protobuf import handoff_pb2 as _handoff_pb2
from poly.handlers.protobuf import knowledge_base_pb2 as _knowledge_base_pb2
from poly.handlers.protobuf import stop_keywords_pb2 as _stop_keywords_pb2
from poly.handlers.protobuf import sms_pb2 as _sms_pb2
from poly.handlers.protobuf import variant_pb2 as _variant_pb2
from poly.handlers.protobuf import llm_settings_pb2 as _llm_settings_pb2
from poly.handlers.protobuf import content_filter_settings_pb2 as _content_filter_settings_pb2
from poly.handlers.protobuf import asr_settings_pb2 as _asr_settings_pb2
from poly.handlers.protobuf import asr_pb2 as _asr_pb2
from poly.handlers.protobuf import languages_pb2 as _languages_pb2
from poly.handlers.protobuf import flows_pb2 as _flows_pb2
from poly.handlers.protobuf import functions_pb2 as _functions_pb2
from poly.handlers.protobuf import agent_settings_pb2 as _agent_settings_pb2
from poly.handlers.protobuf import transcript_corrections_pb2 as _transcript_corrections_pb2
from poly.handlers.protobuf import experimental_config_pb2 as _experimental_config_pb2
from poly.handlers.protobuf import pronunciations_pb2 as _pronunciations_pb2
from poly.handlers.protobuf import keyphrase_boosting_pb2 as _keyphrase_boosting_pb2
from poly.handlers.protobuf import start_function_pb2 as _start_function_pb2
from poly.handlers.protobuf import end_function_pb2 as _end_function_pb2
from poly.handlers.protobuf import entities_pb2 as _entities_pb2
from poly.handlers.protobuf import voice_pb2 as _voice_pb2
from poly.handlers.protobuf import api_integrations_pb2 as _api_integrations_pb2
from poly.handlers.protobuf import variables_pb2 as _variables_pb2
from poly.handlers.protobuf import translations_pb2 as _translations_pb2
from poly.handlers.protobuf import channels_pb2 as _channels_pb2
from poly.handlers.protobuf import csat_pb2 as _csat_pb2
from poly.handlers.protobuf import integrations_pb2 as _integrations_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Snapshot(_message.Message):
    __slots__ = ("handoffs", "knowledge_base", "sms", "variant_management", "stop_keywords", "llm_settings", "content_filter_settings", "asr_settings", "languages", "flows", "global_functions", "agent_settings", "transcript_corrections", "experimental_config", "pronunciations", "keyphrases_boosting", "start_function", "end_function", "voices", "entities", "asr", "api_integrations", "variables", "translations", "channels", "csat", "integrations")
    HANDOFFS_FIELD_NUMBER: _ClassVar[int]
    KNOWLEDGE_BASE_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    VARIANT_MANAGEMENT_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FILTER_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_FIELD_NUMBER: _ClassVar[int]
    FLOWS_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    AGENT_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_CONFIG_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    KEYPHRASES_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    VOICES_FIELD_NUMBER: _ClassVar[int]
    ENTITIES_FIELD_NUMBER: _ClassVar[int]
    ASR_FIELD_NUMBER: _ClassVar[int]
    API_INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    VARIABLES_FIELD_NUMBER: _ClassVar[int]
    TRANSLATIONS_FIELD_NUMBER: _ClassVar[int]
    CHANNELS_FIELD_NUMBER: _ClassVar[int]
    CSAT_FIELD_NUMBER: _ClassVar[int]
    INTEGRATIONS_FIELD_NUMBER: _ClassVar[int]
    handoffs: _handoff_pb2.Handoffs
    knowledge_base: _knowledge_base_pb2.KnowledgeBase
    sms: _sms_pb2.SMS
    variant_management: _variant_pb2.VariantManagement
    stop_keywords: _stop_keywords_pb2.StopKeywords
    llm_settings: _llm_settings_pb2.LLMSettings
    content_filter_settings: _content_filter_settings_pb2.ContentFilterSettings
    asr_settings: _asr_settings_pb2.ASRSettings
    languages: _languages_pb2.Languages
    flows: _flows_pb2.Flows
    global_functions: _functions_pb2.Functions
    agent_settings: _agent_settings_pb2.AgentSettings
    transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections
    experimental_config: _experimental_config_pb2.ExperimentalConfig
    pronunciations: _pronunciations_pb2.Pronunciations
    keyphrases_boosting: _keyphrase_boosting_pb2.KeyphrasesBoosting
    start_function: _start_function_pb2.StartFunction
    end_function: _end_function_pb2.EndFunction
    voices: _voice_pb2.Voices
    entities: _entities_pb2.Entities
    asr: _asr_pb2.Asr
    api_integrations: _api_integrations_pb2.ApiIntegrations
    variables: _variables_pb2.Variables
    translations: _translations_pb2.Translations
    channels: _channels_pb2.Channels
    csat: _csat_pb2.CSATConfig
    integrations: _integrations_pb2.Integrations
    def __init__(self, handoffs: _Optional[_Union[_handoff_pb2.Handoffs, _Mapping]] = ..., knowledge_base: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase, _Mapping]] = ..., sms: _Optional[_Union[_sms_pb2.SMS, _Mapping]] = ..., variant_management: _Optional[_Union[_variant_pb2.VariantManagement, _Mapping]] = ..., stop_keywords: _Optional[_Union[_stop_keywords_pb2.StopKeywords, _Mapping]] = ..., llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings, _Mapping]] = ..., content_filter_settings: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings, _Mapping]] = ..., asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings, _Mapping]] = ..., languages: _Optional[_Union[_languages_pb2.Languages, _Mapping]] = ..., flows: _Optional[_Union[_flows_pb2.Flows, _Mapping]] = ..., global_functions: _Optional[_Union[_functions_pb2.Functions, _Mapping]] = ..., agent_settings: _Optional[_Union[_agent_settings_pb2.AgentSettings, _Mapping]] = ..., transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections, _Mapping]] = ..., experimental_config: _Optional[_Union[_experimental_config_pb2.ExperimentalConfig, _Mapping]] = ..., pronunciations: _Optional[_Union[_pronunciations_pb2.Pronunciations, _Mapping]] = ..., keyphrases_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphrasesBoosting, _Mapping]] = ..., start_function: _Optional[_Union[_start_function_pb2.StartFunction, _Mapping]] = ..., end_function: _Optional[_Union[_end_function_pb2.EndFunction, _Mapping]] = ..., voices: _Optional[_Union[_voice_pb2.Voices, _Mapping]] = ..., entities: _Optional[_Union[_entities_pb2.Entities, _Mapping]] = ..., asr: _Optional[_Union[_asr_pb2.Asr, _Mapping]] = ..., api_integrations: _Optional[_Union[_api_integrations_pb2.ApiIntegrations, _Mapping]] = ..., variables: _Optional[_Union[_variables_pb2.Variables, _Mapping]] = ..., translations: _Optional[_Union[_translations_pb2.Translations, _Mapping]] = ..., channels: _Optional[_Union[_channels_pb2.Channels, _Mapping]] = ..., csat: _Optional[_Union[_csat_pb2.CSATConfig, _Mapping]] = ..., integrations: _Optional[_Union[_integrations_pb2.Integrations, _Mapping]] = ...) -> None: ...
