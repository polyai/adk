"""Handling and managing an Agent Studio Handoff

Copyright PolyAI Limited
"""

import logging
import os
from dataclasses import dataclass
from typing import ClassVar

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.handoff_pb2 import (
    Handoff_Create,
    Handoff_Delete,
    Handoff_Update,
    SipByeHandoffConfig,
    SipConfig,
    SipHeader,
    SipHeaders,
    SipInviteHandoffConfig,
    SipReferHandoffConfig,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    register_resource,
)

logger = logging.getLogger(__name__)

VALID_SIP_METHODS = ("invite", "refer", "bye")
VALID_ENCRYPTION = ("TLS/SRTP", "UDP/RTP")


@dataclass
class HandoffSipConfig:
    method: str
    phone_number: str = ""
    outbound_endpoint: str = ""
    outbound_encryption: str = ""

    def to_yaml_dict(self) -> dict:
        result = {"method": self.method}
        if self.method == "invite":
            result["phone_number"] = self.phone_number
            result["outbound_endpoint"] = self.outbound_endpoint
            result["outbound_encryption"] = self.outbound_encryption
        elif self.method == "refer":
            result["phone_number"] = self.phone_number
        return result

    def to_proto(self) -> SipConfig:
        if self.method == "invite":
            return SipConfig(
                invite=SipInviteHandoffConfig(
                    phone_number=self.phone_number,
                    outbound_endpoint=self.outbound_endpoint,
                    outbound_encryption=self.outbound_encryption,
                )
            )
        elif self.method == "refer":
            return SipConfig(
                refer=SipReferHandoffConfig(
                    phone_number=self.phone_number,
                )
            )
        return SipConfig(bye=SipByeHandoffConfig())


@register_resource("handoffs")
@dataclass
class Handoff(MultiResourceYamlResource):
    """Handoff resource for ADK."""

    description: str
    is_default: bool
    sip_config: HandoffSipConfig
    sip_headers: list[dict]
    top_level_name: ClassVar[str] = "handoffs"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        description: str = "",
        is_default: bool = False,
        sip_config: HandoffSipConfig | dict | None = None,
        sip_headers: list | None = None,
        slim: bool = False,
    ):
        self.resource_id = resource_id
        self.name = name
        self.description = description
        self.is_default = is_default
        self.slim = slim

        if sip_config is None:
            sip_config = {}
        if isinstance(sip_config, dict):
            sip_config = HandoffSipConfig(
                method=sip_config.get("method", "bye"),
                phone_number=sip_config.get("phone_number", ""),
                outbound_endpoint=sip_config.get("outbound_endpoint", ""),
                outbound_encryption=sip_config.get("outbound_encryption", ""),
            )

        self.sip_config = sip_config
        self.sip_headers = sip_headers or []

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "Handoff"]:
        """Parse handoffs from a projection dict."""
        handoffs_projection = projection.get("handoff", {}).get("handoffs", {}).get("entities", {})
        handoffs = {}
        if "handoff" not in projection:
            logger.debug("No read access to handoffs - they will not be pulled.")
            return {}

        # Read access is checked before "active": an auth-filtered handoff has no
        # "active" field, and must not be mistaken for a deactivated one. Inactive
        # handoffs are stubbed too, since we can't tell them apart here - harmless,
        # as an inactive handoff's id is never referenced.
        if any("active" not in handoff for handoff in handoffs_projection.values()):
            logger.debug("No read access to handoffs - keeping names for references only.")
            return {
                handoff_id: cls(
                    resource_id=handoff_id,
                    name=handoff_data.get("name", ""),
                    slim=True,
                )
                for handoff_id, handoff_data in handoffs_projection.items()
            }

        for handoff_id, handoff_data in handoffs_projection.items():
            if not handoff_data.get("active", False):
                continue

            config = handoff_data.get("sipConfig", {}).get("config", {})
            method = config.get("$case", "bye")
            value = config.get("value", {})

            sip_config = {"method": method}
            if method == "invite":
                sip_config["phone_number"] = value.get("phoneNumber", "")
                sip_config["outbound_endpoint"] = value.get("outboundEndpoint", "")
                sip_config["outbound_encryption"] = value.get("outboundEncryption", "")
            elif method == "refer":
                sip_config["phone_number"] = value.get("phoneNumber", "")

            sip_headers = handoff_data.get("sipHeaders", {}).get("headers", [])

            handoffs[handoff_id] = cls(
                resource_id=handoff_id,
                name=handoff_data.get("name", ""),
                description=handoff_data.get("description", ""),
                is_default=handoff_data.get("isDefault", False),
                sip_config=sip_config,
                sip_headers=sip_headers,
            )
        return handoffs

    def to_yaml_dict(self) -> dict:
        result = {
            "name": self.name,
            "description": self.description,
            "is_default": self.is_default,
            "sip_config": self.sip_config.to_yaml_dict(),
        }
        if self.sip_headers:
            result["sip_headers"] = self.sip_headers
        return result

    @property
    def file_path(self) -> str:
        path_safe_name = utils.clean_name(self.name, lowercase=False)
        return os.path.join("config", "handoffs.yaml", self.top_level_name, path_safe_name)

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        return "ho"

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "Handoff":
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or name,
            description=yaml_dict.get("description", ""),
            is_default=yaml_dict.get("is_default", False),
            sip_config=yaml_dict.get("sip_config", {}),
            sip_headers=yaml_dict.get("sip_headers", []),
        )

    @property
    def command_type(self) -> str:
        return "handoff"

    @property
    def delete_command_type(self) -> str:
        return "handoff_delete"

    @property
    def create_command_type(self) -> str:
        return "handoff_create"

    @property
    def update_command_type(self) -> str:
        return "handoff_update"

    def _build_sip_headers_proto(self) -> SipHeaders:
        return SipHeaders(
            headers=[
                SipHeader(key=h["key"], value=h["value"]) for h in self.sip_headers if h.get("key")
            ]
        )

    def build_update_proto(self) -> Handoff_Update:
        return Handoff_Update(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            sip_config=self.sip_config.to_proto(),
            sip_headers=self._build_sip_headers_proto(),
            active=True,
        )

    def build_delete_proto(self) -> Handoff_Delete:
        return Handoff_Delete(id=self.resource_id)

    def build_create_proto(self) -> Handoff_Create:
        return Handoff_Create(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            sip_config=self.sip_config.to_proto(),
            sip_headers=self._build_sip_headers_proto(),
            active=True,
        )

    def validate(self, **kwargs) -> None:
        if not self.name:
            raise ValueError("Handoff name is required")
        if self.sip_config.method not in VALID_SIP_METHODS:
            raise ValueError(
                f"Invalid SIP method '{self.sip_config.method}'. "
                f"Must be one of: {', '.join(VALID_SIP_METHODS)}"
            )
        if (
            self.sip_config.method == "invite"
            and self.sip_config.outbound_encryption not in VALID_ENCRYPTION
        ):
            raise ValueError(
                f"Invalid encryption method '{self.sip_config.outbound_encryption}'. "
                f"Must be one of: {', '.join(VALID_ENCRYPTION)}"
            )

    @classmethod
    def validate_collection(
        cls,
        resources: dict[str, "Handoff"],
    ) -> None:
        default_names = [h.name for h in resources.values() if h.is_default]
        if len(default_names) != 1:
            raise ValueError(
                f"Multiple or zero default handoffs detected: {default_names}. "
                "One handoff must be set as default."
            )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        handoffs_path = os.path.join(base_path, "config", "handoffs.yaml")
        discovered_handoffs: list[str] = []

        if not os.path.exists(handoffs_path):
            return discovered_handoffs

        yaml_dict = Handoff._get_top_level_data(handoffs_path)
        handoffs: list[dict] = yaml_dict.get("handoffs", []) if yaml_dict else []

        for handoff in handoffs:
            name = handoff.get("name")
            if not name:
                continue
            path_safe_name = utils.clean_name(name, lowercase=False)
            discovered_handoffs.append(
                os.path.join(handoffs_path, Handoff.top_level_name, path_safe_name)
            )

        return discovered_handoffs
