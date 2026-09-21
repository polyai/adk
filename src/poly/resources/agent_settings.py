"""Handling and managing an Agent Studio AgentSettings

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from functools import cached_property

from google.protobuf.message import Message

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.agent_settings_pb2 import (
    Persona_UpdatePersona,
    PersonaReferences,
    Rules_UpdateRules,
)
from poly.resources.resource import (
    Resource,
    ResourceMapping,
    register_resource,
)

logger = logging.getLogger(__name__)

ALLOWED_BEHAVIOUR_REFERENCES = [
    "global_functions",
    "sms",
    "handoff",
    "attributes",
    "variables",
    "translations",
]
ALLOWED_PERSONA_REFERENCES = ["attributes", "variables"]


@register_resource("persona")
@dataclass
class SettingsPersona(Resource):
    """Resource class for managing the persona setting.

    A single free-text description of who the agent is, edited as the "Role"
    field in Agent Studio. It replaced the personality and role settings, which
    remain on the wire but are no longer surfaced to builders or handled here.
    """

    content: str

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Persona resource."""
        return os.path.join("agent_settings", "persona.txt")

    @property
    def raw(self) -> str:
        """Convert the resource to a raw format."""
        return self.content

    @staticmethod
    def make_pretty(
        contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource IDs with resource names in the provided contents."""
        return utils.replace_resource_ids_with_names(contents, resource_mappings or [])

    @classmethod
    def from_pretty(
        cls, contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        return utils.replace_resource_names_with_ids(contents, resource_mappings or [])

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the persona resource."""
        references = utils.get_references_from_prompt(
            self.content, ALLOWED_PERSONA_REFERENCES, raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "SettingsPersona"]:
        """Parse the persona setting from a projection dict.

        The projection carries a persona object whether or not any content was
        ever authored, so read the content rather than the object: absent content
        means there is nothing to write to disk, not that anything is wrong.
        """
        agent_settings = projection.get("agentSettings", {})
        persona = agent_settings.get("persona") or {}
        content = persona.get("content")
        if content is None:
            return {}
        return {
            "persona": cls(
                resource_id="persona",
                name="persona",
                content=content,
            )
        }

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "SettingsPersona":
        """Read a local plain text resource from the given file path."""
        content = cls.read_to_raw(file_path, **kwargs)
        return SettingsPersona(
            resource_id=resource_id,
            name=resource_name,
            content=content,
        )

    def build_update_proto(self) -> Persona_UpdatePersona:
        """Create a proto for updating the resource.

        PersonaReferences carries a variables map and nothing else, so attribute
        references travel in the content and are not tracked. Personality and
        role behaved the same way before the persona replaced them.
        """

        references = utils.get_references_from_prompt(self.content, ALLOWED_PERSONA_REFERENCES)

        return Persona_UpdatePersona(
            content=self.content,
            references=PersonaReferences(variables=references.get("variables", {})),
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Persona settings.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Persona settings.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "persona"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        file_path = os.path.join(base_path, "agent_settings", "persona.txt")

        if not os.path.exists(file_path):
            return []

        return [file_path]


@register_resource("rules")
@dataclass
class SettingsRules(Resource):
    """Resource class for managing rules settings"""

    behaviour: str

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Rules resource."""
        return os.path.join("agent_settings", "rules.txt")

    @property
    def raw(self) -> str:
        """Convert the resource to a raw format."""
        return self.behaviour

    @staticmethod
    def make_pretty(
        contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource IDs with resource names in the provided contents."""
        return utils.replace_resource_ids_with_names(contents, resource_mappings or [])

    @classmethod
    def from_pretty(
        cls, contents: str, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> str:
        """Replace resource names with resource IDs in the provided contents."""
        return utils.replace_resource_names_with_ids(contents, resource_mappings or [])

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the rules resource."""
        references = utils.get_references_from_prompt(
            self.behaviour, ALLOWED_BEHAVIOUR_REFERENCES, raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "SettingsRules"]:
        """Parse rules settings from a projection dict."""
        if "agentSettings" not in projection:
            logger.debug("No read access to the agent rules - it will not be pulled.")
            return {}

        agent_settings = projection.get("agentSettings", {})
        rules = agent_settings.get("rules", None)
        if not rules:
            return {}
        return {
            "rules": cls(
                resource_id="rules",
                name="rules",
                behaviour=rules.get("behaviour", ""),
            )
        }

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "SettingsRules":
        """Read a local YAML resource from the given file path."""
        content = cls.read_to_raw(file_path, **kwargs)
        behaviour = content
        return SettingsRules(
            resource_id=resource_id,
            name=resource_name,
            behaviour=behaviour,
        )

    def build_update_proto(self) -> Rules_UpdateRules:
        """Create a proto for updating the resource."""

        references = utils.get_references_from_prompt(self.behaviour, ALLOWED_BEHAVIOUR_REFERENCES)

        # It's called globalFunctions for settings
        references["globalFunctions"] = references.pop("global_functions", {})

        return Rules_UpdateRules(behaviour=self.behaviour, references=references)

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Rules settings.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Rules settings.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "rules"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        file_path = os.path.join(base_path, "agent_settings", "rules.txt")

        if not os.path.exists(file_path):
            return []

        return [file_path]
