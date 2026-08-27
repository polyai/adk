"""Handling and managing an Agent Studio AgentSettings

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field
from functools import cached_property

from google.protobuf.message import Message

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.agent_settings_pb2 import (
    Persona_UpdatePersona,
    Personality_UpdatePersonality,
    PersonaReferences,
    Role_UpdateRole,
    Rules_UpdateRules,
)
from poly.resources.resource import (
    Resource,
    ResourceMapping,
    YamlResource,
    register_resource,
)

ALLOWED_BEHAVIOUR_REFERENCES = [
    "global_functions",
    "sms",
    "handoff",
    "attributes",
    "variables",
    "translations",
]
ALLOWED_PERSONA_REFERENCES = ["variables"]
ALLOWED_ADJECTIVES = {
    "Polite",
    "Calm",
    "Kind",
    "Funny",
    "Other",
    "Energetic",
    "Thoughtful",
}


@register_resource("personality")
@dataclass
class SettingsPersonality(YamlResource):
    """Resource class for managing personality settings"""

    custom: str
    adjectives: dict[str, bool] = field(default_factory=dict)

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Personality resource."""
        return os.path.join("agent_settings", "personality.yaml")

    def to_yaml_dict(self) -> dict:
        """Convert the personality settings to a YAML-serializable dict."""
        return {
            "adjectives": {
                adj: enabled for adj, enabled in sorted(self.adjectives.items()) if enabled
            },
            "custom": self.custom,
        }

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["custom"] = utils.replace_resource_ids_with_names(d["custom"], resource_mappings or [])
        return d

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "SettingsPersonality":
        """Construct personality settings from YAML data and identity fields."""
        return SettingsPersonality(
            resource_id=resource_id,
            name=name,
            adjectives=yaml_dict.get("adjectives", {}),
            custom=yaml_dict.get("custom", ""),
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "SettingsPersonality"]:
        """Parse personality settings from a projection dict."""
        agent_settings = projection.get("agentSettings", {})
        personality = agent_settings.get("personality", None)
        if not personality:
            return {}
        return {
            "personality": cls(
                resource_id="personality",
                name="personality",
                adjectives=personality.get("adjectives", {}),
                custom=personality.get("custom", ""),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the personality resource."""
        # Other adjective can only be set if no other adjectives are selected
        if self.adjectives.get("Other", False) and any(
            v for k, v in self.adjectives.items() if k.lower() != "other"
        ):
            raise ValueError("Other adjective can only be set if no other adjectives are selected.")

        # Adjectives must be from the allowed set
        if any(
            enabled and adj not in ALLOWED_ADJECTIVES for adj, enabled in self.adjectives.items()
        ):
            raise ValueError(
                f"Enabled adjectives must be from the allowed set: {', '.join(ALLOWED_ADJECTIVES)}"
            )

        references = utils.get_references_from_prompt(
            self.custom, ["attributes", "variables"], raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

    def build_update_proto(self) -> Personality_UpdatePersonality:
        """Create a proto for updating the resource."""

        return Personality_UpdatePersonality(
            adjectives={
                "values": {adj: self.adjectives.get(adj, False) for adj in ALLOWED_ADJECTIVES},
            },
            custom=self.custom,
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Personality settings.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Personality settings.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "personality"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        file_path = os.path.join(base_path, "agent_settings", "personality.yaml")

        if not os.path.exists(file_path):
            return []

        return [file_path]


@register_resource("role")
@dataclass
class SettingsRole(YamlResource):
    """Resource class for managing role settings"""

    value: str
    additional_info: str
    custom: str

    @cached_property
    def file_path(self) -> str:
        """Get the file path for the Role resource."""
        return os.path.join("agent_settings", "role.yaml")

    def to_yaml_dict(self) -> dict:
        """Convert the role settings to a YAML-serializable dict."""
        return {
            "value": self.value,
            "additional_info": self.additional_info,
            "custom": self.custom,
        }

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["custom"] = utils.replace_resource_ids_with_names(d["custom"], resource_mappings or [])
        return d

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "SettingsRole":
        """Construct role settings from YAML data and identity fields."""
        return SettingsRole(
            resource_id=resource_id,
            name=name,
            value=yaml_dict.get("value", ""),
            additional_info=yaml_dict.get("additional_info", ""),
            custom=yaml_dict.get("custom", ""),
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "SettingsRole"]:
        """Parse role settings from a projection dict."""
        agent_settings = projection.get("agentSettings", {})
        role = agent_settings.get("role", None)
        if not role:
            return {}
        return {
            "role": cls(
                resource_id="role",
                name="role",
                value=role.get("value", ""),
                additional_info=role.get("additionalInfo", ""),
                custom=role.get("custom", ""),
            )
        }

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the role resource."""
        # Custom role can only exist if role is 'other'
        if self.custom and self.value.lower() != "other":
            raise ValueError("Custom role can only be set if role is 'other'.")

        # Validate references
        references = utils.get_references_from_prompt(
            self.custom, ["attributes", "variables"], raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

    def build_update_proto(self) -> Role_UpdateRole:
        """Create a proto for updating the resource."""

        return Role_UpdateRole(
            value=self.value,
            additional_info=self.additional_info,
            custom=self.custom,
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for Role settings.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for Role settings.")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "role"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        file_path = os.path.join(base_path, "agent_settings", "role.yaml")

        if not os.path.exists(file_path):
            return []

        return [file_path]


@register_resource("persona")
@dataclass
class SettingsPersona(Resource):
    """Resource class for managing the persona setting.

    This is what the "Role" field in Agent Studio edits. It supersedes the
    personality and role settings, which remain on the wire but are no longer
    surfaced to builders.
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

        A project without the persona feature flag still carries a persona object,
        just without content, so absent content means the setting is not enabled
        rather than that anything is wrong.
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
        """Create a proto for updating the resource."""

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
