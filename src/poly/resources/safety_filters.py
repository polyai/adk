"""Handling and managing Agent Studio Safety Filter settings.

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

from google.protobuf.message import Message

from poly.handlers.protobuf.channels_pb2 import Channel_UpdateSafetyFilters, ChannelType
from poly.handlers.protobuf.content_filter_settings_pb2 import (
    AzureContentFilter,
    AzureContentFilterCategory,
    ContentFilterSettings_UpdateContentFilterSettings,
)
from poly.resources.resource import ResourceMapping, YamlResource

PRECISION_MAPPING = {"LOOSE": "lenient", "MEDIUM": "medium", "STRICT": "strict"}
_AZURE_CATEGORY_KEYS = {
    "violence": "violence",
    "hate": "hate",
    "sexual": "sexual",
    "self_harm": "selfHarm",
}


@dataclass
class _SafetyFilterCategory:
    enabled: bool
    precision: str

    def to_dict(self) -> dict:
        # Handle the mapping between UI terminology and backend terms.
        ui_precision_phrase = PRECISION_MAPPING[self.precision]
        return {"enabled": self.enabled, "level": ui_precision_phrase}

    @classmethod
    def from_dict(cls, data: dict) -> "_SafetyFilterCategory":
        for required in ("enabled", "level"):
            if required not in data:
                raise ValueError(
                    f"Missing required field '{required}' in safety filter category config."
                )
        level = data["level"]
        backend_precision_phrase = [k for k, v in PRECISION_MAPPING.items() if v == level]
        if not backend_precision_phrase:
            valid_levels = ", ".join(sorted(PRECISION_MAPPING.values()))
            raise ValueError(f"Invalid level '{level}'. Must be one of: {valid_levels}")

        return cls(
            enabled=data["enabled"],
            precision=backend_precision_phrase[0],
        )

    def to_proto(self) -> AzureContentFilterCategory:
        return AzureContentFilterCategory(
            is_active=self.enabled,
            precision=self.precision,
        )


def _parse_categories(raw: dict) -> dict:
    parsed = {}
    for cat in _AZURE_CATEGORY_KEYS.keys():
        if cat not in raw:
            raise ValueError(
                f"Missing required safety filter category '{cat}'. "
                f"All of {', '.join(_AZURE_CATEGORY_KEYS.keys())} must be provided."
            )
        category = raw[cat]
        if isinstance(category, _SafetyFilterCategory):
            parsed[cat] = category
        elif isinstance(category, dict):
            parsed[cat] = _SafetyFilterCategory.from_dict(category)
        else:
            raise ValueError(
                f"Safety filter category '{cat}' must be a dict, got {type(category).__name__}."
            )
    return parsed


def _build_azure_config(categories: dict) -> AzureContentFilter:
    return AzureContentFilter(
        violence=categories["violence"].to_proto(),
        hate=categories["hate"].to_proto(),
        sexual=categories["sexual"].to_proto(),
        self_harm=categories["self_harm"].to_proto(),
    )


def _build_update_content_filter_proto(
    enabled: bool, filter_type: str, categories: dict
) -> ContentFilterSettings_UpdateContentFilterSettings:
    return ContentFilterSettings_UpdateContentFilterSettings(
        type=filter_type,
        azure_config=_build_azure_config(categories),
        disabled=not enabled,
    )


def parse_categories_from_azure_config(azure_config: dict) -> dict:
    """Parse category data from a camelCase azure projection dict."""
    parsed = {}
    for cat, proj_key in _AZURE_CATEGORY_KEYS.items():
        if proj_key not in azure_config:
            raise ValueError(
                f"Missing required safety filter category '{proj_key}' in azure config."
            )
        category_data = azure_config[proj_key]
        if not isinstance(category_data, dict):
            raise ValueError(
                f"Safety filter category '{proj_key}' must be a dict, got "
                f"{type(category_data).__name__}."
            )
        for required in ("isActive", "precision"):
            if required not in category_data:
                raise ValueError(
                    f"Missing required field '{required}' for safety filter category "
                    f"'{proj_key}' in azure config."
                )
        parsed[cat] = _SafetyFilterCategory(
            enabled=category_data["isActive"],
            precision=category_data["precision"],
        )
    return parsed


@dataclass
class _BaseSafetyFilters(YamlResource):
    """Shared logic for project-level and channel-level safety filters."""

    enabled: bool = True
    filter_type: str = "azure"
    categories: Optional[dict] = None

    def __post_init__(self) -> None:
        """Parse raw category dicts into _SafetyFilterCategory objects."""
        if self.categories is None:
            return
        self.categories = _parse_categories(self.categories)

    def to_yaml_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "type": self.filter_type,
            "categories": {
                cat: self.categories[cat].to_dict() for cat in _AZURE_CATEGORY_KEYS.keys()
            },
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "_BaseSafetyFilters":
        for required in ("enabled", "type", "categories"):
            if required not in yaml_dict:
                raise ValueError(f"Missing required field '{required}' in safety filter config.")
        return cls(
            resource_id=resource_id,
            name=name,
            enabled=yaml_dict["enabled"],
            filter_type=yaml_dict["type"],
            categories=yaml_dict["categories"],
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        valid_precisions = PRECISION_MAPPING.keys()  # LOOSE, MEDIUM, STRICT
        valid_levels = PRECISION_MAPPING.values()  # lenient, medium, strict (for error message)
        for cat_name, cat in self.categories.items():
            if cat.precision not in valid_precisions:
                raise ValueError(
                    f"Invalid level set '{cat.precision}' for category '{cat_name}'. "
                    f"Must be one of: {', '.join(sorted(valid_levels))}"
                )

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for safety filters.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for safety filters.")


@dataclass
class GeneralSafetyFilters(_BaseSafetyFilters):
    """Resource class for managing general (project-level) safety filter settings."""

    @property
    def file_path(self) -> str:
        return os.path.join("agent_settings", "safety_filters.yaml")

    @property
    def command_type(self) -> str:
        return "content_filter_settings"

    @property
    def update_command_type(self) -> str:
        return "update_content_filter_settings"

    def build_update_proto(self) -> ContentFilterSettings_UpdateContentFilterSettings:
        return _build_update_content_filter_proto(self.enabled, self.filter_type, self.categories)

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "agent_settings", "safety_filters.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]


@dataclass
class ChannelSafetyFilters(_BaseSafetyFilters):
    """Base class for channel-level safety filter settings. Subclass for voice/chat."""

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"

    @property
    def file_path(self) -> str:
        """Get the file path for the channel safety filters resource."""
        return os.path.join(self.channel_subpath, "safety_filters.yaml")

    @property
    def command_type(self) -> str:
        """Get the command type for the resource."""
        return f"{self.channel_subpath}_safety_filters"

    @property
    def update_command_type(self) -> str:
        """Get the command type for updating the resource."""
        return "channel_update_safety_filters"

    def build_update_proto(self) -> Channel_UpdateSafetyFilters:
        """Create a proto for updating the resource."""
        return Channel_UpdateSafetyFilters(
            channel_type=self.channel_type,
            safety_filters=_build_update_content_filter_proto(
                self.enabled, self.filter_type, self.categories
            ),
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for channel safety filters.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for channel safety filters.")

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        file_path = os.path.join(base_path, cls.channel_subpath, "safety_filters.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]


@dataclass
class VoiceSafetyFilters(ChannelSafetyFilters):
    """Voice channel safety filter settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.VOICE
    channel_subpath: ClassVar[str] = "voice"


@dataclass
class ChatSafetyFilters(ChannelSafetyFilters):
    """Chat (web chat) channel safety filter settings."""

    channel_type: ClassVar[ChannelType] = ChannelType.WEB_CHAT
    channel_subpath: ClassVar[str] = "chat"
