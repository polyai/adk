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


def resolve_project_scope(
    base_path: str,
    region: Optional[str],
    project_id: Optional[str],
    branch_id: Optional[str],
    output_json: bool = False,
) -> tuple[str, str, str]:
    """Resolve region/project_id/branch_id from explicit flags or the local project.

    Lets headless callers (CI, scripts) skip the local project checkout
    entirely by passing all three explicitly, instead of requiring
    ``load_project`` to read one from disk.

    Args:
        base_path: Base path for the local project, used as a fallback.
        region: Explicit region, if given.
        project_id: Explicit project ID, if given.
        branch_id: Explicit branch ID, if given.
        output_json: If True, print JSON and exit on error instead of a message.

    Returns:
        The resolved (region, project_id, branch_id).
    """
    from poly.output.console import error

    explicit = (region, project_id, branch_id)
    if all(value is not None for value in explicit):
        return region, project_id, branch_id

    if any(value is not None for value in explicit):
        message = (
            "--region, --project_id and --branch_id must all be given together, "
            "or all omitted to use the local project."
        )
        if output_json:
            json_print({"success": False, "error": message})
            sys.exit(1)
        error(message)
        sys.exit(1)

    project = load_project(base_path, output_json=output_json)
    return project.region, project.project_id, project.branch_id


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


def resolve_account_name(project: AgentStudioProject) -> None:
    """Resolve and cache the account name if not already set."""
    if project.account_name:
        return
    try:
        from poly.handlers.interface import AgentStudioInterface

        api_handler = AgentStudioInterface()
        accounts = api_handler.get_accounts(project.region)
        project.account_name = accounts.get(project.account_id)
        if project.account_name:
            project.save_config()
    except Exception:
        pass


def print_project_file_changes(
    project: AgentStudioProject,
    output_json: bool = False,
    extra_json: Optional[dict[str, Any]] = None,
    extra_status_kwargs: Optional[dict[str, Any]] = None,
) -> None:
    """Print project status panel and local file changes.

    Used by ``poly status``.

    Args:
        project: The loaded project.
        output_json: If True, output JSON and return.
        extra_json: Additional keys to merge into the JSON output.
        extra_status_kwargs: Additional kwargs passed to ``print_status()``
            (e.g. ``parent_branch``, ``created_by``, ``is_diverged``).
    """
    from poly.output.console import plain, print_file_list, print_status

    resolve_account_name(project)

    files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()

    if output_json:
        json_output = {
            "account_name": project.account_name,
            "project_name": project.project_name,
            "files_with_conflicts": files_with_conflicts,
            "modified_files": modified_files,
            "new_files": new_files,
            "deleted_files": deleted_files,
        }
        if extra_json:
            json_output.update(extra_json)
        json_print(json_output)
        return

    branch_info = project.get_current_branch()

    print_status(
        region=project.region,
        account_id=project.account_id,
        project_id=project.project_id,
        last_updated=project.last_updated.isoformat(),
        branch=branch_info,
        account_name=project.account_name,
        project_name=project.project_name,
        **(extra_status_kwargs or {}),
    )

    print_file_list("Files with merge conflicts", files_with_conflicts, "filename.conflict")
    print_file_list("New files", new_files, "filename.new")
    print_file_list("Deleted files", deleted_files, "filename.deleted")
    print_file_list("Modified files", modified_files, "filename.modified")

    if not modified_files and not new_files and not deleted_files and not files_with_conflicts:
        plain("\n[muted]No changes detected.[/muted]")


def require_deployment_simplification(
    project: AgentStudioProject, output_json: bool = False
) -> None:
    """Check if the project is using deployment simplification and exit if not.

    Args:
        project: The loaded project.
        output_json: If True, output JSON and exit on failure.
    """
    from poly.output.console import error

    if not project.using_simplified_deployments:
        if output_json:
            json_print(
                {
                    "success": False,
                    "error": "Command is only available for projects using simplified deployments.",
                }
            )
        else:
            error("Command is only available for projects using simplified deployments.")
        sys.exit(1)
