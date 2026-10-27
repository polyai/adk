"""Handling and managing Agent Studio MCP servers

Copyright PolyAI Limited
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf import integrations_pb2
from poly.handlers.protobuf.integrations_pb2 import (
    MCPEnabledFunctions,
    MCPServer_Delete,
    MCPServer_Upsert,
)
from poly.resources.resource import MultiResourceYamlResource, register_resource

logger = logging.getLogger(__name__)

MCP_FILE = os.path.join("config", "mcp.yaml")

URL_PATTERN = re.compile(r"^https?://[^\s/?#]+[^\s]*$")

# Matches the range the Agent Studio UI and public API accept.
MIN_TIMEOUT_SECONDS = 1
MAX_TIMEOUT_SECONDS = 30


@dataclass
class MCPOAuth:
    """OAuth client-credentials settings for an MCP server.

    client_secret_name names a secret stored in Agent Studio; the secret value
    never passes through the ADK.
    """

    client_id: str = ""
    client_secret_name: str = ""
    token_url: str = ""
    audience: str = ""
    scope: str = ""

    def to_yaml_dict(self) -> dict:
        return {
            key: value
            for key, value in (
                ("client_id", self.client_id),
                ("client_secret_name", self.client_secret_name),
                ("token_url", self.token_url),
                ("audience", self.audience),
                ("scope", self.scope),
            )
            if value
        }

    def to_proto(self) -> integrations_pb2.MCPOAuth:
        return integrations_pb2.MCPOAuth(
            client_id=self.client_id,
            client_secret_name=self.client_secret_name,
            token_url=self.token_url,
            audience=self.audience,
            scope=self.scope,
        )

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["MCPOAuth"]:
        """Build from a projection (camelCase) or YAML (snake_case) dict."""
        if not data:
            return None
        data = utils.convert_keys_to_snake_case(data)
        return cls(
            client_id=data.get("client_id") or "",
            client_secret_name=data.get("client_secret_name") or "",
            token_url=data.get("token_url") or "",
            audience=data.get("audience") or "",
            scope=data.get("scope") or "",
        )


@dataclass
class MCPAuth:
    """How an MCP server authenticates: a secret sent in a header or query
    parameter, or OAuth.

    secret_name names a secret stored in Agent Studio; the secret value never
    passes through the ADK.
    """

    header: str = ""
    query_param: str = ""
    secret_name: str = ""
    oauth: Optional[MCPOAuth] = None

    def __init__(
        self,
        header: str = "",
        query_param: str = "",
        secret_name: str = "",
        oauth: MCPOAuth | dict | None = None,
    ):
        self.header = header
        self.query_param = query_param
        self.secret_name = secret_name
        if oauth is not None and not isinstance(oauth, (MCPOAuth, dict)):
            raise ValueError("auth.oauth must be a mapping.")
        self.oauth = MCPOAuth.from_dict(oauth) if isinstance(oauth, dict) else oauth

    def to_yaml_dict(self) -> dict:
        result = {
            key: value
            for key, value in (
                ("header", self.header),
                ("query_param", self.query_param),
                ("secret_name", self.secret_name),
            )
            if value
        }
        oauth = self.oauth.to_yaml_dict() if self.oauth else {}
        if oauth:
            result["oauth"] = oauth
        return result

    def to_proto(self) -> integrations_pb2.MCPAuth:
        return integrations_pb2.MCPAuth(
            header=self.header,
            query_param=self.query_param,
            secret_name=self.secret_name,
            oauth=self.oauth.to_proto() if self.oauth else None,
        )

    def validate(self) -> None:
        """Check the auth settings describe exactly one way to authenticate."""
        methods = [
            name
            for name, is_set in (
                ("header", self.header),
                ("query_param", self.query_param),
                ("oauth", self.oauth and self.oauth.to_yaml_dict()),
            )
            if is_set
        ]
        if len(methods) > 1:
            raise ValueError(f"auth must set only one of header, query_param or oauth: {methods}")
        if (self.header or self.query_param) and not self.secret_name:
            raise ValueError(f"auth.secret_name is required when auth.{methods[0]} is set.")
        if self.secret_name and not (self.header or self.query_param):
            raise ValueError("auth.secret_name needs auth.header or auth.query_param to be set.")
        if methods == ["oauth"]:
            for field in ("client_id", "client_secret_name", "token_url"):
                if not getattr(self.oauth, field):
                    raise ValueError(f"auth.oauth.{field} is required.")
            if not URL_PATTERN.fullmatch(self.oauth.token_url):
                raise ValueError(
                    f"auth.oauth.token_url '{self.oauth.token_url}' must be an http(s) URL."
                )

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["MCPAuth"]:
        """Build from a projection (camelCase) or YAML (snake_case) dict."""
        if not data:
            return None
        oauth = data.get("oauth")
        data = utils.convert_keys_to_snake_case(
            {key: value for key, value in data.items() if key != "oauth"}
        )
        return cls(
            header=data.get("header") or "",
            query_param=data.get("query_param") or "",
            secret_name=data.get("secret_name") or "",
            oauth=MCPOAuth.from_dict(oauth),
        )


@register_resource("mcp_servers")
@dataclass
class MCPServer(MultiResourceYamlResource):
    """An MCP server connected to the agent.

    The platform keys servers by a generated id, which never appears in YAML;
    the YAML identifies each server by its provider_id. last_discovered_at and
    last_discovered_tool_count are set by the platform when it lists the
    server's tools, so they are kept off the YAML and sent back unchanged on
    upsert, which would otherwise clear them.

    Saved MCP profiles are not synced: they hold the same settings as a server,
    kept by Agent Studio so a disconnected provider can be reconnected.
    """

    url: str
    auth: Optional[MCPAuth]
    timeout: Optional[int]
    # None enables every tool the server offers; an empty list enables none.
    enabled_functions: Optional[list[str]]
    last_discovered_at: Optional[str]
    last_discovered_tool_count: Optional[int]

    top_level_name: ClassVar[str] = "mcp_servers"
    resource_key: ClassVar[str] = "provider_id"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        url: str = "",
        auth: MCPAuth | dict | None = None,
        timeout: Optional[int] = None,
        enabled_functions: Optional[list[str]] = None,
        last_discovered_at: Optional[str] = None,
        last_discovered_tool_count: Optional[int] = None,
    ):
        if auth is not None and not isinstance(auth, (MCPAuth, dict)):
            raise ValueError("auth must be a mapping.")
        self.resource_id = resource_id
        self.name = name
        self.url = url
        self.auth = MCPAuth.from_dict(auth) if isinstance(auth, dict) else auth
        self.timeout = timeout
        self.enabled_functions = enabled_functions
        self.last_discovered_at = last_discovered_at
        self.last_discovered_tool_count = last_discovered_tool_count

    @property
    def file_path(self) -> str:
        return os.path.join(
            MCP_FILE, self.top_level_name, utils.clean_name(self.name, lowercase=False)
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "MCPServer"]:
        """Parse MCP servers from a projection dict.

        The mcpConfig slice has no always-present fields, so the API leaves it
        out entirely for a user without read access.
        """
        mcp_projection = projection.get("mcpConfig")
        if mcp_projection is None:
            logger.debug("No read access to MCP config - it will not be pulled.")
            return {}
        servers = mcp_projection.get("servers", {}).get("entities", {})
        return {
            server_id: cls(
                resource_id=server_id,
                # Agent Studio shows a server without a provider under this key too.
                name=server.get("providerId") or f"custom:{server_id}",
                url=server.get("url", ""),
                auth=server.get("auth"),
                timeout=server.get("timeout"),
                enabled_functions=server.get("enabledFunctions"),
                last_discovered_at=server.get("lastDiscoveredAt"),
                last_discovered_tool_count=server.get("lastDiscoveredToolCount"),
            )
            for server_id, server in servers.items()
        }

    def to_yaml_dict(self) -> dict:
        result = {"provider_id": self.name, "url": self.url}
        auth = self.auth.to_yaml_dict() if self.auth else {}
        if auth:
            result["auth"] = auth
        if self.timeout is not None:
            result["timeout"] = self.timeout
        if self.enabled_functions is not None:
            result["enabled_functions"] = list(self.enabled_functions)
        return result

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str = "",
        known_last_discovered_at: Optional[str] = None,
        known_last_discovered_tool_count: Optional[int] = None,
        **kwargs,
    ) -> "MCPServer":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("provider_id") or name,
            url=yaml_dict.get("url") or "",
            auth=yaml_dict.get("auth"),
            timeout=yaml_dict.get("timeout"),
            enabled_functions=yaml_dict.get("enabled_functions"),
            last_discovered_at=known_last_discovered_at,
            last_discovered_tool_count=known_last_discovered_tool_count,
        )

    def validate(self, **kwargs) -> None:
        if not self.name:
            raise ValueError("provider_id is required.")
        if not self.url:
            raise ValueError("url is required.")
        if not URL_PATTERN.fullmatch(self.url):
            raise ValueError(f"url '{self.url}' must be an http(s) URL.")
        if self.auth:
            self.auth.validate()
        if self.timeout is not None and not (
            MIN_TIMEOUT_SECONDS <= self.timeout <= MAX_TIMEOUT_SECONDS
        ):
            raise ValueError(
                f"timeout must be between {MIN_TIMEOUT_SECONDS} and {MAX_TIMEOUT_SECONDS} "
                f"seconds, got {self.timeout}."
            )
        if self.enabled_functions is not None:
            duplicates = sorted(
                {f for f in self.enabled_functions if self.enabled_functions.count(f) > 1}
            )
            if duplicates:
                raise ValueError(f"Duplicate enabled_functions: {duplicates}")
            if not all(self.enabled_functions):
                raise ValueError("enabled_functions entries cannot be empty.")

    @classmethod
    def validate_collection(cls, resources: dict[str, "MCPServer"]) -> None:
        provider_ids = [server.name for server in resources.values()]
        duplicates = sorted({p for p in provider_ids if provider_ids.count(p) > 1})
        if duplicates:
            raise ValueError(f"Duplicate provider_id in mcp_servers: {duplicates}")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        file_path = os.path.join(base_path, MCP_FILE)
        if not os.path.exists(file_path):
            return []
        yaml_dict = MCPServer._get_top_level_data(file_path)
        entries: list[dict] = (yaml_dict.get(MCPServer.top_level_name) if yaml_dict else None) or []
        return [
            os.path.join(
                file_path,
                MCPServer.top_level_name,
                utils.clean_name(entry["provider_id"], lowercase=False),
            )
            for entry in entries
            if isinstance(entry, dict) and entry.get("provider_id")
        ]

    @property
    def command_type(self) -> str:
        return "mcp_server"

    @property
    def create_command_type(self) -> str:
        return "upsert_mcp_server"

    @property
    def update_command_type(self) -> str:
        return "upsert_mcp_server"

    def _build_upsert_proto(self) -> MCPServer_Upsert:
        optional_fields = {
            "auth": self.auth.to_proto() if self.auth else None,
            "timeout": self.timeout,
            "enabled_functions": (
                MCPEnabledFunctions(names=self.enabled_functions)
                if self.enabled_functions is not None
                else None
            ),
            "last_discovered_at": self.last_discovered_at,
            "last_discovered_tool_count": self.last_discovered_tool_count,
        }
        return MCPServer_Upsert(
            server=integrations_pb2.MCPServer(
                id=self.resource_id,
                provider_id=self.name,
                url=self.url,
                **{key: value for key, value in optional_fields.items() if value is not None},
            )
        )

    def build_create_proto(self) -> MCPServer_Upsert:
        return self._build_upsert_proto()

    def build_update_proto(self) -> MCPServer_Upsert:
        return self._build_upsert_proto()

    def build_delete_proto(self) -> MCPServer_Delete:
        return MCPServer_Delete(id=self.resource_id)
