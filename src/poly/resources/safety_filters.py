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
PRECISION_MAPPING_INVERSE = {v: k for k, v in PRECISION_MAPPING.items()}
_AZURE_CATEGORY_KEYS = {
    "violence": "violence",
    "hate": "hate",
    "sexual": "sexual",
    "self_harm": "selfHarm",
}
# Const to auto-populate type for YAML roundtrip.
_FILTER_TYPE = "azure"


@dataclass
class SafetyFilterCategory:
    enabled: Optional[bool] = None
    precision: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SafetyFilterCategory":
        """Construct from a dict using internal (backend) field names.

        Missing or invalid values are stored as-is; validation is deferred
        to ``_BaseSafetyFilters.validate()``.
        """
        return cls(enabled=data.get("enabled"), precision=data.get("precision"))

    @classmethod
    def from_yaml_dict(cls, data: dict) -> "SafetyFilterCategory":
        """Construct from a YAML/UI-vocab dict (level: lenient/medium/strict).

        Missing or unrecognized values are passed through as None.
        """
        level = data.get("level")
        if level is None:
            precision = None
        else:
            # Pass through level even if not recognized, to pick up in validate()
            precision = PRECISION_MAPPING_INVERSE.get(level, level)
        return cls(enabled=data.get("enabled"), precision=precision)

    def to_yaml_dict(self) -> dict:
        """Serialize using YAML/UI vocab (level: lenient/medium/strict)."""
        return {
            "enabled": self.enabled,
            "level": PRECISION_MAPPING.get(self.precision, self.precision),
        }

    def to_proto(self) -> AzureContentFilterCategory:
        return AzureContentFilterCategory(
            is_active=self.enabled,
            precision=self.precision,
        )


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


@dataclass
class _BaseSafetyFilters(YamlResource):
    """Shared logic for project-level and channel-level safety filters."""

    _hide_global_enable: ClassVar[bool] = False

    enabled: bool = True
    filter_type: str = _FILTER_TYPE
    categories: Optional[dict] = None

    @staticmethod
    def _parse_categories(raw: dict) -> dict:
        """Parse raw category dicts into SafetyFilterCategory objects.

        Recognised keys are parsed into SafetyFilterCategory objects; missing
        recognised keys are stored as None.  Unrecognised keys are preserved as-is
        so that validate() can report them rather than silently dropping them.
        """
        parsed = {}
        for cat in _AZURE_CATEGORY_KEYS.keys():
            if cat not in raw:
                parsed[cat] = None
                continue
            category = raw[cat]
            if isinstance(category, SafetyFilterCategory):
                parsed[cat] = category
            elif isinstance(category, dict):
                parsed[cat] = SafetyFilterCategory.from_dict(category)
            else:
                parsed[cat] = None
        for cat in raw:
            if cat not in _AZURE_CATEGORY_KEYS:
                parsed[cat] = raw[cat]
        return parsed

    def __post_init__(self) -> None:
        if self.categories is not None:
            self.categories = self._parse_categories(self.categories)

        # Necessary to match UI of General Filters:
        # If enabled has not yet been set for a general filter,
        # then check if any category filters are set to true
        # and set global enabled to True.
        # Currently always set to true, so extra defensive here.
        if self._hide_global_enable and not self.enabled and self.categories:
            if any(
                isinstance(c, SafetyFilterCategory) and c.enabled is True
                for c in self.categories.values()
            ):
                self.enabled = True

    def to_yaml_dict(self) -> dict:
        """Builds YAML dict of the filters; some fields are present/absent
        Based on flag values.
        """
        categories_dict = {}
        for cat in _AZURE_CATEGORY_KEYS.keys():
            if self.categories[cat] is not None:
                # Convert SafetyFilterCategory to its YAML dict representation.
                categories_dict[cat] = self.categories[cat].to_yaml_dict()
            else:
                # Include the category with an empty dict if not present.
                categories_dict[cat] = {}
        yaml_dict = {
            "categories": categories_dict,
        }

        # If this flag is set as false, then 'enabled' is included in the YAML as the first entry.
        if not self._hide_global_enable:
            # Place enabled as the first key
            yaml_dict = {"enabled": self.enabled, **yaml_dict}
        return yaml_dict

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "_BaseSafetyFilters":
        raw_categories = yaml_dict.get("categories", {})
        translated = {
            cat_name: SafetyFilterCategory.from_yaml_dict(cat_data)
            if isinstance(cat_data, dict)
            else {}
            for cat_name, cat_data in raw_categories.items()
        }
        return cls(
            resource_id=resource_id,
            name=name,
            enabled=False if cls._hide_global_enable else yaml_dict.get("enabled"),
            filter_type=_FILTER_TYPE,
            categories=translated,
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if not self._hide_global_enable:
            if self.enabled is None:
                raise ValueError("Missing required field 'enabled'.")
            if not isinstance(self.enabled, bool):
                raise ValueError(
                    f"Invalid value {self.enabled!r} for 'enabled'. Must be true or false (unquoted)."
                )
        if self.categories is None:
            raise ValueError("Safety filter config is missing 'categories'.")

        valid_keys = sorted(_AZURE_CATEGORY_KEYS.keys())
        invalid_keys = sorted(k for k in self.categories if k not in _AZURE_CATEGORY_KEYS)
        if invalid_keys:
            raise ValueError(
                f"Unrecognised safety filter categories: {', '.join(f'{k!r}' for k in invalid_keys)}. "
                f"Accepted categories are: {', '.join(valid_keys)}"
            )

        for cat in _AZURE_CATEGORY_KEYS:
            if cat not in self.categories or self.categories[cat] is None:
                raise ValueError(
                    f"Missing required safety filter category '{cat}'. "
                    f"All of {', '.join(valid_keys)} must be provided."
                )

        for cat_name, cat in self.categories.items():
            if cat.enabled is None:
                raise ValueError(
                    f"Missing required field 'enabled' for safety filter category '{cat_name}'."
                )
            if not isinstance(cat.enabled, bool):
                raise ValueError(
                    f"Invalid value '{cat.enabled}' for 'enabled' in category '{cat_name}'. "
                    f"Must be true or false."
                )
            if cat.precision is None:
                raise ValueError(
                    f"Missing required field 'level' for safety filter category '{cat_name}'."
                )
            if cat.precision not in PRECISION_MAPPING:
                valid_levels = sorted(PRECISION_MAPPING.values())
                raise ValueError(
                    f"Invalid level set '{cat.precision}' for category '{cat_name}'. "
                    f"Must be one of: {', '.join(valid_levels)}"
                )

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for safety filters.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for safety filters.")


@dataclass
class GeneralSafetyFilters(_BaseSafetyFilters):
    """Resource class for managing general (project-level) safety filter settings."""

    _hide_global_enable: ClassVar[bool] = True  # enabled derived from categories

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
