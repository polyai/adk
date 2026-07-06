"""Shared helpers used across CLI command families.

These are generic utilities owned by no single command family. Command modules
import them directly (e.g. ``from poly.cli_commands.shared import load_project``).

Copyright PolyAI Limited
"""

import base64
import json
import os
import sys
from typing import Any, Optional

from poly.output.json_output import json_print
from poly.project import PROJECT_CONFIG_FILE, STATUS_FILE, AgentStudioProject


def read_project_config(base_path: str) -> AgentStudioProject | None:
    """Read the project configuration from base_path, recursing into parents.

    Args:
        base_path: Path to the project directory.

    Returns:
        The loaded project, or None if no configuration was found.
    """
    # Read from config file if it exists
    config_path = os.path.join(base_path, PROJECT_CONFIG_FILE)
    if os.path.exists(config_path):
        return AgentStudioProject.from_file_path(base_path)

    # If not, read all info from status file
    status_path = os.path.join(base_path, STATUS_FILE)
    if os.path.exists(status_path):
        with open(status_path, "rb") as f:
            encoded_config_data = f.read()

        json_bytes = base64.b64decode(encoded_config_data)
        config_data = json.loads(json_bytes.decode("utf-8"))
        return AgentStudioProject.from_dict(config_data, root_path=base_path)

    parent_path = os.path.dirname(base_path)
    if parent_path == base_path:
        return None
    # Recurse into parent directory
    return read_project_config(parent_path)


def load_project(base_path: str, output_json: bool = False) -> AgentStudioProject:
    """Read project config or exit with a helpful error if not found.

    Args:
        base_path: Path to the project directory.
        output_json: If True, print JSON and exit when config is missing.

    Returns:
        The loaded project.
    """
    from poly.output.console import error

    project = read_project_config(base_path)
    if not project:
        if output_json:
            json_print(
                {
                    "success": False,
                    "error": "No project configuration found. Run poly init to initialize a project, or change your directory to an existing workspace/project.",
                }
            )
            sys.exit(1)
        error(
            "No project configuration found. Run [bold]poly init[/bold] to initialize a project, or change your directory to an existing workspace/project."
        )
        sys.exit(1)
    return project


def compute_diff(
    base_path: str,
    files: list[str] = None,
    before: str = None,
    after: str = None,
    output_json: bool = False,
) -> Optional[dict[str, str]]:
    """Compute diffs between the project and given versions or branches.

    If before and after are not specified, compares local against remote.
    If both are specified, compares the two remote versions.
    If only after is specified, compares against the previous version.
    """
    from poly.output.console import error

    project = load_project(base_path, output_json=output_json)
    files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]
    if not (before or after):
        return project.get_diffs(file_paths=files)

    if not before:
        client_env = "sandbox"
        if after in {"pre-release", "live"}:
            client_env = after
        versions, deployment_hashes = project.get_deployments(client_env=client_env)
        if after in deployment_hashes:
            after = deployment_hashes[after]
        if not versions:
            error("No versions found.")
            return
        version_idx = next(
            (i for i, v in enumerate(versions) if (v.get("version_hash") or "")[:9] == after[:9]),
            None,
        )
        if version_idx is None:
            error(f"Version hash '{after}' not found.")
            return None
        if version_idx == len(versions) - 1:
            error("No previous version found.")
            return None
        previous_version_idx = version_idx + 1
        before = (versions[previous_version_idx].get("version_hash") or "")[:9]

    if not after:
        after = "local"

    return project.diff_remote_named_versions(before_name=before, after_name=after)


def parse_from_projection_json(
    from_projection: Optional[str],
    *,
    json_errors: bool,
) -> Optional[dict[str, Any]]:
    """Parse ``--from-projection`` CLI value into a projection dict, or exit on failure.

    If the value is ``-`` (after stripping), JSON is read from stdin until EOF.
    """
    from poly.output.console import error

    if not from_projection:
        return None
    raw = from_projection.strip()
    if raw == "-":
        raw = sys.stdin.read()
    try:
        parsed: Any = json.loads(raw)
        if isinstance(parsed, dict) and "projection" in parsed:
            parsed = parsed["projection"]
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in --from-projection: {e}"
        if json_errors:
            json_print({"success": False, "error": msg})
        else:
            error(msg)
        sys.exit(1)
    if not isinstance(parsed, dict):
        msg = "--from-projection must be a JSON object (dictionary)."
        if json_errors:
            json_print({"success": False, "error": msg})
        else:
            error(msg)
        sys.exit(1)
    return parsed


def format_gist_choice(g: dict) -> str:
    """Format a gist dict as a human-readable choice label."""
    id_hint = g["id"][:7]
    date = g.get("created_at", "")[:10]
    parts = [p for p in [date, id_hint, g["description"]] if p]
    return "  ".join(parts)
