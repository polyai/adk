"""Handling and managing an Agent Studio Handoff

Copyright PolyAI Limited
"""

import logging
import os
import re
from dataclasses import dataclass
from typing import ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf.handoff_pb2 import (
    HANDOFF_CHANNEL_CALL,
    HANDOFF_REASON_AVAILABILITY_ALWAYS,
    Handoff_Create,
    Handoff_Delete,
    Handoff_Update,
    HandoffMessageOutcome,
    HandoffNotOfferedOutcome,
    HandoffReason_Create,
    HandoffReason_Delete,
    HandoffReason_Update,
    HandoffReasonOutcome,
    HandoffReasonOutcomes,
    HandoffSettings_SetTransferMessage,
    HandoffTransferOutcome,
    SipByeHandoffConfig,
    SipConfig,
    SipHeader,
    SipHeaders,
    SipInviteHandoffConfig,
    SipReferHandoffConfig,
)
from poly.resources.resource import (
    MultiResourceYamlResource,
    ResourceMapping,
    register_resource,
)

logger = logging.getLogger(__name__)

VALID_SIP_METHODS = ("invite", "refer", "bye")
VALID_ENCRYPTION = ("TLS/SRTP", "UDP/RTP")

NAME_MAX = 100
DESCRIPTION_MAX = 300
SIP_FIELD_MAX = 100
SIP_HEADER_NAME_PATTERN = re.compile(r"[A-Za-z0-9!#$%&'*+\-.^_~]{1,100}")
# Printable ASCII: space to tilde.
SIP_HEADER_VALUE_PATTERN = re.compile(r"[\x20-\x7E]{0,1000}")

HANDOFFS_FILE = os.path.join("config", "handoffs.yaml")

# The platform applies the same limits to handoff reasons.
REASON_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]{0,63}")
REASON_NAME_MAX = 100
REASON_DESCRIPTION_MAX = 500
WORDING_MAX = 300
TRANSFER_MESSAGE_MAX = 300


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
    transfer_test_calls: bool
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
        transfer_test_calls: bool = True,
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
        self.transfer_test_calls = transfer_test_calls

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
                transfer_test_calls=not handoff_data.get("skipTestCallTransfers", False),
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
        # Written only when off, so files pulled before the field existed don't change.
        if self.transfer_test_calls is not True:
            result["transfer_test_calls"] = self.transfer_test_calls
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
            transfer_test_calls=yaml_dict.get("transfer_test_calls", True),
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
            skip_test_call_transfers=not self.transfer_test_calls,
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
            skip_test_call_transfers=not self.transfer_test_calls,
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
        for field_name, value, limit in (
            ("name", self.name, NAME_MAX),
            ("description", self.description, DESCRIPTION_MAX),
            ("phone_number", self.sip_config.phone_number, SIP_FIELD_MAX),
            ("outbound_endpoint", self.sip_config.outbound_endpoint, SIP_FIELD_MAX),
        ):
            if len(value or "") > limit:
                raise ValueError(
                    f"Handoff '{self.name}': {field_name} is longer than {limit} characters."
                )

        for header in self.sip_headers:
            key, value = header.get("key"), header.get("value")
            # A header with an empty key is left out of a push.
            if not key:
                continue
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError(
                    f"Handoff '{self.name}': SIP header {key!r} needs a text 'key' and 'value'."
                )
            if not SIP_HEADER_NAME_PATTERN.fullmatch(key):
                raise ValueError(
                    f"Handoff '{self.name}': SIP header name '{key}' must be at most 100 "
                    "letters, digits or !#$%&'*+-.^_~"
                )
            if not SIP_HEADER_VALUE_PATTERN.fullmatch(value):
                raise ValueError(
                    f"Handoff '{self.name}': SIP header '{key}' value must be at most 1000 "
                    "printable ASCII characters."
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


def _file_declares(base_path: str, top_level_name: str) -> bool:
    """Whether the local config/handoffs.yaml has `top_level_name` at all."""
    true_file_path = os.path.join(base_path, HANDOFFS_FILE)
    if not os.path.isfile(true_file_path):
        return False
    yaml_dict = MultiResourceYamlResource._get_top_level_data(true_file_path)
    return top_level_name in (yaml_dict or {})


def projection_supports_handoff_reasons(projection: dict) -> bool:
    """Whether the project's handoff state has reasons at all.

    Projections written before reasons existed have neither `reasons` nor
    `settings` under `handoff`.
    """
    handoff_state = projection.get("handoff") or {}
    return "reasons" in handoff_state or "settings" in handoff_state


def declare_handoff_reasons(file_data: dict[str, dict]) -> None:
    """Give a handoffs file that has destinations an empty `reasons` list.

    Args:
        file_data: Top-level YAML data by true file path, changed in place.
    """
    for true_file_path, top_level_yaml_dict in file_data.items():
        if not os.path.normpath(true_file_path).endswith(HANDOFFS_FILE):
            continue
        if Handoff.top_level_name in top_level_yaml_dict:
            top_level_yaml_dict.setdefault(HandoffReason.top_level_name, [])


OUTCOME_TRANSFER = "transfer"
OUTCOME_MESSAGE = "message"
OUTCOME_NOT_OFFERED = "not_offered"


@dataclass
class ReasonOutcome:
    """What happens on one channel when the agent hands off for a reason.

    In the file::

        call: {transfer_to: Front desk, wording: "..."}  # transfer
        call: {message: "..."}                           # no transfer; guidance, not a script
        call: not_offered                                # the reason isn't offered on this channel

    `destination_id` holds the destination's id; the file shows its name.
    """

    kind: str
    destination_id: str = ""
    wording: Optional[str] = None
    message: str = ""

    @classmethod
    def from_yaml_value(cls, value, channel: str, reason_name: str) -> "ReasonOutcome":
        """Parse one channel's outcome from the file, refusing any other shape."""
        where = f"Reason '{reason_name}': `{channel}`"
        expected = "must be `not_offered`, `{transfer_to: ..., wording: ...}` or `{message: ...}`"
        if isinstance(value, str):
            if value.strip() == OUTCOME_NOT_OFFERED:
                return cls(kind=OUTCOME_NOT_OFFERED)
            raise ValueError(f"{where} {expected}; got {value!r}")
        if not isinstance(value, dict):
            raise ValueError(f"{where} {expected}; got {value!r}")
        unknown = sorted(set(value) - {"transfer_to", "wording", "message"})
        if unknown:
            raise ValueError(f"{where} has unknown keys {unknown}")
        if "message" in value:
            if "transfer_to" in value or "wording" in value:
                raise ValueError(f"{where}: `message` can't go with `transfer_to` or `wording`")
            return cls(kind=OUTCOME_MESSAGE, message=str(value.get("message") or ""))
        if "transfer_to" not in value:
            raise ValueError(f"{where} needs `transfer_to` or `message`")
        wording = value.get("wording")
        return cls(
            kind=OUTCOME_TRANSFER,
            destination_id=str(value.get("transfer_to") or ""),
            wording=None if wording is None else str(wording),
        )

    @classmethod
    def from_projection(
        cls, outcome_state: dict | None, destinations: dict[str, dict]
    ) -> Optional["ReasonOutcome"]:
        """Read one channel's outcome; None when it has none.

        A transfer to a destination that's gone is read as the default
        destination, as the artifact does, so the next push isn't refused.
        """
        outcome = (outcome_state or {}).get("outcome") or {}
        case = outcome.get("$case")
        value = outcome.get("value") or {}
        if case == "transfer":
            destination_id = value.get("destinationId", "")
            if destination_id not in destinations:
                destination_id = next(
                    (i for i, d in destinations.items() if d.get("isDefault")), ""
                )
                if not destination_id:
                    logger.warning("A handoff reason transfers to a missing destination; skipped.")
                    return None
            return cls(
                kind=OUTCOME_TRANSFER,
                destination_id=destination_id,
                wording=value.get("wording"),
            )
        if case == "message":
            return cls(kind=OUTCOME_MESSAGE, message=value.get("message", ""))
        if case == "notOffered":
            return cls(kind=OUTCOME_NOT_OFFERED)
        return None

    def to_yaml_value(self) -> str | dict:
        """The file shape, with the destination's id (see HandoffReason.to_pretty_dict)."""
        if self.kind == OUTCOME_NOT_OFFERED:
            return OUTCOME_NOT_OFFERED
        if self.kind == OUTCOME_MESSAGE:
            return {"message": self.message}
        result = {"transfer_to": self.destination_id}
        if self.wording is not None:
            result["wording"] = self.wording
        return result

    def to_proto(self) -> HandoffReasonOutcome:
        """The outcome proto."""
        if self.kind == OUTCOME_NOT_OFFERED:
            return HandoffReasonOutcome(not_offered=HandoffNotOfferedOutcome())
        if self.kind == OUTCOME_MESSAGE:
            return HandoffReasonOutcome(message=HandoffMessageOutcome(message=self.message))
        transfer = HandoffTransferOutcome(destination_id=self.destination_id)
        if self.wording is not None:
            transfer.wording = self.wording
        return HandoffReasonOutcome(transfer=transfer)

    def validate(
        self, channel: str, reason_name: str, resource_mappings: list[ResourceMapping] | None
    ) -> None:
        """Apply the per-channel rules."""
        if channel == "chat" and self.kind == OUTCOME_TRANSFER:
            raise ValueError(
                f"Reason '{reason_name}': a chat outcome is `message` or `not_offered`; "
                "chat can't transfer."
            )
        if self.kind == OUTCOME_MESSAGE:
            if not self.message.strip():
                raise ValueError(f"Reason '{reason_name}': the {channel} message is empty.")
            if len(self.message) > WORDING_MAX:
                raise ValueError(
                    f"Reason '{reason_name}': the {channel} message is longer than "
                    f"{WORDING_MAX} characters."
                )
        if self.kind != OUTCOME_TRANSFER:
            return
        if self.wording is not None and len(self.wording) > WORDING_MAX:
            raise ValueError(
                f"Reason '{reason_name}': {channel} wording is longer than "
                f"{WORDING_MAX} characters."
            )
        if resource_mappings is None:
            return
        destinations = {
            m.resource_id: m.resource_name for m in resource_mappings if m.resource_type is Handoff
        }
        if self.destination_id not in destinations:
            raise ValueError(
                f"Reason '{reason_name}' transfers to '{self.destination_id}', which is not a "
                f"destination in {HANDOFFS_FILE}. Destinations: {sorted(destinations.values())}"
            )


@register_resource("handoff_reasons")
@dataclass
class HandoffReason(MultiResourceYamlResource):
    """Why the agent hands off (a `reasons:` entry in config/handoffs.yaml).

    The key is the analytics value written to HANDOFF_REASON. It is optional on
    create (the platform derives one) and fixed afterwards.
    """

    key: str
    description: str
    call: ReasonOutcome
    chat: Optional[ReasonOutcome]
    top_level_name: ClassVar[str] = "reasons"

    def __init__(
        self,
        *,
        resource_id: str,
        name: str,
        key: str = "",
        description: str = "",
        call: ReasonOutcome | dict | None = None,
        chat: ReasonOutcome | dict | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.key = key
        self.description = description
        # The status file stores outcomes as plain dicts.
        if isinstance(call, dict):
            call = ReasonOutcome(**call)
        if isinstance(chat, dict):
            chat = ReasonOutcome(**chat)
        self.call = call or ReasonOutcome(kind=OUTCOME_NOT_OFFERED)
        self.chat = chat

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "HandoffReason"]:
        """Parse active reasons from a projection dict."""
        handoff_state = projection.get("handoff") or {}
        destinations = {
            handoff_id: data
            for handoff_id, data in (
                (handoff_state.get("handoffs") or {}).get("entities") or {}
            ).items()
            if data.get("active", False)
        }
        reasons = {}
        for reason_id, data in ((handoff_state.get("reasons") or {}).get("entities") or {}).items():
            if not data.get("active", False):
                continue
            outcomes = data.get("outcomes") or {}
            call = ReasonOutcome.from_projection(outcomes.get("call"), destinations)
            if call is None:
                logger.warning(f"Handoff reason {data.get('name')!r} has no call outcome; skipped.")
                continue
            reasons[reason_id] = cls(
                resource_id=reason_id,
                name=data.get("name", ""),
                key=data.get("key", ""),
                description=data.get("description", ""),
                call=call,
                chat=ReasonOutcome.from_projection(outcomes.get("chat"), destinations),
            )
        return reasons

    @property
    def file_path(self) -> str:
        """Virtual path of this entry inside config/handoffs.yaml."""
        return os.path.join(
            HANDOFFS_FILE, self.top_level_name, utils.clean_name(self.name, lowercase=False)
        )

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        """Prefix for references to reasons (not referenced in prompts)."""
        return "hr"

    def to_yaml_dict(self) -> dict:
        """Return the entry, with destination ids (made names by to_pretty_dict)."""
        result = {"name": self.name}
        if self.key:
            result["key"] = self.key
        result["description"] = self.description
        result["call"] = self.call.to_yaml_value()
        if self.chat is not None:
            result["chat"] = self.chat.to_yaml_value()
        return result

    @classmethod
    def _map_destinations(cls, d: dict, lookup: dict[str, str]) -> dict:
        d = dict(d)
        for channel in ("call", "chat"):
            outcome = d.get(channel)
            if isinstance(outcome, dict) and "transfer_to" in outcome:
                outcome = dict(outcome)
                outcome["transfer_to"] = lookup.get(outcome["transfer_to"], outcome["transfer_to"])
                d[channel] = outcome
        return d

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Show destinations by name."""
        lookup = {
            m.resource_id: m.resource_name
            for m in resource_mappings or []
            if m.resource_type is Handoff
        }
        return cls._map_destinations(d, lookup)

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Resolve destination names to ids; an unknown name is left for validate()."""
        lookup: dict[str, str] = {}
        for m in resource_mappings or []:
            if m.resource_type is Handoff:
                lookup.setdefault(m.resource_name, m.resource_id)
                lookup.setdefault(utils.clean_name(m.resource_name, lowercase=False), m.resource_id)
        return cls._map_destinations(yaml_dict, lookup)

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "HandoffReason":
        """Create a reason from its file entry."""
        reason_name = yaml_dict.get("name") or name
        if "call" not in yaml_dict:
            raise ValueError(f"Reason '{reason_name}' needs a `call` outcome.")
        chat = yaml_dict.get("chat")
        return cls(
            resource_id=resource_id,
            name=reason_name,
            key=yaml_dict.get("key") or "",
            description=yaml_dict.get("description", ""),
            call=ReasonOutcome.from_yaml_value(yaml_dict["call"], "call", reason_name),
            chat=None if chat is None else ReasonOutcome.from_yaml_value(chat, "chat", reason_name),
        )

    @classmethod
    def read_key(cls, file_path: str) -> str:
        """The `key` an entry on disk sets, or ""."""
        return str(cls._get_matching(file_path).get("key") or "")

    @classmethod
    def left_alone_when_undeclared(cls, base_path: str) -> bool:
        """A file without `reasons:` says nothing about them, so a push mustn't delete them."""
        return not _file_declares(base_path, cls.top_level_name)

    @property
    def command_type(self) -> str:
        """The platform command family."""
        return "handoff_reason"

    @property
    def create_command_type(self) -> str:
        """The platform create command."""
        return "handoff_reason_create"

    @property
    def update_command_type(self) -> str:
        """The platform update command."""
        return "handoff_reason_update"

    @property
    def delete_command_type(self) -> str:
        """The platform delete command."""
        return "handoff_reason_delete"

    def _outcomes_proto(self) -> HandoffReasonOutcomes:
        outcomes = HandoffReasonOutcomes(call=self.call.to_proto())
        if self.chat is not None:
            outcomes.chat.CopyFrom(self.chat.to_proto())
        return outcomes

    def build_create_proto(self) -> HandoffReason_Create:
        """Create a proto for creating the reason."""
        proto = HandoffReason_Create(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            availability=HANDOFF_REASON_AVAILABILITY_ALWAYS,
            outcomes=self._outcomes_proto(),
        )
        if self.key:
            proto.key = self.key
        return proto

    def build_update_proto(self) -> HandoffReason_Update:
        """Create a proto for updating the reason; the key can't change."""
        return HandoffReason_Update(
            id=self.resource_id,
            name=self.name,
            description=self.description,
            availability=HANDOFF_REASON_AVAILABILITY_ALWAYS,
            outcomes=self._outcomes_proto(),
        )

    def build_delete_proto(self) -> HandoffReason_Delete:
        """Create a proto for deleting the reason."""
        return HandoffReason_Delete(id=self.resource_id)

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Validate the reason as the platform does."""
        name = self.name.strip()
        if not name:
            raise ValueError("Reason name is required.")
        if len(name) > REASON_NAME_MAX:
            raise ValueError(f"Reason '{name}': name is longer than {REASON_NAME_MAX} characters.")
        if self.key and not REASON_KEY_PATTERN.fullmatch(self.key):
            raise ValueError(
                f"Reason '{name}': key '{self.key}' must be capital letters, digits and "
                "underscores, start with a letter, and be at most 64 characters."
            )
        if not self.description.strip():
            raise ValueError(f"Reason '{name}' needs a description: when the agent should use it.")
        if len(self.description) > REASON_DESCRIPTION_MAX:
            raise ValueError(
                f"Reason '{name}': description is longer than {REASON_DESCRIPTION_MAX} characters."
            )
        self.call.validate("call", name, resource_mappings)
        if self.chat is not None:
            self.chat.validate("chat", name, resource_mappings)

    @classmethod
    def validate_collection(cls, resources: dict[str, "HandoffReason"]) -> None:
        """Names and keys are unique."""
        names = [r.name.strip().lower() for r in resources.values()]
        duplicate_names = sorted({n for n in names if names.count(n) > 1})
        if duplicate_names:
            raise ValueError(f"Reason names must be unique: {duplicate_names}")
        keys = [r.key for r in resources.values() if r.key]
        duplicate_keys = sorted({k for k in keys if keys.count(k) > 1})
        if duplicate_keys:
            raise ValueError(f"Reason keys must be unique: {duplicate_keys}")

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """Virtual paths for every reason in config/handoffs.yaml."""
        true_file_path = os.path.join(base_path, HANDOFFS_FILE)
        if not os.path.exists(true_file_path):
            return []
        yaml_dict = HandoffReason._get_top_level_data(true_file_path)
        discovered = []
        for reason in (yaml_dict or {}).get(HandoffReason.top_level_name) or []:
            name = reason.get("name") if isinstance(reason, dict) else None
            if not name:
                continue
            discovered.append(
                os.path.join(
                    true_file_path,
                    HandoffReason.top_level_name,
                    utils.clean_name(name, lowercase=False),
                )
            )
        return discovered


@register_resource("handoff_transfer_message")
@dataclass
class HandoffTransferMessage(MultiResourceYamlResource):
    """The default call transfer message (`transfer_message: {call: ...}`).

    `call: null` means no default line; `call: ""` means transfer without a
    line. Chat has no default transfer message, so `chat` is refused.
    """

    call: Optional[str]
    unsupported_keys: list[str]
    top_level_name: ClassVar[str] = "transfer_message"
    _singleton: ClassVar[bool] = True
    RESOURCE_ID: ClassVar[str] = "handoff_transfer_message"

    def __init__(
        self,
        *,
        resource_id: str = RESOURCE_ID,
        name: str = "transfer_message",
        call: Optional[str] = None,
        unsupported_keys: list[str] | None = None,
    ):
        self.resource_id = resource_id
        self.name = name
        self.call = call
        self.unsupported_keys = unsupported_keys or []

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "HandoffTransferMessage"]:
        """Read the call message; chat's isn't pulled."""
        settings = (projection.get("handoff") or {}).get("settings") or {}
        call = settings.get("callTransferMessage")
        if call is None:
            return {}
        return {cls.RESOURCE_ID: cls(call=call)}

    @property
    def file_path(self) -> str:
        """Virtual path of the section inside config/handoffs.yaml."""
        return os.path.join(HANDOFFS_FILE, self.top_level_name)

    @staticmethod
    def get_resource_prefix(**kwargs) -> str:
        """Prefix for references (not referenced in prompts)."""
        return "htm"

    def to_yaml_dict(self) -> dict:
        """Return the section."""
        return {"call": self.call}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "HandoffTransferMessage":
        """Create the message from the file section."""
        call = yaml_dict.get("call")
        return cls(
            resource_id=resource_id,
            name=name or "transfer_message",
            call=None if call is None else str(call),
            unsupported_keys=sorted(k for k in yaml_dict if k != "call"),
        )

    @classmethod
    def left_alone_when_undeclared(cls, base_path: str) -> bool:
        """A file without `transfer_message:` leaves the project's message as it is."""
        return not _file_declares(base_path, cls.top_level_name)

    @property
    def command_type(self) -> str:
        """The platform command family."""
        return "handoff_settings_set_transfer_message"

    @property
    def create_command_type(self) -> str:
        """Setting the message is the only command."""
        return self.command_type

    @property
    def update_command_type(self) -> str:
        """Setting the message is the only command."""
        return self.command_type

    @property
    def delete_command_type(self) -> str:
        """Removing the section with `call` in it unsets the message."""
        return self.command_type

    def _proto(self, call: Optional[str]) -> HandoffSettings_SetTransferMessage:
        proto = HandoffSettings_SetTransferMessage(channel=HANDOFF_CHANNEL_CALL)
        if call is not None:
            proto.message = call
        return proto

    def build_create_proto(self) -> HandoffSettings_SetTransferMessage:
        """Set the call message."""
        return self._proto(self.call)

    def build_update_proto(self) -> HandoffSettings_SetTransferMessage:
        """Set the call message."""
        return self._proto(self.call)

    def build_delete_proto(self) -> HandoffSettings_SetTransferMessage:
        """Unset the call message."""
        return self._proto(None)

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        """Only `call` is supported, at most 300 characters."""
        if self.unsupported_keys:
            raise ValueError(
                f"transfer_message only takes `call`, got {self.unsupported_keys}. "
                "Chat has no default transfer message."
            )
        if self.call is not None and len(self.call) > TRANSFER_MESSAGE_MAX:
            raise ValueError(
                f"transfer_message.call is longer than {TRANSFER_MESSAGE_MAX} characters."
            )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        """The section's virtual path, when the file has it."""
        true_file_path = os.path.join(base_path, HANDOFFS_FILE)
        if not os.path.exists(true_file_path):
            return []
        yaml_dict = HandoffTransferMessage._get_top_level_data(true_file_path)
        section = (yaml_dict or {}).get(HandoffTransferMessage.top_level_name)
        if not isinstance(section, dict) or not section:
            # An empty `transfer_message:` is a deleted section, which unsets the message.
            return []
        return [os.path.join(true_file_path, HandoffTransferMessage.top_level_name)]
