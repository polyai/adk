"""Migration utilities for Agent Development Kit
Tools to help with migrating from older versions of the Agent Development Kit to newer versions.

Copyright PolyAI Limited
"""

from copy import deepcopy
import os
from poly.resources import resource_utils

from enum import Enum


class MigrationFlag(Enum):
    """Flags to indicate which migrations have been applied. This can be used to
    track which migrations have been run and prevent running the same migration
    multiple times.
    """

    MIGRATED_LEGACY_TOPIC_FILES = "migrated_legacy_topic_files"


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


def run_migrations(root_path: str, applied_migrations: set[MigrationFlag]) -> set[MigrationFlag]:
    """Run necessary migrations based on the current state of the project and
    which migrations have already been applied.

    Args:
        root_path: The root path of the project.
        applied_migrations: A set of MigrationFlag indicating which migrations have already been applied.

    Returns:
        A new set of MigrationFlag indicating which migrations have been applied after running this function.
    """
    new_flags = deepcopy(applied_migrations)
    if MigrationFlag.MIGRATED_LEGACY_TOPIC_FILES not in applied_migrations:
        migrate_legacy_topic_files(root_path)
        new_flags.add(MigrationFlag.MIGRATED_LEGACY_TOPIC_FILES)

    return new_flags


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
