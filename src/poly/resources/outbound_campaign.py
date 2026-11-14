"""Copyright PolyAI Limited"""

import ast
import datetime
import functools
import keyword
import logging
import os
import re
import uuid
import zoneinfo
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Callable, ClassVar, Optional

import poly.resources.resource_utils as utils
from poly.resources.countries import COUNTRY_CODES
from poly.resources.resource import (
    MultiResourceYamlResource,
    Resource,
    ResourceMapping,
    _parse_multi_resource_path,
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
BRANCH_ID_PREFIX = "b-"

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


@functools.cache
def timezones() -> frozenset[str]:
    """The IANA time zones this system knows, lowercased; empty with no time zone database."""
    return frozenset(zone.lower() for zone in zoneinfo.available_timezones())


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
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return value


def _convert_keys(value: Any, convert: Callable[[str], str]) -> Any:
    if isinstance(value, dict):
        return {
            convert(key) if isinstance(key, str) and key else key: _convert_keys(item, convert)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_convert_keys(item, convert) for item in value]
    return value


def _from_file_key(key: str) -> str:
    return key if any(char.isupper() for char in key) else utils.to_camel_case(key)


def to_file_keys(values: Any) -> Any:
    """Turn Agent Studio's camelCase keys, at every level, into the snake_case of the file."""
    return _convert_keys(values, utils.to_snake_case)


def from_file_keys(values: Any) -> Any:
    """Turn the file's snake_case keys, at every level, back into Agent Studio's camelCase.

    A key already in camelCase is kept as it is.
    """
    return _convert_keys(values, _from_file_key)


def _drop_unset_settings(settings: Any) -> Any:
    if not isinstance(settings, dict):
        return settings
    settings = {
        key: value
        for key, value in settings.items()
        if not (value is None and key in SETTINGS_DEFAULTS and SETTINGS_DEFAULTS[key] is None)
    }
    for key in ("voiceDispatchLimits", "smsDispatchLimits"):
        limits = settings.get(key)
        if isinstance(limits, dict):
            settings[key] = {
                limit: value
                for limit, value in limits.items()
                if not (limit in DISPATCH_LIMIT_KEYS and value is None)
            }
    return settings


def _without_branch_ids(data: dict) -> dict:
    branches = data.get("branches")
    if not isinstance(branches, list):
        return data
    return {
        **data,
        "branches": [
            {key: value for key, value in branch.items() if key != "id"}
            if isinstance(branch, dict)
            else branch
            for branch in branches
        ],
    }


def with_branch_ids(data: dict, known_branches: Any) -> dict:
    """Give each branch the id of the saved branch with its `variable`, or a new id.

    Saved branches are matched in order, each once. A branch with no match gets an id like
    Agent Studio's, `b-<uuid>`.
    """
    branches = data.get("branches")
    if not isinstance(branches, list):
        return data
    unused = [
        branch
        for branch in known_branches or []
        if isinstance(branch, dict) and isinstance(branch.get("id"), str)
    ]
    resolved = []
    for branch in branches:
        if not isinstance(branch, dict):
            resolved.append(branch)
            continue
        branch = {key: value for key, value in branch.items() if key != "id"}
        match = next(
            (known for known in unused if known.get("variable") == branch.get("variable")), None
        )
        if match is not None:
            unused.remove(match)
            branch_id = match["id"]
        else:
            branch_id = f"{BRANCH_ID_PREFIX}{uuid.uuid4()}"
        resolved.append({"id": branch_id, **branch})
    return {**data, "branches": resolved}


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
    settings.update({key: None for key, value in settings.items() if value == ""})
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


def campaign_names(campaigns: list[dict]) -> dict[str, str]:
    """Return each campaign's name by id, unique once cleaned.

    Agent Studio allows two campaigns the same name, but each needs its own folder. The oldest
    keeps its name, and a later one whose name cleans to a name taken becomes `<name> (1)`,
    numbered past any name another campaign already has. A name with nothing left once cleaned
    becomes `Campaign`, numbered the same way.
    """
    order = sorted(
        range(len(campaigns)),
        key=lambda index: (
            not campaigns[index].get("createdAt"),
            campaigns[index].get("createdAt") or "",
            index,
        ),
    )
    bases = []
    for campaign in campaigns:
        name = utils.strip_strings(campaign.get("name") or "")
        bases.append(name if utils.clean_name(name) else "Campaign")
    counts = Counter(utils.clean_name(base) for base in bases)
    taken = {utils.clean_name(base) for base in bases if counts[utils.clean_name(base)] == 1}
    names: dict[str, str] = {}
    for index in order:
        base = bases[index]
        candidate, number = base, 1
        if counts[utils.clean_name(base)] > 1:
            while utils.clean_name(candidate) in taken:
                candidate, number = f"{base} ({number})", number + 1
            taken.add(utils.clean_name(candidate))
        names[campaigns[index]["id"]] = candidate
    return names


def campaign_folders(campaigns: list[dict]) -> dict[str, str]:
    """Return each campaign's folder by id: its cleaned name."""
    return {
        campaign_id: utils.clean_name(name)
        for campaign_id, name in campaign_names(campaigns).items()
    }


def node_names(nodes: list[dict]) -> dict[str, str]:
    """Return each platform node's name by id: its label, or a default for its type.

    Labels are kept as they are when present and unique. A node without one, or whose label
    another node already has, gets that label numbered, or its type's default name when the
    label is only punctuation or symbols.
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
        base = (
            label
            if utils.clean_name(label)
            else DEFAULT_NODE_NAMES.get((node.get("data") or {}).get("type"), "Node")
        )
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


def campaign_nodes(changes: dict, campaign_id: str) -> dict[str, "OutboundCampaignNode"]:
    """Return the nodes of campaign `campaign_id` among `changes`, by name."""
    return {
        node.name: node
        for node in changes.get(OutboundCampaignNode, {}).values()
        if isinstance(node, OutboundCampaignNode) and node.campaign_id == campaign_id
    }


def node_pairing_key(node: "OutboundCampaignNode") -> tuple[Optional[str], Optional[str]]:
    """Return what pairs a node across a campaign rename: its name and type, or the trigger."""
    node_type = node.data.get("type") if isinstance(node.data, dict) else None
    return (None if node_type == "trigger" else node.name, node_type)


def _node_signature(nodes: dict[str, "OutboundCampaignNode"]) -> tuple:
    return tuple(sorted((node_pairing_key(node) for node in nodes.values()), key=repr))


def _source_type_error(source: Optional[str]) -> str:
    return f"The contact source stays '{source}' once the campaign has been published."


def _source_type_errors(
    saved: dict[str, "OutboundCampaignNode"], local: dict[str, "OutboundCampaignNode"]
) -> list[str]:
    saved_trigger = next((node.data for node in saved.values() if node.is_trigger), {})
    local_trigger = next((node.data for node in local.values() if node.is_trigger), {})
    source = saved_trigger.get("sourceType")
    return [] if local_trigger.get("sourceType") == source else [_source_type_error(source)]


def paired_campaigns(new_resources: dict, deleted_resources: dict) -> dict[str, str]:
    """Pair each deleted campaign with the new one its folder was renamed to, by old id.

    A rename reads as a delete and a create. They pair when the new campaign's nodes have
    exactly the names and types of the deleted campaign's, and no other campaign's on either
    side has the same.
    """
    new_signatures = {
        campaign_id: _node_signature(campaign_nodes(new_resources, campaign_id))
        for campaign_id in new_resources.get(OutboundCampaign, {})
    }
    old_signatures = {
        campaign_id: _node_signature(campaign_nodes(deleted_resources, campaign_id))
        for campaign_id in deleted_resources.get(OutboundCampaign, {})
    }
    pairs = {}
    for old_id, signature in old_signatures.items():
        matches = [new_id for new_id, other in new_signatures.items() if other == signature]
        if signature and len(matches) == 1 and list(old_signatures.values()).count(signature) == 1:
            pairs[old_id] = matches[0]
    return pairs


@register_resource("outbound_campaigns")
@dataclass
class OutboundCampaign(MultiResourceYamlResource):
    """An outbound campaign's name, description and settings in `<folder>/campaign.yaml`.

    The same file holds the campaign's nodes under `nodes`, each an `OutboundCampaignNode`;
    this resource reads and writes only its own keys. `platform_label` is set only when pull
    renamed the campaign because another has its name, so the next push sends the new name.
    `status` is kept from the last pull and never written to the file or sent.
    """

    resource_id_prefix = "CMPGN"
    top_level_name = CAMPAIGN_KEY

    description: Optional[str] = None
    settings: dict = field(default_factory=lambda: normalise_settings({}))
    folder_name: str = ""
    platform_label: Optional[str] = field(default=None, repr=False, compare=False)
    status: Optional[str] = field(default=None, repr=False, compare=False)

    node_entries: Any = field(default=None, init=False, repr=False, compare=False)
    unknown_keys: list[str] = field(default_factory=list, init=False, repr=False, compare=False)
    had_trigger: bool = field(default=False, init=False, repr=False, compare=False)
    saved_settings: Optional[dict] = field(default=None, init=False, repr=False, compare=False)

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

    def moved_to(self, other: MultiResourceYamlResource) -> "OutboundCampaign":
        return replace(self, folder_name=other.folder_name)

    @property
    def raw(self) -> str:
        return utils.dump_yaml(to_file_keys(utils.strip_strings(self.to_yaml_dict())))

    def compute_hash(self) -> str:
        campaign = self.to_yaml_dict()
        if self.platform_label is not None:
            campaign["name"] = self.platform_label
        return utils.compute_hash_from_dict(utils.strip_strings(campaign))

    def get_diff(self, other_resource: Resource) -> str:
        """Diff from Agent Studio's name when pull renamed the campaign."""
        if self.platform_label is None or not other_resource:
            return super().get_diff(other_resource)
        saved = utils.dump_yaml(
            to_file_keys(utils.strip_strings({**self.to_yaml_dict(), "name": self.platform_label}))
        )
        return utils.get_diff(saved, other_resource.raw)

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str = "",
        had_trigger: bool = False,
        known_status: Optional[str] = None,
        known_settings: Optional[dict] = None,
        **kwargs,
    ) -> "OutboundCampaign":
        yaml_dict = utils.strip_strings(_plain(yaml_dict or {}))
        campaign = cls(
            resource_id=resource_id,
            name=yaml_dict.get("name") or "",
            description=yaml_dict.get("description"),
            settings=normalise_settings(yaml_dict.get("settings")),
            status=known_status,
        )
        campaign.had_trigger = had_trigger
        campaign.saved_settings = known_settings
        return campaign

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
        """Parse campaigns from a projection, skipping archived ones.

        Returns `{}` if it has none.
        """
        campaigns = _projection_campaigns(projection)
        if campaigns is None:
            logger.debug("No outbound campaigns in projection - they will not be pulled.")
            return {}
        names = campaign_names(campaigns)
        resources = {}
        for campaign in campaigns:
            name = names[campaign["id"]]
            label = utils.strip_strings(campaign.get("name") or "")
            if label != name:
                logger.warning(
                    f"Renamed '{label}' to '{name}': campaign names must be unique. "
                    "The next push sends the new name."
                )
            resources[campaign["id"]] = cls(
                resource_id=campaign["id"],
                name=name,
                description=utils.strip_strings(campaign.get("description")),
                settings=utils.strip_strings(normalise_settings(campaign.get("settings"))),
                folder_name=utils.clean_name(name),
                platform_label=None if label == name else label,
                status=campaign.get("status"),
            )
        return resources

    @classmethod
    def to_pretty_dict(
        cls, d: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Write keys in snake_case, leave unset settings out, and name the default variant.

        The default variant goes under `default_variant`, by name.
        """
        d = dict(d)
        settings = _drop_unset_settings(d.get("settings"))
        if isinstance(settings, dict) and VARIANT_ID_KEY in settings:
            variant_id = settings[VARIANT_ID_KEY]
            if variant_id:
                variant_id = (
                    utils.resource_name_for_id(variant_id, Variant, resource_mappings) or variant_id
                )
            settings = _rename_key(settings, VARIANT_ID_KEY, VARIANT_NAME_KEY, variant_id)
        if "settings" in d:
            d["settings"] = settings
        return to_file_keys(d)

    @classmethod
    def from_pretty_dict(
        cls, yaml_dict: dict, resource_mappings: list[ResourceMapping] = None, **kwargs
    ) -> dict:
        """Read snake_case keys, and turn `default_variant` back into the variant's id."""
        yaml_dict = from_file_keys(
            super().from_pretty_dict(yaml_dict, resource_mappings=resource_mappings, **kwargs)
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
        if expected and folder != expected:
            raise ValueError(
                f"Campaign folder name does not match campaign name '{campaign.name}'. "
                f"{folder} != {expected}"
            )
        campaign.folder_name = folder
        top = cls._top_level(file_path)
        campaign.node_entries = top.get(NODES_KEY)
        campaign.unknown_keys = sorted(set(top) - {*CAMPAIGN_KEYS, NODES_KEY})
        return campaign

    @classmethod
    def discover_resources(cls, base_path: str) -> list[str]:
        discovered = []
        for folder in _campaign_folders_on_disk(base_path):
            path = _campaign_file(base_path, folder)
            try:
                cls._get_top_level_data(path)
            except utils.MergeConflictError:
                raise
            except Exception:
                pass
            discovered.append(os.path.join(path, CAMPAIGN_KEY))
        return discovered

    def validate(self, resource_mappings: list[ResourceMapping] = None, **kwargs) -> None:
        errors = self.validation_errors(resource_mappings)
        if errors:
            raise ValueError("; ".join(errors))

    def validation_errors(self, resource_mappings: list[ResourceMapping] = None) -> list[str]:
        """Return every problem the platform would reject.

        `validate` reports them all at once.
        """
        errors: list[str] = []
        if not isinstance(self.name, str) or not self.name.strip():
            errors.append(
                "Name is required. If the campaign was deleted or archived in Agent Studio, "
                "name it to create it again, or delete its folder."
                if self.node_entries
                else "Name is required."
            )
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
        if self.saved_settings is not None and self.settings != self.saved_settings:
            errors.extend(_unsendable_settings_errors(self.settings))
        errors.extend(_node_entry_errors(self.node_entries))
        if (
            self.had_trigger
            and isinstance(self.node_entries, (list, type(None)))
            and not _has_trigger(self.node_entries)
        ):
            errors.append(
                "The campaign needs its trigger node: rename or replace the trigger rather than "
                "delete it."
            )

        variant_id = self.settings.get(VARIANT_ID_KEY) if isinstance(self.settings, dict) else None
        if variant_id and resource_mappings is not None:
            if utils.resource_name_for_id(variant_id, Variant, resource_mappings) is None:
                errors.append(f"Variant '{variant_id}' not found.")
        return errors

    def is_modified(self, other_hash: str) -> bool:
        """Treat a node list that can't be read as a change, so validation reports it."""
        return super().is_modified(other_hash) or bool(_node_entry_errors(self.node_entries))

    @classmethod
    def validate_creates_and_deletes(
        cls, new_resources: dict, deleted_resources: dict
    ) -> list[str]:
        """Refuse deleting a published campaign, or changing its trigger's source through a rename.

        A folder rename that pairs with a deleted campaign keeps its id; any other delete and
        create go through as they are. A new campaign is refused settings the ADK can't send,
        unless a rename keeps them as they were.
        """
        paired = paired_campaigns(new_resources, deleted_resources)
        renamed_from = {new_id: old_id for old_id, new_id in paired.items()}
        errors = []
        for campaign_id, campaign in new_resources.get(cls, {}).items():
            saved = deleted_resources.get(cls, {}).get(renamed_from.get(campaign_id))
            if saved is None or campaign.settings != saved.settings:
                errors.extend(_unsendable_settings_errors(campaign.settings))
        for campaign_id, campaign in deleted_resources.get(cls, {}).items():
            if campaign_id in paired:
                if campaign.status not in (None, "draft"):
                    errors.extend(
                        _source_type_errors(
                            campaign_nodes(deleted_resources, campaign_id),
                            campaign_nodes(new_resources, paired[campaign_id]),
                        )
                    )
                continue
            if campaign.status not in (None, "draft"):
                errors.append(
                    f"'{campaign.name}' has been published, so it can't be deleted. To retire "
                    "it, run `poly campaign pause` then `poly campaign archive`, and restore its "
                    "folder here. It stops being pulled once it's archived."
                )
        return errors

    def build_create_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")

    def build_update_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")

    def build_delete_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")


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


def _has_trigger(entries: Optional[list]) -> bool:
    return any(
        isinstance(entry, dict) and entry.get("type") == "trigger" for entry in entries or []
    )


def _unsendable_settings_errors(settings: Any) -> list[str]:
    unknown = sorted(set(settings) - set(SETTINGS_DEFAULTS)) if isinstance(settings, dict) else []
    if not unknown:
        return []
    return [
        f"Settings {', '.join(_file_key(key) for key in unknown)} can't be sent from the ADK, and a settings change "
        "replaces them all. Change this campaign's settings in Agent Studio, or update the ADK."
    ]


def _file_key(key: str) -> str:
    if key == VARIANT_ID_KEY:
        key = VARIANT_NAME_KEY
    return utils.to_snake_case(PRETTY_ROUTE_KEYS.get(key, key))


def _settings_errors(settings: Any) -> list[str]:
    if not isinstance(settings, dict):
        return ["Settings must be a mapping."]
    errors = []
    for key in (
        "startDate",
        "endDate",
        "fromNumber",
        "smsFromNumber",
        "defaultVariantId",
        "defaultTimezone",
    ):
        if settings.get(key) is not None and not isinstance(settings[key], str):
            errors.append(f"Setting '{_file_key(key)}' must be text or null.")
    start, end = settings.get("startDate"), settings.get("endDate")
    if isinstance(start, str) and isinstance(end, str) and end < start:
        errors.append("Setting 'end_date' can't be before 'start_date'.")
    country = settings.get("country")
    if country is not None and country not in COUNTRY_CODES:
        errors.append(
            "Setting 'country' must be an ISO 3166-1 alpha-2 country code in capitals, e.g. US."
        )
    timezone = settings.get("defaultTimezone")
    if isinstance(timezone, str) and timezones() and timezone.lower() not in timezones():
        errors.append(f"Setting 'default_timezone' must be an IANA time zone, not '{timezone}'.")
    use_case = settings.get("useCase")
    if use_case is not None and use_case not in USE_CASES:
        errors.append(f"Setting 'use_case' must be one of: {', '.join(USE_CASES)}.")
    if not _is_positive_int_or_none(settings.get("dailyContactLimit")):
        errors.append("Setting 'daily_contact_limit' must be a positive whole number or null.")
    for key in ("voiceDispatchLimits", "smsDispatchLimits"):
        limits = settings.get(key)
        if limits is None:
            continue
        if not isinstance(limits, dict):
            errors.append(f"Setting '{_file_key(key)}' must be a mapping or null.")
            continue
        for limit_key, value in limits.items():
            if limit_key not in DISPATCH_LIMIT_KEYS:
                errors.append(
                    f"Setting '{_file_key(key)}' has an unknown field '{_file_key(limit_key)}'."
                )
            elif not _is_positive_int_or_none(value):
                errors.append(
                    f"Setting '{_file_key(key)}.{_file_key(limit_key)}' must be a positive "
                    "whole number or null."
                )
    window = settings.get("contactWindow")
    if window is not None:
        if not isinstance(window, dict):
            errors.append("Setting 'contact_window' must be a mapping or null.")
        else:
            errors.extend(_contact_window_errors(window))
    return errors


def _contact_window_errors(window: dict) -> list[str]:
    errors = []
    days = window.get("daysOfWeek")
    if not isinstance(days, list) or any(day not in DAYS_OF_WEEK for day in days):
        errors.append(
            f"Setting 'contact_window.days_of_week' must be a list of: {', '.join(DAYS_OF_WEEK)}."
        )
    elif not days:
        errors.append("Setting 'contact_window' needs at least one day.")
    times = [window.get(key) for key in ("startTime", "endTime")]
    for key, value in zip(("startTime", "endTime"), times):
        if not isinstance(value, str) or not TIME_OF_DAY.fullmatch(value):
            errors.append(
                f"Setting 'contact_window.{_file_key(key)}' must be a time of day, as \"HH:mm\"."
            )
    if all(isinstance(value, str) and TIME_OF_DAY.fullmatch(value) for value in times):
        if times[1] <= times[0]:
            errors.append("Setting 'contact_window' must end after it starts, on the same day.")
    unknown = sorted(set(window) - set(CONTACT_WINDOW_KEYS))
    if unknown:
        errors.append(
            "Setting 'contact_window' has unknown fields: "
            f"{', '.join(_file_key(key) for key in unknown)}."
        )
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
        pretty = [_file_key(key) for key in unknown]
        errors.append(f"unknown fields for a {node_type} node: {', '.join(pretty)}.")
    missing = [key for key in NODE_REQUIRED[node_type] if data.get(key) is None]
    if missing:
        pretty = [repr(_file_key(key)) for key in missing]
        errors.append(f"a {node_type} node needs {', '.join(pretty)}.")
    for key, allowed in NODE_ENUMS.get(node_type, {}).items():
        if data.get(key) is not None and data[key] not in allowed:
            errors.append(f"'{_file_key(key)}' must be one of: {', '.join(allowed)}.")
    for key in NODE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{_file_key(key)}' must be text.")
    for key in NODE_NULLABLE_STRING_FIELDS & set(data):
        if data[key] is not None and not isinstance(data[key], str):
            errors.append(f"'{_file_key(key)}' must be a node name or null.")
    if data.get("function") is not None:
        errors.extend(_function_errors(data["function"], function_file))
    if "routes" in data:
        errors.extend(_routes_errors(data["routes"]))

    if node_type == "call":
        attempts = data.get("maxAttempts")
        if attempts is not None and not (_is_int(attempts) and 1 <= attempts <= 5):
            errors.append("'max_attempts' must be a whole number from 1 to 5.")
        backoff = data.get("backoff")
        if backoff is not None and not (_is_int(backoff) and backoff >= 0):
            errors.append("'backoff' must be a whole number, 0 or more.")
        if data.get("voicemailEnabled") is not None and not isinstance(
            data["voicemailEnabled"], bool
        ):
            errors.append("'voicemail_enabled' must be true or false.")
        if data.get("voicemailEnabled"):
            for key in ("voicemailScript", "voicemailWhen"):
                if data.get(key) is None:
                    errors.append(f"'{_file_key(key)}' is required when voicemail_enabled is true.")
    elif node_type == "sms":
        timeout = data.get("replyTimeoutValue")
        if timeout is not None and not (_is_int(timeout) and timeout >= 0):
            errors.append("'reply_timeout_value' must be a whole number, 0 or more.")
    elif node_type == "conditional":
        branches = data.get("branches")
        if branches is not None and (
            not isinstance(branches, list)
            or not all(
                isinstance(branch, dict)
                and all(isinstance(branch.get(key), str) for key in ("variable", "targetNodeId"))
                for branch in branches
            )
        ):
            errors.append("Each branch needs text 'variable' and 'next'.")
        elif branches:
            variables = [branch["variable"] for branch in branches]
            for variable in sorted({value for value in variables if variables.count(value) > 1}):
                errors.append(f"Branch value '{variable}' is used by more than one branch.")
    elif node_type == "wait":
        amount = data.get("amount")
        if amount is not None and not (_is_int(amount) and amount > 0):
            errors.append("'amount' must be a positive whole number.")
    elif node_type == "end":
        if data.get("writebackEnabled") is not None and not isinstance(
            data["writebackEnabled"], bool
        ):
            errors.append("'writeback_enabled' must be true or false.")
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
    kept from the last pull, as a flow step's is. The function code is the
    `OutboundCampaignFunction` in `functions/<node name>.py`, and goes out with the node.
    `platform_label` is set only when pull named the node other than
    Agent Studio's label, so the saved hash differs and the next push sends the name.
    """

    top_level_name = NODES_KEY
    _names_cache: ClassVar[tuple] = (None, 0, {})

    campaign_folder: str = ""
    data: dict = field(default_factory=dict)
    position: Optional[dict] = None
    code: str = ""
    platform_label: Optional[str] = field(default=None, repr=False, compare=False)
    campaign_published: bool = field(default=False, repr=False, compare=False)

    saved_type: Optional[str] = field(default=None, init=False, repr=False, compare=False)
    saved_data: Optional[dict] = field(default=None, init=False, repr=False, compare=False)
    saved_code: Optional[str] = field(default=None, init=False, repr=False, compare=False)
    campaign_has_trigger: bool = field(default=False, init=False, repr=False, compare=False)

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
    def is_trigger(self) -> bool:
        """Whether the node is its campaign's trigger."""
        return isinstance(self.data, dict) and self.data.get("type") == "trigger"

    @property
    def platform_name(self) -> str:
        """The label Agent Studio has for the node: its name, unless pull had to rename it."""
        return self.name if self.platform_label is None else self.platform_label

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

    def moved_to(self, other: MultiResourceYamlResource) -> "OutboundCampaignNode":
        return replace(self, campaign_folder=other.campaign_folder)

    @classmethod
    def _entry_key(cls, entry: Any) -> str:
        """Match no entry that isn't a mapping with a text name, so validation reports it."""
        if not isinstance(entry, dict) or not isinstance(entry.get(cls.resource_key), str):
            return ""
        return super()._entry_key(entry)

    def _file_view(self, name: str) -> str:
        node = _without_branch_ids({**self.to_yaml_dict(), "name": name})
        return utils.dump_yaml(to_file_keys(utils.strip_strings(node)))

    @property
    def raw(self) -> str:
        return self._file_view(self.name)

    def get_diff(self, other_resource: Resource) -> str:
        """Diff from Agent Studio's label when pull named the node differently."""
        if self.platform_label is None or not other_resource:
            return super().get_diff(other_resource)
        return utils.get_diff(self._file_view(self.platform_label), other_resource.raw)

    def compute_hash(self) -> str:
        node = _without_branch_ids(self.to_yaml_dict())
        if self.platform_label is not None:
            node["name"] = self.platform_label
        return utils.compute_hash_from_dict(utils.strip_strings(node))

    @classmethod
    def from_yaml_dict(
        cls,
        yaml_dict: dict,
        resource_id: str,
        name: str = "",
        known_position: Optional[dict] = None,
        known_type: Optional[str] = None,
        known_data: Optional[dict] = None,
        known_code: Optional[str] = None,
        known_published: bool = False,
        **kwargs,
    ) -> "OutboundCampaignNode":
        yaml_dict = utils.strip_strings(_plain(yaml_dict or {}))
        node_name = yaml_dict.pop("name", None) or name
        node = cls(
            resource_id=resource_id,
            name=node_name,
            data=normalise_node_data(
                with_branch_ids(yaml_dict, (known_data or {}).get("branches"))
            ),
            position=known_position,
        )
        node.saved_type = known_type
        node.saved_data = known_data
        node.saved_code = known_code
        node.campaign_published = known_published
        return node

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
                name = names[platform_node["id"]]
                label = platform_node.get("label") or ""
                node = cls(
                    resource_id=f"{campaign['id']}:{platform_node['id']}",
                    name=name,
                    campaign_folder=folders[campaign["id"]],
                    data=utils.strip_strings(normalise_node_data(data, from_platform=True)),
                    position=_normalise_position(platform_node.get("position")),
                    code=(data.get("function") or {}).get("code") or "",
                    platform_label=None if label == name else label,
                    campaign_published=campaign.get("status") not in (None, "draft"),
                )
                nodes[node.resource_id] = node
        return nodes

    @classmethod
    def _names_by_id(
        cls, resource_mappings: Optional[list[ResourceMapping]], path: Optional[str]
    ) -> dict[str, str]:
        folder = campaign_folder_of(path or "")
        if not folder or not resource_mappings:
            return {}
        return dict(cls._names_by_folder(resource_mappings).get(folder, {}))

    @classmethod
    def _names_by_folder(
        cls, resource_mappings: list[ResourceMapping]
    ) -> dict[str, dict[str, str]]:
        """Group the node names in `resource_mappings` by campaign folder, once per list."""
        cached, size, grouped = cls._names_cache
        if cached is resource_mappings and size == len(resource_mappings):
            return grouped
        grouped = {}
        for mapping in resource_mappings:
            if mapping.resource_type is cls:
                grouped.setdefault(campaign_folder_of(mapping.file_path), {})[
                    mapping.resource_id.split(":", 1)[-1]
                ] = mapping.resource_name
        cls._names_cache = (resource_mappings, len(resource_mappings), grouped)
        return grouped

    @classmethod
    def to_pretty_dict(
        cls,
        d: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Name the nodes routes lead to, leave branch ids out, and write keys in snake_case.

        Routes go under `next` and `default_next`.
        """
        names = cls._names_by_id(resource_mappings, file_path)
        d = map_route_targets(_without_branch_ids(d), lambda target: names.get(target, target))
        return to_file_keys(_rename_route_keys(d, PRETTY_ROUTE_KEYS))

    @classmethod
    def from_pretty_dict(
        cls,
        yaml_dict: dict,
        resource_mappings: list[ResourceMapping] = None,
        file_path: str = None,
        **kwargs,
    ) -> dict:
        """Read snake_case keys, and turn the node names in routes back into node ids."""
        yaml_dict = from_file_keys(
            super().from_pretty_dict(yaml_dict, resource_mappings=resource_mappings, **kwargs)
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
        """Read the node's entry, and the code in its function file to send with it."""
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
        top = cls._get_top_level_data(true_file_path)
        entries = top.get(NODES_KEY) if isinstance(top, dict) else None
        node.campaign_has_trigger = _has_trigger(entries if isinstance(entries, list) else None)
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
        if (
            self.saved_type == "trigger"
            and not self.campaign_has_trigger
            and (not isinstance(self.data, dict) or self.data.get("type") != "trigger")
        ):
            errors.append("The trigger can't change type unless another node becomes the trigger.")
        source = self.saved_data.get("sourceType") if self.saved_data else None
        if (
            self.campaign_published
            and self.saved_type == "trigger"
            and self.is_trigger
            and self.data.get("sourceType") != source
        ):
            errors.append(_source_type_error(source))
        if len(self.name) > 256:
            errors.append("The name must be under 256 characters.")
        if resource_mappings is not None and isinstance(self.data, dict) and self._routes_changed():
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
            and self._function_changed()
        ):
            error = def_line_error(function["name"], self.code, parameters)
            if error:
                errors.append(f"{self.function_file}: {error}.")
        if errors:
            raise ValueError("; ".join(errors))

    def _is_replaced(self) -> bool:
        return self.saved_data is None or self.saved_data.get("type") != self.data.get("type")

    def _routes_changed(self) -> bool:
        return self._is_replaced() or route_targets(self.data) != route_targets(self.saved_data)

    def _function_changed(self) -> bool:
        """Agent Studio checks the `def` line on create, and when the code or contract changes."""
        if self._is_replaced() or self.code != self.saved_code:
            return True
        saved_function = self.saved_data.get("function") or {}
        return (self.data.get("function") or {}).get("name") != saved_function.get(
            "name"
        ) or function_parameters(self.data) != function_parameters(self.saved_data)

    def build_create_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")

    def build_update_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")

    def build_delete_proto(self):
        raise NotImplementedError("Outbound campaigns can't be pushed yet.")


@register_resource("outbound_campaign_functions")
@dataclass
class OutboundCampaignFunction(Resource):
    """A node's function code in `functions/<node name>.py`.

    Its id is its node's, so a pull that renames the node or its campaign moves the file like
    any other renamed resource. It has no command of its own: a change goes out with its node.
    """

    campaign_folder: str = ""
    code: str = ""

    @property
    def file_path(self) -> str:
        return os.path.join(
            CAMPAIGNS_DIR,
            self.campaign_folder,
            FUNCTIONS_DIR,
            f"{function_file_stem(self.name)}.py",
        )

    @property
    def raw(self) -> str:
        return self.code

    @property
    def command_type(self) -> str:
        return "outbound_campaign_update_node"

    @staticmethod
    def make_pretty(contents: str, **kwargs) -> str:
        return contents

    @classmethod
    def from_pretty(cls, contents: str, **kwargs) -> str:
        return contents

    @staticmethod
    def format_resource(content: str, file_name: str, **kwargs) -> str:
        return utils.format_code_with_ruff(content, file_name)

    @classmethod
    def from_projection(cls, projection: dict) -> dict[str, "OutboundCampaignFunction"]:
        return {
            node.resource_id: cls(
                resource_id=node.resource_id,
                name=function_file_stem(node.name),
                campaign_folder=node.campaign_folder,
                code=node.code,
            )
            for node in OutboundCampaignNode.from_projection(projection).values()
            if node.code
        }

    @classmethod
    def read_local_resource(
        cls, file_path: str, resource_id: str, resource_name: str, **kwargs
    ) -> "OutboundCampaignFunction":
        return cls(
            resource_id=resource_id,
            name=os.path.splitext(os.path.basename(file_path))[0],
            campaign_folder=campaign_folder_of(file_path),
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
        stem = function_file_stem(self.name)
        if resource_mappings is not None and not any(
            mapping.resource_type is OutboundCampaignNode
            and campaign_folder_of(mapping.file_path) == self.campaign_folder
            and function_file_stem(mapping.resource_name) == stem
            for mapping in resource_mappings
        ):
            raise ValueError(
                f"{FUNCTIONS_DIR}/{stem}.py has no node of that name in "
                f"{CAMPAIGNS_DIR}/{self.campaign_folder}/{CAMPAIGN_FILE}."
            )

    def build_create_proto(self):
        raise NotImplementedError("Campaign function code is pushed with its node.")

    def build_update_proto(self):
        raise NotImplementedError("Campaign function code is pushed with its node.")

    def build_delete_proto(self):
        raise NotImplementedError("Campaign function code is pushed with its node.")
