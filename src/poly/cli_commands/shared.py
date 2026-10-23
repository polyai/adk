"""Shared helpers used across CLI command families.

These are generic utilities owned by no single command family. Command modules
import them directly (e.g. ``from poly.cli_commands.shared import load_project``).

Copyright PolyAI Limited
"""

import argparse
import base64
import json
import logging
import os
import sys
from argparse import ArgumentParser
from typing import Any, Optional

import requests

from poly.constants import (
    DATA_CHANNELS,
    DATA_CLIENT_ENVS,
    DATA_LIST_OPS,
    DATA_RATE_LIMIT_PER_MINUTE,
    REGION_NAMES,
)
from poly.handlers.interface import REGIONS
from poly.output.json_output import json_print
from poly.project import PROJECT_CONFIG_FILE, STATUS_FILE, AgentStudioProject

logger = logging.getLogger(__name__)

PACKAGE_NAME = "polyai-adk"
# The optional extra carrying the voice calling (`poly call`) dependencies.
CALL_EXTRA_SPEC = f"{PACKAGE_NAME}[call]"
PYPI_JSON_URL = f"https://pypi.org/pypi/{PACKAGE_NAME}/json"
# Deliberately generous: this only runs when the user explicitly asks for an update,
# so waiting is expected. A check on the CLI's startup path would need to be far
# shorter, since every command would pay it.
PYPI_TIMEOUT_SECONDS = 10


class RegionChoices(list):
    """argparse ``choices`` for every ``--region`` flag.

    Lists the advertised names, so ``--help`` and shell completion show ``us``,
    ``eu``, ``uk`` and ``studio``. Membership also accepts the internal identifiers
    ``region_type`` resolves to, since argparse checks ``choices`` after ``type``.
    """

    def __contains__(self, item: object) -> bool:
        return item in REGIONS or super().__contains__(item)


REGION_CHOICES = RegionChoices(REGION_NAMES)


def region_type(value: str) -> str:
    """argparse ``type=`` for ``--region``: an advertised name to its internal identifier.

    Case-insensitive. The older spellings ``us-1``, ``euw-1`` and ``uk-1`` and the
    internal ``staging``/``dev`` are still accepted for backwards compatibility but
    are not advertised. Anything else raises ``ArgumentTypeError`` so argparse
    rejects it with a message that lists the advertised names.
    """
    name = value.lower()
    region = REGION_NAMES.get(name, name)
    if region not in REGIONS:
        raise argparse.ArgumentTypeError(
            f"'{value}' is not a region. Use one of: {', '.join(REGION_NAMES)}."
        )
    return region


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
    flag_name: str = "--from-projection",
) -> Optional[dict[str, Any]]:
    """Parse a projection-carrying CLI value into a projection dict, or exit on failure.

    If the value is ``-`` (after stripping), JSON is read from stdin until EOF.

    Args:
        from_projection (Optional[str]): The raw CLI value; None/empty returns None.
        json_errors (bool): Emit failures as JSON instead of console errors.
        flag_name (str): The flag the value came from, used in error messages.
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
        msg = f"Invalid JSON in {flag_name}: {e}"
        if json_errors:
            json_print({"success": False, "error": msg})
        else:
            error(msg)
        sys.exit(1)
    if not isinstance(parsed, dict):
        msg = f"{flag_name} must be a JSON object (dictionary)."
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


def resolve_branch_id(branches: dict[str, dict], branch_name: str) -> str | None:
    """Resolve a branch name to its ID.

    Args:
        branches: Mapping of branch name to metadata, as returned by
            ``AgentStudioProject.get_branches``.
        branch_name: Name of the branch.

    Returns:
        The branch ID, or None if the branch doesn't exist.
    """
    return branches.get(branch_name, {}).get("branchId")


def branch_id_map(branches: dict[str, dict]) -> dict[str, dict]:
    """Invert a name → metadata branch mapping into branch ID → metadata plus ``name``."""
    return {
        meta["branchId"]: {"name": name, **meta}
        for name, meta in branches.items()
        if meta.get("branchId")
    }


def fetch_branch_id_map(project: AgentStudioProject) -> dict[str, dict]:
    """Build a branch ID → branch dict map for decorating output with branch names.

    Failures are swallowed since a missing label falls back to the raw ID. Resolving
    a user-supplied name to an ID is a functional need, so fetch branches directly
    for that and let failures surface.
    """
    try:
        _, branches = project.get_branches()
        return branch_id_map(branches)
    except Exception as e:
        logger.debug("Failed to fetch branches for display: %s", e)
        return {}


def require_experiments_enabled(project: AgentStudioProject, output_json: bool = False) -> None:
    """Check if the project is eligible to use experiments and exit if not.

    Experiments require both the simplified deployment model and a
    ``deployment_mode`` that supports top-level branches (see
    ``AgentStudioProject.experiments_enabled``).

    Args:
        project: The loaded project.
        output_json: If True, output JSON and exit on failure.
    """
    from poly.output.console import error

    if not project.experiments_enabled:
        msg = (
            "Command is only available for projects using simplified deployments"
            " with top-level branches."
        )
        if output_json:
            json_print({"success": False, "error": msg})
        else:
            error(msg)
        sys.exit(1)


def get_package_version() -> str:
    """Get the version of the polyai-adk package installed in the current environment.

    Returns:
        The version string of the package.
    """
    from importlib.metadata import version

    try:
        _version = version(PACKAGE_NAME)
    except Exception:
        _version = "unknown"
    return _version


def get_latest_version(timeout: float = PYPI_TIMEOUT_SECONDS) -> str:
    """Get the latest version of the polyai-adk package from PyPI.

    Args:
        timeout: Seconds to wait for PyPI. Callers on the CLI's startup path should
            pass something far shorter than the default, which every command pays.

    Returns:
        The latest version string of the package, or "unknown" if PyPI is unreachable.
    """
    import requests

    try:
        response = requests.get(PYPI_JSON_URL, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except Exception:
        return "unknown"


def get_available_versions() -> list[str]:
    """Get every released version of polyai-adk from PyPI, oldest first.

    Returns:
        The released versions, or an empty list if PyPI is unreachable. Versions
        PyPI reports but ``packaging`` cannot parse are skipped rather than
        failing the whole lookup.
    """
    import requests
    from packaging.version import InvalidVersion, Version

    try:
        response = requests.get(PYPI_JSON_URL, timeout=PYPI_TIMEOUT_SECONDS)
        response.raise_for_status()
        releases = response.json().get("releases", {})
    except Exception:
        return []

    parsed: list[tuple[Version, str]] = []
    for release in releases:
        try:
            parsed.append((Version(release), release))
        except InvalidVersion:
            continue
    return [release for _, release in sorted(parsed)]


def is_newer_version(candidate: str, current: str) -> bool:
    """Check whether ``candidate`` is a strictly newer release than ``current``.

    Args:
        candidate: The version to compare, e.g. one from ``get_latest_version``.
        current: The currently installed version.

    Returns:
        True if candidate is newer. Unparseable versions (including "unknown")
        compare as not newer, so a local dev build does not report an update
        available on every run.
    """
    from packaging.version import InvalidVersion, Version

    try:
        return Version(candidate) > Version(current)
    except InvalidVersion:
        return False


def coerce_filter_value(raw: str) -> Any:
    """Turn a command-line token into the JSON type the Data API expects."""
    lowered = raw.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        return raw


def filter_flags_to_filters(flags: Optional[list[list[str]]]) -> list[dict]:
    """Map repeated ``--filter METRIC OP VALUE`` triples onto Data API filter dicts.

    ``in`` and ``ex`` take a comma-separated list; the others take one value.
    The project validates the operator.
    """
    filters = []
    for metric, op, value in flags or []:
        op = op.lower()
        if op in DATA_LIST_OPS:
            coerced: Any = [coerce_filter_value(v.strip()) for v in value.split(",") if v.strip()]
        else:
            coerced = coerce_filter_value(value)
        filters.append({"metric": metric, "op": op, "value": coerced})
    return filters


def having_flags_to_having(flags: Optional[list[list[str]]]) -> list[dict]:
    """Map repeated ``--having AGG OP VALUE`` triples onto Data API threshold dicts."""
    return [{"field": field, "op": op, "value": value} for field, op, value in flags or []]


def sort_flag_to_sort(value: Optional[str]) -> Optional[dict]:
    """Map ``FIELD`` or ``FIELD:asc|desc`` onto a Data API sort dict."""
    if not value:
        return None
    field, _, order = value.partition(":")
    return {"field": field, "order": order or "asc"}


def add_window_arguments(parser: ArgumentParser, default_help: str) -> None:
    """Add ``--from``/``--to`` to a Data API read command."""
    parser.add_argument(
        "--from",
        dest="from_dt",
        type=str,
        default=None,
        metavar="DATE",
        help=f"Inclusive start, YYYY-MM-DD or ISO datetime. {default_help}",
    )
    parser.add_argument(
        "--to",
        dest="to_dt",
        type=str,
        default=None,
        metavar="DATE",
        help="Exclusive end, YYYY-MM-DD (whole day included) or ISO datetime.",
    )


def add_cohort_arguments(parser: ArgumentParser, *, deployments: bool = True) -> None:
    """Add the channel/environment/deployment/variant restrictors."""
    parser.add_argument(
        "--channel",
        action="append",
        choices=DATA_CHANNELS,
        default=None,
        help="Restrict to a channel. Repeatable.",
    )
    parser.add_argument(
        "--env",
        action="append",
        choices=DATA_CLIENT_ENVS,
        default=None,
        help="Restrict to an environment (pre-release is Staging). Repeatable.",
    )
    if deployments:
        parser.add_argument(
            "--deployment",
            action="append",
            default=None,
            metavar="ID",
            help="Restrict to a deployment ID. Repeatable.",
        )
        parser.add_argument(
            "--variant",
            action="append",
            default=None,
            metavar="ID",
            help="Restrict to a variant ID. Repeatable.",
        )


def describe_data_api_error(e: requests.HTTPError) -> str:
    """Explain a Data API HTTP error in the caller's terms."""
    response = e.response
    status = response.status_code if response is not None else None
    detail = ""
    if response is not None:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("message") or ""
        elif payload is not None:
            detail = payload
        else:
            detail = response.text.strip()[:200]
        if isinstance(detail, list):
            detail = "; ".join(
                str(d.get("msg", d)) if isinstance(d, dict) else str(d) for d in detail
            )
        elif not isinstance(detail, str):
            detail = json.dumps(detail)
    if status == 400:
        return f"The Data API rejected the request: {detail or 'validation error'}."
    if status == 401:
        return "The API key for this region is missing or invalid. Run `poly apikey`."
    if status == 403:
        return "Your API key does not have permission for this project or account."
    if status == 404:
        return detail or "Not found, or the key cannot access this account."
    if status == 422:
        return f"Unsupported filter: {detail or 'see --help for valid operators'}."
    if status == 429:
        return (
            f"Rate limited: the Data API allows {DATA_RATE_LIMIT_PER_MINUTE} requests "
            "per minute per key. Wait a minute and retry."
        )
    return f"Request failed ({status}): {detail or str(e)}"
