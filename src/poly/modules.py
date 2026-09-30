"""Shared flows: materializing '_modules/flows/<name>/' into a project's own 'flows/'.

A project loads specific shared flows by name via its project.yaml:

    modules:
      flows:
        - address_collection

Each declared name maps 1:1 onto flows defined in _modules directory.

Copyright PolyAI Limited
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from poly.project import AgentStudioProject

logger = logging.getLogger(__name__)

# Marker file dropped into every materialized flow folder. Its presence is what lets ADK tell
# a shared-flow copy apart from a hand-authored one, without touching FlowConfig/FlowStep.
MODULE_SOURCE_MARKER = ".module_source"


class ModuleSyncError(Exception):
    """Raised when a project's declared shared flows can't be resolved or synced safely."""


def find_repo_root(root_path: str) -> str:
    """Walk upward from root to find the _modules/ directory definition.

    Stops successfully at the first ancestor containing a sibling _modules/ directory.
    Stops (and raises) at the first ancestor containing a .git file.
    """
    current = os.path.abspath(root_path)
    while True:
        if os.path.isdir(os.path.join(current, "_modules")):
            return current
        if os.path.exists(os.path.join(current, ".git")):
            raise ModuleSyncError(
                f"Could not find a _modules/ directory above {root_path!r} "
                f"(stopped at repo root {current!r})."
            )
        parent = os.path.dirname(current)
        if parent == current:
            raise ModuleSyncError(f"Could not find a _modules/ directory above {root_path!r}.")
        current = parent


def resolve_shared_flow_path(repo_root: str, flow_name: str) -> str:
    """Return the absolute path of a shared flow's source directory under '_modules/flows/'."""
    return os.path.join(repo_root, "_modules", "flows", flow_name)


def get_module_owned_flow_names(root_path: str) -> set[str]:
    """Return the shared flows used in project."""
    flows_dir = os.path.join(root_path, "flows")
    owned: set[str] = set()
    if not os.path.isdir(flows_dir):
        return owned
    for entry in os.listdir(flows_dir):
        if os.path.isfile(os.path.join(flows_dir, entry, MODULE_SOURCE_MARKER)):
            owned.add(entry)
    return owned


def sync_project_modules(project: "AgentStudioProject") -> None:
    """Materialize the project's declared shared flows, and clean up ones no longer declared."""
    declared_flow_names = list(dict.fromkeys(project.imported_flow_names))
    flows_dir = os.path.join(project.root_path, "flows")

    repo_root = find_repo_root(project.root_path) if declared_flow_names else None

    for flow_name in declared_flow_names:
        source_dir = resolve_shared_flow_path(repo_root, flow_name)
        if not os.path.isdir(source_dir):
            raise ModuleSyncError(
                f"Project declares shared flow '{flow_name}' under 'modules.flows', but no "
                f"such flow exists at {source_dir!r}."
            )

        target_dir = os.path.join(flows_dir, flow_name)
        marker_path = os.path.join(target_dir, MODULE_SOURCE_MARKER)
        if os.path.isdir(target_dir) and not os.path.isfile(marker_path):
            raise ModuleSyncError(
                f"Cannot import shared flow '{flow_name}': a flow already exists at "
                f"{target_dir!r} without a '{MODULE_SOURCE_MARKER}' marker."
                f"It is likely a custom flow. Rename, remove, or drop the shared flow from "
                "'modules.flows', to resolve the collision."
            )

        if os.path.isdir(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(source_dir, target_dir)
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write(f"_modules/flows/{flow_name}\n")

    # Cleanup: remove any previously-materialized flow that's no longer declared.
    if os.path.isdir(flows_dir):
        for entry in os.listdir(flows_dir):
            if entry in declared_flow_names:
                continue
            if os.path.isfile(os.path.join(flows_dir, entry, MODULE_SOURCE_MARKER)):
                logger.info(f"Removing shared flow '{entry}': no longer declared in modules.flows")
                shutil.rmtree(os.path.join(flows_dir, entry))
