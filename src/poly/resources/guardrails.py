"""Handling and managing Agent Studio Guardrails (platform and custom)

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from typing import ClassVar

from google.protobuf.message import Message

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.guardrails_pb2 import (
    Guardrail,
    GuardrailName,
    Guardrails_CreateCustomGuardrail,
    Guardrails_DeleteCustomGuardrail,
    Guardrails_UpdateCustomGuardrail,
    Guardrails_UpdateGuardrails,
)
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping, register_resource

GUARDRAILS_FILE = os.path.join("agent_settings", "guardrails.yaml")

logger = logging.getLogger(__name__)

CUSTOM_GUARDRAIL_REFERENCES = [
    "global_functions",
    "sms",
    "handoff",
    "attributes",
    "variables",
    "translations",
]

# Guardrail.name is a fixed platform enum (GuardrailName), not a free string.
# Map it to/from a short lowercase form for the YAML/CLI-facing "id", e.g.
# GUARDRAIL_NAME_JAILBREAK_DEFENCE <-> "jailbreak_defence".
_GUARDRAIL_NAME_PREFIX = "GUARDRAIL_NAME_"


def _guardrail_name_to_yaml(proto_name: str) -> str:
    """Convert a GuardrailName enum string to its short YAML form."""
    return proto_name.removeprefix(_GUARDRAIL_NAME_PREFIX).lower()


def _guardrail_name_from_yaml(yaml_name: str) -> str:
    """Convert a short YAML guardrail name back to its GuardrailName enum string."""
    return f"{_GUARDRAIL_NAME_PREFIX}{yaml_name.upper()}"


# The fixed catalog of real platform guardrails, as full GuardrailName enum
# strings, excluding the GUARDRAIL_NAME_UNSPECIFIED sentinel. Computed once
# here so every consumer agrees on what counts as a valid guardrail.
_GUARDRAIL_CATALOG: tuple[str, ...] = tuple(
    value.name
    for value in GuardrailName.DESCRIPTOR.values
    if value.name != "GUARDRAIL_NAME_UNSPECIFIED"
)


class _GuardrailYamlResource(MultiResourceYamlResource):
    """Shared base for the guardrail resources stored in ``GUARDRAILS_FILE``.

    Platform and custom guardrails live as separate top-level lists in the
    same file, keyed by ``top_level_name`` — discovery is otherwise identical.
    """

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        """Discover resources of this type in the given base path."""
        yaml_path = os.path.join(base_path, GUARDRAILS_FILE)
        discovered: list[str] = []

        if not os.path.exists(yaml_path):
            return discovered

        yaml_dict = cls._get_top_level_data(yaml_path)
        guardrails: list[dict] = yaml_dict.get(cls.top_level_name, []) if yaml_dict else []

        for guardrail in guardrails:
            name = guardrail.get("name")
            if not name:
                continue
            clean_name = utils.clean_name(name, lowercase=False)
            discovered.append(os.path.join(yaml_path, cls.top_level_name, clean_name))

        return discovered


@register_resource("platform_guardrails")
@dataclass
class PlatformGuardrail(_GuardrailYamlResource):
    """Dataclass representing an Agent Studio platform guardrail's toggle state.

    Platform guardrails are provided by the platform (the catalog of possible
    guardrails is fixed) — only the ``enabled`` toggle can be updated locally.
    """

    enabled: bool = True
    top_level_name: ClassVar[str] = "platform_guardrails"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "PlatformGuardrail"]:
        """Parse platform guardrails from a projection dict.

        guardrails.guardrails is a map keyed by the short GuardrailName enum
        suffix (e.g. "JAILBREAK_DEFENCE", without the "GUARDRAIL_NAME_"
        prefix), each value an object carrying an explicit `enabled` toggle.
        Emit one resource per entry in the fixed catalog, defaulting to
        enabled if the platform hasn't reported a state for it.
        """
        guardrails_section = projection.get("guardrails")
        if not guardrails_section:
            return {}
        guardrails_map = guardrails_section.get("guardrails") or {}

        guardrails = {}
        for proto_name in _GUARDRAIL_CATALOG:
            short_proto_name = proto_name.removeprefix(_GUARDRAIL_NAME_PREFIX)
            entry = guardrails_map.get(short_proto_name, {})
            if not isinstance(entry, dict):
                logger.warning(
                    "Skipping platform guardrail projection entry of unexpected shape "
                    "(expected an object, got %s): %r",
                    type(entry).__name__,
                    entry,
                )
                entry = {}
            name = _guardrail_name_to_yaml(proto_name)
            guardrails[name] = cls(
                resource_id=name,
                name=name,
                enabled=entry.get("enabled", True),
            )
        return guardrails

    @property
    def file_path(self) -> str:
        """Get the file path for the platform guardrail."""
        clean_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(GUARDRAILS_FILE, self.top_level_name, clean_name)

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "name": self.name,
            "enabled": self.enabled,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "PlatformGuardrail":
        """Create an instance from YAML data and identity fields."""
        resolved_name = yaml_dict.get("name") or name
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            enabled=yaml_dict.get("enabled", True),
        )

    def validate(self, **kwargs) -> None:
        """Validate the platform guardrail resource."""
        if not self.name:
            raise ValueError("Name is required")
        if not isinstance(self.name, str):
            raise ValueError(f"Invalid value {self.name!r} for 'name'. Must be a string.")
        if not isinstance(self.enabled, bool):
            raise ValueError(
                f"Invalid value {self.enabled!r} for 'enabled'. Must be true or false (unquoted)."
            )

        proto_name = _guardrail_name_from_yaml(self.name)
        if proto_name not in _GUARDRAIL_CATALOG:
            valid_names = sorted(_guardrail_name_to_yaml(n) for n in _GUARDRAIL_CATALOG)
            raise ValueError(
                f"Unrecognised platform guardrail '{self.name}'. "
                f"Must be one of: {', '.join(valid_names)}"
            )

    @classmethod
    def validate_collection(cls, resources: dict[str, "PlatformGuardrail"]) -> None:
        """Ensure every guardrail in the fixed platform catalog is present locally.

        The catalog is fixed by the platform, so a missing entry means the local
        file has drifted (e.g. a line was deleted by hand) rather than reflecting
        a real platform state.
        """
        present_names = {guardrail.name for guardrail in resources.values()}
        catalog_names = {_guardrail_name_to_yaml(n) for n in _GUARDRAIL_CATALOG}
        missing = sorted(catalog_names - present_names)
        if missing:
            raise ValueError(
                f"Missing platform guardrail(s) in {GUARDRAILS_FILE}: {', '.join(missing)}. "
                "Run 'poly pull' to sync the full guardrail catalog."
            )

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "guardrails"

    def build_update_proto(self) -> Guardrails_UpdateGuardrails:
        """Create a proto for updating the resource."""
        return Guardrails_UpdateGuardrails(
            guardrails=[Guardrail(name=_guardrail_name_from_yaml(self.name), enabled=self.enabled)]
        )

    def build_create_proto(self) -> Message:
        """Create a proto for creating the resource."""
        raise NotImplementedError("Create operation not supported for platform guardrails.")

    def build_delete_proto(self) -> Message:
        """Create a proto for deleting the resource."""
        raise NotImplementedError("Delete operation not supported for platform guardrails.")


@register_resource("custom_guardrails")
@dataclass
class CustomGuardrail(_GuardrailYamlResource):
    """Dataclass representing an Agent Studio custom guardrail.

    Stored as an optional ``custom_guardrails`` list in the same
    ``agent_settings/guardrails.yaml`` file used by ``PlatformGuardrail``.
    """

    prompt: str
    action: str
    enabled: bool = True
    top_level_name: ClassVar[str] = "custom_guardrails"

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "CustomGuardrail"]:
        """Parse custom guardrails from a projection dict."""
        custom_guardrails = {}
        for guardrail_id, guardrail in (
            projection.get("guardrails", {}).get("customGuardrails", {}).get("entities", {}).items()
        ):
            if not isinstance(guardrail, dict):
                logger.warning(
                    "Skipping custom guardrail projection entry of unexpected shape "
                    "(expected an object, got %s): %r",
                    type(guardrail).__name__,
                    guardrail,
                )
                continue
            custom_guardrails[guardrail_id] = cls(
                resource_id=guardrail_id,
                name=guardrail.get("name", ""),
                prompt=guardrail.get("prompt", ""),
                action=guardrail.get("action", ""),
                enabled=guardrail.get("enabled", True),
            )
        return custom_guardrails

    @property
    def file_path(self) -> str:
        """Get the file path for the custom guardrail."""
        clean_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(GUARDRAILS_FILE, self.top_level_name, clean_name)

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "action": self.action,
            "prompt": self.prompt,
        }

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Return the pretty dictionary."""
        d["action"] = utils.replace_resource_ids_with_names(d["action"], resource_mappings or [])
        return d

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "CustomGuardrail":
        """Create an instance from YAML data and identity fields."""
        resolved_name = yaml_dict.get("name") or name
        return cls(
            resource_id=resource_id,
            name=resolved_name,
            prompt=yaml_dict.get("prompt", ""),
            action=yaml_dict.get("action", ""),
            enabled=yaml_dict.get("enabled", True),
        )

    def validate(self, resource_mappings: list = None, **kwargs) -> None:
        """Validate the custom guardrail resource."""
        if not self.name:
            raise ValueError("Name is required")
        if not self.prompt:
            raise ValueError("Prompt is required")
        if not self.action:
            raise ValueError("Action is required")

        references = utils.get_references_from_prompt(
            self.action, CUSTOM_GUARDRAIL_REFERENCES, raise_on_invalid=True
        )
        valid, invalid_references = utils.validate_references(references, resource_mappings)
        if not valid:
            raise ValueError(f"Invalid references: {invalid_references}")

    def build_create_proto(self) -> Guardrails_CreateCustomGuardrail:
        """Create a proto for creating the resource."""
        references = utils.get_references_from_prompt(self.action, CUSTOM_GUARDRAIL_REFERENCES)
        return Guardrails_CreateCustomGuardrail(
            id=self.resource_id,
            name=self.name,
            prompt=self.prompt,
            action=self.action,
            enabled=self.enabled,
            references=references,
        )

    def build_update_proto(self) -> Guardrails_UpdateCustomGuardrail:
        """Create a proto for updating the resource."""
        references = utils.get_references_from_prompt(self.action, CUSTOM_GUARDRAIL_REFERENCES)
        return Guardrails_UpdateCustomGuardrail(
            id=self.resource_id,
            name=self.name,
            prompt=self.prompt,
            action=self.action,
            enabled=self.enabled,
            references=references,
        )

    def build_delete_proto(self) -> Guardrails_DeleteCustomGuardrail:
        """Create a proto for deleting the resource."""
        return Guardrails_DeleteCustomGuardrail(id=self.resource_id)

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "custom_guardrail"
