"""Handling and managing an Agent Studio KB Topic

Copyright PolyAI Limited
"""

import logging
import os
import re
from dataclasses import dataclass, field
from functools import cached_property
from typing import Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.knowledge_base_pb2 import (
    ExampleQueries,
    KnowledgeBase_CreateTopic,
    KnowledgeBase_DeleteTopic,
    KnowledgeBase_SetTopicTags,
    KnowledgeBase_UpdateTopic,
)
from poly.resources.resource import ResourceMapping, SubResource, YamlResource, register_resource

logger = logging.getLogger(__name__)

FUNCTION_REGEX = re.compile(r"{{fn:([\w-]+)}}")
FLOW_FUNCTION_REGEX = re.compile(r"{{ft:([\w-]+)}}")


TOPIC_REFERENCES = ["global_functions", "sms", "handoff", "attributes", "variables", "translations"]


@dataclass
class TopicTags(SubResource):
    """Tags on an existing topic.

    update_topic carries no tags, so changing them takes a separate set_topic_tags command.
    """

    tags: list[str] = field(default_factory=list)

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "topic_tags"

    @property
    def update_command_type(self) -> str:
        """Get the command type for setting the tags."""
        return "set_topic_tags"

    def build_update_proto(self) -> KnowledgeBase_SetTopicTags:
        """Create a proto for setting the tags."""
        return KnowledgeBase_SetTopicTags(id=self.resource_id, tags=list(self.tags))

    def build_create_proto(self) -> None:
        """Topic tags are created with their topic, never on their own."""
        raise NotImplementedError("Topic tags cannot be created")

    def build_delete_proto(self) -> None:
        """Topic tags are cleared by setting an empty list, never deleted."""
        raise NotImplementedError("Topic tags cannot be deleted")


@register_resource("topics")
@dataclass
class Topic(YamlResource):
    """Dataclass representing an Agent Studio KB Topic"""

    actions: str
    content: str
    example_queries: list[str]
    enabled: bool
    tags: list[str]

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        actions: str,
        content: str,
        example_queries: list[str],
        enabled: bool = True,
        tags: Optional[list[str]] = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.actions = actions
        self.content = content
        self.example_queries = example_queries or []
        self.enabled = enabled
        self.tags = [] if tags is None else tags

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "Topic"]:
        """Parse topics from a projection dict."""
        topics = {}
        topics_projection = (
            projection.get("knowledgeBase", {}).get("topics", {}).get("entities", {})
        )
        if "knowledgeBase" not in projection or any(
            "content" not in topic for topic in topics_projection.values()
        ):
            logger.debug("No read access to the knowledge base - it will not be pulled.")
            return {}

        for topic_id, topic in topics_projection.items():
            example_queries = topic.get("exampleQueries", [])
            queries = [
                example_queries["query"]
                for example_queries in example_queries
                if "query" in example_queries
            ]
            topics[topic_id] = cls(
                resource_id=topic_id,
                name=topic["name"],
                actions=topic["actions"],
                content=topic["content"],
                example_queries=queries,
                enabled=topic.get("isActive", True),
                tags=list(topic.get("tags") or []),
            )
        return topics

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the topic."""
        file_name = f"{utils.clean_name(self.name)}.yaml"
        return os.path.join("topics", file_name)

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization.

        tags is written only when the topic has some, so untagged topic files stay as they were.
        """
        output = {
            "name": self.name,
            "enabled": self.enabled,
        }
        if self.tags:
            output["tags"] = self.tags
        output["actions"] = self.actions
        output["content"] = self.content
        output["example_queries"] = self.example_queries
        return output

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "YamlResource":
        """Create an instance from YAML data and identity fields."""
        resolved_name = yaml_dict.get("name") or name
        tags = yaml_dict.get("tags")
        if isinstance(tags, list):
            # Non-strings are left for check_yaml_field_types to report
            tags = [tag.strip() if isinstance(tag, str) else tag for tag in tags]
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            actions=yaml_dict.get("actions", ""),
            content=yaml_dict.get("content", ""),
            example_queries=yaml_dict.get("example_queries", []),
            enabled=yaml_dict.get("enabled", True),
            tags=tags,
        )

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "Topic":
        """Read a local YAML resource, validating name against filename."""
        topic: Topic = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )

        file_name = os.path.splitext(os.path.basename(file_path))[0]
        expected_file_name = utils.clean_name(topic.name)

        if file_name != expected_file_name:
            raise ValueError(
                f"Topic name '{topic.name}' in file {file_name}.yaml does not match "
                f"expected filename: {expected_file_name}.yaml"
            )
        return topic

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

        self._validate_tags()

    def _validate_tags(self) -> None:
        """Validate the topic's tags.

        Length is not checked: Agent Studio's tag input limits it, but imported topics can
        carry longer tags, and validation must pass on what a pull writes.
        """
        if any(not tag.strip() for tag in self.tags):
            raise ValueError("Tags must not be empty")

        duplicates = sorted({tag for tag in self.tags if self.tags.count(tag) > 1})
        if duplicates:
            raise ValueError(f"Duplicate tags: {duplicates}")

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
            tags=list(self.tags),
        )

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["Topic"]
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Get the tags change for this topic, if any.

        A new topic sends its tags on create_topic. An existing topic whose tags changed
        sends them as an updated TopicTags subresource.
        """
        if old_resource is None or old_resource.tags == self.tags:
            return [], [], []
        return [], [TopicTags(resource_id=self.resource_id, name="tags", tags=self.tags)], []

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

        for file_name in os.listdir(topics_path):
            if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                file_path = os.path.join(topics_path, file_name)
                discovered_topics.append(file_path)

        return discovered_topics
