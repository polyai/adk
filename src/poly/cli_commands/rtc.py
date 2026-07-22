"""RTC command family: pull and push Real-Time Configuration.

Copyright PolyAI Limited
"""

import json
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

import questionary
import requests

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.output.console import edit_in_editor, error, info, success, warning
from poly.output.json_output import json_print
from poly.project import AgentStudioProject
from poly.resources.resource_utils import contains_merge_conflict
from poly.utils import merge_rtc_dicts, read_json_file, write_json_file

RTC_ENV_TO_DIR = {
    "sandbox": "draft_and_sandbox",
    "pre-release": "pre_release",
    "live": "live",
}
RTC_DIR_TO_ENV = {v: k for k, v in RTC_ENV_TO_DIR.items()}

RTC_BASE_SCHEMA_FILE = ".rtc_base_schema.json"
RTC_BASE_DATA_FILE = ".rtc_base_data.json"


def _save_rtc_base(env_dir: str, schema: dict, variables: dict) -> None:
    """Save base copies of schema and data for 3-way merge on push."""
    write_json_file(os.path.join(env_dir, RTC_BASE_SCHEMA_FILE), schema)
    write_json_file(os.path.join(env_dir, RTC_BASE_DATA_FILE), variables)


def _load_rtc_base(env_dir: str) -> tuple[Optional[dict], Optional[dict]]:
    """Load base copies, returning (schema, variables) or (None, None)."""
    try:
        schema = read_json_file(os.path.join(env_dir, RTC_BASE_SCHEMA_FILE))
        variables = read_json_file(os.path.join(env_dir, RTC_BASE_DATA_FILE))
    except json.JSONDecodeError:
        return None, None
    return schema, variables


def _to_sorted_json(data: dict) -> str:
    """Serialize a dict to deterministically ordered JSON for merging."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _get_rtc_last_updated(project: AgentStudioProject, env: str) -> Optional[str]:
    """Get the stored lastUpdated for an RTC environment from project config."""
    if not project.rtc_metadata:
        return None
    env_meta = project.rtc_metadata.get(env)
    if not env_meta:
        return None
    return env_meta.get("last_updated")


def _set_rtc_last_updated(
    project: AgentStudioProject, env: str, last_updated: Optional[str]
) -> None:
    """Set the lastUpdated for an RTC environment and save project config."""
    if project.rtc_metadata is None:
        project.rtc_metadata = {}
    project.rtc_metadata[env] = {"last_updated": last_updated}
    project.save_config()


def _merge_rtc_file(
    filename: str,
    base: dict,
    local: dict,
    remote: dict,
    output_json: bool = False,
) -> Optional[dict]:
    """Attempt 3-way merge on a single RTC JSON file.

    Returns:
        Merged dict, or None if the user cancelled.
    """
    if local == remote:
        return local
    if local == base:
        return remote
    if remote == base:
        return local

    merged, conflict_keys = merge_rtc_dicts(base, local, remote)

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
                "  poly rtc pull --env sandbox --schema\n"
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
        rtc_pull_mode = rtc_pull_parser.add_mutually_exclusive_group()
        rtc_pull_mode.add_argument(
            "--schema",
            action="store_true",
            help="Pull schema only.",
        )
        rtc_pull_mode.add_argument(
            "--data",
            action="store_true",
            help="Pull data only.",
        )

        rtc_push_parser = rtc_subparsers.add_parser(
            "push",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Push RTC from local files to Agent Studio.",
            description=(
                "Push Real-Time Configuration from local files to Agent Studio.\n\n"
                "Examples:\n"
                "  poly rtc push --env sandbox\n"
                "  poly rtc push --env sandbox --schema\n"
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
        rtc_push_mode = rtc_push_parser.add_mutually_exclusive_group()
        rtc_push_mode.add_argument(
            "--schema",
            action="store_true",
            help="Push schema only.",
        )
        rtc_push_mode.add_argument(
            "--data",
            action="store_true",
            help="Push data only.",
        )

        rtc_edit_parser = rtc_subparsers.add_parser(
            "edit",
            parents=[parents.path, parents.verbose, parents.debug],
            help="Pull, edit, and push RTC in one step.",
            description=(
                "Pull the latest RTC config, open it in your editor, and push changes\n"
                "back immediately. Set $EDITOR or $VISUAL to your preferred editor.\n\n"
                "Examples:\n"
                "  poly rtc edit --env sandbox\n"
                "  poly rtc edit --env sandbox --schema\n"
                "  poly rtc edit --env live --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        rtc_edit_parser.add_argument(
            "--env",
            type=str,
            required=True,
            choices=["sandbox", "pre-release", "live"],
            help="Environment to edit.",
        )
        rtc_edit_parser.add_argument(
            "--schema",
            action="store_true",
            help="Edit the schema instead of the data variables.",
        )
        rtc_edit_parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompt for live environment.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching RTC sub-handler."""
        schema_only = getattr(args, "schema", False)
        data_only = getattr(args, "data", False)

        if args.rtc_subcommand == "pull":
            result = cls.rtc_pull(
                args.path,
                args.env,
                output_json=args.json,
                schema_only=schema_only,
                data_only=data_only,
            )
            if args.json:
                json_print(result)
            else:
                if not result["success"]:
                    error(result["error"])
                    sys.exit(1)
                for f in result["files_written"]:
                    if not data_only:
                        success(f"Pulled {f['environment']} — {f['schema_file']}")
                    if not schema_only:
                        success(f"Pulled {f['environment']} — {f['data_file']}")
        elif args.rtc_subcommand == "push":
            result = cls.rtc_push(
                args.path,
                args.env,
                force=getattr(args, "force", False),
                output_json=args.json,
                no_merge=getattr(args, "no_merge", False),
                schema_only=schema_only,
                data_only=data_only,
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
        elif args.rtc_subcommand == "edit":
            cls.rtc_edit(
                args.path,
                args.env,
                edit_schema=getattr(args, "schema", False),
                force=getattr(args, "force", False),
            )

    @classmethod
    def rtc_pull(
        cls,
        base_path: str,
        env: str = "all",
        output_json: bool = False,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> dict:
        """Pull RTC from Agent Studio and write to local files.

        Args:
            base_path: Base path for the project.
            env: Environment(s) to pull — sandbox, pre-release, live, or all.
            output_json: If True, format errors as JSON on failure.
            schema_only: If True, only pull schema.
            data_only: If True, only pull data.

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

                schema_path = os.path.join(env_dir, "schema.json")
                data_path = os.path.join(env_dir, "data.json")

                if not data_only:
                    write_json_file(schema_path, schema)
                if not schema_only:
                    write_json_file(data_path, variables)

                base_schema, base_variables = _load_rtc_base(env_dir)
                _save_rtc_base(
                    env_dir,
                    schema if not data_only else (base_schema or schema),
                    variables if not schema_only else (base_variables or variables),
                )
                _set_rtc_last_updated(project, client_env, config.get("lastUpdated"))

                results.append(
                    {
                        "environment": client_env,
                        "schema_file": schema_path,
                        "data_file": data_path,
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
        schema_only: bool = False,
        data_only: bool = False,
    ) -> Optional[dict]:
        """Push RTC from local files to Agent Studio.

        Args:
            base_path: Base path for the project.
            env: Environment to push to — sandbox, pre-release, or live.
            force: If True, skip drift check and confirmation prompt.
            output_json: If True, format errors as JSON on failure.
            no_merge: If True, disable merge on drift; hard-fail instead.
            schema_only: If True, only push schema.
            data_only: If True, only push data.

        Returns:
            dict with success status, or None if the user cancelled interactively.
        """
        project = load_project(base_path, output_json=output_json)
        project_root = project.root_path

        dir_name = RTC_ENV_TO_DIR[env]
        env_dir = os.path.join(project_root, "real_time_configuration", dir_name)

        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not data_only and not os.path.exists(schema_path):
            return {"success": False, "error": f"schema.json not found at {schema_path}"}

        if not schema_only and not os.path.exists(data_path):
            return {"success": False, "error": f"data.json not found at {data_path}"}

        try:
            schema = None
            variables = None
            if not data_only:
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema = json.load(f)
            if not schema_only:
                with open(data_path, "r", encoding="utf-8") as f:
                    variables = json.load(f)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON in local RTC file: {e}"}

        # Drift protection
        if not force:
            local_last_updated = _get_rtc_last_updated(project, env)
            if local_last_updated is None:
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
                        if merge_result.get("schema") is not None:
                            schema = merge_result["schema"]
                        if merge_result.get("variables") is not None:
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

        return cls._do_push(
            project, env, env_dir, schema, variables, output_json, schema_only, data_only
        )

    @classmethod
    def _handle_drift(
        cls,
        env_dir: str,
        remote_config: dict,
        local_schema: Optional[dict],
        local_variables: Optional[dict],
        output_json: bool,
        no_merge: bool,
        env: str,
        local_last_updated: Optional[str],
        remote_last_updated: Optional[str],
    ) -> Optional[dict]:
        """Handle drift between local and remote RTC config."""
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

        merged_schema = local_schema
        if local_schema is not None:
            merged_schema = _merge_rtc_file(
                "schema.json", base_schema, local_schema, remote_schema, output_json
            )
            if merged_schema is None and not output_json:
                return None
            if merged_schema is None:
                return {
                    "success": False,
                    "error": drift_msg + "Schema conflicts.",
                    "conflicts": True,
                }

        merged_variables = local_variables
        if local_variables is not None:
            merged_variables = _merge_rtc_file(
                "data.json", base_variables, local_variables, remote_variables, output_json
            )
            if merged_variables is None and not output_json:
                return None
            if merged_variables is None:
                return {
                    "success": False,
                    "error": drift_msg + "Data conflicts.",
                    "conflicts": True,
                }

        if not output_json:
            info("Merge complete.")

        return {"success": True, "schema": merged_schema, "variables": merged_variables}

    @classmethod
    def _do_push(
        cls,
        project: AgentStudioProject,
        env: str,
        env_dir: str,
        schema: Optional[dict],
        variables: Optional[dict],
        output_json: bool,
        schema_only: bool = False,
        data_only: bool = False,
    ) -> dict:
        """Execute the actual push to the API and update local state."""
        last_response = None
        if schema is not None and not data_only:
            try:
                last_response = AgentStudioInterface.put_rtc_schema(
                    region=project.region,
                    project_id=project.project_id,
                    client_env=env,
                    schema=schema,
                )
            except requests.HTTPError as e:
                return {"success": False, "error": str(e), "step": "schema"}

        if variables is not None and not schema_only:
            try:
                last_response = AgentStudioInterface.patch_rtc_variables(
                    region=project.region,
                    project_id=project.project_id,
                    client_env=env,
                    variables=variables,
                )
            except requests.HTTPError as e:
                # Schema was already pushed — update metadata so drift check
                # doesn't falsely trigger on retry.
                if last_response and last_response.get("lastUpdated"):
                    _set_rtc_last_updated(project, env, last_response["lastUpdated"])
                if not output_json and schema is not None:
                    error(f"Warning: schema was pushed to {env}, but variables update failed.")
                return {
                    "success": False,
                    "error": f"Schema pushed but variables failed: {e}",
                    "step": "variables",
                }

        if last_response and last_response.get("lastUpdated"):
            _set_rtc_last_updated(project, env, last_response["lastUpdated"])

        base_schema, base_variables = _load_rtc_base(env_dir)
        _save_rtc_base(
            env_dir,
            schema if schema is not None else (base_schema or {}),
            variables if variables is not None else (base_variables or {}),
        )
        if schema is not None:
            write_json_file(os.path.join(env_dir, "schema.json"), schema)
        if variables is not None:
            write_json_file(os.path.join(env_dir, "data.json"), variables)

        return {
            "success": True,
            "environment": env,
            "schema_file": os.path.join(env_dir, "schema.json"),
            "data_file": os.path.join(env_dir, "data.json"),
        }

    @classmethod
    def rtc_edit(
        cls,
        base_path: str,
        env: str,
        edit_schema: bool = False,
        force: bool = False,
    ) -> None:
        """Pull latest RTC, open in editor, and push back.

        Args:
            base_path: Base path for the project.
            env: Environment to edit.
            edit_schema: If True, edit schema instead of data.
            force: If True, skip confirmation for live environment.
        """
        project = load_project(base_path)
        project_root = project.root_path

        try:
            config = AgentStudioInterface.get_rtc_config(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
            )
        except requests.HTTPError as e:
            error(f"Failed to fetch RTC config: {e}")
            sys.exit(1)

        baseline_last_updated = config.get("lastUpdated")

        if edit_schema:
            content = config.get("schema", {})
            filename = "schema.json"
        else:
            content = config.get("variables", {})
            filename = "data.json"

        content_str = json.dumps(content, indent=2, sort_keys=True) + "\n"

        try:
            edited_str = edit_in_editor(content_str, extension=".json", filename=filename)
        except ValueError:
            info("No changes made.")
            return
        except (FileNotFoundError, OSError) as e:
            error(f"Could not open editor: {e}. Check your $EDITOR or $VISUAL setting.")
            sys.exit(1)

        try:
            edited = json.loads(edited_str)
        except json.JSONDecodeError as e:
            error(f"Invalid JSON: {e}")
            sys.exit(1)

        # Race check: ensure remote hasn't changed while editing
        try:
            current_config = AgentStudioInterface.get_rtc_config(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
            )
        except requests.HTTPError as e:
            error(f"Failed to check remote state: {e}")
            sys.exit(1)

        if current_config.get("lastUpdated") != baseline_last_updated:
            error(
                "Remote config was modified while you were editing. "
                "Your changes have NOT been pushed. Please try again."
            )
            sys.exit(1)

        if env == "live" and not force:
            confirm = questionary.confirm(
                f"Push RTC to {env}? This will update live configuration.",
                auto_enter=False,
                default=False,
            ).ask()
            if not confirm:
                info("Push cancelled.")
                return

        try:
            if edit_schema:
                response = AgentStudioInterface.put_rtc_schema(
                    region=project.region,
                    project_id=project.project_id,
                    client_env=env,
                    schema=edited,
                )
            else:
                response = AgentStudioInterface.patch_rtc_variables(
                    region=project.region,
                    project_id=project.project_id,
                    client_env=env,
                    variables=edited,
                )
        except requests.HTTPError as e:
            error(f"Push failed: {e}")
            sys.exit(1)

        if response and response.get("lastUpdated"):
            _set_rtc_last_updated(project, env, response["lastUpdated"])

        # Update local files if the env directory exists
        dir_name = RTC_ENV_TO_DIR[env]
        env_dir = os.path.join(project_root, "real_time_configuration", dir_name)
        if os.path.isdir(env_dir):
            if edit_schema:
                write_json_file(os.path.join(env_dir, "schema.json"), edited)
                base_schema, base_variables = _load_rtc_base(env_dir)
                _save_rtc_base(env_dir, edited, base_variables or {})
            else:
                write_json_file(os.path.join(env_dir, "data.json"), edited)
                base_schema, base_variables = _load_rtc_base(env_dir)
                _save_rtc_base(env_dir, base_schema or {}, edited)

        success(f"Edited and pushed RTC {filename} to {env}")
