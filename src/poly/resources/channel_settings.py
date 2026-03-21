"""Handling and managing Agent Studio Channel Settings (Voice, Chat)

Copyright PolyAI Limited
"""

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
    Channel_UpdateGreeting,
    Channel_UpdateStylePrompt,
    ChannelType,
    StylePrompt_UpdateStylePrompt,
    VoiceChannel_UpdateDisclaimer,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
)


def _config_path(channel: str) -> str:
    """Return config path for a channel (e.g. voice/configuration.yaml)."""
    return os.path.join(channel, "configuration.yaml")


@dataclass
class VoiceDisclaimerMessage(MultiResourceYamlResource):
    """Resource class for managing disclaimer message settings (voice-only)"""

    projection_path: ClassVar[list[str]] = ["channels", "voice", "disclaimer"]

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
            self.message, ["attributes", "variables"], raise_on_invalid=True
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
            self.welcome_message, ["attributes", "variables"], raise_on_invalid=True
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


@dataclass
class VoiceGreeting(ChannelGreeting):
    """Voice channel greeting settings."""

    projection_path: ClassVar[list[str]] = ["channels", "voice", "config", "greeting"]

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"


@dataclass
class ChatGreeting(ChannelGreeting):
    """Chat (web chat) channel greeting settings."""

    projection_path: ClassVar[list[str]] = ["channels", "webChat", "config", "greeting"]

    channel_type: ClassVar[ChannelType] = ChannelType.WEB_CHAT
    channel_subpath: ClassVar[str] = "chat"


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


@dataclass
class VoiceStylePrompt(ChannelStylePrompt):
    """Voice channel style prompt settings."""

    projection_path: ClassVar[list[str]] = ["channels", "voice", "config", "stylePrompt"]

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"


@dataclass
class ChatStylePrompt(ChannelStylePrompt):
    """Chat (web chat) channel style prompt settings."""

    projection_path: ClassVar[list[str]] = ["channels", "webChat", "config", "stylePrompt"]

    channel_type: ClassVar[ChannelType] = ChannelType.WEB_CHAT
    channel_subpath: ClassVar[str] = "chat"
