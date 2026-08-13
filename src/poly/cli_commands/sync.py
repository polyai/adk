"""Sync command family: pull, push, status, revert, diff, format, validate.

Copyright PolyAI Limited
"""

import logging
import os
import shutil
import subprocess
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from contextlib import nullcontext
from typing import Any, Optional

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import (
    compute_diff,
    load_project,
    parse_from_projection_json,
    print_project_file_changes,
)
from poly.output.json_output import commands_to_dicts, json_print

logger = logging.getLogger(__name__)


class FetchCommand(BaseCommand):
    """Fetch the latest project configuration from Agent Studio without applying it."""

    command = "fetch"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``fetch`` subcommand."""
        fetch_parser = subparsers.add_parser(
            "fetch",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Fetch the latest project state from Agent Studio without modifying local files.",
            description="Fetch the latest project state from Agent Studio without modifying local resource files.\n\nLike 'git fetch', this updates the tracked remote state but does not change your working files.\nUse --branch to switch to a different branch before fetching.\n\nExamples:\n  poly fetch\n  poly fetch --branch my-feature",
            formatter_class=RawTextHelpFormatter,
        )
        fetch_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )
        fetch_parser.add_argument(
            "--branch",
            "-b",
            type=str,
            default=None,
            help="Switch to this branch before fetching. Errors if the branch does not exist.",
        )
        fetch_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        fetch_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help=SUPPRESS,
            default=False,
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the fetch command."""
        cls.fetch(
            args.path,
            args.branch,
            args.from_projection,
            output_json=args.json,
            output_json_projection=args.output_json_projection,
        )

    @classmethod
    def fetch(
        cls,
        base_path: str,
        branch_name: Optional[str] = None,
        from_projection: Optional[str] = None,
        output_json: bool = False,
        output_json_projection: bool = False,
    ) -> None:
        """Fetch the latest project state from Agent Studio without modifying local files."""

        from poly.output.console import info, success

        project = load_project(base_path, output_json=output_json)
        if not output_json:
            info(f"Fetching project [bold]{project.account_id}/{project.project_id}[/bold]...")

        projection_json = parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        projection = project.fetch_project(
            branch_name=branch_name,
            projection_json=projection_json,
        )

        if output_json or output_json_projection:
            json_output: dict[str, Any] = {"success": True}
            if branch_name:
                json_output["branch_name"] = branch_name
                json_output["branch_id"] = project.branch_id
            if output_json_projection:
                json_output["projection"] = projection
            json_print(json_output)
            return

        if branch_name:
            info(f"Switched to branch '{branch_name}'.")
        success(f"Fetched {project.account_id}/{project.project_id}")


class PullCommand(BaseCommand):
    """Pull the latest project configuration from Agent Studio."""

    command = "pull"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``pull`` subcommand."""
        pull_parser = subparsers.add_parser(
            "pull",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Pull the latest project configuration from Agent Studio.",
            description="Pull the latest project configuration from Agent Studio.\n\nExamples:\n  poly pull --path /path/to/project\n  poly pull -f  # force overwrite local changes",
            formatter_class=RawTextHelpFormatter,
        )
        pull_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to pull the project. Defaults to current working directory.",
        )
        pull_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force pull the project, overwriting all local changes (includes deleting new resources)",
        )
        pull_parser.add_argument(
            "--format",
            action="store_true",
            help="Format resources after pulling.",
            default=False,
        )
        pull_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        pull_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help=SUPPRESS,
            default=False,
        )
        pull_parser.add_argument(
            "--include-rtc",
            action="store_true",
            default=False,
            help="Also pull Real-Time Configuration for all environments.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the pull command."""
        cls.pull(
            args.path,
            args.force,
            args.format,
            args.from_projection,
            output_json=args.json,
            output_json_projection=args.output_json_projection,
            include_rtc=getattr(args, "include_rtc", False),
        )

    @classmethod
    def pull(
        cls,
        base_path: str,
        force: bool = False,
        format: bool = False,
        from_projection: str = None,
        output_json: bool = False,
        output_json_projection: bool = False,
        include_rtc: bool = False,
    ) -> None:
        """Pull the latest project configuration from the Agent Studio."""
        from poly.output.console import console, error, info, print_file_list, success, warning

        project = load_project(base_path, output_json=output_json)
        if not output_json:
            info(f"Pulling project [bold]{project.account_id}/{project.project_id}[/bold]...")

        projection_json = parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        original_branch_id = project.branch_id

        ctx = (
            console.status("[info]Saving resources...[/info]") if not output_json else nullcontext()
        )
        on_save = None

        with ctx as status:
            if status:

                def on_save(current: int, total: int) -> None:
                    status.update(f"[info]Saving resources ({current}/{total})...[/info]")

            files_with_conflicts, projection = project.pull_project(
                force=force, format=format, projection_json=projection_json, on_save=on_save
            )

        new_branch_name = None
        if original_branch_id != project.branch_id:
            new_branch_name = project.get_current_branch()
        if output_json or output_json_projection:
            json_output = {
                "success": not bool(files_with_conflicts),
                "files_with_conflicts": files_with_conflicts,
            }
            if new_branch_name:
                json_output["new_branch_name"] = new_branch_name
                json_output["new_branch_id"] = project.branch_id
            if output_json_projection:
                json_output["projection"] = projection
            if include_rtc and not files_with_conflicts:
                from poly.cli_commands.rtc import RTCCommand

                rtc_result = RTCCommand.rtc_pull(base_path, env="all", output_json=True)
                json_output["rtc"] = rtc_result
                if not rtc_result["success"]:
                    json_output["success"] = False
            json_print(json_output)
            if files_with_conflicts or not json_output["success"]:
                sys.exit(1)
            return

        if new_branch_name:
            warning(
                f"Current branch no longer exists in Agent Studio. Switched to branch '{new_branch_name}'."
            )
        if files_with_conflicts:
            print_file_list("Merge conflicts detected", files_with_conflicts, "filename.conflict")

        success(f"Pulled {project.account_id}/{project.project_id}")

        if include_rtc and not files_with_conflicts:
            from poly.cli_commands.rtc import RTCCommand

            rtc_result = RTCCommand.rtc_pull(base_path, env="all")
            if rtc_result["success"]:
                for f in rtc_result["files_written"]:
                    success(f"Pulled RTC {f['environment']} — {f['schema_file']}")
                    success(f"Pulled RTC {f['environment']} — {f['data_file']}")
            else:
                error(f"RTC pull failed: {rtc_result['error']}")
                sys.exit(1)


class PushCommand(BaseCommand):
    """Push the project configuration to Agent Studio."""

    command = "push"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``push`` subcommand."""
        push_parser = subparsers.add_parser(
            "push",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Push the project configuration to Agent Studio.",
            description="Push the project configuration to Agent Studio.\n\nExamples:\n  poly push --path /path/to/project\n  poly push --skip-validation --dry-run",
            formatter_class=RawTextHelpFormatter,
        )
        push_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to push the project. Defaults to current working directory.",
        )
        push_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force push the project, overwriting remote changes.",
        )
        push_parser.add_argument(
            "--skip-validation",
            action="store_true",
            help="Skip validation of the project before pushing.",
        )
        push_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run of the push without actually sending changes.",
        )
        push_parser.add_argument(
            "--format",
            action="store_true",
            help="Format resources before pushing.",
            default=False,
        )
        push_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        push_parser.add_argument(
            "--output-json-commands",
            action="store_true",
            help=SUPPRESS,
            default=False,
        )
        push_parser.add_argument(
            "--include-rtc",
            action="store_true",
            default=False,
            help="Also push Real-Time Configuration. Defaults to sandbox; use --rtc-env to override.",
        )
        push_parser.add_argument(
            "--rtc-env",
            type=str,
            default=None,
            choices=["sandbox", "pre-release", "live"],
            help="RTC environment to push to. Requires --include-rtc. Defaults to sandbox.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the push command."""
        if args.rtc_env is not None and not args.include_rtc:
            from poly.output.console import warning

            warning("--rtc-env has no effect without --include-rtc.")

        cls.push(
            args.path,
            args.force,
            args.skip_validation,
            args.dry_run,
            args.format,
            args.from_projection,
            output_json=args.json,
            output_commands=args.output_json_commands,
            include_rtc=args.include_rtc,
            rtc_env=args.rtc_env or "sandbox",
        )

    @classmethod
    def push(
        cls,
        base_path: str,
        force: bool = False,
        skip_validation: bool = False,
        dry_run: bool = False,
        format: bool = False,
        from_projection: str = None,
        output_json: bool = False,
        output_commands: bool = False,
        include_rtc: bool = False,
        rtc_env: str = "sandbox",
    ) -> None:
        """Push the project configuration to the Agent Studio."""
        from poly.output.console import error, info, plain, success, warning

        project = load_project(base_path, output_json=output_json)
        if not output_json and not output_commands:
            info(
                f"Pushing local changes for [bold]{project.account_id}/{project.project_id}[/bold]..."
            )

        projection_json = parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_commands,
        )

        original_branch_id = project.branch_id
        push_ok, output, commands = project.push_project(
            force=force,
            skip_validation=skip_validation,
            dry_run=dry_run,
            format=format,
            projection_json=projection_json,
        )
        new_branch_name = None
        if original_branch_id != project.branch_id:
            new_branch_name = project.get_current_branch()
        if output_json or output_commands:
            json_output = {
                "success": push_ok,
                "message": output,
                "dry_run": dry_run,
            }
            if new_branch_name:
                json_output["switched_to"] = new_branch_name
                json_output["new_branch_id"] = project.branch_id
            if output_commands:
                json_output["commands"] = commands_to_dicts(commands)
            if include_rtc and push_ok and not dry_run:
                from poly.cli_commands.rtc import RTCCommand

                rtc_result = RTCCommand.rtc_push(
                    base_path,
                    env=rtc_env,
                    force=force,
                    output_json=(output_json or output_commands),
                )
                if rtc_result is None:
                    json_output["rtc"] = {"success": False, "error": "RTC push cancelled."}
                    json_output["success"] = False
                else:
                    json_output["rtc"] = rtc_result
                    if not rtc_result.get("success"):
                        json_output["success"] = False
            json_print(json_output)
            if not json_output["success"]:
                sys.exit(1)
            return

        if new_branch_name:
            warning(f"Created and switched to new branch '{new_branch_name}'.")
        if push_ok:
            success(f"Pushed {project.account_id}/{project.project_id} to Agent Studio.")
        else:
            error(f"Failed to push {project.account_id}/{project.project_id} to Agent Studio.")
            plain(output)

        if include_rtc and push_ok and not dry_run:
            from poly.cli_commands.rtc import RTCCommand

            rtc_result = RTCCommand.rtc_push(base_path, env=rtc_env, force=force)
            if rtc_result is None:
                error("RTC push cancelled.")
                sys.exit(1)
            elif rtc_result["success"]:
                success(f"Pushed RTC to {rtc_env}")
            else:
                error(f"RTC push failed: {rtc_result['error']}")
                sys.exit(1)


class StatusCommand(BaseCommand):
    """Check the changed files of the project."""

    command = "status"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``status`` subcommand."""
        status_parser = subparsers.add_parser(
            "status",
            parents=[parents.verbose, parents.json],
            help="Check the changed files of the project.",
            description="Check the changed files of the project.\n\nExamples:\n  poly status\n  poly status --path /path/to/project",
            formatter_class=RawTextHelpFormatter,
        )
        status_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="""
            Base path to check the project status. Defaults to current working directory.
            """,
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the status command."""
        cls.status(args.path, args.json)

    @classmethod
    def status(cls, base_path: str, output_json: bool = False) -> None:
        """Check the changed files of the project."""
        project = load_project(base_path, output_json=output_json)
        print_project_file_changes(project, output_json=output_json)


class RevertCommand(BaseCommand):
    """Revert changes in the project."""

    command = "revert"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``revert`` subcommand."""
        revert_parser = subparsers.add_parser(
            "revert",
            parents=[parents.verbose, parents.json],
            help="Revert changes in the project.",
            description="Revert changes in the project.\n\nExamples:\n  poly revert\n  poly revert file1.yaml file2.yaml",
            formatter_class=RawTextHelpFormatter,
        )
        revert_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="""
            Base path to revert the project. Defaults to current working directory.
            """,
        )
        revert_parser.add_argument(
            "files",
            nargs="*",
            help="List of files to revert. If not specified, it will revert all changes.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the revert command."""
        cls.revert(args.path, args.files, output_json=args.json)

    @classmethod
    def revert(
        cls,
        base_path: str,
        files: list[str] = None,
        output_json: bool = False,
    ) -> None:
        """Revert changes in the project."""
        from poly.output.console import plain, success

        project = load_project(base_path, output_json=output_json)

        # If relative paths are provided, convert them to absolute paths
        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        files_reverted = project.revert_changes(file_paths=files)
        if output_json:
            json_print(
                {
                    "success": True,
                    "files_reverted": files_reverted,
                }
            )
            return
        if not files_reverted:
            plain("[muted]No changes to revert.[/muted]")
            return

        success("Changes reverted successfully.")


class DiffCommand(BaseCommand):
    """Show the changes made to the project."""

    command = "diff"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``diff`` subcommand."""
        diff_parser = subparsers.add_parser(
            "diff",
            parents=[parents.verbose, parents.json],
            help="Show the changes made to the project.",
            description="Show the changes made to the project.\n\nExamples:\n  poly diff\n  poly diff sandbox\n  poly diff --before hash1 --after hash2\n  poly diff --files file1.yaml",
            formatter_class=RawTextHelpFormatter,
        )
        diff_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="""
            Base path to check the project status. Defaults to current working directory.
            """,
        )
        diff_parser.add_argument(
            "hash",
            nargs="?",
            default=None,
            type=str,
            help="Hash of the version to compare against. If not specified, it will be inferred from the --before and --after arguments.",
        )
        diff_parser.add_argument(
            "--files",
            nargs="*",
            help=("List of files to show changes for. If not specified, shows all changes."),
        )
        diff_parser.add_argument(
            "--before",
            type=str,
            help="Name of the original branch or version to compare with. If specified without --after, it will be compared against the current local project (before vs local).",
        )
        diff_parser.add_argument(
            "--after",
            type=str,
            help="Name of the branch or version to compare against. If specified without --before, it will be compared against the previous version",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the diff command."""
        cls.diff(args.path, args.files, args.hash, args.before, args.after, args.json)

    @classmethod
    def diff(
        cls,
        base_path: str,
        files: list[str] = None,
        version_hash: str = None,
        before: str = None,
        after: str = None,
        output_json: bool = False,
    ) -> None:
        """Show diffs for the project.

        With no arguments, shows local changes against the remote version.
        Pass a version hash to compare that version against its predecessor.
        Use --before / --after to compare any two named versions or branches.
        """
        from poly.output.console import console, error, plain, print_diff

        if version_hash and (before or after):
            error("Cannot specify both hash and before/after versions.")
            return

        if version_hash:
            after = version_hash

        diffs = compute_diff(base_path, files, before, after, output_json=output_json)

        if not diffs:
            if output_json and diffs is not None:
                json_print({"success": False, "message": "No changes detected"})
            elif output_json:
                json_print({"success": False, "message": "Failed to compute diffs."})
            else:
                plain("[muted]No changes detected.[/muted]")
            return

        if output_json:
            json_print(
                {
                    "success": True,
                    "diffs": diffs,
                }
            )
            return

        for file_path, diff_text in diffs.items():
            console.rule(f"[bold]{file_path}[/bold]")
            print_diff(diff_text)


class FormatCommand(BaseCommand):
    """Format project resources (Python via ruff, YAML/JSON via in-process formatting)."""

    command = "format"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``format`` subparser."""
        format_parser = subparsers.add_parser(
            "format",
            parents=[parents.verbose, parents.json],
            help="Run ruff and YAML/JSON formatting on the project (optional ty with --ty).",
            description=(
                "Run ruff (lint + format) on Python and formatting on YAML/JSON resources.\n\n"
                "By default applies fixes (ruff check --fix, ruff format; YAML/JSON via ruamel.yaml and stdlib).\n"
                "Use --check to only verify without writing changes. Use --ty to also run type checking.\n\n"
                "Examples:\n"
                "  poly format\n"
                "  poly format --path /path/to/project\n"
                "  poly format --check\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        format_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to run format/lint. Defaults to current working directory.",
        )
        format_parser.add_argument(
            "--files",
            nargs="*",
            help="Specific files/dirs to format. If not specified, runs on the whole --path tree.",
        )
        format_parser.add_argument(
            "--check",
            action="store_true",
            help="Only check; do not write (reports Python/YAML/JSON files that would be reformatted).",
        )
        format_parser.add_argument(
            "--ty",
            action="store_true",
            help="Run type checking (ty). Off by default because it can hang on some systems.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Run the format command."""
        cls.format(
            args.path,
            args.files,
            getattr(args, "check", False),
            getattr(args, "ty", False),
            output_json=args.json,
        )

    @classmethod
    def format(
        cls,
        base_path: str,
        files: list[str] = None,
        check_only: bool = False,
        run_ty: bool = False,
        output_json: bool = False,
    ) -> None:
        """Format project resources (Python via ruff, YAML/JSON via in-process formatting); optionally run ty."""
        from poly.output.console import error, info, plain, success

        project = load_project(base_path, output_json=output_json)
        files_resolved: list[str] | None = None
        if files:
            files_resolved = [os.path.abspath(os.path.join(base_path, f)) for f in files]

        if not output_json:
            if check_only:
                info("[bold]Check-only[/bold]: verifying formatting (no files will be modified).")
            else:
                info("[bold]Fix mode[/bold]: formatting project resources.")
            plain("")
            info(
                "Checking project resources (Python + YAML/JSON)"
                if check_only
                else "Formatting project resources (Python + YAML/JSON)"
            )

        affected, format_errors = project.format_files(files=files_resolved, check_only=check_only)
        rel_affected = [os.path.relpath(p, base_path) or p for p in affected]

        if format_errors:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "check_only": check_only,
                        "format_errors": format_errors,
                        "affected": rel_affected,
                        "ty_ran": False,
                        "ty_returncode": None,
                        "ty_timed_out": False,
                    }
                )
            else:
                for msg in format_errors:
                    plain(f"[red]{msg}[/red]")
                error("Format failed for some files.")
            sys.exit(1)

        if check_only and affected:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "check_only": check_only,
                        "format_errors": [],
                        "affected": rel_affected,
                        "ty_ran": False,
                        "ty_returncode": None,
                        "ty_timed_out": False,
                    }
                )
            else:
                for path in affected:
                    rel = os.path.relpath(path, base_path) or path
                    plain(f"[red]{rel}[/red]")
                info("Try [bold]poly format[/bold] to fix.")
            sys.exit(1)

        if not output_json:
            for path in affected:
                rel = os.path.relpath(path, base_path) or path
                plain(rel)
            success("Passed.")
            if check_only:
                success("All checks passed (no changes written).")
            else:
                success("All issues fixed." if affected else "No issues found.")

        ty_returncode: int | None = None
        ty_timed_out = False
        if run_ty:
            ty_cmd = [sys.executable, "-m", "ty"]
            if shutil.which("ty"):
                ty_cmd = ["ty"]
            if not output_json:
                info("Type checking (ty)")
            try:
                r = subprocess.run(
                    ty_cmd + ["check"],
                    cwd=base_path,
                    capture_output=output_json,
                    text=True,
                    timeout=15,
                    stdin=subprocess.DEVNULL,
                )
                ty_returncode = r.returncode
            except subprocess.TimeoutExpired:
                ty_timed_out = True
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "check_only": check_only,
                            "format_errors": [],
                            "affected": rel_affected,
                            "ty_ran": True,
                            "ty_returncode": None,
                            "ty_timed_out": True,
                        }
                    )
                else:
                    plain("[red]Timed out after 15s.[/red]")
                sys.exit(1)

            if not output_json and ty_returncode != 0:
                sys.exit(1)
            if not output_json:
                success("Passed.")

        if output_json:
            json_print(
                {
                    "success": not (run_ty and ty_returncode not in (None, 0)),
                    "check_only": check_only,
                    "format_errors": [],
                    "affected": rel_affected,
                    "ty_ran": run_ty,
                    "ty_returncode": ty_returncode,
                    "ty_timed_out": ty_timed_out,
                }
            )
            if run_ty and ty_returncode != 0:
                sys.exit(1)


class ValidateCommand(BaseCommand):
    """Validate the project configuration locally."""

    command = "validate"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``validate`` subparser."""
        validate_parser = subparsers.add_parser(
            "validate",
            parents=[parents.verbose, parents.json],
            help="Validate the project configuration locally.",
            description="Validate the project configuration locally.\n\nExamples:\n  poly validate --path /path/to/project\n",
            formatter_class=RawTextHelpFormatter,
        )
        validate_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to validate the project. Defaults to current working directory.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Run the validate command."""
        cls.validate_project(args.path, args.json)

    @classmethod
    def validate_project(cls, base_path: str, output_json: bool = False) -> None:
        """Validate the project configuration locally."""
        from poly.output.console import print_validation_errors, success

        project = load_project(base_path, output_json=output_json)
        errors = project.validate_project()

        if output_json:
            json_output = {
                "valid": bool(not errors),
                "errors": errors,
            }
            json_print(json_output)
            return

        if not errors:
            success("Project configuration is valid.")
        else:
            print_validation_errors(errors)
            sys.exit(1)
