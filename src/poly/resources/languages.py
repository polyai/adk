"""Handling and managing Agent Studio Config

Copyright PolyAI Limited
"""

from dataclasses import dataclass
import os
from typing import ClassVar

from poly.handlers.protobuf.languages_pb2 import (
    Languages_AddLanguage,
    Languages_DeleteLanguage,
    Languages_UpdateDefaultLanguage,
)

from poly.resources.resource import MultiResourceYamlResource, ResourceMapping

import poly.resources.resource_utils as utils


@dataclass
class Language(MultiResourceYamlResource):
    """Dataclass representing an Agent Studio Language"""

    is_default: bool = False
    top_level_name: ClassVar[str] = "languages"
    resource_key: ClassVar[str] = "language_code"

    def to_yaml_dict(self) -> dict:
        yaml_dict = {
            "language_code": self.name,
        }
        if self.is_default:
            yaml_dict["is_default"] = self.is_default
        return yaml_dict

    @classmethod
    def from_yaml_dict(cls, yaml_dict: dict, resource_id: str, name: str, **kwargs) -> "Language":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("language_code", name),
            is_default=yaml_dict.get("is_default", False),
        )

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join("agent_settings", "languages.yaml", self.top_level_name, path_safe_name)

    @property
    def command_type(self):
        return "language"

    @property
    def create_command_type(self):
        return "languages_add_language"

    @property
    def update_command_type(self):
        return "languages_update_default_language"

    @property
    def delete_command_type(self):
        return "languages_delete_language"

    def build_update_proto(self):
        return Languages_UpdateDefaultLanguage(
            language_code=self.name,
        )

    def build_delete_proto(self) -> Languages_DeleteLanguage:
        return Languages_DeleteLanguage(
            code=self.name,
        )

    def build_create_proto(self) -> Languages_AddLanguage:
        return Languages_AddLanguage(
            code=self.name,
        )

    def validate(self, resource_mappings: list[ResourceMapping], **kwargs):
        for resource in resource_mappings:
            if (
                resource.resource_type == Language
                and resource.resource_id != self.resource_id
                and resource.resource_name == self.name
            ):
                raise ValueError(f"Language {self.name} already exists")

    @classmethod
    def validate_collection(cls, resources: dict[str, "Language"]) -> None:
        default_names = [v.name for v in resources.values() if v.is_default]
        if len(default_names) != 1:
            raise ValueError(
                f"Multiple or zero default variants detected: {default_names}. "
                "One variant must be set as default."
            )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        languages_dict = os.path.join(base_path, "agent_settings", "languages.yaml")
        discovered_languages: list[str] = []

        if not os.path.exists(languages_dict):
            return discovered_languages

        yaml_data = Language._get_top_level_data(languages_dict)
        languages: list[str] = yaml_data.get("languages", []) if yaml_data else []

        for language_dict in languages:
            language_name = language_dict.get(Language.resource_key)

            if not language_name:
                continue
            path_safe_name = utils.clean_name(language_name, lowercase=False)
            discovered_languages.append(
                os.path.join(languages_dict, Language.top_level_name, path_safe_name)
            )

        return discovered_languages
