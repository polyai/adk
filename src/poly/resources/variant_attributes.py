"""Handling and managing an Agent Studio Variant Attributes

Copyright PolyAI Limited
"""

import json
import logging
import math
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from google.protobuf.struct_pb2 import Struct

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.variant_pb2 import (
    AttributeType,
    AttributeValues,
    EnumConfig,
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


class AttributeKind(str, Enum):
    """Enum representing the declared type of a variant attribute."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    OBJECT = "object"


# Ordinal mapping for the proto AttributeKind enum, which projections send as a raw int
# rather than the string values used in YAML.
ATTRIBUTE_KIND_FROM_PROTO_INT: dict[int, AttributeKind] = {
    0: AttributeKind.STRING,
    1: AttributeKind.NUMBER,
    2: AttributeKind.BOOLEAN,
    3: AttributeKind.ENUM,
    4: AttributeKind.OBJECT,
}

ATTRIBUTE_KIND_TO_PROTO_INT: dict[AttributeKind, int] = {
    kind: value for value, kind in ATTRIBUTE_KIND_FROM_PROTO_INT.items()
}


def _normalise_number(value: Any) -> Any:
    """Collapse whole floats to int so YAML and the platform agree on `3` vs `3.0`.

    Values cross the wire in a protobuf Struct, which holds every number as a double.
    Without this, an attribute written as `3` locally would read back as `3.0` and show
    up as a phantom diff on every status/push.
    """
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def parse_attribute_value(value: Any, kind: "AttributeKind", enum_values: list[str]) -> Any:
    """Coerce a value read from YAML or a projection into its declared native type.

    Mirrors the platform's `parseValueForKind`. Values are stored as strings on disk
    (see `to_yaml_dict`), so this is the inverse of `stringify_attribute_value` — but a
    value that is already native is passed straight through, so a hand-written `3` or
    `true` works as naturally as the quoted form ADK writes.

    A value that cannot be read as its kind is returned untouched rather than raising,
    so `validate` can report it against its variant instead of blowing up mid-parse.
    """
    if isinstance(value, str):
        value = value.strip()
    if is_unset_attribute_value(value):
        return None if kind != AttributeKind.STRING else value

    match kind:
        case AttributeKind.NUMBER:
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return _normalise_number(value)
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return value
            # Reject nan/inf: their JSON form is null, so they would not round-trip.
            return _normalise_number(parsed) if math.isfinite(parsed) else value
        case AttributeKind.BOOLEAN:
            if isinstance(value, bool):
                return value
            if isinstance(value, str) and value.lower() in ("true", "false"):
                return value.lower() == "true"
            return value
        case AttributeKind.OBJECT:
            if isinstance(value, (dict, list)):
                return value
            try:
                parsed = json.loads(value)
            except (TypeError, ValueError):
                return value
            return parsed if isinstance(parsed, (dict, list)) else value
        case _:
            # STRING and ENUM are both stored as-is; an unquoted scalar becomes its
            # text so an older or hand-written file reads without complaint.
            if isinstance(value, bool) or isinstance(value, (int, float)):
                return stringify_attribute_value(value)
            return value


def is_unset_attribute_value(value: Any) -> bool:
    """Whether a stored attribute value means "unset".

    Mirrors the platform's `isUnsetVariantValue`: `''` is the legacy marker written into
    the string `values` map, `None` the one written into `typed_values` for a typed
    attribute. Both mean the author has not given this variant a value.
    """
    return value is None or value == ""


def stringify_attribute_value(value: Any) -> str:
    """Stringify a native value for the legacy `values` map.

    Mirrors the platform's `stringifyValue`: objects and lists are JSON, everything
    else is `str(value)`, and unset is the empty string.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"))
    return str(value)


def _build_struct(values: dict[str, Any]) -> Struct:
    """Build a protobuf Struct from native Python values, preserving nulls."""
    struct = Struct()
    struct.update(values)
    return struct


def _merge_variant_values(variant_attribute_values: dict) -> dict[str, Any]:
    """Merge one variant's legacy string values with its native `typedValues`.

    Mirrors the platform's `safeMergeVariantValues`: the native value wins per key, but
    a `typedValues` that is not a mapping (corrupted or pre-typed data) is discarded
    rather than merged, since spreading it would silently produce a partial result.
    """
    values = variant_attribute_values.get("values") or {}
    typed_values = variant_attribute_values.get("typedValues")
    if not isinstance(typed_values, dict):
        return dict(values)
    return {**values, **typed_values}


def _read_attribute_type(type_data: dict | None) -> tuple[AttributeKind, dict]:
    """Parse an attribute's declared type out of a projection.

    Returns the kind and its flattened config. Projections carry `kind` as the proto
    ordinal and wrap the `config` oneof the way ts-proto does — `{"$case": "enumConfig",
    "value": {...}}` — which is flattened here to the plain config dict used in YAML.
    Data written before typed attributes existed has no `type` at all and reads as STRING.
    """
    if not isinstance(type_data, dict):
        return AttributeKind.STRING, {}

    raw_kind = type_data.get("kind", 0)
    if isinstance(raw_kind, str):
        # The platform keeps `kind` numeric end to end; a token is only ever seen from
        # a hand-written or legacy payload. Accept it rather than silently reading an
        # ENUM as a STRING, which would drop the type on the next push. An unrecognised
        # token falls back like an unrecognised ordinal does — one odd attribute must
        # not fail the whole pull, which is the tolerance #299 established here.
        try:
            kind = AttributeKind(raw_kind.removeprefix("ATTRIBUTE_KIND_").strip().lower())
        except ValueError:
            logger.debug("Unknown variant attribute kind %r, reading as string.", raw_kind)
            kind = AttributeKind.STRING
    else:
        kind = ATTRIBUTE_KIND_FROM_PROTO_INT.get(raw_kind, AttributeKind.STRING)

    config = type_data.get("config")
    if isinstance(config, dict):
        # ts-proto oneof wrapper; older payloads set the member directly.
        config = config.get("value", config)
    if not isinstance(config, dict):
        config = type_data.get("enum_config") or type_data.get("enumConfig") or {}

    return kind, utils.convert_keys_to_snake_case(config or {})


@register_resource("variants")
@dataclass
class Variant(MultiResourceYamlResource):
    """Dataclass representing a variant"""

    is_default: bool = False
    top_level_name: ClassVar[str] = "variants"
    # Seed values for the attributes a newly created variant must carry, as
    # {attribute_id: unset marker}. Filled in at push time by
    # prepush.default_new_variant_attributes; never read from or written to YAML.
    attribute_values: dict[str, Any] = field(default_factory=dict, repr=False, init=False)

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
        self.attribute_values = {}

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
        # A new variant must carry an entry for every attribute, but has no values of
        # its own yet — the real values arrive with the attribute updates that follow.
        # A typed attribute cannot hold "", so its seed is a native null in
        # typed_values; the string map keeps "" so legacy readers see what they always did.
        typed_seeds = {
            attribute_id: value
            for attribute_id, value in self.attribute_values.items()
            if value is None
        }
        return Variant_CreateVariant(
            id=self.resource_id,
            name=self.name,
            attribute_values=AttributeValues(
                values={attribute_id: "" for attribute_id in self.attribute_values},
                typed_values=_build_struct(typed_seeds),
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

    mappings: dict[str, Any]
    kind: AttributeKind = AttributeKind.STRING
    config: dict = field(default_factory=dict)
    top_level_name: ClassVar[str] = "attributes"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        mappings: dict[str, Any] | None = None,
        kind: str | AttributeKind = AttributeKind.STRING,
        config: dict | None = None,
        slim: bool = False,
    ):
        self.resource_id = resource_id
        self.name = name
        self.slim = slim
        # kind and config first: parsing each value needs the declared type.
        self.kind = AttributeKind(kind) if isinstance(kind, str) else kind
        self.config = utils.convert_keys_to_snake_case(config or {})
        self.mappings = {
            variant_id: parse_attribute_value(value, self.kind, self.enum_values)
            for variant_id, value in (mappings or {}).items()
        }

    @property
    def enum_values(self) -> list[str]:
        """Allowed values for an ENUM attribute; empty for every other kind."""
        values = self.config.get("values") if self.kind == AttributeKind.ENUM else None
        return list(values) if isinstance(values, list) else []

    def to_yaml_dict(self) -> dict:
        yaml_dict: dict[str, Any] = {"name": self.name}
        # An untyped attribute is a string one, so a STRING attribute is left
        # un-annotated: `kind: string` carries no information, and writing it would
        # rewrite the file for every project that has never used a type.
        if self.kind != AttributeKind.STRING:
            yaml_dict["kind"] = self.kind.value
        if self.config:
            yaml_dict["config"] = dict(self.config)
        # Values are written as strings — the same strings the platform keeps in its
        # legacy `values` map, with `kind` saying how to read them. Writing them
        # natively would be prettier, but an ADK released before typed attributes
        # calls .strip() on every value and would die on an int, bool or nested map
        # the moment it read a file a newer ADK had written.
        yaml_dict["values"] = {
            variant_id: stringify_attribute_value(value)
            for variant_id, value in self.mappings.items()
        }
        return yaml_dict

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
        kind = yaml_dict.get("kind") or AttributeKind.STRING
        if isinstance(kind, str):
            try:
                kind = AttributeKind(kind.strip().lower())
            except ValueError:
                raise ValueError(
                    f"Unknown attribute kind '{kind}'. "
                    f"Expected one of: {', '.join(k.value for k in AttributeKind)}"
                ) from None
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            mappings=yaml_dict.get("values") or {},
            kind=kind,
            config=yaml_dict.get("config") or {},
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
            kind, config = _read_attribute_type(attribute_data.get("type"))
            variant_attributes[attribute_id] = cls(
                resource_id=attribute_id,
                name=attribute_data["name"],
                mappings={},
                kind=kind,
                config=config,
            )
        if not variant_attributes:
            return {}

        for variant_id, variant_attribute_values in (
            projection.get("variantManagement", {})
            .get("variantAttributeValues", {})
            .get("entities", {})
            .items()
        ):
            for attribute_id, attribute_value in _merge_variant_values(
                variant_attribute_values
            ).items():
                if attribute_id in variant_attributes:
                    attribute = variant_attributes[attribute_id]
                    # A legacy value arrives only in the string map; parsing it against
                    # the declared kind gives the same native value a typed one has.
                    attribute.mappings[variant_id] = parse_attribute_value(
                        attribute_value, attribute.kind, attribute.enum_values
                    )

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
        # `values:` with nothing under it parses as None, not {}. Tolerate it here so
        # the empty attribute reaches validate() and fails with "Mappings are required"
        # rather than an AttributeError from the pretty path.
        new_mapping = {
            variant_ids_to_names.get(variant_id, variant_id): variant_value
            for variant_id, variant_value in (d.get("values") or {}).items()
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
        for variant_name, variant_value in (yaml_dict.get("values") or {}).items():
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

    def build_type_proto(self) -> AttributeType:
        """Build the declared type, with its config for the kinds that have one."""
        if self.kind == AttributeKind.ENUM:
            return AttributeType(
                kind=ATTRIBUTE_KIND_TO_PROTO_INT[self.kind],
                enum_config=EnumConfig(values=self.enum_values),
            )
        return AttributeType(kind=ATTRIBUTE_KIND_TO_PROTO_INT[self.kind])

    def build_variant_values_proto(self) -> VariantValues:
        """Dual-write the per-variant values: stringified for legacy readers, native for typed ones.

        A STRING attribute writes only the string map — it is what it has always
        written, and `typed_values` would add nothing.
        """
        values = {
            variant_id: stringify_attribute_value(value)
            for variant_id, value in self.mappings.items()
        }
        if self.kind == AttributeKind.STRING:
            return VariantValues(values=values)
        return VariantValues(values=values, typed_values=_build_struct(dict(self.mappings)))

    def build_update_proto(self) -> Variant_UpdateAttribute:
        return Variant_UpdateAttribute(
            id=self.resource_id,
            name=self.name,
            variant_values=self.build_variant_values_proto(),
            type=self.build_type_proto(),
        )

    def build_delete_proto(self) -> Variant_DeleteAttribute:
        return Variant_DeleteAttribute(
            id=self.resource_id,
        )

    def build_create_proto(self) -> Variant_CreateAttribute:
        return Variant_CreateAttribute(
            id=self.resource_id,
            name=self.name,
            variant_values=self.build_variant_values_proto(),
            type=self.build_type_proto(),
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

        self._validate_config()
        for variant_id, value in self.mappings.items():
            if not self._value_matches_kind(value):
                variant_name = known_variant_id_to_name.get(variant_id, variant_id)
                raise ValueError(
                    f"Value for variant '{variant_name}' does not match the declared "
                    f"type of attribute '{self.name}': expected {self._describe_kind()}, "
                    f"got {value!r}"
                )

    def _describe_kind(self) -> str:
        """Human-readable form of the declared type, for validation messages."""
        if self.kind == AttributeKind.ENUM:
            return f"enum ({', '.join(self.enum_values)})"
        return self.kind.value

    def _validate_config(self) -> None:
        """Check the type's config is well formed for its kind."""
        if self.kind != AttributeKind.ENUM:
            if self.config:
                raise ValueError(f"Attribute kind '{self.kind.value}' does not take a config")
            return

        values = self.config.get("values")
        if not isinstance(values, list) or not values:
            raise ValueError("An enum attribute needs a non-empty 'config.values' list")
        if any(not isinstance(value, str) for value in values):
            raise ValueError("Enum values must be strings")
        if len(set(values)) != len(values):
            raise ValueError(f"Duplicate enum values for attribute '{self.name}': {values}")

    def _value_matches_kind(self, value: Any) -> bool:
        """Whether one value is valid for the declared type.

        Mirrors the platform's `validateValueMatchesType`, including its treatment of
        unset: a blank value is valid for every kind, so an attribute can be added
        before every variant has been given a value.
        """
        if is_unset_attribute_value(value):
            return True
        match self.kind:
            case AttributeKind.NUMBER:
                # bool is an int subclass in Python, but is not a number here.
                # The platform checks Number.isFinite, so a YAML `.inf` or `.nan`
                # has to fail here rather than at push time — neither survives the
                # JSON round trip through typed_values anyway.
                return (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                )
            case AttributeKind.BOOLEAN:
                return isinstance(value, bool)
            case AttributeKind.ENUM:
                return isinstance(value, str) and value in self.enum_values
            case AttributeKind.OBJECT:
                return isinstance(value, (dict, list))
            case _:
                return isinstance(value, str)

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
