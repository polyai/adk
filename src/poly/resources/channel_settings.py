"""Handling and managing Agent Studio Channel Settings (Voice, Chat)

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass, field
from functools import cached_property
from typing import ClassVar

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.agent_settings_pb2 import (
    DisclaimerMessage_UpdateDisclaimerMessage,
    Greeting_UpdateGreeting,
)
from poly.handlers.protobuf.channels_pb2 import (
    AmbienceSettings,
    Channel_UpdateGreeting,
    Channel_UpdateStylePrompt,
    ChannelType,
    FillerUtterances,
    StylePrompt_UpdateStylePrompt,
    VoiceChannel_ResetSilenceFillerUtterances,
    VoiceChannel_UpdateAmbience,
    VoiceChannel_UpdateDisclaimer,
    VoiceChannel_UpdateSilenceFillerUtterances,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    register_resource,
)

logger = logging.getLogger(__name__)

# Limits of Agent Studio's voice settings.
FILLER_INITIAL_INTERVAL_MIN_SECONDS = 0.5
FILLER_INTERVAL_MIN_SECONDS = 1.0
AMBIENCE_LOUDNESS_MIN_DB = -70
AMBIENCE_LOUDNESS_MAX_DB = -20

# Agent Studio rejects any other preset; new ones need a platform release first.
AMBIENCE_PRESETS = ("office-ambiance", "restaurant-ambiance", "whitenoise-subtle")

DEFAULT_FILLER_PHRASES = ("One moment...", "Just a second...", "One second...")


def _config_path(channel: str) -> str:
    """Return config path for a channel (e.g. voice/configuration.yaml)."""
    return os.path.join(channel, "configuration.yaml")


def _reject_unknown_keys(yaml_dict: dict, known_keys: tuple[str, ...], section: str) -> None:
    """Raise if a section has keys it doesn't define, so a misspelt key isn't dropped.

    Raises:
        ValueError: If the section has unknown keys.
    """
    if unknown_keys := sorted(set(yaml_dict) - set(known_keys)):
        raise ValueError(
            f"Unknown key(s) in '{section}': {', '.join(unknown_keys)}. "
            f"Expected: {', '.join(known_keys)}."
        )


def _discover_voice_section(base_path: str, top_level_name: str) -> list[str]:
    """Return the section's resource path when voice/configuration.yaml has it set."""
    file_path = os.path.join(base_path, _config_path("voice"))
    if not os.path.exists(file_path):
        return []
    yaml_dict = MultiResourceYamlResource._get_top_level_data(file_path)
    if not (yaml_dict or {}).get(top_level_name):
        return []
    return [os.path.join(file_path, top_level_name)]


@register_resource("voice_disclaimer")
@dataclass
class VoiceDisclaimerMessage(MultiResourceYamlResource):
    """Resource class for managing disclaimer message settings (voice-only)"""

    message: str = field(default="")
    enabled: bool = field(default=False)
    language_code: str = field(default="en-GB")

    top_level_name: ClassVar[str] = "disclaimer_messages"
    _singleton: ClassVar[bool] = True

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the DisclaimerMessage resource."""
        return os.path.join(_config_path("voice"), VoiceDisclaimerMessage.top_level_name)

    def to_yaml_dict(self) -> dict:
        """Convert the disclaimer settings to a YAML-serializable dict."""
        return {
            "message": self.message,
            "enabled": self.enabled,
            "language_code": self.language_code,
        }

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["message"] = utils.replace_resource_ids_with_names(d["message"], resource_mappings or [])
        return d

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "VoiceDisclaimerMessage":
        """Construct disclaimer settings from YAML data and identity fields."""
        return VoiceDisclaimerMessage(
            resource_id=resource_id,
            name=name,
            message=yaml_dict.get("message", ""),
            enabled=yaml_dict.get("enabled", False),
            language_code=yaml_dict.get("language_code", "en-GB"),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the disclaimer message resource."""

        references = utils.get_references_from_prompt(
            self.message, ["attributes", "variables", "translations"], raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

        if not self.language_code:
            raise ValueError("Language code cannot be empty.")

    def build_update_proto(self) -> VoiceChannel_UpdateDisclaimer:
        """Create a proto for updating the resource."""

        return VoiceChannel_UpdateDisclaimer(
            disclaimer=DisclaimerMessage_UpdateDisclaimerMessage(
                message=self.message,
                is_enabled=self.enabled,
                language_code=self.language_code,
            )
        )

    def build_create_proto(self):
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Disclaimer settings.")

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Disclaimer settings.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "disclaimer_message"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_disclaimer"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VoiceDisclaimerMessage"]:
        """Parse voice disclaimer from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to the voice disclaimer - it will not be pulled.")
            return {}

        voice_settings = projection.get("channels", {}).get("voice", {})
        voice_disclaimer = voice_settings.get("disclaimer", None)
        if not voice_disclaimer:
            return {}
        return {
            "voice_disclaimer": cls(
                resource_id="voice_disclaimer",
                name="voice_disclaimer",
                message=voice_disclaimer.get("message", ""),
                enabled=voice_disclaimer.get("isEnabled", False),
                language_code=voice_disclaimer.get("languageCode", "en-GB"),
            )
        }

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        file_path = os.path.join(base_path, _config_path("voice"))

        if not os.path.exists(file_path):
            return []

        yaml_dict = VoiceDisclaimerMessage._get_top_level_data(file_path)
        disclaimer_messages: list[dict] = (
            yaml_dict.get("disclaimer_messages", []) if yaml_dict else []
        )

        if not disclaimer_messages:
            return []

        return [os.path.join(file_path, VoiceDisclaimerMessage.top_level_name)]


@dataclass
class ChannelGreeting(MultiResourceYamlResource):
    """Base class for channel greeting settings. Subclass for voice/chat."""

    _singleton: ClassVar[bool] = True

    welcome_message: str = field(default="")
    language_code: str = field(default="en-GB")
    top_level_name: ClassVar[str] = "greeting"

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Greeting resource."""
        return os.path.join(_config_path(self.channel_subpath), self.top_level_name)

    def to_yaml_dict(self) -> dict:
        """Convert the greeting settings to a YAML-serializable dict."""
        return {"welcome_message": self.welcome_message, "language_code": self.language_code}

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["welcome_message"] = utils.replace_resource_ids_with_names(
            d["welcome_message"], resource_mappings or []
        )
        return d

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "ChannelGreeting":
        """Construct greeting settings from YAML data and identity fields."""
        return cls(
            resource_id=resource_id,
            name=name,
            welcome_message=yaml_dict.get("welcome_message", ""),
            language_code=yaml_dict.get("language_code", "en-GB"),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the greeting resource."""
        references = utils.get_references_from_prompt(
            self.welcome_message, ["attributes", "variables", "translations"], raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

        if not self.welcome_message:
            raise ValueError("Welcome message cannot be empty.")

        if not self.language_code:
            raise ValueError("Language code cannot be empty.")

    def build_update_proto(self) -> Channel_UpdateGreeting:
        """Create a proto for updating the resource."""
        return Channel_UpdateGreeting(
            channel_type=self.channel_type,
            greeting=Greeting_UpdateGreeting(
                welcome_message=self.welcome_message,
                language_code=self.language_code,
            ),
        )

    def build_create_proto(self):
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Greeting settings.")

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Greeting settings.")

    @property
    def command_type(self) -> str:
        return "greeting"

    @property
    def update_command_type(self) -> str:
        return "channel_update_greeting"

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        file_path = os.path.join(base_path, _config_path(cls.channel_subpath))

        if not os.path.exists(file_path):
            return []

        yaml_dict = cls._get_top_level_data(file_path)
        greeting: dict = yaml_dict.get("greeting", {}) if yaml_dict else {}

        if not greeting:
            return []

        return [os.path.join(file_path, cls.top_level_name)]


@register_resource("voice_greeting")
@dataclass
class VoiceGreeting(ChannelGreeting):
    """Voice channel greeting settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VoiceGreeting"]:
        """Parse voice greeting from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to the voice greeting - it will not be pulled.")
            return {}

        voice_config = projection.get("channels", {}).get("voice", {}).get("config", {}) or {}
        voice_greeting = voice_config.get("greeting", None)
        if not voice_greeting:
            return {}
        return {
            "voice_greeting": cls(
                resource_id="voice_greeting",
                name="voice_greeting",
                welcome_message=voice_greeting.get("welcomeMessage", ""),
                language_code=voice_greeting.get("languageCode", "en-GB"),
            )
        }


@register_resource("chat_greeting")
@dataclass
class ChatGreeting(ChannelGreeting):
    """Chat (web chat) channel greeting settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.WEB_CHAT
    channel_subpath: ClassVar[str] = "chat"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "ChatGreeting"]:
        """Parse chat greeting from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to the chat greeting - it will not be pulled.")
            return {}

        web_chat_settings = projection.get("channels", {}).get("webChat", {})
        if not web_chat_settings.get("status", False):
            return {}
        chat_config = web_chat_settings.get("config", {}) or {}
        chat_greeting = chat_config.get("greeting", None)
        if not chat_greeting:
            return {}
        return {
            "chat_greeting": cls(
                resource_id="chat_greeting",
                name="chat_greeting",
                welcome_message=chat_greeting.get("welcomeMessage", ""),
                language_code=chat_greeting.get("languageCode", "en-GB"),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the chat greeting resource."""
        super().validate(resource_mappings=resource_mappings, **kwargs)
        utils.validate_webchat_siblings(type(self), resource_mappings)


@dataclass
class ChannelStylePrompt(MultiResourceYamlResource):
    """Base class for channel style prompt settings. Subclass for voice/chat."""

    _singleton: ClassVar[bool] = True

    prompt: str = field(default="")
    top_level_name: ClassVar[str] = "style_prompt"

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the StylePrompt resource."""
        return os.path.join(_config_path(self.channel_subpath), self.top_level_name)

    def to_yaml_dict(self) -> dict:
        """Convert the style prompt settings to a YAML-serializable dict."""
        return {"prompt": self.prompt}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "ChannelStylePrompt":
        """Construct style prompt settings from YAML data and identity fields."""
        return cls(
            resource_id=resource_id,
            name=name,
            prompt=yaml_dict.get("prompt", ""),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        utils.get_references_from_prompt(self.prompt, [], raise_on_invalid=True)

    def build_update_proto(self) -> Channel_UpdateStylePrompt:
        """Create a proto for updating the resource."""
        return Channel_UpdateStylePrompt(
            channel_type=self.channel_type,
            style_prompt=StylePrompt_UpdateStylePrompt(prompt=self.prompt),
        )

    def build_create_proto(self):
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for StylePrompt settings.")

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for StylePrompt settings.")

    @property
    def command_type(self) -> str:
        return "style_prompt"

    @property
    def update_command_type(self) -> str:
        return "channel_update_style_prompt"

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        file_path = os.path.join(base_path, _config_path(cls.channel_subpath))

        if not os.path.exists(file_path):
            return []

        yaml_dict = cls._get_top_level_data(file_path)
        style_prompt: dict = yaml_dict.get("style_prompt", {}) if yaml_dict else {}

        if not style_prompt:
            return []

        return [os.path.join(file_path, cls.top_level_name)]


@register_resource("voice_style_prompt")
@dataclass
class VoiceStylePrompt(ChannelStylePrompt):
    """Voice channel style prompt settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VoiceStylePrompt"]:
        """Parse voice style prompt from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to the voice style prompt - it will not be pulled.")
            return {}

        voice_config = projection.get("channels", {}).get("voice", {}).get("config", {}) or {}
        voice_style_prompt = voice_config.get("stylePrompt", None)
        if not voice_style_prompt:
            return {}
        return {
            "voice_style_prompt": cls(
                resource_id="voice_style_prompt",
                name="voice_style_prompt",
                prompt=voice_style_prompt.get("prompt", ""),
            )
        }


@register_resource("chat_style_prompt")
@dataclass
class ChatStylePrompt(ChannelStylePrompt):
    """Chat (web chat) channel style prompt settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.WEB_CHAT
    channel_subpath: ClassVar[str] = "chat"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "ChatStylePrompt"]:
        """Parse chat style prompt from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to the chat style prompt - it will not be pulled.")
            return {}

        web_chat_settings = projection.get("channels", {}).get("webChat", {})
        if not web_chat_settings.get("status", False):
            return {}
        chat_config = web_chat_settings.get("config", {}) or {}
        chat_style_prompt = chat_config.get("stylePrompt", None)
        if not chat_style_prompt:
            return {}
        return {
            "chat_style_prompt": cls(
                resource_id="chat_style_prompt",
                name="chat_style_prompt",
                prompt=chat_style_prompt.get("prompt", ""),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the chat style prompt resource."""
        super().validate(resource_mappings=resource_mappings, **kwargs)
        utils.validate_webchat_siblings(type(self), resource_mappings)


@register_resource("voice_filler_phrases")
@dataclass
class VoiceFillerPhrases(MultiResourceYamlResource):
    """Phrases the agent says while the caller waits on a slow turn.

    Pushed as the voice channel's silence filler utterances. Removing the section resets them.
    """

    enabled: bool = False
    phrases: list[str] = field(default_factory=lambda: list(DEFAULT_FILLER_PHRASES))
    randomize: bool = True
    initial_interval_seconds: float = 2.5
    interval_seconds: float = 5

    top_level_name: ClassVar[str] = "filler_phrases"
    _singleton: ClassVar[bool] = True
    yaml_keys: ClassVar[tuple[str, ...]] = (
        "enabled",
        "phrases",
        "randomize",
        "initial_interval_seconds",
        "interval_seconds",
    )

    @cached_property
    def file_path(self) -> str:
        return os.path.join(_config_path("voice"), self.top_level_name)

    def to_yaml_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "phrases": list(self.phrases),
            "randomize": self.randomize,
            "initial_interval_seconds": self.initial_interval_seconds,
            "interval_seconds": self.interval_seconds,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "VoiceFillerPhrases":
        _reject_unknown_keys(yaml_dict, cls.yaml_keys, cls.top_level_name)
        return cls(
            resource_id=resource_id,
            name=name,
            **{key: yaml_dict[key] for key in cls.yaml_keys if key in yaml_dict},
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VoiceFillerPhrases"]:
        """Parse the voice channel's silence filler utterances from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to voice filler phrases - they will not be pulled.")
            return {}

        filler = projection.get("channels", {}).get("voice", {}).get("silenceFillerUtterances")
        if not filler:
            return {}
        return {
            "voice_filler_phrases": cls(
                resource_id="voice_filler_phrases",
                name="voice_filler_phrases",
                enabled=filler.get("enabled", False),
                phrases=[
                    utterance.get("message", "") for utterance in filler.get("utterances", [])
                ],
                randomize=filler.get("randomize", False),
                initial_interval_seconds=filler.get("initialIntervalSeconds", 2.5),
                interval_seconds=filler.get("intervalSeconds", 5),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if self.enabled and not any(phrase.strip() for phrase in self.phrases):
            raise ValueError("filler_phrases needs at least one phrase when enabled.")
        if self.initial_interval_seconds < FILLER_INITIAL_INTERVAL_MIN_SECONDS:
            raise ValueError(
                "filler_phrases.initial_interval_seconds must be at least "
                f"{FILLER_INITIAL_INTERVAL_MIN_SECONDS:g}."
            )
        if self.interval_seconds < FILLER_INTERVAL_MIN_SECONDS:
            raise ValueError(
                f"filler_phrases.interval_seconds must be at least {FILLER_INTERVAL_MIN_SECONDS:g}."
            )

    @property
    def command_type(self) -> str:
        return "voice_silence_filler_utterances"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_silence_filler_utterances"

    @property
    def create_command_type(self) -> str:
        return self.update_command_type

    @property
    def delete_command_type(self) -> str:
        return "voice_channel_reset_silence_filler_utterances"

    def build_update_proto(self) -> VoiceChannel_UpdateSilenceFillerUtterances:
        return VoiceChannel_UpdateSilenceFillerUtterances(
            silence_filler_utterances=FillerUtterances(
                enabled=self.enabled,
                utterances=[FillerUtterances.Utterance(message=phrase) for phrase in self.phrases],
                randomize=self.randomize,
                initial_interval_seconds=self.initial_interval_seconds,
                interval_seconds=self.interval_seconds,
            )
        )

    def build_create_proto(self) -> VoiceChannel_UpdateSilenceFillerUtterances:
        return self.build_update_proto()

    def build_delete_proto(self) -> VoiceChannel_ResetSilenceFillerUtterances:
        return VoiceChannel_ResetSilenceFillerUtterances()

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        return _discover_voice_section(base_path, cls.top_level_name)


@register_resource("voice_background_ambience")
@dataclass
class VoiceBackgroundAmbience(MultiResourceYamlResource):
    """Background sound played under the agent's speech.

    The section exists only while ambience is on. The platform has no command to clear
    ambience, so a removed section is pushed as an update that turns it off (see
    prepush.switch_off_removed_ambience).
    """

    preset: str = ""
    loudness: float = -50
    # Only False on the update built to turn ambience off; never read from or written to YAML.
    enabled: bool = field(default=True, init=False, repr=False)

    top_level_name: ClassVar[str] = "background_ambience"
    _singleton: ClassVar[bool] = True
    yaml_keys: ClassVar[tuple[str, ...]] = ("preset", "loudness")

    @cached_property
    def file_path(self) -> str:
        return os.path.join(_config_path("voice"), self.top_level_name)

    def to_yaml_dict(self) -> dict:
        return {"preset": self.preset, "loudness": self.loudness}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "VoiceBackgroundAmbience":
        _reject_unknown_keys(yaml_dict, cls.yaml_keys, cls.top_level_name)
        return cls(
            resource_id=resource_id,
            name=name,
            **{key: yaml_dict[key] for key in cls.yaml_keys if key in yaml_dict},
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VoiceBackgroundAmbience"]:
        """Parse the voice channel's ambience from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to voice background ambience - it will not be pulled.")
            return {}

        ambience = projection.get("channels", {}).get("voice", {}).get("ambience")
        if not ambience or not ambience.get("enabled"):
            return {}
        return {
            "voice_background_ambience": cls(
                resource_id="voice_background_ambience",
                name="voice_background_ambience",
                preset=ambience.get("preset", ""),
                loudness=ambience.get("loudness", -50),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if not self.preset:
            raise ValueError("background_ambience needs a preset.")
        if not AMBIENCE_LOUDNESS_MIN_DB <= self.loudness <= AMBIENCE_LOUDNESS_MAX_DB:
            raise ValueError(
                f"background_ambience.loudness must be between {AMBIENCE_LOUDNESS_MIN_DB} "
                f"and {AMBIENCE_LOUDNESS_MAX_DB} dB."
            )
        if self.preset not in AMBIENCE_PRESETS:
            # Warn rather than fail, so a preset added to the platform after this ADK
            # release can still be pushed.
            logger.warning(
                f"background_ambience.preset '{self.preset}' is not a known preset "
                f"({', '.join(AMBIENCE_PRESETS)}). Agent Studio may reject it."
            )

    def switched_off(self) -> "VoiceBackgroundAmbience":
        """Return a copy that turns ambience off, keeping its preset and loudness."""
        off = VoiceBackgroundAmbience(
            resource_id=self.resource_id,
            name=self.name,
            preset=self.preset,
            loudness=self.loudness,
        )
        off.enabled = False
        return off

    @property
    def command_type(self) -> str:
        return "voice_ambience"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_ambience"

    @property
    def create_command_type(self) -> str:
        return self.update_command_type

    def build_update_proto(self) -> VoiceChannel_UpdateAmbience:
        return VoiceChannel_UpdateAmbience(
            ambience=AmbienceSettings(
                enabled=self.enabled, preset=self.preset, loudness=self.loudness
            )
        )

    def build_create_proto(self) -> VoiceChannel_UpdateAmbience:
        return self.build_update_proto()

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Ambience cannot be reset")

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        return _discover_voice_section(base_path, cls.top_level_name)
