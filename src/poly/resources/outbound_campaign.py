"""Copyright PolyAI Limited"""

import ast
import keyword
import logging
import os
import re
import zoneinfo
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import poly.resources.resource_utils as utils
from poly.handlers.protobuf import outbound_campaigns_pb2 as campaigns_pb2
from poly.resources.countries import COUNTRY_CODES
from poly.resources.resource import (
    MultiResourceYamlResource,
    Resource,
    ResourceMapping,
    SubResource,
    _parse_multi_resource_path,
    _strip_strings,
    register_resource,
)
from poly.resources.variant_attributes import Variant

logger = logging.getLogger(__name__)

CAMPAIGNS_DIR = "outbound_campaigns"
CAMPAIGN_FILE = "campaign.yaml"
FUNCTIONS_DIR = "functions"
CAMPAIGN_KEY = "campaign"
NODES_KEY = "nodes"
CAMPAIGN_KEYS = ("name", "description", "settings")

VARIANT_ID_KEY = "defaultVariantId"
VARIANT_NAME_KEY = "defaultVariant"
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
TIME_OF_DAY = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

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
        "defaultRoute",
    ),
    "sms": (
        "function",
        "messageTemplate",
        "replyFlowName",
        "replyTimeoutValue",
        "replyTimeoutUnit",
        "defaultRoute",
    ),
    "conditional": ("function", "branches", "defaultTargetNodeId"),
    "wait": ("amount", "unit", "targetNodeId"),
    "writeback": ("target", "function", "targetNodeId"),
    "end": ("exitReason", "writebackEnabled", "function"),
}
NODE_DEFAULTS: dict[str, dict[str, Any]] = {
    "trigger": {"routes": [], "sourceType": "csv", "ingestInterval": "daily"},
    "call": {"defaultRoute": None},
    "sms": {"defaultRoute": None},
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
DEFAULT_NODE_NAMES = {
    "trigger": "Trigger",
    "call": "Voice call",
    "sms": "SMS",
    "conditional": "Condition",
    "wait": "Wait",
    "writeback": "Writeback",
    "end": "End",
}
PRETTY_ROUTE_KEYS = {"targetNodeId": "next", "defaultTargetNodeId": "defaultNext"}

CSV_TRIGGER_PARAMETERS = ("contacts: list[dict]", "outbound_campaign: OutboundCampaign")
API_TRIGGER_PARAMETERS = ("outbound_campaign: OutboundCampaign", "sync: dict")
CSV_WRITEBACK_PARAMETERS = (
    "outbound_contacts: list[OutboundContact]",
    "outbound_campaign: OutboundCampaign",
)
PER_CONTACT_PARAMETERS = (
    "outbound_contact: OutboundContact",
    "outbound_campaign: OutboundCampaign",
)

PYTHONIC_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
TIMEZONES = {zone.lower() for zone in zoneinfo.available_timezones()}


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


def normalise_node_data(data: Any, from_platform: bool = False) -> Any:
    """Fill a node's defaults and order its keys as in `campaign.yaml`.

    With `from_platform`, fields the ADK does not keep (function code, call and SMS `routes`)
    are dropped. Input that isn't a node of a known type is returned as is.
    """
    if not isinstance(data, dict) or data.get("type") not in NODE_FIELDS:
        return data
    node_type = data["type"]
    data = {**NODE_DEFAULTS.get(node_type, {}), **data}
    if from_platform:
        data = {
            key: value for key, value in data.items() if key in ("type", *NODE_FIELDS[node_type])
        }
    if "function" in data:
        data["function"] = _normalise_function(data["function"], from_platform)
    return _ordered(data, ("type", *NODE_FIELDS[node_type]))


def _normalise_position(position: Any) -> Optional[dict]:
    if not isinstance(position, dict):
        return None
    return {
        axis: float(value) if isinstance(value, (int, float)) else 0.0
        for axis, value in ((axis, position.get(axis)) for axis in ("x", "y"))
    }


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


def map_route_targets(data: dict, change: Callable[[str], str]) -> dict:
    """Return a copy of node `data` with `change` applied to every node it routes to."""
    if not isinstance(data, dict):
        return data
    data = dict(data)
    for key in ("defaultRoute", "defaultTargetNodeId", "targetNodeId"):
        if isinstance(data.get(key), str):
            data[key] = change(data[key])
    for key in ("routes", "branches"):
        if isinstance(data.get(key), list):
            data[key] = [
                {**item, "targetNodeId": change(item["targetNodeId"])}
                if isinstance(item, dict) and isinstance(item.get("targetNodeId"), str)
                else item
                for item in data[key]
            ]
    return data


def route_targets(data: dict) -> list[str]:
    """Return the ids (or names) of every node `data` routes to, in order."""
    targets: list[str] = []
    map_route_targets(data, lambda target: targets.append(target) or target)
    return targets


def _rename_route_keys(data: dict, renames: dict[str, str]) -> dict:
    def rename(values: dict) -> dict:
        return {renames.get(key, key): value for key, value in values.items()}

    data = rename(data)
    for key in ("routes", "branches"):
        if isinstance(data.get(key), list):
            data[key] = [rename(item) if isinstance(item, dict) else item for item in data[key]]
    return data


def _routes_proto(routes: list[dict]) -> list[campaigns_pb2.RouteEdge]:
    return [
        campaigns_pb2.RouteEdge(
            **utils.drop_unset(
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
            **utils.drop_unset(
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
            campaign_function=_function_proto(function, code),
            **utils.drop_unset(
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
            campaign_function=_function_proto(function, code),
            **utils.drop_unset(
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
            **utils.drop_unset(dict(default_target_node_id=data.get("defaultTargetNodeId"))),
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
        **utils.drop_unset(
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
        **utils.drop_unset(
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


def campaign_folders(campaigns: list[dict]) -> dict[str, str]:
    """Return each campaign's folder by id.

    The folder is the cleaned name. Campaign names need not be unique, so a later campaign whose
    name cleans to a folder already taken gets the end of its id added.
    """
    folders: dict[str, str] = {}
    taken: set[str] = set()
    for campaign in campaigns:
        folder = utils.clean_name(campaign.get("name") or "")
        if not folder or folder in taken:
            folder = f"{folder}-{utils.clean_name(campaign['id'].rsplit('-', 1)[-1])[-8:]}".strip(
                "-"
            )
        taken.add(folder)
        folders[campaign["id"]] = folder
    return folders


def node_names(nodes: list[dict]) -> dict[str, str]:
    """Return each platform node's name by id: its label, or a default for its type.

    Labels are kept as they are when present and unique. A node without one, or whose label
    another node already has, gets its type's default name, numbered if that is taken too.
    """
    names: dict[str, str] = {}
    taken: set[str] = set()
    unnamed = []
    for node in nodes:
        label = (node.get("label") or "").strip()
        if label and utils.clean_name(label) and utils.clean_name(label) not in taken:
            taken.add(utils.clean_name(label))
            names[node["id"]] = label
        else:
            unnamed.append((node, label))
    for node, label in unnamed:
        base = label or DEFAULT_NODE_NAMES.get((node.get("data") or {}).get("type"), "Node")
        name, number = base, 2
        while utils.clean_name(name) in taken:
            name, number = f"{base} {number}", number + 1
        taken.add(utils.clean_name(name))
        names[node["id"]] = name
    return names


def function_file_stem(node_name: str) -> str:
    """Return the file name, without `.py`, that holds the function of the node `node_name`."""
    return utils.clean_name(node_name)


def campaign_folder_of(path: str) -> str:
    """Return the campaign folder a path inside `outbound_campaigns/<folder>/` belongs to."""
    parts = os.path.normpath(path or "").split(os.sep)
    if CAMPAIGNS_DIR in parts:
        index = len(parts) - 1 - parts[::-1].index(CAMPAIGNS_DIR)
        if index + 1 < len(parts):
            return parts[index + 1]
    return ""


def _campaign_file(base_path: str, folder: str) -> str:
    return os.path.join(base_path, CAMPAIGNS_DIR, folder, CAMPAIGN_FILE)


def _campaign_folders_on_disk(base_path: str) -> list[str]:
    campaigns_path = os.path.join(base_path, CAMPAIGNS_DIR)
    if not os.path.isdir(campaigns_path):
        return []
    return [
        folder
        for folder in sorted(os.listdir(campaigns_path))
        if os.path.isfile(_campaign_file(base_path, folder))
    ]


@register_resource("outbound_campaigns")
@dataclass
class OutboundCampaign(MultiResourceYamlResource):
    """An outbound campaign's name, description and settings in `<folder>/campaign.yaml`.

    The same file holds the campaign's nodes under `nodes`, each an `OutboundCampaignNode`;
    this resource reads and writes only its own keys.
    """

    resource_id_prefix = "CMPGN"
    top_level_name = CAMPAIGN_KEY

    description: Optional[str] = None
    settings: dict = field(default_factory=lambda: normalise_settings({}))
    folder_name: str = ""

    node_entries: Any = field(default=None, init=False, repr=False, compare=False)
    unknown_keys: list[str] = field(default_factory=list, init=False, repr=False, compare=False)

    @property
    def folder(self) -> str:
        """The campaign's folder under `outbound_campaigns/`."""
        return self.folder_name or utils.clean_name(self.name)

    @property
    def file_path(self) -> str:
        return os.path.join(CAMPAIGNS_DIR, self.folder, CAMPAIGN_FILE, CAMPAIGN_KEY)

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
        return {"name": self.name, "description": self.description, "settings": self.settings}

    @classmethod
    def from_yaml_dict(
        cls, yaml_dict: dict, resource_id: str, name: str = "", **kwargs
    ) -> "OutboundCampaign":
        yaml_dict = _strip_strings(_plain(yaml_dict or {}))
        return cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or "",
            description=yaml_dict.get("description"),
            settings=normalise_settings(yaml_dict.get("settings")),
        )

    @classmethod
    def _top_level(cls, file_path: str) -> dict:
        true_file_path, _ = _parse_multi_resource_path(file_path)
        top = cls._get_top_level_data(true_file_path)
        if not isinstance(top, dict):
            raise ValueError(f"{CAMPAIGN_FILE} must be a mapping: {true_file_path}")
        return top

    @classmethod
    def _get_matching(cls, file_path: str) -> dict:
        top = cls._top_level(file_path)
        return {key: top[key] for key in CAMPAIGN_KEYS if key in top}

    def save(
        self, base_path: str, format: bool = False, save_to_cache: bool = False, **kwargs
    ) -> None:
        """Write the campaign's keys into its `campaign.yaml`, leaving its nodes as they are."""
        yaml_content = self.to_pretty_dict(self.to_yaml_dict(), file_path=self.file_path, **kwargs)
        if format:
            content = self.format_resource(utils.dump_yaml(yaml_content), file_name=self.name)
            yaml_content = utils.load_yaml(content) or {}
        true_file_path, _ = _parse_multi_resource_path(self.get_path(base_path))
        if not os.path.exists(true_file_path):
            if save_to_cache:
                self._file_cache.setdefault(true_file_path, (0.0, {}))
            else:
                self.save_to_file("", true_file_path)
        top = self._get_top_level_data(true_file_path)
        if not isinstance(top, dict):
            top = {}
        top = {
            **yaml_content,
            **{key: value for key, value in top.items() if key not in CAMPAIGN_KEYS},
        }
        self._update_cache_after_write(true_file_path, top)
        if not save_to_cache:
            self.save_to_file(utils.dump_yaml(top), true_file_path)

    @classmethod
    def delete_resource(cls, file_path: str, save_to_cache: bool = False) -> None:
        """Remove the campaign's keys from its file, and the file once nothing is left in it."""
        true_file_path, _ = _parse_multi_resource_path(file_path)
        if not os.path.exists(true_file_path):
            return
        top = cls._get_top_level_data(true_file_path)
        remaining = (
            {key: value for key, value in top.items() if key not in CAMPAIGN_KEYS}
            if isinstance(top, dict)
            else {}
        )
        if is_empty_campaign_file(remaining):
            remaining = {}
        cls._update_cache_after_write(true_file_path, remaining)
        if save_to_cache:
            return
        if remaining:
            cls.save_to_file(utils.dump_yaml(remaining), true_file_path)
        else:
            os.remove(true_file_path)
            cls._file_cache.pop(true_file_path, None)

    @staticmethod
    def remove_empty_files(base_path: str) -> None:
        """Delete `campaign.yaml` files left with no campaign and no nodes in them."""
        for folder in _campaign_folders_on_disk(base_path):
            path = _campaign_file(base_path, folder)
            try:
                top = utils.load_yaml(Resource.read_from_file(path))
            except Exception:
                continue
            if is_empty_campaign_file(top):
                os.remove(path)

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "OutboundCampaign"]:
        """Parse campaigns from a projection, skipping archived ones. Returns `{}` if it has none."""
        campaigns = _projection_campaigns(projection)
        if campaigns is None:
            logger.debug("No outbound campaigns in projection - they will not be pulled.")
            return {}
        folders = campaign_folders(campaigns)
        return {
            campaign["id"]: cls(
                resource_id=campaign["id"],
                name=_strip_strings(campaign.get("name") or ""),
                description=_strip_strings(campaign.get("description")),
                settings=_strip_strings(normalise_settings(campaign.get("settings"))),
                folder_name=folders[campaign["id"]],
            )
            for campaign in campaigns
        }

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Show the default variant by name, under `defaultVariant`."""
        settings = d.get("settings")
        if isinstance(settings, dict) and VARIANT_ID_KEY in settings:
            variant_id = settings[VARIANT_ID_KEY]
            if variant_id:
                variant_id = (
                    utils.resource_name_for_id(variant_id, Variant, resource_mappings) or variant_id
                )
            d["settings"] = _rename_key(settings, VARIANT_ID_KEY, VARIANT_NAME_KEY, variant_id)
        return d

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Turn `defaultVariant` back into the variant's id, under `defaultVariantId`."""
        yaml_dict = super().from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, **kwargs
        )
        settings = yaml_dict.get("settings")
        if isinstance(settings, dict) and VARIANT_NAME_KEY in settings:
            variant_name = settings[VARIANT_NAME_KEY]
            if variant_name:
                variant_name = (
                    utils.resource_id_for_name(variant_name, Variant, resource_mappings)
                    or variant_name
                )
            yaml_dict["settings"] = _rename_key(
                settings, VARIANT_NAME_KEY, VARIANT_ID_KEY, variant_name
            )
        return yaml_dict

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaign":
        campaign: OutboundCampaign = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )
        folder = campaign_folder_of(file_path)
        expected = utils.clean_name(campaign.name)
        if folder != expected and not folder.startswith(f"{expected}-"):
            raise ValueError(
                f"Campaign folder name does not match campaign name '{campaign.name}'. "
                f"{folder} != {expected}"
            )
        campaign.folder_name = folder
        top = cls._top_level(file_path)
        campaign.node_entries = top.get(NODES_KEY)
        campaign.unknown_keys = sorted(set(top) - {*CAMPAIGN_KEYS, NODES_KEY})
        return campaign

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        return [
            os.path.join(_campaign_file(base_path, folder), CAMPAIGN_KEY)
            for folder in _campaign_folders_on_disk(base_path)
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
        if self.unknown_keys:
            errors.append(f"Unknown fields: {', '.join(self.unknown_keys)}.")
        errors.extend(_settings_errors(self.settings))
        errors.extend(_node_entry_errors(self.node_entries))

        variant_id = self.settings.get(VARIANT_ID_KEY) if isinstance(self.settings, dict) else None
        if variant_id and resource_mappings is not None:
            if utils.resource_name_for_id(variant_id, Variant, resource_mappings) is None:
                errors.append(f"Variant '{variant_id}' not found.")
        return errors

    def is_modified(self, other_hash: str) -> bool:
        """A node list that can't be read in full counts as a change, so validation reports it."""
        return super().is_modified(other_hash) or bool(_node_entry_errors(self.node_entries))

    def build_create_proto(self) -> campaigns_pb2.OutboundCampaign_Create:
        return campaigns_pb2.OutboundCampaign_Create(
            id=self.resource_id,
            name=self.name,
            **utils.drop_unset(dict(description=self.description)),
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

    def get_new_updated_deleted_subresources(
        self, old_resource: Optional["OutboundCampaign"]
    ) -> tuple[list[SubResource], list[SubResource], list[SubResource]]:
        """Return the settings to send: always for a new campaign, otherwise only when changed."""
        if old_resource is None:
            return [self.settings_change()], [], []
        if self.settings != old_resource.settings:
            return [], [self.settings_change()], []
        return [], [], []


def is_empty_campaign_file(top: Any) -> bool:
    """Whether a parsed `campaign.yaml` holds neither a campaign nor any node."""
    if not top:
        return True
    return isinstance(top, dict) and set(top) <= {NODES_KEY} and not top.get(NODES_KEY)


def _rename_key(values: dict, old_key: str, new_key: str, value: Any) -> dict:
    return {
        (new_key if key == old_key else key): (value if key == old_key else item)
        for key, item in values.items()
    }


def _node_entry_errors(entries: Any) -> list[str]:
    if entries is None:
        return []
    if not isinstance(entries, list):
        return ["Nodes must be a list."]
    errors = []
    names: set[str] = set()
    triggers = 0
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"Node {index} must be a mapping.")
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not utils.clean_name(name):
            errors.append(f"Node {index} needs a name.")
        elif utils.clean_name(name) in names:
            errors.append(f"Node name '{name}' is used more than once.")
        else:
            names.add(utils.clean_name(name))
        if entry.get("type") == "trigger":
            triggers += 1
    if triggers > 1:
        errors.append("A campaign can have only one trigger node.")
    return errors


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
    start, end = settings.get("startDate"), settings.get("endDate")
    if isinstance(start, str) and isinstance(end, str) and end < start:
        errors.append("Setting 'endDate' can't be before 'startDate'.")
    country = settings.get("country")
    if country is not None and (
        not isinstance(country, str) or country.strip().upper() not in COUNTRY_CODES
    ):
        errors.append("Setting 'country' must be an ISO 3166-1 alpha-2 country code, e.g. US.")
    timezone = settings.get("defaultTimezone")
    if isinstance(timezone, str) and TIMEZONES and timezone.lower() not in TIMEZONES:
        errors.append(f"Setting 'defaultTimezone' must be an IANA time zone, not '{timezone}'.")
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
            errors.extend(_contact_window_errors(window))
    return errors


def _contact_window_errors(window: dict) -> list[str]:
    errors = []
    days = window.get("daysOfWeek")
    if not isinstance(days, list) or any(day not in DAYS_OF_WEEK for day in days):
        errors.append(
            f"Setting 'contactWindow.daysOfWeek' must be a list of: {', '.join(DAYS_OF_WEEK)}."
        )
    elif not days:
        errors.append("Setting 'contactWindow' needs at least one day.")
    times = [window.get(key) for key in ("startTime", "endTime")]
    for key, value in zip(("startTime", "endTime"), times):
        if not isinstance(value, str) or not TIME_OF_DAY.fullmatch(value):
            errors.append(f"Setting 'contactWindow.{key}' must be a time of day, as \"HH:mm\".")
    if all(isinstance(value, str) and TIME_OF_DAY.fullmatch(value) for value in times):
        if times[1] <= times[0]:
            errors.append("Setting 'contactWindow' must end after it starts, on the same day.")
    unknown = sorted(set(window) - set(CONTACT_WINDOW_KEYS))
    if unknown:
        errors.append(f"Setting 'contactWindow' has unknown fields: {', '.join(unknown)}.")
    return errors


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_positive_int_or_none(value: Any) -> bool:
    return value is None or (_is_int(value) and value > 0)


def _function_errors(function: Any, function_file: str) -> list[str]:
    if not isinstance(function, dict):
        return ["'function' must be a mapping with a name and description."]
    errors = []
    if "code" in function:
        errors.append(
            f"'function.code' does not belong in {CAMPAIGN_FILE}: put the code in {function_file}."
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
            return ["Each route needs a 'next'."]
        if route.get("outcome") is not None and not isinstance(route["outcome"], str):
            return ["A route's 'outcome' must be text."]
        if set(route) - {"targetNodeId", "outcome"}:
            return ["A route has only 'next' and 'outcome'."]
    return []


def node_data_errors(data: Any, function_file: str) -> list[str]:
    """Return what the platform would refuse in a node's type and fields."""
    if not isinstance(data, dict):
        return ["must be a mapping."]
    node_type = data.get("type")
    if node_type not in NODE_FIELDS:
        return [f"'type' must be one of: {', '.join(NODE_FIELDS)}."]

    errors = []
    unknown = sorted(set(data) - {"type", *NODE_FIELDS[node_type]})
    if unknown:
        pretty = [PRETTY_ROUTE_KEYS.get(key, key) for key in unknown]
        errors.append(f"unknown fields for a {node_type} node: {', '.join(pretty)}.")
    missing = [key for key in NODE_REQUIRED[node_type] if data.get(key) is None]
    if missing:
        pretty = [repr(PRETTY_ROUTE_KEYS.get(key, key)) for key in missing]
        errors.append(f"a {node_type} node needs {', '.join(pretty)}.")
    for key, allowed in NODE_ENUMS.get(node_type, {}).items():
        if data.get(key) is not None and data[key] not in allowed:
            errors.append(f"'{key}' must be one of: {', '.join(allowed)}.")
    for key in NODE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{PRETTY_ROUTE_KEYS.get(key, key)}' must be text.")
    for key in NODE_NULLABLE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{PRETTY_ROUTE_KEYS.get(key, key)}' must be a node name or null.")
    if data.get("function") is not None:
        errors.extend(_function_errors(data["function"], function_file))
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
            errors.append("Each branch needs text 'id', 'variable' and 'next'.")
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


def function_parameters(data: dict) -> Optional[tuple[str, ...]]:
    """Return the parameters the node's function is called with, or None if it runs none."""
    node_type = data.get("type")
    if node_type == "wait":
        return None
    if node_type == "trigger":
        source = data.get("sourceType")
        if source == "webhook":
            return None
        return API_TRIGGER_PARAMETERS if source == "api" else CSV_TRIGGER_PARAMETERS
    if node_type == "writeback" and data.get("target") == "csv":
        return CSV_WRITEBACK_PARAMETERS
    return PER_CONTACT_PARAMETERS


def def_line_error(function_name: str, code: str, parameters: tuple[str, ...]) -> Optional[str]:
    """Say why `code` doesn't define `function_name` with exactly `parameters`, or return None.

    The platform reads the last top-level `def` of the function, which must be whole on one line
    and end in a colon. Parameters are passed by name, so only their names have to match.
    """
    if not code.strip():
        return None
    def_line = f"def {function_name}({', '.join(parameters)}):"
    whole_line = (
        f"the code must define {function_name} with its whole def line, ending in a colon, "
        f"on one line at the left margin: `{def_line}`"
    )
    pattern = re.compile(rf"^def\s+{re.escape(function_name)}\s*\(")
    lines = [line for line in code.splitlines() if pattern.match(line)]
    if not lines:
        return whole_line
    definition = None
    for source in (lines[-1], f"{lines[-1]}\n    pass"):
        try:
            definition = ast.parse(source).body[0]
            break
        except SyntaxError:
            continue
    if not isinstance(definition, ast.FunctionDef):
        return whole_line
    arguments = definition.args
    found = [
        argument.arg
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *([arguments.vararg] if arguments.vararg else []),
            *arguments.kwonlyargs,
            *([arguments.kwarg] if arguments.kwarg else []),
        )
    ]
    expected = [parameter.split(":")[0].strip() for parameter in parameters]
    if sorted(found) != sorted(expected):
        return (
            f"{function_name} must take exactly ({', '.join(expected)}), not ({', '.join(found)})"
        )
    return None


@register_resource("outbound_campaign_nodes")
@dataclass
class OutboundCampaignNode(MultiResourceYamlResource):
    """One node of a campaign: an entry under `nodes` in its `campaign.yaml`, keyed by name.

    The id is `<campaign id>:<node id>`. Routes name the nodes they lead to. The position is
    kept from the last pull, as a flow step's is, and the function code lives in
    `functions/<node name>.py`.
    """

    top_level_name = NODES_KEY

    campaign_folder: str = ""
    data: dict = field(default_factory=dict)
    position: Optional[dict] = None
    code: str = ""

    @property
    def campaign_id(self) -> str:
        """The id of the campaign the node belongs to."""
        return self.resource_id.split(":", 1)[0]

    @property
    def node_id(self) -> str:
        """The node's id within its campaign."""
        return self.resource_id.split(":", 1)[-1]

    @property
    def file_path(self) -> str:
        return os.path.join(
            CAMPAIGNS_DIR,
            self.campaign_folder,
            CAMPAIGN_FILE,
            NODES_KEY,
            utils.clean_name(self.name, lowercase=False),
        )

    @property
    def function_file(self) -> str:
        """The path of the file holding the node's function code."""
        return os.path.join(
            CAMPAIGNS_DIR,
            self.campaign_folder,
            FUNCTIONS_DIR,
            f"{function_file_stem(self.name)}.py",
        )

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

    def to_yaml_dict(self) -> dict:
        return {"name": self.name, **self.data}

    def compute_hash(self) -> str:
        return utils.compute_hash_from_dict(
            {"node": _strip_strings(self.to_yaml_dict()), "code": self.code}
        )

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str = "",
        known_position: Optional[dict] = None,
        **kwargs,
    ) -> "OutboundCampaignNode":
        yaml_dict = _strip_strings(_plain(yaml_dict or {}))
        node_name = yaml_dict.pop("name", None) or name
        return cls(
            resource_id=resource_id,
            name=node_name,
            data=normalise_node_data(yaml_dict),
            position=known_position,
        )

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "OutboundCampaignNode"]:
        nodes: dict[str, OutboundCampaignNode] = {}
        campaigns = _projection_campaigns(projection) or []
        folders = campaign_folders(campaigns)
        for campaign in campaigns:
            platform_nodes = _projection_nodes(campaign)
            names = node_names(platform_nodes)
            for platform_node in platform_nodes:
                data = platform_node.get("data") or {}
                node = cls(
                    resource_id=f"{campaign['id']}:{platform_node['id']}",
                    name=names[platform_node["id"]],
                    campaign_folder=folders[campaign["id"]],
                    data=_strip_strings(normalise_node_data(data, from_platform=True)),
                    position=_normalise_position(platform_node.get("position")),
                    code=(data.get("function") or {}).get("code") or "",
                )
                nodes[node.resource_id] = node
        return nodes

    @classmethod
    def _names_by_id(
        cls, resource_mappings: Optional[list[ResourceMapping]], path: Optional[str]
    ) -> dict[str, str]:
        folder = campaign_folder_of(path or "")
        if not folder:
            return {}
        return {
            mapping.resource_id.split(":", 1)[-1]: mapping.resource_name
            for mapping in resource_mappings or []
            if mapping.resource_type is cls and campaign_folder_of(mapping.file_path) == folder
        }

    @classmethod
    def to_pretty_dict(
        cls,
        d: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Name the nodes each route leads to, under `next` and `defaultNext`."""
        names = cls._names_by_id(resource_mappings, file_path)
        d = map_route_targets(d, lambda target: names.get(target, target))
        return _rename_route_keys(d, PRETTY_ROUTE_KEYS)

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Turn the node names in routes back into node ids."""
        yaml_dict = super().from_pretty_dict(
            yaml_dict, resource_mappings=resource_mappings, **kwargs
        )
        yaml_dict = _rename_route_keys(yaml_dict, {v: k for k, v in PRETTY_ROUTE_KEYS.items()})
        ids = {
            name: node_id
            for node_id, name in cls._names_by_id(resource_mappings, file_path).items()
        }
        return map_route_targets(yaml_dict, lambda target: ids.get(target, target))

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaignNode":
        node: OutboundCampaignNode = super().read_local_resource(
            file_path, resource_id=resource_id, resource_name=resource_name, **kwargs
        )
        node.campaign_folder = campaign_folder_of(file_path)
        true_file_path, _ = _parse_multi_resource_path(file_path)
        code_path = os.path.join(
            os.path.dirname(true_file_path), FUNCTIONS_DIR, f"{function_file_stem(node.name)}.py"
        )
        if os.path.isfile(code_path):
            node.code = Resource.read_from_file(code_path)
        return node

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        discovered = []
        for folder in _campaign_folders_on_disk(base_path):
            path = _campaign_file(base_path, folder)
            try:
                top = cls._get_top_level_data(path)
            except utils.MergeConflictError:
                raise
            except Exception:
                continue
            entries = top.get(NODES_KEY) if isinstance(top, dict) else None
            seen: set[str] = set()
            for entry in entries if isinstance(entries, list) else []:
                name = entry.get("name") if isinstance(entry, dict) else None
                if not isinstance(name, str):
                    continue
                clean = utils.clean_name(name, lowercase=False)
                if clean and clean.lower() not in seen:
                    seen.add(clean.lower())
                    discovered.append(os.path.join(path, NODES_KEY, clean))
        return discovered

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        errors = node_data_errors(self.data, self.function_file)
        if len(self.name) > 256:
            errors.append("The name must be under 256 characters.")
        if resource_mappings is not None and isinstance(self.data, dict):
            known = self._names_by_id(resource_mappings, self.file_path)
            errors.extend(
                f"'{target}' is not a node in this campaign."
                for target in route_targets(self.data)
                if target not in known
            )
        function = self.data.get("function") if isinstance(self.data, dict) else None
        if self.code and not function:
            errors.append(f"{self.function_file} has code, but the node has no function.")
        parameters = function_parameters(self.data) if isinstance(self.data, dict) else None
        if (
            isinstance(function, dict)
            and isinstance(function.get("name"), str)
            and PYTHONIC_NAME.fullmatch(function["name"])
            and parameters
        ):
            error = def_line_error(function["name"], self.code, parameters)
            if error:
                errors.append(f"{self.function_file}: {error}.")
        if errors:
            raise ValueError("; ".join(errors))

    def _position_proto(self) -> campaigns_pb2.Position:
        position = self.position or {}
        return campaigns_pb2.Position(x=position.get("x", 0.0), y=position.get("y", 0.0))

    def _data_proto(self) -> dict:
        data_field, data = node_data_proto(self.data, self.code)
        return {data_field: data}

    def build_create_proto(self) -> campaigns_pb2.OutboundCampaign_CreateNode:
        return campaigns_pb2.OutboundCampaign_CreateNode(
            outbound_campaign_id=self.campaign_id,
            node=campaigns_pb2.OutboundCampaignNode(
                id=self.node_id,
                position=self._position_proto(),
                label=self.name,
                **self._data_proto(),
            ),
        )

    def build_update_proto(self) -> campaigns_pb2.OutboundCampaign_UpdateNode:
        return campaigns_pb2.OutboundCampaign_UpdateNode(
            outbound_campaign_id=self.campaign_id,
            node_id=self.node_id,
            data=campaigns_pb2.OutboundCampaignNodeData(**self._data_proto()),
            position=self._position_proto(),
            label=self.name,
        )

    def build_delete_proto(self) -> campaigns_pb2.OutboundCampaign_DeleteNode:
        return campaigns_pb2.OutboundCampaign_DeleteNode(
            outbound_campaign_id=self.campaign_id, node_id=self.node_id
        )


@register_resource("outbound_campaign_functions")
@dataclass
class OutboundCampaignFunction(Resource):
    """A node's function code in `functions/<node name>.py`.

    Pull writes it and the node reads it, so an edit shows up as a change to the node. It is
    never sent on its own.
    """

    campaign_folder: str = ""
    stem: str = ""
    code: str = ""

    @staticmethod
    def id_for(campaign_folder: str, stem: str) -> str:
        """Return the status-file id for a node's function file."""
        return f"{campaign_folder}/{stem}"

    @classmethod
    def id_from_path(cls, file_path: str) -> str:
        """Return the status-file id for the function file at `file_path`."""
        stem = os.path.splitext(os.path.basename(file_path))[0]
        return cls.id_for(campaign_folder_of(file_path), stem)

    @property
    def file_path(self) -> str:
        return os.path.join(CAMPAIGNS_DIR, self.campaign_folder, FUNCTIONS_DIR, f"{self.stem}.py")

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
        for node in OutboundCampaignNode.from_projection(projection).values():
            if not node.code:
                continue
            stem = function_file_stem(node.name)
            resource = cls(
                resource_id=cls.id_for(node.campaign_folder, stem),
                name=stem,
                campaign_folder=node.campaign_folder,
                stem=stem,
                code=node.code,
            )
            functions[resource.resource_id] = resource
        return functions

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaignFunction":
        stem = os.path.splitext(os.path.basename(file_path))[0]
        return cls(
            resource_id=resource_id,
            name=stem,
            campaign_folder=campaign_folder_of(file_path),
            stem=stem,
            code=cls.read_to_raw(file_path),
        )

    @staticmethod
    def discover_resources(base_path: str) -> list[str]:
        discovered = []
        for folder in _campaign_folders_on_disk(base_path):
            functions_path = os.path.join(base_path, CAMPAIGNS_DIR, folder, FUNCTIONS_DIR)
            if os.path.isdir(functions_path):
                discovered.extend(
                    os.path.join(functions_path, file_name)
                    for file_name in sorted(os.listdir(functions_path))
                    if file_name.endswith(".py")
                )
        return discovered

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        has_node = any(
            mapping.resource_type is OutboundCampaignNode
            and campaign_folder_of(mapping.file_path) == self.campaign_folder
            and function_file_stem(mapping.resource_name) == self.stem
            for mapping in resource_mappings or []
        )
        if not has_node:
            raise ValueError(
                f"{FUNCTIONS_DIR}/{self.stem}.py has no node of that name in "
                f"outbound_campaigns/{self.campaign_folder}/{CAMPAIGN_FILE}."
            )

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
