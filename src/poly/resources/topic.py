"""Handling and managing an Agent Studio KB Topic

Copyright PolyAI Limited
"""

import os
import re
from dataclasses import dataclass
from functools import cached_property

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.knowledge_base_pb2 import (
    ExampleQueries,
    KnowledgeBase_CreateTopic,
    KnowledgeBase_DeleteTopic,
    KnowledgeBase_UpdateTopic,
)
from poly.resources.resource import ResourceMapping, YamlResource

FUNCTION_REGEX = re.compile(r"{{fn:([\w-]+)}}")
FLOW_FUNCTION_REGEX = re.compile(r"{{ft:([\w-]+)}}")


TOPIC_REFERENCES = ["global_functions", "sms", "handoff", "attributes", "variables"]


@dataclass
class Topic(YamlResource):
    """Dataclass representing an Agent Studio KB Topic"""

    actions: str
    content: str
    example_queries: list[str]
    enabled: bool

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        actions: str,
        content: str,
        example_queries: list[str],
        enabled: bool = True,
    ):
        self.resource_id = resource_id
        self.name = name
        self.actions = actions
        self.content = content
        self.example_queries = example_queries or []
        self.enabled = enabled

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the topic."""
        file_name = f"{self.name}.yaml"
        return os.path.join("topics", file_name)

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "enabled": self.enabled,
            "actions": self.actions,
            "content": self.content,
            "example_queries": self.example_queries,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "YamlResource":
        """Create an instance from YAML data and identity fields."""
        return cls(
            resource_id=resource_id,
            name=name,
            actions=yaml_dict.get("actions", ""),
            content=yaml_dict.get("content", ""),
            example_queries=yaml_dict.get("example_queries", []),
            enabled=yaml_dict.get("enabled", True),
        )

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["actions"] = utils.replace_resource_ids_with_names(d["actions"], resource_mappings or [])
        d["content"] = utils.replace_resource_ids_with_names(d["content"], resource_mappings or [])
        return d

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the topic resource."""

        references = utils.get_references_from_prompt(
            self.actions + self.content, TOPIC_REFERENCES, raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

        # limit example queries to 20
        if len(self.example_queries) > 20:
            raise ValueError("Example queries must be less than 20")

    def build_update_proto(self) -> KnowledgeBase_UpdateTopic:
        """Create a proto for updating the resource."""
        # Compute references to other resources
        references = utils.get_references_from_prompt(self.actions + self.content, TOPIC_REFERENCES)

        return KnowledgeBase_UpdateTopic(
            id=self.resource_id,
            name=self.name,
            actions=self.actions,
            content=self.content,
            example_queries=ExampleQueries(queries=[q for q in self.example_queries]),
            references=references,
            is_active=self.enabled,
        )

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""

        return KnowledgeBase_DeleteTopic(
            id=self.resource_id,
        )

    def build_create_proto(self) -> KnowledgeBase_CreateTopic:
        """Create a proto for creating the resource."""
        # Compute references to other resources
        references = utils.get_references_from_prompt(self.actions + self.content, TOPIC_REFERENCES)

        return KnowledgeBase_CreateTopic(
            id=self.resource_id,
            name=self.name,
            actions=self.actions,
            content=self.content,
            example_queries=ExampleQueries(queries=[q for q in self.example_queries]),
            references=references,
            is_active=self.enabled,
        )

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "topic"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        topics_path = os.path.join(base_path, "topics")
        discovered_topics: list[str] = []

        if not os.path.exists(topics_path):
            return discovered_topics

        for dirpath, _, filenames in os.walk(topics_path):
            for file_name in filenames:
                if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                    file_path = os.path.join(dirpath, file_name)
                    discovered_topics.append(file_path)

        return discovered_topics
