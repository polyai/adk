"""Handling and managing Agent Studio Language Configuration

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar

from google.protobuf.message import Message

from poly.handlers.protobuf.languages_pb2 import (
    Languages_AddLanguage,
    Languages_DeleteLanguage,
    Languages_UpdateDefaultLanguage,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    _parse_multi_resource_path,
)

import poly.resources.resource_utils as utils

LANGUAGES_FILE = os.path.join("agent_settings", "languages.yaml")
EMPTY_LANGUAGES = {"default_language": None, "additional_languages": []}


def _ensure_languages_file(
    cls: type[MultiResourceYamlResource], true_file_path: str, save_to_cache: bool
) -> None:
    """Create the languages file or seed the cache if it doesn't exist."""
    if os.path.exists(true_file_path):
        return
    if save_to_cache:
        cls._file_cache.setdefault(true_file_path, (0.0, dict(EMPTY_LANGUAGES)))
    else:
        cls.save_to_file(utils.dump_yaml(dict(EMPTY_LANGUAGES)), true_file_path)


def _write_languages(
    cls: type[MultiResourceYamlResource],
    true_file_path: str,
    top_level: dict,
    save_to_cache: bool,
) -> None:
    """Update cache and optionally flush to disk."""
    cls._update_cache_after_write(true_file_path, top_level)
    if not save_to_cache:
        cls.save_to_file(utils.dump_yaml(top_level), true_file_path)


@dataclass
class DefaultLanguage(MultiResourceYamlResource):
    """Resource representing the default language."""

    top_level_name: ClassVar[str] = "default_language"
    _singleton: ClassVar[bool] = True

    @property
    def file_path(self) -> str:
        return os.path.join(LANGUAGES_FILE, self.top_level_name)

    def to_yaml_dict(self) -> dict:
        return {"language_code": self.name}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "DefaultLanguage":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("language_code", name),
        )

    @property
    def command_type(self) -> str:
        return "languages_update_default_language"

    def build_update_proto(self) -> Languages_UpdateDefaultLanguage:
        return Languages_UpdateDefaultLanguage(language_code=self.name)

    def build_create_proto(self) -> Message:
        raise NotImplementedError

    def build_delete_proto(self) -> Message:
        raise NotImplementedError

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Save the default language as a bare string value."""
        true_file_path = os.path.join(base_path, LANGUAGES_FILE)
        _ensure_languages_file(type(self), true_file_path, save_to_cache)
        top_level = self._get_top_level_data(true_file_path)
        top_level["default_language"] = self.name
        _write_languages(type(self), true_file_path, top_level, save_to_cache)

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        true_file_path, _ = _parse_multi_resource_path(file_path)
        top_level = cls._get_top_level_data(true_file_path)
        value = top_level.get("default_language")
        if not value:
            raise FileNotFoundError(f"default_language not found in {true_file_path}")
        return utils.dump_yaml({"language_code": value})

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        true_file_path, _ = _parse_multi_resource_path(file_path)
        if not os.path.exists(true_file_path):
            return
        top_level = cls._get_top_level_data(true_file_path)
        top_level["default_language"] = None
        _write_languages(cls, true_file_path, top_level, save_to_cache)

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover the default language resource."""
        file_path = os.path.join(base_path, LANGUAGES_FILE)
        if not os.path.exists(file_path):
            return []
        top_level = DefaultLanguage._get_top_level_data(file_path)
        if top_level.get("default_language"):
            return [os.path.join(file_path, "default_language")]
        return []

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if not self.name:
            raise ValueError("Default language code is required.")
        if resource_mappings:
            additional_codes = [
                m.resource_name for m in resource_mappings if m.resource_type == AdditionalLanguage
            ]
            if self.name in additional_codes:
                raise ValueError(
                    f"Default language '{self.name}' also appears in additional languages."
                )


@dataclass
class AdditionalLanguage(MultiResourceYamlResource):
    """Resource representing an additional language."""

    top_level_name: ClassVar[str] = "additional_languages"

    @property
    def file_path(self) -> str:
        return os.path.join(LANGUAGES_FILE, self.top_level_name, self.name)

    def to_yaml_dict(self) -> dict:
        return {"language_code": self.name}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "AdditionalLanguage":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("language_code", name),
        )

    @property
    def command_type(self) -> str:
        return "languages_add_language"

    @property
    def create_command_type(self) -> str:
        return "languages_add_language"

    @property
    def delete_command_type(self) -> str:
        return "languages_delete_language"

    def build_create_proto(self) -> Languages_AddLanguage:
        return Languages_AddLanguage(code=self.name)

    def build_delete_proto(self) -> Languages_DeleteLanguage:
        return Languages_DeleteLanguage(code=self.name)

    def build_update_proto(self) -> Message:
        raise NotImplementedError

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Save this language into the additional_languages list."""
        true_file_path = os.path.join(base_path, LANGUAGES_FILE)
        _ensure_languages_file(type(self), true_file_path, save_to_cache)
        top_level = self._get_top_level_data(true_file_path)
        additional = top_level.get("additional_languages") or []
        if self.name not in additional:
            additional.append(self.name)
        top_level["additional_languages"] = additional
        _write_languages(type(self), true_file_path, top_level, save_to_cache)

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        true_file_path, segments = _parse_multi_resource_path(file_path)
        resource_name = segments[-1]
        top_level = cls._get_top_level_data(true_file_path)
        additional = top_level.get("additional_languages") or []
        if resource_name not in additional:
            raise FileNotFoundError(f"Language {resource_name} not found in {true_file_path}")
        return utils.dump_yaml({"language_code": resource_name})

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        true_file_path, segments = _parse_multi_resource_path(file_path)
        resource_name = segments[-1]
        if not os.path.exists(true_file_path):
            return
        top_level = cls._get_top_level_data(true_file_path)
        additional = top_level.get("additional_languages") or []
        top_level["additional_languages"] = [lang for lang in additional if lang != resource_name]
        _write_languages(cls, true_file_path, top_level, save_to_cache)

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover additional language resources."""
        file_path = os.path.join(base_path, LANGUAGES_FILE)
        if not os.path.exists(file_path):
            return []
        top_level = AdditionalLanguage._get_top_level_data(file_path)
        additional = top_level.get("additional_languages") or []
        return [os.path.join(file_path, "additional_languages", lang) for lang in additional]

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        if not self.name:
            raise ValueError("Language code is required.")
        if resource_mappings:
            all_language_codes = [
                m.resource_name
                for m in resource_mappings
                if m.resource_type in (DefaultLanguage, AdditionalLanguage)
                and m.resource_id != self.resource_id
            ]
            if self.name in all_language_codes:
                raise ValueError(f"Duplicate language code: '{self.name}'.")
