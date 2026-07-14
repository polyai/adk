"""RTC command family: pull and push Real-Time Configuration.

Copyright PolyAI Limited
"""

import json
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from datetime import datetime, timezone
from typing import Optional

import questionary
import requests

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.project import AgentStudioProject
from poly.output.console import edit_in_editor, error, info, success, warning
from poly.output.json_output import json_print
from poly.resources.resource_utils import contains_merge_conflict

RTC_ENV_TO_DIR = {
    "sandbox": "draft_and_sandbox",
    "pre-release": "pre_release",
    "live": "live",
}
RTC_DIR_TO_ENV = {v: k for k, v in RTC_ENV_TO_DIR.items()}

RTC_METADATA_FILE = ".rtc_metadata.json"
RTC_BASE_SCHEMA_FILE = ".rtc_base_schema.json"
RTC_BASE_DATA_FILE = ".rtc_base_data.json"


def _write_json_file(path: str, data: dict) -> None:
    """Write a dict as pretty-printed JSON with trailing newline."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def _read_json_file(path: str) -> Optional[dict]:
    """Read a JSON file, or None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_rtc_metadata(env_dir: str, last_updated: Optional[str]) -> None:
    """Write RTC metadata after a pull or successful push."""
    metadata = {
        "last_updated": last_updated,
        "pulled_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json_file(os.path.join(env_dir, RTC_METADATA_FILE), metadata)


def _load_rtc_metadata(env_dir: str) -> Optional[dict]:
    """Load RTC metadata from disk, or None if not present."""
    return _read_json_file(os.path.join(env_dir, RTC_METADATA_FILE))


def _save_rtc_base(env_dir: str, schema: dict, variables: dict) -> None:
    """Save base copies of schema and data for 3-way merge on push."""
    _write_json_file(os.path.join(env_dir, RTC_BASE_SCHEMA_FILE), schema)
    _write_json_file(os.path.join(env_dir, RTC_BASE_DATA_FILE), variables)


def _load_rtc_base(env_dir: str) -> tuple[Optional[dict], Optional[dict]]:
    """Load base copies, returning (schema, variables) or (None, None)."""
    schema = _read_json_file(os.path.join(env_dir, RTC_BASE_SCHEMA_FILE))
    variables = _read_json_file(os.path.join(env_dir, RTC_BASE_DATA_FILE))
    return schema, variables


def _to_sorted_json(data: dict) -> str:
    """Serialize a dict to deterministically ordered JSON for merging."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _merge_dicts(base: dict, local: dict, remote: dict) -> tuple[dict, list[str]]:
    """3-way merge at the dict key level.

    Returns:
        (merged_dict, list_of_conflict_keys). If conflict_keys is empty, the
        merge is clean.
    """
    all_keys = set(base) | set(local) | set(remote)
    merged = {}
    conflicts = []

    for key in sorted(all_keys):
        base_val = base.get(key)
        local_val = local.get(key)
        remote_val = remote.get(key)

        if local_val == remote_val:
            merged[key] = local_val
        elif local_val == base_val:
            merged[key] = remote_val
        elif remote_val == base_val:
            merged[key] = local_val
        else:
            conflicts.append(key)
            merged[key] = local_val

    return merged, conflicts


def _merge_rtc_file(
    filename: str,
    base: dict,
    local: dict,
    remote: dict,
    output_json: bool = False,
) -> Optional[dict]:
    """Attempt 3-way merge on a single RTC JSON file.

    Args:
        filename: Display name (e.g. "data.json").
        base: The pulled version.
        local: The user's local version.
        remote: The current remote version.
        output_json: If True, skip interactive resolution.

    Returns:
        Merged dict, or None if the user cancelled.
    """
    if local == remote:
        return local
    if local == base:
        return remote
    if remote == base:
        return local

    merged, conflict_keys = _merge_dicts(base, local, remote)

    if not conflict_keys:
        if not output_json:
            info(f"  {filename}: clean merge")
        return merged

    if output_json:
        return None

    warning(f"  {filename}: {len(conflict_keys)} conflicting field(s): {', '.join(conflict_keys)}")

    return _resolve_rtc_conflict_interactively(
        filename,
        _to_sorted_json(base),
        _to_sorted_json(local),
        _to_sorted_json(remote),
        _to_sorted_json(merged),
    )


def _resolve_rtc_conflict_interactively(
    filename: str,
    base_str: str,
    local_str: str,
    remote_str: str,
    merged_str: str,
) -> Optional[dict]:
    """Interactive conflict resolution for a single RTC file.

    Returns:
        Resolved dict, or None if the user cancelled.
    """
    while True:
        choices = [
            questionary.Choice("Use local version (yours)", value="local"),
            questionary.Choice("Use remote version (theirs)", value="remote"),
            questionary.Choice("Use base version (before both edits)", value="base"),
            questionary.Choice("Edit merged result in $EDITOR", value="edit"),
            questionary.Choice("Cancel push", value="cancel"),
        ]

        answer = questionary.select(
            f"How do you want to resolve {filename}?",
            choices=choices,
        ).ask()

        if answer is None or answer == "cancel":
            info("Push cancelled.")
            return None
        elif answer == "local":
            return json.loads(local_str)
        elif answer == "remote":
            return json.loads(remote_str)
        elif answer == "base":
            return json.loads(base_str)
        elif answer == "edit":
            try:
                edited = edit_in_editor(merged_str, extension=".json", filename=filename)
            except (ValueError, FileNotFoundError, OSError) as e:
                error(f"Editor error: {e}")
                continue

            if contains_merge_conflict(edited):
                warning("Conflict markers still present. Please resolve all conflicts.")
                merged_str = edited
                continue

            try:
                return json.loads(edited)
            except json.JSONDecodeError as e:
                error(f"Invalid JSON: {e}")
                merged_str = edited
                continue


class RTCCommand(BaseCommand):
    """Manage Real-Time Configuration for the project."""

    command = "rtc"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``rtc`` subcommand tree."""
        rtc_parser = subparsers.add_parser(
            "rtc",
            parents=[parents.verbose],
            help="Manage Real-Time Configuration.",
            description=(
                "Manage Real-Time Configuration (RTC) for the project.\n\n"
                "Examples:\n"
                "  poly rtc pull\n"
                "  poly rtc pull --env sandbox\n"
                "  poly rtc push --env sandbox\n"
                "  poly rtc push --env live --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        rtc_subparsers = rtc_parser.add_subparsers(dest="rtc_subcommand", required=True)

        rtc_pull_parser = rtc_subparsers.add_parser(
            "pull",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Pull RTC from Agent Studio and write to local files.",
            description=(
                "Pull Real-Time Configuration from Agent Studio and write to local files.\n\n"
                "Examples:\n"
                "  poly rtc pull\n"
                "  poly rtc pull --env sandbox\n"
                "  poly rtc pull --env all\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        rtc_pull_parser.add_argument(
            "--env",
            type=str,
            default="all",
            choices=["sandbox", "pre-release", "live", "all"],
            help="Environment to pull. Defaults to all.",
        )

        rtc_push_parser = rtc_subparsers.add_parser(
            "push",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Push RTC from local files to Agent Studio.",
            description=(
                "Push Real-Time Configuration from local files to Agent Studio.\n\n"
                "Examples:\n"
                "  poly rtc push --env sandbox\n"
                "  poly rtc push --env live --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        rtc_push_parser.add_argument(
            "--env",
            type=str,
            required=True,
            choices=["sandbox", "pre-release", "live"],
            help="Environment to push to.",
        )
        rtc_push_parser.add_argument(
            "--force",
            action="store_true",
            help="Skip drift protection check and confirmation prompt.",
        )
        rtc_push_parser.add_argument(
            "--no-merge",
            action="store_true",
            help="Disable automatic merge on drift; fail with error instead.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching RTC sub-handler."""
        if args.rtc_subcommand == "pull":
            result = cls.rtc_pull(args.path, args.env, output_json=args.json)
            if args.json:
                json_print(result)
            else:
                if not result["success"]:
                    error(result["error"])
                    sys.exit(1)
                for f in result["files_written"]:
                    success(f"Pulled {f['environment']} — {f['schema_file']}")
                    success(f"Pulled {f['environment']} — {f['data_file']}")
        elif args.rtc_subcommand == "push":
            result = cls.rtc_push(
                args.path,
                args.env,
                force=getattr(args, "force", False),
                output_json=args.json,
                no_merge=getattr(args, "no_merge", False),
            )
            if result is None:
                return
            if args.json:
                json_print(result)
            else:
                if not result["success"]:
                    error(result["error"])
                    sys.exit(1)
                success(f"Pushed RTC to {args.env}")

    @classmethod
    def rtc_pull(
        cls,
        base_path: str,
        env: str = "all",
        output_json: bool = False,
    ) -> dict:
        """Pull RTC from Agent Studio and write to local files.

        Args:
            base_path: Base path for the project.
            env: Environment(s) to pull — sandbox, pre-release, live, or all.
            output_json: If True, format errors as JSON on failure.

        Returns:
            dict: Result with success status and files_written list.
        """
        project = load_project(base_path, output_json=output_json)
        project_root = project.root_path

        if env == "all":
            envs_to_fetch = list(RTC_ENV_TO_DIR.keys())
        else:
            envs_to_fetch = [env]

        rtc_root = os.path.join(project_root, "real_time_configuration")
        results = []

        try:
            for client_env in envs_to_fetch:
                config = AgentStudioInterface.get_rtc_config(
                    region=project.region,
                    project_id=project.project_id,
                    client_env=client_env,
                )

                dir_name = RTC_ENV_TO_DIR[client_env]
                env_dir = os.path.join(rtc_root, dir_name)
                os.makedirs(env_dir, exist_ok=True)

                schema = config.get("schema", {})
                variables = config.get("variables", {})

                _write_json_file(os.path.join(env_dir, "schema.json"), schema)
                _write_json_file(os.path.join(env_dir, "data.json"), variables)
                _save_rtc_base(env_dir, schema, variables)
                _save_rtc_metadata(env_dir, config.get("lastUpdated"))

                results.append(
                    {
                        "environment": client_env,
                        "schema_file": os.path.join(env_dir, "schema.json"),
                        "data_file": os.path.join(env_dir, "data.json"),
                    }
                )

            return {"success": True, "files_written": results}

        except requests.HTTPError as e:
            return {"success": False, "error": str(e), "files_written": results}

    @classmethod
    def rtc_push(
        cls,
        base_path: str,
        env: str,
        force: bool = False,
        output_json: bool = False,
        no_merge: bool = False,
    ) -> Optional[dict]:
        """Push RTC from local files to Agent Studio.

        Args:
            base_path: Base path for the project.
            env: Environment to push to — sandbox, pre-release, or live.
            force: If True, skip drift check and confirmation prompt.
            output_json: If True, format errors as JSON on failure.
            no_merge: If True, disable merge on drift; hard-fail instead.

        Returns:
            dict with success status, or None if the user cancelled interactively.
        """
        project = load_project(base_path, output_json=output_json)
        project_root = project.root_path

        dir_name = RTC_ENV_TO_DIR[env]
        env_dir = os.path.join(project_root, "real_time_configuration", dir_name)

        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not os.path.exists(schema_path):
            return {"success": False, "error": f"schema.json not found at {schema_path}"}

        if not os.path.exists(data_path):
            return {"success": False, "error": f"data.json not found at {data_path}"}

        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
            with open(data_path, "r", encoding="utf-8") as f:
                variables = json.load(f)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in local RTC file: {e}"}

        # Drift protection
        if not force:
            metadata = _load_rtc_metadata(env_dir)
            if metadata is None:
                if not output_json:
                    info(
                        "No RTC metadata found; skipping drift check. "
                        "Run 'poly rtc pull' to enable drift protection."
                    )
            else:
                try:
                    remote_config = AgentStudioInterface.get_rtc_config(
                        region=project.region,
                        project_id=project.project_id,
                        client_env=env,
                    )
                    remote_last_updated = remote_config.get("lastUpdated")
                    local_last_updated = metadata.get("last_updated")

                    if remote_last_updated != local_last_updated:
                        merge_result = cls._handle_drift(
                            env_dir=env_dir,
                            remote_config=remote_config,
                            local_schema=schema,
                            local_variables=variables,
                            output_json=output_json,
                            no_merge=no_merge,
                            env=env,
                            local_last_updated=local_last_updated,
                            remote_last_updated=remote_last_updated,
                        )
                        if merge_result is None:
                            return None
                        if not merge_result["success"]:
                            return merge_result
                        schema = merge_result["schema"]
                        variables = merge_result["variables"]

                except requests.HTTPError as e:
                    return {"success": False, "error": f"Drift check failed: {e}"}

        if env == "live" and not force:
            if output_json:
                return {
                    "success": False,
                    "error": "Refusing to push RTC to live without --force.",
                }
            confirm = questionary.confirm(
                f"Push RTC to {env}? This will update live configuration.",
                auto_enter=False,
                default=False,
            ).ask()
            if not confirm:
                info("Push cancelled.")
                return None

        return cls._do_push(project, env, env_dir, schema, variables, output_json)

    @classmethod
    def _handle_drift(
        cls,
        env_dir: str,
        remote_config: dict,
        local_schema: dict,
        local_variables: dict,
        output_json: bool,
        no_merge: bool,
        env: str,
        local_last_updated: Optional[str],
        remote_last_updated: Optional[str],
    ) -> Optional[dict]:
        """Handle drift between local and remote RTC config.

        Returns:
            dict with "success" and merged "schema"/"variables" on merge success,
            dict with "success": False on error,
            or None if the user cancelled.
        """
        drift_msg = (
            f"Remote RTC config has changed since your last pull "
            f"(local: {local_last_updated}, remote: {remote_last_updated}). "
        )

        if no_merge:
            return {
                "success": False,
                "error": drift_msg + f"Run 'poly rtc pull --env {env}' first, "
                "or use --force to override.",
            }

        base_schema, base_variables = _load_rtc_base(env_dir)
        if base_schema is None or base_variables is None:
            return {
                "success": False,
                "error": drift_msg + "Cannot merge: no base version available. "
                f"Run 'poly rtc pull --env {env}' to enable merge on future pushes, "
                "or use --force to overwrite.",
            }

        remote_schema = remote_config.get("schema", {})
        remote_variables = remote_config.get("variables", {})

        if not output_json:
            info("Remote has changed since your last pull. Attempting merge...")

        merged_schema = _merge_rtc_file(
            "schema.json", base_schema, local_schema, remote_schema, output_json
        )
        if merged_schema is None and not output_json:
            return None
        if merged_schema is None:
            return {"success": False, "error": drift_msg + "Schema conflicts.", "conflicts": True}

        merged_variables = _merge_rtc_file(
            "data.json", base_variables, local_variables, remote_variables, output_json
        )
        if merged_variables is None and not output_json:
            return None
        if merged_variables is None:
            return {"success": False, "error": drift_msg + "Data conflicts.", "conflicts": True}

        if not output_json:
            info("Merge complete.")

        return {"success": True, "schema": merged_schema, "variables": merged_variables}

    @classmethod
    def _do_push(
        cls,
        project: AgentStudioProject,
        env: str,
        env_dir: str,
        schema: dict,
        variables: dict,
        output_json: bool,
    ) -> dict:
        """Execute the actual push to the API and update local state."""
        try:
            AgentStudioInterface.put_rtc_schema(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
                schema=schema,
            )
        except requests.HTTPError as e:
            return {"success": False, "error": str(e), "step": "schema"}

        try:
            push_response = AgentStudioInterface.patch_rtc_variables(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
                variables=variables,
            )
        except requests.HTTPError as e:
            if not output_json:
                error(f"Warning: schema was pushed to {env}, but variables update failed.")
            return {
                "success": False,
                "error": f"Schema pushed but variables failed: {e}",
                "step": "variables",
            }

        new_last_updated = push_response.get("lastUpdated") if push_response else None
        _save_rtc_metadata(env_dir, new_last_updated)
        _save_rtc_base(env_dir, schema, variables)
        _write_json_file(os.path.join(env_dir, "schema.json"), schema)
        _write_json_file(os.path.join(env_dir, "data.json"), variables)

        return {
            "success": True,
            "environment": env,
            "schema_file": os.path.join(env_dir, "schema.json"),
            "data_file": os.path.join(env_dir, "data.json"),
        }
