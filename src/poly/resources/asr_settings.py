"""Handling and managing Agent Studio ASR Settings (barge-in, interaction style)

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from functools import cached_property
from typing import Optional

from google.protobuf.message import Message

from poly.handlers.protobuf.asr_settings_pb2 import (
    ASRSettings_UpdateASRSettings,
    LatencyConfig,
)
from poly.handlers.protobuf.channels_pb2 import (
    VoiceChannel_UpdateASRSettings,
    VoiceChannel_UpdateBargeInConfig,
)
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource

logger = logging.getLogger(__name__)

VALID_INTERACTION_STYLES = {"balanced", "precise", "swift", "sonic", "turbo"}


@dataclass
class VoiceBargeInConfig(SubResource):
    """Barge-in on the voice channel.

    Agent Studio runs bargeInConfig.enabled over asrSettings.bargeIn whenever it is set, so
    barge_in is also sent as voice_channel_update_barge_in_config.
    """

    enabled: bool = False

    @property
    def command_type(self) -> str:
        return "voice_barge_in_config"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_barge_in_config"

    def build_update_proto(self) -> VoiceChannel_UpdateBargeInConfig:
        return VoiceChannel_UpdateBargeInConfig(enabled=self.enabled)

    def build_create_proto(self) -> None:
        raise NotImplementedError("Barge-in config cannot be created")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("Barge-in config cannot be deleted")


@register_resource("asr_settings")
@dataclass
class AsrSettings(YamlResource):
    """Resource class for managing ASR (speech recognition) settings"""

    barge_in: bool
    interaction_style: str

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        barge_in: bool = False,
        interaction_style: str = "balanced",
    ):
        self.resource_id = resource_id
        self.name = name
        self.barge_in = barge_in
        self.interaction_style = interaction_style

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "AsrSettings"]:
        """Parse ASR settings from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to ASR settings - it will not be pulled.")
            return {}

        voice_settings = projection.get("channels", {}).get("voice", {})
        asr_settings_data = voice_settings.get("asrSettings", {})
        if not asr_settings_data:
            return {}

        barge_in_config = voice_settings.get("bargeInConfig")
        if barge_in_config is not None:
            barge_in = barge_in_config.get("enabled", False)
        else:
            barge_in_legacy = asr_settings_data.get("bargeIn", False)
            barge_in = barge_in_legacy

        interaction_style = asr_settings_data.get("latencyConfig", {}).get(
            "interactionStyle", "balanced"
        )

        return {
            "asr_settings": cls(
                resource_id="asr_settings",
                name="asr_settings",
                barge_in=barge_in,
                interaction_style=interaction_style,
            )
        }

    @cached_property
    def file_path(self) -> str:
        return os.path.join("voice", "speech_recognition", "asr_settings.yaml")

    def to_yaml_dict(self) -> dict:
        return {
            "barge_in": self.barge_in,
            "interaction_style": self.interaction_style,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "AsrSettings":
        interaction_style = yaml_dict.get("interaction_style", "balanced")
        if interaction_style == "turbo":
            # this one is turbo in the FE, but sonic in the BE
            interaction_style = "sonic"

        return cls(
            resource_id=resource_id,
            name=name,
            barge_in=yaml_dict.get("barge_in", False),
            interaction_style=interaction_style,
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if not self.interaction_style and not self.barge_in:
            logger.warning(
                "Neither interaction style or barge-in setting detected. "
                "These will be reset to default on next push."
            )

        if self.interaction_style not in VALID_INTERACTION_STYLES:
            raise ValueError(
                f"Invalid interaction_style '{self.interaction_style}'. "
                f"Must be one of: {', '.join(VALID_INTERACTION_STYLES)}"
            )

    @property
    def command_type(self) -> str:
        return "voice_asr_settings"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_asr_settings"

    def build_update_proto(self) -> VoiceChannel_UpdateASRSettings:
        return VoiceChannel_UpdateASRSettings(
            asr_settings=ASRSettings_UpdateASRSettings(
                barge_in=self.barge_in,
                latency_config=LatencyConfig(
                    interaction_style=self.interaction_style,
                ),
            ),
        )

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for ASR settings.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for ASR settings.")

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["AsrSettings"]
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        if old_resource is None or old_resource.barge_in == self.barge_in:
            return [], [], []
        return (
            [],
            [
                VoiceBargeInConfig(
                    resource_id=self.resource_id, name="barge_in", enabled=self.barge_in
                )
            ],
            [],
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "voice", "speech_recognition", "asr_settings.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]
