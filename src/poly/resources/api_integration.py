"""Handling and managing Agent Studio API Configs

Copyright PolyAI Limited
"""

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
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
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    SubResource,
)

logger = logging.getLogger(__name__)

# RFC 3986 path chars + {param} placeholders (e.g. /users/{id}/orders)
OPERATION_RESOURCE_PATTERN = re.compile(
    r"^(/([a-zA-Z0-9._~!$&'()*+,;=:@%-]|%[0-9A-Fa-f]{2}|\{[a-zA-Z_][a-zA-Z0-9_]*\})*)+$"
)

AVAILABLE_OPERATIONS = {"GET", "POST", "PATCH", "PUT", "DELETE"}
AVAILABLE_AUTH_TYPES = {"none", "basic", "apiKey", "oauth2"}

# Matches an empty string (no URL configured) or a valid http(s) base URL
URL_PATTERN = re.compile(r"^(https?://[^\s]+)?$")


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

    @property
    def command_type(self) -> str:
        return "api_integration_operation"

    def to_yaml_dict(self) -> dict:
        return {
            "name": self.name,
            "method": self.method,
            "resource": self.resource,
        }

    def build_create_proto(self) -> ApiIntegrationOperation_Create:
        return ApiIntegrationOperation_Create(
            id=self.resource_id or str(uuid.uuid4()),
            name=self.name,
            method=self.method,
            resource=self.resource,
            integration_id=self.integration_id,
        )

    def build_update_proto(self) -> ApiIntegrationOperation_Update:
        return ApiIntegrationOperation_Update(
            id=self.resource_id,
            name=self.name,
            method=self.method,
            resource=self.resource,
            integration_id=self.integration_id,
        )

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
        return cls(
            resource_id=data.get("resource_id") or data.get("id", ""),
            name=data.get("name", ""),
            method=data.get("method", "").upper(),
            resource=data.get("resource", ""),
        )


@dataclass
class ApiIntegration(MultiResourceYamlResource):
    """Dataclass representing an API integration."""

    top_level_name: ClassVar[str] = "api_integrations"
    resource_id_prefix: ClassVar[str] = "API-INTEGRATION"
    description: str = ""
    environments: ApiIntegrationEnvironments = field(default_factory=ApiIntegrationEnvironments)
    operations: list[ApiIntegrationOperation] = field(default_factory=list)

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
            "operations": [op.to_yaml_dict() for op in self.operations],
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
            name=name,
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
        """Return new, updated, and deleted operations and environment configs (integration_id set)."""
        old_integration = old_resource if isinstance(old_resource, ApiIntegration) else None
        old_ops_list = old_integration.operations if old_integration else []
        old_ops: dict[str, ApiIntegrationOperation] = {}
        for op_obj in old_ops_list:
            old_ops[op_obj.resource_id] = op_obj
        new_ops: list[SubResource] = []
        updated_ops: list[SubResource] = []
        deleted_ops: list[SubResource] = []

        for op_obj in self.operations:
            old = old_ops.get(op_obj.resource_id)
            op_with_parent = ApiIntegrationOperation(
                resource_id=op_obj.resource_id,
                name=op_obj.name,
                method=op_obj.method,
                resource=op_obj.resource,
                integration_id=self.resource_id,
            )
            if old is None:
                new_ops.append(op_with_parent)
            else:
                if (
                    old.name != op_obj.name
                    or old.method != op_obj.method
                    or old.resource != op_obj.resource
                ):
                    updated_ops.append(op_with_parent)

        for key, old in old_ops.items():
            if not any(o.resource_id == key for o in self.operations):
                deleted_ops.append(
                    ApiIntegrationOperation(
                        resource_id=old.resource_id,
                        name=old.name,
                        method=old.method,
                        resource=old.resource,
                        integration_id=self.resource_id,
                    )
                )

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
