# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore


from typing import Any, Literal, NewType
import requests
from .external_events import GenericExternalEvent, SMSReceived
from .agentic_dial import AgenticDialData
from .entity_validator import EntityValidationResult
from .history import AgentResponse, UserInput
from .integrations.integrations import Integrations
from .memory import Memory
from .sms import OutgoingSMS, OutgoingSMSTemplate, SMSTemplate
from .webchat import WebchatInterface
from .attachment import Attachment


__all__ = [
    "SMSIntegrationNotFound",
    "SMSMissingAssistantAccess",
    "MissingTemplate",
    "MissingHandoff",
    "TTSVoice",
    "CustomVoice",
    "ElevenLabsVoice",
    "RimeVoice",
    "EmotionKind",
    "EmotionIntensity",
    "Emotion",
    "CartesiaVoice",
    "PlayHTVoice",
    "MinimaxVoice",
    "HumeVoice",
    "GoogleVoice",
    "VoiceWeighting",
    "FlowTransition",
    "Variant",
    "Entities",
    "HandoffConfig",
    "Handoff",
    "ApiIntegrationData",
    "ASRBiasing",
    "State",
    "ReadOnlyDict",
    "TranslationReplacementProxy",
    "RealtimeConfig",
    "MetricEvent",
    "FunctionExecutor",
    "ApiExecutor",
    "Conversation",
    "EmotionKindValue",
    "EmotionIntensityValue",
    "VoiceType",
    "SupportedLanguageCodes",
]

SupportedLanguageCodes = Literal[
    "en-US",
    "en-GB",
    "es-US",
    "es-ES",
    "ar-SA",
    "zh-CN",
    "zh-TW",
    "ja-JP",
    "ko-KR",
    "cs-CZ",
    "nl-NL",
    "en-AU",
    "en-CA",
    "en-IE",
    "en-NZ",
    "en-SG",
    "fr-CA",
    "fr-FR",
    "fr-BE",
    "de-DE",
    "it-IT",
    "pl-PL",
    "pt-BR",
    "pt-PT",
    "sr-RS",
    "es-ES",
    "sv-SE",
    "tr-TR",
    "nl-BE",
    "hr-HR",
    "yue-HK",
    "el-GR",
    "hi-IN",
    "bg-BG",
    "bs-BA",
    "sk-SK",
]


class SMSIntegrationNotFound(Exception):
    """No integration with given provider fo[und in secret"""

    def __init__(self, secret_name: str, integration: str): ...


class SMSMissingAssistantAccess(Exception):
    """No access for assistant on SMS secret"""

    def __init__(self, secret_name: str, assistant_id: str, integration: str): ...


class MissingTemplate(Exception):
    """Template reference doesn't exist"""


class MissingHandoff(Exception):
    """Handoff does not exist"""

    def __init__(self, handoff_destination: str): ...


class TTSVoice:
    """Base class for TTS voice configurations"""

    def __init__(self, provider: str, provider_voice_id: str, config: dict = ...): ...
    @property
    def provider(self) -> str:
        """The provider name."""

    @property
    def provider_voice_id(self) -> str:
        """The unique identifier for the voice."""

    def to_dict(self):
        """Convert the TTSVoice to a dictionary."""


class CustomVoice(TTSVoice):
    """Voice configuration for a custom TTS provider."""

    def __init__(self, provider: str, provider_voice_id: str, **kwargs):
        """Initialize a voice from the given TTS provider."""


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
    ):
        """Initialize ElevenLabs voice."""

    @property
    def similarity_boost(self) -> float | None:
        """The similarity boost factor."""

    @property
    def stability(self) -> float | None:
        """The stability factor."""

    @property
    def speed(self) -> float | None:
        """The speed factor."""


class RimeVoice(TTSVoice):
    """Rime voice config"""

    def __init__(
        self,
        provider_voice_id: str,
        speech_alpha: float | None = ...,
        model_id: Literal["mist", "mistv2"] | None = ...,
    ):
        """Initialize Rime voice."""

    @property
    def speech_alpha(self) -> float | None:
        """speech pace"""


class EmotionKind:
    """Enum for emotion kind"""


class EmotionIntensity:
    """Enum for emotion intensity"""


class Emotion:
    """Emotion for Cartesia voice"""

    def __init__(
        self, kind: EmotionKindValue | None = ..., intensity: EmotionIntensityValue | None = ...
    ):
        """Initialize an Emotion instance."""

    def to_dict(self) -> dict:
        """Convert the emotion to a dictionary."""


class CartesiaVoice(TTSVoice):
    """Carteisa voice config"""

    def __init__(
        self,
        provider_voice_id: str,
        speed: float | None = ...,
        emotions: list[Emotion] | None = ...,
        model_id: str | None = ...,
        volume: float | None = ...,
        emotion: str | None = ...,
        language: str | None = ...,
    ):
        """Initialize Cartesia voice."""

    @property
    def emotions(self) -> list[Emotion] | None:
        """speech emotion list"""

    @property
    def speed(self) -> float | None:
        """speech speed"""

    @property
    def volume(self) -> float | None:
        """speech volume (Sonic 3)"""

    @property
    def emotion(self) -> str | None:
        """emotion string (Sonic 3)"""

    @property
    def language(self) -> str | None:
        """language code (Sonic 3)"""


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
    ):
        """Initialize the PlayHT voice."""

    @property
    def temperature(self) -> float | None:
        """The temperature."""


class MinimaxVoice(TTSVoice):
    """Voice config for Minimax"""

    def __init__(
        self,
        model_id: Literal["speech-02-hd", "speech-02-turbo", "speech-01-hd", "speech-01-turbo"],
        voice_id: str,
        speed: float | None = ...,
        vol: float | None = ...,
        pitch: float | None = ...,
        emotion: Literal["happy", "sad", "angry", "fearful", "disgusted", "surprised", "neutral"]
        | None = ...,
    ):
        """Initialise the Minimax TTS voice"""

    @property
    def model_id(self) -> str:
        """The model ID."""

    @property
    def speed(self) -> float | None:
        """The speed of the generated speech."""

    @property
    def vol(self) -> float | None:
        """The volume of the generated speech."""

    @property
    def pitch(self) -> float | None:
        """The pitch of the generated speech."""

    @property
    def emotion(self) -> str | None:
        """The emotion of the generated speech."""


class HumeVoice(TTSVoice):
    """Voice config for Hume"""

    def __init__(
        self,
        provider_voice_id: str,
        voice_description: str | None = ...,
        version: str | None = ...,
        instant_mode: bool | None = ...,
        provider: Literal["CUSTOM_VOICE", "HUME_AI"] | None = ...,
    ):
        """Initialize Hume voice."""


class GoogleVoice(TTSVoice):
    """Voice configuration for Google TTS."""

    def __init__(
        self, provider_voice_id: str, gender: Literal["male", "female", "neutral"] | None = ...
    ):
        """Initialize Google TTS voice."""

    @property
    def gender(self) -> str | None:
        """The gender of the voice."""


class VoiceWeighting:
    """Weighting for a voice"""

    def __init__(self, voice: VoiceType, weight: float | None = ...):
        """Create a VoiceWeighting for voice randomization."""

    @property
    def voice(self) -> VoiceType:
        """The TTSVoice to use."""

    @property
    def weight(self) -> float | None:
        """The weight for the voice."""


class FlowTransition:
    """Mutable object to trigger flow transitions"""

    goto_flow: str | None
    exit_flow: bool

    def __init__(self, goto_flow: str | None = ..., exit_flow: bool = ...) -> None: ...


class Variant(dict):
    """Variant object exposing variant attributes"""


class Entities(dict):
    """Entities object exposing entities attributes"""


class HandoffConfig:
    """Handoff configuration"""

    sip_type: HandoffMethod
    sip_config: dict
    sip_headers: dict

    def __init__(
        self, sip_type: HandoffMethod, sip_config: dict = ..., sip_headers: dict = ...
    ) -> None: ...
    @classmethod
    def from_dict(cls, d: dict):
        """from_dict"""


class Handoff:
    """Handoff response"""

    handoff: HandoffConfig
    reason: str | None
    destination: str | None

    def __init__(
        self, handoff: HandoffConfig, reason: str | None, destination: str | None = ...
    ) -> None: ...
    @classmethod
    def from_dict(cls, d: dict):
        """from_dict"""

    def to_response(self) -> dict:
        """Convert dataclass object into response format"""


class ApiIntegrationData:
    """API integration data for runtime"""

    id: str
    name: str
    environments: dict[str, dict[str, str]]
    operations: list[dict[str, str]]

    def __init__(
        self,
        id: str,
        name: str,
        environments: dict[str, dict[str, str]],
        operations: list[dict[str, str]],
    ) -> None: ...
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ApiIntegrationData:
        """Create from dictionary with defensive access"""


class ASRBiasing:
    """ASR biasing configuration set by a function"""

    keywords: list[str] | None
    custom_biases: dict[str, float] | None

    def __init__(
        self, keywords: list[str] | None = ..., custom_biases: dict[str, float] | None = ...
    ) -> None: ...


class State(dict):
    """`dict` subclass with ergonomic attribute-style access"""

    def __getattr__(self, key: str) -> Any | None:
        """Attribute access of values using keys"""

    def __setattr__(self, key: str, value: Any):
        """Attribute style update of values using keys"""

    def __deepcopy__(self, memo):
        """deepcopy"""

    def __reduce__(self):
        """reduce"""


class ReadOnlyDict(dict):
    """Read-only dictionary"""

    def __readonly__(self, *args, **kwargs):
        """raise TypeError when trying to modify the dictionary"""

    def __init__(self, *args, **kwargs): ...


class TranslationReplacementProxy:
    """Custom dictionary to support language translations replacements"""

    def __init__(
        self, translations_config: dict[str, dict[str, str]] | None, language_code: str | None
    ): ...
    def __getattr__(self, name):
        """__getattr__"""


class RealtimeConfig(ReadOnlyDict):
    """Realtime config"""

    def __init__(self, **kwargs):
        """init"""


class MetricEvent:
    """Representation of a metric that has already been written to history."""

    name: str
    value: float | str | int | None

    def __init__(self, name: str, value: float | str | int | None) -> None: ...


class FunctionExecutor(dict):
    """Function executor"""

    def __init__(self, conv: Conversation): ...
    def __getattr__(self, name: str) -> Any:
        """Dynamically import and return a function when accessed via dot notation."""


class ApiExecutor:
    """API executor"""

    def __init__(self, conv: Conversation, api_integrations: ApiIntegrations | None = ...): ...
    def __getattr__(self, name: str) -> Any:
        """Dynamically return API integration by name when accessed via dot notation."""


class Conversation:
    """Object exposing useful information from the conversation runtime"""

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
        variant: str | None = ...,
        variants: dict[str, Variant] | None = ...,
        sms_templates: dict[str, SMSTemplate] | None = ...,
        language: str | None = ...,
        turn_number: int | None = ...,
        history: list[UserInput | AgentResponse] | None = ...,
        transcript_alternatives: list[str] | None = ...,
        handoffs: dict[str, HandoffConfig] | None = ...,
        integration_attributes: dict[str, Any] | None = ...,
        memory: Memory | None = ...,
        metric_events: list[MetricEvent] | None = ...,
        sms_received: list[SMSReceived] | None = ...,
        realtime_config: dict[str, Any] | None = ...,
        functions: dict[str, Any] | None = ...,
        vpc_enabled: bool | None = ...,
        generic_external_events: list[GenericExternalEvent] | None = ...,
        channel_type: Literal["sms", "VOICE", "sip.polyai"] | None = ...,
        entities: dict[str, EntityValidationResult] | None = ...,
        apis: list[ApiIntegrationData] | None = ...,
        variables: dict[str, str] | None = ...,
        translations: dict[str, dict] | None = ...,
        agentic_dial: AgenticDialData | None = ...,
        provider_voice_id: str | None = ...,
        integrations_config: dict[str, Any] | None = ...,
    ):
        """init"""

    @classmethod
    def from_runtime_data(
        cls,
        runtime_data: dict[str, Any],
        call_sid: str,
        account_id: str,
        project_id: str,
        env: str,
        flow_transition: FlowTransition,
        vpc_enabled: bool = ...,
    ) -> Conversation:
        """Build Conversation object from runtime_data JSON dict"""

    @property
    def id(self) -> str:
        """The ID of the conversation"""

    @property
    def account_id(self) -> str:
        """The account ID"""

    @property
    def project_id(self) -> str:
        """The project ID"""

    @property
    def env(self) -> str:
        """The client environment this is executing in"""

    @property
    def sip_headers(self) -> dict[str, str]:
        """Dict mapping header names to values"""

    @property
    def integration_attributes(self) -> dict[str, Any] | None:
        """Attributes provided by an external integration."""

    @property
    def caller_number(self) -> str | None:
        """The caller's phone number"""

    @property
    def callee_number(self) -> str | None:
        """The callee's phone number"""

    @property
    def state(self) -> State:
        """Dictionary of saved variables that persist through the conversation"""

    @property
    def entities(self) -> Entities:
        """The entities collected from the conversation"""

    @property
    def current_flow(self) -> str | None:
        """Name of the flow we are currently in"""

    @property
    def current_step(self) -> str | None:
        """Name of the step we are currently in"""

    @property
    def sms_queue(self) -> list[OutgoingSMS | OutgoingSMSTemplate]:
        """Queue of SMS messages to send"""

    @property
    def metrics_queue(self) -> list[dict]:
        """Queue of metrics to write"""

    @property
    def variant_name(self) -> str | None:
        """The name of the variant of the conversation"""

    @property
    def variants(self) -> dict[str, Variant]:
        """The variants of the conversation with their attributes"""

    @property
    def variant(self) -> Variant | None:
        """The variant of the conversation"""

    @property
    def sms_templates(self) -> dict[str, SMSTemplate]:
        """The SMS templates available to the conversation"""

    @property
    def voice_change(self) -> TTSVoice | None:
        """The request to change voice for the conversation"""

    @property
    def language(self) -> str | None:
        """The ISO 639 language code of the language set for the conversation"""

    @property
    def history(self) -> list[UserInput | AgentResponse]:
        """The history of the conversation so far"""

    @property
    def handoffs(self) -> dict[str, HandoffConfig]:
        """The handoffs available to the conversation"""

    @property
    def transcript_alternatives(self) -> list[str]:
        """List of transcription alternatives for the last user input,"""

    @property
    def real_time_config(self) -> dict[str, Any | None]:
        """The real time config for the conversation"""

    @property
    def functions(self) -> FunctionExecutor:
        """The functions available to the conversation"""

    @property
    def api(self) -> ApiExecutor:
        """Access to API integrations via conv.api.{api_name}.{operation}()"""

    @property
    def generic_external_events(self) -> list[dict]:
        """The generic external events available to the conversation initiated by the"""

    @property
    def channel_type(self) -> str:
        """The channel of the conversation e.g. 'sms', 'sip.polyai'"""

    @property
    def attachments(self) -> list[Attachment]:
        """List of attachments to be included with the next agent message."""

    @property
    def response_suggestions(self) -> list[str]:
        """List of response suggestions (text strings) for the next agent message."""

    @property
    def webchat(self) -> WebchatInterface:
        """Webchat-specific interface."""

    @property
    def translations(self) -> TranslationReplacementProxy:
        """Return the localized translation of the accessed field name."""

    @property
    def provider_voice_id(self) -> str:
        """The TTS provider voice ID set for the conversation"""

    @property
    def integrations(self) -> Integrations:
        """Access to external integrations via conv.integrations.{integration_name}()"""

    def send_email(self, to: str, body: str, subject: str = ...) -> None:
        """Send an email"""

    def set_voice(self, voice: VoiceType):
        """Change the voice for the current conversation moving forward."""

    def set_language(self, language: SupportedLanguageCodes):
        """Change the language for the current conversation moving forward."""

    def set_asr_biasing(
        self, keywords: list[str] | None = ..., custom_biases: dict[str, float] | None = ...
    ) -> None:
        """Set ASR biasing for the conversation."""

    def clear_asr_biasing(self) -> None:
        """Clear ASR biasing for future turns."""

    def say(self, utterance: str):
        """Set the next utterance to be said following the execution of the function"""

    def randomize_voice(self, voice_weights: list[VoiceWeighting]):
        """Randomly selects a voice from a weighted list of voices."""

    def goto_flow(self, flow_name: str):
        """Trigger a transition to a flow"""

    def exit_flow(self):
        """Trigger exiting the current flow"""

    def goto_csat_flow(self):
        """Trigger a transition to the CSAT survey flow for voice."""

    def set_variant(self, variant: str):
        """Set the variant of the conversation"""

    def log_api_response(self, response: requests.models.Response, override_url: str = ...):
        """Log api response for analytics"""

    def send_sms(
        self, to_number: str, from_number: str, content: str, retry_count: int | None = ...
    ) -> dict | None:
        """Sends an SMS"""

    def send_whatsapp(
        self,
        to_number: str,
        from_number: str,
        content_id: str,
        content: str | None = ...,
        retry_count: int | None = ...,
    ) -> dict | None:
        """Sends a WhatsApp message"""

    def send_content_template(
        self,
        messaging_service_id: str,
        to_number: str,
        content_id: str,
        content: str | None = ...,
        whatsapp: bool | None = ...,
        content_variables: dict | None = ...,
        retry_count: int | None = ...,
    ) -> dict | None:
        """Sends a WhatsApp message"""

    def send_sms_template(
        self, to_number: str, template: str, retry_count: int | None = ...
    ) -> dict | None:
        """Sends an SMS template"""

    def set_csat_eligibility(self, eligible: bool, reason: str | None = ...):
        """Set whether this conversation is eligible for CSAT surveys."""

    def set_csat_phone_number(self, phone_number: str):
        """Set the phone number to use for CSAT SMS surveys."""

    def set_csat_score(self, score: int):
        """Set the CSAT score for this conversation."""

    def set_csat_survey_entered(self):
        """Mark that the CSAT survey was entered for this conversation."""

    def add_attachments(self, attachments: list[Attachment]) -> None:
        """Adds the given attachments to the agent message."""

    def set_response_suggestions(self, suggestions: list[str]) -> None:
        """Sets response suggestions for the agent message."""

    def generate_external_event(self, *, send_to_llm: bool = ...) -> str:
        """Generate an external event ID which can be sent to some external provider."""

    @property
    def metric_events(self) -> list[MetricEvent]:
        """List of metric events already written in the conversation."""

    def write_metric(
        self, name: str, value: float | int | str | None = ..., *, write_once: bool = ...
    ):
        """Write a custom metric for call analytics."""

    def call_handoff(
        self,
        destination: str,
        reason: str = ...,
        utterance: str = ...,
        sip_headers: dict[str, str] | None = ...,
        route: str | None = ...,
    ):
        """Trigger a transfer of the conversation to a live agent"""

    def discard_recording(self):
        """Stop any recordings of the current conversation and prevent them from being"""


EmotionKindValue = NewType("EmotionKindValue", int)
EmotionIntensityValue = NewType("EmotionIntensityValue", int)
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
