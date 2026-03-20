"""Handling and managing Agent Studio Pronunciations (TTS Rules)

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.pronunciations_pb2 import (
    Pronunciations_CreatePronunciation,
    Pronunciations_DeletePronunciation,
    Pronunciations_UpdatePronunciation,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    _parse_multi_resource_path,
)


@dataclass
class Pronunciation(MultiResourceYamlResource):
    """Dataclass representing a TTS Rule"""

    regex: str
    replacement: str
    case_sensitive: bool
    language_code: str
    description: str
    position: int
    top_level_name: ClassVar[str] = "pronunciations"

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        regex: str = "",
        replacement: str = "",
        case_sensitive: bool = False,
        language_code: str = "",
        description: str = "",
        position: int = 0,
    ):
        self.resource_id = resource_id
        self.name = name
        self.regex = regex
        self.replacement = replacement
        self.case_sensitive = case_sensitive
        self.language_code = language_code
        self.description = description
        self.position = position

    @property
    def file_path(self) -> str:
        # pronunciation rules don't have names
        path_safe_name = utils.clean_name(str(self.position), lowercase=False)
        return os.path.join(
            "voice",
            "response_control",
            "pronunciations.yaml",
            self.top_level_name,
            path_safe_name,
        )

    def to_yaml_dict(self) -> dict:
        d = {
            "regex": self.regex,
            "replacement": self.replacement,
            "case_sensitive": self.case_sensitive,
            "language_code": self.language_code,
            "description": self.description,
        }
        return {k: v for k, v in d.items() if (v != "" or k == "replacement")}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "Pronunciation":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name", ""),
            regex=yaml_dict.get("regex", ""),
            replacement=yaml_dict.get("replacement", ""),
            case_sensitive=yaml_dict.get("case_sensitive", False),
            language_code=yaml_dict.get("language_code", ""),
            description=(yaml_dict.get("description") or "").strip(),
            position=kwargs.get("position", -1),
        )

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        return d

    @classmethod
    def read_from_file(cls, file_path: str) -> str:
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        resource_clean_name = segments[-1]
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)
        # list() preserves document order from the YAML file
        yaml_list = list(top_level_yaml_dict.get(top_level_name, []))

        if not isinstance(yaml_list, list):
            raise ValueError(f"Top level YAML data is not a list: {top_level_yaml_dict}")

        matching_resource = next(
            (r for i, r in enumerate(yaml_list) if i == int(resource_clean_name)),
            None,
        )
        if not matching_resource:
            raise FileNotFoundError(
                f"Resource with name {resource_clean_name} not found in {true_file_path}"
            )

        return utils.dump_yaml(matching_resource)

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "Pronunciation":
        """Read local resource and derive position from the item's place in the collection."""
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        resource_clean_name = segments[-1]
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)
        # list() preserves document order from the YAML file
        yaml_list = list(top_level_yaml_dict.get(top_level_name, []))

        position = 0
        contents = None
        for i, item in enumerate(yaml_list):
            if i == int(resource_clean_name):
                position = i
                contents = utils.dump_yaml(item)
                break

        if not contents:
            raise FileNotFoundError(
                f"Resource with name {resource_clean_name} not found in {true_file_path}"
            )

        content = cls.from_pretty(contents, file_path=file_path, **kwargs)
        try:
            yaml_dict = utils.load_yaml(content) or {}
        except Exception as e:
            raise ValueError(f"Error loading YAML file: {file_path}") from e

        return cls.from_yaml_dict(
            yaml_dict, resource_id=resource_id, name="", position=position, **kwargs
        )

    @property
    def command_type(self) -> str:
        return "pronunciation"

    @property
    def delete_command_type(self) -> str:
        return "pronunciations_delete_pronunciation"

    @property
    def create_command_type(self) -> str:
        return "pronunciations_create_pronunciation"

    @property
    def update_command_type(self) -> str:
        return "pronunciations_update_pronunciation"

    def build_create_proto(self) -> Pronunciations_CreatePronunciation:
        return Pronunciations_CreatePronunciation(
            id=self.resource_id,
            regex=self.regex,
            replacement=self.replacement,
            case_sensitive=self.case_sensitive,
            language_code=self.language_code,
            description=self.description,
            position=self.position,
            name=self.name,
        )

    def build_update_proto(self) -> Pronunciations_UpdatePronunciation:
        return Pronunciations_UpdatePronunciation(
            id=self.resource_id,
            regex=self.regex,
            replacement=self.replacement,
            case_sensitive=self.case_sensitive,
            language_code=self.language_code,
            description=self.description,
            position=self.position,
            name=self.name,
        )

    def build_delete_proto(self) -> Pronunciations_DeletePronunciation:
        return Pronunciations_DeletePronunciation(
            id=self.resource_id,
        )

    def validate(self, **kwargs) -> None:
        if not self.regex:
            raise ValueError("Regex pattern is required")

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Save the resource; pronunciations are matched by position (index), not by name."""
        content = self.to_pretty(**kwargs)
        if format:
            content = self.format_resource(content, file_name=str(self.position))
        file_path = self.get_path(base_path)

        yaml_content = utils.load_yaml(content) or {}
        true_file_path, segments = _parse_multi_resource_path(file_path)
        resource_clean_name = segments[-1]
        if not os.path.exists(true_file_path):
            if not save_to_cache:
                self.save_to_file(f"{self.top_level_name}: []", true_file_path)
            else:
                self._file_cache.setdefault(true_file_path, (0.0, {self.top_level_name: []}))

        top_level_yaml_dict = self._get_top_level_data(true_file_path)
        yaml_list = list(top_level_yaml_dict.get(self.top_level_name, []))
        if not isinstance(yaml_list, list):
            raise ValueError(f"Top level YAML data is not a list: {top_level_yaml_dict}")

        try:
            matching_idx = int(resource_clean_name)
        except ValueError:
            yaml_list.append(yaml_content)
        else:
            if matching_idx < len(yaml_list):
                # if index within list, assign the value to that index
                yaml_list[matching_idx] = yaml_content
            else:
                # otherwise, just append to the end
                yaml_list.append(yaml_content)

        top_level_yaml_dict[self.top_level_name] = yaml_list
        self._update_cache_after_write(true_file_path, top_level_yaml_dict)
        if not save_to_cache:
            self.save_to_file(utils.dump_yaml(top_level_yaml_dict), true_file_path)

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        """Delete the resource from the given file path."""
        true_file_path, segments = _parse_multi_resource_path(file_path)
        top_level_name = segments[0]
        if not os.path.exists(true_file_path):
            return
        top_level_yaml_dict = cls._get_top_level_data(true_file_path)
        resource_clean_name = segments[-1]
        yaml_list = top_level_yaml_dict.get(top_level_name, [])

        # Pronunciations use list index (not name/position) for identification
        try:
            matching_idx = int(resource_clean_name)
        except ValueError:
            return
        if matching_idx < 0 or matching_idx >= len(yaml_list):
            return
        del yaml_list[matching_idx]
        top_level_yaml_dict[top_level_name] = yaml_list

        cls._update_cache_after_write(true_file_path, top_level_yaml_dict)
        if not save_to_cache:
            cls.save_to_file(utils.dump_yaml(top_level_yaml_dict), true_file_path)

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        yaml_path = os.path.join(base_path, "voice", "response_control", "pronunciations.yaml")
        discovered: list[str] = []

        if not os.path.exists(yaml_path):
            return discovered

        yaml_dict = Pronunciation._get_top_level_data(yaml_path)
        # list() preserves document order from the YAML file
        items: list[dict] = list(yaml_dict.get("pronunciations", [])) if yaml_dict else []

        for i, item in enumerate(items):
            path_safe_name = utils.clean_name(str(i), lowercase=False)
            discovered.append(os.path.join(yaml_path, Pronunciation.top_level_name, path_safe_name))

        return discovered
