"""Handling and managing Agent Studio API Configs

Copyright PolyAI Limited
"""

import copy
import json
import logging
import os
import re
import uuid
from dataclasses import dataclass, field, replace
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf import api_integrations_pb2
from poly.handlers.protobuf.api_integrations_pb2 import (
    ApiIntegration_Create,
    ApiIntegration_Delete,
    ApiIntegration_Update,
    ApiIntegrationConfig_Update,
    ApiIntegrationOperation_Create,
    ApiIntegrationOperation_Delete,
    ApiIntegrationOperation_Update,
    Environments,
    OperationHeaders,
    OperationResponseSchemas,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    SubResource,
    register_resource,
)

logger = logging.getLogger(__name__)

# RFC 3986 path + {param} placeholders; optional ?query (query allows pchar, /, ?)
OPERATION_RESOURCE_PATTERN = re.compile(
    r"^(/([a-zA-Z0-9._~!$&'()*+,;=:@%-]|%[0-9A-Fa-f]{2}|\{[a-zA-Z_][a-zA-Z0-9_]*\})*)+"
    r"(?:\?([a-zA-Z0-9._~!$&'()*+,;=:@%/?-]|%[0-9A-Fa-f]{2}|\{[a-zA-Z_][a-zA-Z0-9_]*\})*)?$"
)

AVAILABLE_OPERATIONS = {"GET", "POST", "PATCH", "PUT", "DELETE"}
AVAILABLE_AUTH_TYPES = {
    "none",
    "basic",
    "apiKey",
    "oauth2",
    "oauth2_client_credentials",
    "jwt_client_assertion",
}

# Matches an empty string (no URL configured) or a valid http(s) base URL
URL_PATTERN = re.compile(r"^(https?://[^\s]+)?$")

# The platform's rules for an operation's headers and description, mirrored so a bad
# push fails in `poly validate` rather than on the server.
HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+^_`|~0-9A-Za-z-]+$")
# Authorization comes from the environment's auth config and Host from its base URL.
RESERVED_HEADER_NAMES = {"authorization", "host"}
MAX_OPERATION_HEADERS = 50
HEADER_VALUE_MAX = 4096
OPERATION_DESCRIPTION_MAX = 1000


def _is_valid_header_value(value: str) -> bool:
    """ASCII with no control characters other than tab, and no leading or trailing space."""
    return value == value.strip() and all(
        0x20 <= ord(char) < 0x7F or char == "\t" for char in value
    )


def _bool_header_text(value: bool) -> str:
    """`x-flag: true` as the platform stores it; plain `str()` would send Python's `"True"`."""
    return "true" if value else "false"


# An operation's request and response schemas are JSON Schema 2020-12, written as YAML
# mappings in the file and stored as JSON text by the platform. These mirror its rules.
SCHEMA_SOURCES = {"default", "manual", "observed", "openapi"}
# The label for a hand-written schema, and what one written without `schema_source` is
# pushed as. Not to be confused with `default`, which marks a prebuilt template's schema.
HAND_WRITTEN_SCHEMA_SOURCE = "manual"
JSON_SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
MAX_SCHEMA_BYTES = 65_536
MAX_SCHEMA_DEPTH = 64
RESPONSE_KEY_PATTERN = re.compile(r"^([1-5]\d{2}|[1-5]XX|default)$")
BODYLESS_METHODS = {"GET", "DELETE"}


def _stringify_keys(node: object) -> object:
    """Make every mapping key text: YAML reads `200:` as an int, JSON and hashing need str."""
    if isinstance(node, dict):
        return {str(key): _stringify_keys(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_stringify_keys(item) for item in node]
    return node


def _parse_schema(value: object) -> object:
    """A schema as an object: the projection carries JSON text, YAML and status files objects.

    None and "" mean unset. Text that isn't JSON is kept as-is so validate() can report it.
    """
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return value
    return _stringify_keys(value)


def _schema_text(schema: object) -> str:
    """The JSON text sent to the platform, and the text its size limit is measured on."""
    return json.dumps(schema, separators=(",", ":"), ensure_ascii=False)


def _depth(node: object, level: int = 1) -> int:
    """How deep objects and arrays nest, the root being 1. Like the platform, scalar leaves
    don't count, so 64 nested objects ending in `"type": "string"` are 64 deep."""
    if isinstance(node, dict):
        children = node.values()
    elif isinstance(node, list):
        children = node
    else:
        return level - 1
    return max([level, *(_depth(child, level + 1) for child in children)])


def _validate_json_schema(schema: object, where: str) -> None:
    """Raise ValueError for a schema the platform would refuse."""
    if not isinstance(schema, dict):
        raise ValueError(f"{where} must be a JSON Schema object (a YAML mapping).")
    dialect = schema.get("$schema")
    if dialect is not None and dialect not in (JSON_SCHEMA_DIALECT, f"{JSON_SCHEMA_DIALECT}#"):
        raise ValueError(f"{where}: $schema must be {JSON_SCHEMA_DIALECT} or omitted.")
    if _depth(schema) > MAX_SCHEMA_DEPTH:
        raise ValueError(f"{where} nests deeper than {MAX_SCHEMA_DEPTH} levels.")
    try:
        size = len(_schema_text(schema).encode("utf-8"))
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"{where} is not valid JSON ({error}); quote dates and other special values."
        ) from error
    if size > MAX_SCHEMA_BYTES:
        raise ValueError(f"{where} is {size} bytes; the limit is {MAX_SCHEMA_BYTES} bytes.")

    # Imported here so the CLI doesn't pay for jsonschema at startup.
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError

    try:
        # No format checks: the platform compiles `pattern` as a JavaScript regex, which
        # Python's `re` disagrees with both ways (`\p{L}`, `(?P<id>...)`), and checks the
        # `$ref`/`$id` URIs itself on push.
        Draft202012Validator.check_schema(schema, format_checker=None)
    except SchemaError as error:
        path = "/".join(str(part) for part in error.absolute_path) or "the root"
        raise ValueError(
            f"{where} is not a valid JSON Schema at {path}: {error.message}"
        ) from error


def _default_config() -> "ApiIntegrationConfig":
    return ApiIntegrationConfig(base_url="", auth_type="none")


def _default_environments() -> "ApiIntegrationEnvironments":
    c = _default_config()
    return ApiIntegrationEnvironments(sandbox=c, pre_release=c, live=c)


@dataclass
class ApiIntegrationConfig(SubResource):
    """Per-environment API config (base URL and auth type)."""

    base_url: str = ""
    auth_type: str = "none"
    resource_id: str = ""
    name: str = ""  # environment name: sandbox, pre_release, live
    integration_id: str = ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ApiIntegrationConfig):
            return NotImplemented
        return self.base_url == other.base_url and self.auth_type == other.auth_type

    @property
    def command_type(self) -> str:
        return "api_integration_config"

    def validate(self, env_name: str = "") -> None:
        """Validate the environment config's fields."""
        label = f"Environment '{env_name}': " if env_name else ""
        if not URL_PATTERN.fullmatch(self.base_url):
            raise ValueError(f"{label}base_url '{self.base_url}' is not a valid URL path.")
        if not self.base_url and self.auth_type is not None and self.auth_type != "none":
            raise ValueError(f"{label}base_url cannot be empty.")
        if self.auth_type not in AVAILABLE_AUTH_TYPES:
            raise ValueError(
                f"{label}auth_type '{self.auth_type}' invalid, "
                f"must be one of {sorted(AVAILABLE_AUTH_TYPES)}."
            )

    def to_yaml_dict(self) -> dict:
        return {"base_url": self.base_url, "auth_type": self.auth_type}

    def to_proto(self) -> api_integrations_pb2.ApiIntegrationConfig:
        return api_integrations_pb2.ApiIntegrationConfig(
            base_url=self.base_url,
            auth_type=self.auth_type,
        )

    def build_create_proto(self) -> None:
        raise NotImplementedError("ApiIntegrationConfig cannot be created independently.")

    def build_delete_proto(self) -> None:
        raise NotImplementedError("ApiIntegrationConfig cannot be deleted independently.")

    def build_update_proto(
        self,
    ) -> ApiIntegrationConfig_Update:
        """Build proto for push; uses integration_id and name (environment) set by parent."""
        api_env = "pre-release" if self.name == "pre_release" else self.name
        return self.build_config_update_proto(self.integration_id, api_env)

    def build_config_update_proto(
        self, integration_id: str, environment: str
    ) -> ApiIntegrationConfig_Update:
        """Build proto to update this config for one environment."""
        return ApiIntegrationConfig_Update(
            id=integration_id,
            environment=environment,
            base_url=self.base_url,
            auth_type=self.auth_type,
        )

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApiIntegrationConfig":
        if not data:
            return cls()
        data = utils.convert_keys_to_snake_case(data)
        return cls(
            base_url=data.get("base_url", ""),
            auth_type=data.get("auth_type") or "none",
        )


@dataclass
class ApiIntegrationEnvironments:
    """Nested environments: sandbox, pre_release, live."""

    sandbox: ApiIntegrationConfig = field(default_factory=_default_config)
    pre_release: ApiIntegrationConfig = field(default_factory=_default_config)
    live: ApiIntegrationConfig = field(default_factory=_default_config)

    def __init__(
        self,
        sandbox: ApiIntegrationConfig | None = None,
        pre_release: ApiIntegrationConfig | None = None,
        live: ApiIntegrationConfig | None = None,
    ) -> None:
        self.sandbox = sandbox if sandbox is not None else _default_config()
        self.pre_release = pre_release if pre_release is not None else _default_config()
        self.live = live if live is not None else _default_config()

    def to_yaml_dict(self) -> dict:
        # YAML uses "pre-release"; code uses pre_release
        return {
            "sandbox": self.sandbox.to_yaml_dict(),
            "pre-release": self.pre_release.to_yaml_dict(),
            "live": self.live.to_yaml_dict(),
        }

    def to_proto(self) -> Environments:
        return Environments(
            sandbox=self.sandbox.to_proto(),
            pre_release=self.pre_release.to_proto(),
            live=self.live.to_proto(),
        )

    def build_create_proto(self) -> Environments:
        """Environments are created as part of ApiIntegration_Create; same as to_proto()."""
        return self.to_proto()

    def build_update_proto(self, integration_id: str) -> list[ApiIntegrationConfig_Update]:
        """One config update per environment (sandbox, pre_release, live) for update_api_integration_config."""
        return [
            self.sandbox.build_config_update_proto(integration_id, "sandbox"),
            self.pre_release.build_config_update_proto(integration_id, "pre-release"),
            self.live.build_config_update_proto(integration_id, "live"),
        ]

    def build_delete_proto(self) -> None:
        """No delete command for environments; they are part of the integration."""

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApiIntegrationEnvironments":
        if not data:
            return _default_environments()
        data = utils.convert_keys_to_snake_case(data)
        # YAML uses "pre-release"; code uses pre_release — accept both when reading
        pre_release_data = data.get("pre_release") or data.get("pre-release")
        return cls(
            sandbox=ApiIntegrationConfig.from_dict(data.get("sandbox")),
            pre_release=ApiIntegrationConfig.from_dict(pre_release_data),
            live=ApiIntegrationConfig.from_dict(data.get("live")),
        )


@dataclass(kw_only=True)
class ApiIntegrationOperation(SubResource):
    """Dataclass representing a single API operation."""

    resource_id: str = ""
    name: str = ""
    method: str = ""
    resource: str = ""
    integration_id: str = (
        ""  # Set by parent when yielding from get_new_updated_deleted_subresources
    )
    description: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    # None is "no schema"; {} is a real, permissive schema. Response schemas are keyed by
    # status code ("200"), status class ("4XX") or "default".
    request_query_schema: Optional[dict] = None
    request_body_schema: Optional[dict] = None
    response_schemas: dict[str, dict] = field(default_factory=dict)
    # Where the schemas came from (default | manual | observed | openapi), an audit label
    # the platform requires whenever a schema is set. "" when the operation has none.
    schema_source: str = ""

    @property
    def has_schemas(self) -> bool:
        return (
            self.request_query_schema is not None
            or self.request_body_schema is not None
            or bool(self.response_schemas)
        )

    def _effective_schema_source(self) -> Optional[str]:
        """The source pushed with the schemas: the YAML's, or the default when it has none."""
        if not self.has_schemas:
            return None
        return self.schema_source or HAND_WRITTEN_SCHEMA_SOURCE

    def validate(self) -> None:
        """Validate the operation's fields."""
        if not self.name:
            raise ValueError("Operation name cannot be empty.")
        if not self.method:
            raise ValueError(f"Operation '{self.name}': method cannot be empty.")
        if self.method not in AVAILABLE_OPERATIONS:
            raise ValueError(
                f"Operation '{self.name}': method '{self.method}' invalid, "
                f"must be one of {sorted(AVAILABLE_OPERATIONS)}."
            )
        if not self.resource:
            raise ValueError(f"Operation '{self.name}': resource cannot be empty.")
        if not OPERATION_RESOURCE_PATTERN.fullmatch(self.resource):
            raise ValueError(
                f"Operation '{self.name}': resource '{self.resource}' is not a valid URL path."
            )
        self._validate_description()
        self._validate_headers()
        self._validate_schemas()

    def _validate_description(self) -> None:
        label = f"Operation '{self.name}': "
        if not isinstance(self.description, str):
            raise ValueError(f"{label}description must be text.")
        if len(self.description) > OPERATION_DESCRIPTION_MAX:
            raise ValueError(
                f"{label}description is longer than {OPERATION_DESCRIPTION_MAX} characters."
            )

    def _validate_headers(self) -> None:
        label = f"Operation '{self.name}': "
        if not isinstance(self.headers, dict):
            raise ValueError(f"{label}headers must be a mapping of header name to value.")
        if len(self.headers) > MAX_OPERATION_HEADERS:
            raise ValueError(
                f"{label}has {len(self.headers)} headers; the limit is {MAX_OPERATION_HEADERS}."
            )
        seen: set[str] = set()
        for header_name, value in self.headers.items():
            if not HEADER_NAME_PATTERN.fullmatch(header_name):
                raise ValueError(
                    f"{label}header name '{header_name}' is not a valid HTTP header name."
                )
            lowered = header_name.lower()
            if lowered in RESERVED_HEADER_NAMES:
                raise ValueError(
                    f"{label}header '{header_name}' is set from the environment config "
                    "and cannot be set per operation."
                )
            if lowered in seen:
                raise ValueError(
                    f"{label}duplicate header '{header_name}' (header names are case-insensitive)."
                )
            seen.add(lowered)
            if not isinstance(value, str):
                raise ValueError(
                    f"{label}header '{header_name}' value must be text; quote it in YAML."
                )
            if len(value) > HEADER_VALUE_MAX:
                raise ValueError(
                    f"{label}header '{header_name}' value is longer than "
                    f"{HEADER_VALUE_MAX} characters."
                )
            if not _is_valid_header_value(value):
                raise ValueError(
                    f"{label}header '{header_name}' value cannot contain line breaks, control "
                    "characters or non-ASCII characters, or start or end with a space."
                )

    def _validate_schemas(self) -> None:
        label = f"Operation '{self.name}': "
        if self.request_query_schema is not None:
            _validate_json_schema(self.request_query_schema, f"{label}request_query_schema")
        if self.request_body_schema is not None:
            if self.method in BODYLESS_METHODS:
                raise ValueError(
                    f"{label}{self.method} requests have no body; remove request_body_schema "
                    "or change the method."
                )
            _validate_json_schema(self.request_body_schema, f"{label}request_body_schema")
        if not isinstance(self.response_schemas, dict):
            raise ValueError(f"{label}response_schemas must be a mapping of status code to schema.")
        for key, schema in self.response_schemas.items():
            if not RESPONSE_KEY_PATTERN.fullmatch(key):
                raise ValueError(
                    f"{label}response_schemas key '{key}' must be a status code ('200'), "
                    "a status class ('4XX') or 'default'."
                )
            _validate_json_schema(schema, f"{label}response_schemas['{key}']")
        if self.schema_source and self.schema_source not in SCHEMA_SOURCES:
            raise ValueError(
                f"{label}schema_source '{self.schema_source}' invalid, "
                f"must be one of {sorted(SCHEMA_SOURCES)}."
            )

    @property
    def command_type(self) -> str:
        return "api_integration_operation"

    def same_definition(self, other: "ApiIntegrationOperation") -> bool:
        """Whether both operations describe the same platform state, ids aside.

        Schemas compare as parsed objects, so key order or the platform's JSON formatting
        never counts as a change, and a YAML that omits `schema_source` matches the default.
        """
        return (
            self.name == other.name
            and self.method == other.method
            and self.resource == other.resource
            and self.description == other.description
            and self.headers == other.headers
            and self.same_schemas(other)
            and self._effective_schema_source() == other._effective_schema_source()
        )

    def same_schemas(self, other: "ApiIntegrationOperation") -> bool:
        return (
            self.request_query_schema == other.request_query_schema
            and self.request_body_schema == other.request_body_schema
            and self.response_schemas == other.response_schemas
        )

    def is_hand_edit_of(self, old: "ApiIntegrationOperation") -> bool:
        """Whether the schemas were edited but kept the label `old` was pulled with.

        Such an edit is the user's, not the earlier writer's: the platform requires a
        source on every schema write so that a new schema never inherits the old label.
        """
        return (
            self.has_schemas
            and not self.same_schemas(old)
            and self._effective_schema_source() == old._effective_schema_source()
        )

    def to_yaml_dict(self) -> dict:
        # The description comes straight after the name, so it reads as the operation's heading.
        data = {"name": self.name}
        if self.description:
            data["description"] = self.description
        data["method"] = self.method
        data["resource"] = self.resource
        if self.headers:
            # A non-mapping is kept as written so validate() reports it, rather than the
            # hash or the diff crashing first.
            data["headers"] = dict(self.headers) if isinstance(self.headers, dict) else self.headers
        # Copies, so a schema shared between operations is never written as a YAML alias.
        if self.request_query_schema is not None:
            data["request_query_schema"] = copy.deepcopy(self.request_query_schema)
        if self.request_body_schema is not None:
            data["request_body_schema"] = copy.deepcopy(self.request_body_schema)
        if self.response_schemas:
            data["response_schemas"] = copy.deepcopy(self.response_schemas)
        if self.has_schemas and self.schema_source:
            data["schema_source"] = self.schema_source
        return data

    def _response_schema_texts(self) -> dict[str, str]:
        return {key: _schema_text(schema) for key, schema in self.response_schemas.items()}

    def build_create_proto(self) -> ApiIntegrationOperation_Create:
        proto = ApiIntegrationOperation_Create(
            id=self.resource_id or str(uuid.uuid4()),
            name=self.name,
            method=self.method,
            resource=self.resource,
            integration_id=self.integration_id,
            headers=self.headers,
            response_schemas=self._response_schema_texts(),
        )
        if self.description:
            proto.description = self.description
        if self.request_query_schema is not None:
            proto.request_query_schema = _schema_text(self.request_query_schema)
        if self.request_body_schema is not None:
            proto.request_body_schema = _schema_text(self.request_body_schema)
        source = self._effective_schema_source()
        if source:
            proto.schema_source = source
        return proto

    def build_update_proto(self) -> ApiIntegrationOperation_Update:
        # The YAML is the full desired state, so every field is sent: an empty wrapper, an
        # empty description or an empty schema clears what the platform holds, where an
        # unsent one keeps it. The source only travels with a schema; the platform refuses
        # a bare one.
        proto = ApiIntegrationOperation_Update(
            id=self.resource_id,
            name=self.name,
            method=self.method,
            resource=self.resource,
            integration_id=self.integration_id,
            description=self.description,
            headers=OperationHeaders(entries=self.headers),
            request_query_schema=(
                "" if self.request_query_schema is None else _schema_text(self.request_query_schema)
            ),
            request_body_schema=(
                "" if self.request_body_schema is None else _schema_text(self.request_body_schema)
            ),
            response_schemas=OperationResponseSchemas(entries=self._response_schema_texts()),
        )
        source = self._effective_schema_source()
        if source:
            proto.schema_source = source
        return proto

    def build_delete_proto(self) -> ApiIntegrationOperation_Delete:
        return ApiIntegrationOperation_Delete(
            id=self.resource_id,
            integration_id=self.integration_id,
        )

    @classmethod
    def from_dict(cls, data: dict | None) -> "ApiIntegrationOperation":
        if not data:
            return cls(resource_id="", name="")
        data = utils.convert_keys_to_snake_case(data)
        headers = data.get("headers") or {}
        if isinstance(headers, dict):
            # map<string, string> on the wire. YAML has already typed unquoted scalars, and
            # only a bool converts back to the text that was written (`1.10` loads as 1.1),
            # so every other non-string value is left for validate() to report.
            headers = {
                str(key): _bool_header_text(value) if isinstance(value, bool) else value
                for key, value in headers.items()
            }
        response_schemas = data.get("response_schemas") or {}
        if isinstance(response_schemas, dict):
            parsed = {str(key): _parse_schema(value) for key, value in response_schemas.items()}
            response_schemas = {key: schema for key, schema in parsed.items() if schema is not None}
        # `manual` is the default: the platform labels hand edits with it, and a schema
        # written without a source is pushed as it. Holding it as "" keeps the hash, the
        # diff and the file in agreement, so pulled files never carry the label.
        source = data.get("schema_source")
        if source is not None and str(source) == HAND_WRITTEN_SCHEMA_SOURCE:
            source = None
        operation = cls(
            resource_id=data.get("resource_id") or data.get("id", ""),
            name=data.get("name", ""),
            method=data.get("method", "").upper(),
            resource=data.get("resource", ""),
            description=data.get("description") or "",
            headers=headers,
            request_query_schema=_parse_schema(data.get("request_query_schema")),
            request_body_schema=_parse_schema(data.get("request_body_schema")),
            response_schemas=response_schemas,
            schema_source="" if source is None else str(source),
        )
        if not operation.has_schemas:
            # The platform labels every operation, schemas or not; without one the label
            # is noise in the file.
            operation.schema_source = ""
        return operation


@register_resource("api_integration")
@dataclass
class ApiIntegration(MultiResourceYamlResource):
    """Dataclass representing an API integration."""

    top_level_name: ClassVar[str] = "api_integrations"
    resource_id_prefix: ClassVar[str] = "API-INTEGRATION"
    description: str = ""
    environments: ApiIntegrationEnvironments = field(default_factory=ApiIntegrationEnvironments)
    operations: list[ApiIntegrationOperation] = field(default_factory=list)

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "ApiIntegration"]:
        """Parse API integrations from a projection dict."""
        if "apiIntegrations" not in projection:
            logger.debug("No read access to API integrations - it will not be pulled.")
            return {}

        api_integrations = {}
        for integration_id, integration_data in (
            projection.get("apiIntegrations", {})
            .get("apiIntegrations", {})
            .get("entities", {})
            .items()
        ):
            environments = ApiIntegrationEnvironments.from_dict(
                integration_data.get("environments")
            )
            operations_raw = integration_data.get("operations") or {}
            operations = [ApiIntegrationOperation.from_dict(v) for v in operations_raw.values()]

            api_integrations[integration_id] = cls(
                resource_id=integration_id,
                name=integration_data.get("name", ""),
                description=integration_data.get("description", ""),
                environments=environments,
                operations=operations,
            )
        return api_integrations

    def __init__(
        self,
        *,
        resource_id: str,
        name: str = "",
        description: str = "",
        environments: ApiIntegrationEnvironments | dict | None = None,
        operations: list[ApiIntegrationOperation | dict] | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description
        self.environments: ApiIntegrationEnvironments = (
            ApiIntegrationEnvironments.from_dict(environments)
            if isinstance(environments, dict)
            else environments or _default_environments()
        )
        self.operations: list[ApiIntegrationOperation] = [
            ApiIntegrationOperation.from_dict(op) if isinstance(op, dict) else op
            for op in (operations or [])
        ]

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join("config", "api_integrations.yaml", self.top_level_name, path_safe_name)

    def to_yaml_dict(self) -> dict:
        """Serialize to a dict for YAML; key order is stable for merge-friendly output."""
        return {
            "name": self.name,
            "description": self.description,
            "environments": self.environments.to_yaml_dict(),
            "operations": [
                op.to_yaml_dict() for op in sorted(self.operations, key=lambda op: op.name)
            ],
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str, **kwargs
    ) -> "ApiIntegration":
        env_data = yaml_dict.get("environments")
        environments = (
            ApiIntegrationEnvironments.from_dict(env_data) if env_data else _default_environments()
        )
        ops_data = yaml_dict.get("operations") or []
        if isinstance(ops_data, dict):
            ops_data = list(ops_data.values())
        operations = [ApiIntegrationOperation.from_dict(o) for o in ops_data]
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            description=yaml_dict.get("description", ""),
            environments=environments,
            operations=operations,
        )

    _NAME_PATTERN: ClassVar[re.Pattern] = re.compile(r"^[a-z_][a-z0-9_]*$")

    def validate(
        self,
        resource_mappings: list[ResourceMapping] | None = None,
        **kwargs,
    ) -> None:
        """Validate the API integration resource."""
        if not self.name:
            raise ValueError("Name cannot be empty.")
        if not self._NAME_PATTERN.fullmatch(self.name):
            raise ValueError(
                f"API integration name '{self.name}' must follow Python function naming convention "
                "(lowercase letters, numbers, and underscores only, starting with letter or underscore)."
            )

        for env_name in ("sandbox", "pre_release", "live"):
            config = getattr(self.environments, env_name, None)
            if config is not None:
                config.validate(env_name=env_name)

        seen: set[tuple[str, str]] = set()
        for op in self.operations:
            op.validate()

            key = (op.name, op.method)
            if key in seen:
                raise ValueError(f"Duplicate operation: name='{op.name}', method='{op.method}'.")
            seen.add(key)

    @property
    def command_type(self) -> str:
        return "api_integration"

    @property
    def update_command_type(self) -> str:
        return "update_api_integration"

    def build_create_proto(self) -> ApiIntegration_Create:
        return ApiIntegration_Create(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            environments=self.environments.to_proto(),
        )

    def build_update_proto(self) -> ApiIntegration_Update:
        return ApiIntegration_Update(
            id=self.resource_id,
            name=self.name,
            description=self.description,
        )

    def build_delete_proto(self) -> ApiIntegration_Delete:
        return ApiIntegration_Delete(id=self.resource_id)

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["ApiIntegration"]
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Return new, updated, and deleted operations and environment configs (integration_id set).

        Operations are matched by resource_id when present (local ops with explicit IDs), or by
        name when resource_id is absent (local ops loaded from YAML, which does not persist IDs).
        When matched by name, the remote resource_id is carried forward so that update commands
        target the correct remote resource.
        """
        old_integration = old_resource if isinstance(old_resource, ApiIntegration) else None
        old_ops_list = old_integration.operations if old_integration else []
        old_ops_by_id: dict[str, ApiIntegrationOperation] = {
            op.resource_id: op for op in old_ops_list if op.resource_id
        }
        old_ops_by_name: dict[str, ApiIntegrationOperation] = {op.name: op for op in old_ops_list}
        new_ops: list[SubResource] = []
        updated_ops: list[SubResource] = []
        deleted_ops: list[SubResource] = []
        matched_old_ids: set[str] = set()

        for op_obj in self.operations:
            # Prefer resource_id match; fall back to name match for YAML-loaded ops (no ID stored)
            old = (
                old_ops_by_id.get(op_obj.resource_id)
                if op_obj.resource_id
                else old_ops_by_name.get(op_obj.name)
            )
            # When matched by name but local op has no resource_id, borrow it from remote.
            # For genuinely new ops (no match), generate a stable UUID now so that multiple
            # new ops don't all collide on the "" key when stored in new_subresources.
            effective_id = op_obj.resource_id or (old.resource_id if old else str(uuid.uuid4()))
            # replace() carries every field, so a new one can't be silently dropped here.
            op_with_parent = replace(
                op_obj, resource_id=effective_id, integration_id=self.resource_id
            )
            if old is None:
                new_ops.append(op_with_parent)
            else:
                matched_old_ids.add(old.resource_id)
                if not old.same_definition(op_obj):
                    if op_obj.is_hand_edit_of(old):
                        # Pushed as hand-written. The file keeps the old label until the
                        # next pull, which brings `manual` down and drops the key.
                        op_with_parent.schema_source = ""
                    updated_ops.append(op_with_parent)

        for old in old_ops_list:
            if old.resource_id not in matched_old_ids:
                deleted_ops.append(replace(old, integration_id=self.resource_id))

        # Check environment configs (sandbox, pre_release, live) for updates
        env_names = ("sandbox", "pre_release", "live")
        old_envs = old_integration.environments if old_integration else None
        for env_name in env_names:
            old_config: ApiIntegrationConfig | None = getattr(old_envs, env_name, None)
            new_config: ApiIntegrationConfig | None = getattr(self.environments, env_name, None)
            if old_config is not None and new_config is not None and old_config != new_config:
                updated_ops.append(
                    ApiIntegrationConfig(
                        base_url=new_config.base_url,
                        auth_type=new_config.auth_type,
                        resource_id=f"{self.resource_id}:{env_name}",
                        name=env_name,
                        integration_id=self.resource_id,
                    )
                )

        return new_ops, updated_ops, deleted_ops

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Discover resources of this type in the given base path.

        Args:
            base_path (str): The base path to search for resources.

        Returns:
            list[str]: A list of file paths of discovered resources.
        """
        integration_path = os.path.join(base_path, "config", "api_integrations.yaml")
        discovered_integrations: list[str] = []

        if not os.path.exists(integration_path):
            return discovered_integrations

        yaml_dict = ApiIntegration._get_top_level_data(integration_path)
        integrations: list[dict] = yaml_dict.get("api_integrations", []) if yaml_dict else []

        for integration in integrations:
            name = integration.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_integrations.append(
                os.path.join(integration_path, ApiIntegration.top_level_name, path_safe_name)
            )

        return discovered_integrations
