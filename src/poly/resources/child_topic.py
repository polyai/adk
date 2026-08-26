"""Handling and managing Agent Studio KB child topics

A child topic is a KB Topic scoped to a single variant: it only applies when that variant
is active. It lives in a separate collection from the base `knowledge_base.topics` --
`ChildOverwrites.knowledge_base` on the platform's Snapshot message -- gets its own
platform-assigned ID independent of any base topic (there is no backend link field between
a child topic and a base topic), and its name must be unique across the base topics and
every child topic, including those belonging to other variants.

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass
from functools import cached_property
from typing import Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.knowledge_base_pb2 import (
    KnowledgeBase_CreateTopic,
    KnowledgeBase_UpdateTopic,
)
from poly.resources.resource import ResourceMapping, register_resource
from poly.resources.topic import Topic
from poly.resources.variant_attributes import Variant

CHILD_TOPICS_DIR = "child_topics"


def _get_variant_folder_from_path(file_path: str) -> Optional[str]:
    """Extract the variant folder from a child_topics/<variant>/<topic>.yaml path."""
    parts = os.path.normpath(file_path).split(os.sep)
    if CHILD_TOPICS_DIR not in parts:
        return None
    dir_index = parts.index(CHILD_TOPICS_DIR)
    # There must be both a variant folder and a file after it.
    if dir_index + 2 < len(parts):
        return parts[dir_index + 1]
    return None


def _get_variant_from_folder(
    variant_folder: str, resource_mappings: list[ResourceMapping]
) -> tuple[Optional[str], Optional[str]]:
    """Resolve a variant folder name to (variant_id, variant_name) via resource mappings.

    Both sides are put through clean_name so a variant declared as "Variant 1" matches its
    folder on disk, which is written lowercased as "variant_1".
    """
    folder = utils.clean_name(variant_folder)
    for resource in resource_mappings:
        if resource.resource_type == Variant and utils.clean_name(resource.resource_name) == folder:
            return resource.resource_id, resource.resource_name
    return None, None


@register_resource("child_topics")
@dataclass
class ChildTopic(Topic):
    """Dataclass representing a variant-scoped Agent Studio KB child topic.

    Stored at child_topics/<cleaned_variant_name>/<cleaned_topic_name>.yaml, separate from
    the base topics in topics/. The variant is not stored in the YAML -- it's inferred from
    the enclosing folder name, the same way a FlowStep infers its parent flow from its
    enclosing folder.
    """

    variant_id: str
    variant_name: str

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        variant_id: str,
        variant_name: str,
        actions: str,
        content: str,
        example_queries: list[str],
        enabled: bool = True,
    ):
        self.resource_id = resource_id
        self.name = name
        self.variant_id = variant_id
        self.variant_name = variant_name
        self.actions = actions
        self.content = content
        self.example_queries = example_queries or []
        self.enabled = enabled

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "ChildTopic"]:
        """Parse variant-scoped child topics from a projection dict."""
        variant_names = {
            variant_id: variant["name"]
            for variant_id, variant in (
                projection.get("variantManagement", {})
                .get("variants", {})
                .get("entities", {})
                .items()
            )
        }

        child_topics = {}
        topics = (
            projection.get("childOverwrites", {})
            .get("knowledgeBase", {})
            .get("topics", {})
            .get("entities", {})
        )
        for topic_id, topic in topics.items():
            variant_id = topic.get("variantId")
            variant_name = variant_names.get(variant_id)
            if not variant_id or not variant_name:
                continue

            example_queries = topic.get("exampleQueries", [])
            queries = [
                example_queries["query"]
                for example_queries in example_queries
                if "query" in example_queries
            ]

            child_topics[topic_id] = cls(
                resource_id=topic_id,
                name=topic["name"],
                variant_id=variant_id,
                variant_name=variant_name,
                actions=topic["actions"],
                content=topic["content"],
                example_queries=queries,
                enabled=topic.get("isActive", True),
            )
        return child_topics

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the child topic.

        The variant folder is lowercased like every other name in a topic path, so a
        variant named "Variant 1" lives at child_topics/variant_1/.
        """
        variant_folder = utils.clean_name(self.variant_name)
        file_name = f"{utils.clean_name(self.name)}.yaml"
        return os.path.join(CHILD_TOPICS_DIR, variant_folder, file_name)

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str,
        variant_id: str = None,
        variant_name: str = None,
        **kwargs,
    ) -> "ChildTopic":
        """Create an instance from YAML data and identity fields."""
        resolved_name = yaml_dict.get("name") or name
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            variant_id=variant_id,
            variant_name=variant_name,
            actions=yaml_dict.get("actions", ""),
            content=yaml_dict.get("content", ""),
            example_queries=yaml_dict.get("example_queries", []),
            enabled=yaml_dict.get("enabled", True),
        )

    @classmethod
    def read_local_resource(
        cls,
        file_path: str,
        resource_id: str,
        resource_name: str,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> "ChildTopic":
        """Read a local YAML child topic, resolving its variant from its enclosing folder.

        Resolution failures are deferred to validate() rather than raised here, since this
        is also called with an empty resource_mappings list purely to recover a resource's
        real name during discovery (before the full resource mapping is known).
        """
        resource_mappings = resource_mappings or []

        variant_folder = _get_variant_folder_from_path(file_path)
        variant_id, variant_name = (
            _get_variant_from_folder(variant_folder, resource_mappings)
            if variant_folder
            else (None, None)
        )

        # An unresolved variant is reported by validate(), not raised here -- discovery
        # calls this with no resource mappings purely to recover the resource's real name.
        # Fall back to the folder as read from disk so file_path can still be built until
        # then; validate() still rejects it, because variant_id is left unset.
        variant_name = variant_name or variant_folder

        # Delegates to Topic.read_local_resource, which performs the same
        # filename-vs-name match check.
        return super().read_local_resource(
            file_path,
            resource_id=resource_id,
            resource_name=resource_name,
            resource_mappings=resource_mappings,
            variant_id=variant_id,
            variant_name=variant_name,
            **kwargs,
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the child topic resource."""
        super().validate(resource_mappings=resource_mappings, **kwargs)
        resource_mappings = resource_mappings or []

        variant_exists = any(
            resource.resource_type == Variant and resource.resource_id == self.variant_id
            for resource in resource_mappings
        )
        if not self.variant_id or not variant_exists:
            raise ValueError(
                f"Child topic '{self.name}' is not inside a known variant folder. "
                "Check config/variant_attributes.yaml."
            )

        # The platform requires a topic name to be unique across the base topics and every
        # child topic, in every variant -- not just within this one. Enforce that here so
        # the clash is reported against the offending file rather than as a push failure.
        own_clean_name = utils.clean_name(self.name)
        for resource in resource_mappings:
            if resource.resource_id == self.resource_id:
                continue
            if resource.resource_type not in (Topic, ChildTopic):
                continue
            if utils.clean_name(resource.resource_name) != own_clean_name:
                continue

            if resource.resource_type == Topic:
                clash = f"base topic '{resource.resource_name}'"
            else:
                variant_folder = _get_variant_folder_from_path(resource.file_path)
                clash = f"child topic '{resource.resource_name}'" + (
                    f" in variant '{utils.clean_name(variant_folder)}'" if variant_folder else ""
                )
            raise ValueError(
                f"Child topic '{self.name}' has the same name as {clash}. Topic names must "
                "be unique across all topics and child topics, including across variants."
            )

    def build_update_proto(self) -> KnowledgeBase_UpdateTopic:
        """Create a proto for updating the resource."""
        proto = super().build_update_proto()
        proto.variant_id = self.variant_id
        return proto

    def build_create_proto(self) -> KnowledgeBase_CreateTopic:
        """Create a proto for creating the resource."""
        proto = super().build_create_proto()
        proto.variant_id = self.variant_id
        return proto

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource.

        Routes through the create_child_topic/update_child_topic/delete_child_topic
        commands, which operate on the childOverwrites collection only -- distinct from
        Topic's "topic" command_type, which would touch the base topic collection instead.
        """
        return "child_topic"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Every subdirectory of child_topics/ is treated as a candidate variant folder; the
        variant name itself is checked later, in validate().

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        child_topics_path = os.path.join(base_path, CHILD_TOPICS_DIR)
        discovered_child_topics: list[str] = []

        if not os.path.exists(child_topics_path):
            return discovered_child_topics

        for variant_folder in os.listdir(child_topics_path):
            variant_path = os.path.join(child_topics_path, variant_folder)
            if not os.path.isdir(variant_path):
                continue
            for file_name in os.listdir(variant_path):
                if file_name.endswith(".yaml") or file_name.endswith(".yml"):
                    discovered_child_topics.append(os.path.join(variant_path, file_name))

        return discovered_child_topics
