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


def _build_registry() -> dict[str, CommandSpec]:
    """Build the command type → projection path registry from resource classes.

    Iterates all resource classes in ``RESOURCE_NAME_TO_CLASS`` and derives
    CommandSpecs from their ``projection_path``, ``command_type``, and related
    ClassVars. This means adding a new resource type with a ``projection_path``
    automatically registers it — no manual updates needed.
    """
    from poly.project import RESOURCE_NAME_TO_CLASS

    r: dict[str, CommandSpec] = {}

    # Channel-routed command types: multiple resource classes share the same
    # update_command_type but target different projection paths based on channel_type
    # in the payload. We detect these and register them with an empty path so
    # apply_command resolves the path dynamically.
    channel_routed: set[str] = set()
    cmd_to_path: dict[str, list[str]] = {}
    for resource_cls in RESOURCE_NAME_TO_CLASS.values():
        path = resource_cls.projection_path
        if not path:
            continue
        try:
            dummy = object.__new__(resource_cls)
            dummy.resource_id = ""
            update_cmd = dummy.update_command_type
        except Exception:
            continue
        if update_cmd in cmd_to_path and cmd_to_path[update_cmd] != path:
            channel_routed.add(update_cmd)
        cmd_to_path[update_cmd] = path

    for resource_cls in RESOURCE_NAME_TO_CLASS.values():
        path = resource_cls.projection_path
        if not path:
            continue  # Sub-resources without a projection path (e.g. ASRBiasing, DTMFConfig)

        # Read command_type properties via a minimal instance (they're @property, not ClassVar)
        try:
            dummy = object.__new__(resource_cls)
            dummy.resource_id = ""
            create_cmd = dummy.create_command_type
            update_cmd = dummy.update_command_type
            delete_cmd = dummy.delete_command_type
        except (NotImplementedError, AttributeError, TypeError):
            try:
                dummy = object.__new__(resource_cls)
                dummy.resource_id = ""
                update_cmd = dummy.update_command_type
            except Exception:
                continue
            create_cmd = None
            delete_cmd = None

        # Skip duplicate registrations for channel-routed commands (voice/chat share
        # the same command type). They get a single entry with an empty path.
        if update_cmd in channel_routed:
            if update_cmd not in r:
                r[update_cmd] = CommandSpec(
                    path=[],  # resolved dynamically in _resolve_channel_path
                    operation="update",
                    payload_key=update_cmd,
                )
            continue

        id_field = resource_cls.projection_id_field
        update_id_field = resource_cls.projection_update_id_field or id_field
        flow_id_field = resource_cls.projection_parent_id_field

        is_singleton = "{id}" not in path

        if is_singleton:
            r[update_cmd] = CommandSpec(
                path=path,
                operation="update",
                payload_key=update_cmd,
            )
        else:
            if create_cmd and create_cmd not in r:
                r[create_cmd] = CommandSpec(
                    path=path,
                    operation="create",
                    payload_key=create_cmd,
                    id_field=id_field,
                    flow_id_field=flow_id_field,
                )
            if update_cmd not in r:
                r[update_cmd] = CommandSpec(
                    path=path,
                    operation="update",
                    payload_key=update_cmd,
                    id_field=update_id_field,
                    flow_id_field=flow_id_field,
                )
            if delete_cmd and delete_cmd not in r:
                r[delete_cmd] = CommandSpec(
                    path=path,
                    operation="delete",
                    payload_key=delete_cmd,
                    id_field=update_id_field,
                    flow_id_field=flow_id_field,
                )

    # Extra commands not tied to a single resource class
    r["handoff_set_default"] = CommandSpec(
        path=["handoff", "handoffs", "entities", "{id}"],
        operation="update",
        payload_key="handoff_set_default",
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


def resolve_command_path(command_dict: dict) -> Optional[tuple[CommandSpec, list[str]]]:
    """Resolve the projection path for a serialized command.

    Args:
        command_dict: A serialized command dict from ``commands_to_dicts``.

    Returns:
        A tuple of (CommandSpec, resolved path), or None if the command type is unknown.
    """
    cmd_type = command_dict.get("type", "")
    spec = COMMAND_TYPE_REGISTRY.get(cmd_type)
    if spec is None:
        logger.warning(f"Unknown command type '{cmd_type}', skipping in projection diff")
        return None

    payload = command_dict.get(spec.payload_key, {})

    if not spec.path:
        path = _resolve_channel_path(command_dict, spec)
        if not path:
            return None
    else:
        path = _resolve_path(spec, payload)

    return spec, path


def _get_at_path(d: dict, path: list[str]) -> Any:
    """Get a value from a nested dict by path, returning None if any segment is missing."""
    current = d
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def apply_command(projection: dict, command_dict: dict) -> None:
    """Apply a single serialized command to the projection in-place.

    Args:
        projection: The projection dict to mutate.
        command_dict: A serialized command dict from ``commands_to_dicts``.
    """
    resolved = resolve_command_path(command_dict)
    if resolved is None:
        return

    spec, path = resolved
    payload = command_dict.get(spec.payload_key, {})
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


def enrich_commands_with_diffs(projection_before: dict, command_dicts: list[dict]) -> list[dict]:
    """Augment each command dict with a ``diff`` showing what changed.

    Applies the commands to a copy of the projection, then for each command
    looks up the before/after values at its projection path and computes
    a per-field diff.

    Args:
        projection_before: The projection state before the commands are applied.
        command_dicts: Serialized command dicts from ``commands_to_dicts``.

    Returns:
        A new list of command dicts, each with an added ``diff`` key.
    """
    projection_after = apply_commands(projection_before, command_dicts)

    result = []
    for cmd_dict in command_dicts:
        enriched = dict(cmd_dict)
        resolved = resolve_command_path(cmd_dict)

        if resolved is not None:
            _, path = resolved
            before_val = _get_at_path(projection_before, path)
            after_val = _get_at_path(projection_after, path)
            enriched["diff"] = diff_projections(before_val, after_val)
        else:
            enriched["diff"] = {}

        result.append(enriched)

    return result


def generate_projection_diff(project: Any) -> dict:
    """Generate a projection-level diff showing what a push would change.

    Fetches the remote projection, generates push commands, applies them
    to a copy of the projection, and computes a per-command diff. Each
    command in the output includes a ``diff`` key showing what changed
    at that command's projection path.

    Args:
        project: An ``AgentStudioProject`` instance.

    Returns:
        A dict with ``commands`` — each command dict augmented with a
        ``diff`` key showing ``{before, after}`` for changed fields.
    """
    before = project.fetch_projection()

    commands = project.generate_push_commands(skip_validation=True)
    command_dicts = commands_to_dicts(commands)

    return {"commands": enrich_commands_with_diffs(before, command_dicts)}
