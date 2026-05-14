"""Handling and managing Agent Studio Phrase Filters (Stop Keywords)

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.stop_keywords_pb2 import (
    StopKeyword_Create,
    StopKeyword_Delete,
    StopKeyword_Update,
    StopKeywordReferences,
)
from poly.resources.function import Function
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping


@dataclass
class PhraseFilter(MultiResourceYamlResource):
    """Dataclass representing an Agent Studio Phrase Filter (Stop Keyword)"""

    description: str
    regular_expressions: list[str]
    say_phrase: bool
    language_code: str
    function: Optional[str] = None
    top_level_name: ClassVar[str] = "phrase_filtering"

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        name: str = "",
        description: str = "",
        regular_expressions: Optional[list[str]] = None,
        say_phrase: bool = False,
        language_code: str = "",
        function: Optional[str] = None,
    ):
        self.resource_id = resource_id
        self.name = name or ""
        self.description = description
        self.regular_expressions = regular_expressions if regular_expressions is not None else []
        self.say_phrase = say_phrase
        self.language_code = language_code
        self.function = function

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "voice",
            "response_control",
            "phrase_filtering.yaml",
            self.top_level_name,
            path_safe_name,
        )

    def to_yaml_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "regular_expressions": self.regular_expressions,
            "say_phrase": self.say_phrase,
            "language_code": self.language_code,
            "function": self.function,
        }
        return {k: v for k, v in d.items() if v != "" and v is not None}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "PhraseFilter":
        return cls(
            resource_id=resource_id,
            name=(yaml_dict.get("name") or name or ""),
            description=(yaml_dict.get("description") or "").strip(),
            regular_expressions=yaml_dict.get("regular_expressions", []),
            say_phrase=yaml_dict.get("say_phrase", False),
            language_code=yaml_dict.get("language_code", ""),
            function=yaml_dict.get("function"),
        )

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Replace function ID with human-readable function name."""
        function_id = d.get("function")
        if function_id:
            for resource in resource_mappings or []:
                if (
                    resource.resource_id == function_id
                    and resource.resource_type == Function
                    and resource.flow_name is None
                ):
                    d["function"] = resource.resource_name
                    break
        return d

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Replace function name with ID in a parsed YAML dict."""
        function_name = yaml_dict.get("function")
        if function_name:
            for resource in resource_mappings or []:
                if (
                    resource.resource_name == function_name
                    and resource.resource_id != function_name
                    and resource.resource_type == Function
                ):
                    yaml_dict["function"] = resource.resource_id
                    break
        return yaml_dict

    @classmethod
    def from_pretty(
        cls, contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace function name with ID. Returns original contents on invalid YAML."""
        try:
            yaml_dict = utils.load_yaml(contents) or {}
        except Exception:
            return contents
        yaml_dict = cls.from_pretty_dict(yaml_dict, resource_mappings=resource_mappings, **kwargs)
        return utils.dump_yaml(yaml_dict)

    @property
    def command_type(self) -> str:
        return "stop_keywords"

    @property
    def delete_command_type(self) -> str:
        return "stop_keywords_delete"

    @property
    def create_command_type(self) -> str:
        return "stop_keywords_create"

    @property
    def update_command_type(self) -> str:
        return "stop_keywords_update"

    def build_create_proto(self) -> StopKeyword_Create:
        return StopKeyword_Create(
            id=self.resource_id,
            title=self.name,
            description=self.description,
            regular_expressions=self.regular_expressions,
            say_phrase=self.say_phrase,
            references=StopKeywordReferences(
                globalFunctions={self.function: True} if self.function else {}
            ),
            language_code=self.language_code,
        )

    def build_update_proto(self) -> StopKeyword_Update:
        return StopKeyword_Update(
            id=self.resource_id,
            title=self.name,
            description=self.description,
            regular_expressions=self.regular_expressions,
            say_phrase=self.say_phrase,
            language_code=self.language_code,
            references=StopKeywordReferences(
                globalFunctions={self.function: True} if self.function else {}
            ),
        )

    def build_delete_proto(self) -> StopKeyword_Delete:
        return StopKeyword_Delete(
            id=self.resource_id,
        )

    def validate(self, **kwargs) -> None:
        if not self.name:
            raise ValueError("Name is required")
        if not self.regular_expressions:
            raise ValueError("At least one regular expression is required")

        resource_mappings = kwargs.get("resource_mappings") or {}
        if self.function:
            is_valid = any(
                r.resource_id == self.function
                and r.flow_name is None
                and r.resource_type is Function
                for r in resource_mappings
            )
            if not is_valid:
                raise ValueError(f"Invalid function(s): {self.function}.")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        yaml_path = os.path.join(base_path, "voice", "response_control", "phrase_filtering.yaml")
        discovered: list[str] = []

        if not os.path.exists(yaml_path):
            return discovered

        yaml_dict = PhraseFilter._get_top_level_data(yaml_path)
        filters: list[dict] = yaml_dict.get("phrase_filtering", []) if yaml_dict else []

        for pf in filters:
            name = pf.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered.append(os.path.join(yaml_path, PhraseFilter.top_level_name, path_safe_name))

        return discovered
