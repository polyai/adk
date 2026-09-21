"""RTC command family: pull and push Real-Time Configuration.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.console import edit_in_editor, error, info, success, warning
from poly.output.json_output import json_print
from poly.project import AgentStudioProject
from poly.resources.resource_utils import contains_merge_conflict
from poly.utils import merge_rtc_dicts


def _to_sorted_json(data: dict) -> str:
    """Serialize a dict to deterministically ordered JSON for merging."""
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


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
    import questionary

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

    group = PROJECT_SYNC_GROUP

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
        rtc_push_parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip schema validation before pushing.",
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

        rtc_diff_parser = rtc_subparsers.add_parser(
            "diff",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Show differences between local and remote RTC config.",
            description=(
                "Compare local RTC files against the remote Agent Studio config.\n\n"
                "Examples:\n"
                "  poly rtc diff --env sandbox\n"
                "  poly rtc diff --env all\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        rtc_diff_parser.add_argument(
            "--env",
            type=str,
            default="all",
            choices=["sandbox", "pre-release", "live", "all"],
            help="Environment to diff. Defaults to all.",
        )

        rtc_validate_parser = rtc_subparsers.add_parser(
            "validate",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Validate local RTC data against its schema.",
            description=(
                "Validate that local data.json conforms to its schema.json.\n\n"
                "Examples:\n"
                "  poly rtc validate --env sandbox\n"
                "  poly rtc validate --env all\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        rtc_validate_parser.add_argument(
            "--env",
            type=str,
            default="all",
            choices=["sandbox", "pre-release", "live", "all"],
            help="Environment to validate. Defaults to all.",
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
                    if not data_only and "schema_file" in f:
                        success(f"Pulled {f['environment']} — {f['schema_file']}")
                    if not schema_only and "data_file" in f:
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
                skip_validation=getattr(args, "skip_validation", False),
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
            result = cls.rtc_edit(
                args.path,
                args.env,
                edit_schema=getattr(args, "schema", False),
                force=getattr(args, "force", False),
            )
            if result is None:
                return
            if not result["success"]:
                error(result["error"])
                sys.exit(1)
            what = "schema.json" if getattr(args, "schema", False) else "data.json"
            success(f"Edited and pushed RTC {what} to {args.env}")
        elif args.rtc_subcommand == "diff":
            result = cls.rtc_diff(args.path, args.env, output_json=args.json)
            if args.json:
                json_print(result)
            else:
                if not result["success"]:
                    error(result["error"])
                    sys.exit(1)
        elif args.rtc_subcommand == "validate":
            result = cls.rtc_validate(args.path, args.env, output_json=args.json)
            if args.json:
                json_print(result)
            else:
                if not result["success"]:
                    error(result["error"])
                    sys.exit(1)

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

        Returns:
            dict: Result with success status and files_written list.
        """
        import requests

        project = load_project(base_path, output_json=output_json)

        if env == "all":
            envs_to_fetch = list(AgentStudioProject.RTC_ENV_TO_DIR.keys())
        else:
            envs_to_fetch = [env]

        results = []
        try:
            for client_env in envs_to_fetch:
                result = project.rtc_pull_env(
                    client_env, schema_only=schema_only, data_only=data_only
                )
                results.append(result)

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
        skip_validation: bool = False,
    ) -> Optional[dict]:
        """Push RTC from local files to Agent Studio.

        Returns:
            dict with success status, or None if the user cancelled interactively.
        """
        import questionary
        import requests

        project = load_project(base_path, output_json=output_json)

        # Load local files
        try:
            local = project.rtc_load_local(env, schema_only=schema_only, data_only=data_only)
        except (FileNotFoundError, ValueError) as e:
            return {"success": False, "error": str(e)}

        schema = local["schema"]
        variables = local["variables"]

        # Schema validation
        if not skip_validation and schema is not None and variables is not None:
            validation_errors = AgentStudioProject.validate_rtc_data(schema, variables)
            if validation_errors:
                err_lines = "\n  ".join(validation_errors)
                return {
                    "success": False,
                    "error": f"RTC validation failed:\n  {err_lines}\n"
                    "Use --skip-validation to bypass.",
                    "validation_errors": validation_errors,
                }

        # Drift protection
        if not force:
            try:
                drift = project.check_rtc_drift(env)
            except requests.HTTPError as e:
                return {"success": False, "error": f"Drift check failed: {e}"}

            if drift["status"] == "no_metadata":
                if not output_json:
                    info(
                        "No RTC metadata found; skipping drift check. "
                        "Run 'poly rtc pull' to enable drift protection."
                    )
            elif drift["status"] == "drifted":
                merge_result = cls._handle_drift(
                    project=project,
                    remote_config=drift["remote_config"],
                    local_schema=schema,
                    local_variables=variables,
                    output_json=output_json,
                    no_merge=no_merge,
                    env=env,
                    local_last_updated=drift["local_last_updated"],
                    remote_last_updated=drift["remote_last_updated"],
                )
                if merge_result is None:
                    return None
                if not merge_result["success"]:
                    return merge_result
                if merge_result.get("schema") is not None:
                    schema = merge_result["schema"]
                if merge_result.get("variables") is not None:
                    variables = merge_result["variables"]

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

        result = project.rtc_push_to_api(
            env,
            schema=schema,
            variables=variables,
            schema_only=schema_only,
            data_only=data_only,
        )
        if not result["success"] and not output_json and result.get("step") == "variables":
            error(f"Warning: schema was pushed to {env}, but variables update failed.")
        return result

    @classmethod
    def _handle_drift(
        cls,
        project: AgentStudioProject,
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

        base_schema, base_variables = project.get_rtc_base(env)

        needs_schema_base = local_schema is not None
        needs_data_base = local_variables is not None
        if (needs_schema_base and base_schema is None) or (
            needs_data_base and base_variables is None
        ):
            return {
                "success": False,
                "error": drift_msg + "Cannot merge: no base version available. "
                f"Run 'poly rtc pull --env {env}' to enable merge on future pushes, "
                "or use --force to overwrite.",
            }

        remote_schema = remote_config.get("schema") or {}
        remote_variables = remote_config.get("variables") or {}

        if not output_json:
            info("Remote has changed since your last pull. Attempting merge...")

        merged_schema = local_schema
        if local_schema is not None and base_schema is not None:
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
        if local_variables is not None and base_variables is not None:
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
    def rtc_edit(
        cls,
        base_path: str,
        env: str,
        edit_schema: bool = False,
        force: bool = False,
    ) -> Optional[dict]:
        """Pull latest RTC, open in editor, and push back.

        Returns:
            dict with success status, or None if cancelled/no changes.
        """
        import questionary
        import requests

        project = load_project(base_path)

        try:
            config = project.rtc_fetch_config(env)
        except requests.HTTPError as e:
            return {"success": False, "error": f"Failed to fetch RTC config: {e}"}

        baseline_last_updated = config.get("lastUpdated")
        schema = config.get("schema") or {}
        variables = config.get("variables") or {}

        if edit_schema:
            content = schema
            filename = "schema.json"
        else:
            content = variables
            filename = "data.json"

        content_str = json.dumps(content, indent=2, sort_keys=True, ensure_ascii=False) + "\n"

        try:
            edited_str = edit_in_editor(content_str, extension=".json", filename=filename)
        except ValueError:
            info("No changes made.")
            return None
        except (FileNotFoundError, OSError) as e:
            return {
                "success": False,
                "error": f"Could not open editor: {e}. Check your $EDITOR or $VISUAL setting.",
            }

        try:
            edited = json.loads(edited_str)
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {e}"}

        # Schema validation (validate edited data against schema, or check edited schema)
        if not edit_schema and schema:
            validation_errors = AgentStudioProject.validate_rtc_data(schema, edited)
            if validation_errors:
                err_lines = "\n  ".join(validation_errors)
                return {
                    "success": False,
                    "error": f"RTC validation failed:\n  {err_lines}",
                    "validation_errors": validation_errors,
                }

        # Race check
        try:
            current_config = project.rtc_fetch_config(env)
        except requests.HTTPError as e:
            return {"success": False, "error": f"Failed to check remote state: {e}"}

        if current_config.get("lastUpdated") != baseline_last_updated:
            return {
                "success": False,
                "error": "Remote config was modified while you were editing. "
                "Your changes have NOT been pushed. Please try again.",
            }

        if env == "live" and not force:
            confirm = questionary.confirm(
                f"Push RTC to {env}? This will update live configuration.",
                auto_enter=False,
                default=False,
            ).ask()
            if not confirm:
                info("Push cancelled.")
                return None

        if edit_schema:
            result = project.rtc_push_to_api(env, schema=edited)
        else:
            result = project.rtc_push_to_api(env, variables=edited)

        return result

    @classmethod
    def rtc_diff(
        cls,
        base_path: str,
        env: str = "all",
        output_json: bool = False,
    ) -> dict:
        """Show differences between local and remote RTC config.

        Returns:
            dict with success status and per-environment diffs.
        """
        import requests

        project = load_project(base_path, output_json=output_json)

        if env == "all":
            envs_to_diff = list(AgentStudioProject.RTC_ENV_TO_DIR.keys())
        else:
            envs_to_diff = [env]

        diffs = []
        try:
            for client_env in envs_to_diff:
                env_diff = project.rtc_diff_env(client_env)

                if not output_json:
                    if env_diff.get("status") == "no_local_files":
                        info(f"  {client_env}: no local files — run poly rtc pull first")
                    else:
                        _print_env_diff(client_env, env_diff)

                diffs.append(env_diff)

            return {"success": True, "diffs": diffs}

        except requests.HTTPError as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def rtc_validate(
        cls,
        base_path: str,
        env: str = "all",
        output_json: bool = False,
    ) -> dict:
        """Validate local RTC data against its schema.

        Returns:
            dict with success status and per-environment validation results.
        """
        project = load_project(base_path, output_json=output_json)

        if env == "all":
            envs_to_validate = list(AgentStudioProject.RTC_ENV_TO_DIR.keys())
        else:
            envs_to_validate = [env]

        results = []
        all_valid = True

        for client_env in envs_to_validate:
            result = project.rtc_validate_env(client_env)

            if result.get("status") == "skipped":
                if not output_json:
                    info(f"  {client_env}: skipped — missing local files")
            elif result.get("valid") is False:
                all_valid = False
                if not output_json:
                    error(f"  {client_env}: validation failed")
                    for err in result["errors"]:
                        error(f"    {err}")
            else:
                if not output_json:
                    success(f"  {client_env}: valid")

            results.append(result)

        return {"success": all_valid, "results": results}


def _print_env_diff(env: str, env_diff: dict) -> None:
    """Print a human-readable diff for one environment."""
    schema_changes = env_diff.get("schema", [])
    data_changes = env_diff.get("data", [])

    if not schema_changes and not data_changes:
        success(f"  {env}: no changes")
        return

    info(f"  === {env} ===")
    if schema_changes:
        info("  schema.json:")
        for c in schema_changes:
            _print_change(c)
    else:
        info("  schema.json: (no changes)")

    if data_changes:
        info("  data.json:")
        for c in data_changes:
            _print_change(c)
    else:
        info("  data.json: (no changes)")


def _print_change(change: dict) -> None:
    """Print a single field-level change."""
    path = change["path"]
    change_type = change["type"]

    if change_type == "added_locally":
        info(f"    + {path}: {json.dumps(change['local'], ensure_ascii=False)}")
    elif change_type == "only_remote":
        info(f"    - {path}: {json.dumps(change['remote'], ensure_ascii=False)} (only on remote)")
    elif change_type == "changed":
        info(
            f"    ~ {path}: {json.dumps(change['remote'], ensure_ascii=False)} → "
            f"{json.dumps(change['local'], ensure_ascii=False)}"
        )
