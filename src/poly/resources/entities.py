"""Handling and managing an Agent Studio Entity

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

from google.protobuf.message import Message

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.entities_pb2 import (
    AddressConfig,
    AlphanumericConfig,
    DateConfig,
    Entity_Create,
    Entity_Delete,
    Entity_Update,
    FreeTextConfig,
    MultipleOptionsConfig,
    NameConfig,
    NumberConfig,
    PhoneNumberConfig,
    TimeConfig,
)
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping


class EntityType(str, Enum):
    """Enum representing the type of an Entity"""

    NUMERIC = "numeric"
    ALPHANUMERIC = "alphanumeric"
    ENUM = "enum"
    DATE = "date"
    PHONE_NUMBER = "phone_number"
    TIME = "time"
    ADDRESS = "address"
    FREE_TEXT = "free_text"
    NAME = "name_config"


EXPECTED_ENTITY_CONFIG_FIELDS: dict[EntityType, dict[str, type | tuple]] = {
    EntityType.NUMERIC: {
        "has_decimal": bool,
        "has_range": bool,
        "min": (float, int),
        "max": (float, int),
    },
    EntityType.ALPHANUMERIC: {
        "enabled": bool,
        "validation_type": str,
        "regular_expression": str,
    },
    EntityType.ENUM: {
        "options": list,
    },
    EntityType.DATE: {
        "relative_date": bool,
    },
    EntityType.PHONE_NUMBER: {
        "enabled": bool,
        "country_codes": list,
    },
    EntityType.TIME: {
        "enabled": bool,
        "start_time": str,
        "end_time": str,
    },
    EntityType.ADDRESS: {},
    EntityType.FREE_TEXT: {},
    EntityType.NAME: {},
}


@dataclass
class Entity(MultiResourceYamlResource):
    """Dataclass representing an Agent Studio Entity"""

    projection_path: ClassVar[list[str]] = ["entities", "entities", "entities", "{id}"]

    description: str
    entity_type: EntityType
    config: dict = field(default_factory=dict)
    top_level_name: ClassVar[str] = "entities"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        entity_type: str | EntityType,
        description: str = "",
        config: dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description
        self.entity_type = (
            EntityType(utils.to_snake_case(entity_type))
            if isinstance(entity_type, str)
            else entity_type
        )
        self.config = utils.convert_keys_to_snake_case(config or {})

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        """
        Reference prefix for the resource type
        E.g. "entity" in {entity:id}
        """
        return "entity"

    @property
    def file_path(self) -> str:
        """Get the file path for the entity."""
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join("config", "entities.yaml", self.top_level_name, path_safe_name)

    def to_yaml_dict(self) -> dict:
        """Return a dictionary suitable for YAML serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "entity_type": self.entity_type.value,
            "config": self.config,
        }

    @classmethod
    def from_yaml_dict(cls, yaml_data: dict, resource_id: str, name: str, **kwargs) -> "Entity":
        """Create an instance from YAML data and identity fields."""
        return cls(
            resource_id=resource_id,
            name=yaml_data.get("name", ""),
            description=(yaml_data.get("description") or "").strip(),
            entity_type=EntityType(yaml_data.get("entity_type")),
            config=yaml_data.get("config", {}),
        )

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs):
        """Validate the topic resource."""
        # Validate config fields based on entity type
        expected_fields = EXPECTED_ENTITY_CONFIG_FIELDS[self.entity_type]
        for config_field, field_type in expected_fields.items():
            if config_field not in self.config:
                continue
            if not isinstance(self.config[config_field], field_type):
                type_name = (
                    field_type.__name__
                    if isinstance(field_type, type)
                    else " or ".join(t.__name__ for t in field_type)
                )
                raise ValueError(
                    f"Config field '{config_field}' should be of type '{type_name}' "
                    f"for entity type '{self.entity_type.value}'."
                )

        if self.description != self.description.strip():
            raise ValueError("Description cannot contain leading or trailing whitespace.")

    def build_update_proto(self) -> Entity_Update:
        """Create a proto for updating the resource."""
        # Compute references in other resources
        return Entity_Update(
            id=self.resource_id,
            name=self.name,
            type=utils.to_camel_case(self.entity_type.value),
            description=self.description,
            **self._build_config_proto(),
        )

    def build_delete_proto(self):
        """Create a proto for deleting the resource."""
        return Entity_Delete(
            id=self.resource_id,
        )

    def build_create_proto(self) -> Entity_Create:
        """Create a proto for creating the resource."""
        return Entity_Create(
            id=self.resource_id,
            name=self.name,
            type=utils.to_camel_case(self.entity_type.value),
            description=self.description,
            **self._build_config_proto(),
            references={"flow_steps": {}, "no_code_steps": {}},
        )

    def _build_config_proto(self) -> dict[str, Message]:
        """Build the config proto based on entity type and config."""
        if self.entity_type == EntityType.NUMERIC:
            return {
                "numeric": NumberConfig(
                    has_decimal=self.config.get("has_decimal", False),
                    has_range=self.config.get("has_range", False),
                    min=self.config.get("min", 0.0),
                    max=self.config.get("max", 0.0),
                )
            }
        elif self.entity_type == EntityType.ALPHANUMERIC:
            return {
                "alphanumeric": AlphanumericConfig(
                    enabled=self.config.get("enabled", True),
                    validation_type=self.config.get("validation_type", ""),
                    regular_expression=self.config.get("regular_expression", ""),
                )
            }
        elif self.entity_type == EntityType.ENUM:
            return {
                "enum": MultipleOptionsConfig(
                    options=self.config.get("options", []),
                )
            }
        elif self.entity_type == EntityType.DATE:
            return {
                "date": DateConfig(
                    relative_date=self.config.get("relative_date", False),
                )
            }
        elif self.entity_type == EntityType.PHONE_NUMBER:
            return {
                "phone_number": PhoneNumberConfig(
                    enabled=self.config.get("enabled", True),
                    country_codes=self.config.get("country_codes", []),
                )
            }
        elif self.entity_type == EntityType.TIME:
            return {
                "time": TimeConfig(
                    enabled=self.config.get("enabled", True),
                    start_time=self.config.get("start_time", ""),
                    end_time=self.config.get("end_time", ""),
                )
            }
        elif self.entity_type == EntityType.ADDRESS:
            return {"address": AddressConfig()}
        elif self.entity_type == EntityType.FREE_TEXT:
            return {"free_text": FreeTextConfig()}
        elif self.entity_type == EntityType.NAME:
            return {"name_config": NameConfig()}
        raise ValueError(f"Unsupported entity type: {self.entity_type}")

    @property
    def command_type(self) -> str:
        """Get the update type for updating the resource."""
        return "entity"

    @property
    def delete_command_type(self) -> str:
        return "entity_delete"

    @property
    def create_command_type(self) -> str:
        return "entity_create"

    @property
    def update_command_type(self) -> str:
        return "entity_update"

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        entities_path = os.path.join(base_path, "config", "entities.yaml")
        discovered_entities: list[str] = []

        if not os.path.exists(entities_path):
            return discovered_entities

        yaml_dict = Entity._get_top_level_data(entities_path)
        entities: list[dict] = yaml_dict.get("entities", []) if yaml_dict else []

        for entity in entities:
            name = entity.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_entities.append(
                os.path.join(entities_path, Entity.top_level_name, path_safe_name)
            )

        return discovered_entities
