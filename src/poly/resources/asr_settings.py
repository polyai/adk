"""Handling and managing the voice channel's turn-taking

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Optional, Union

from google.protobuf.message import Message

from poly.handlers.protobuf.channels_pb2 import (
    VADConfig,
    VoiceChannel_ResetBargeInConfig,
    VoiceChannel_ResetVadConfig,
    VoiceChannel_UpdateBargeInConfig,
    VoiceChannel_UpdateVadConfig,
)
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource

logger = logging.getLogger(__name__)

# Limits of Agent Studio's voice settings. The backend only checks for non-negative values.
SPEECH_END_DELAY_MS_MIN = 200
SPEECH_END_DELAY_MS_MAX = 1500


@dataclass
class BargeIn:
    """Whether, and how often, the caller can interrupt the agent."""

    enabled: bool = False
    allow_on_first_turn: bool = False
    # Absent means the platform has no limit stored, which is different from 0.
    max_per_call: Optional[int] = None

    def validate(self) -> None:
        """Validate the barge-in configuration."""
        if self.max_per_call is not None and self.max_per_call < 0:
            raise ValueError("barge_in.max_per_call cannot be negative.")

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        output: dict[str, Any] = {
            "enabled": self.enabled,
            "allow_on_first_turn": self.allow_on_first_turn,
        }
        if self.max_per_call is not None:
            output["max_per_call"] = self.max_per_call
        return output


@dataclass
class VoiceVadConfig(SubResource):
    """The speech_end_delay_ms section, pushed as the voice channel's VAD config."""

    speech_end_delay_ms: Optional[int] = None

    @property
    def command_type(self) -> str:
        return "voice_vad_config"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_vad_config"

    @property
    def delete_command_type(self) -> str:
        return "voice_channel_reset_vad_config"

    def build_update_proto(self) -> VoiceChannel_UpdateVadConfig:
        return VoiceChannel_UpdateVadConfig(
            vad_config=VADConfig(speech_end_window_seconds=self.speech_end_delay_ms / 1000)
        )

    def build_delete_proto(self) -> VoiceChannel_ResetVadConfig:
        return VoiceChannel_ResetVadConfig()

    def build_create_proto(self) -> None:
        raise NotImplementedError("VAD config cannot be created")


@dataclass
class VoiceBargeInConfig(SubResource):
    """The barge_in section, pushed as the voice channel's barge-in config.

    The platform merges a barge-in update into what it has, so fields left out of the proto
    keep their stored value.
    """

    barge_in: Optional[BargeIn] = None

    @property
    def command_type(self) -> str:
        return "voice_barge_in_config"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_barge_in_config"

    @property
    def delete_command_type(self) -> str:
        return "voice_channel_reset_barge_in_config"

    def build_update_proto(self) -> VoiceChannel_UpdateBargeInConfig:
        return VoiceChannel_UpdateBargeInConfig(
            enabled=self.barge_in.enabled,
            allowed_first_turn=self.barge_in.allow_on_first_turn,
            max_per_call=self.barge_in.max_per_call,
        )

    def build_delete_proto(self) -> VoiceChannel_ResetBargeInConfig:
        return VoiceChannel_ResetBargeInConfig()

    def build_create_proto(self) -> None:
        raise NotImplementedError("Barge-in config cannot be created")


def _as_section(value: Any, section_type: type, section_name: str) -> Any:
    """Build a section from a dict (YAML or status file), passing instances and None through.

    Raises:
        ValueError: If the section is not a mapping or has keys the section doesn't have.
    """
    if value is None or isinstance(value, section_type):
        return value
    if not isinstance(value, dict):
        raise ValueError(f"'{section_name}' should be a mapping but got {type(value).__name__}.")
    known_keys = set(section_type.__dataclass_fields__)
    if unknown_keys := sorted(set(value) - known_keys):
        raise ValueError(
            f"Unknown key(s) in '{section_name}': {', '.join(unknown_keys)}. "
            f"Expected: {', '.join(section_type.__dataclass_fields__)}."
        )
    try:
        return section_type(**value)
    except TypeError as e:
        raise ValueError(f"Invalid '{section_name}': {e}") from e


@register_resource("asr_settings")
@dataclass
class AsrSettings(YamlResource):
    """The voice channel's turn-taking: speech end delay and barge-in.

    Each section is pushed with its own voice channel command. A section that is left out
    uses the platform default, and removing one resets it.
    """

    speech_end_delay_ms: Optional[int]
    barge_in: Optional[BargeIn]

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        speech_end_delay_ms: Optional[int] = None,
        barge_in: Union[BargeIn, dict, None] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.speech_end_delay_ms = speech_end_delay_ms
        self.barge_in = _as_section(barge_in, BargeIn, "barge_in")

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "AsrSettings"]:
        """Parse the voice channel's turn-taking from a projection dict."""
        if "channels" not in projection:
            logger.debug("No read access to ASR settings - it will not be pulled.")
            return {}

        voice = projection.get("channels", {}).get("voice")
        if voice is None:
            return {}

        speech_end_delay_ms = None
        vad_config = voice.get("vadConfig")
        if vad_config and vad_config.get("speechEndWindowSeconds") is not None:
            speech_end_delay_ms = round(vad_config["speechEndWindowSeconds"] * 1000)

        barge_in = None
        barge_in_config = voice.get("bargeInConfig")
        if barge_in_config is not None:
            # The projection leaves out false values.
            barge_in = BargeIn(
                enabled=barge_in_config.get("enabled", False),
                allow_on_first_turn=barge_in_config.get("allowedFirstTurn", False),
                max_per_call=barge_in_config.get("maxPerCall"),
            )
        elif "bargeIn" in voice.get("asrSettings", {}):
            # Without a barge-in config the runtime still follows the legacy flag.
            barge_in = BargeIn(enabled=voice["asrSettings"]["bargeIn"])

        return {
            "asr_settings": cls(
                resource_id="asr_settings",
                name="asr_settings",
                speech_end_delay_ms=speech_end_delay_ms,
                barge_in=barge_in,
            )
        }

    @cached_property
    def file_path(self) -> str:
        return os.path.join("voice", "speech_recognition", "asr_settings.yaml")

    def to_yaml_dict(self) -> dict:
        output: dict[str, Any] = {}
        if self.speech_end_delay_ms is not None:
            output["speech_end_delay_ms"] = self.speech_end_delay_ms
        if self.barge_in:
            output["barge_in"] = self.barge_in.to_yaml_dict()
        return output

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "AsrSettings":
        return cls(
            resource_id=resource_id,
            name=name,
            speech_end_delay_ms=yaml_dict.get("speech_end_delay_ms"),
            barge_in=yaml_dict.get("barge_in"),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if self.speech_end_delay_ms is not None and not (
            SPEECH_END_DELAY_MS_MIN <= self.speech_end_delay_ms <= SPEECH_END_DELAY_MS_MAX
        ):
            raise ValueError(
                f"speech_end_delay_ms must be between {SPEECH_END_DELAY_MS_MIN} and "
                f"{SPEECH_END_DELAY_MS_MAX}."
            )
        if self.barge_in:
            self.barge_in.validate()

    @property
    def command_type(self) -> str:
        return "voice_asr_settings"

    def build_update_proto(self) -> Message:
        raise NotImplementedError("ASR settings are pushed section by section.")

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for ASR settings.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for ASR settings.")

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["AsrSettings"]
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Get the voice channel commands for the sections that changed.

        A changed section is updated and a removed one is reset.
        """
        updated: list[SubResource] = []
        deleted: list[SubResource] = []

        def _diff(attr: str, sub_resource_type: type[SubResource]) -> None:
            new_value = getattr(self, attr)
            old_value = getattr(old_resource, attr) if old_resource else None
            if new_value == old_value:
                return
            sub_resource = sub_resource_type(
                resource_id=self.resource_id, name=attr, **{attr: new_value}
            )
            if new_value is not None:
                updated.append(sub_resource)
            elif old_value is not None:
                deleted.append(sub_resource)

        _diff("speech_end_delay_ms", VoiceVadConfig)
        _diff("barge_in", VoiceBargeInConfig)

        old_barge_in = old_resource.barge_in if old_resource else None
        if (
            self.barge_in
            and old_barge_in
            and old_barge_in.max_per_call is not None
            and self.barge_in.max_per_call is None
        ):
            # Barge-in updates merge, so clearing a field takes a reset before the update.
            deleted.append(
                VoiceBargeInConfig(resource_id=self.resource_id, name="barge_in", barge_in=None)
            )

        return [], updated, deleted

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "voice", "speech_recognition", "asr_settings.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]
