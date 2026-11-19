"""Handling and managing the voice channel's turn-taking

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any, Optional, Union

from google.protobuf.message import Message

from poly.handlers.protobuf.asr_pb2 import Asr
from poly.handlers.protobuf.channels_pb2 import (
    VADConfig,
    VoiceChannel_ResetAsrConfig,
    VoiceChannel_ResetBargeInConfig,
    VoiceChannel_ResetVadConfig,
    VoiceChannel_UpdateAsrConfig,
    VoiceChannel_UpdateBargeInConfig,
    VoiceChannel_UpdateVadConfig,
)
from poly.library import Library
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource

if TYPE_CHECKING:
    from poly.resources.channel_settings import VoiceLLMSettings

logger = logging.getLogger(__name__)

# Limits of Agent Studio's voice settings. The backend only checks for non-negative values.
SPEECH_END_DELAY_MS_MIN = 200
SPEECH_END_DELAY_MS_MAX = 1500


@dataclass
class ASRModel:
    """Representation of an ASR model, either by name or by provider and model."""

    # The actual ASR model provider and model name.
    provider: Optional[str] = None
    model: Optional[str] = None

    # The replacement name for Yaml output
    name: Optional[str] = None

    def to_yaml_dict(self) -> dict:
        output: dict[str, Any] = {}
        if self.provider is not None:
            output["provider"] = self.provider
        if self.model is not None:
            output["model"] = self.model
        if self.name is not None:
            output["name"] = self.name
        return output

    def validate(self, library: Optional[Library] = None):
        """Validate the ASR configuration against the model library, when there is one."""
        if self.name and (self.provider or self.model):
            raise ValueError("ASR model takes either name, or provider and model, not both.")
        if self.name:
            if library is None:
                logger.warning(f"Can't check ASR model '{self.name}' without the model library.")
                return
            raise ValueError(f"Unknown ASR model '{self.name}'.")
        if library and self.provider and self.model:
            if not library.get_asr_model_by_provider_and_model(self.provider, self.model):
                logger.warning(
                    f"ASR model {self.model} from '{self.provider}' isn't in the model library.",
                )


@dataclass
class ASRModelConfig(SubResource):
    """ASR model configuration for the voice channel's ASR."""

    asr_model: Optional[ASRModel] = None

    @property
    def command_type(self) -> str:
        return "voice_channel_asr_config"

    @property
    def update_command_type(self) -> str:
        return "voice_channel_update_asr_config"

    @property
    def delete_command_type(self) -> str:
        return "voice_channel_reset_asr_config"

    def build_update_proto(self) -> VoiceChannel_UpdateAsrConfig:
        if self.asr_model.name:
            raise ValueError(
                f"Unknown ASR model '{self.asr_model.name}'. Use a known model name, or a provider and model."
            )
        return VoiceChannel_UpdateAsrConfig(
            asr_config=Asr(provider_id=self.asr_model.provider, model_id=self.asr_model.model)
        )

    def build_delete_proto(self) -> VoiceChannel_ResetAsrConfig:
        return VoiceChannel_ResetAsrConfig()

    def build_create_proto(self) -> None:
        raise NotImplementedError("ASR config cannot be created")


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
    keep their stored value. Clearing a field therefore takes a reset followed by an update;
    that reset carries the section being updated. A reset without one would remove the
    section, which isn't allowed: the project would fall back to its legacy barge-in flag.
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
        if self.barge_in is None:
            raise NotImplementedError(
                "barge_in can't be removed from voice/speech_recognition/asr_settings.yaml. "
                "Set 'enabled: false' to turn barge-in off."
            )
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

    Each section is pushed with its own voice channel command. Removing speech_end_delay_ms
    resets it to the platform default. barge_in is always pulled and can't be removed.
    """

    asr_model: Optional[ASRModel]
    speech_end_delay_ms: Optional[int]
    barge_in: Optional[BargeIn]

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        asr_model: Union[ASRModel, dict, None] = None,
        speech_end_delay_ms: Optional[int] = None,
        barge_in: Union[BargeIn, dict, None] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.speech_end_delay_ms = speech_end_delay_ms
        self.barge_in = _as_section(barge_in, BargeIn, "barge_in")
        self.asr_model = _as_section(asr_model, ASRModel, "asr_model")

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

        # The projection leaves out false values.
        barge_in_config = voice.get("bargeInConfig")
        if barge_in_config is not None:
            barge_in = BargeIn(
                enabled=barge_in_config.get("enabled", False),
                allow_on_first_turn=barge_in_config.get("allowedFirstTurn", False),
                max_per_call=barge_in_config.get("maxPerCall"),
            )
        else:
            # Without a barge-in config the runtime uses the legacy flag. Its other fields
            # aren't stored, which the runtime treats as off and no limit.
            legacy_enabled = (voice.get("asrSettings") or {}).get("bargeIn", False)
            barge_in = BargeIn(enabled=legacy_enabled)

        if asr_config := voice.get("asrConfig"):
            asr_model = ASRModel(
                provider=asr_config.get("providerId"),
                model=asr_config.get("modelId"),
            )
        else:
            asr_model = None

        return {
            "asr_settings": cls(
                resource_id="asr_settings",
                name="asr_settings",
                asr_model=asr_model,
                speech_end_delay_ms=speech_end_delay_ms,
                barge_in=barge_in,
            )
        }

    @cached_property
    def file_path(self) -> str:
        return os.path.join("voice", "speech_recognition", "asr_settings.yaml")

    def to_yaml_dict(self) -> dict:
        output: dict[str, Any] = {}
        if self.asr_model:
            output["asr_model"] = self.asr_model.to_yaml_dict()
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
            asr_model=yaml_dict.get("asr_model"),
        )

    def validate(
        self,
        library: Library = None,
        voice_llm_settings: Optional["VoiceLLMSettings"] = None,
        **kwargs,
    ) -> None:
        if voice_llm_settings and voice_llm_settings.model_id and library:
            model = library.get_llm_model_by_id(voice_llm_settings.model_id)
            if model and model.speech_native:
                if self.asr_model is not None:
                    raise ValueError(
                        f"asr_model doesn't apply while the voice channel uses '{model.name}', which is end to end."
                    )
                if self.speech_end_delay_ms is not None:
                    raise ValueError(
                        f"speech_end_delay_ms doesn't apply while the voice channel uses '{model.name}', which is end to end."
                    )

        if self.speech_end_delay_ms is not None and not (
            SPEECH_END_DELAY_MS_MIN <= self.speech_end_delay_ms <= SPEECH_END_DELAY_MS_MAX
        ):
            raise ValueError(
                f"speech_end_delay_ms must be between {SPEECH_END_DELAY_MS_MIN} and "
                f"{SPEECH_END_DELAY_MS_MAX}."
            )
        if self.barge_in:
            self.barge_in.validate()

        if self.asr_model:
            self.asr_model.validate(library=library)

    @staticmethod
    def to_pretty_dict(
        d: dict,
        file_path: str = None,
        resource_mappings: list[ResourceMapping] = None,
        library: Library = None,
        **kwargs,
    ) -> dict:
        """Return dict with resource IDs replaced by names."""
        # Replace library resource IDs with names
        if library:
            if asr_model := d.get("asr_model"):
                asr_model_name = library.get_asr_model_by_provider_and_model(
                    asr_model.get("provider"), asr_model.get("model")
                )
                if asr_model_name:
                    d["asr_model"] = {"name": asr_model_name.name}
        return d

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        library: Library = None,
        **kwargs,
    ) -> dict:
        """Replace resource names with IDs in a parsed YAML dict."""

        if asr_model := yaml_dict.get("asr_model"):
            name = asr_model.get("name")
            has_ids = "provider" in asr_model or "model" in asr_model
            if name and not has_ids and library:
                if asr_model_obj := library.get_asr_model_by_name(name):
                    del asr_model["name"]
                    asr_model["provider"] = asr_model_obj.provider
                    asr_model["model"] = asr_model_obj.model

        return yaml_dict

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
        _diff("asr_model", ASRModelConfig)

        old_barge_in = old_resource.barge_in if old_resource else None
        if (
            self.barge_in
            and old_barge_in
            and old_barge_in.max_per_call is not None
            and self.barge_in.max_per_call is None
        ):
            # Barge-in updates merge, so clearing a field takes a reset before the update.
            deleted.append(
                VoiceBargeInConfig(
                    resource_id=self.resource_id, name="barge_in", barge_in=self.barge_in
                )
            )

        return [], updated, deleted

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "voice", "speech_recognition", "asr_settings.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]
