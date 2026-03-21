"""Projection diff logic for poly diff --proto.

Applies serialized push commands to a remote projection to compute
a before/after diff of the projection state.

Copyright PolyAI Limited
"""

import copy
import logging
from dataclasses import dataclass
from typing import Any, Optional

from poly.output import commands_to_dicts
from poly.resources.resource_utils import to_camel_case

logger = logging.getLogger(__name__)


def snake_to_camel_keys(d: Any) -> Any:
    """Recursively convert dict keys from snake_case to camelCase.

    Args:
        d: A dict, list, or scalar value.

    Returns:
        The same structure with all dict keys converted to camelCase.
    """
    if isinstance(d, dict):
        return {to_camel_case(k): snake_to_camel_keys(v) for k, v in d.items()}
    if isinstance(d, list):
        return [snake_to_camel_keys(item) for item in d]
    return d


def deep_merge(base: dict, override: dict) -> None:
    """Deep merge override into base dict, mutating base in-place.

    Args:
        base: The base dict to merge into.
        override: The dict whose values take precedence.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


# ---------------------------------------------------------------------------
# Command type → projection path registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommandSpec:
    """Describes how a command type maps to the projection."""

    path: list[str]
    """Projection path segments. Use ``{id}`` for entity ID and ``{flow_id}`` for flow ID."""

    operation: str
    """One of 'create', 'update', 'delete'."""

    payload_key: str
    """Key in the serialized command dict that holds the payload."""

    id_field: str = "id"
    """Field name within the payload that holds the entity ID."""

    flow_id_field: Optional[str] = None
    """Field name within the payload that holds the flow ID (for nested flow resources)."""


def _register_entity_resource(
    registry: dict[str, CommandSpec],
    create_cmd: str,
    update_cmd: str,
    delete_cmd: str,
    path: list[str],
    id_field: str = "id",
    flow_id_field: Optional[str] = None,
) -> None:
    """Register create/update/delete specs for an entity-based resource."""
    for cmd, op in [(create_cmd, "create"), (update_cmd, "update"), (delete_cmd, "delete")]:
        registry[cmd] = CommandSpec(
            path=path,
            operation=op,
            payload_key=cmd,
            id_field=id_field,
            flow_id_field=flow_id_field,
        )


def _register_singleton(
    registry: dict[str, CommandSpec],
    cmd: str,
    path: list[str],
) -> None:
    """Register an update-only singleton resource."""
    registry[cmd] = CommandSpec(
        path=path,
        operation="update",
        payload_key=cmd,
    )


def _build_registry() -> dict[str, CommandSpec]:
    """Build the complete command type → projection path registry."""
    r: dict[str, CommandSpec] = {}

    # Topics
    _register_entity_resource(
        r,
        "create_topic",
        "update_topic",
        "delete_topic",
        ["knowledgeBase", "topics", "entities", "{id}"],
    )

    # Entities
    _register_entity_resource(
        r,
        "entity_create",
        "entity_update",
        "entity_delete",
        ["entities", "entities", "entities", "{id}"],
    )

    # Variables
    _register_entity_resource(
        r,
        "variable_create",
        "variable_update",
        "variable_delete",
        ["variables", "variables", "entities", "{id}"],
    )

    # Functions (global)
    _register_entity_resource(
        r,
        "create_function",
        "update_function",
        "delete_function",
        ["functions", "functions", "entities", "{id}"],
    )

    # Flows
    _register_entity_resource(
        r,
        "create_flow",
        "update_flow",
        "delete_flow",
        ["flows", "flows", "entities", "{id}"],
        id_field="id",
    )
    # update_flow and delete_flow use flow_id instead of id
    r["update_flow"] = CommandSpec(
        path=["flows", "flows", "entities", "{id}"],
        operation="update",
        payload_key="update_flow",
        id_field="flow_id",
    )
    r["delete_flow"] = CommandSpec(
        path=["flows", "flows", "entities", "{id}"],
        operation="delete",
        payload_key="delete_flow",
        id_field="flow_id",
    )

    # Flow steps (nested under flow)
    _flow_step_path = ["flows", "flows", "entities", "{flow_id}", "steps", "entities", "{id}"]
    _register_entity_resource(
        r,
        "create_flow_step",
        "update_flow_step",
        "delete_flow_step",
        _flow_step_path,
        flow_id_field="flow_id",
    )

    # Function steps (create_step / update_step / delete_step)
    _register_entity_resource(
        r,
        "create_step",
        "update_step",
        "delete_step",
        _flow_step_path,
        id_field="step_id",
        flow_id_field="flow_id",
    )

    # SMS Templates
    _register_entity_resource(
        r,
        "sms_create_template",
        "sms_update_template",
        "sms_delete_template",
        ["sms", "templates", "entities", "{id}"],
    )

    # Handoffs
    _register_entity_resource(
        r,
        "handoff_create",
        "handoff_update",
        "handoff_delete",
        ["handoff", "handoffs", "entities", "{id}"],
    )

    # Handoff set default (separate command)
    r["handoff_set_default"] = CommandSpec(
        path=["handoff", "handoffs", "entities", "{id}"],
        operation="update",
        payload_key="handoff_set_default",
    )

    # Phrase filters (stop keywords)
    _register_entity_resource(
        r,
        "stop_keywords_create",
        "stop_keywords_update",
        "stop_keywords_delete",
        ["stopKeywords", "filters", "entities", "{id}"],
    )

    # Pronunciations
    _register_entity_resource(
        r,
        "pronunciations_create_pronunciation",
        "pronunciations_update_pronunciation",
        "pronunciations_delete_pronunciation",
        ["pronunciations", "pronunciations", "entities", "{id}"],
    )

    # Keyphrase boosting
    _register_entity_resource(
        r,
        "create_keyphrase_boosting",
        "update_keyphrase_boosting",
        "delete_keyphrase_boosting",
        ["keyphraseBoosting", "keyphraseBoosting", "entities", "{id}"],
    )

    # Transcript corrections
    _register_entity_resource(
        r,
        "create_transcript_corrections",
        "update_transcript_corrections",
        "delete_transcript_corrections",
        ["transcriptCorrections", "transcriptCorrections", "entities", "{id}"],
    )

    # Variants
    _register_entity_resource(
        r,
        "variant_create_variant",
        "variant_set_default_variant",
        "variant_delete_variant",
        ["variantManagement", "variants", "entities", "{id}"],
    )

    # Variant attributes
    _register_entity_resource(
        r,
        "variant_create_attribute",
        "variant_update_attribute",
        "variant_delete_attribute",
        ["variantManagement", "attributes", "entities", "{id}"],
    )

    # --- Singletons (update only) ---

    _register_singleton(r, "update_personality", ["agentSettings", "personality"])
    _register_singleton(r, "update_role", ["agentSettings", "role"])
    _register_singleton(r, "update_rules", ["agentSettings", "rules"])
    _register_singleton(r, "voice_channel_update_disclaimer", ["channels", "voice", "disclaimer"])
    _register_singleton(r, "experimental_config_update_config", ["experimentalConfig"])
    _register_singleton(
        r, "voice_channel_update_asr_settings", ["channels", "voice", "asrSettings"]
    )

    # Channel-routed commands are handled specially in apply_command
    r["channel_update_greeting"] = CommandSpec(
        path=[],  # resolved dynamically
        operation="update",
        payload_key="channel_update_greeting",
    )
    r["channel_update_style_prompt"] = CommandSpec(
        path=[],  # resolved dynamically
        operation="update",
        payload_key="channel_update_style_prompt",
    )

    return r


COMMAND_TYPE_REGISTRY: dict[str, CommandSpec] = _build_registry()

# Channel type values from the protobuf enum
_CHANNEL_TYPE_VOICE = 1
_CHANNEL_TYPE_WEB_CHAT = 2


def _resolve_channel_path(command_dict: dict, spec: CommandSpec) -> list[str]:
    """Resolve the projection path for channel-routed commands.

    Args:
        command_dict: The serialized command dict.
        spec: The command spec.

    Returns:
        The resolved projection path segments.
    """
    payload = command_dict.get(spec.payload_key, {})
    channel_type = payload.get("channel_type", _CHANNEL_TYPE_VOICE)

    if channel_type == _CHANNEL_TYPE_WEB_CHAT:
        channel = "webChat"
    else:
        channel = "voice"

    if spec.payload_key == "channel_update_greeting":
        return ["channels", channel, "config", "greeting"]
    else:
        return ["channels", channel, "config", "stylePrompt"]


def _resolve_path(spec: CommandSpec, payload: dict) -> list[str]:
    """Resolve placeholder segments in a path template.

    Args:
        spec: The command spec with path template.
        payload: The command payload dict (snake_case keys).

    Returns:
        Fully resolved path segments.
    """
    resolved = []
    for segment in spec.path:
        if segment == "{id}":
            resolved.append(payload.get(spec.id_field, ""))
        elif segment == "{flow_id}" and spec.flow_id_field:
            resolved.append(payload.get(spec.flow_id_field, ""))
        else:
            resolved.append(segment)
    return resolved


def apply_command(projection: dict, command_dict: dict) -> None:
    """Apply a single serialized command to the projection in-place.

    Args:
        projection: The projection dict to mutate.
        command_dict: A serialized command dict from ``commands_to_dicts``.
    """
    cmd_type = command_dict.get("type", "")
    spec = COMMAND_TYPE_REGISTRY.get(cmd_type)
    if spec is None:
        logger.warning(f"Unknown command type '{cmd_type}', skipping in projection diff")
        return

    payload = command_dict.get(spec.payload_key, {})

    # Determine the projection path
    if cmd_type in ("channel_update_greeting", "channel_update_style_prompt"):
        path = _resolve_channel_path(command_dict, spec)
    else:
        path = _resolve_path(spec, payload)

    if not path:
        return

    payload_camel = snake_to_camel_keys(payload)

    # Navigate to the parent, creating intermediate dicts as needed
    parent = projection
    for key in path[:-1]:
        if key not in parent or not isinstance(parent[key], dict):
            parent[key] = {}
        parent = parent[key]

    final_key = path[-1]

    if spec.operation == "delete":
        parent.pop(final_key, None)
    elif spec.operation == "create":
        parent[final_key] = payload_camel
    elif spec.operation == "update":
        existing = parent.get(final_key)
        if isinstance(existing, dict):
            deep_merge(existing, payload_camel)
        else:
            parent[final_key] = payload_camel


def apply_commands(projection: dict, command_dicts: list[dict]) -> dict:
    """Apply a list of serialized commands to a deep copy of the projection.

    Args:
        projection: The original projection dict.
        command_dicts: Serialized command dicts from ``commands_to_dicts``.

    Returns:
        A new projection dict with all commands applied.
    """
    result = copy.deepcopy(projection)
    for cmd_dict in command_dicts:
        apply_command(result, cmd_dict)
    return result


def diff_projections(before: Any, after: Any) -> Any:
    """Recursively diff two projection values, returning only changed paths.

    For dicts, recurse into shared keys and report added/deleted keys.
    For leaf values, return ``{"before": old, "after": new}``.
    Returns an empty dict if there are no changes.

    Args:
        before: The original value.
        after: The modified value.

    Returns:
        A nested dict of changes, or an empty dict if identical.
    """
    if before == after:
        return {}

    if isinstance(before, dict) and isinstance(after, dict):
        diff: dict = {}
        all_keys = set(before.keys()) | set(after.keys())

        for key in sorted(all_keys):
            old_val = before.get(key)
            new_val = after.get(key)

            if old_val == new_val:
                continue

            if isinstance(old_val, dict) and isinstance(new_val, dict):
                nested = diff_projections(old_val, new_val)
                if nested:
                    diff[key] = nested
            else:
                diff[key] = {"before": old_val, "after": new_val}

        return diff

    # Non-dict leaf change
    return {"before": before, "after": after}


def generate_projection_diff(project: Any) -> dict:
    """Generate a projection-level diff showing what a push would change.

    Fetches the remote projection, generates push commands, applies them
    to a copy of the projection, and diffs the two states.

    Args:
        project: An ``AgentStudioProject`` instance.

    Returns:
        A dict with ``commands`` (serialized command list) and ``diff``
        (structured before/after projection diff).
    """
    before = project.fetch_projection()

    commands = project.generate_push_commands(skip_validation=True)
    command_dicts = commands_to_dicts(commands)

    after = apply_commands(before, command_dicts)

    projection_diff = diff_projections(before, after)

    return {
        "commands": command_dicts,
        "diff": projection_diff,
    }
