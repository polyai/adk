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
import webbrowser
from argparse import SUPPRESS, ArgumentParser, RawTextHelpFormatter
from contextlib import nullcontext
from importlib.metadata import version as get_package_version
from typing import Any, Optional
from xml.parsers.expat import errors

import argcomplete
import requests
import questionary
import traceback

from poly.output.console import (
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
from poly.output.json_output import json_print, commands_to_dicts
from poly.handlers.github_api_handler import GitHubAPIHandler
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


def _format_gist_choice(g: dict) -> str:
    """Format a gist dict as a human-readable choice label."""
    id_hint = g["id"][:7]
    date = g.get("created_at", "")[:10]  # YYYY-MM-DD
    parts = [p for p in [date, id_hint, g["description"]] if p]
    return "  ".join(parts)


class AgentStudioCLI:
    """CLI Interface for Agent Studio."""

    @classmethod
    def _branch_name_completer(
        cls,
        prefix: str,
        action: Any = None,
        parser: Any = None,
        parsed_args: Any = None,
        **kwargs: Any,
    ) -> list[str]:
        """Return deletable branch names for argcomplete tab-completion."""
        try:
            base_path = getattr(parsed_args, "path", None) or os.getcwd()
            project = cls.read_project_config(base_path)
            if project is None:
                return []
            _, branches = project.get_branches()
            return [name for name in branches if name != "main" and name.startswith(prefix)]
        except Exception:
            return []

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

        json_parent = ArgumentParser(add_help=False)
        json_parent.add_argument(
            "--json",
            action="store_true",
            help="Print a single JSON object on stdout (machine-readable).",
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
            parents=[verbose_parent, json_parent],
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
        init_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        init_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help=SUPPRESS,
            default=False,
        )
        init_parser.add_argument("--debug", action="store_true", help="Display debug logs.")

        # PULL
        pull_parser = subparsers.add_parser(
            "pull",
            parents=[verbose_parent, json_parent],
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
        pull_parser.add_argument("--debug", action="store_true", help="Display debug logs.")

        # PUSH
        push_parser = subparsers.add_parser(
            "push",
            parents=[verbose_parent, json_parent],
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
            "--email",
            type=str,
            help="Email to use for metadata creation for push",
            default=None,
        )

        # STATUS
        status_parser = subparsers.add_parser(
            "status",
            parents=[verbose_parent, json_parent],
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

        # REVERT
        revert_parser = subparsers.add_parser(
            "revert",
            parents=[verbose_parent, json_parent],
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
            parents=[verbose_parent, json_parent],
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

        # REVIEW
        review_parser = subparsers.add_parser(
            "review",
            parents=[verbose_parent, json_parent],
            help="Create a GitHub Gist of Agent Studio project changes to share changes.",
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
                "  poly review list\n"
                "  poly review list --json\n"
                "  poly review delete\n"
                "  poly review delete --id GIST_ID\n"
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
            help="Name of the original branch or version to compare against.",
        )
        review_parser.add_argument(
            "--after",
            type=str,
            help="Name of the branch or version to compare with.",
        )
        review_parser.set_defaults(review_subcommand=None)
        review_subparsers = review_parser.add_subparsers(dest="review_subcommand")

        review_list_parser = review_subparsers.add_parser(
            "list",
            parents=[json_parent],
            help="Interactively select a review gist to open in the browser.",
        )
        review_list_parser.set_defaults(review_subcommand="list")

        review_delete_parser = review_subparsers.add_parser(
            "delete",
            parents=[json_parent],
            help="Interactively select and delete review gists.",
        )
        review_delete_parser.add_argument(
            "--id",
            type=str,
            default=None,
            metavar="GIST_ID",
            help="Gist ID (or first 7 characters) to delete directly, skipping the interactive prompt.",
        )
        review_delete_parser.set_defaults(review_subcommand="delete")

        # Branch
        branch_path_parent = ArgumentParser(add_help=False)
        branch_path_parent.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        branches_parser = subparsers.add_parser(
            "branch",
            parents=[verbose_parent],
            help="Manage branches in the Agent Studio project.",
            description=(
                "Manage branches in the Agent Studio project.\n\n"
                "Examples:\n"
                "  poly branch list\n"
                "  poly branch create new-branch\n"
                "  poly branch switch existing-branch\n"
                "  poly branch current\n"
                "  poly branch delete\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        branch_subparsers = branches_parser.add_subparsers(dest="branch_subcommand", required=True)

        branch_list_parser = branch_subparsers.add_parser(
            "list",
            parents=[branch_path_parent, json_parent],
            help="List all branches in the project.",
        )
        branch_list_parser.set_defaults(branch_subcommand="list")

        branch_create_parser = branch_subparsers.add_parser(
            "create",
            parents=[branch_path_parent, json_parent],
            help="Create a new branch.",
        )
        branch_create_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to create."
        )
        branch_create_parser.add_argument(
            "--env",
            "--environment",
            type=str,
            choices=["sandbox", "pre-release", "live"],
            default=None,
            dest="environment",
            help="Initiate the new branch from this environment instead of sandbox (main).",
        )
        branch_create_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force switch to a different branch/create new branch and discard changes.",
        )
        branch_create_parser.set_defaults(branch_subcommand="create")

        branch_switch_parser = branch_subparsers.add_parser(
            "switch",
            parents=[branch_path_parent, json_parent],
            help="Switch to a different branch.",
        )
        branch_switch_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to switch to."
        )
        branch_switch_parser.add_argument(
            "--debug", action="store_true", help="Display debug logs."
        )
        branch_switch_parser.add_argument(
            "--format",
            action="store_true",
            help="Format the project after switching branches.",
        )
        branch_switch_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Force switch to a different branch and discard changes.",
        )
        branch_switch_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        branch_switch_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help="Output the projection in json format",
            default=False,
        )
        branch_switch_parser.set_defaults(branch_subcommand="switch")

        branch_current_parser = branch_subparsers.add_parser(
            "current",
            parents=[branch_path_parent, json_parent],
            help="Show the current branch.",
        )
        branch_current_parser.set_defaults(branch_subcommand="current")

        branch_delete_parser = branch_subparsers.add_parser(
            "delete",
            parents=[branch_path_parent, json_parent],
            help="Interactively select and delete a branch.",
        )
        branch_delete_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Name of the branch to delete directly, skipping the interactive prompt.",
        ).completer = cls._branch_name_completer
        branch_delete_parser.set_defaults(branch_subcommand="delete")

        # FORMAT
        format_parser = subparsers.add_parser(
            "format",
            parents=[verbose_parent, json_parent],
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
            parents=[verbose_parent, json_parent],
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

        # CHAT
        chat_parser = subparsers.add_parser(
            "chat",
            parents=[verbose_parent, json_parent],
            help="Start an interactive chat session with the agent.",
            description=(
                "Start an interactive chat session with the agent.\n\n"
                "Examples:\n"
                "  poly chat\n"
                "  poly chat --environment live\n"
                "  poly chat --path /path/to/project -e sandbox\n"
                "\n"
                "Non-interactive (scripted) mode:\n"
                "  poly chat -m 'Hello' -m 'What can you help with?'\n"
                "  poly chat --input-file ./script.txt\n"
                "  echo -e 'Hello\\nGoodbye' | poly chat --input-file -\n"
                "\n"
                "Resume an existing conversation:\n"
                "  poly chat --conv-id <conversation_id>\n"
                "  poly chat --conv-id <conversation_id> -m 'Follow-up message'\n"
                "\n"
                "Machine-readable output (emits a single JSON object when done):\n"
                "  poly chat --json -m 'Hello'\n"
                "  poly chat --json --input-file ./script.txt\n"
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
        chat_parser.add_argument(
            "--push",
            action="store_true",
            default=False,
            help="Push the project before starting the chat session.",
        )
        chat_parser.add_argument(
            "--message",
            "-m",
            action="append",
            dest="messages",
            metavar="MSG",
            help="Send a message non-interactively (repeatable).",
        )
        chat_parser.add_argument(
            "--input-file",
            type=str,
            default=None,
            metavar="FILE",
            help="Read messages line-by-line from a file (- for stdin).",
        )
        chat_parser.add_argument(
            "--conversation-id",
            "--conv-id",
            type=str,
            default=None,
            help="Conversation ID for the chat session. If a current session, chats with that conversation",
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

        try:
            if args.command == "init":
                cls.init_project(
                    args.base_path,
                    args.region,
                    args.account_id,
                    args.project_id,
                    args.format,
                    args.from_projection,
                    output_json=args.json,
                    output_json_projection=args.output_json_projection,
                )

            elif args.command == "pull":
                cls.pull(
                    args.path,
                    args.force,
                    args.format,
                    args.from_projection,
                    output_json=args.json,
                    output_json_projection=args.output_json_projection,
                )

            elif args.command == "push":
                cls.push(
                    args.path,
                    args.force,
                    args.skip_validation,
                    args.dry_run,
                    args.format,
                    args.email,
                    args.from_projection,
                    output_json=args.json,
                    output_commands=args.output_json_commands,
                )

            elif args.command == "status":
                cls.status(args.path, args.json)

            elif args.command == "revert":
                cls.revert(args.path, args.all, args.files, output_json=args.json)

            elif args.command == "diff":
                cls.diff(args.path, args.files, args.json)

            elif args.command == "chat":
                show_all = args.metadata
                input_messages = None
                if args.input_file:
                    try:
                        src = sys.stdin if args.input_file == "-" else open(args.input_file)
                    except FileNotFoundError:
                        error(f"Input file not found: {args.input_file}")
                        sys.exit(1)
                    with src:
                        input_messages = [line.rstrip("\n") for line in src if line.strip()]
                elif args.messages:
                    input_messages = args.messages
                cls.chat(
                    args.path,
                    args.environment,
                    args.variant,
                    args.channel,
                    show_functions=show_all or args.functions,
                    show_flow=show_all or args.flows,
                    show_state=show_all or args.state,
                    push_before_chat=args.push,
                    input_messages=input_messages,
                    conversation_id=args.conversation_id,
                    output_json=args.json,
                )

            elif args.command == "review":
                if args.review_subcommand == "delete":
                    cls.delete_gists(gist_id=args.id, output_json=args.json)
                elif args.review_subcommand == "list":
                    cls.list_gists(output_json=args.json)
                else:
                    if args.before and args.after:
                        cls.review(
                            base_path=args.path,
                            before_name=args.before,
                            after_name=args.after,
                            output_json=args.json,
                        )
                    else:
                        cls.review(args.path, output_json=args.json)

            elif args.command == "branch":
                if args.branch_subcommand == "list":
                    cls.branch_list(args.path, args.json)

                elif args.branch_subcommand == "create":
                    cls.branch_create(
                        args.path,
                        args.branch_name,
                        args.json,
                        getattr(args, "environment", None),
                        getattr(args, "force", False),
                    )

                elif args.branch_subcommand == "switch":
                    cls.branch_switch(
                        args.path,
                        args.branch_name,
                        getattr(args, "force", False),
                        getattr(args, "format", False),
                        args.json,
                        output_json_projection=args.output_json_projection,
                        from_projection=args.from_projection,
                    )

                elif args.branch_subcommand == "current":
                    cls.get_current_branch(args.path, args.json)

                elif args.branch_subcommand == "delete":
                    cls.branch_delete(args.path, args.branch_name, args.json)

            elif args.command == "format":
                cls.format(
                    args.path,
                    args.files,
                    getattr(args, "check", False),
                    getattr(args, "ty", False),
                    output_json=args.json,
                )

            elif args.command == "validate":
                cls.validate_project(args.path, args.json)

            elif args.command == "docs":
                cls.docs(
                    documents=args.documents,
                    all_documents=getattr(args, "all", False),
                    output=getattr(args, "output", None),
                )

            elif args.command == "completion":
                cls.print_completion(args.shell)

        except Exception as e:
            if hasattr(args, "json") and args.json:
                json_print({"success": False, "error": str(e), "traceback": traceback.format_exc()})
                sys.exit(1)
            else:
                raise

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
        argcomplete.autocomplete(parser, always_complete_options=False)

        try:
            if sys_args:
                args = parser.parse_args(args=sys_args)
            else:
                args = parser.parse_args()

            set_verbose(getattr(args, "verbose", False))
            cls._run_command(args)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            plain("\nAborted.")
            sys.exit(130)
        except Exception as e:
            handle_exception(e)

    @staticmethod
    def _parse_from_projection_json(
        from_projection: Optional[str],
        *,
        json_errors: bool,
    ) -> Optional[dict[str, Any]]:
        """Parse ``--from-projection`` CLI value into a projection dict, or exit on failure.

        If the value is ``-`` (after stripping), JSON is read from stdin until EOF.
        """
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

    @classmethod
    def _load_project(cls, base_path: str, output_json: bool = False) -> AgentStudioProject:
        """Read project config or exit with a helpful error if not found.

        Args:
            base_path: Path to the project directory.
            output_json: If True, print JSON and exit when config is missing.
        """
        project = cls.read_project_config(base_path)
        if not project:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "No project configuration found. Run poly init to initialize a project.",
                    }
                )
                sys.exit(1)
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
        from_projection: str = None,
        output_json: bool = False,
        output_json_projection: bool = False,
    ) -> None:
        """Initialize a new Agent Studio project."""
        if output_json and not (region and account_id and project_id):
            json_print(
                {
                    "success": False,
                    "error": "init with --json requires --region, --account_id, and --project_id.",
                }
            )
            sys.exit(1)

        if not output_json:
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
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No account selected.",
                        }
                    )
                    sys.exit(1)
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
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No project selected.",
                        }
                    )
                    sys.exit(1)
                warning("No project selected. Exiting.")
                return
            project_id = projects[project_menu]

        if not output_json:
            info(f"Initializing project [bold]{account_id}/{project_id}[/bold]...")

        projection_json = cls._parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        ctx = (
            console.status("[info]Saving resources...[/info]") if not output_json else nullcontext()
        )
        on_save = None

        with ctx as status:
            if status:

                def on_save(current: int, total: int) -> None:
                    status.update(f"[info]Saving resources ({current}/{total})...[/info]")

            project, projection = AgentStudioProject.init_project(
                base_path=base_path,
                region=region,
                account_id=account_id,
                project_id=project_id,
                format=format,
                projection_json=projection_json,
                on_save=on_save,
            )

        if not project:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "Failed to initialize the project.",
                    }
                )
            else:
                error("Failed to initialize the project.")
            sys.exit(1)

        if output_json or output_json_projection:
            json_output = {
                "success": True,
                "root_path": project.root_path,
            }
            if output_json_projection:
                json_output["projection"] = projection
            json_print(json_output)
        else:
            success(f"Project initialized at {project.root_path}")

    @classmethod
    def pull(
        cls,
        base_path: str,
        force: bool = False,
        format: bool = False,
        from_projection: str = None,
        output_json: bool = False,
        output_json_projection: bool = False,
    ) -> None:
        """Pull the latest project configuration from the Agent Studio."""
        project = cls._load_project(base_path, output_json=output_json)
        if not output_json:
            info(f"Pulling project [bold]{project.account_id}/{project.project_id}[/bold]...")

        projection_json = cls._parse_from_projection_json(
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
            json_print(json_output)
            if files_with_conflicts:
                sys.exit(1)
            return

        if new_branch_name:
            warning(
                f"Current branch no longer exists in Agent Studio. Switched to branch '{new_branch_name}'."
            )
        if files_with_conflicts:
            print_file_list("Merge conflicts detected", files_with_conflicts, "filename.conflict")

        success(f"Pulled {project.account_id}/{project.project_id}")

    @classmethod
    def push(
        cls,
        base_path: str,
        force: bool = False,
        skip_validation: bool = False,
        dry_run: bool = False,
        format: bool = False,
        email: Optional[str] = None,
        from_projection: str = None,
        output_json: bool = False,
        output_commands: bool = False,
    ) -> None:
        """Push the project configuration to the Agent Studio."""
        project = cls._load_project(base_path, output_json=output_json)
        if not output_json and not output_commands:
            info(
                f"Pushing local changes for [bold]{project.account_id}/{project.project_id}[/bold]..."
            )

        projection_json = cls._parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_commands,
        )

        original_branch_id = project.branch_id
        push_ok, output, commands = project.push_project(
            force=force,
            skip_validation=skip_validation,
            dry_run=dry_run,
            format=format,
            email=email,
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
            json_print(json_output)
            if not push_ok:
                sys.exit(1)
            return

        if new_branch_name:
            warning(f"Created and switched to new branch '{new_branch_name}'.")
        if push_ok:
            success(f"Pushed {project.account_id}/{project.project_id} to Agent Studio.")
        else:
            error(f"Failed to push {project.account_id}/{project.project_id} to Agent Studio.")
            plain(output)

    @classmethod
    def status(cls, base_path: str, output_json: bool = False) -> None:
        """Check the changed files of the project."""
        project = cls._load_project(base_path, output_json=output_json)

        files_with_conflicts, modified_files, new_files, deleted_files = project.project_status()

        if output_json:
            json_output = {
                "files_with_conflicts": files_with_conflicts,
                "modified_files": modified_files,
                "new_files": new_files,
                "deleted_files": deleted_files,
            }
            json_print(json_output)
            return

        branch_info = project.get_current_branch()

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
    def revert(
        cls,
        base_path: str,
        all_files: bool = False,
        files: list[str] = None,
        output_json: bool = False,
    ) -> None:
        """Revert changes in the project."""
        if not all_files and not files:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "No files specified to revert. Use --all or list files.",
                    }
                )
                sys.exit(1)
            error("No files specified to revert. Use [bold]--all[/bold] to revert all changes.")
            return

        project = cls._load_project(base_path, output_json=output_json)

        # If relative paths are provided, convert them to absolute paths
        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        files_reverted = project.revert_changes(all_files=all_files, files=files)
        if output_json:
            json_print(
                {
                    "success": bool(files_reverted),
                    "files_reverted": files_reverted,
                }
            )
            return

        if not files_reverted:
            plain("[muted]No changes to revert.[/muted]")
            return

        success("Changes reverted successfully.")

    @classmethod
    def _diff(
        cls, base_path: str, files: list[str] = None, output_json: bool = False
    ) -> dict[str, str]:
        """Compute local diffs; may print a human hint when there are no changes."""

        project = cls._load_project(base_path, output_json=output_json)

        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        diffs = project.get_diffs(all_files=not files, files=files) or {}

        if not diffs and not output_json:
            plain("[muted]No changes detected.[/muted]")

        return diffs

    @classmethod
    def diff(cls, base_path: str, files: list[str] = None, output_json: bool = False) -> None:
        """Show the changes made to the project."""
        diffs = cls._diff(base_path, files, output_json=output_json)
        if output_json:
            json_print(
                {
                    "diffs": diffs,
                }
            )
            return

        if not diffs:
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
            diffs = cls._diff(base_path)

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
        output_json: bool = False,
    ) -> None:
        """Show the changes made to the project in a Pull Request format.
        Args:
            base_path: Base path for the project (used to read project config)
            before_name: Optional name of base branch (for comparing two remote branches)
            after_name: Optional name of compare branch (for comparing two remote branches)
            output_json: If True, print result as a JSON object instead of rich text
        """
        project_name = "/".join(os.path.abspath(base_path).split(os.sep)[-2:])
        if before_name and after_name:
            body = cls._review(
                base_path=base_path,
                before_name=before_name,
                after_name=after_name,
            )
            description = f"Poly ADK: {project_name}: {before_name} → {after_name}"
        else:
            body = cls._review(base_path)
            description = f"Poly ADK: {project_name}: local → remote"

        if not body:
            if output_json:
                json_print({"success": False, "message": "No changes to review."})
            return

        try:
            url = GitHubAPIHandler.create_gist(
                files=body,
                description=description,
                public=False,
            )
            if output_json:
                json_print({"success": True, "link": url})
            else:
                success(f"Gist created: {url}")
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))

    @classmethod
    def list_gists(cls, output_json: bool = False) -> None:
        """Interactively select a review gist and open it in the browser."""
        try:
            gists = GitHubAPIHandler.list_diff_gists()
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
            return
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))
            return

        if output_json:
            json_print(gists)
            return

        if not gists:
            plain("[muted]No review gists found.[/muted]")
            return

        url_by_choice = {_format_gist_choice(g): g["html_url"] for g in gists}
        selected = questionary.select("Select a gist to open", choices=list(url_by_choice)).ask()
        if not selected:
            return

        webbrowser.open(url_by_choice[selected])

    @classmethod
    def delete_gists(cls, gist_id: Optional[str] = None, output_json: bool = False) -> None:
        """Interactively select and delete review gists from the user's GitHub account.

        If gist_id is provided (full ID or first 7 characters), delete that specific gist
        without an interactive prompt.
        """
        try:
            gists = GitHubAPIHandler.list_diff_gists()
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
            return
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))
            return

        if gist_id:
            matched = next(
                (g for g in gists if g["id"].startswith(gist_id)),
                None,
            )
            if not matched:
                if output_json:
                    json_print(
                        {"success": False, "message": f"No review gist found matching '{gist_id}'."}
                    )
                else:
                    error(f"No review gist found matching '{gist_id}'.")
                return
            try:
                GitHubAPIHandler.delete_gist(matched["id"])
            except requests.HTTPError as e:
                if output_json:
                    json_print({"success": False, "message": f"GitHub API error: {e}"})
                else:
                    error(f"GitHub API error: {e}")
                return
            except OSError as e:
                if output_json:
                    json_print({"success": False, "message": str(e)})
                else:
                    error(str(e))
                return
            if output_json:
                json_print({"success": True})
            else:
                success(f"Deleted gist: {matched['id']}")
            return

        if not gists:
            plain("[muted]No review gists found.[/muted]")
            return

        choices = [_format_gist_choice(g) for g in gists]
        description_to_id = {_format_gist_choice(g): g["id"] for g in gists}

        selected = questionary.checkbox("Select gists to delete", choices=choices).ask()
        if not selected:
            warning("No gists selected. Exiting.")
            return

        try:
            for description in selected:
                gist_id = description_to_id[description]
                GitHubAPIHandler.delete_gist(gist_id)
                if not output_json:
                    plain(f"  [muted]Deleted gist:[/muted] {description}")
            if output_json:
                json_print({"success": True})
            else:
                success(f"Deleted {len(selected)} gist(s).")
        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "message": f"GitHub API error: {e}"})
            else:
                error(f"GitHub API error: {e}")
        except OSError as e:
            if output_json:
                json_print({"success": False, "message": str(e)})
            else:
                error(str(e))

    @classmethod
    def branch_list(cls, base_path: str, output_json: bool = False) -> None:
        """List branches in the Agent Studio project."""
        project = cls._load_project(base_path, output_json=output_json)

        current_branch, branches = project.get_branches()

        if output_json:
            json_output = {
                "current_branch": current_branch,
                "branches": branches,
            }
            json_print(json_output)
            return

        if not branches:
            plain("[muted]No branches found.[/muted]")
            return

        print_branches(branches, current_branch)

        if current_branch is None:
            warning(
                f"Current local branch does not exist in Agent Studio. "
                "It may have been deleted or merged."
            )

    @classmethod
    def branch_create(
        cls,
        base_path: str,
        branch_name: str = None,
        output_json: bool = False,
        env: str = None,
        force: bool = False,
    ) -> None:
        """Create a new branch in the Agent Studio project."""
        project = cls._load_project(base_path, output_json=output_json)

        if project.branch_id != "main":
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "Branches can only be created from the main branch (sandbox).",
                    }
                )
            else:
                error(
                    "Branches can only be created from the [bold]main[/bold] branch (sandbox). "
                    "Please switch and try again."
                )
            sys.exit(1)

        if env in ["pre-release", "live"]:
            # Checks for any local changes on main before creating env branch.
            if diffs := project.get_diffs(all_files=True):
                if not force:
                    raise ValueError(
                        f"Uncommitted changes on main branch, diffs: {list(diffs.keys())}"
                    )
            project.pull_project_from_env(env=env, format=False)
            success(f"Pulled {project.account_id}/{project.project_id}")

        if not branch_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "branch create with --json requires a branch name argument.",
                    }
                )
                sys.exit(1)
            branch_name = input("Enter the name of the new branch: ").strip()
            if not branch_name:
                warning("No branch name provided. Exiting.")
                return

        new_branch_id = project.create_branch(branch_name)
        if output_json:
            json_print(
                {
                    "success": bool(new_branch_id),
                    "new_branch_id": new_branch_id,
                    "branch_name": branch_name,
                }
            )
            if not new_branch_id:
                sys.exit(1)
            return

        if new_branch_id:
            success(f"Branch '{branch_name}' created (ID: {new_branch_id})")
        else:
            error("Failed to create the branch.")
            sys.exit(1)

        # Pushes existing state of env to provide clean slate for hotfixes.
        if env in ["pre-release", "live"]:
            project.push_project(
                force=True,
                skip_validation=True,
                dry_run=False,
                format=False,
                email=None,
            )

    @classmethod
    def branch_switch(
        cls,
        base_path: str,
        branch_name: str = None,
        force: bool = False,
        format: bool = False,
        output_json: bool = False,
        output_json_projection: bool = False,
        from_projection: str = None,
    ) -> None:
        """Switch to a different branch in the Agent Studio project."""
        project = cls._load_project(base_path, output_json=output_json)

        if not branch_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "branch switch with --json requires a branch name argument.",
                    }
                )
                sys.exit(1)
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

        projection_json = cls._parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        ctx = (
            console.status("[info]Saving resources...[/info]") if not output_json else nullcontext()
        )
        on_save = None

        with ctx as status:
            if status:

                def on_save(current: int, total: int) -> None:
                    status.update(f"[info]Saving resources ({current}/{total})...[/info]")

            switch_ok, projection = project.switch_branch(
                branch_name,
                force=force,
                format=format,
                projection_json=projection_json,
                on_save=on_save,
            )

        if output_json or output_json_projection:
            json_output = {
                "success": switch_ok,
                "branch_name": branch_name,
            }
            if output_json_projection:
                json_output["projection"] = projection
            json_print(json_output)
            if not switch_ok:
                sys.exit(1)
            return

        if switch_ok:
            success(f"Switched to branch '{branch_name}'.")
        else:
            error(f"Failed to switch to branch '{branch_name}'.")
            sys.exit(1)

    @classmethod
    def get_current_branch(cls, base_path: str, output_json: bool = False) -> None:
        """Get the current branch of the Agent Studio project."""
        project = cls._load_project(base_path, output_json=output_json)

        current_branch = project.get_current_branch()
        if output_json:
            json_output = {
                "current_branch": current_branch,
            }
            json_print(json_output)
            return

        if current_branch is None:
            warning(
                f"Current local branch does not exist in Agent Studio. "
                "It may have been deleted or merged."
            )
            return
        plain(f"Current branch: [bold]{current_branch}[/bold]")

    @classmethod
    def branch_delete(
        cls,
        base_path: str,
        branch_name: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Interactively select and delete a branch from the Agent Studio project.

        If branch_name is provided, delete that specific branch without an interactive prompt.
        """
        project = cls._load_project(base_path, output_json=output_json)
        current_branch, branches = project.get_branches()

        # Filter out 'main' — it cannot be deleted
        deletable = {name: bid for name, bid in branches.items() if name != "main"}

        if branch_name:
            if branch_name not in deletable:
                msg = f"Branch '{branch_name}' does not exist or cannot be deleted."
                if output_json:
                    json_print({"success": False, "message": msg})
                else:
                    error(msg)
                return
            if not output_json:
                confirmed = questionary.confirm(
                    f"Delete branch '{branch_name}'?", default=False
                ).ask()
                if not confirmed:
                    warning("Aborted.")
                    return
            try:
                deleted = project.delete_branch(branch_name)
            except (ValueError, Exception) as e:
                if output_json:
                    json_print({"success": False, "message": str(e)})
                else:
                    error(str(e))
                return
            if output_json:
                result = {"success": deleted}
                if deleted and branch_name == current_branch:
                    result["switched_to"] = "main"
                json_print(result)
            else:
                if deleted:
                    success(f"Deleted branch: {branch_name}")
                    if branch_name == current_branch:
                        info("Switched to branch 'main'.")
                else:
                    error(f"Failed to delete branch '{branch_name}'.")
            return

        if not deletable:
            plain("[muted]No deletable branches found.[/muted]")
            return

        choices = []
        for name in deletable:
            label = f"{name} (current)" if name == current_branch else name
            choices.append(label)

        selected = questionary.checkbox("Select branches to delete", choices=choices).ask()
        if not selected:
            warning("No branches selected. Exiting.")
            return

        branch_names = [label.replace(" (current)", "") for label in selected]
        confirm_msg = f"Delete {len(branch_names)} branch(es): {', '.join(branch_names)}?"
        confirmed = questionary.confirm(confirm_msg, default=False).ask()
        if not confirmed:
            warning("Aborted.")
            return

        deleted_count = 0
        current_branch_deleted = False
        for label in selected:
            name = label.replace(" (current)", "")
            try:
                deleted = project.delete_branch(name)
                if deleted:
                    deleted_count += 1
                    if name == current_branch:
                        current_branch_deleted = True
                    if not output_json:
                        plain(f"  [muted]Deleted branch:[/muted] {name}")
                        if name == current_branch:
                            info("Switched to branch 'main'.")
                else:
                    if not output_json:
                        error(f"Failed to delete branch '{name}'.")
            except (ValueError, Exception) as e:
                if not output_json:
                    error(str(e))

        if output_json:
            result = {"success": deleted_count > 0, "deleted": deleted_count}
            if current_branch_deleted:
                result["switched_to"] = "main"
            json_print(result)
        else:
            if deleted_count:
                success(f"Deleted {deleted_count} branch(es).")

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
        project = cls._load_project(base_path, output_json=output_json)
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

    @classmethod
    def chat(
        cls,
        base_path: str,
        environment: str = None,
        variant: str = None,
        channel: str = None,
        push_before_chat: bool = False,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
        output_json: bool = False,
        input_messages: Optional[list[str]] = None,
        conversation_id: str = None,
    ) -> None:
        """Start an interactive chat session with the agent."""
        project = cls._load_project(base_path)

        if push_before_chat:
            if not output_json:
                info("Pushing project before starting chat session...")
            push_success, output, _ = project.push_project(
                force=False,
                skip_validation=False,
                dry_run=False,
                format=False,
                email=None,
            )
            if output == "No changes detected":
                push_success = True  # Not an error if there are no changes to push

            if push_success and not output_json:
                success("Project pushed successfully.")

            if not push_success:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "message": "Failed to push project before chat session.",
                            "error": error,
                        }
                    )
                else:
                    error(
                        f"Failed to push {project.account_id}/{project.project_id} to Agent Studio."
                    )
                    plain(output)
                sys.exit(1)

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
        if not output_json:
            info(f"Starting chat for {label}...")

        # Resume an existing conversation — skip session creation.
        if conversation_id:
            if not output_json:
                success(f"Resuming conversation: {conversation_id}")
            _, conversation = cls._run_chat_loop(
                project,
                conversation_id,
                environment,
                show_functions=show_functions,
                show_flow=show_flow,
                show_state=show_state,
                input_messages=input_messages,
                output_json=output_json,
            )
            if output_json:
                json_print({"conversations": [conversation]})
            return

        conversations: list[dict] = []
        while True:
            if environment == "draft" and not output_json:
                info("Preparing branch deployment...")
            try:
                response = project.create_chat_session(
                    environment,
                    channel,
                    variant,
                )
            except (requests.HTTPError, ValueError) as e:
                if output_json:
                    json_print({"success": False, "error": str(e)})
                else:
                    error(f"Failed to create chat session: {e}")
                return

            conversation_id = response.get("conversation_id")
            if not conversation_id:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No conversation_id in response",
                            "response": response,
                        }
                    )
                else:
                    error(f"Unexpected response when creating chat: {response}")
                return

            url = project.get_conversation_url(conversation_id)
            greeting = response.get("response", "")
            if not output_json:
                success(
                    f"Chat session started (conversation: [link={url}]{conversation_id}[/link])"
                )
                print_turn_metadata(response, show_functions, show_flow, show_state)
                if greeting:
                    plain(f"\n[bold]Agent:[/bold] {greeting}")

            if response.get("conversation_ended"):
                if not output_json:
                    plain("[muted]Conversation ended by agent.[/muted]")
                return

            if not output_json:
                plain(
                    "[muted]Type your messages below. "
                    "Press Ctrl+C or type '/exit' to quit. "
                    "Type '/restart' to begin a new chat.[/muted]"
                )

            restart, conversation = cls._run_chat_loop(
                project,
                conversation_id,
                environment,
                show_functions=show_functions,
                show_flow=show_flow,
                show_state=show_state,
                input_messages=input_messages,
                output_json=output_json,
                initial_response=response,
            )
            if output_json:
                conversations.append(conversation)

            if not restart:
                if output_json:
                    json_print({"conversations": conversations})
                return

            if not output_json:
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
        input_messages: Optional[list[str]] = None,
        output_json: bool = False,
        initial_response: Optional[dict] = None,
    ) -> tuple[bool, dict]:
        """Run the interactive message loop.

        Returns:
            A tuple of (restart, conversation) where restart is True if the user
            requested a new session, and conversation is a dict with conversation_id,
            url, and turns (populated when output_json=True).
        """
        conversation_ended = False
        restart = False
        url = None
        turns: list[dict] = (
            [{"input": None, **initial_response}] if output_json and initial_response else []
        )
        try:
            while True:
                if input_messages is not None:
                    if not input_messages:
                        break
                    user_input = input_messages.pop(0).strip()
                    if not output_json:
                        plain(f"\n[muted]You:[/muted] {user_input}")
                else:
                    try:
                        user_input = input("\nYou: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        if not output_json:
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
                    if output_json:
                        turns.append({"input": user_input, "error": str(e)})
                    else:
                        error(f"Failed to send message: {e}")
                    continue

                if output_json:
                    turns.append({"input": user_input, **reply})
                else:
                    print_turn_metadata(reply, show_functions, show_flow, show_state)
                    agent_text = reply.get("response") or json.dumps(reply, indent=2)
                    plain(f"\n[bold]Agent:[/bold] {agent_text}")

                if reply.get("conversation_ended"):
                    conversation_ended = True
                    if not output_json:
                        plain("[muted]Conversation ended by agent.[/muted]")
                    break
        finally:
            if not conversation_ended:
                try:
                    project.end_chat(conversation_id, environment)
                    url = project.get_conversation_url(conversation_id)
                    if not output_json:
                        info(f"Chat session ended (conversation: {conversation_id})")
                        plain(f"[info]Call Link:[/info] [link={url}]{url}[/link]")
                except requests.HTTPError:
                    if not output_json:
                        warning("Failed to end chat session on server.")

        return restart, {"conversation_id": conversation_id, "url": url, "turns": turns}

    @classmethod
    def validate_project(cls, base_path: str, output_json: bool = False) -> None:
        """Validate the project configuration locally."""
        project = cls._load_project(base_path, output_json=output_json)
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
