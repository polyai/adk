"""Copyright PolyAI Limited"""

import keyword
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf import outbound_campaigns_pb2 as campaigns_pb2
from poly.resources.flows import _drop_unset
from poly.resources.resource import (
    Resource,
    ResourceMapping,
    SubResource,
    YamlResource,
    _strip_strings,
    register_resource,
)

logger = logging.getLogger(__name__)

CAMPAIGNS_DIR = "outbound_campaigns"
CAMPAIGN_FILE = "campaign.yaml"
FUNCTIONS_DIR = "functions"

NODE_KEYS = ("id", "position", "label", "data")
FUNCTION_KEYS = ("name", "description")

SETTINGS_DEFAULTS: dict[str, Any] = {
    "startDate": None,
    "endDate": None,
    "fromNumber": None,
    "smsFromNumber": None,
    "defaultVariantId": None,
    "country": None,
    "useCase": None,
    "dailyContactLimit": 3,
    "voiceDispatchLimits": None,
    "smsDispatchLimits": None,
    "defaultTimezone": None,
    "contactWindow": None,
}
DISPATCH_LIMIT_KEYS = ("maxConcurrent", "perHour", "perDay")
CONTACT_WINDOW_KEYS = ("daysOfWeek", "startTime", "endTime")
DAYS_OF_WEEK = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
USE_CASES = ("transactional", "marketing")
TIME_UNITS = ("minutes", "hours", "days")

NODE_FIELDS: dict[str, tuple[str, ...]] = {
    "trigger": ("function", "routes", "sourceType", "ingestInterval"),
    "call": (
        "flowName",
        "amdFlowName",
        "function",
        "greeting",
        "voicemailEnabled",
        "voicemailScript",
        "voicemailWhen",
        "maxAttempts",
        "backoff",
        "backoffUnit",
        "routes",
        "defaultRoute",
    ),
    "sms": (
        "function",
        "messageTemplate",
        "replyFlowName",
        "replyTimeoutValue",
        "replyTimeoutUnit",
        "routes",
        "defaultRoute",
    ),
    "conditional": ("function", "branches", "defaultTargetNodeId"),
    "wait": ("amount", "unit", "targetNodeId"),
    "writeback": ("target", "function", "targetNodeId"),
    "end": ("exitReason", "writebackEnabled", "function"),
}
NODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "trigger": {"routes": [], "sourceType": "csv", "ingestInterval": "daily"},
    "call": {"routes": [], "defaultRoute": None},
    "sms": {"routes": [], "defaultRoute": None},
    "conditional": {"defaultTargetNodeId": None},
}
NODE_REQUIRED: dict[str, tuple[str, ...]] = {
    "trigger": ("function",),
    "call": (
        "flowName",
        "function",
        "greeting",
        "voicemailEnabled",
        "maxAttempts",
        "backoff",
        "backoffUnit",
    ),
    "sms": ("function", "messageTemplate"),
    "conditional": ("function", "branches"),
    "wait": ("amount", "unit", "targetNodeId"),
    "writeback": ("target", "function", "targetNodeId"),
    "end": ("exitReason", "writebackEnabled"),
}
NODE_ENUMS: dict[str, dict[str, tuple[str, ...]]] = {
    "trigger": {
        "sourceType": ("csv", "api", "webhook"),
        "ingestInterval": ("hourly", "daily", "manual"),
    },
    "call": {"voicemailWhen": ("detection", "final_retry"), "backoffUnit": TIME_UNITS},
    "sms": {"replyTimeoutUnit": TIME_UNITS},
    "wait": {"unit": TIME_UNITS},
    "writeback": {"target": ("api", "csv")},
}
NODE_STRING_FIELDS = {
    "flowName",
    "amdFlowName",
    "greeting",
    "voicemailScript",
    "messageTemplate",
    "replyFlowName",
    "targetNodeId",
    "exitReason",
}
NODE_NULLABLE_STRING_FIELDS = {"defaultRoute", "defaultTargetNodeId"}

PYTHONIC_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SAFE_NODE_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_plain(item) for item in value]
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return float(value)
    if isinstance(value, str):
        return str(value)
    return value


def _ordered(values: dict, keys: tuple[str, ...]) -> dict:
    ordered = {key: values[key] for key in keys if key in values}
    ordered.update({key: value for key, value in values.items() if key not in ordered})
    return ordered


def _normalise_function(function: Any, from_platform: bool) -> Any:
    if not isinstance(function, dict):
        return function
    function = _ordered(function, FUNCTION_KEYS)
    if from_platform:
        function = {key: value for key, value in function.items() if key in FUNCTION_KEYS}
    return function


def _normalise_node_data(data: Any, from_platform: bool = False) -> Any:
    if not isinstance(data, dict) or data.get("type") not in NODE_FIELDS:
        return data
    node_type = data["type"]
    data = {**NODE_DEFAULTS.get(node_type, {}), **data}
    if "function" in data:
        data["function"] = _normalise_function(data["function"], from_platform)
    return _ordered(data, ("type", *NODE_FIELDS[node_type]))


def _normalise_position(position: Any) -> Any:
    if not isinstance(position, dict):
        return position
    normalised = dict(position)
    for axis in ("x", "y"):
        value = normalised.get(axis)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            normalised[axis] = float(value)
    return _ordered(normalised, ("x", "y"))


def normalise_node(node: Any, from_platform: bool = False) -> Any:
    """Fill a node's defaults and order its keys as in `campaign.yaml`. Non-dict input is returned as is."""
    if not isinstance(node, dict):
        return node
    node = dict(node)
    if "position" in node:
        node["position"] = _normalise_position(node["position"])
    if "data" in node:
        node["data"] = _normalise_node_data(node["data"], from_platform)
    return _ordered(node, NODE_KEYS)


def normalise_settings(settings: Any) -> Any:
    """Fill missing settings with their defaults and order the keys as in `campaign.yaml`."""
    if settings is None:
        settings = {}
    if not isinstance(settings, dict):
        return settings
    settings = {**SETTINGS_DEFAULTS, **settings}
    for key in ("voiceDispatchLimits", "smsDispatchLimits"):
        limits = settings.get(key)
        if isinstance(limits, dict):
            settings[key] = _ordered(
                {**dict.fromkeys(DISPATCH_LIMIT_KEYS), **limits}, DISPATCH_LIMIT_KEYS
            )
    window = settings.get("contactWindow")
    if isinstance(window, dict):
        settings["contactWindow"] = _ordered(window, CONTACT_WINDOW_KEYS)
    return _ordered(settings, tuple(SETTINGS_DEFAULTS))


def _routes_proto(routes: list[dict]) -> list[campaigns_pb2.RouteEdge]:
    return [
        campaigns_pb2.RouteEdge(
            **_drop_unset(
                dict(target_node_id=route.get("targetNodeId"), outcome=route.get("outcome"))
            )
        )
        for route in routes or []
    ]


def _function_proto(function: Optional[dict], code: str) -> campaigns_pb2.CampaignNodeFunction:
    function = function or {}
    return campaigns_pb2.CampaignNodeFunction(
        name=function.get("name") or "",
        description=function.get("description") or "",
        code=code or "",
    )


def node_data_proto(data: dict, code: str) -> tuple[str, Any]:
    """Return the node-data oneof field name and message for a node's `data` and function code.

    Raises:
        ValueError: if `data.type` is not a known node type.
    """
    node_type = data["type"]
    function = data.get("function")
    function_name = (function or {}).get("name") or ""
    if node_type == "trigger":
        message = campaigns_pb2.TriggerNodeData(
            function=function_name,
            routes=_routes_proto(data.get("routes")),
            campaign_function=_function_proto(function, code),
            **_drop_unset(
                dict(source_type=data.get("sourceType"), ingest_interval=data.get("ingestInterval"))
            ),
        )
    elif node_type == "call":
        message = campaigns_pb2.CallNodeData(
            flow_name=data.get("flowName") or "",
            function=function_name,
            greeting=data.get("greeting") or "",
            voicemail_enabled=bool(data.get("voicemailEnabled")),
            max_attempts=data.get("maxAttempts") or 0,
            backoff=data.get("backoff") or 0,
            backoff_unit=data.get("backoffUnit") or "",
            routes=_routes_proto(data.get("routes")),
            campaign_function=_function_proto(function, code),
            **_drop_unset(
                dict(
                    amd_flow_name=data.get("amdFlowName"),
                    voicemail_script=data.get("voicemailScript"),
                    voicemail_when=data.get("voicemailWhen"),
                    default_route=data.get("defaultRoute"),
                )
            ),
        )
    elif node_type == "sms":
        message = campaigns_pb2.SmsNodeData(
            function=function_name,
            message_template=data.get("messageTemplate") or "",
            routes=_routes_proto(data.get("routes")),
            campaign_function=_function_proto(function, code),
            **_drop_unset(
                dict(
                    reply_flow_name=data.get("replyFlowName"),
                    reply_timeout_value=data.get("replyTimeoutValue"),
                    reply_timeout_unit=data.get("replyTimeoutUnit"),
                    default_route=data.get("defaultRoute"),
                )
            ),
        )
    elif node_type == "conditional":
        message = campaigns_pb2.ConditionalNodeData(
            function=function_name,
            branches=[
                campaigns_pb2.ConditionalBranch(
                    id=branch.get("id") or "",
                    variable=branch.get("variable") or "",
                    target_node_id=branch.get("targetNodeId") or "",
                )
                for branch in data.get("branches") or []
            ],
            campaign_function=_function_proto(function, code),
            **_drop_unset(dict(default_target_node_id=data.get("defaultTargetNodeId"))),
        )
    elif node_type == "wait":
        message = campaigns_pb2.WaitNodeData(
            amount=data.get("amount") or 0,
            unit=data.get("unit") or "",
            target_node_id=data.get("targetNodeId") or "",
        )
    elif node_type == "writeback":
        message = campaigns_pb2.WritebackNodeData(
            target=data.get("target") or "",
            function=function_name,
            target_node_id=data.get("targetNodeId") or "",
            campaign_function=_function_proto(function, code),
        )
    elif node_type == "end":
        with_function = (
            {"function": function_name, "campaign_function": _function_proto(function, code)}
            if function
            else {}
        )
        message = campaigns_pb2.EndNodeData(
            exit_reason=data.get("exitReason") or "",
            writeback_enabled=bool(data.get("writebackEnabled")),
            **with_function,
        )
    else:
        raise ValueError(f"Unknown node type: {node_type}")
    return node_type, message


def _dispatch_limits_proto(limits: Optional[dict]) -> Optional[campaigns_pb2.DispatchLimits]:
    if limits is None:
        return None
    return campaigns_pb2.DispatchLimits(
        **_drop_unset(
            dict(
                max_concurrent=limits.get("maxConcurrent"),
                per_hour=limits.get("perHour"),
                per_day=limits.get("perDay"),
            )
        )
    )


def settings_proto(settings: dict) -> campaigns_pb2.OutboundCampaignSettings:
    """Build the settings message from the camelCase settings block."""
    window = settings.get("contactWindow")
    return campaigns_pb2.OutboundCampaignSettings(
        **_drop_unset(
            dict(
                start_date=settings.get("startDate"),
                end_date=settings.get("endDate"),
                from_number=settings.get("fromNumber"),
                sms_from_number=settings.get("smsFromNumber"),
                default_variant_id=settings.get("defaultVariantId"),
                country=settings.get("country"),
                use_case=settings.get("useCase"),
                daily_contact_limit=settings.get("dailyContactLimit"),
                voice_dispatch_limits=_dispatch_limits_proto(settings.get("voiceDispatchLimits")),
                sms_dispatch_limits=_dispatch_limits_proto(settings.get("smsDispatchLimits")),
                default_timezone=settings.get("defaultTimezone"),
                contact_window=(
                    campaigns_pb2.ContactWindow(
                        days_of_week=window.get("daysOfWeek") or [],
                        start_time=window.get("startTime") or "",
                        end_time=window.get("endTime") or "",
                    )
                    if window is not None
                    else None
                ),
            )
        )
    )


def _projection_campaigns(projection: dict) -> Optional[list[dict]]:
    section = projection.get("outboundCampaigns")
    if not isinstance(section, dict):
        return None
    collection = section.get("outboundCampaigns") or {}
    entities = collection.get("entities") or {}
    ids = collection.get("ids") or list(entities)
    return [
        entities[campaign_id]
        for campaign_id in ids
        if campaign_id in entities and not entities[campaign_id].get("archived")
    ]


def _projection_nodes(campaign: dict) -> list[dict]:
    nodes = campaign.get("nodes") or {}
    entities = nodes.get("entities") or {}
    return [entities[node_id] for node_id in nodes.get("ids") or [] if node_id in entities]


@register_resource("outbound_campaigns")
@dataclass
class OutboundCampaign(YamlResource):
    """An outbound campaign, kept as `outbound_campaigns/<name>/campaign.yaml`.

    Node function code lives in `functions/<node_id>.py` beside it and is held in
    `function_code` while pushing.
    """

    resource_id_prefix = "CMPGN"

    description: Optional[str] = None
    settings: dict = field(default_factory=lambda: normalise_settings({}))
    nodes: list[dict] = field(default_factory=list)

    function_code: dict[str, str] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    @property
    def folder(self) -> str:
        return utils.clean_name(self.name)

    @property
    def file_path(self) -> str:
        return os.path.join(CAMPAIGNS_DIR, self.folder, CAMPAIGN_FILE)

    @property
    def command_type(self) -> str:
        return "outbound_campaign"

    @property
    def create_command_type(self) -> str:
        return "outbound_campaign_create"

    @property
    def update_command_type(self) -> str:
        return "outbound_campaign_update"

    @property
    def delete_command_type(self) -> str:
        return "outbound_campaign_delete"

    def to_yaml_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "settings": self.settings,
            "nodes": self.nodes,
        }

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "OutboundCampaign":
        yaml_dict = _strip_strings(_plain(yaml_dict or {}))
        nodes = yaml_dict.get("nodes")
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or "",
            description=yaml_dict.get("description"),
            settings=normalise_settings(yaml_dict.get("settings")),
            nodes=[normalise_node(node) for node in nodes] if isinstance(nodes, list) else nodes,
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "OutboundCampaign"]:
        """Parse campaigns from a projection, skipping archived ones. Returns `{}` if it has none."""
        campaigns = _projection_campaigns(projection)
        if campaigns is None:
            logger.debug("No outbound campaigns in projection - they will not be pulled.")
            return {}
        return {
            campaign["id"]: cls(
                resource_id=campaign["id"],
                name=_strip_strings(campaign.get("name") or ""),
                description=_strip_strings(campaign.get("description")),
                settings=_strip_strings(normalise_settings(campaign.get("settings"))),
                nodes=[
                    _strip_strings(normalise_node(node, from_platform=True))
                    for node in _projection_nodes(campaign)
                ],
            )
            for campaign in campaigns
        }

    @classmethod
    def from_pretty_dict(cls, yaml_dict: dict, **kwargs) -> dict:
        return yaml_dict

    @classmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaign":
        campaign: OutboundCampaign = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )
        folder = os.path.basename(os.path.dirname(file_path))
        if folder != campaign.folder:
            raise ValueError(
                f"Campaign folder name does not match campaign name '{campaign.name}'. "
                f"{folder} != {campaign.folder}"
            )
        return campaign

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        campaigns_path = os.path.join(base_path, CAMPAIGNS_DIR)
        if not os.path.isdir(campaigns_path):
            return []
        return [
            os.path.join(campaigns_path, folder, CAMPAIGN_FILE)
            for folder in sorted(os.listdir(campaigns_path))
            if os.path.isfile(os.path.join(campaigns_path, folder, CAMPAIGN_FILE))
        ]

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        errors = self.validation_errors(resource_mappings)
        if errors:
            raise ValueError("; ".join(errors))

    def validation_errors(self, resource_mappings: list[ResourceMapping] = None) -> list[str]:
        """Return every problem the platform would reject, so `validate` can report them all at once."""
        errors: list[str] = []
        if not isinstance(self.name, str) or not self.name.strip():
            errors.append("Name is required.")
        elif len(self.name) > 256:
            errors.append("Name must be under 256 characters.")
        if self.description is not None:
            if not isinstance(self.description, str):
                errors.append("Description must be text or null.")
            elif len(self.description) > 1024:
                errors.append("Description must be under 1024 characters.")

        errors.extend(_settings_errors(self.settings))

        if not isinstance(self.nodes, list):
            errors.append("Nodes must be a list.")
            return errors
        seen_ids: set[str] = set()
        for index, node in enumerate(self.nodes):
            node_errors = _node_errors(node)
            node_id = node.get("id") if isinstance(node, dict) else None
            label = f"Node '{node_id}'" if node_id else f"Node {index + 1}"
            errors.extend(f"{label}: {message}" for message in node_errors)
            if isinstance(node_id, str):
                if node_id in seen_ids:
                    errors.append(f"Node id '{node_id}' is used more than once.")
                seen_ids.add(node_id)

        errors.extend(self._function_file_errors(resource_mappings))
        return errors

    def _function_file_errors(
        self, resource_mappings: Optional[list[ResourceMapping]]
    ) -> list[str]:
        nodes_with_function = {
            node.get("id")
            for node in self.nodes
            if isinstance(node, dict)
            and isinstance(node.get("data"), dict)
            and node["data"].get("function")
        }
        errors = []
        for mapping in resource_mappings or []:
            if mapping.resource_type is not OutboundCampaignFunction:
                continue
            if OutboundCampaignFunction.folder_from_path(mapping.file_path) != self.folder:
                continue
            node_id = mapping.resource_name
            if node_id not in nodes_with_function:
                errors.append(
                    f"{FUNCTIONS_DIR}/{node_id}.py has no node '{node_id}' with a function "
                    "in campaign.yaml."
                )
        return errors

    def build_create_proto(self) -> campaigns_pb2.OutboundCampaign_Create:
        return campaigns_pb2.OutboundCampaign_Create(
            id=self.resource_id,
            name=self.name,
            **_drop_unset(dict(description=self.description)),
        )

    def build_update_proto(self) -> campaigns_pb2.OutboundCampaign_Update:
        description = (
            {"clear_description": True}
            if self.description is None
            else {"description": self.description}
        )
        return campaigns_pb2.OutboundCampaign_Update(
            id=self.resource_id, name=self.name, **description
        )

    def build_delete_proto(self) -> campaigns_pb2.OutboundCampaign_Delete:
        return campaigns_pb2.OutboundCampaign_Delete(id=self.resource_id)

    def settings_change(self) -> "OutboundCampaignSettings":
        """Return the settings as a change to send. Settings are always sent whole."""
        return OutboundCampaignSettings(
            resource_id=self.resource_id, name=self.name, settings=self.settings
        )

    def node_changes(
        self, original: Optional["OutboundCampaign"]
    ) -> tuple[
        list["OutboundCampaignNode"], list["OutboundCampaignNode"], list["OutboundCampaignNode"]
    ]:
        """Compare nodes with `original` and return the new, updated and deleted ones.

        A node counts as updated when its data, function code, position or label changed;
        `changed_fields` says which, so the update carries only those.
        """
        original_nodes = {node["id"]: node for node in (original.nodes if original else [])}
        current_ids = {node["id"] for node in self.nodes}
        new, updated = [], []
        for node in self.nodes:
            node_id = node["id"]
            change = OutboundCampaignNode(
                resource_id=f"{self.resource_id}:{node_id}",
                name=node.get("label") or node_id,
                campaign_id=self.resource_id,
                node=node,
                code=self.function_code.get(node_id, ""),
            )
            old = original_nodes.get(node_id)
            if old is None:
                new.append(change)
                continue
            old_code = original.function_code.get(node_id, "")
            change.changed_fields = tuple(
                name
                for name, differs in (
                    ("data", node.get("data") != old.get("data") or change.code != old_code),
                    ("position", node.get("position") != old.get("position")),
                    ("label", (node.get("label") or "") != (old.get("label") or "")),
                )
                if differs
            )
            if change.changed_fields:
                updated.append(change)
        deleted = [
            OutboundCampaignNode(
                resource_id=f"{self.resource_id}:{node_id}",
                name=node.get("label") or node_id,
                campaign_id=self.resource_id,
                node=node,
            )
            for node_id, node in original_nodes.items()
            if node_id not in current_ids
        ]
        return new, updated, deleted


def _settings_errors(settings: Any) -> list[str]:
    if not isinstance(settings, dict):
        return ["Settings must be a mapping."]
    errors = []
    unknown = sorted(set(settings) - set(SETTINGS_DEFAULTS))
    if unknown:
        errors.append(f"Unknown settings: {', '.join(unknown)}.")
    for key in (
        "startDate",
        "endDate",
        "fromNumber",
        "smsFromNumber",
        "defaultVariantId",
        "defaultTimezone",
    ):
        if settings.get(key) is not None and not isinstance(settings[key], str):
            errors.append(f"Setting '{key}' must be text or null.")
    country = settings.get("country")
    if country is not None and (
        not isinstance(country, str) or not re.fullmatch(r"[A-Za-z]{2}", country.strip())
    ):
        errors.append("Setting 'country' must be an ISO 3166-1 alpha-2 country code.")
    use_case = settings.get("useCase")
    if use_case is not None and use_case not in USE_CASES:
        errors.append(f"Setting 'useCase' must be one of: {', '.join(USE_CASES)}.")
    if not _is_positive_int_or_none(settings.get("dailyContactLimit")):
        errors.append("Setting 'dailyContactLimit' must be a positive whole number or null.")
    for key in ("voiceDispatchLimits", "smsDispatchLimits"):
        limits = settings.get(key)
        if limits is None:
            continue
        if not isinstance(limits, dict):
            errors.append(f"Setting '{key}' must be a mapping or null.")
            continue
        for limit_key, value in limits.items():
            if limit_key not in DISPATCH_LIMIT_KEYS:
                errors.append(f"Setting '{key}' has an unknown field '{limit_key}'.")
            elif not _is_positive_int_or_none(value):
                errors.append(
                    f"Setting '{key}.{limit_key}' must be a positive whole number or null."
                )
    window = settings.get("contactWindow")
    if window is not None:
        if not isinstance(window, dict):
            errors.append("Setting 'contactWindow' must be a mapping or null.")
        else:
            days = window.get("daysOfWeek")
            if not isinstance(days, list) or any(day not in DAYS_OF_WEEK for day in days):
                errors.append(
                    f"Setting 'contactWindow.daysOfWeek' must be a list of: {', '.join(DAYS_OF_WEEK)}."
                )
            for key in ("startTime", "endTime"):
                if not isinstance(window.get(key), str):
                    errors.append(f"Setting 'contactWindow.{key}' is required, as \"HH:mm\".")
            unknown = sorted(set(window) - set(CONTACT_WINDOW_KEYS))
            if unknown:
                errors.append(f"Setting 'contactWindow' has unknown fields: {', '.join(unknown)}.")
    return errors


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_positive_int_or_none(value: Any) -> bool:
    return value is None or (_is_int(value) and value > 0)


def _function_errors(function: Any) -> list[str]:
    if not isinstance(function, dict):
        return ["'function' must be a mapping with a name and description."]
    errors = []
    if "code" in function:
        errors.append(
            "'function.code' does not belong in campaign.yaml: put the code in "
            f"{FUNCTIONS_DIR}/<node id>.py."
        )
    unknown = sorted(set(function) - set(FUNCTION_KEYS) - {"code"})
    if unknown:
        errors.append(f"'function' has unknown fields: {', '.join(unknown)}.")
    name = function.get("name")
    if not isinstance(name, str) or not PYTHONIC_NAME.fullmatch(name):
        errors.append("'function.name' must be a valid Python name.")
    elif keyword.iskeyword(name):
        errors.append(f"'function.name' cannot be the Python keyword '{name}'.")
    if not isinstance(function.get("description"), str):
        errors.append("'function.description' is required.")
    return errors


def _routes_errors(routes: Any) -> list[str]:
    if not isinstance(routes, list):
        return ["'routes' must be a list."]
    for route in routes:
        if not isinstance(route, dict) or not isinstance(route.get("targetNodeId"), str):
            return ["Each route needs a 'targetNodeId'."]
        if route.get("outcome") is not None and not isinstance(route["outcome"], str):
            return ["A route's 'outcome' must be text."]
        if set(route) - {"targetNodeId", "outcome"}:
            return ["A route has only 'targetNodeId' and 'outcome'."]
    return []


def _node_errors(node: Any) -> list[str]:
    if not isinstance(node, dict):
        return ["must be a mapping."]
    errors = []
    unknown = sorted(set(node) - set(NODE_KEYS))
    if unknown:
        errors.append(f"unknown fields: {', '.join(unknown)}.")
    if not isinstance(node.get("id"), str) or not node["id"].strip():
        errors.append("'id' is required.")
    position = node.get("position")
    if not isinstance(position, dict) or not all(
        isinstance(position.get(axis), (int, float)) and not isinstance(position.get(axis), bool)
        for axis in ("x", "y")
    ):
        errors.append("'position' needs numeric 'x' and 'y'.")
    label = node.get("label")
    if label is not None and (not isinstance(label, str) or len(label) > 256):
        errors.append("'label' must be text under 256 characters.")
    data = node.get("data")
    if not isinstance(data, dict):
        return errors + ["'data' is required."]
    node_type = data.get("type")
    if node_type not in NODE_FIELDS:
        return errors + [f"'data.type' must be one of: {', '.join(NODE_FIELDS)}."]

    unknown = sorted(set(data) - {"type", *NODE_FIELDS[node_type]})
    if unknown:
        errors.append(f"unknown fields for a {node_type} node: {', '.join(unknown)}.")
    missing = [key for key in NODE_REQUIRED[node_type] if data.get(key) is None]
    if missing:
        errors.append(f"a {node_type} node needs {', '.join(repr(key) for key in missing)}.")
    for key, allowed in NODE_ENUMS.get(node_type, {}).items():
        if data.get(key) is not None and data[key] not in allowed:
            errors.append(f"'{key}' must be one of: {', '.join(allowed)}.")
    for key in NODE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{key}' must be text.")
    for key in NODE_NULLABLE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{key}' must be a node id or null.")
    if data.get("function") is not None:
        errors.extend(_function_errors(data["function"]))
    if "routes" in data:
        errors.extend(_routes_errors(data["routes"]))

    if node_type == "call":
        attempts = data.get("maxAttempts")
        if attempts is not None and not (_is_int(attempts) and 1 <= attempts <= 5):
            errors.append("'maxAttempts' must be a whole number from 1 to 5.")
        backoff = data.get("backoff")
        if backoff is not None and not (_is_int(backoff) and backoff >= 0):
            errors.append("'backoff' must be a whole number, 0 or more.")
        if data.get("voicemailEnabled") is not None and not isinstance(
            data["voicemailEnabled"], bool
        ):
            errors.append("'voicemailEnabled' must be true or false.")
        if data.get("voicemailEnabled"):
            for key in ("voicemailScript", "voicemailWhen"):
                if data.get(key) is None:
                    errors.append(f"'{key}' is required when voicemailEnabled is true.")
    elif node_type == "sms":
        timeout = data.get("replyTimeoutValue")
        if timeout is not None and not (_is_int(timeout) and timeout >= 0):
            errors.append("'replyTimeoutValue' must be a whole number, 0 or more.")
    elif node_type == "conditional":
        branches = data.get("branches")
        if branches is not None and (
            not isinstance(branches, list)
            or not all(
                isinstance(branch, dict)
                and all(
                    isinstance(branch.get(key), str) for key in ("id", "variable", "targetNodeId")
                )
                for branch in branches
            )
        ):
            errors.append("Each branch needs text 'id', 'variable' and 'targetNodeId'.")
    elif node_type == "wait":
        amount = data.get("amount")
        if amount is not None and not (_is_int(amount) and amount > 0):
            errors.append("'amount' must be a positive whole number.")
    elif node_type == "end":
        if data.get("writebackEnabled") is not None and not isinstance(
            data["writebackEnabled"], bool
        ):
            errors.append("'writebackEnabled' must be true or false.")
    return errors


@register_resource("outbound_campaign_functions")
@dataclass
class OutboundCampaignFunction(Resource):
    """A node's function code in `functions/<node_id>.py`.

    It is tracked so edits are detected, but never sent on its own: the code travels in its
    node's create or update.
    """

    campaign_folder: str = ""
    node_id: str = ""
    code: str = ""

    @staticmethod
    def id_for(campaign_folder: str, node_id: str) -> str:
        """Return the status-file id for a node's function file."""
        return f"{campaign_folder}/{node_id}"

    @staticmethod
    def folder_from_path(file_path: str) -> str:
        """Return the campaign folder name a function file belongs to."""
        return os.path.basename(os.path.dirname(os.path.dirname(file_path)))

    @classmethod
    def id_from_path(cls, file_path: str) -> str:
        """Return the status-file id for the function file at `file_path`."""
        node_id = os.path.splitext(os.path.basename(file_path))[0]
        return cls.id_for(cls.folder_from_path(file_path), node_id)

    @property
    def file_path(self) -> str:
        return os.path.join(
            CAMPAIGNS_DIR, self.campaign_folder, FUNCTIONS_DIR, f"{self.node_id}.py"
        )

    @property
    def raw(self) -> str:
        return self.code

    @property
    def command_type(self) -> str:
        return "outbound_campaign_node"

    @staticmethod
    def make_pretty(contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "OutboundCampaignFunction"]:
        functions = {}
        for campaign in _projection_campaigns(projection) or []:
            folder = utils.clean_name(campaign.get("name") or "")
            for node in _projection_nodes(campaign):
                code = ((node.get("data") or {}).get("function") or {}).get("code") or ""
                if not code:
                    continue
                node_id = node.get("id") or ""
                if not SAFE_NODE_ID.fullmatch(node_id):
                    logger.warning(
                        "Campaign '%s' node '%s' has an id that cannot be a file name; "
                        "its function code is not pulled.",
                        campaign.get("name"),
                        node_id,
                    )
                    continue
                resource = cls(
                    resource_id=cls.id_for(folder, node_id),
                    name=node_id,
                    campaign_folder=folder,
                    node_id=node_id,
                    code=code,
                )
                functions[resource.resource_id] = resource
        return functions

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaignFunction":
        node_id = os.path.splitext(os.path.basename(file_path))[0]
        return cls(
            resource_id=resource_id,
            name=node_id,
            campaign_folder=cls.folder_from_path(file_path),
            node_id=node_id,
            code=cls.read_to_raw(file_path),
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        campaigns_path = os.path.join(base_path, CAMPAIGNS_DIR)
        if not os.path.isdir(campaigns_path):
            return []
        discovered = []
        for folder in sorted(os.listdir(campaigns_path)):
            functions_path = os.path.join(campaigns_path, folder, FUNCTIONS_DIR)
            if not os.path.isdir(functions_path):
                continue
            discovered.extend(
                os.path.join(functions_path, file_name)
                for file_name in sorted(os.listdir(functions_path))
                if file_name.endswith(".py")
            )
        return discovered

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        has_campaign = any(
            mapping.resource_type is OutboundCampaign
            and os.path.basename(os.path.dirname(mapping.file_path)) == self.campaign_folder
            for mapping in resource_mappings or []
        )
        if not has_campaign:
            raise ValueError(f"No {CAMPAIGN_FILE} in outbound_campaigns/{self.campaign_folder}/.")

    def build_create_proto(self):
        raise NotImplementedError("Campaign function files are pushed through their node.")

    def build_update_proto(self):
        raise NotImplementedError("Campaign function files are pushed through their node.")

    def build_delete_proto(self):
        raise NotImplementedError("Campaign function files are pushed through their node.")


@dataclass
class OutboundCampaignSettings(SubResource):
    """A campaign's settings, sent as one update command."""

    settings: dict

    @property
    def command_type(self) -> str:
        return "outbound_campaign_update_settings"

    @property
    def create_command_type(self) -> str:
        return "outbound_campaign_update_settings"

    @property
    def update_command_type(self) -> str:
        return "outbound_campaign_update_settings"

    def build_update_proto(self) -> campaigns_pb2.OutboundCampaign_UpdateSettings:
        return campaigns_pb2.OutboundCampaign_UpdateSettings(
            id=self.resource_id, settings=settings_proto(self.settings)
        )

    def build_create_proto(self) -> campaigns_pb2.OutboundCampaign_UpdateSettings:
        return self.build_update_proto()

    def build_delete_proto(self):
        raise NotImplementedError("Campaign settings cannot be deleted.")


@dataclass
class OutboundCampaignNode(SubResource):
    """One node of a campaign, sent as a node create, update or delete command."""

    campaign_id: str
    node: dict
    code: str = ""
    changed_fields: tuple[str, ...] = ("data", "position", "label")

    @property
    def node_id(self) -> str:
        return self.node["id"]

    @property
    def command_type(self) -> str:
        return "outbound_campaign_update_node"

    @property
    def create_command_type(self) -> str:
        return "outbound_campaign_create_node"

    @property
    def update_command_type(self) -> str:
        return "outbound_campaign_update_node"

    @property
    def delete_command_type(self) -> str:
        return "outbound_campaign_delete_node"

    def _position_proto(self) -> campaigns_pb2.Position:
        position = self.node.get("position") or {}
        return campaigns_pb2.Position(x=position.get("x", 0.0), y=position.get("y", 0.0))

    def build_create_proto(self) -> campaigns_pb2.OutboundCampaign_CreateNode:
        data_field, data = node_data_proto(self.node["data"], self.code)
        return campaigns_pb2.OutboundCampaign_CreateNode(
            outbound_campaign_id=self.campaign_id,
            node=campaigns_pb2.OutboundCampaignNode(
                id=self.node_id,
                position=self._position_proto(),
                **_drop_unset(dict(label=self.node.get("label"))),
                **{data_field: data},
            ),
        )

    def build_update_proto(self) -> campaigns_pb2.OutboundCampaign_UpdateNode:
        fields: dict[str, Any] = {}
        if "data" in self.changed_fields:
            data_field, data = node_data_proto(self.node["data"], self.code)
            fields["data"] = campaigns_pb2.OutboundCampaignNodeData(**{data_field: data})
        if "position" in self.changed_fields:
            fields["position"] = self._position_proto()
        if "label" in self.changed_fields:
            fields["label"] = self.node.get("label") or ""
        return campaigns_pb2.OutboundCampaign_UpdateNode(
            outbound_campaign_id=self.campaign_id, node_id=self.node_id, **fields
        )

    def build_delete_proto(self) -> campaigns_pb2.OutboundCampaign_DeleteNode:
        return campaigns_pb2.OutboundCampaign_DeleteNode(
            outbound_campaign_id=self.campaign_id, node_id=self.node_id
        )
