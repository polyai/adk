"""Handling and managing an Agent Studio Variant Attributes

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass, field
from typing import ClassVar

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.variant_pb2 import (
    AttributeValues,
    Variant_CreateAttribute,
    Variant_CreateVariant,
    Variant_DeleteAttribute,
    Variant_DeleteVariant,
    Variant_UpdateAttribute,
    Variant_UpdateVariant,
    VariantValues,
)
from poly.resources.resource import MultiResourceYamlResource, ResourceMapping, register_resource

logger = logging.getLogger(__name__)


@register_resource("variants")
@dataclass
class Variant(MultiResourceYamlResource):
    """Dataclass representing a variant"""

    is_default: bool = False
    top_level_name: ClassVar[str] = "variants"
    attribute_ids: list[str] = field(default_factory=list, repr=False, init=False)

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        is_default: bool = False,
        slim: bool = False,
    ):
        self.resource_id = resource_id
        self.name = name
        self.is_default = is_default
        self.slim = slim
        self.attribute_ids = []

    def to_yaml_dict(self) -> dict:
        yaml_dict = {
            "name": self.name,
        }
        if self.is_default:
            yaml_dict["is_default"] = self.is_default
        return yaml_dict

    @classmethod
    def from_yaml_dict(cls, yaml_dict: dict, resource_id: str, name: str, **kwargs) -> "Variant":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            is_default=yaml_dict.get("is_default", False),
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "Variant"]:
        """Parse variants from a projection dict."""
        variants = {}
        variants_projection = (
            projection.get("variantManagement", {}).get("variants", {}).get("entities", {})
        )
        if "variantManagement" not in projection:
            logger.debug("No read access to variants - they will not be pulled.")
            return {}

        # Guard on "isDefault", not "name": names are deliberately exposed to
        # filtered readers so test cases can resolve their variant, so a name
        # no longer distinguishes a readable variant from a withheld one.
        if any("isDefault" not in variant for variant in variants_projection.values()):
            logger.debug("No read access to variants - keeping names for references only.")
            return {
                variant_id: cls(
                    resource_id=variant_id,
                    name=variant_data.get("name", ""),
                    slim=True,
                )
                for variant_id, variant_data in variants_projection.items()
            }

        for variant_id, variant_data in variants_projection.items():
            variants[variant_id] = cls(
                resource_id=variant_id,
                name=variant_data["name"],
                is_default=variant_data.get("isDefault", False),
            )
        return variants

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "config", "variant_attributes.yaml", self.top_level_name, path_safe_name
        )

    @property
    def command_type(self) -> str:
        return "variant"

    @property
    def delete_command_type(self) -> str:
        return "variant_delete_variant"

    @property
    def create_command_type(self) -> str:
        return "variant_create_variant"

    @property
    def update_command_type(self) -> str:
        return "variant_update_variant"

    def build_update_proto(self) -> Variant_UpdateVariant:
        return Variant_UpdateVariant(
            id=self.resource_id,
            name=self.name,
        )

    def build_delete_proto(self) -> Variant_DeleteVariant:
        return Variant_DeleteVariant(
            id=self.resource_id,
        )

    def build_create_proto(self) -> Variant_CreateVariant:
        return Variant_CreateVariant(
            id=self.resource_id,
            name=self.name,
            attribute_values=AttributeValues(
                values={attribute_id: "" for attribute_id in self.attribute_ids}
            ),
        )

    def validate(self, resource_mappings: list[ResourceMapping], **kwargs):
        for resource in resource_mappings:
            if (
                resource.resource_type == Variant
                and resource.resource_id != self.resource_id
                and resource.resource_name == self.name
            ):
                raise ValueError(f"Variant {self.name} already exists")

    @classmethod
    def validate_collection(cls, resources: dict[str, "Variant"]) -> None:
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
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")
        discovered_variants: list[str] = []

        if not os.path.exists(variant_attributes_path):
            return discovered_variants

        yaml_data = Variant._get_top_level_data(variant_attributes_path)
        variants: list[str] = yaml_data.get("variants", []) if yaml_data else []

        for variant_dict in variants:
            variant_name = variant_dict.get(Variant.resource_key)

            if not variant_name:
                continue
            path_safe_name = utils.clean_name(variant_name, lowercase=False)
            discovered_variants.append(
                os.path.join(variant_attributes_path, Variant.top_level_name, path_safe_name)
            )

        return discovered_variants


@register_resource("variant_attributes")
@dataclass
class VariantAttribute(MultiResourceYamlResource):
    """Dataclass representing a variant attribute"""

    mappings: dict[str, str]
    top_level_name: ClassVar[str] = "attributes"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        mappings: dict[str, str] | None = None,
        slim: bool = False,
    ):
        self.resource_id = resource_id
        self.name = name
        self.mappings = mappings if mappings is not None else {}
        self.slim = slim

    def to_yaml_dict(self) -> dict:
        return {
            "name": self.name,
            "values": dict(self.mappings),
        }

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join(
            "config", "variant_attributes.yaml", self.top_level_name, path_safe_name
        )

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        return "attr"

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "VariantAttribute":
        clean_mapping = {key: value.strip() for key, value in yaml_dict.get("values", {}).items()}
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            mappings=clean_mapping,
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "VariantAttribute"]:
        """Parse variant attributes from a projection dict."""
        variant_attributes = {}
        attributes_projection = (
            projection.get("variantManagement", {}).get("attributes", {}).get("entities", {})
        )
        if "variantManagement" not in projection:
            logger.debug("No read access to variant attributes - they will not be pulled.")
            return {}

        # "archived" is optional in the API schema, so it can't distinguish an
        # auth-filtered attribute from an unarchived one. "type" always is.
        # Auth-filtered: keep id and name only, so {{attr:<id>}} in a readable
        # topic or prompt still renders as a name rather than a raw id. Archived
        # attributes are stubbed too, since we can't tell them apart here.
        if any("type" not in attribute for attribute in attributes_projection.values()):
            logger.debug(
                "No read access to variant attributes - keeping names for references only."
            )
            return {
                attribute_id: cls(
                    resource_id=attribute_id,
                    name=attribute_data.get("name", ""),
                    slim=True,
                )
                for attribute_id, attribute_data in attributes_projection.items()
            }

        for attribute_id, attribute_data in attributes_projection.items():
            if attribute_data.get("archived"):
                continue
            variant_attributes[attribute_id] = cls(
                resource_id=attribute_id, name=attribute_data["name"], mappings={}
            )
        if not variant_attributes:
            return {}

        for variant_id, variant_attribute_values in (
            projection.get("variantManagement", {})
            .get("variantAttributeValues", {})
            .get("entities", {})
            .items()
        ):
            for attribute_id, attribute_value in variant_attribute_values.get("values", {}).items():
                if attribute_id in variant_attributes:
                    variant_attributes[attribute_id].mappings[variant_id] = attribute_value

        return variant_attributes

    @staticmethod
    def to_pretty_dict(
        d: dict,
        resource_mappings: list[ResourceMapping] = None,
        **kwargs,
    ) -> dict:
        """Return dict with variant IDs replaced by names in values keys."""
        d = d.copy()
        variant_ids_to_names = {
            resource.resource_id: resource.resource_name
            for resource in resource_mappings or []
            if resource.resource_type == Variant
        }
        new_mapping = {
            variant_ids_to_names.get(variant_id, variant_id): variant_value
            for variant_id, variant_value in d.get("values", {}).items()
        }
        d["values"] = new_mapping
        return d

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Replace variant names with IDs in a parsed YAML dict."""
        yaml_dict = super().from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, **kwargs
        )
        variant_names_to_ids = {
            resource.resource_name: resource.resource_id
            for resource in resource_mappings or []
            if resource.resource_type == Variant
        }

        new_mapping = {}
        for variant_name, variant_value in yaml_dict.get("values", {}).items():
            new_mapping[variant_names_to_ids.get(variant_name, variant_name)] = variant_value

        yaml_dict["values"] = new_mapping
        return yaml_dict

    @property
    def command_type(self) -> str:
        return "variant_attribute"

    @property
    def delete_command_type(self) -> str:
        return "variant_delete_attribute"

    @property
    def create_command_type(self) -> str:
        return "variant_create_attribute"

    @property
    def update_command_type(self) -> str:
        return "variant_update_attribute"

    def build_update_proto(self) -> Variant_UpdateAttribute:
        return Variant_UpdateAttribute(
            id=self.resource_id, name=self.name, variant_values=VariantValues(values=self.mappings)
        )

    def build_delete_proto(self) -> Variant_DeleteAttribute:
        return Variant_DeleteAttribute(
            id=self.resource_id,
        )

    def build_create_proto(self) -> Variant_CreateAttribute:
        return Variant_CreateAttribute(
            id=self.resource_id,
            name=self.name,
            variant_values=VariantValues(values=self.mappings),
            references={},
        )

    def validate(self, resource_mappings: list[ResourceMapping], **kwargs):
        if not self.name:
            raise ValueError("Name is required")
        if not self.mappings:
            raise ValueError("Mappings are required")

        known_variant_id_to_name = {
            resource.resource_id: resource.resource_name
            for resource in resource_mappings
            if resource.resource_type == Variant
        }
        known_variants_ids = set(known_variant_id_to_name.keys())
        attribute_variants = set(self.mappings.keys())

        if additional_variants := attribute_variants - known_variants_ids:
            raise ValueError(f"Additional variants found for attribute: {additional_variants}")

        if missing_variants := known_variants_ids - attribute_variants:
            raise ValueError(
                f"Missing variants for variant attribute: {[known_variant_id_to_name[variant_id] for variant_id in missing_variants]}"
            )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        variant_attributes_path = os.path.join(base_path, "config", "variant_attributes.yaml")
        discovered_variant_attributes: list[str] = []

        if not os.path.exists(variant_attributes_path):
            return discovered_variant_attributes

        yaml_dict = Variant._get_top_level_data(variant_attributes_path)
        variant_attributes: list[dict] = yaml_dict.get("attributes", []) if yaml_dict else []

        for variant_attribute in variant_attributes:
            name = variant_attribute.get(VariantAttribute.resource_key)
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_variant_attributes.append(
                os.path.join(
                    variant_attributes_path, VariantAttribute.top_level_name, path_safe_name
                )
            )

        return discovered_variant_attributes
