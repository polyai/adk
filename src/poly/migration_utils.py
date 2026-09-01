"""Migration utilities for Agent Development Kit
Tools to help with migrating from older versions of the Agent Development Kit to newer versions.

Copyright PolyAI Limited
"""

import logging
import os
from copy import deepcopy
from enum import Enum

from poly.resources import resource_utils

logger = logging.getLogger(__name__)


class MigrationFlag(Enum):
    """Flags to indicate which migrations have been applied. This can be used to
    track which migrations have been run and prevent running the same migration
    multiple times.
    """

    MIGRATED_LEGACY_TOPIC_FILES = "migrated_legacy_topic_files"
    MIGRATED_FLOW_STEP_RESOURCE_IDS = "migrated_flow_step_resource_ids"
    MIGRATED_FLOW_STEP_SETTINGS = "migrated_flow_step_settings"
    REMOVED_PERSONALITY_AND_ROLE_FILES = "removed_personality_and_role_files"


def load_migration_flags(flags: list[str]) -> set[MigrationFlag]:
    """Load a set of MigrationFlag from a list of strings. This can be used to
    load the set of applied migrations from a file or other source.

    Args:
        flags: A list of strings representing the applied migration flags.
    Returns:
        A set of MigrationFlag values corresponding to the input strings.
    """
    valid_flags = set(flag.value for flag in MigrationFlag)
    return set(MigrationFlag(flag) for flag in flags if flag in valid_flags)


def get_all_migration_flags() -> set[MigrationFlag]:
    """Get a set of all migration flags. This can be used to initialize the set
    of applied migrations when first running the migrations.

    Returns:
        A set of all MigrationFlag values.
    """
    return set(flag for flag in MigrationFlag)


def run_migrations(
    root_path: str,
    applied_migrations: set[MigrationFlag],
    status_dict: dict | None = None,
) -> set[MigrationFlag]:
    """Run necessary migrations based on the current state of the project and
    which migrations have already been applied.

    Args:
        root_path: The root path of the project.
        applied_migrations: A set of MigrationFlag indicating which migrations have already been applied.
        status_dict: The raw status dict. Required for dict-level migrations
            that re-key entries before resources are loaded.

    Returns:
        A new set of MigrationFlag indicating which migrations have been applied after running this function.
    """
    new_flags = deepcopy(applied_migrations)
    if MigrationFlag.MIGRATED_LEGACY_TOPIC_FILES not in applied_migrations:
        migrate_legacy_topic_files(root_path)
        new_flags.add(MigrationFlag.MIGRATED_LEGACY_TOPIC_FILES)

    if (
        MigrationFlag.MIGRATED_FLOW_STEP_RESOURCE_IDS not in applied_migrations
        and status_dict is not None
    ):
        migrate_flow_step_resource_ids(status_dict)
        new_flags.add(MigrationFlag.MIGRATED_FLOW_STEP_RESOURCE_IDS)

    if (
        MigrationFlag.MIGRATED_FLOW_STEP_SETTINGS not in applied_migrations
        and status_dict is not None
    ):
        migrate_flow_step_settings(status_dict)
        new_flags.add(MigrationFlag.MIGRATED_FLOW_STEP_SETTINGS)

    if MigrationFlag.REMOVED_PERSONALITY_AND_ROLE_FILES not in applied_migrations:
        remove_personality_and_role_files(root_path)
        new_flags.add(MigrationFlag.REMOVED_PERSONALITY_AND_ROLE_FILES)

    return new_flags


def remove_personality_and_role_files(root_path: str) -> None:
    """Delete the personality and role files, which are superseded by the persona.

    Agent Studio replaced both settings with a single free-text persona, so the
    files no longer describe anything the agent uses. They are removed rather
    than left in place so a stale copy can't be edited and pushed.
    """
    removed = []
    for file_name in ("personality.yaml", "role.yaml"):
        file_path = os.path.join(root_path, "agent_settings", file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            removed.append(os.path.join("agent_settings", file_name))

    if removed:
        logger.warning(
            f"Removed {', '.join(removed)}: personality and role have been replaced by "
            "agent_settings/persona.txt. Run 'poly pull' to fetch it."
        )


# Sub-config keys set internally by the config classes rather than accepted as __init__ args.
_LEGACY_SETTING_INTERNALS = ("resource_id", "name", "step_id", "flow_id")
# Legacy top-level key on a serialized flow step -> its key within FlowSettings.
_LEGACY_SETTING_KEYS = {"asr_biasing": "asr_biasing", "dtmf_config": "dtmf"}


def migrate_flow_step_settings(status_dict: dict) -> None:
    """Fold legacy top-level asr_biasing/dtmf_config on flow steps into ``settings``.

    Flow step config used to be serialized as separate top-level keys. It now lives in a
    single nested ``settings`` object, so a status dict written by an older version would
    otherwise load with empty settings and report every advanced step as modified.

    The legacy keys are left in place rather than removed: resource loading ignores keys
    that aren't init fields, and the next save drops them anyway.
    """
    for resource_dict in status_dict.get("resources", {}).get("flow_steps", {}).values():
        legacy = {
            settings_key: resource_dict[legacy_key]
            for legacy_key, settings_key in _LEGACY_SETTING_KEYS.items()
            if isinstance(resource_dict.get(legacy_key), dict)
        }
        if not legacy:
            continue

        settings = resource_dict.setdefault("settings", {})
        for settings_key, config in legacy.items():
            # Only carry over sections the newer format doesn't already define.
            if settings_key in settings:
                continue
            settings[settings_key] = {
                key: value for key, value in config.items() if key not in _LEGACY_SETTING_INTERNALS
            }


def migrate_flow_step_resource_ids(status_dict: dict) -> None:
    """Re-key flow step resource IDs from {flow_name}_{step_id} to {flow_id}_{step_id}."""
    resources = status_dict.get("resources", {})
    file_structure_info = status_dict.get("file_structure_info", {})

    for resource_key in ("flow_steps", "function_steps"):
        entries = resources.get(resource_key)
        if not entries:
            continue

        rekeyed = {}
        for old_id, resource_dict in entries.items():
            flow_name = resource_dict.get("flow_name")
            flow_id = resource_dict.get("flow_id")
            if not flow_name or not flow_id:
                rekeyed[old_id] = resource_dict
                continue

            step_id = old_id.removeprefix(f"{flow_name}_")
            if step_id == old_id:
                # Prefix didn't match — may already be migrated or have a different format
                rekeyed[old_id] = resource_dict
                continue

            new_id = f"{flow_id}_{step_id}"
            resource_dict["resource_id"] = new_id
            rekeyed[new_id] = resource_dict

            # Update file_structure_info entries that reference the old resource_id
            for file_info in file_structure_info.values():
                if file_info.get("resource_id") == old_id:
                    file_info["resource_id"] = new_id

        resources[resource_key] = rekeyed


def migrate_legacy_topic_files(root_path: str) -> None:
    """Migrate topic files from legacy format (name as filename) to new format
    (clean filename with name stored inside the YAML).

    This handles the transition where topic files were previously saved as
    ``topics/{name}.yaml`` and are now saved as ``topics/{clean_name}.yaml``
    with a ``name`` key inside the YAML content.

    Migrates both existing (pulled) topics and new local-only topic files.
    """
    topics_dir = os.path.join(root_path, "topics")

    if not os.path.isdir(topics_dir):
        return

    topics = {}
    old_files = []
    old_dirs = set()

    # Walk recursively to catch legacy topics in nested subdirectories
    # (e.g. topics/Billing/Refunds.yaml from a name containing "/")
    for dirpath, _, filenames in os.walk(topics_dir):
        for filename in filenames:
            if not filename.endswith(".yaml"):
                continue

            topic_path = os.path.join(dirpath, filename)
            with open(topic_path, "r", encoding="utf-8") as f:
                content = resource_utils.load_yaml(f.read())

            if not isinstance(content, dict) or "name" in content:
                # Already in new format, skip
                continue

            # Reconstruct the original topic name from the relative path
            # e.g. topics/Billing/Refunds.yaml -> "Billing/Refunds"
            rel_path = os.path.relpath(topic_path, topics_dir)
            # os.path.relpath uses os.sep, but topic names use forward slashes.
            file_name = os.path.splitext(rel_path)[0].replace(os.sep, "/")
            clean_file_name = resource_utils.clean_name(file_name)
            clean_file_path = os.path.join(topics_dir, f"{clean_file_name}.yaml")
            if clean_file_path in topics:
                raise ValueError(
                    "Can't migrate legacy topic files: "
                    "multiple topics with the same file name after cleaning: " + clean_file_name
                )

            new_content = {"name": file_name, **content}

            topics[clean_file_path] = new_content
            old_files.append(topic_path)
            if dirpath != topics_dir:
                old_dirs.add(dirpath)

    # Write new files (always into the top-level topics/ dir)
    for clean_file_path, content in topics.items():
        with open(clean_file_path, "w", encoding="utf-8") as f:
            f.write(resource_utils.dump_yaml(content))

    # Remove old files
    for old_file in old_files:
        # Don't delete if old file is same as new file
        if old_file in topics:
            continue
        os.remove(old_file)

    # Remove empty subdirectories left behind (deepest first)
    for old_dir in sorted(old_dirs, key=lambda d: d.count(os.sep), reverse=True):
        if os.path.isdir(old_dir) and not os.listdir(old_dir):
            os.rmdir(old_dir)
