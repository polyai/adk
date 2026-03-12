from google.protobuf import timestamp_pb2 as _timestamp_pb2
from poly.handlers.protobuf import llm_settings_pb2 as _llm_settings_pb2
from poly.handlers.protobuf import content_filter_settings_pb2 as _content_filter_settings_pb2
from poly.handlers.protobuf import asr_settings_pb2 as _asr_settings_pb2
from poly.handlers.protobuf import agent_settings_pb2 as _agent_settings_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ChannelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VOICE: _ClassVar[ChannelType]
    WEB_CHAT: _ClassVar[ChannelType]

class ChannelStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    NOT_CREATED: _ClassVar[ChannelStatus]
    CREATED: _ClassVar[ChannelStatus]
VOICE: ChannelType
WEB_CHAT: ChannelType
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
    __slots__ = ("llm_settings", "style_prompt", "greeting", "safety_filters")
    LLM_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    STYLE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    GREETING_FIELD_NUMBER: _ClassVar[int]
    SAFETY_FILTERS_FIELD_NUMBER: _ClassVar[int]
    llm_settings: _llm_settings_pb2.LLMSettings
    style_prompt: StylePrompt
    greeting: _agent_settings_pb2.Greeting
    safety_filters: _content_filter_settings_pb2.ContentFilterSettings
    def __init__(self, llm_settings: _Optional[_Union[_llm_settings_pb2.LLMSettings, _Mapping]] = ..., style_prompt: _Optional[_Union[StylePrompt, _Mapping]] = ..., greeting: _Optional[_Union[_agent_settings_pb2.Greeting, _Mapping]] = ..., safety_filters: _Optional[_Union[_content_filter_settings_pb2.ContentFilterSettings, _Mapping]] = ...) -> None: ...

class VoiceChannel(_message.Message):
    __slots__ = ("config", "asr_settings", "disclaimer")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    ASR_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_FIELD_NUMBER: _ClassVar[int]
    config: ChannelConfig
    asr_settings: _asr_settings_pb2.ASRSettings
    disclaimer: _agent_settings_pb2.DisclaimerMessage
    def __init__(self, config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., asr_settings: _Optional[_Union[_asr_settings_pb2.ASRSettings, _Mapping]] = ..., disclaimer: _Optional[_Union[_agent_settings_pb2.DisclaimerMessage, _Mapping]] = ...) -> None: ...

class WebChatChannel(_message.Message):
    __slots__ = ("config", "status")
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    config: ChannelConfig
    status: ChannelStatus
    def __init__(self, config: _Optional[_Union[ChannelConfig, _Mapping]] = ..., status: _Optional[_Union[ChannelStatus, str]] = ...) -> None: ...

class Channels(_message.Message):
    __slots__ = ("voice", "web_chat")
    VOICE_FIELD_NUMBER: _ClassVar[int]
    WEB_CHAT_FIELD_NUMBER: _ClassVar[int]
    voice: VoiceChannel
    web_chat: WebChatChannel
    def __init__(self, voice: _Optional[_Union[VoiceChannel, _Mapping]] = ..., web_chat: _Optional[_Union[WebChatChannel, _Mapping]] = ...) -> None: ...

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

class WebChatChannel_UpdateStatus(_message.Message):
    __slots__ = ("status",)
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: ChannelStatus
    def __init__(self, status: _Optional[_Union[ChannelStatus, str]] = ...) -> None: ...
