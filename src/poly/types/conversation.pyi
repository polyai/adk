# Copyright PolyAI Limited
__all__ = [
    "SMSIntegrationNotFound",
    "SMSMissingAssistantAccess",
    "MissingTemplate",
    "TTSVoice",
    "CustomVoice",
    "ElevenLabsVoice",
    "RimeVoice",
    "GoogleVoice",
    "EmotionKindValue",
    "EmotionIntensityValue",
    "Emotion",
    "EmotionIntensity",
    "EmotionKind",
    "CartesiaVoice",
    "PlayHTVoice",
    "MinimaxVoice",
    "HumeVoice",
    "VoiceType",
    "VoiceWeighting",
    "Variant",
    "State",
    "Conversation",
    "MetricEvent",
    "FunctionExecutor",
    "ApiExecutor",
    "Integrations",
]

import requests
from . import external_events as external_events
from dataclasses import dataclass, field
from .agentic_dial import AgenticDialData
from .attachment import Attachment as Attachment
from .entity_validator import EntityValidationResult
from .history import AgentResponse, UserInput
from .integrations.integrations import Integrations
from .knowledge_base import KnowledgeBase
from .memory import Memory
from .sms import (
    OutgoingSMS,
    OutgoingSMSTemplate as OutgoingSMSTemplate,
    SMSCredentials,
    SMSTemplate,
)
from .webchat import WebchatInterface
from typing import Any, Literal

def best_effort_substitute(prompt: str, variables: dict) -> str: ...

class SMSIntegrationNotFound(Exception):
    def __init__(self, secret_name: str, integration: str) -> None: ...

class SMSMissingAssistantAccess(Exception):
    def __init__(self, secret_name: str, assistant_id: str, integration: str) -> None: ...

class MissingTemplate(Exception): ...

class MissingHandoff(Exception):
    def __init__(self, handoff_destination: str) -> None: ...

class TTSVoice:
    def __init__(self, provider: str, provider_voice_id: str, config: dict = {}) -> None: ...
    @property
    def provider(self) -> str: ...
    @property
    def provider_voice_id(self) -> str: ...
    def to_dict(self): ...

class CustomVoice(TTSVoice):
    def __init__(self, provider: str, provider_voice_id: str, **kwargs) -> None: ...

class ElevenLabsVoice(TTSVoice):
    def __init__(
        self,
        provider_voice_id: str,
        similarity_boost: float | None = None,
        stability: float | None = None,
        model_id: Literal[
            "eleven_monolingual_v1",
            "eleven_multilingual_v1",
            "eleven_turbo_v2",
            "eleven_turbo_v2_5",
            "eleven_flash_v2_5",
        ]
        | None = "eleven_turbo_v2_5",
        speed: float | None = None,
    ) -> None: ...
    @property
    def similarity_boost(self) -> float | None: ...
    @property
    def stability(self) -> float | None: ...
    @property
    def speed(self) -> float | None: ...

class RimeVoice(TTSVoice):
    def __init__(
        self,
        provider_voice_id: str,
        speech_alpha: float | None = 1.0,
        model_id: Literal["mist", "mistv2"] | None = "mistv2",
    ) -> None: ...
    @property
    def speech_alpha(self) -> float | None: ...

EmotionKindValue: Any
EmotionIntensityValue: Any

class EmotionKind:
    ANGER: Any
    POSITIVITY: Any
    SURPRISE: Any

class EmotionIntensity:
    LOWEST: Any
    LOW: Any
    HIGH: Any
    HIGHEST: Any

class Emotion:
    kind: Any
    intensity: Any
    def __init__(
        self, kind: EmotionKindValue | None = None, intensity: EmotionIntensityValue | None = None
    ) -> None: ...
    def to_dict(self) -> dict: ...

class CartesiaVoice(TTSVoice):
    def __init__(
        self,
        provider_voice_id: str,
        speed: float | None = 0,
        emotions: list[Emotion] | None = None,
        model_id: str | None = "sonic",
        volume: float | None = None,
        emotion: str | None = None,
        language: str | None = None,
    ) -> None: ...
    @property
    def emotions(self) -> list[Emotion] | None: ...
    @property
    def speed(self) -> float | None: ...
    @property
    def volume(self) -> float | None: ...
    @property
    def emotion(self) -> str | None: ...
    @property
    def language(self) -> str | None: ...

class PlayHTVoice(TTSVoice):
    def __init__(
        self,
        provider_voice_id: str,
        speed: float | None = None,
        temperature: float | None = None,
        emotion: Literal[
            "female_happy",
            "female_sad",
            "female_angry",
            "female_fearful",
            "female_disgust",
            "female_surprised",
            "male_happy",
            "male_sad",
            "male_angry",
            "male_fearful",
            "male_disgust",
            "male_surprised",
        ]
        | None = None,
        voice_guidance: int | None = None,
        style_guidance: int | None = None,
        voice_engine: Literal[
            "Play3.0-mini", "PlayDialog", "PlayHT2.0-turbo", "PlayHT2.0", "PlayHT1.0"
        ]
        | None = None,
    ) -> None: ...
    @property
    def temperature(self) -> float | None: ...

class MinimaxVoice(TTSVoice):
    def __init__(
        self,
        model_id: Literal["speech-02-hd", "speech-02-turbo", "speech-01-hd", "speech-01-turbo"],
        voice_id: str,
        speed: float | None = None,
        vol: float | None = None,
        pitch: float | None = None,
        emotion: Literal["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
        | None = None,
    ) -> None: ...
    @property
    def model_id(self) -> str: ...
    @property
    def speed(self) -> float | None: ...
    @property
    def vol(self) -> float | None: ...
    @property
    def pitch(self) -> float | None: ...
    @property
    def emotion(self) -> str | None: ...

class HumeVoice(TTSVoice):
    def __init__(
        self,
        provider_voice_id: str,
        voice_description: str | None = None,
        version: str | None = "2",
        instant_mode: bool | None = False,
        provider: Literal["CUSTOM_VOICE", "HUME_AI"] | None = "CUSTOM_VOICE",
    ) -> None: ...

class GoogleVoice(TTSVoice):
    def __init__(
        self, provider_voice_id: str, gender: Literal["male", "female", "neutral"] | None = None
    ) -> None: ...
    @property
    def gender(self) -> str | None: ...

VoiceType = (
    CustomVoice
    | ElevenLabsVoice
    | PlayHTVoice
    | CartesiaVoice
    | RimeVoice
    | MinimaxVoice
    | HumeVoice
    | GoogleVoice
)
SupportedLanguageCodes: Any

class VoiceWeighting:
    def __init__(self, voice: VoiceType, weight: float | None = None) -> None: ...
    @property
    def voice(self) -> VoiceType: ...
    @property
    def weight(self) -> float | None: ...

@dataclass
class BackgroundTrack:
    name: str
    loudness: float = ...

@dataclass
class FlowTransition:
    goto_flow: str | None = ...
    exit_flow: bool = ...

class Variant(dict):
    __getattr__: Any

class Entities(dict):
    __getattr__: Any

@dataclass
class HandoffConfig:
    sip_type: Any
    sip_config: dict = field(default_factory=dict)
    sip_headers: dict = field(default_factory=dict)
    @classmethod
    def from_dict(cls, d: dict): ...

@dataclass
class Handoff:
    handoff: HandoffConfig
    reason: str | None
    destination: str | None = ...
    @classmethod
    def from_dict(cls, d: dict): ...
    def to_response(self) -> dict: ...

@dataclass
class ApiIntegrationData:
    id: str
    name: str
    environments: dict[str, dict[str, str]]
    operations: list[dict[str, str]]
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiIntegrationData: ...

@dataclass
class ASRBiasing:
    keywords: list[str] | None = ...
    custom_biases: dict[str, float] | None = ...

class State(dict):
    def __getattr__(self, key: str) -> Any | None: ...
    def __setattr__(self, key: str, value: Any): ...
    def __deepcopy__(self, memo): ...
    def __reduce__(self): ...

class ReadOnlyDict(dict):
    def __readonly__(self, *args, **kwargs) -> None: ...
    __setitem__ = __readonly__
    __delitem__ = __readonly__
    clear = __readonly__
    pop = __readonly__
    popitem = __readonly__
    setdefault = __readonly__
    update = __readonly__
    def __init__(self, *args, **kwargs) -> None: ...

class TranslationReplacementProxy:
    def __init__(
        self, translations_config: dict[str, dict[str, str]] | None, language_code: str | None
    ) -> None: ...
    def __getattr__(self, name): ...

class RealtimeConfig(ReadOnlyDict):
    def __init__(self, **kwargs) -> None: ...

@dataclass
class MetricEvent:
    name: str
    value: float | str | int | None

class FunctionExecutor(dict):
    conv: Any
    def __init__(self, conv: Conversation) -> None: ...
    def __getattr__(self, name: str) -> Any: ...

class ApiExecutor:
    conv: Any
    api_integrations: Any
    def __init__(self, conv: Conversation, api_integrations: Any | None = None) -> None: ...
    def __getattr__(self, name: str) -> Any: ...

class Conversation:
    utils: Any
    memory: Any
    log: Any
    agentic_dial: Any
    def __init__(
        self,
        call_sid: str,
        account_id: str,
        project_id: str,
        env: str,
        sip_headers: dict[str, str],
        state: State,
        current_flow: str | None,
        current_step: str | None,
        flow_transition: FlowTransition,
        caller_number: str | None,
        callee_number: str | None,
        variant: str | None = None,
        variants: dict[str, Variant] | None = None,
        sms_templates: dict[str, SMSTemplate] | None = None,
        language: str | None = None,
        turn_number: int | None = None,
        history: list[UserInput | AgentResponse] | None = None,
        transcript_alternatives: list[str] | None = None,
        handoffs: dict[str, HandoffConfig] | None = None,
        integration_attributes: dict[str, Any] | None = None,
        memory: Memory | None = None,
        metric_events: list[MetricEvent] | None = None,
        sms_received: list[external_events.SMSReceived] | None = None,
        realtime_config: dict[str, Any] | None = None,
        functions: dict[str, Any] | None = None,
        vpc_enabled: bool | None = False,
        generic_external_events: list[external_events.GenericExternalEvent] | None = None,
        channel_type: Literal["sms", "VOICE", "sip.polyai"] | None = None,
        entities: dict[str, EntityValidationResult] | None = None,
        apis: list[ApiIntegrationData] | None = None,
        variables: dict[str, str] | None = None,
        translations: dict[str, dict] | None = None,
        agentic_dial: AgenticDialData | None = None,
        provider_voice_id: str | None = None,
        integrations_config: dict[str, Any] | None = None,
    ) -> None: ...
    @classmethod
    def from_runtime_data(
        cls,
        runtime_data: dict[str, Any],
        call_sid: str,
        account_id: str,
        project_id: str,
        env: str,
        flow_transition: FlowTransition,
        vpc_enabled: bool = False,
    ) -> Conversation: ...
    @property
    def id(self) -> str: ...
    @property
    def account_id(self) -> str: ...
    @property
    def project_id(self) -> str: ...
    @property
    def env(self) -> str: ...
    @property
    def sip_headers(self) -> dict[str, str]: ...
    @property
    def integration_attributes(self) -> dict[str, Any] | None: ...
    @property
    def caller_number(self) -> str | None: ...
    @property
    def callee_number(self) -> str | None: ...
    @property
    def state(self) -> State: ...
    @property
    def entities(self) -> Entities: ...
    @property
    def current_flow(self) -> str | None: ...
    @property
    def current_step(self) -> str | None: ...
    @property
    def sms_queue(self) -> list[OutgoingSMS | OutgoingSMSTemplate]: ...
    @property
    def metrics_queue(self) -> list[dict]: ...
    @property
    def variant_name(self) -> str | None: ...
    @property
    def variants(self) -> dict[str, Variant]: ...
    @property
    def variant(self) -> Variant | None: ...
    @property
    def sms_templates(self) -> dict[str, SMSTemplate]: ...
    @property
    def voice_change(self) -> TTSVoice | None: ...
    @property
    def language(self) -> str | None: ...
    @property
    def history(self) -> list[UserInput | AgentResponse]: ...
    @property
    def handoffs(self) -> dict[str, HandoffConfig]: ...
    @property
    def transcript_alternatives(self) -> list[str]: ...
    @property
    def real_time_config(self) -> dict[str, Any | None]: ...
    @property
    def functions(self) -> FunctionExecutor: ...
    @property
    def api(self) -> ApiExecutor: ...
    @property
    def generic_external_events(self) -> list[dict]: ...
    @property
    def channel_type(self) -> str: ...
    @property
    def attachments(self) -> list[Attachment]: ...
    @property
    def response_suggestions(self) -> list[str]: ...
    @property
    def webchat(self) -> WebchatInterface: ...
    @property
    def translations(self) -> TranslationReplacementProxy: ...
    @property
    def provider_voice_id(self) -> str: ...
    @property
    def integrations(self) -> Integrations: ...
    def send_email(self, to: str, body: str, subject: str = "") -> None: ...
    def set_voice(self, voice: VoiceType): ...
    def set_language(self, language: SupportedLanguageCodes): ...
    def set_asr_biasing(
        self, keywords: list[str] | None = None, custom_biases: dict[str, float] | None = None
    ) -> None: ...
    def clear_asr_biasing(self) -> None: ...
    @property
    def knowledge_base(self) -> KnowledgeBase: ...
    def say(self, utterance: str): ...
    def randomize_voice(self, voice_weights: list[VoiceWeighting]): ...
    def goto_flow(self, flow_name: str): ...
    def exit_flow(self) -> None: ...
    def goto_csat_flow(self) -> None: ...
    def set_variant(self, variant: str): ...
    def log_api_response(self, response: requests.models.Response, override_url: str = None): ...
    def send_sms(
        self, to_number: str, from_number: str, content: str, retry_count: int | None = None
    ) -> dict | None: ...
    def send_whatsapp(
        self,
        to_number: str,
        from_number: str,
        content_id: str,
        content: str | None = "",
        retry_count: int | None = None,
    ) -> dict | None: ...
    def send_content_template(
        self,
        messaging_service_id: str,
        to_number: str,
        content_id: str,
        content: str | None = "",
        whatsapp: bool | None = False,
        content_variables: dict | None = None,
        retry_count: int | None = None,
    ) -> dict | None: ...
    def send_sms_template(
        self, to_number: str, template: str, retry_count: int | None = None
    ) -> dict | None: ...
    def set_csat_eligibility(self, eligible: bool, reason: str | None = None): ...
    def set_csat_phone_number(self, phone_number: str): ...
    def set_csat_score(self, score: int): ...
    def set_csat_survey_entered(self) -> None: ...
    def set_background_track(self, name: str, loudness: float = -40): ...
    def add_attachments(self, attachments: list[Attachment]) -> None: ...
    def set_response_suggestions(self, suggestions: list[str]) -> None: ...
    def generate_external_event(self, *, send_to_llm: bool = False) -> str: ...
    @property
    def metric_events(self) -> list[MetricEvent]: ...
    def write_metric(
        self, name: str, value: float | int | str | None = None, *, write_once: bool = False
    ): ...
    def call_handoff(
        self,
        destination: str,
        reason: str = None,
        utterance: str = None,
        sip_headers: dict[str, str] | None = None,
        route: str | None = None,
    ): ...
    def discard_recording(self) -> None: ...

def retrieve_sms_credentials(
    secret_name: str, secret_dict: dict[str, Any], project_id: str, integration: str
) -> SMSCredentials: ...
