from google.protobuf import timestamp_pb2 as _timestamp_pb2
from poly.handlers.protobuf import llm_settings_pb2 as _llm_settings_pb2
from poly.handlers.protobuf import content_filter_settings_pb2 as _content_filter_settings_pb2
from poly.handlers.protobuf import asr_settings_pb2 as _asr_settings_pb2
from poly.handlers.protobuf import agent_settings_pb2 as _agent_settings_pb2
from poly.handlers.protobuf import asr_pb2 as _asr_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ChannelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VOICE: _ClassVar[ChannelType]
    WEB_CHAT: _ClassVar[ChannelType]
    SMS: _ClassVar[ChannelType]

class ChannelStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_CREATED: _ClassVar[ChannelStatus]
    CREATED: _ClassVar[ChannelStatus]
VOICE: ChannelType
WEB_CHAT: ChannelType
SMS: ChannelType
NOT_CREATED: ChannelStatus
CREATED: ChannelStatus

class StylePrompt(_message.Message):
    __slots__ = ("prompt", "created_at", "created_by", "updated_at", "updated_by")
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    prompt: str
    created_at: str
    created_by: str
    updated_at: _timestamp_pb2.Timestamp
    updated_by: str
    def __init__(self, prompt: _Optional[str] = ..., created_at: _Optional[str] = ..., created_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ...) -> None: ...

class StylePrompt_UpdateStylePrompt(_message.Message):
    __slots__ = ("prompt",)
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    prompt: str
    def __init__(self, prompt: _Optional[str] = ...) -> None: ...

class ChannelConfig(_message.Message):
    __slots__ = ("llm_settings", "style_prompt", "greeting", "safety_filters", "temperature")
    LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    GREETING_FIELD_NUMBER: _ClassVar[int]
    SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    llm_settings: _llm_settings_pb2.LLMSettings
    style_prompt: StylePrompt
    greeting: _agent_settings_pb2.Greeting
    safety_filters: _content_filter_settings_pb2.ContentFilterSettings
    temperature: float
    def __init__(self, llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings, _Mapping]] = ..., style_prompt: _Optional[_Union[StylePrompt, _Mapping]] = ..., greeting: _Optional[_Union[_agent_settings_pb2.Greeting, _Mapping]] = ..., safety_filters: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings, _Mapping]] = ..., temperature: _Optional[float] = ...) -> None: ...

class VADConfig(_message.Message):
    __slots__ = ("speech_end_window_seconds",)
    SPEECH_END_WINDOW_SECONDS_FIELD_NUMBER: _ClassVar[int]
    speech_end_window_seconds: float
    def __init__(self, speech_end_window_seconds: _Optional[float] = ...) -> None: ...

class BargeInConfig(_message.Message):
    __slots__ = ("enabled", "allowed_first_turn", "max_per_call", "min_speech_duration_seconds")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_FIRST_TURN_FIELD_NUMBER: _ClassVar[int]
    MAX_PER_CALL_FIELD_NUMBER: _ClassVar[int]
    MIN_SPEECH_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    allowed_first_turn: bool
    max_per_call: int
    min_speech_duration_seconds: float
    def __init__(self, enabled: bool = ..., allowed_first_turn: bool = ..., max_per_call: _Optional[int] = ..., min_speech_duration_seconds: _Optional[float] = ...) -> None: ...

class FillerUtterances(_message.Message):
    __slots__ = ("enabled", "utterances", "randomize", "initial_interval_seconds", "interval_seconds")
    class Utterance(_message.Message):
        __slots__ = ("message",)
        MESSAGE_FIELD_NUMBER: _ClassVar[int]
        message: str
        def __init__(self, message: _Optional[str] = ...) -> None: ...
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    UTTERANCES_FIELD_NUMBER: _ClassVar[int]
    RANDOMIZE_FIELD_NUMBER: _ClassVar[int]
    INITIAL_INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    utterances: _containers.RepeatedCompositeFieldContainer[FillerUtterances.Utterance]
    randomize: bool
    initial_interval_seconds: float
    interval_seconds: float
    def __init__(self, enabled: bool = ..., utterances: _Optional[_Iterable[_Union[FillerUtterances.Utterance, _Mapping]]] = ..., randomize: bool = ..., initial_interval_seconds: _Optional[float] = ..., interval_seconds: _Optional[float] = ...) -> None: ...

class AICousticsEnhancement(_message.Message):
    __slots__ = ("enabled", "model_quality_tier", "noise_reduction", "voice_gain", "noise_gate")
    class QualityTier(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        QUALITY_TIER_UNSPECIFIED: _ClassVar[AICousticsEnhancement.QualityTier]
        QUALITY_TIER_STANDARD: _ClassVar[AICousticsEnhancement.QualityTier]
        QUALITY_TIER_HIGH: _ClassVar[AICousticsEnhancement.QualityTier]
        QUALITY_TIER_FAST: _ClassVar[AICousticsEnhancement.QualityTier]
    QUALITY_TIER_UNSPECIFIED: AICousticsEnhancement.QualityTier
    QUALITY_TIER_STANDARD: AICousticsEnhancement.QualityTier
    QUALITY_TIER_HIGH: AICousticsEnhancement.QualityTier
    QUALITY_TIER_FAST: AICousticsEnhancement.QualityTier
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    MODEL_QUALITY_TIER_FIELD_NUMBER: _ClassVar[int]
    NOISE_REDUCTION_FIELD_NUMBER: _ClassVar[int]
    VOICE_GAIN_FIELD_NUMBER: _ClassVar[int]
    NOISE_GATE_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    model_quality_tier: AICousticsEnhancement.QualityTier
    noise_reduction: float
    voice_gain: float
    noise_gate: bool
    def __init__(self, enabled: bool = ..., model_quality_tier: _Optional[_Union[AICousticsEnhancement.QualityTier, str]] = ..., noise_reduction: _Optional[float] = ..., voice_gain: _Optional[float] = ..., noise_gate: bool = ...) -> None: ...

class AudioEnhancement(_message.Message):
    __slots__ = ("ai_coustics",)
    AI_COUSTICS_FIELD_NUMBER: _ClassVar[int]
    ai_coustics: AICousticsEnhancement
    def __init__(self, ai_coustics: _Optional[_Union[AICousticsEnhancement, _Mapping]] = ...) -> None: ...

class AmbienceSettings(_message.Message):
    __slots__ = ("enabled", "preset", "loudness")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    PRESET_FIELD_NUMBER: _ClassVar[int]
    LOUDNESS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    preset: str
    loudness: float
    def __init__(self, enabled: bool = ..., preset: _Optional[str] = ..., loudness: _Optional[float] = ...) -> None: ...

class VoiceChannel(_message.Message):
    __slots__ = ("config", "asr_settings", "disclaimer", "vad_config", "audio_enhancement", "silence_filler_utterances", "asr_config", "barge_in_config", "ambience")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    VAD_CONFIG_FIELD_NUMBER: _ClassVar[int]
    AUDIO_ENHANCEMENT_FIELD_NUMBER: _ClassVar[int]
    SILENCE_FILLER_UTTERANCES_FIELD_NUMBER: _ClassVar[int]
    ASR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    BARGE_IN_CONFIG_FIELD_NUMBER: _ClassVar[int]
    AMBIENCE_FIELD_NUMBER: _ClassVar[int]
    config: ChannelConfig
    asr_settings: _asr_settings_pb2.ASRSettings
    disclaimer: _agent_settings_pb2.DisclaimerMessage
    vad_config: VADConfig
    audio_enhancement: AudioEnhancement
    silence_filler_utterances: FillerUtterances
    asr_config: _asr_pb2.Asr
    barge_in_config: BargeInConfig
    ambience: AmbienceSettings
    def __init__(self, config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings, _Mapping]] = ..., disclaimer: _Optional[_Union[_agent_settings_pb2.DisclaimerMessage, _Mapping]] = ..., vad_config: _Optional[_Union[VADConfig, _Mapping]] = ..., audio_enhancement: _Optional[_Union[AudioEnhancement, _Mapping]] = ..., silence_filler_utterances: _Optional[_Union[FillerUtterances, _Mapping]] = ..., asr_config: _Optional[_Union[_asr_pb2.Asr, _Mapping]] = ..., barge_in_config: _Optional[_Union[BargeInConfig, _Mapping]] = ..., ambience: _Optional[_Union[AmbienceSettings, _Mapping]] = ...) -> None: ...

class WebChatChannel(_message.Message):
    __slots__ = ("config", "status")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    config: ChannelConfig
    status: ChannelStatus
    def __init__(self, config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., status: _Optional[_Union[ChannelStatus, str]] = ...) -> None: ...

class SmsComplianceKeyword(_message.Message):
    __slots__ = ("keyword", "action", "auto_reply")
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    AUTO_REPLY_FIELD_NUMBER: _ClassVar[int]
    keyword: str
    action: str
    auto_reply: str
    def __init__(self, keyword: _Optional[str] = ..., action: _Optional[str] = ..., auto_reply: _Optional[str] = ...) -> None: ...

class SmsBehaviorConfig(_message.Message):
    __slots__ = ("tones", "emoji_use", "sign_off", "opener", "date_format", "time_format")
    TONES_FIELD_NUMBER: _ClassVar[int]
    EMOJI_USE_FIELD_NUMBER: _ClassVar[int]
    SIGN_OFF_FIELD_NUMBER: _ClassVar[int]
    OPENER_FIELD_NUMBER: _ClassVar[int]
    DATE_FORMAT_FIELD_NUMBER: _ClassVar[int]
    TIME_FORMAT_FIELD_NUMBER: _ClassVar[int]
    tones: _containers.RepeatedScalarFieldContainer[str]
    emoji_use: str
    sign_off: str
    opener: str
    date_format: str
    time_format: str
    def __init__(self, tones: _Optional[_Iterable[str]] = ..., emoji_use: _Optional[str] = ..., sign_off: _Optional[str] = ..., opener: _Optional[str] = ..., date_format: _Optional[str] = ..., time_format: _Optional[str] = ...) -> None: ...

class SmsChannel(_message.Message):
    __slots__ = ("config", "status", "sender_phone_number", "channel_behavior_mode", "behavior_config", "ending_message", "error_fallback_message", "compliance_keywords")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SENDER_PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_BEHAVIOR_MODE_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    ENDING_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FALLBACK_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMPLIANCE_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    config: ChannelConfig
    status: ChannelStatus
    sender_phone_number: str
    channel_behavior_mode: str
    behavior_config: SmsBehaviorConfig
    ending_message: str
    error_fallback_message: str
    compliance_keywords: _containers.RepeatedCompositeFieldContainer[SmsComplianceKeyword]
    def __init__(self, config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., status: _Optional[_Union[ChannelStatus, str]] = ..., sender_phone_number: _Optional[str] = ..., channel_behavior_mode: _Optional[str] = ..., behavior_config: _Optional[_Union[SmsBehaviorConfig, _Mapping]] = ..., ending_message: _Optional[str] = ..., error_fallback_message: _Optional[str] = ..., compliance_keywords: _Optional[_Iterable[_Union[SmsComplianceKeyword, _Mapping]]] = ...) -> None: ...

class Channels(_message.Message):
    __slots__ = ("voice", "web_chat", "sms")
    VOICE_FIELD_NUMBER: _ClassVar[int]
    WEB_CHAT_FIELD_NUMBER: _ClassVar[int]
    SMS_FIELD_NUMBER: _ClassVar[int]
    voice: VoiceChannel
    web_chat: WebChatChannel
    sms: SmsChannel
    def __init__(self, voice: _Optional[_Union[VoiceChannel, _Mapping]] = ..., web_chat: _Optional[_Union[WebChatChannel, _Mapping]] = ..., sms: _Optional[_Union[SmsChannel, _Mapping]] = ...) -> None: ...

class SmsChannel_UpdateSettings(_message.Message):
    __slots__ = ("sender_phone_number", "channel_behavior_mode", "behavior_config", "ending_message", "error_fallback_message", "compliance_keywords", "enabled")
    SENDER_PHONE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    CHANNEL_BEHAVIOR_MODE_FIELD_NUMBER: _ClassVar[int]
    BEHAVIOR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    ENDING_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ERROR_FALLBACK_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    COMPLIANCE_KEYWORDS_FIELD_NUMBER: _ClassVar[int]
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    sender_phone_number: str
    channel_behavior_mode: str
    behavior_config: SmsBehaviorConfig
    ending_message: str
    error_fallback_message: str
    compliance_keywords: _containers.RepeatedCompositeFieldContainer[SmsComplianceKeyword]
    enabled: bool
    def __init__(self, sender_phone_number: _Optional[str] = ..., channel_behavior_mode: _Optional[str] = ..., behavior_config: _Optional[_Union[SmsBehaviorConfig, _Mapping]] = ..., ending_message: _Optional[str] = ..., error_fallback_message: _Optional[str] = ..., compliance_keywords: _Optional[_Iterable[_Union[SmsComplianceKeyword, _Mapping]]] = ..., enabled: bool = ...) -> None: ...

class Channel_UpdateGreeting(_message.Message):
    __slots__ = ("channel_type", "greeting")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    GREETING_FIELD_NUMBER: _ClassVar[int]
    channel_type: ChannelType
    greeting: _agent_settings_pb2.Greeting_UpdateGreeting
    def __init__(self, channel_type: _Optional[_Union[ChannelType, str]] = ..., greeting: _Optional[_Union[_agent_settings_pb2.Greeting_UpdateGreeting, _Mapping]] = ...) -> None: ...

class Channel_UpdateStylePrompt(_message.Message):
    __slots__ = ("channel_type", "style_prompt")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    channel_type: ChannelType
    style_prompt: StylePrompt_UpdateStylePrompt
    def __init__(self, channel_type: _Optional[_Union[ChannelType, str]] = ..., style_prompt: _Optional[_Union[StylePrompt_UpdateStylePrompt, _Mapping]] = ...) -> None: ...

class Channel_UpdateSafetyFilters(_message.Message):
    __slots__ = ("channel_type", "safety_filters")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    channel_type: ChannelType
    safety_filters: _content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings
    def __init__(self, channel_type: _Optional[_Union[ChannelType, str]] = ..., safety_filters: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings_UpdateContentFilterSettings, _Mapping]] = ...) -> None: ...

class Channel_UpdateLLMSettings(_message.Message):
    __slots__ = ("channel_type", "llm_settings")
    CHANNEL_TYPE_FIELD_NUMBER: _ClassVar[int]
    LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    channel_type: ChannelType
    llm_settings: _llm_settings_pb2.LLMSettings_UpdateLLMSettings
    def __init__(self, channel_type: _Optional[_Union[ChannelType, str]] = ..., llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings_UpdateLLMSettings, _Mapping]] = ...) -> None: ...

class Channel_UpdateStatus(_message.Message):
    __slots__ = ("webchat",)
    WEBCHAT_FIELD_NUMBER: _ClassVar[int]
    webchat: WebChatChannel_UpdateStatus
    def __init__(self, webchat: _Optional[_Union[WebChatChannel_UpdateStatus, _Mapping]] = ...) -> None: ...

class VoiceChannel_UpdateASRSettings(_message.Message):
    __slots__ = ("asr_settings",)
    ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    asr_settings: _asr_settings_pb2.ASRSettings_UpdateASRSettings
    def __init__(self, asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings_UpdateASRSettings, _Mapping]] = ...) -> None: ...

class VoiceChannel_UpdateDisclaimer(_message.Message):
    __slots__ = ("disclaimer",)
    DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    disclaimer: _agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage
    def __init__(self, disclaimer: _Optional[_Union[_agent_settings_pb2.DisclaimerMessage_UpdateDisclaimerMessage, _Mapping]] = ...) -> None: ...

class VoiceChannel_UpdateVadConfig(_message.Message):
    __slots__ = ("vad_config",)
    VAD_CONFIG_FIELD_NUMBER: _ClassVar[int]
    vad_config: VADConfig
    def __init__(self, vad_config: _Optional[_Union[VADConfig, _Mapping]] = ...) -> None: ...

class VoiceChannel_ResetVadConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateAudioEnhancement(_message.Message):
    __slots__ = ("audio_enhancement",)
    AUDIO_ENHANCEMENT_FIELD_NUMBER: _ClassVar[int]
    audio_enhancement: AudioEnhancement
    def __init__(self, audio_enhancement: _Optional[_Union[AudioEnhancement, _Mapping]] = ...) -> None: ...

class VoiceChannel_ResetAudioEnhancement(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateSilenceFillerUtterances(_message.Message):
    __slots__ = ("silence_filler_utterances",)
    SILENCE_FILLER_UTTERANCES_FIELD_NUMBER: _ClassVar[int]
    silence_filler_utterances: FillerUtterances
    def __init__(self, silence_filler_utterances: _Optional[_Union[FillerUtterances, _Mapping]] = ...) -> None: ...

class VoiceChannel_ResetSilenceFillerUtterances(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateAsrConfig(_message.Message):
    __slots__ = ("asr_config",)
    ASR_CONFIG_FIELD_NUMBER: _ClassVar[int]
    asr_config: _asr_pb2.Asr
    def __init__(self, asr_config: _Optional[_Union[_asr_pb2.Asr, _Mapping]] = ...) -> None: ...

class VoiceChannel_ResetAsrConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateBargeInConfig(_message.Message):
    __slots__ = ("enabled", "allowed_first_turn", "max_per_call", "min_speech_duration_seconds")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    ALLOWED_FIRST_TURN_FIELD_NUMBER: _ClassVar[int]
    MAX_PER_CALL_FIELD_NUMBER: _ClassVar[int]
    MIN_SPEECH_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    allowed_first_turn: bool
    max_per_call: int
    min_speech_duration_seconds: float
    def __init__(self, enabled: bool = ..., allowed_first_turn: bool = ..., max_per_call: _Optional[int] = ..., min_speech_duration_seconds: _Optional[float] = ...) -> None: ...

class VoiceChannel_ResetBargeInConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateTemperature(_message.Message):
    __slots__ = ("temperature",)
    TEMPERATURE_FIELD_NUMBER: _ClassVar[int]
    temperature: float
    def __init__(self, temperature: _Optional[float] = ...) -> None: ...

class VoiceChannel_ResetTemperature(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class VoiceChannel_UpdateAmbience(_message.Message):
    __slots__ = ("ambience",)
    AMBIENCE_FIELD_NUMBER: _ClassVar[int]
    ambience: AmbienceSettings
    def __init__(self, ambience: _Optional[_Union[AmbienceSettings, _Mapping]] = ...) -> None: ...

class WebChatChannel_UpdateStatus(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: ChannelStatus
    def __init__(self, status: _Optional[_Union[ChannelStatus, str]] = ...) -> None: ...
