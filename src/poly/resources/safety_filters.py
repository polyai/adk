"""Handling and managing Agent Studio Safety Filter settings.

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import Optional

from google.protobuf.message import Message

from poly.handlers.protobuf.channels_pb2 import VOICE, Channel_UpdateSafetyFilters
from poly.handlers.protobuf.content_filter_settings_pb2 import (
    AzureContentFilter,
    AzureContentFilterCategory,
    ContentFilterSettings_UpdateContentFilterSettings,
)
from poly.resources.resource import ResourceMapping, YamlResource

VALID_PRECISIONS = {"loose", "medium", "strict"}
CATEGORIES = ("violence", "hate", "sexual", "self_harm")
DEFAULT_PRECISION = "medium"
_FILTER_TYPE = "azure"


@dataclass
class _SafetyFilterCategory:
    enabled: bool = False
    precision: str = DEFAULT_PRECISION

    def to_dict(self) -> dict:
        return {"enabled": self.enabled, "precision": self.precision}

    @classmethod
    def from_dict(cls, data: dict) -> "_SafetyFilterCategory":
        return cls(
            enabled=data.get("enabled", False),
            precision=data.get("precision", DEFAULT_PRECISION),
        )

    def to_proto(self) -> AzureContentFilterCategory:
        return AzureContentFilterCategory(
            is_active=self.enabled,
            precision=self.precision,
        )


def _parse_categories(raw: dict) -> dict:
    parsed = {}
    for cat in CATEGORIES:
        category = raw.get(cat, {})
        if isinstance(category, _SafetyFilterCategory):
            parsed[cat] = category
        elif isinstance(category, dict):
            parsed[cat] = _SafetyFilterCategory.from_dict(category)
        else:
            parsed[cat] = _SafetyFilterCategory()
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


class _BaseSafetyFilters(YamlResource):
    """Shared logic for project-level and channel-level safety filters."""

    enabled: bool = True
    filter_type: str = _FILTER_TYPE
    categories: dict = None

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        enabled: bool = True,
        filter_type: str = _FILTER_TYPE,
        categories: Optional[dict] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.enabled = enabled
        self.filter_type = filter_type
        self.categories = _parse_categories(categories or {})

    @classmethod
    def get_categories_from_azure_config(cls, azure_config: dict) -> dict:
        """Parse category data from the camelCase azure projection dict."""
        return {
            "violence": _SafetyFilterCategory(
                enabled=azure_config.get("violence", {}).get("isActive", False),
                precision=azure_config.get("violence", {}).get("precision", DEFAULT_PRECISION),
            ),
            "hate": _SafetyFilterCategory(
                enabled=azure_config.get("hate", {}).get("isActive", False),
                precision=azure_config.get("hate", {}).get("precision", DEFAULT_PRECISION),
            ),
            "sexual": _SafetyFilterCategory(
                enabled=azure_config.get("sexual", {}).get("isActive", False),
                precision=azure_config.get("sexual", {}).get("precision", DEFAULT_PRECISION),
            ),
            "self_harm": _SafetyFilterCategory(
                enabled=azure_config.get("selfHarm", {}).get("isActive", False),
                precision=azure_config.get("selfHarm", {}).get("precision", DEFAULT_PRECISION),
            ),
        }

    def to_yaml_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "type": self.filter_type,
            "categories": {cat: self.categories[cat].to_dict() for cat in CATEGORIES},
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "_BaseSafetyFilters":
        return cls(
            resource_id=resource_id,
            name=name,
            enabled=yaml_dict.get("enabled", True),
            filter_type=yaml_dict.get("type", _FILTER_TYPE),
            categories=yaml_dict.get("categories", {}),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        for cat_name, cat in self.categories.items():
            if cat.precision not in VALID_PRECISIONS:
                raise ValueError(
                    f"Invalid precision '{cat.precision}' for category '{cat_name}'. "
                    f"Must be one of: {', '.join(sorted(VALID_PRECISIONS))}"
                )

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for safety filters.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for safety filters.")


class SafetyFilters(_BaseSafetyFilters):
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

    @classmethod
    def from_projection_data(cls, data: dict) -> "SafetyFilters":
        """Instantiate from a raw contentFilterSettings projection dict."""
        azure = data.get("azureConfig", {})
        return cls(
            resource_id="safety_filters",
            name="safety_filters",
            enabled=not data.get("disabled", False),
            filter_type=data.get("type", _FILTER_TYPE),
            categories=cls.get_categories_from_azure_config(azure),
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "agent_settings", "safety_filters.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]


class VoiceSafetyFilters(_BaseSafetyFilters):
    """Resource class for managing voice channel safety filter settings."""

    @property
    def file_path(self) -> str:
        return os.path.join("voice", "safety_filters.yaml")

    @property
    def command_type(self) -> str:
        return "voice_safety_filters"

    @property
    def update_command_type(self) -> str:
        return "channel_update_safety_filters"

    def build_update_proto(self) -> Channel_UpdateSafetyFilters:
        return Channel_UpdateSafetyFilters(
            channel_type=VOICE,
            safety_filters=_build_update_content_filter_proto(
                self.enabled, self.filter_type, self.categories
            ),
        )

    def build_create_proto(self) -> Message:
        raise NotImplementedError("Create operation not supported for voice safety filters.")

    def build_delete_proto(self) -> Message:
        raise NotImplementedError("Delete operation not supported for voice safety filters.")

    @classmethod
    def from_projection_data(cls, data: dict) -> "VoiceSafetyFilters":
        """Instantiate from a raw voice channel safetyFilters projection dict."""
        azure = data.get("azureConfig", {})
        return cls(
            resource_id="voice_safety_filters",
            name="voice_safety_filters",
            enabled=not data.get("disabled", False),
            filter_type=data.get("type", _FILTER_TYPE),
            categories=cls.get_categories_from_azure_config(azure),
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, "voice", "safety_filters.yaml")
        if not os.path.exists(file_path):
            return []
        return [file_path]
