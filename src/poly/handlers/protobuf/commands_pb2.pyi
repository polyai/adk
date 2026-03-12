from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import struct_pb2 as _struct_pb2
from poly.handlers.protobuf import handoff_pb2 as _handoff_pb2
from poly.handlers.protobuf import knowledge_base_pb2 as _knowledge_base_pb2
from poly.handlers.protobuf import sms_pb2 as _sms_pb2
from poly.handlers.protobuf import stop_keywords_pb2 as _stop_keywords_pb2
from poly.handlers.protobuf import variant_pb2 as _variant_pb2
from poly.handlers.protobuf import llm_settings_pb2 as _llm_settings_pb2
from poly.handlers.protobuf import content_filter_settings_pb2 as _content_filter_settings_pb2
from poly.handlers.protobuf import asr_settings_pb2 as _asr_settings_pb2
from poly.handlers.protobuf import languages_pb2 as _languages_pb2
from poly.handlers.protobuf import transcript_corrections_pb2 as _transcript_corrections_pb2
from poly.handlers.protobuf import flows_pb2 as _flows_pb2
from poly.handlers.protobuf import agent_settings_pb2 as _agent_settings_pb2
from poly.handlers.protobuf import experimental_config_pb2 as _experimental_config_pb2
from poly.handlers.protobuf import pronunciations_pb2 as _pronunciations_pb2
from poly.handlers.protobuf import keyphrase_boosting_pb2 as _keyphrase_boosting_pb2
from poly.handlers.protobuf import voice_pb2 as _voice_pb2
from poly.handlers.protobuf import functions_pb2 as _functions_pb2
from poly.handlers.protobuf import start_function_pb2 as _start_function_pb2
from poly.handlers.protobuf import end_function_pb2 as _end_function_pb2
from poly.handlers.protobuf import entities_pb2 as _entities_pb2
from poly.handlers.protobuf import api_integrations_pb2 as _api_integrations_pb2
from poly.handlers.protobuf import variables_pb2 as _variables_pb2
from poly.handlers.protobuf import translations_pb2 as _translations_pb2
from poly.handlers.protobuf import channels_pb2 as _channels_pb2
from poly.handlers.protobuf import csat_pb2 as _csat_pb2
from poly.handlers.protobuf import integrations_pb2 as _integrations_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ResolutionStrategy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    theirs: _ClassVar[ResolutionStrategy]
    ours: _ClassVar[ResolutionStrategy]
    base: _ClassVar[ResolutionStrategy]
theirs: ResolutionStrategy
ours: ResolutionStrategy
base: ResolutionStrategy

class Metadata(_message.Message):
    __slots__ = ("created_at", "created_by")
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    def __init__(self, created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ...) -> None: ...

class Event(_message.Message):
    __slots__ = ("sequence", "command_id", "server_timestamp", "metadata", "create_topic", "update_topic", "delete_topic", "import_topics", "toggle_topic_status", "sms_create_template", "sms_update_template", "sms_delete_template", "handoff_create", "handoff_update", "handoff_delete", "handoff_set_default", "handoff_reset_handoff_configs", "create_flow_step", "update_flow_step", "delete_flow_step", "update_flow_step_position", "update_flow_step_positions", "update_flow_step_dtmf_config", "update_flow_step_asr_config", "create_flow_transition_function", "update_flow_transition_function", "delete_flow_transition_function", "delete_flow", "create_flow", "import_flow", "update_flow", "update_flow_transition_function_latency_control", "create_no_code_step", "update_no_code_step", "delete_no_code_step", "update_no_code_step_position", "create_no_code_condition", "delete_no_code_condition", "update_no_code_condition", "update_no_code_condition_position", "update_no_code_condition_exit_flow_position", "move_flow_component", "move_flow_components", "create_step", "update_step", "delete_step", "create_step_condition", "update_step_condition", "delete_step_condition", "update_step_condition_position", "variant_create_attribute", "variant_update_attribute", "variant_delete_attribute", "variant_create_variant", "variant_update_variant", "variant_delete_variant", "variant_set_default_variant", "variant_import_variants", "stop_keywords_create", "stop_keywords_update", "stop_keywords_delete", "update_llm_settings", "update_content_filter_settings", "update_asr_settings", "update_tts_settings", "languages_update_default_language", "languages_add_language", "languages_delete_language", "experimental_config_update_config", "pronunciations_create_pronunciation", "pronunciations_update_pronunciation", "pronunciations_delete_pronunciation", "pronunciations_reorder_pronunciations", "create_transcript_corrections", "update_transcript_corrections", "delete_transcript_corrections", "update_greeting", "update_personality", "update_role", "update_disclaimer_message", "update_rules", "update_language_behavior", "create_function", "update_function", "delete_function", "update_latency_control", "create_start_function", "update_start_function", "delete_start_function", "create_end_function", "update_end_function", "delete_end_function", "create_keyphrase_boosting", "update_keyphrase_boosting", "delete_keyphrase_boosting", "voice_add_agent_voice", "voice_delete_agent_voice", "voice_update_agent_voice", "voice_create_agent_voice_settings", "voice_update_agent_voice_settings", "voice_update_disclaimer_voice", "voice_create_disclaimer_voice_settings", "voice_update_disclaimer_voice_settings", "voice_add_favorite_voice", "voice_remove_favorite_voice", "branch_trigger_merge", "branch_created", "branch_merged", "branch_deleted", "project_created", "project_loaded_from_jupiter", "deployment_completed", "deployment_rollback", "entity_create", "entity_update", "entity_delete", "variable_create", "variable_update", "variable_delete", "function_deployment_completed", "create_api_integration", "update_api_integration", "delete_api_integration", "update_api_integration_config", "create_api_integration_operation", "update_api_integration_operation", "delete_api_integration_operation", "create_translation", "update_translation", "delete_translation", "voice_channel_update_asr_settings", "voice_channel_update_disclaimer", "channel_update_greeting", "channel_update_style_prompt", "channel_update_safety_filters", "channel_update_llm_settings", "channel_update_status", "csat_update_config", "connect_integration", "enable_integration", "disable_integration", "update_integration_functions", "disconnect_integration")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    CREATE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    DELETE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    IMPORT_TOPICS_FIELD_NUMBER: _ClassVar[int]
    TOGGLE_TOPIC_STATUS_FIELD_NUMBER: _ClassVar[int]
    SMS_CREATE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SMS_UPDATE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SMS_DELETE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_CREATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_UPDATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_DELETE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_SET_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_RESET_HANDOFF_CONFIGS_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_POSITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_ASR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_FIELD_NUMBER: _ClassVar[int]
    IMPORT_FLOW_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_TRANSITION_FUNCTION_LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_STEP_POSITION_FIELD_NUMBER: _ClassVar[int]
    CREATE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    DELETE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_POSITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_EXIT_FLOW_POSITION_FIELD_NUMBER: _ClassVar[int]
    MOVE_FLOW_COMPONENT_FIELD_NUMBER: _ClassVar[int]
    MOVE_FLOW_COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    CREATE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_STEP_FIELD_NUMBER: _ClassVar[int]
    CREATE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    DELETE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_CONDITION_POSITION_FIELD_NUMBER: _ClassVar[int]
    VARIANT_CREATE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_UPDATE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_DELETE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_CREATE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_UPDATE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_DELETE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_SET_DEFAULT_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_IMPORT_VARIANTS_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_CREATE_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_DELETE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_CONTENT_FILTER_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TTS_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_UPDATE_DEFAULT_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_ADD_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_DELETE_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_CONFIG_UPDATE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_CREATE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_UPDATE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_DELETE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_REORDER_PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    CREATE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    DELETE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_GREETING_FIELD_NUMBER: _ClassVar[int]
    UPDATE_PERSONALITY_FIELD_NUMBER: _ClassVar[int]
    UPDATE_ROLE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_DISCLAIMER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_RULES_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LANGUAGE_BEHAVIOR_FIELD_NUMBER: _ClassVar[int]
    CREATE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CREATE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CREATE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    UPDATE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    DELETE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    VOICE_ADD_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_DELETE_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_CREATE_AGENT_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_AGENT_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_DISCLAIMER_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_CREATE_DISCLAIMER_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_DISCLAIMER_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_ADD_FAVORITE_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_REMOVE_FAVORITE_VOICE_FIELD_NUMBER: _ClassVar[int]
    BRANCH_TRIGGER_MERGE_FIELD_NUMBER: _ClassVar[int]
    BRANCH_CREATED_FIELD_NUMBER: _ClassVar[int]
    BRANCH_MERGED_FIELD_NUMBER: _ClassVar[int]
    BRANCH_DELETED_FIELD_NUMBER: _ClassVar[int]
    PROJECT_CREATED_FIELD_NUMBER: _ClassVar[int]
    PROJECT_LOADED_FROM_JUPITER_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    DEPLOYMENT_ROLLBACK_FIELD_NUMBER: _ClassVar[int]
    ENTITY_CREATE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_DELETE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_CREATE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_UPDATE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_DELETE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_DEPLOYMENT_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    CREATE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CREATE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    CREATE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    VOICE_CHANNEL_UPDATE_ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_CHANNEL_UPDATE_DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_GREETING_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_STATUS_FIELD_NUMBER: _ClassVar[int]
    CSAT_UPDATE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CONNECT_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    ENABLE_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    DISABLE_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_INTEGRATION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    DISCONNECT_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    command_id: str
    server_timestamp: _timestamp_pb2.Timestamp
    metadata: Metadata
    create_topic: _knowledge_base_pb2.KnowledgeBase_CreateTopic
    update_topic: _knowledge_base_pb2.KnowledgeBase_UpdateTopic
    delete_topic: _knowledge_base_pb2.KnowledgeBase_DeleteTopic
    import_topics: _knowledge_base_pb2.KnowledgeBase_ImportTopics
    toggle_topic_status: _knowledge_base_pb2.KnowledgeBase_ToggleTopicStatus
    sms_create_template: _sms_pb2.SMS_CreateTemplate
    sms_update_template: _sms_pb2.SMS_UpdateTemplate
    sms_delete_template: _sms_pb2.SMS_DeleteTemplate
    handoff_create: _handoff_pb2.Handoff_Create
    handoff_update: _handoff_pb2.Handoff_Update
    handoff_delete: _handoff_pb2.Handoff_Delete
    handoff_set_default: _handoff_pb2.Handoff_SetDefault
    handoff_reset_handoff_configs: _handoff_pb2.Handoff_ResetHandoffConfigs
    create_flow_step: _flows_pb2.Flow_CreateStep
    update_flow_step: _flows_pb2.Flow_UpdateStep
    delete_flow_step: _flows_pb2.Flow_DeleteStep
    update_flow_step_position: _flows_pb2.Flow_UpdateStepPosition
    update_flow_step_positions: _flows_pb2.Flow_UpdateStepPositions
    update_flow_step_dtmf_config: _flows_pb2.Flow_UpdateStepDtmfConfig
    update_flow_step_asr_config: _flows_pb2.Flow_UpdateStepAsrConfig
    create_flow_transition_function: _flows_pb2.Flow_CreateTransitionFunction
    update_flow_transition_function: _flows_pb2.Flow_UpdateTransitionFunction
    delete_flow_transition_function: _flows_pb2.Flow_DeleteTransitionFunction
    delete_flow: _flows_pb2.Flow_DeleteFlow
    create_flow: _flows_pb2.Flow_CreateFlow
    import_flow: _flows_pb2.Flow_ImportFlow
    update_flow: _flows_pb2.Flow_UpdateFlow
    update_flow_transition_function_latency_control: _flows_pb2.Flow_UpdateTransitionFunctionLatencyControl
    create_no_code_step: _flows_pb2.CreateNoCodeStep
    update_no_code_step: _flows_pb2.UpdateNoCodeStep
    delete_no_code_step: _flows_pb2.DeleteNoCodeStep
    update_no_code_step_position: _flows_pb2.UpdateNoCodeStepPosition
    create_no_code_condition: _flows_pb2.CreateNoCodeCondition
    delete_no_code_condition: _flows_pb2.DeleteNoCodeCondition
    update_no_code_condition: _flows_pb2.UpdateNoCodeCondition
    update_no_code_condition_position: _flows_pb2.UpdateNoCodeConditionPosition
    update_no_code_condition_exit_flow_position: _flows_pb2.UpdateNoCodeConditionExitFlowPosition
    move_flow_component: _flows_pb2.MoveFlowComponent
    move_flow_components: _flows_pb2.MoveFlowComponents
    create_step: _flows_pb2.CreateStep
    update_step: _flows_pb2.UpdateStep
    delete_step: _flows_pb2.DeleteStep
    create_step_condition: _flows_pb2.CreateStepCondition
    update_step_condition: _flows_pb2.UpdateStepCondition
    delete_step_condition: _flows_pb2.DeleteStepCondition
    update_step_condition_position: _flows_pb2.UpdateStepConditionPosition
    variant_create_attribute: _variant_pb2.Variant_CreateAttribute
    variant_update_attribute: _variant_pb2.Variant_UpdateAttribute
    variant_delete_attribute: _variant_pb2.Variant_DeleteAttribute
    variant_create_variant: _variant_pb2.Variant_CreateVariant
    variant_update_variant: _variant_pb2.Variant_UpdateVariant
    variant_delete_variant: _variant_pb2.Variant_DeleteVariant
    variant_set_default_variant: _variant_pb2.Variant_SetDefaultVariant
    variant_import_variants: _variant_pb2.Variant_ImportVariants
    stop_keywords_create: _stop_keywords_pb2.StopKeyword_Create
    stop_keywords_update: _stop_keywords_pb2.StopKeyword_Update
    stop_keywords_delete: _stop_keywords_pb2.StopKeyword_Delete
    update_llm_settings: _llm_settings_pb2.LLMSettings_UpdateLLMSettings
    update_content_filter_settings: _content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings
    update_asr_settings: _asr_settings_pb2.ASRSettings_UpdateASRSettings
    update_tts_settings: _languages_pb2.Languages_UpdateDefaultLanguage
    languages_update_default_language: _languages_pb2.Languages_UpdateDefaultLanguage
    languages_add_language: _languages_pb2.Languages_AddLanguage
    languages_delete_language: _languages_pb2.Languages_DeleteLanguage
    experimental_config_update_config: _experimental_config_pb2.ExperimentalConfig_UpdateConfig
    pronunciations_create_pronunciation: _pronunciations_pb2.Pronunciations_CreatePronunciation
    pronunciations_update_pronunciation: _pronunciations_pb2.Pronunciations_UpdatePronunciation
    pronunciations_delete_pronunciation: _pronunciations_pb2.Pronunciations_DeletePronunciation
    pronunciations_reorder_pronunciations: _pronunciations_pb2.Pronunciations_ReorderPronunciations
    create_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_CreateTranscriptCorrections
    update_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_UpdateTranscriptCorrections
    delete_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_DeleteTranscriptCorrections
    update_greeting: _agent_settings_pb2.Greeting_UpdateGreeting
    update_personality: _agent_settings_pb2.Personality_UpdatePersonality
    update_role: _agent_settings_pb2.Role_UpdateRole
    update_disclaimer_message: _agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage
    update_rules: _agent_settings_pb2.Rules_UpdateRules
    update_language_behavior: _agent_settings_pb2.LanguageBehavior_UpdateLanguageBehavior
    create_function: _functions_pb2.Function_CreateFunction
    update_function: _functions_pb2.Function_UpdateFunction
    delete_function: _functions_pb2.Function_DeleteFunction
    update_latency_control: _functions_pb2.Function_UpdateLatencyControl
    create_start_function: _start_function_pb2.StartFunction_Create
    update_start_function: _start_function_pb2.StartFunction_Update
    delete_start_function: _start_function_pb2.StartFunction_Delete
    create_end_function: _end_function_pb2.EndFunction_Create
    update_end_function: _end_function_pb2.EndFunction_Update
    delete_end_function: _end_function_pb2.EndFunction_Delete
    create_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_CreateKeyphrase
    update_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_UpdateKeyphrase
    delete_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_DeleteKeyphrase
    voice_add_agent_voice: _voice_pb2.Voice_AddAgentVoice
    voice_delete_agent_voice: _voice_pb2.Voice_DeleteAgentVoice
    voice_update_agent_voice: _voice_pb2.Voice_UpdateAgentVoice
    voice_create_agent_voice_settings: _voice_pb2.Voice_CreateAgentVoiceSettings
    voice_update_agent_voice_settings: _voice_pb2.Voice_UpdateAgentVoiceSettings
    voice_update_disclaimer_voice: _voice_pb2.Voice_UpdateDisclaimerVoice
    voice_create_disclaimer_voice_settings: _voice_pb2.Voice_CreateDisclaimerVoiceSettings
    voice_update_disclaimer_voice_settings: _voice_pb2.Voice_UpdateDisclaimerVoiceSettings
    voice_add_favorite_voice: _voice_pb2.Voice_AddFavoriteVoice
    voice_remove_favorite_voice: _voice_pb2.Voice_RemoveFavoriteVoice
    branch_trigger_merge: Branch_TriggerMerge
    branch_created: Branch_Created
    branch_merged: Branch_Merged
    branch_deleted: Branch_Deleted
    project_created: Project_Created
    project_loaded_from_jupiter: Project_LoadedFromJupiter
    deployment_completed: DeploymentCompleted
    deployment_rollback: DeploymentRollback
    entity_create: _entities_pb2.Entity_Create
    entity_update: _entities_pb2.Entity_Update
    entity_delete: _entities_pb2.Entity_Delete
    variable_create: _variables_pb2.Variable_Create
    variable_update: _variables_pb2.Variable_Update
    variable_delete: _variables_pb2.Variable_Delete
    function_deployment_completed: FunctionDeploymentCompleted
    create_api_integration: _api_integrations_pb2.ApiIntegration_Create
    update_api_integration: _api_integrations_pb2.ApiIntegration_Update
    delete_api_integration: _api_integrations_pb2.ApiIntegration_Delete
    update_api_integration_config: _api_integrations_pb2.ApiIntegrationConfig_Update
    create_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Create
    update_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Update
    delete_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Delete
    create_translation: _translations_pb2.LanguageHubTranslations_Create
    update_translation: _translations_pb2.LanguageHubTranslations_Update
    delete_translation: _translations_pb2.LanguageHubTranslations_Delete
    voice_channel_update_asr_settings: _channels_pb2.VoiceChannel_UpdateASRSettings
    voice_channel_update_disclaimer: _channels_pb2.VoiceChannel_UpdateDisclaimer
    channel_update_greeting: _channels_pb2.Channel_UpdateGreeting
    channel_update_style_prompt: _channels_pb2.Channel_UpdateStylePrompt
    channel_update_safety_filters: _channels_pb2.Channel_UpdateSafetyFilters
    channel_update_llm_settings: _channels_pb2.Channel_UpdateLLMSettings
    channel_update_status: _channels_pb2.Channel_UpdateStatus
    csat_update_config: _csat_pb2.CSAT_UpdateConfig
    connect_integration: _integrations_pb2.Integration_Connect
    enable_integration: _integrations_pb2.Integration_Enable
    disable_integration: _integrations_pb2.Integration_Disable
    update_integration_functions: _integrations_pb2.Integration_UpdateFunctions
    disconnect_integration: _integrations_pb2.Integration_Disconnect
    def __init__(self, sequence: _Optional[int] = ..., command_id: _Optional[str] = ..., server_timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., metadata: _Optional[_Union[Metadata, _Mapping]] = ..., create_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_CreateTopic, _Mapping]] = ..., update_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_UpdateTopic, _Mapping]] = ..., delete_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_DeleteTopic, _Mapping]] = ..., import_topics: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_ImportTopics, _Mapping]] = ..., toggle_topic_status: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_ToggleTopicStatus, _Mapping]] = ..., sms_create_template: _Optional[_Union[_sms_pb2.SMS_CreateTemplate, _Mapping]] = ..., sms_update_template: _Optional[_Union[_sms_pb2.SMS_UpdateTemplate, _Mapping]] = ..., sms_delete_template: _Optional[_Union[_sms_pb2.SMS_DeleteTemplate, _Mapping]] = ..., handoff_create: _Optional[_Union[_handoff_pb2.Handoff_Create, _Mapping]] = ..., handoff_update: _Optional[_Union[_handoff_pb2.Handoff_Update, _Mapping]] = ..., handoff_delete: _Optional[_Union[_handoff_pb2.Handoff_Delete, _Mapping]] = ..., handoff_set_default: _Optional[_Union[_handoff_pb2.Handoff_SetDefault, _Mapping]] = ..., handoff_reset_handoff_configs: _Optional[_Union[_handoff_pb2.Handoff_ResetHandoffConfigs, _Mapping]] = ..., create_flow_step: _Optional[_Union[_flows_pb2.Flow_CreateStep, _Mapping]] = ..., update_flow_step: _Optional[_Union[_flows_pb2.Flow_UpdateStep, _Mapping]] = ..., delete_flow_step: _Optional[_Union[_flows_pb2.Flow_DeleteStep, _Mapping]] = ..., update_flow_step_position: _Optional[_Union[_flows_pb2.Flow_UpdateStepPosition, _Mapping]] = ..., update_flow_step_positions: _Optional[_Union[_flows_pb2.Flow_UpdateStepPositions, _Mapping]] = ..., update_flow_step_dtmf_config: _Optional[_Union[_flows_pb2.Flow_UpdateStepDtmfConfig, _Mapping]] = ..., update_flow_step_asr_config: _Optional[_Union[_flows_pb2.Flow_UpdateStepAsrConfig, _Mapping]] = ..., create_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_CreateTransitionFunction, _Mapping]] = ..., update_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_UpdateTransitionFunction, _Mapping]] = ..., delete_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_DeleteTransitionFunction, _Mapping]] = ..., delete_flow: _Optional[_Union[_flows_pb2.Flow_DeleteFlow, _Mapping]] = ..., create_flow: _Optional[_Union[_flows_pb2.Flow_CreateFlow, _Mapping]] = ..., import_flow: _Optional[_Union[_flows_pb2.Flow_ImportFlow, _Mapping]] = ..., update_flow: _Optional[_Union[_flows_pb2.Flow_UpdateFlow, _Mapping]] = ..., update_flow_transition_function_latency_control: _Optional[_Union[_flows_pb2.Flow_UpdateTransitionFunctionLatencyControl, _Mapping]] = ..., create_no_code_step: _Optional[_Union[_flows_pb2.CreateNoCodeStep, _Mapping]] = ..., update_no_code_step: _Optional[_Union[_flows_pb2.UpdateNoCodeStep, _Mapping]] = ..., delete_no_code_step: _Optional[_Union[_flows_pb2.DeleteNoCodeStep, _Mapping]] = ..., update_no_code_step_position: _Optional[_Union[_flows_pb2.UpdateNoCodeStepPosition, _Mapping]] = ..., create_no_code_condition: _Optional[_Union[_flows_pb2.CreateNoCodeCondition, _Mapping]] = ..., delete_no_code_condition: _Optional[_Union[_flows_pb2.DeleteNoCodeCondition, _Mapping]] = ..., update_no_code_condition: _Optional[_Union[_flows_pb2.UpdateNoCodeCondition, _Mapping]] = ..., update_no_code_condition_position: _Optional[_Union[_flows_pb2.UpdateNoCodeConditionPosition, _Mapping]] = ..., update_no_code_condition_exit_flow_position: _Optional[_Union[_flows_pb2.UpdateNoCodeConditionExitFlowPosition, _Mapping]] = ..., move_flow_component: _Optional[_Union[_flows_pb2.MoveFlowComponent, _Mapping]] = ..., move_flow_components: _Optional[_Union[_flows_pb2.MoveFlowComponents, _Mapping]] = ..., create_step: _Optional[_Union[_flows_pb2.CreateStep, _Mapping]] = ..., update_step: _Optional[_Union[_flows_pb2.UpdateStep, _Mapping]] = ..., delete_step: _Optional[_Union[_flows_pb2.DeleteStep, _Mapping]] = ..., create_step_condition: _Optional[_Union[_flows_pb2.CreateStepCondition, _Mapping]] = ..., update_step_condition: _Optional[_Union[_flows_pb2.UpdateStepCondition, _Mapping]] = ..., delete_step_condition: _Optional[_Union[_flows_pb2.DeleteStepCondition, _Mapping]] = ..., update_step_condition_position: _Optional[_Union[_flows_pb2.UpdateStepConditionPosition, _Mapping]] = ..., variant_create_attribute: _Optional[_Union[_variant_pb2.Variant_CreateAttribute, _Mapping]] = ..., variant_update_attribute: _Optional[_Union[_variant_pb2.Variant_UpdateAttribute, _Mapping]] = ..., variant_delete_attribute: _Optional[_Union[_variant_pb2.Variant_DeleteAttribute, _Mapping]] = ..., variant_create_variant: _Optional[_Union[_variant_pb2.Variant_CreateVariant, _Mapping]] = ..., variant_update_variant: _Optional[_Union[_variant_pb2.Variant_UpdateVariant, _Mapping]] = ..., variant_delete_variant: _Optional[_Union[_variant_pb2.Variant_DeleteVariant, _Mapping]] = ..., variant_set_default_variant: _Optional[_Union[_variant_pb2.Variant_SetDefaultVariant, _Mapping]] = ..., variant_import_variants: _Optional[_Union[_variant_pb2.Variant_ImportVariants, _Mapping]] = ..., stop_keywords_create: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Create, _Mapping]] = ..., stop_keywords_update: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Update, _Mapping]] = ..., stop_keywords_delete: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Delete, _Mapping]] = ..., update_llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings_UpdateLLMSettings, _Mapping]] = ..., update_content_filter_settings: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings, _Mapping]] = ..., update_asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings_UpdateASRSettings, _Mapping]] = ..., update_tts_settings: _Optional[_Union[_languages_pb2.Languages_UpdateDefaultLanguage, _Mapping]] = ..., languages_update_default_language: _Optional[_Union[_languages_pb2.Languages_UpdateDefaultLanguage, _Mapping]] = ..., languages_add_language: _Optional[_Union[_languages_pb2.Languages_AddLanguage, _Mapping]] = ..., languages_delete_language: _Optional[_Union[_languages_pb2.Languages_DeleteLanguage, _Mapping]] = ..., experimental_config_update_config: _Optional[_Union[_experimental_config_pb2.ExperimentalConfig_UpdateConfig, _Mapping]] = ..., pronunciations_create_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_CreatePronunciation, _Mapping]] = ..., pronunciations_update_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_UpdatePronunciation, _Mapping]] = ..., pronunciations_delete_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_DeletePronunciation, _Mapping]] = ..., pronunciations_reorder_pronunciations: _Optional[_Union[_pronunciations_pb2.Pronunciations_ReorderPronunciations, _Mapping]] = ..., create_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_CreateTranscriptCorrections, _Mapping]] = ..., update_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_UpdateTranscriptCorrections, _Mapping]] = ..., delete_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_DeleteTranscriptCorrections, _Mapping]] = ..., update_greeting: _Optional[_Union[_agent_settings_pb2.Greeting_UpdateGreeting, _Mapping]] = ..., update_personality: _Optional[_Union[_agent_settings_pb2.Personality_UpdatePersonality, _Mapping]] = ..., update_role: _Optional[_Union[_agent_settings_pb2.Role_UpdateRole, _Mapping]] = ..., update_disclaimer_message: _Optional[_Union[_agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage, _Mapping]] = ..., update_rules: _Optional[_Union[_agent_settings_pb2.Rules_UpdateRules, _Mapping]] = ..., update_language_behavior: _Optional[_Union[_agent_settings_pb2.LanguageBehavior_UpdateLanguageBehavior, _Mapping]] = ..., create_function: _Optional[_Union[_functions_pb2.Function_CreateFunction, _Mapping]] = ..., update_function: _Optional[_Union[_functions_pb2.Function_UpdateFunction, _Mapping]] = ..., delete_function: _Optional[_Union[_functions_pb2.Function_DeleteFunction, _Mapping]] = ..., update_latency_control: _Optional[_Union[_functions_pb2.Function_UpdateLatencyControl, _Mapping]] = ..., create_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Create, _Mapping]] = ..., update_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Update, _Mapping]] = ..., delete_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Delete, _Mapping]] = ..., create_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Create, _Mapping]] = ..., update_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Update, _Mapping]] = ..., delete_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Delete, _Mapping]] = ..., create_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_CreateKeyphrase, _Mapping]] = ..., update_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_UpdateKeyphrase, _Mapping]] = ..., delete_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_DeleteKeyphrase, _Mapping]] = ..., voice_add_agent_voice: _Optional[_Union[_voice_pb2.Voice_AddAgentVoice, _Mapping]] = ..., voice_delete_agent_voice: _Optional[_Union[_voice_pb2.Voice_DeleteAgentVoice, _Mapping]] = ..., voice_update_agent_voice: _Optional[_Union[_voice_pb2.Voice_UpdateAgentVoice, _Mapping]] = ..., voice_create_agent_voice_settings: _Optional[_Union[_voice_pb2.Voice_CreateAgentVoiceSettings, _Mapping]] = ..., voice_update_agent_voice_settings: _Optional[_Union[_voice_pb2.Voice_UpdateAgentVoiceSettings, _Mapping]] = ..., voice_update_disclaimer_voice: _Optional[_Union[_voice_pb2.Voice_UpdateDisclaimerVoice, _Mapping]] = ..., voice_create_disclaimer_voice_settings: _Optional[_Union[_voice_pb2.Voice_CreateDisclaimerVoiceSettings, _Mapping]] = ..., voice_update_disclaimer_voice_settings: _Optional[_Union[_voice_pb2.Voice_UpdateDisclaimerVoiceSettings, _Mapping]] = ..., voice_add_favorite_voice: _Optional[_Union[_voice_pb2.Voice_AddFavoriteVoice, _Mapping]] = ..., voice_remove_favorite_voice: _Optional[_Union[_voice_pb2.Voice_RemoveFavoriteVoice, _Mapping]] = ..., branch_trigger_merge: _Optional[_Union[Branch_TriggerMerge, _Mapping]] = ..., branch_created: _Optional[_Union[Branch_Created, _Mapping]] = ..., branch_merged: _Optional[_Union[Branch_Merged, _Mapping]] = ..., branch_deleted: _Optional[_Union[Branch_Deleted, _Mapping]] = ..., project_created: _Optional[_Union[Project_Created, _Mapping]] = ..., project_loaded_from_jupiter: _Optional[_Union[Project_LoadedFromJupiter, _Mapping]] = ..., deployment_completed: _Optional[_Union[DeploymentCompleted, _Mapping]] = ..., deployment_rollback: _Optional[_Union[DeploymentRollback, _Mapping]] = ..., entity_create: _Optional[_Union[_entities_pb2.Entity_Create, _Mapping]] = ..., entity_update: _Optional[_Union[_entities_pb2.Entity_Update, _Mapping]] = ..., entity_delete: _Optional[_Union[_entities_pb2.Entity_Delete, _Mapping]] = ..., variable_create: _Optional[_Union[_variables_pb2.Variable_Create, _Mapping]] = ..., variable_update: _Optional[_Union[_variables_pb2.Variable_Update, _Mapping]] = ..., variable_delete: _Optional[_Union[_variables_pb2.Variable_Delete, _Mapping]] = ..., function_deployment_completed: _Optional[_Union[FunctionDeploymentCompleted, _Mapping]] = ..., create_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Create, _Mapping]] = ..., update_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Update, _Mapping]] = ..., delete_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Delete, _Mapping]] = ..., update_api_integration_config: _Optional[_Union[_api_integrations_pb2.ApiIntegrationConfig_Update, _Mapping]] = ..., create_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Create, _Mapping]] = ..., update_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Update, _Mapping]] = ..., delete_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Delete, _Mapping]] = ..., create_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Create, _Mapping]] = ..., update_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Update, _Mapping]] = ..., delete_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Delete, _Mapping]] = ..., voice_channel_update_asr_settings: _Optional[_Union[_channels_pb2.VoiceChannel_UpdateASRSettings, _Mapping]] = ..., voice_channel_update_disclaimer: _Optional[_Union[_channels_pb2.VoiceChannel_UpdateDisclaimer, _Mapping]] = ..., channel_update_greeting: _Optional[_Union[_channels_pb2.Channel_UpdateGreeting, _Mapping]] = ..., channel_update_style_prompt: _Optional[_Union[_channels_pb2.Channel_UpdateStylePrompt, _Mapping]] = ..., channel_update_safety_filters: _Optional[_Union[_channels_pb2.Channel_UpdateSafetyFilters, _Mapping]] = ..., channel_update_llm_settings: _Optional[_Union[_channels_pb2.Channel_UpdateLLMSettings, _Mapping]] = ..., channel_update_status: _Optional[_Union[_channels_pb2.Channel_UpdateStatus, _Mapping]] = ..., csat_update_config: _Optional[_Union[_csat_pb2.CSAT_UpdateConfig, _Mapping]] = ..., connect_integration: _Optional[_Union[_integrations_pb2.Integration_Connect, _Mapping]] = ..., enable_integration: _Optional[_Union[_integrations_pb2.Integration_Enable, _Mapping]] = ..., disable_integration: _Optional[_Union[_integrations_pb2.Integration_Disable, _Mapping]] = ..., update_integration_functions: _Optional[_Union[_integrations_pb2.Integration_UpdateFunctions, _Mapping]] = ..., disconnect_integration: _Optional[_Union[_integrations_pb2.Integration_Disconnect, _Mapping]] = ...) -> None: ...

class EventBatch(_message.Message):
    __slots__ = ("events",)
    EVENTS_FIELD_NUMBER: _ClassVar[int]
    events: _containers.RepeatedCompositeFieldContainer[Event]
    def __init__(self, events: _Optional[_Iterable[_Union[Event, _Mapping]]] = ...) -> None: ...

class SetProjection(_message.Message):
    __slots__ = ("sequence", "projection", "server_timestamp")
    SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    PROJECTION_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    sequence: int
    projection: bytes
    server_timestamp: _timestamp_pb2.Timestamp
    def __init__(self, sequence: _Optional[int] = ..., projection: _Optional[bytes] = ..., server_timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class SocketError(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class Envelope(_message.Message):
    __slots__ = ("event_batch", "set_projection", "notification", "error")
    EVENT_BATCH_FIELD_NUMBER: _ClassVar[int]
    SET_PROJECTION_FIELD_NUMBER: _ClassVar[int]
    NOTIFICATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    event_batch: EventBatch
    set_projection: SetProjection
    notification: Notification
    error: SocketError
    def __init__(self, event_batch: _Optional[_Union[EventBatch, _Mapping]] = ..., set_projection: _Optional[_Union[SetProjection, _Mapping]] = ..., notification: _Optional[_Union[Notification, _Mapping]] = ..., error: _Optional[_Union[SocketError, _Mapping]] = ...) -> None: ...

class Notification(_message.Message):
    __slots__ = ("type", "branch_created", "branch_merged", "branch_deleted", "branch_trigger_merge")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    BRANCH_CREATED_FIELD_NUMBER: _ClassVar[int]
    BRANCH_MERGED_FIELD_NUMBER: _ClassVar[int]
    BRANCH_DELETED_FIELD_NUMBER: _ClassVar[int]
    BRANCH_TRIGGER_MERGE_FIELD_NUMBER: _ClassVar[int]
    type: str
    branch_created: Branch_Created
    branch_merged: Branch_Merged
    branch_deleted: Branch_Deleted
    branch_trigger_merge: Branch_TriggerMerge
    def __init__(self, type: _Optional[str] = ..., branch_created: _Optional[_Union[Branch_Created, _Mapping]] = ..., branch_merged: _Optional[_Union[Branch_Merged, _Mapping]] = ..., branch_deleted: _Optional[_Union[Branch_Deleted, _Mapping]] = ..., branch_trigger_merge: _Optional[_Union[Branch_TriggerMerge, _Mapping]] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("type", "metadata", "command_id", "create_topic", "update_topic", "delete_topic", "import_topics", "toggle_topic_status", "sms_create_template", "sms_update_template", "sms_delete_template", "handoff_create", "handoff_update", "handoff_delete", "handoff_set_default", "handoff_reset_handoff_configs", "variant_create_attribute", "variant_update_attribute", "variant_delete_attribute", "variant_create_variant", "variant_update_variant", "variant_delete_variant", "variant_set_default_variant", "variant_import_variants", "stop_keywords_create", "stop_keywords_update", "stop_keywords_delete", "update_llm_settings", "update_content_filter_settings", "update_asr_settings", "update_tts_settings", "languages_update_default_language", "languages_add_language", "languages_delete_language", "experimental_config_update_config", "pronunciations_create_pronunciation", "pronunciations_update_pronunciation", "pronunciations_delete_pronunciation", "pronunciations_reorder_pronunciations", "create_transcript_corrections", "update_transcript_corrections", "delete_transcript_corrections", "update_greeting", "update_personality", "update_role", "update_disclaimer_message", "update_rules", "update_language_behavior", "create_function", "update_function", "delete_function", "update_latency_control", "create_start_function", "update_start_function", "delete_start_function", "create_end_function", "update_end_function", "delete_end_function", "voice_add_agent_voice", "voice_delete_agent_voice", "voice_update_agent_voice", "voice_create_agent_voice_settings", "voice_update_agent_voice_settings", "voice_update_disclaimer_voice", "voice_create_disclaimer_voice_settings", "voice_update_disclaimer_voice_settings", "voice_add_favorite_voice", "voice_remove_favorite_voice", "entity_create", "entity_update", "entity_delete", "variable_create", "variable_update", "variable_delete", "create_flow_step", "update_flow_step", "delete_flow_step", "update_flow_step_position", "update_flow_step_positions", "update_flow_step_dtmf_config", "update_flow_step_asr_config", "create_flow_transition_function", "update_flow_transition_function", "delete_flow_transition_function", "delete_flow", "create_flow", "import_flow", "update_flow", "update_flow_transition_function_latency_control", "create_no_code_step", "update_no_code_step", "delete_no_code_step", "update_no_code_step_position", "create_no_code_condition", "delete_no_code_condition", "update_no_code_condition", "update_no_code_condition_position", "update_no_code_condition_exit_flow_position", "move_flow_component", "move_flow_components", "create_step", "update_step", "delete_step", "create_step_condition", "update_step_condition", "delete_step_condition", "update_step_condition_position", "create_keyphrase_boosting", "update_keyphrase_boosting", "delete_keyphrase_boosting", "create_api_integration", "update_api_integration", "delete_api_integration", "update_api_integration_config", "create_api_integration_operation", "update_api_integration_operation", "delete_api_integration_operation", "create_translation", "update_translation", "delete_translation", "voice_channel_update_asr_settings", "voice_channel_update_disclaimer", "channel_update_greeting", "channel_update_style_prompt", "channel_update_safety_filters", "channel_update_llm_settings", "channel_update_status", "csat_update_config", "connect_integration", "enable_integration", "disable_integration", "update_integration_functions", "disconnect_integration")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    CREATE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    DELETE_TOPIC_FIELD_NUMBER: _ClassVar[int]
    IMPORT_TOPICS_FIELD_NUMBER: _ClassVar[int]
    TOGGLE_TOPIC_STATUS_FIELD_NUMBER: _ClassVar[int]
    SMS_CREATE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SMS_UPDATE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SMS_DELETE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_CREATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_UPDATE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_DELETE_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_SET_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    HANDOFF_RESET_HANDOFF_CONFIGS_FIELD_NUMBER: _ClassVar[int]
    VARIANT_CREATE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_UPDATE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_DELETE_ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    VARIANT_CREATE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_UPDATE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_DELETE_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_SET_DEFAULT_VARIANT_FIELD_NUMBER: _ClassVar[int]
    VARIANT_IMPORT_VARIANTS_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_CREATE_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    STOP_KEYWORDS_DELETE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_CONTENT_FILTER_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TTS_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_UPDATE_DEFAULT_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_ADD_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    LANGUAGES_DELETE_LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    EXPERIMENTAL_CONFIG_UPDATE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_CREATE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_UPDATE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_DELETE_PRONUNCIATION_FIELD_NUMBER: _ClassVar[int]
    PRONUNCIATIONS_REORDER_PRONUNCIATIONS_FIELD_NUMBER: _ClassVar[int]
    CREATE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    DELETE_TRANSCRIPT_CORRECTIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_GREETING_FIELD_NUMBER: _ClassVar[int]
    UPDATE_PERSONALITY_FIELD_NUMBER: _ClassVar[int]
    UPDATE_ROLE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_DISCLAIMER_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_RULES_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LANGUAGE_BEHAVIOR_FIELD_NUMBER: _ClassVar[int]
    CREATE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_START_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CREATE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_END_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    VOICE_ADD_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_DELETE_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_AGENT_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_CREATE_AGENT_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_AGENT_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_DISCLAIMER_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_CREATE_DISCLAIMER_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_UPDATE_DISCLAIMER_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_ADD_FAVORITE_VOICE_FIELD_NUMBER: _ClassVar[int]
    VOICE_REMOVE_FAVORITE_VOICE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_CREATE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ENTITY_DELETE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_CREATE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_UPDATE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_DELETE_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_POSITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_POSITIONS_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_DTMF_CONFIG_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_STEP_ASR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_TRANSITION_FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DELETE_FLOW_FIELD_NUMBER: _ClassVar[int]
    CREATE_FLOW_FIELD_NUMBER: _ClassVar[int]
    IMPORT_FLOW_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_FIELD_NUMBER: _ClassVar[int]
    UPDATE_FLOW_TRANSITION_FUNCTION_LATENCY_CONTROL_FIELD_NUMBER: _ClassVar[int]
    CREATE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_NO_CODE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_STEP_POSITION_FIELD_NUMBER: _ClassVar[int]
    CREATE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    DELETE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_POSITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_NO_CODE_CONDITION_EXIT_FLOW_POSITION_FIELD_NUMBER: _ClassVar[int]
    MOVE_FLOW_COMPONENT_FIELD_NUMBER: _ClassVar[int]
    MOVE_FLOW_COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    CREATE_STEP_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_FIELD_NUMBER: _ClassVar[int]
    DELETE_STEP_FIELD_NUMBER: _ClassVar[int]
    CREATE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    DELETE_STEP_CONDITION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_STEP_CONDITION_POSITION_FIELD_NUMBER: _ClassVar[int]
    CREATE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    UPDATE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    DELETE_KEYPHRASE_BOOSTING_FIELD_NUMBER: _ClassVar[int]
    CREATE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_API_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CREATE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_API_INTEGRATION_OPERATION_FIELD_NUMBER: _ClassVar[int]
    CREATE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    DELETE_TRANSLATION_FIELD_NUMBER: _ClassVar[int]
    VOICE_CHANNEL_UPDATE_ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    VOICE_CHANNEL_UPDATE_DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_GREETING_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_UPDATE_STATUS_FIELD_NUMBER: _ClassVar[int]
    CSAT_UPDATE_CONFIG_FIELD_NUMBER: _ClassVar[int]
    CONNECT_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    ENABLE_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    DISABLE_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    UPDATE_INTEGRATION_FUNCTIONS_FIELD_NUMBER: _ClassVar[int]
    DISCONNECT_INTEGRATION_FIELD_NUMBER: _ClassVar[int]
    type: str
    metadata: Metadata
    command_id: str
    create_topic: _knowledge_base_pb2.KnowledgeBase_CreateTopic
    update_topic: _knowledge_base_pb2.KnowledgeBase_UpdateTopic
    delete_topic: _knowledge_base_pb2.KnowledgeBase_DeleteTopic
    import_topics: _knowledge_base_pb2.KnowledgeBase_ImportTopics
    toggle_topic_status: _knowledge_base_pb2.KnowledgeBase_ToggleTopicStatus
    sms_create_template: _sms_pb2.SMS_CreateTemplate
    sms_update_template: _sms_pb2.SMS_UpdateTemplate
    sms_delete_template: _sms_pb2.SMS_DeleteTemplate
    handoff_create: _handoff_pb2.Handoff_Create
    handoff_update: _handoff_pb2.Handoff_Update
    handoff_delete: _handoff_pb2.Handoff_Delete
    handoff_set_default: _handoff_pb2.Handoff_SetDefault
    handoff_reset_handoff_configs: _handoff_pb2.Handoff_ResetHandoffConfigs
    variant_create_attribute: _variant_pb2.Variant_CreateAttribute
    variant_update_attribute: _variant_pb2.Variant_UpdateAttribute
    variant_delete_attribute: _variant_pb2.Variant_DeleteAttribute
    variant_create_variant: _variant_pb2.Variant_CreateVariant
    variant_update_variant: _variant_pb2.Variant_UpdateVariant
    variant_delete_variant: _variant_pb2.Variant_DeleteVariant
    variant_set_default_variant: _variant_pb2.Variant_SetDefaultVariant
    variant_import_variants: _variant_pb2.Variant_ImportVariants
    stop_keywords_create: _stop_keywords_pb2.StopKeyword_Create
    stop_keywords_update: _stop_keywords_pb2.StopKeyword_Update
    stop_keywords_delete: _stop_keywords_pb2.StopKeyword_Delete
    update_llm_settings: _llm_settings_pb2.LLMSettings_UpdateLLMSettings
    update_content_filter_settings: _content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings
    update_asr_settings: _asr_settings_pb2.ASRSettings_UpdateASRSettings
    update_tts_settings: _languages_pb2.Languages_UpdateDefaultLanguage
    languages_update_default_language: _languages_pb2.Languages_UpdateDefaultLanguage
    languages_add_language: _languages_pb2.Languages_AddLanguage
    languages_delete_language: _languages_pb2.Languages_DeleteLanguage
    experimental_config_update_config: _experimental_config_pb2.ExperimentalConfig_UpdateConfig
    pronunciations_create_pronunciation: _pronunciations_pb2.Pronunciations_CreatePronunciation
    pronunciations_update_pronunciation: _pronunciations_pb2.Pronunciations_UpdatePronunciation
    pronunciations_delete_pronunciation: _pronunciations_pb2.Pronunciations_DeletePronunciation
    pronunciations_reorder_pronunciations: _pronunciations_pb2.Pronunciations_ReorderPronunciations
    create_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_CreateTranscriptCorrections
    update_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_UpdateTranscriptCorrections
    delete_transcript_corrections: _transcript_corrections_pb2.TranscriptCorrections_DeleteTranscriptCorrections
    update_greeting: _agent_settings_pb2.Greeting_UpdateGreeting
    update_personality: _agent_settings_pb2.Personality_UpdatePersonality
    update_role: _agent_settings_pb2.Role_UpdateRole
    update_disclaimer_message: _agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage
    update_rules: _agent_settings_pb2.Rules_UpdateRules
    update_language_behavior: _agent_settings_pb2.LanguageBehavior_UpdateLanguageBehavior
    create_function: _functions_pb2.Function_CreateFunction
    update_function: _functions_pb2.Function_UpdateFunction
    delete_function: _functions_pb2.Function_DeleteFunction
    update_latency_control: _functions_pb2.Function_UpdateLatencyControl
    create_start_function: _start_function_pb2.StartFunction_Create
    update_start_function: _start_function_pb2.StartFunction_Update
    delete_start_function: _start_function_pb2.StartFunction_Delete
    create_end_function: _end_function_pb2.EndFunction_Create
    update_end_function: _end_function_pb2.EndFunction_Update
    delete_end_function: _end_function_pb2.EndFunction_Delete
    voice_add_agent_voice: _voice_pb2.Voice_AddAgentVoice
    voice_delete_agent_voice: _voice_pb2.Voice_DeleteAgentVoice
    voice_update_agent_voice: _voice_pb2.Voice_UpdateAgentVoice
    voice_create_agent_voice_settings: _voice_pb2.Voice_CreateAgentVoiceSettings
    voice_update_agent_voice_settings: _voice_pb2.Voice_UpdateAgentVoiceSettings
    voice_update_disclaimer_voice: _voice_pb2.Voice_UpdateDisclaimerVoice
    voice_create_disclaimer_voice_settings: _voice_pb2.Voice_CreateDisclaimerVoiceSettings
    voice_update_disclaimer_voice_settings: _voice_pb2.Voice_UpdateDisclaimerVoiceSettings
    voice_add_favorite_voice: _voice_pb2.Voice_AddFavoriteVoice
    voice_remove_favorite_voice: _voice_pb2.Voice_RemoveFavoriteVoice
    entity_create: _entities_pb2.Entity_Create
    entity_update: _entities_pb2.Entity_Update
    entity_delete: _entities_pb2.Entity_Delete
    variable_create: _variables_pb2.Variable_Create
    variable_update: _variables_pb2.Variable_Update
    variable_delete: _variables_pb2.Variable_Delete
    create_flow_step: _flows_pb2.Flow_CreateStep
    update_flow_step: _flows_pb2.Flow_UpdateStep
    delete_flow_step: _flows_pb2.Flow_DeleteStep
    update_flow_step_position: _flows_pb2.Flow_UpdateStepPosition
    update_flow_step_positions: _flows_pb2.Flow_UpdateStepPositions
    update_flow_step_dtmf_config: _flows_pb2.Flow_UpdateStepDtmfConfig
    update_flow_step_asr_config: _flows_pb2.Flow_UpdateStepAsrConfig
    create_flow_transition_function: _flows_pb2.Flow_CreateTransitionFunction
    update_flow_transition_function: _flows_pb2.Flow_UpdateTransitionFunction
    delete_flow_transition_function: _flows_pb2.Flow_DeleteTransitionFunction
    delete_flow: _flows_pb2.Flow_DeleteFlow
    create_flow: _flows_pb2.Flow_CreateFlow
    import_flow: _flows_pb2.Flow_ImportFlow
    update_flow: _flows_pb2.Flow_UpdateFlow
    update_flow_transition_function_latency_control: _flows_pb2.Flow_UpdateTransitionFunctionLatencyControl
    create_no_code_step: _flows_pb2.CreateNoCodeStep
    update_no_code_step: _flows_pb2.UpdateNoCodeStep
    delete_no_code_step: _flows_pb2.DeleteNoCodeStep
    update_no_code_step_position: _flows_pb2.UpdateNoCodeStepPosition
    create_no_code_condition: _flows_pb2.CreateNoCodeCondition
    delete_no_code_condition: _flows_pb2.DeleteNoCodeCondition
    update_no_code_condition: _flows_pb2.UpdateNoCodeCondition
    update_no_code_condition_position: _flows_pb2.UpdateNoCodeConditionPosition
    update_no_code_condition_exit_flow_position: _flows_pb2.UpdateNoCodeConditionExitFlowPosition
    move_flow_component: _flows_pb2.MoveFlowComponent
    move_flow_components: _flows_pb2.MoveFlowComponents
    create_step: _flows_pb2.CreateStep
    update_step: _flows_pb2.UpdateStep
    delete_step: _flows_pb2.DeleteStep
    create_step_condition: _flows_pb2.CreateStepCondition
    update_step_condition: _flows_pb2.UpdateStepCondition
    delete_step_condition: _flows_pb2.DeleteStepCondition
    update_step_condition_position: _flows_pb2.UpdateStepConditionPosition
    create_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_CreateKeyphrase
    update_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_UpdateKeyphrase
    delete_keyphrase_boosting: _keyphrase_boosting_pb2.KeyphraseBoosting_DeleteKeyphrase
    create_api_integration: _api_integrations_pb2.ApiIntegration_Create
    update_api_integration: _api_integrations_pb2.ApiIntegration_Update
    delete_api_integration: _api_integrations_pb2.ApiIntegration_Delete
    update_api_integration_config: _api_integrations_pb2.ApiIntegrationConfig_Update
    create_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Create
    update_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Update
    delete_api_integration_operation: _api_integrations_pb2.ApiIntegrationOperation_Delete
    create_translation: _translations_pb2.LanguageHubTranslations_Create
    update_translation: _translations_pb2.LanguageHubTranslations_Update
    delete_translation: _translations_pb2.LanguageHubTranslations_Delete
    voice_channel_update_asr_settings: _channels_pb2.VoiceChannel_UpdateASRSettings
    voice_channel_update_disclaimer: _channels_pb2.VoiceChannel_UpdateDisclaimer
    channel_update_greeting: _channels_pb2.Channel_UpdateGreeting
    channel_update_style_prompt: _channels_pb2.Channel_UpdateStylePrompt
    channel_update_safety_filters: _channels_pb2.Channel_UpdateSafetyFilters
    channel_update_llm_settings: _channels_pb2.Channel_UpdateLLMSettings
    channel_update_status: _channels_pb2.Channel_UpdateStatus
    csat_update_config: _csat_pb2.CSAT_UpdateConfig
    connect_integration: _integrations_pb2.Integration_Connect
    enable_integration: _integrations_pb2.Integration_Enable
    disable_integration: _integrations_pb2.Integration_Disable
    update_integration_functions: _integrations_pb2.Integration_UpdateFunctions
    disconnect_integration: _integrations_pb2.Integration_Disconnect
    def __init__(self, type: _Optional[str] = ..., metadata: _Optional[_Union[Metadata, _Mapping]] = ..., command_id: _Optional[str] = ..., create_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_CreateTopic, _Mapping]] = ..., update_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_UpdateTopic, _Mapping]] = ..., delete_topic: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_DeleteTopic, _Mapping]] = ..., import_topics: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_ImportTopics, _Mapping]] = ..., toggle_topic_status: _Optional[_Union[_knowledge_base_pb2.KnowledgeBase_ToggleTopicStatus, _Mapping]] = ..., sms_create_template: _Optional[_Union[_sms_pb2.SMS_CreateTemplate, _Mapping]] = ..., sms_update_template: _Optional[_Union[_sms_pb2.SMS_UpdateTemplate, _Mapping]] = ..., sms_delete_template: _Optional[_Union[_sms_pb2.SMS_DeleteTemplate, _Mapping]] = ..., handoff_create: _Optional[_Union[_handoff_pb2.Handoff_Create, _Mapping]] = ..., handoff_update: _Optional[_Union[_handoff_pb2.Handoff_Update, _Mapping]] = ..., handoff_delete: _Optional[_Union[_handoff_pb2.Handoff_Delete, _Mapping]] = ..., handoff_set_default: _Optional[_Union[_handoff_pb2.Handoff_SetDefault, _Mapping]] = ..., handoff_reset_handoff_configs: _Optional[_Union[_handoff_pb2.Handoff_ResetHandoffConfigs, _Mapping]] = ..., variant_create_attribute: _Optional[_Union[_variant_pb2.Variant_CreateAttribute, _Mapping]] = ..., variant_update_attribute: _Optional[_Union[_variant_pb2.Variant_UpdateAttribute, _Mapping]] = ..., variant_delete_attribute: _Optional[_Union[_variant_pb2.Variant_DeleteAttribute, _Mapping]] = ..., variant_create_variant: _Optional[_Union[_variant_pb2.Variant_CreateVariant, _Mapping]] = ..., variant_update_variant: _Optional[_Union[_variant_pb2.Variant_UpdateVariant, _Mapping]] = ..., variant_delete_variant: _Optional[_Union[_variant_pb2.Variant_DeleteVariant, _Mapping]] = ..., variant_set_default_variant: _Optional[_Union[_variant_pb2.Variant_SetDefaultVariant, _Mapping]] = ..., variant_import_variants: _Optional[_Union[_variant_pb2.Variant_ImportVariants, _Mapping]] = ..., stop_keywords_create: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Create, _Mapping]] = ..., stop_keywords_update: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Update, _Mapping]] = ..., stop_keywords_delete: _Optional[_Union[_stop_keywords_pb2.StopKeyword_Delete, _Mapping]] = ..., update_llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings_UpdateLLMSettings, _Mapping]] = ..., update_content_filter_settings: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings, _Mapping]] = ..., update_asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings_UpdateASRSettings, _Mapping]] = ..., update_tts_settings: _Optional[_Union[_languages_pb2.Languages_UpdateDefaultLanguage, _Mapping]] = ..., languages_update_default_language: _Optional[_Union[_languages_pb2.Languages_UpdateDefaultLanguage, _Mapping]] = ..., languages_add_language: _Optional[_Union[_languages_pb2.Languages_AddLanguage, _Mapping]] = ..., languages_delete_language: _Optional[_Union[_languages_pb2.Languages_DeleteLanguage, _Mapping]] = ..., experimental_config_update_config: _Optional[_Union[_experimental_config_pb2.ExperimentalConfig_UpdateConfig, _Mapping]] = ..., pronunciations_create_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_CreatePronunciation, _Mapping]] = ..., pronunciations_update_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_UpdatePronunciation, _Mapping]] = ..., pronunciations_delete_pronunciation: _Optional[_Union[_pronunciations_pb2.Pronunciations_DeletePronunciation, _Mapping]] = ..., pronunciations_reorder_pronunciations: _Optional[_Union[_pronunciations_pb2.Pronunciations_ReorderPronunciations, _Mapping]] = ..., create_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_CreateTranscriptCorrections, _Mapping]] = ..., update_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_UpdateTranscriptCorrections, _Mapping]] = ..., delete_transcript_corrections: _Optional[_Union[_transcript_corrections_pb2.TranscriptCorrections_DeleteTranscriptCorrections, _Mapping]] = ..., update_greeting: _Optional[_Union[_agent_settings_pb2.Greeting_UpdateGreeting, _Mapping]] = ..., update_personality: _Optional[_Union[_agent_settings_pb2.Personality_UpdatePersonality, _Mapping]] = ..., update_role: _Optional[_Union[_agent_settings_pb2.Role_UpdateRole, _Mapping]] = ..., update_disclaimer_message: _Optional[_Union[_agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage, _Mapping]] = ..., update_rules: _Optional[_Union[_agent_settings_pb2.Rules_UpdateRules, _Mapping]] = ..., update_language_behavior: _Optional[_Union[_agent_settings_pb2.LanguageBehavior_UpdateLanguageBehavior, _Mapping]] = ..., create_function: _Optional[_Union[_functions_pb2.Function_CreateFunction, _Mapping]] = ..., update_function: _Optional[_Union[_functions_pb2.Function_UpdateFunction, _Mapping]] = ..., delete_function: _Optional[_Union[_functions_pb2.Function_DeleteFunction, _Mapping]] = ..., update_latency_control: _Optional[_Union[_functions_pb2.Function_UpdateLatencyControl, _Mapping]] = ..., create_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Create, _Mapping]] = ..., update_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Update, _Mapping]] = ..., delete_start_function: _Optional[_Union[_start_function_pb2.StartFunction_Delete, _Mapping]] = ..., create_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Create, _Mapping]] = ..., update_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Update, _Mapping]] = ..., delete_end_function: _Optional[_Union[_end_function_pb2.EndFunction_Delete, _Mapping]] = ..., voice_add_agent_voice: _Optional[_Union[_voice_pb2.Voice_AddAgentVoice, _Mapping]] = ..., voice_delete_agent_voice: _Optional[_Union[_voice_pb2.Voice_DeleteAgentVoice, _Mapping]] = ..., voice_update_agent_voice: _Optional[_Union[_voice_pb2.Voice_UpdateAgentVoice, _Mapping]] = ..., voice_create_agent_voice_settings: _Optional[_Union[_voice_pb2.Voice_CreateAgentVoiceSettings, _Mapping]] = ..., voice_update_agent_voice_settings: _Optional[_Union[_voice_pb2.Voice_UpdateAgentVoiceSettings, _Mapping]] = ..., voice_update_disclaimer_voice: _Optional[_Union[_voice_pb2.Voice_UpdateDisclaimerVoice, _Mapping]] = ..., voice_create_disclaimer_voice_settings: _Optional[_Union[_voice_pb2.Voice_CreateDisclaimerVoiceSettings, _Mapping]] = ..., voice_update_disclaimer_voice_settings: _Optional[_Union[_voice_pb2.Voice_UpdateDisclaimerVoiceSettings, _Mapping]] = ..., voice_add_favorite_voice: _Optional[_Union[_voice_pb2.Voice_AddFavoriteVoice, _Mapping]] = ..., voice_remove_favorite_voice: _Optional[_Union[_voice_pb2.Voice_RemoveFavoriteVoice, _Mapping]] = ..., entity_create: _Optional[_Union[_entities_pb2.Entity_Create, _Mapping]] = ..., entity_update: _Optional[_Union[_entities_pb2.Entity_Update, _Mapping]] = ..., entity_delete: _Optional[_Union[_entities_pb2.Entity_Delete, _Mapping]] = ..., variable_create: _Optional[_Union[_variables_pb2.Variable_Create, _Mapping]] = ..., variable_update: _Optional[_Union[_variables_pb2.Variable_Update, _Mapping]] = ..., variable_delete: _Optional[_Union[_variables_pb2.Variable_Delete, _Mapping]] = ..., create_flow_step: _Optional[_Union[_flows_pb2.Flow_CreateStep, _Mapping]] = ..., update_flow_step: _Optional[_Union[_flows_pb2.Flow_UpdateStep, _Mapping]] = ..., delete_flow_step: _Optional[_Union[_flows_pb2.Flow_DeleteStep, _Mapping]] = ..., update_flow_step_position: _Optional[_Union[_flows_pb2.Flow_UpdateStepPosition, _Mapping]] = ..., update_flow_step_positions: _Optional[_Union[_flows_pb2.Flow_UpdateStepPositions, _Mapping]] = ..., update_flow_step_dtmf_config: _Optional[_Union[_flows_pb2.Flow_UpdateStepDtmfConfig, _Mapping]] = ..., update_flow_step_asr_config: _Optional[_Union[_flows_pb2.Flow_UpdateStepAsrConfig, _Mapping]] = ..., create_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_CreateTransitionFunction, _Mapping]] = ..., update_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_UpdateTransitionFunction, _Mapping]] = ..., delete_flow_transition_function: _Optional[_Union[_flows_pb2.Flow_DeleteTransitionFunction, _Mapping]] = ..., delete_flow: _Optional[_Union[_flows_pb2.Flow_DeleteFlow, _Mapping]] = ..., create_flow: _Optional[_Union[_flows_pb2.Flow_CreateFlow, _Mapping]] = ..., import_flow: _Optional[_Union[_flows_pb2.Flow_ImportFlow, _Mapping]] = ..., update_flow: _Optional[_Union[_flows_pb2.Flow_UpdateFlow, _Mapping]] = ..., update_flow_transition_function_latency_control: _Optional[_Union[_flows_pb2.Flow_UpdateTransitionFunctionLatencyControl, _Mapping]] = ..., create_no_code_step: _Optional[_Union[_flows_pb2.CreateNoCodeStep, _Mapping]] = ..., update_no_code_step: _Optional[_Union[_flows_pb2.UpdateNoCodeStep, _Mapping]] = ..., delete_no_code_step: _Optional[_Union[_flows_pb2.DeleteNoCodeStep, _Mapping]] = ..., update_no_code_step_position: _Optional[_Union[_flows_pb2.UpdateNoCodeStepPosition, _Mapping]] = ..., create_no_code_condition: _Optional[_Union[_flows_pb2.CreateNoCodeCondition, _Mapping]] = ..., delete_no_code_condition: _Optional[_Union[_flows_pb2.DeleteNoCodeCondition, _Mapping]] = ..., update_no_code_condition: _Optional[_Union[_flows_pb2.UpdateNoCodeCondition, _Mapping]] = ..., update_no_code_condition_position: _Optional[_Union[_flows_pb2.UpdateNoCodeConditionPosition, _Mapping]] = ..., update_no_code_condition_exit_flow_position: _Optional[_Union[_flows_pb2.UpdateNoCodeConditionExitFlowPosition, _Mapping]] = ..., move_flow_component: _Optional[_Union[_flows_pb2.MoveFlowComponent, _Mapping]] = ..., move_flow_components: _Optional[_Union[_flows_pb2.MoveFlowComponents, _Mapping]] = ..., create_step: _Optional[_Union[_flows_pb2.CreateStep, _Mapping]] = ..., update_step: _Optional[_Union[_flows_pb2.UpdateStep, _Mapping]] = ..., delete_step: _Optional[_Union[_flows_pb2.DeleteStep, _Mapping]] = ..., create_step_condition: _Optional[_Union[_flows_pb2.CreateStepCondition, _Mapping]] = ..., update_step_condition: _Optional[_Union[_flows_pb2.UpdateStepCondition, _Mapping]] = ..., delete_step_condition: _Optional[_Union[_flows_pb2.DeleteStepCondition, _Mapping]] = ..., update_step_condition_position: _Optional[_Union[_flows_pb2.UpdateStepConditionPosition, _Mapping]] = ..., create_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_CreateKeyphrase, _Mapping]] = ..., update_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_UpdateKeyphrase, _Mapping]] = ..., delete_keyphrase_boosting: _Optional[_Union[_keyphrase_boosting_pb2.KeyphraseBoosting_DeleteKeyphrase, _Mapping]] = ..., create_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Create, _Mapping]] = ..., update_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Update, _Mapping]] = ..., delete_api_integration: _Optional[_Union[_api_integrations_pb2.ApiIntegration_Delete, _Mapping]] = ..., update_api_integration_config: _Optional[_Union[_api_integrations_pb2.ApiIntegrationConfig_Update, _Mapping]] = ..., create_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Create, _Mapping]] = ..., update_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Update, _Mapping]] = ..., delete_api_integration_operation: _Optional[_Union[_api_integrations_pb2.ApiIntegrationOperation_Delete, _Mapping]] = ..., create_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Create, _Mapping]] = ..., update_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Update, _Mapping]] = ..., delete_translation: _Optional[_Union[_translations_pb2.LanguageHubTranslations_Delete, _Mapping]] = ..., voice_channel_update_asr_settings: _Optional[_Union[_channels_pb2.VoiceChannel_UpdateASRSettings, _Mapping]] = ..., voice_channel_update_disclaimer: _Optional[_Union[_channels_pb2.VoiceChannel_UpdateDisclaimer, _Mapping]] = ..., channel_update_greeting: _Optional[_Union[_channels_pb2.Channel_UpdateGreeting, _Mapping]] = ..., channel_update_style_prompt: _Optional[_Union[_channels_pb2.Channel_UpdateStylePrompt, _Mapping]] = ..., channel_update_safety_filters: _Optional[_Union[_channels_pb2.Channel_UpdateSafetyFilters, _Mapping]] = ..., channel_update_llm_settings: _Optional[_Union[_channels_pb2.Channel_UpdateLLMSettings, _Mapping]] = ..., channel_update_status: _Optional[_Union[_channels_pb2.Channel_UpdateStatus, _Mapping]] = ..., csat_update_config: _Optional[_Union[_csat_pb2.CSAT_UpdateConfig, _Mapping]] = ..., connect_integration: _Optional[_Union[_integrations_pb2.Integration_Connect, _Mapping]] = ..., enable_integration: _Optional[_Union[_integrations_pb2.Integration_Enable, _Mapping]] = ..., disable_integration: _Optional[_Union[_integrations_pb2.Integration_Disable, _Mapping]] = ..., update_integration_functions: _Optional[_Union[_integrations_pb2.Integration_UpdateFunctions, _Mapping]] = ..., disconnect_integration: _Optional[_Union[_integrations_pb2.Integration_Disconnect, _Mapping]] = ...) -> None: ...

class CommandBatch(_message.Message):
    __slots__ = ("last_known_sequence", "commands")
    LAST_KNOWN_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    COMMANDS_FIELD_NUMBER: _ClassVar[int]
    last_known_sequence: int
    commands: _containers.RepeatedCompositeFieldContainer[Command]
    def __init__(self, last_known_sequence: _Optional[int] = ..., commands: _Optional[_Iterable[_Union[Command, _Mapping]]] = ...) -> None: ...

class Branch_Created(_message.Message):
    __slots__ = ("id", "created_at", "created_by", "snapshot_key")
    ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    id: str
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    snapshot_key: str
    def __init__(self, id: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., snapshot_key: _Optional[str] = ...) -> None: ...

class Branch_TriggerMerge(_message.Message):
    __slots__ = ("branch_id", "user_timestamp", "triggered_by")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    USER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    TRIGGERED_BY_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    user_timestamp: _timestamp_pb2.Timestamp
    triggered_by: str
    def __init__(self, branch_id: _Optional[str] = ..., user_timestamp: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., triggered_by: _Optional[str] = ...) -> None: ...

class ConflictResolution(_message.Message):
    __slots__ = ("path", "strategy", "value")
    PATH_FIELD_NUMBER: _ClassVar[int]
    STRATEGY_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    path: _containers.RepeatedScalarFieldContainer[str]
    strategy: ResolutionStrategy
    value: _struct_pb2.Struct
    def __init__(self, path: _Optional[_Iterable[str]] = ..., strategy: _Optional[_Union[ResolutionStrategy, str]] = ..., value: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...) -> None: ...

class Branch_Merged(_message.Message):
    __slots__ = ("branch_id", "merged_at", "merged_by", "main_sequence", "snapshot_key", "resolutions")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    MERGED_AT_FIELD_NUMBER: _ClassVar[int]
    MERGED_BY_FIELD_NUMBER: _ClassVar[int]
    MAIN_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    RESOLUTIONS_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    merged_at: _timestamp_pb2.Timestamp
    merged_by: str
    main_sequence: int
    snapshot_key: str
    resolutions: _containers.RepeatedCompositeFieldContainer[ConflictResolution]
    def __init__(self, branch_id: _Optional[str] = ..., merged_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., merged_by: _Optional[str] = ..., main_sequence: _Optional[int] = ..., snapshot_key: _Optional[str] = ..., resolutions: _Optional[_Iterable[_Union[ConflictResolution, _Mapping]]] = ...) -> None: ...

class Branch_Deleted(_message.Message):
    __slots__ = ("branch_id", "deleted_at", "deleted_by")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    DELETED_AT_FIELD_NUMBER: _ClassVar[int]
    DELETED_BY_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    deleted_at: _timestamp_pb2.Timestamp
    deleted_by: str
    def __init__(self, branch_id: _Optional[str] = ..., deleted_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., deleted_by: _Optional[str] = ...) -> None: ...

class Project_Created(_message.Message):
    __slots__ = ("created_at", "created_by", "name", "snapshot_key")
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    created_at: _timestamp_pb2.Timestamp
    created_by: str
    name: str
    snapshot_key: str
    def __init__(self, created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., created_by: _Optional[str] = ..., name: _Optional[str] = ..., snapshot_key: _Optional[str] = ...) -> None: ...

class Project_LoadedFromJupiter(_message.Message):
    __slots__ = ("loaded_at", "artifact_version", "rag_kb_version", "snapshot_key")
    LOADED_AT_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    RAG_KB_VERSION_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    loaded_at: _timestamp_pb2.Timestamp
    artifact_version: str
    rag_kb_version: str
    snapshot_key: str
    def __init__(self, loaded_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., artifact_version: _Optional[str] = ..., rag_kb_version: _Optional[str] = ..., snapshot_key: _Optional[str] = ...) -> None: ...

class DeploymentCompleted(_message.Message):
    __slots__ = ("branch_id", "client_env", "snapshot_key", "artifact_version", "rag_kb_version", "function_deployment_version", "lambda_deployment_version", "version_hash")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_ENV_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    RAG_KB_VERSION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_DEPLOYMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    LAMBDA_DEPLOYMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    VERSION_HASH_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    client_env: str
    snapshot_key: str
    artifact_version: str
    rag_kb_version: str
    function_deployment_version: str
    lambda_deployment_version: str
    version_hash: str
    def __init__(self, branch_id: _Optional[str] = ..., client_env: _Optional[str] = ..., snapshot_key: _Optional[str] = ..., artifact_version: _Optional[str] = ..., rag_kb_version: _Optional[str] = ..., function_deployment_version: _Optional[str] = ..., lambda_deployment_version: _Optional[str] = ..., version_hash: _Optional[str] = ...) -> None: ...

class DeploymentRollback(_message.Message):
    __slots__ = ("branch_id", "snapshot_key", "artifact_version", "rag_kb_version", "function_deployment_version", "version_hash")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_VERSION_FIELD_NUMBER: _ClassVar[int]
    RAG_KB_VERSION_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_DEPLOYMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    VERSION_HASH_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    snapshot_key: str
    artifact_version: str
    rag_kb_version: str
    function_deployment_version: str
    version_hash: str
    def __init__(self, branch_id: _Optional[str] = ..., snapshot_key: _Optional[str] = ..., artifact_version: _Optional[str] = ..., rag_kb_version: _Optional[str] = ..., function_deployment_version: _Optional[str] = ..., version_hash: _Optional[str] = ...) -> None: ...

class LoadedFromBundle(_message.Message):
    __slots__ = ("snapshot_key",)
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    snapshot_key: str
    def __init__(self, snapshot_key: _Optional[str] = ...) -> None: ...

class FunctionDeploymentCompleted(_message.Message):
    __slots__ = ("branch_id", "snapshot_key", "function_deployment_id", "lambda_deployment_version")
    BRANCH_ID_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_KEY_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_DEPLOYMENT_ID_FIELD_NUMBER: _ClassVar[int]
    LAMBDA_DEPLOYMENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    branch_id: str
    snapshot_key: str
    function_deployment_id: str
    lambda_deployment_version: str
    def __init__(self, branch_id: _Optional[str] = ..., snapshot_key: _Optional[str] = ..., function_deployment_id: _Optional[str] = ..., lambda_deployment_version: _Optional[str] = ...) -> None: ...
