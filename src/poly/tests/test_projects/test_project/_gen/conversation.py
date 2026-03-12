# flake8: noqa
# ruff: noqa
# type: ignore
from typing import Any, Literal, NewType

from .attachment import Attachment
from .conv_utils import Utils
from .external_events import ExternalEvents, SMSReceived
from .history import AgentResponse, UserInput
from .log_utils import ConversationLogger
from .memory import Memory
from .sms import OutgoingSMS, OutgoingSMSTemplate, SMSTemplate

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
    "ApiIntegrations",
    "ApiExecutor",
]

# --- Exceptions ---

class SMSIntegrationNotFound(Exception):
    """No integration with given provider found in secret"""

    def __init__(self, secret_name: str, integration: str) -> None: ...


class SMSMissingAssistantAccess(Exception):
    """No access for assistant on SMS secret"""

    def __init__(self, secret_name: str, assistant_id: str, integration: str) -> None: ...


class MissingTemplate(Exception):
    """Template reference doesn't exist"""


# --- Emotion types ---

EmotionKindValue = NewType("EmotionKindValue", int)
EmotionIntensityValue = NewType("EmotionIntensityValue", int)


class EmotionKind:
    """Enum for emotion kind"""

    ANGER: EmotionKindValue
    POSITIVITY: EmotionKindValue
    SURPRISE: EmotionKindValue


class EmotionIntensity:
    """Enum for emotion intensity"""

    LOWEST: EmotionIntensityValue
    LOW: EmotionIntensityValue
    HIGH: EmotionIntensityValue
    HIGHEST: EmotionIntensityValue


class Emotion:
    """Emotion for Cartesia voice"""

    kind: EmotionKindValue | None
    intensity: EmotionIntensityValue | None

    def __init__(
        self,
        kind: EmotionKindValue | None = ...,
        intensity: EmotionIntensityValue | None = ...,
    ) -> None: ...
    def to_dict(self) -> dict: ...


# --- Voice types ---

class TTSVoice:
    """Base class for TTS voice configurations"""

    def __init__(
        self, provider: str, provider_voice_id: str, config: dict = ...
    ) -> None: ...
    @property
    def provider(self) -> str: ...
    @property
    def provider_voice_id(self) -> str: ...
    def to_dict(self) -> dict: ...


class CustomVoice(TTSVoice):
    """Voice configuration for a custom TTS provider."""

    def __init__(
        self, provider: str, provider_voice_id: str, **kwargs: Any
    ) -> None: ...


class ElevenLabsVoice(TTSVoice):
    """Voice configuration for ElevenLabs."""

    def __init__(
        self,
        provider_voice_id: str,
        similarity_boost: float | None = ...,
        stability: float | None = ...,
        model_id: Literal[
            "eleven_monolingual_v1",
            "eleven_multilingual_v1",
            "eleven_turbo_v2",
            "eleven_turbo_v2_5",
            "eleven_flash_v2_5",
        ]
        | None = ...,
        speed: float | None = ...,
    ) -> None: ...


class RimeVoice(TTSVoice):
    """Rime voice config"""

    def __init__(
        self,
        provider_voice_id: str,
        speech_alpha: float | None = ...,
        model_id: Literal["mist", "mistv2"] | None = ...,
    ) -> None: ...


class CartesiaVoice(TTSVoice):
    """Cartesia voice config"""

    def __init__(
        self,
        provider_voice_id: str,
        speed: float | None = ...,
        emotions: list[Emotion] | None = ...,
        model_id: str | None = ...,
        volume: float | None = ...,
        emotion: str | None = ...,
        language: str | None = ...,
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
    """Voice config for PlayHT"""

    def __init__(
        self,
        provider_voice_id: str,
        speed: float | None = ...,
        temperature: float | None = ...,
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
        | None = ...,
        voice_guidance: int | None = ...,
        style_guidance: int | None = ...,
        voice_engine: Literal[
            "Play3.0-mini", "PlayDialog", "PlayHT2.0-turbo", "PlayHT2.0", "PlayHT1.0"
        ]
        | None = ...,
    ) -> None: ...


class MinimaxVoice(TTSVoice):
    """Voice config for Minimax"""

    def __init__(
        self,
        model_id: Literal[
            "speech-02-hd",
            "speech-02-turbo",
            "speech-01-hd",
            "speech-01-turbo",
        ],
        voice_id: str,
        speed: float | None = ...,
        vol: float | None = ...,
        pitch: float | None = ...,
        emotion: Literal[
            "happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"
        ]
        | None = ...,
    ) -> None: ...


class HumeVoice(TTSVoice):
    """Voice config for Hume"""

    def __init__(
        self,
        provider_voice_id: str,
        voice_description: str | None = ...,
        version: str | None = ...,
        instant_mode: bool | None = ...,
        provider: Literal["CUSTOM_VOICE", "HUME_AI"] | None = ...,
    ) -> None: ...


class GoogleVoice(TTSVoice):
    """Voice configuration for Google TTS."""

    def __init__(
        self,
        provider_voice_id: str,
        gender: Literal["male", "female", "neutral"] | None = ...,
    ) -> None: ...


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


class VoiceWeighting:
    """Weighting for a voice"""

    def __init__(self, voice: VoiceType, weight: float | None = ...) -> None: ...
    @property
    def voice(self) -> VoiceType: ...
    @property
    def weight(self) -> float | None: ...


# --- State and dict-like types ---

class Variant(dict):
    """Variant object exposing variant attributes"""

    def __getattr__(self, key: str) -> Any: ...


class Entities(dict):
    """Entities object exposing entities attributes"""

    def __getattr__(self, key: str) -> Any: ...


class ReadOnlyDict(dict):
    """Read-only dictionary"""

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


class RealtimeConfig(ReadOnlyDict):
    """Realtime config"""

    def __init__(self, **kwargs: Any) -> None: ...


class State(dict):
    """`dict` subclass with ergonomic attribute-style access"""

    def __getattr__(self, key: str) -> Any: ...
    def __setattr__(self, key: str, value: Any) -> None: ...


# --- Metric ---

class MetricEvent:
    """Representation of a metric that has already been written to history."""

    name: str
    value: float | str | int | None

    def __init__(self, name: str, value: float | str | int | None) -> None: ...


# --- Executors and integrations ---

class ApiIntegrations:
    """Access to configured API integrations"""

    def __getattr__(self, name: str) -> Any: ...


class FunctionExecutor(dict):
    """Function executor for importing functions from the functions directory."""

    def __init__(self, conv: Conversation) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


class ApiExecutor:
    """API executor for calling configured API integrations."""

    def __init__(
        self,
        conv: Conversation,
        api_integrations: ApiIntegrations | None = ...,
    ) -> None: ...
    def __getattr__(self, name: str) -> Any: ...


# --- Conversation ---

class Conversation:
    """Object exposing useful information from the conversation runtime"""

    memory: Memory | None
    utils: Utils
    log: ConversationLogger

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
    def handoffs(self) -> dict[str, Any]: ...
    @property
    def transcript_alternatives(self) -> list[str]: ...
    @property
    def real_time_config(self) -> dict[str, Any]: ...
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
    def metric_events(self) -> list[MetricEvent]: ...
    def set_voice(self, voice: VoiceType) -> None: ...
    def set_language(self, language: str) -> None: ...
    def set_asr_biasing(
        self,
        keywords: list[str] | None = ...,
        custom_biases: dict[str, float] | None = ...,
    ) -> None: ...
    def clear_asr_biasing(self) -> None: ...
    def say(self, utterance: str) -> None: ...
    def randomize_voice(self, voice_weights: list[VoiceWeighting]) -> None: ...
    def goto_flow(self, flow_name: str) -> None: ...
    def exit_flow(self) -> None: ...
    def goto_csat_flow(self) -> None: ...
    def set_variant(self, variant: str) -> None: ...
    def send_sms(
        self,
        to_number: str,
        from_number: str,
        content: str,
        retry_count: int | None = ...,
    ) -> dict | None: ...
    def send_whatsapp(
        self,
        to_number: str,
        from_number: str,
        content_id: str,
        content: str | None = ...,
        retry_count: int | None = ...,
    ) -> dict | None: ...
    def send_content_template(
        self,
        messaging_service_id: str,
        to_number: str,
        content_id: str,
        content: str | None = ...,
        whatsapp: bool | None = ...,
        content_variables: dict | None = ...,
        retry_count: int | None = ...,
    ) -> dict | None: ...
    def send_sms_template(
        self,
        to_number: str,
        template: str,
        retry_count: int | None = ...,
    ) -> dict | None: ...
    def send_email(self, to: str, body: str, subject: str = ...) -> None: ...
    def call_handoff(
        self,
        destination: str,
        reason: str = ...,
        utterance: str = ...,
        sip_headers: dict[str, str] | None = ...,
        route: str | None = ...,
    ) -> None: ...
    def generate_external_event(self, *, send_to_llm: bool = ...) -> str: ...
    def write_metric(
        self,
        name: str,
        value: float | int | str | None = ...,
        *,
        write_once: bool = ...,
    ) -> None: ...
    def add_attachments(self, attachments: list[Attachment]) -> None: ...
    def set_response_suggestions(self, suggestions: list[str]) -> None: ...
    def set_csat_eligibility(
        self, eligible: bool, reason: str | None = ...
    ) -> None: ...
    def set_csat_phone_number(self, phone_number: str) -> None: ...
    def set_csat_score(self, score: int) -> None: ...
    def set_csat_survey_entered(self) -> None: ...
    def discard_recording(self) -> None: ...
    def log_api_response(
        self, response: Any, override_url: str = ...
    ) -> None: ...
