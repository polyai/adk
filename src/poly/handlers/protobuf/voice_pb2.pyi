from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ElevenLabsTtsConfig(_message.Message):
    __slots__ = ("model_id", "similarity_boost", "stability", "speed")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    SIMILARITY_BOOST_FIELD_NUMBER: _ClassVar[int]
    STABILITY_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    similarity_boost: float
    stability: float
    speed: float
    def __init__(self, model_id: _Optional[str] = ..., similarity_boost: _Optional[float] = ..., stability: _Optional[float] = ..., speed: _Optional[float] = ...) -> None: ...

class PlayHTTtsConfig(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class CartesiaTtsConfig(_message.Message):
    __slots__ = ("model_id", "speed", "emotion", "volume")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    SPEED_FIELD_NUMBER: _ClassVar[int]
    EMOTION_FIELD_NUMBER: _ClassVar[int]
    VOLUME_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    speed: float
    emotion: str
    volume: float
    def __init__(self, model_id: _Optional[str] = ..., speed: _Optional[float] = ..., emotion: _Optional[str] = ..., volume: _Optional[float] = ...) -> None: ...

class HumeTtsConfig(_message.Message):
    __slots__ = ("model_id", "voice_description", "instant_mode", "provider")
    MODEL_ID_FIELD_NUMBER: _ClassVar[int]
    VOICE_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    INSTANT_MODE_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    model_id: str
    voice_description: str
    instant_mode: bool
    provider: str
    def __init__(self, model_id: _Optional[str] = ..., voice_description: _Optional[str] = ..., instant_mode: bool = ..., provider: _Optional[str] = ...) -> None: ...

class Voice(_message.Message):
    __slots__ = ("voice_id", "created_by", "created_at", "updated_by", "updated_at", "eleven_labs", "play_ht", "cartesia", "hume")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    ELEVEN_LABS_FIELD_NUMBER: _ClassVar[int]
    PLAY_HT_FIELD_NUMBER: _ClassVar[int]
    CARTESIA_FIELD_NUMBER: _ClassVar[int]
    HUME_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    eleven_labs: ElevenLabsTtsConfig
    play_ht: PlayHTTtsConfig
    cartesia: CartesiaTtsConfig
    hume: HumeTtsConfig
    def __init__(self, voice_id: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., eleven_labs: _Optional[_Union[ElevenLabsTtsConfig, _Mapping]] = ..., play_ht: _Optional[_Union[PlayHTTtsConfig, _Mapping]] = ..., cartesia: _Optional[_Union[CartesiaTtsConfig, _Mapping]] = ..., hume: _Optional[_Union[HumeTtsConfig, _Mapping]] = ...) -> None: ...

class AgentVoice(_message.Message):
    __slots__ = ("voice_id", "probability", "updated_by", "updated_at", "language_code")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    probability: float
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    language_code: str
    def __init__(self, voice_id: _Optional[str] = ..., probability: _Optional[float] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class DisclaimerVoice(_message.Message):
    __slots__ = ("voice_id", "updated_by", "updated_at", "language_code")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    language_code: str
    def __init__(self, voice_id: _Optional[str] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., language_code: _Optional[str] = ...) -> None: ...

class FavoriteVoice(_message.Message):
    __slots__ = ("voice_id", "account_id", "created_by", "created_at", "updated_by", "updated_at")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    CREATED_BY_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_BY_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    account_id: str
    created_by: str
    created_at: _timestamp_pb2.Timestamp
    updated_by: str
    updated_at: _timestamp_pb2.Timestamp
    def __init__(self, voice_id: _Optional[str] = ..., account_id: _Optional[str] = ..., created_by: _Optional[str] = ..., created_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., updated_by: _Optional[str] = ..., updated_at: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class Voices(_message.Message):
    __slots__ = ("agent_voices", "disclaimer_voices", "agent_voice_settings", "disclaimer_voice_settings", "favorite_voices")
    AGENT_VOICES_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_VOICES_FIELD_NUMBER: _ClassVar[int]
    AGENT_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    DISCLAIMER_VOICE_SETTINGS_FIELD_NUMBER: _ClassVar[int]
    FAVORITE_VOICES_FIELD_NUMBER: _ClassVar[int]
    agent_voices: _containers.RepeatedCompositeFieldContainer[AgentVoice]
    disclaimer_voices: _containers.RepeatedCompositeFieldContainer[DisclaimerVoice]
    agent_voice_settings: _containers.RepeatedCompositeFieldContainer[Voice]
    disclaimer_voice_settings: _containers.RepeatedCompositeFieldContainer[Voice]
    favorite_voices: _containers.RepeatedCompositeFieldContainer[FavoriteVoice]
    def __init__(self, agent_voices: _Optional[_Iterable[_Union[AgentVoice, _Mapping]]] = ..., disclaimer_voices: _Optional[_Iterable[_Union[DisclaimerVoice, _Mapping]]] = ..., agent_voice_settings: _Optional[_Iterable[_Union[Voice, _Mapping]]] = ..., disclaimer_voice_settings: _Optional[_Iterable[_Union[Voice, _Mapping]]] = ..., favorite_voices: _Optional[_Iterable[_Union[FavoriteVoice, _Mapping]]] = ...) -> None: ...

class Voice_AddAgentVoice(_message.Message):
    __slots__ = ("voice_id", "probability", "language_code")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    probability: float
    language_code: str
    def __init__(self, voice_id: _Optional[str] = ..., probability: _Optional[float] = ..., language_code: _Optional[str] = ...) -> None: ...

class Voice_DeleteAgentVoice(_message.Message):
    __slots__ = ("voice_id",)
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    def __init__(self, voice_id: _Optional[str] = ...) -> None: ...

class Voice_UpdateAgentVoice(_message.Message):
    __slots__ = ("voice_id", "probability", "new_voice_id")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    PROBABILITY_FIELD_NUMBER: _ClassVar[int]
    NEW_VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    probability: float
    new_voice_id: str
    def __init__(self, voice_id: _Optional[str] = ..., probability: _Optional[float] = ..., new_voice_id: _Optional[str] = ...) -> None: ...

class Voice_CreateAgentVoiceSettings(_message.Message):
    __slots__ = ("voice_id", "eleven_labs", "play_ht", "cartesia", "hume")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ELEVEN_LABS_FIELD_NUMBER: _ClassVar[int]
    PLAY_HT_FIELD_NUMBER: _ClassVar[int]
    CARTESIA_FIELD_NUMBER: _ClassVar[int]
    HUME_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    eleven_labs: ElevenLabsTtsConfig
    play_ht: PlayHTTtsConfig
    cartesia: CartesiaTtsConfig
    hume: HumeTtsConfig
    def __init__(self, voice_id: _Optional[str] = ..., eleven_labs: _Optional[_Union[ElevenLabsTtsConfig, _Mapping]] = ..., play_ht: _Optional[_Union[PlayHTTtsConfig, _Mapping]] = ..., cartesia: _Optional[_Union[CartesiaTtsConfig, _Mapping]] = ..., hume: _Optional[_Union[HumeTtsConfig, _Mapping]] = ...) -> None: ...

class Voice_UpdateAgentVoiceSettings(_message.Message):
    __slots__ = ("voice_id", "eleven_labs", "play_ht", "cartesia", "hume")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ELEVEN_LABS_FIELD_NUMBER: _ClassVar[int]
    PLAY_HT_FIELD_NUMBER: _ClassVar[int]
    CARTESIA_FIELD_NUMBER: _ClassVar[int]
    HUME_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    eleven_labs: ElevenLabsTtsConfig
    play_ht: PlayHTTtsConfig
    cartesia: CartesiaTtsConfig
    hume: HumeTtsConfig
    def __init__(self, voice_id: _Optional[str] = ..., eleven_labs: _Optional[_Union[ElevenLabsTtsConfig, _Mapping]] = ..., play_ht: _Optional[_Union[PlayHTTtsConfig, _Mapping]] = ..., cartesia: _Optional[_Union[CartesiaTtsConfig, _Mapping]] = ..., hume: _Optional[_Union[HumeTtsConfig, _Mapping]] = ...) -> None: ...

class Voice_UpdateDisclaimerVoice(_message.Message):
    __slots__ = ("voice_id", "language_code")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_CODE_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    language_code: str
    def __init__(self, voice_id: _Optional[str] = ..., language_code: _Optional[str] = ...) -> None: ...

class Voice_CreateDisclaimerVoiceSettings(_message.Message):
    __slots__ = ("voice_id", "eleven_labs", "play_ht", "cartesia", "hume")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ELEVEN_LABS_FIELD_NUMBER: _ClassVar[int]
    PLAY_HT_FIELD_NUMBER: _ClassVar[int]
    CARTESIA_FIELD_NUMBER: _ClassVar[int]
    HUME_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    eleven_labs: ElevenLabsTtsConfig
    play_ht: PlayHTTtsConfig
    cartesia: CartesiaTtsConfig
    hume: HumeTtsConfig
    def __init__(self, voice_id: _Optional[str] = ..., eleven_labs: _Optional[_Union[ElevenLabsTtsConfig, _Mapping]] = ..., play_ht: _Optional[_Union[PlayHTTtsConfig, _Mapping]] = ..., cartesia: _Optional[_Union[CartesiaTtsConfig, _Mapping]] = ..., hume: _Optional[_Union[HumeTtsConfig, _Mapping]] = ...) -> None: ...

class Voice_UpdateDisclaimerVoiceSettings(_message.Message):
    __slots__ = ("voice_id", "eleven_labs", "play_ht", "cartesia", "hume")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ELEVEN_LABS_FIELD_NUMBER: _ClassVar[int]
    PLAY_HT_FIELD_NUMBER: _ClassVar[int]
    CARTESIA_FIELD_NUMBER: _ClassVar[int]
    HUME_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    eleven_labs: ElevenLabsTtsConfig
    play_ht: PlayHTTtsConfig
    cartesia: CartesiaTtsConfig
    hume: HumeTtsConfig
    def __init__(self, voice_id: _Optional[str] = ..., eleven_labs: _Optional[_Union[ElevenLabsTtsConfig, _Mapping]] = ..., play_ht: _Optional[_Union[PlayHTTtsConfig, _Mapping]] = ..., cartesia: _Optional[_Union[CartesiaTtsConfig, _Mapping]] = ..., hume: _Optional[_Union[HumeTtsConfig, _Mapping]] = ...) -> None: ...

class Voice_AddFavoriteVoice(_message.Message):
    __slots__ = ("voice_id", "account_id")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    account_id: str
    def __init__(self, voice_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...

class Voice_RemoveFavoriteVoice(_message.Message):
    __slots__ = ("voice_id", "account_id")
    VOICE_ID_FIELD_NUMBER: _ClassVar[int]
    ACCOUNT_ID_FIELD_NUMBER: _ClassVar[int]
    voice_id: str
    account_id: str
    def __init__(self, voice_id: _Optional[str] = ..., account_id: _Optional[str] = ...) -> None: ...
