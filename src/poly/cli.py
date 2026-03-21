"""Agent Development Kit (ADK) CLI for managing Agent Studio projects.

Copyright PolyAI Limited
"""

# flake8: noqa

import base64
import json
import logging
import os
import shutil
import subprocess
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
from importlib.metadata import version as get_package_version
from typing import Optional

import argcomplete
import requests
import questionary

from poly.console import (
    console,
    error,
    handle_exception,
    info,
    plain,
    print_branches,
    print_diff,
    print_file_list,
    print_status,
    print_turn_metadata,
    print_validation_errors,
    set_verbose,
    success,
    warning,
)
from poly.handlers.github_api_handler import GitHubAPIHandler
from poly.output import commands_to_dicts, json_print
from poly.handlers.interface import (
    REGIONS,
    AgentStudioInterface,
)
from poly.resources import resource_utils
from poly.project import (
    PROJECT_CONFIG_FILE,
    STATUS_FILE,
    AgentStudioProject,
)

logger = logging.getLogger(__name__)

DOCUMENT_CHOICES = AgentStudioProject.discover_docs()


class AgentStudioCLI:
    """CLI Interface for Agent Studio."""

    @classmethod
    def _create_parser(cls) -> ArgumentParser:
        """Create and configure the CLI command parser."""
        try:
            _version = get_package_version("polyai-adk")
        except Exception:
            _version = "unknown"
        parser = ArgumentParser()
        parser.add_argument(
            "-v",
            "--version",
            action="version",
            version=_version,
            help="show the version and exit",
        )

        # Shared parent parser so --verbose works after any subcommand
        verbose_parent = ArgumentParser(add_help=False)
        verbose_parent.add_argument(
            "--verbose",
            action="store_true",
            default=False,
            help="Show full error tracebacks for debugging.",
        )

        subparsers = parser.add_subparsers(dest="command", required=True)

        # DOCS
        docs_parser = subparsers.add_parser(
            "docs",
            parents=[verbose_parent],
            help="Outputs documentation for a given topic.",
            description="Generate documentation",
            formatter_class=RawTextHelpFormatter,
        )
        docs_parser.add_argument(
            "documents",
            nargs="*",
            choices=DOCUMENT_CHOICES,
            help=f"Output documentation for the given topics. Choices: {', '.join(DOCUMENT_CHOICES)}",
        )
        docs_parser.add_argument(
            "--all",
            action="store_true",
            help="Output documentation for all topics.",
        )
        docs_parser.add_argument(
            "--output",
            "--write",
            "-o",
            type=str,
            metavar="FILE_PATH",
            dest="output",
            help="Write output to FILE_PATH instead of stdout.",
        )

        # INIT
        init_parser = subparsers.add_parser(
            "init",
            parents=[verbose_parent],
            help="Initialize a new Agent Studio project.",
            description="Initialize a new Agent Studio project.\n\nExamples:\n  poly init --region eu-west-1 --account_id 123 --project_id my_project\n  poly init  # (interactive selection)",
            formatter_class=RawTextHelpFormatter,
        )
        init_parser.add_argument(
            "--base-path",
            type=str,
            default=os.getcwd(),
            help="""
            Base path to initialize the project. Defaults to current working directory.
            """,
        )
        init_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--project_id",
            type=str,
            help="Project ID for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--format", action="store_true", help="Format resources after init."
        )
        init_parser.add_argument("--debug", action="store_true", help="Display debug logs.")

        # PULL
        pull_parser = subparsers.add_parser(
            "pull",
            parents=[verbose_parent],
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
        pull_parser.add_argument("--debug", action="store_true", help="Display debug logs.")
        pull_parser.add_argument(
            "--projection",
            action="store_true",
            default=False,
            help="Output the full SDK projection as JSON after pulling.",
        )

        # PUSH
        push_parser = subparsers.add_parser(
            "push",
            parents=[verbose_parent],
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
        push_parser.add_argument("--debug", action="store_true", help="Display debug logs.")
        push_parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Output machine-readable JSON instead of Rich formatting.",
        )
        push_parser.add_argument(
            "--commands",
            action="store_true",
            default=False,
            help="Output the SDK push commands that were sent, serialized as JSON.",
        )

        # STATUS
        status_parser = subparsers.add_parser(
            "status",
            parents=[verbose_parent],
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
        status_parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Output machine-readable JSON instead of Rich formatting.",
        )
        status_parser.add_argument(
            "--commands",
            action="store_true",
            default=False,
            help="Output the SDK push commands that would be sent, serialized as JSON.",
        )

        # REVERT
        revert_parser = subparsers.add_parser(
            "revert",
            parents=[verbose_parent],
            help="Revert changes in the project.",
            description="Revert changes in the project.\n\nExamples:\n  poly revert --all\n  poly revert file1.yaml file2.yaml",
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
            "--all",
            "-a",
            action="store_true",
            help="Revert all changes in the project.",
        )
        revert_parser.add_argument(
            "files",
            nargs="*",
            help="List of files to revert.",
        )

        # DIFF
        diff_parser = subparsers.add_parser(
            "diff",
            parents=[verbose_parent],
            help="Show the changes made to the project.",
            description="Show the changes made to the project.\n\nExamples:\n  poly diff\n  poly diff file1.yaml",
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
            "files",
            nargs="*",
            help=("List of files to show changes for. If not specified, shows all changes."),
        )
        diff_parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Output machine-readable JSON instead of Rich formatting.",
        )

        # REVIEW
        review_parser = subparsers.add_parser(
            "review",
            parents=[verbose_parent],
            help="Create an experience similar to a Pull Request, so that people can review changes locally or between versions/branches.",
            description=(
                "Make a review page against project configuration in Agent Studio.\n\n"
                "If you do not specify --before/--after, it compares your local project "
                "to the remote version (local vs remote).\n"
                "If you provide --before and --after, it compares those versions or "
                "branches directly.\n\n"
                "Examples:\n"
                "  poly review --path /path/to/project\n"
                "  poly review --path /path/to/project --before main --after feature-branch\n"
                "  poly review --path /path/to/project --before sandbox --after live\n"
                "  poly review --path /path/to/project --before version-hash-1 --after version-hash-2\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        review_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )
        review_parser.add_argument(
            "--before",
            type=str,
            help="Name of the original branch or version to compare against",
        )
        review_parser.add_argument(
            "--after",
            type=str,
            help="Name of the branch or version to compare with",
        )
        review_parser.add_argument(
            "--delete",
            action="store_true",
            help="Delete all the fully diff gists in your GitHub account.",
        )

        # Branch
        # GET BRANCHES 'branch list'
        branches_parser = subparsers.add_parser(
            "branch",
            parents=[verbose_parent],
            help="Manage branches in the Agent Studio project.",
            description="Manage branches in the Agent Studio project.\n\nExamples:\n  poly branch list\n  poly branch create new-branch\n  poly branch switch existing-branch",
            formatter_class=RawTextHelpFormatter,
        )
        branches_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to push the project. Defaults to current working directory.",
        )
        branches_parser.add_argument(
            "action",
            choices=["list", "create", "switch", "current"],
        )
        branches_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to create or switch to."
        )
        branches_parser.add_argument("--debug", action="store_true", help="Display debug logs.")
        branches_parser.add_argument(
            "--format",
            action="store_true",
            help="Format the project after switching branches.",
        )
        branches_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force switch to a different branch and discard changes.",
        )

        # FORMAT
        format_parser = subparsers.add_parser(
            "format",
            parents=[verbose_parent],
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
            "files",
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

        # Validate
        validate_parser = subparsers.add_parser(
            "validate",
            parents=[verbose_parent],
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
        validate_parser.add_argument(
            "--json",
            action="store_true",
            default=False,
            help="Output machine-readable JSON instead of Rich formatting.",
        )

        # CHAT
        chat_parser = subparsers.add_parser(
            "chat",
            parents=[verbose_parent],
            help="Start an interactive chat session with the agent.",
            description=(
                "Start an interactive chat session with the agent.\n\n"
                "Examples:\n"
                "  poly chat\n"
                "  poly chat --environment live\n"
                "  poly chat --path /path/to/project -e sandbox\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        chat_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )
        chat_parser.add_argument(
            "--environment",
            "-e",
            type=str,
            default="branch",
            choices=["branch", "sandbox", "pre-release", "live"],
            help="Environment to chat against. Defaults to current branch.",
        )
        chat_parser.add_argument(
            "--variant",
            type=str,
            default=None,
            help="Name of variant to use for the chat session.",
        )
        chat_parser.add_argument(
            "--channel",
            type=str,
            default="voice",
            choices=["voice", "webchat"],
            help="Channel to chat against. Defaults to voice.",
        )
        chat_parser.add_argument("--debug", action="store_true", help="Display debug logs.")
        chat_parser.add_argument(
            "--functions",
            action="store_true",
            default=False,
            help="Show function/tool calls made each turn.",
        )
        chat_parser.add_argument(
            "--flows",
            action="store_true",
            default=False,
            help="Show the active flow and step each turn.",
        )
        chat_parser.add_argument(
            "--state",
            action="store_true",
            default=False,
            help="Show per-turn state variable changes.",
        )
        chat_parser.add_argument(
            "--metadata",
            action="store_true",
            default=False,
            help="Show all metadata (functions, flows, and state). Equivalent to --functions --flows --state.",
        )

        # completion
        completion_parser = subparsers.add_parser(
            "completion",
            formatter_class=RawTextHelpFormatter,
            help="Generate shell completion scripts",
            description=(
                "Output a shell completion script for poly/adk.\n\n"
                "Add the output to your shell configuration to enable tab completion:\n\n"
                '  Bash:  eval "$(poly completion bash)"\n'
                "         # or: poly completion bash >> ~/.bash_completion\n\n"
                '  Zsh:   eval "$(poly completion zsh)"\n'
                "         # or: poly completion zsh > ~/.zsh/completions/_poly\n\n"
                "  Fish:  poly completion fish | source\n"
                "         # or: poly completion fish > ~/.config/fish/completions/poly.fish\n"
            ),
        )
        completion_parser.add_argument(
            "shell",
            choices=["bash", "zsh", "fish"],
            help="Shell type to generate completions for.",
        )

        return parser

    @classmethod
    def _run_command(cls, args):
        """Run the Agent Studio CLI command."""
        if hasattr(args, "debug") and args.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        if args.command == "init":
            cls.init_project(
                args.base_path,
                args.region,
                args.account_id,
                args.project_id,
                args.format,
            )

        elif args.command == "pull":
            cls.pull(
                args.path,
                args.force,
                args.format,
                projection_output=getattr(args, "projection", False),
            )

        elif args.command == "push":
            cls.push(
                args.path,
                args.force,
                args.skip_validation,
                args.dry_run,
                args.format,
                json_output=getattr(args, "json", False),
                commands_output=getattr(args, "commands", False),
            )

        elif args.command == "status":
            cls.status(
                args.path,
                json_output=getattr(args, "json", False),
                commands_output=getattr(args, "commands", False),
            )

        elif args.command == "revert":
            cls.revert(args.path, args.all, args.files)

        elif args.command == "diff":
            cls.diff(args.path, args.files, json_output=getattr(args, "json", False))

        elif args.command == "review":
            if args.delete:
                cls.delete_gists()
            else:
                if args.before and args.after:
                    cls.review(
                        base_path=args.path,
                        before_name=args.before,
                        after_name=args.after,
                    )
                else:
                    cls.review(args.path)

        elif args.command == "branch":
            if args.action == "list":
                cls.branch_list(args.path)

            elif args.action == "create":
                cls.branch_create(args.path, args.branch_name)

            elif args.action == "switch":
                cls.branch_switch(
                    args.path,
                    args.branch_name,
                    getattr(args, "force", False),
                    getattr(args, "format", False),
                )

            elif args.action == "current":
                cls.get_current_branch(args.path)

        elif args.command == "format":
            cls.format(
                args.path,
                args.files,
                getattr(args, "check", False),
                getattr(args, "ty", False),
            )

        elif args.command == "validate":
            cls.validate_project(args.path, json_output=getattr(args, "json", False))

        elif args.command == "docs":
            cls.docs(
                documents=args.documents,
                all_documents=getattr(args, "all", False),
                output=getattr(args, "output", None),
            )

        elif args.command == "chat":
            show_all = args.metadata
            cls.chat(
                args.path,
                args.environment,
                args.variant,
                args.channel,
                show_functions=show_all or args.functions,
                show_flow=show_all or args.flows,
                show_state=show_all or args.state,
            )

        elif args.command == "completion":
            cls.print_completion(args.shell)

    @classmethod
    def print_completion(cls, shell: str) -> None:
        """Print a shell completion script for poly/adk.

        Args:
            shell: Target shell — one of 'bash', 'zsh', or 'fish'.
        """
        script = argcomplete.shellcode(["poly", "adk"], shell=shell)
        print(script)

    @classmethod
    def main(cls, sys_args=None):
        """Main entry point for the CLI tool."""
        parser = cls._create_parser()
        argcomplete.autocomplete(parser)

        try:
            if sys_args:
                args = parser.parse_args(args=sys_args)
            else:
                args = parser.parse_args()

            set_verbose(args.verbose)
            cls._run_command(args)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            plain("\nAborted.")
            sys.exit(130)
        except Exception as e:
            handle_exception(e)

    @classmethod
    def _load_project(cls, base_path: str) -> AgentStudioProject:
        """Read project config or exit with a helpful error if not found.

        Args:
            base_path: Path to the project directory.
        """
        project = cls.read_project_config(base_path)
        if not project:
            error(
                "No project configuration found. Run [bold]poly init[/bold] to initialize a project."
            )
            sys.exit(1)
        return project

    @classmethod
    def read_project_config(cls, base_path: str) -> AgentStudioProject:
        """Read the project configuration from the specified base path.
        If not found, recurse into parent directories.
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
        return cls.read_project_config(parent_path)

    @classmethod
    def init_project(
        cls,
        base_path: str,
        region: str = None,
        account_id: str = None,
        project_id: str = None,
        format: bool = False,
    ) -> AgentStudioProject:
        """Initialize a new Agent Studio project."""
        info("Initialising project...")

        if not region:
            regions = REGIONS
            region_menu = questionary.select("Select Region", choices=regions).ask()
            region = region_menu

        api_handler = AgentStudioInterface()

        if not account_id:
            accounts = api_handler.get_accounts(region)
            account_menu = questionary.select(
                "Select Account",
                choices=list(accounts.keys()),
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not account_menu:
                warning("No account selected. Exiting.")
                return
            account_id = accounts[account_menu]

        if not project_id:
            projects = api_handler.get_projects(region, account_id)
            project_menu = questionary.select(
                "Select Project",
                choices=list(projects.keys()),
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not project_menu:
                warning("No project selected. Exiting.")
                return
            project_id = projects[project_menu]

        info(f"Initializing project [bold]{account_id}/{project_id}[/bold]...")

        project = AgentStudioProject.init_project(
            base_path=base_path,
            region=region,
            account_id=account_id,
            project_id=project_id,
            format=format,
        )

        if not project:
            error("Failed to initialize the project.")
            return None

        success(f"Project initialized at {project.root_path}")
        return project

    @classmethod
    def pull(
        cls,
        base_path: str,
        force: bool = False,
        format: bool = False,
        projection_output: bool = False,
    ) -> AgentStudioProject:
        """Pull the latest project configuration from the Agent Studio."""
        project = cls._load_project(base_path)

        if not projection_output:
            info(f"Pulling project [bold]{project.account_id}/{project.project_id}[/bold]...")

        files_with_conflicts = project.pull_project(force=force, format=format)

        if projection_output:
            projection = project.fetch_projection()
            json_print(projection)
            return project

        if files_with_conflicts:
            print_file_list("Merge conflicts detected", files_with_conflicts, "filename.conflict")

        success(f"Pulled {project.account_id}/{project.project_id}")
        return project

    @classmethod
    def push(
        cls,
        base_path: str,
        force: bool = False,
        skip_validation: bool = False,
        dry_run: bool = False,
        format: bool = False,
        json_output: bool = False,
        commands_output: bool = False,
    ) -> AgentStudioProject:
        """Push the project configuration to the Agent Studio."""
        project = cls._load_project(base_path)
        capture = json_output or commands_output

        if not capture:
            info(
                f"Pushing local changes for [bold]{project.account_id}/{project.project_id}[/bold]..."
            )

        push_ok, push_output, push_commands = project.push_project(
            force=force,
            skip_validation=skip_validation,
            dry_run=dry_run,
            format=format,
            capture_commands=capture,
        )

        if capture:
            result = {"success": push_ok, "message": push_output}
            if commands_output:
                result["commands"] = commands_to_dicts(push_commands)
            json_print(result)
            if not push_ok:
                sys.exit(1)
            return project

        if push_ok:
            success(f"Pushed {project.account_id}/{project.project_id} to Agent Studio.")
        else:
            error(f"Failed to push {project.account_id}/{project.project_id} to Agent Studio.")
            plain(push_output)

        return project

    @classmethod
    def status(
        cls,
        base_path: str,
        json_output: bool = False,
        commands_output: bool = False,
    ) -> None:
        """Check the changed files of the project."""
        project = cls._load_project(base_path)

        if commands_output:
            commands = project.generate_push_commands(skip_validation=True)
            json_print({"commands": commands_to_dicts(commands)})
            return

        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()
        branch_info = project.get_current_branch()

        if json_output:

            def _relativize(paths: list[str]) -> list[str]:
                return [os.path.relpath(p, project.root_path) for p in paths]

            json_print(
                {
                    "branch": branch_info,
                    "conflicts": _relativize(files_with_conflicts),
                    "new": _relativize(new_files),
                    "modified": _relativize(modified_files),
                    "deleted": _relativize(deleted_files),
                }
            )
            return

        print_status(
            region=project.region,
            account_id=project.account_id,
            project_id=project.project_id,
            last_updated=project.last_updated.isoformat(),
            branch=branch_info,
        )

        print_file_list("Files with merge conflicts", files_with_conflicts, "filename.conflict")
        print_file_list("New files", new_files, "filename.new")
        print_file_list("Deleted files", deleted_files, "filename.deleted")
        print_file_list("Modified files", modified_files, "filename.modified")

        if not modified_files and not new_files and not deleted_files and not files_with_conflicts:
            plain("\n[muted]No changes detected.[/muted]")

    @classmethod
    def revert(cls, base_path: str, all_files: bool = False, files: list[str] = None) -> None:
        """Revert changes in the project."""
        if not all_files and not files:
            error("No files specified to revert. Use [bold]--all[/bold] to revert all changes.")
            return

        project = cls._load_project(base_path)

        # If relative paths are provided, convert them to absolute paths
        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        files_reverted = project.revert_changes(all_files=all_files, files=files)
        if not files_reverted:
            plain("[muted]No changes to revert.[/muted]")
            return

        success("Changes reverted successfully.")

    @classmethod
    def _diff(cls, base_path: str, files: list[str] = None) -> Optional[dict[str, str]]:
        """Show the changes made to the project."""

        project = cls._load_project(base_path)

        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        diffs = project.get_diffs(all_files=not files, files=files)

        if not diffs:
            plain("[muted]No changes detected.[/muted]")
            return None

        return diffs

    @classmethod
    def diff(cls, base_path: str, files: list[str] = None, json_output: bool = False) -> None:
        """Show the changes made to the project."""
        diffs = cls._diff(base_path, files) or {}

        if json_output:
            project = cls._load_project(base_path)
            json_print(
                {
                    "files": [
                        {
                            "path": os.path.relpath(file_path, project.root_path),
                            "diff": diff_text,
                        }
                        for file_path, diff_text in diffs.items()
                    ]
                }
            )
            return

        for file_path, diff_text in diffs.items():
            console.rule(f"[bold]{file_path}[/bold]")
            print_diff(diff_text)

    @classmethod
    def _review(
        cls,
        base_path: str,
        before_name: str = None,
        after_name: str = None,
    ) -> dict:
        """Review the changes made to the project.
        Args:
            base_path: Base path for the project (used to read project config)
            before_name: Optional name of base branch (for comparing two remote branches)
            after_name: Optional name of compare branch (for comparing two remote branches)
        """
        if before_name and after_name:
            # Compare two remote versions/branches/environments
            project = cls._load_project(base_path)
            diffs = project.diff_remote_named_versions(before_name, after_name) or {}
        else:
            # Compare local vs remote (existing behavior)
            diffs = cls._diff(base_path) or {}

        if not diffs:
            return {}

        body = {}
        for file_path, diff in diffs.items():
            # Use the file_path as-is (it's already relative or a file path)
            safe_name = file_path.replace(os.sep, "_")
            body[f"{safe_name}.diff"] = {"content": diff}

        return body

    @classmethod
    def review(
        cls,
        base_path: str,
        before_name: str = None,
        after_name: str = None,
    ) -> None:
        """Show the changes made to the project in a Pull Request format.
        Args:
            base_path: Base path for the project (used to read project config)
            before_name: Optional name of base branch (for comparing two remote branches)
            after_name: Optional name of compare branch (for comparing two remote branches)
        """
        if before_name and after_name:
            body = cls._review(
                base_path=base_path,
                before_name=before_name,
                after_name=after_name,
            )
            description = f"Diff between '{before_name}' and '{after_name}'"
        else:
            body = cls._review(base_path)
            description = f"Diff for {'/'.join(base_path.split(os.sep)[-2:])}"

        if not body:
            return

        try:
            url = GitHubAPIHandler.create_gist(
                files=body,
                description=description,
                public=False,
            )
            success(f"Gist created: {url}")
        except requests.HTTPError as e:
            error(f"GitHub API error: {e}")
        except OSError as e:
            error(str(e))
        return

    @classmethod
    def delete_gists(cls) -> None:
        """Delete the gists made for the reviews of the project."""
        try:
            deleted = GitHubAPIHandler.delete_diff_gists()
            for gist_id in deleted:
                plain(f"  [muted]Deleted gist:[/muted] {gist_id}")
            success("All diff gists deleted.")
        except requests.HTTPError as e:
            error(f"GitHub API error: {e}")
        except OSError as e:
            error(str(e))
        return

    @classmethod
    def branch_list(cls, base_path: str) -> None:
        """List branches in the Agent Studio project."""
        project = cls._load_project(base_path)

        current_branch, branches = project.get_branches()
        if not branches:
            plain("[muted]No branches found.[/muted]")
            return

        print_branches(branches, current_branch)

        if current_branch is None:
            warning(
                f"Current local branch '{project.branch_id}' does not exist in Agent Studio. "
                "It may have been deleted or merged."
            )

    @classmethod
    def branch_create(cls, base_path: str, branch_name: str = None) -> None:
        """Create a new branch in the Agent Studio project."""
        project = cls._load_project(base_path)

        if project.branch_id != "main":
            error(
                "Branches can only be created from the [bold]main[/bold] branch (sandbox). "
                "Please switch and try again."
            )
            return

        if not branch_name:
            branch_name = input("Enter the name of the new branch: ").strip()
            if not branch_name:
                warning("No branch name provided. Exiting.")
                return

        new_branch_id = project.create_branch(branch_name)
        if new_branch_id:
            success(f"Branch '{branch_name}' created (ID: {new_branch_id})")
        else:
            error("Failed to create the branch.")

    @classmethod
    def branch_switch(
        cls, base_path: str, branch_name: str = None, force: bool = False, format: bool = False
    ) -> None:
        """Switch to a different branch in the Agent Studio project."""
        project = cls._load_project(base_path)

        if not branch_name:
            # Drop down menu to select branch
            current_branch, branches = project.get_branches()
            if not branches:
                plain("[muted]No branches found.[/muted]")
                return

            # Create menu options from branch names
            menu_options = []
            for name in branches.keys():
                if name == current_branch:
                    menu_options.append(f"{name} (current)")
                else:
                    menu_options.append(name)

            branch_menu = questionary.select(
                "Select Branch", choices=menu_options, use_search_filter=True, use_jk_keys=False
            ).ask()
            if not branch_menu:
                warning("No branch selected. Exiting.")
                return

            # Get the selected branch name (remove "(current)" suffix if present)
            selected_option = branch_menu
            branch_name = selected_option.replace(" (current)", "")

        switch_ok = project.switch_branch(branch_name, force=force, format=format)
        if switch_ok:
            success(f"Switched to branch '{branch_name}'.")
        else:
            error(f"Failed to switch to branch '{branch_name}'.")

    @classmethod
    def get_current_branch(cls, base_path: str) -> None:
        """Get the current branch of the Agent Studio project."""
        project = cls._load_project(base_path)

        current_branch = project.get_current_branch()
        if current_branch is None:
            warning(
                f"Current local branch '{project.branch_id}' does not exist in Agent Studio. "
                "It may have been deleted or merged."
            )
            return
        plain(f"Current branch: [bold]{current_branch}[/bold]")

    @classmethod
    def format(
        cls,
        base_path: str,
        files: list[str] = None,
        check_only: bool = False,
        run_ty: bool = False,
    ) -> None:
        """Format project resources (Python via ruff, YAML/JSON via in-process formatting); optionally run ty."""
        project = cls._load_project(base_path)
        # Resolve to absolute paths so they match resource_mapping.file_path
        files_resolved: list[str] | None = None
        if files:
            files_resolved = [os.path.abspath(os.path.join(base_path, f)) for f in files]

        if check_only:
            info("[bold]Check-only[/bold]: verifying formatting (no files will be modified).")
        else:
            info("[bold]Fix mode[/bold]: formatting project resources.")

        plain("")

        step = (
            "Checking project resources (Python + YAML/JSON)"
            if check_only
            else "Formatting project resources (Python + YAML/JSON)"
        )
        info(step)
        affected, format_errors = project.format_files(files=files_resolved, check_only=check_only)
        for msg in format_errors:
            plain(f"[red]{msg}[/red]")
        if format_errors:
            error("Format failed for some files.")
            sys.exit(1)
            return
        if check_only and affected:
            for path in affected:
                rel = os.path.relpath(path, base_path) or path
                plain(f"[red]{rel}[/red]")
            info("Try [bold]poly format[/bold] to fix.")
            sys.exit(1)
            return
        for path in affected:
            rel = os.path.relpath(path, base_path) or path
            plain(rel)
        success("Passed.")
        if check_only:
            success("All checks passed (no changes written).")
        else:
            success("All issues fixed." if affected else "No issues found.")

        # Ty (type check only; no fix) — off by default; use --ty to enable.
        if run_ty:
            ty_cmd = [sys.executable, "-m", "ty"]
            if shutil.which("ty"):
                ty_cmd = ["ty"]
            info("Type checking (ty)")
            try:
                r = subprocess.run(
                    ty_cmd + ["check"],
                    cwd=base_path,
                    capture_output=False,
                    text=True,
                    timeout=15,
                    stdin=subprocess.DEVNULL,
                )
            except subprocess.TimeoutExpired:
                plain("[red]Timed out after 15s.[/red]")
                sys.exit(1)
                return
            if r.returncode != 0:
                sys.exit(1)
                return
            success("Passed.")

    @classmethod
    def chat(
        cls,
        base_path: str,
        environment: str = None,
        variant: str = None,
        channel: str = None,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
    ) -> None:
        """Start an interactive chat session with the agent."""
        project = cls._load_project(base_path)
        branch_id = project.branch_id
        branch_label = None

        if environment == "branch":
            if branch_id and branch_id != "main":
                branch_label = project.get_current_branch() or branch_id
                environment = "draft" if branch_label != "main" else "sandbox"
            else:
                environment = "sandbox"
        else:
            environment = environment or "sandbox"

        channel_map = {"voice": "chat.polyai", "webchat": "webchat.polyai"}
        channel = channel_map.get(channel, "chat.polyai")

        label = f"[bold]{project.account_id}/{project.project_id}[/bold]"
        if branch_label:
            label += f" branch=[bold]{branch_label}[/bold]"
        else:
            label += f" ({environment})"
        if variant:
            label += f" variant=[bold]{variant}[/bold]"
        info(f"Starting chat for {label}...")

        while True:
            if environment == "draft":
                info("Preparing branch deployment...")
            try:
                response = project.create_chat_session(
                    environment,
                    channel,
                    variant,
                )
            except (requests.HTTPError, ValueError) as e:
                error(f"Failed to create chat session: {e}")
                return

            conversation_id = response.get("conversation_id")
            if not conversation_id:
                error(f"Unexpected response when creating chat: {response}")
                return

            url = project.get_conversation_url(conversation_id)
            success(f"Chat session started (conversation: [link={url}]{conversation_id}[/link])")
            print_turn_metadata(response, show_functions, show_flow, show_state)
            greeting = response.get("response", "")
            if greeting:
                plain(f"\n[bold]Agent:[/bold] {greeting}")

            if response.get("conversation_ended"):
                plain("[muted]Conversation ended by agent.[/muted]")
                return

            plain(
                "[muted]Type your messages below. "
                "Press Ctrl+C or type '/exit' to quit. "
                "Type '/restart' to begin a new chat.[/muted]"
            )

            restart = cls._run_chat_loop(
                project,
                conversation_id,
                environment,
                show_functions=show_functions,
                show_flow=show_flow,
                show_state=show_state,
            )

            if not restart:
                return

            info("Restarting chat session...")

    @classmethod
    def _run_chat_loop(
        cls,
        project: AgentStudioProject,
        conversation_id: str,
        environment: str,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
    ) -> bool:
        """Run the interactive message loop.

        Returns:
            True if the user requested a restart, False otherwise.
        """
        conversation_ended = False
        restart = False
        try:
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                except (KeyboardInterrupt, EOFError):
                    plain("")
                    break

                if not user_input:
                    continue
                if user_input.lower() == "/exit":
                    break
                if user_input.lower() == "/restart":
                    restart = True
                    break

                try:
                    reply = project.send_message(
                        conversation_id,
                        user_input,
                        environment,
                    )
                except requests.HTTPError as e:
                    error(f"Failed to send message: {e}")
                    continue

                print_turn_metadata(reply, show_functions, show_flow, show_state)
                agent_text = reply.get("response") or json.dumps(reply, indent=2)
                plain(f"\n[bold]Agent:[/bold] {agent_text}")

                if reply.get("conversation_ended"):
                    conversation_ended = True
                    plain("[muted]Conversation ended by agent.[/muted]")
                    break
        finally:
            if not conversation_ended:
                try:
                    project.end_chat(conversation_id, environment)
                    info(f"Chat session ended (conversation: {conversation_id})")
                    url = project.get_conversation_url(conversation_id)
                    plain(f"[info]Call Link:[/info] [link={url}]{url}[/link]")
                except requests.HTTPError:
                    warning("Failed to end chat session on server.")

        return restart

    @classmethod
    def validate_project(cls, base_path: str, json_output: bool = False) -> None:
        """Validate the project configuration locally."""
        project = cls._load_project(base_path)

        errors = project.validate_project()

        if json_output:
            parsed_errors = []
            for err in errors:
                parts = err.split(": ", 1)
                if len(parts) == 2 and parts[0].startswith("Validation error in "):
                    file_path = parts[0].removeprefix("Validation error in ")
                    parsed_errors.append({"file": file_path, "message": err})
                else:
                    parsed_errors.append({"file": None, "message": err})
            json_print({"valid": len(errors) == 0, "errors": parsed_errors})
            if errors:
                sys.exit(1)
            return

        if not errors:
            success("Project configuration is valid.")
        else:
            print_validation_errors(errors)
            sys.exit(1)

    @classmethod
    def docs(
        cls,
        documents: list[str] = None,
        all_documents: bool = False,
        output: Optional[str] = None,
    ) -> None:
        """Generate documentation for the project."""
        parts: list[str] = []
        if not documents and not all_documents:
            parts.append(AgentStudioProject.load_docs("docs"))
        if all_documents:
            parts.append(AgentStudioProject.load_docs("docs"))
            parts.extend([AgentStudioProject.load_docs(doc) for doc in DOCUMENT_CHOICES])
        else:
            parts.extend([AgentStudioProject.load_docs(doc) for doc in documents])

        content: str = "\n\n".join(parts)

        if output:
            output_path = os.path.abspath(output)
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            success(f"Documentation written to {output_path}")
        else:
            plain(content)


def main():
    """Entry point for the CLI tool."""
    AgentStudioCLI.main()
