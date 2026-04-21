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
from collections import Counter
from typing import Any, Optional

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
    edit_in_editor,
    output_merge_conflict_table,
    print_merge_conflict_interactive_header,
    print_deployments,
)
from poly.output.json_output import json_print, commands_to_dicts
from poly.handlers.github_api_handler import GitHubAPIHandler
from poly.handlers.interface import (
    REGIONS,
    AgentStudioInterface,
)
from poly.utils import merge_strings
from poly.resources.resource_utils import contains_merge_conflict
from poly.project import (
    PROJECT_CONFIG_FILE,
    STATUS_FILE,
    AgentStudioProject,
)

logger = logging.getLogger(__name__)

# Single-line values longer than this are treated like multiline (no terminal dump; editor for edit).
_BRANCH_MERGE_LONG_LINE_THRESHOLD = 800

DOCUMENT_CHOICES = AgentStudioProject.discover_docs()


def _branch_merge_conflict_file_key(path: list[str]) -> str:
    """Group field-level API conflicts by parent path (resource-ish key)."""
    if not path:
        return ""
    if len(path) <= 1:
        return os.sep.join(path)
    return os.sep.join(path[:-1])


def enrich_branch_merge_conflicts(conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add visual_path, merged_value, can_auto_merge, file_key, conflicts_in_resource for branch merge UI."""
    user = [
        c for c in conflicts if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
    ]
    counts: Counter[str] = Counter(_branch_merge_conflict_file_key(c["path"]) for c in user)
    out: list[dict[str, Any]] = []
    for c in conflicts:
        row = dict(c)
        path = row.get("path")
        if not path or path[-1] in {"updatedAt", "createdAt"}:
            out.append(row)
            continue
        merged = merge_strings(row["baseValue"], row["theirsValue"], row["oursValue"])
        fk = _branch_merge_conflict_file_key(path)
        row["visual_path"] = os.sep.join(path)
        row["merged_value"] = merged
        row["can_auto_merge"] = not contains_merge_conflict(merged)
        row["file_key"] = fk
        row["conflicts_in_resource"] = counts[fk]
        out.append(row)
    return out


def _auto_merge_resolution(path: list[str], merged_value: str) -> dict[str, Any]:
    """API payload shape for accepting the locally computed clean merge."""
    return {"path": path, "value": merged_value, "strategy": "theirs"}


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

        debug_parent = ArgumentParser(add_help=False)
        debug_parent.add_argument(
            "--debug",
            action="store_true",
            help="Display debug logs.",
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
            parents=[verbose_parent, json_parent, debug_parent],
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

        # PULL
        pull_parser = subparsers.add_parser(
            "pull",
            parents=[verbose_parent, json_parent, debug_parent],
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

        # PUSH
        push_parser = subparsers.add_parser(
            "push",
            parents=[verbose_parent, json_parent, debug_parent],
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

        # DIFF
        diff_parser = subparsers.add_parser(
            "diff",
            parents=[verbose_parent, json_parent],
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
                "  poly review create\n"
                "  poly review create --path /path/to/project\n"
                "  poly review create version-hash-1\n"
                "  poly review create --before main --after feature-branch\n"
                "  poly review create --before sandbox --after live\n"
                "  poly review create --before version-hash-1 --after version-hash-2\n"
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

        review_subparsers = review_parser.add_subparsers(dest="review_subcommand")

        review_create_parser = review_subparsers.add_parser(
            "create",
            parents=[verbose_parent, json_parent],
            help="Create a review gist for the current changes.",
        )
        review_create_parser.add_argument(
            "hash",
            nargs="?",
            default=None,
            type=str,
            help="Hash of the version to compare against. If not specified, it will be inferred from the --before and --after arguments.",
        )
        review_create_parser.add_argument(
            "--before",
            type=str,
            help="Name of the original branch or version to compare with.",
        )
        review_create_parser.add_argument(
            "--after",
            type=str,
            help="Name of the branch or version to compare with.",
        )
        review_create_parser.add_argument(
            "--files",
            nargs="*",
            help=("List of files to show changes for. If not specified, shows all changes."),
        )
        review_create_parser.set_defaults(review_subcommand="create")

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
            parents=[],
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
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
            help="List all branches in the project.",
        )
        branch_list_parser.set_defaults(branch_subcommand="list")

        branch_create_parser = branch_subparsers.add_parser(
            "create",
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
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
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
            help="Switch to a different branch.",
        )
        branch_switch_parser.add_argument(
            "branch_name", nargs="?", help="Name of the branch to switch to."
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
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
            help="Show the current branch.",
        )
        branch_current_parser.set_defaults(branch_subcommand="current")

        branch_delete_parser = branch_subparsers.add_parser(
            "delete",
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
            help="Interactively select and delete a branch.",
        )
        branch_delete_parser.add_argument(
            "branch_name",
            nargs="?",
            default=None,
            help="Name of the branch to delete directly, skipping the interactive prompt.",
        ).completer = cls._branch_name_completer
        branch_delete_parser.set_defaults(branch_subcommand="delete")

        branch_merge_parser = branch_subparsers.add_parser(
            "merge",
            parents=[branch_path_parent, verbose_parent, json_parent, debug_parent],
            help="Merge branch into main",
        )
        branch_merge_parser.add_argument(
            "message",
            nargs="?",
            default=None,
            help="Message for the merge.",
        )
        branch_merge_parser.add_argument(
            "--interactive",
            "-i",
            action="store_true",
            help="Enable interactive mode for resolving any merge conflicts. Set $EDITOR or $VISUAL to your preferred editor for editing merge conflict values if needed.",
        )
        branch_merge_parser.add_argument(
            "--resolutions",
            type=str,
            default=None,
            help=(
                "Conflict resolutions as a JSON file path, inline JSON string, or '-' for stdin. "
                "The JSON should be an array of objects, each with: "
                '"path" (list of strings), "strategy" ("ours", "theirs", or "base"), '
                'and optionally "value" (custom resolved string).'
            ),
        )
        branch_merge_parser.set_defaults(branch_subcommand="merge")

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
            parents=[verbose_parent, debug_parent, json_parent],
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
            "--lang",
            type=str,
            help="Language tag for both input and output messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--input-lang",
            type=str,
            help="Language tag for input messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--output-lang",
            type=str,
            help="Language tag for output messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--channel",
            type=str,
            default="voice",
            choices=["voice", "webchat"],
            help="Channel to chat against. Defaults to voice.",
        )
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
            help="Reuse an existing conversation ID instead of starting a new conversation.",
        )

        # COMPLETION
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

        # DEPLOYMENTS
        deployments_path_parent = ArgumentParser(add_help=False)
        deployments_path_parent.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        deployments_parser = subparsers.add_parser(
            "deployments",
            parents=[verbose_parent],
            help="Manage deployments for the project.",
            description=(
                "Manage deployments for the project.\n\nExamples:\n  poly deployments list\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        deployments_subparsers = deployments_parser.add_subparsers(
            dest="deployments_subcommand", required=True
        )

        deployment_list_parser = deployments_subparsers.add_parser(
            "list",
            parents=[deployments_path_parent, json_parent],
            help="List deployments for the project.",
            description=(
                "List deployments for the project.\n\n"
                "Examples:\n"
                "  poly deployments list\n"
                "  poly deployments list --env live\n"
                "  poly deployments list --details\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        deployment_list_parser.add_argument(
            "--env",
            "-e",
            type=str,
            default="sandbox",
            choices=["sandbox", "pre-release", "live"],
            help="Environment to list deployments for. Defaults to sandbox.",
        )
        deployment_list_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of versions to show. Defaults to 10.",
        )
        deployment_list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of versions to skip. Defaults to 0.",
        )
        deployment_list_parser.add_argument(
            "--hash",
            type=str,
            help="Hash of the version to start from.",
        )
        deployment_list_parser.add_argument(
            "--details",
            action="store_true",
            help="Output each deployment with detailed information.",
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
                cls.revert(args.path, args.files, output_json=args.json)

            elif args.command == "diff":
                cls.diff(args.path, args.files, args.hash, args.before, args.after, args.json)

            elif args.command == "chat":
                show_all = args.metadata
                input_messages = None
                input_lang = args.input_lang or args.lang
                output_lang = args.output_lang or args.lang
                if args.input_file:
                    try:
                        if args.input_file == "-":
                            with nullcontext(sys.stdin) as f:
                                src = f.read()
                        else:
                            with open(args.input_file, "r", encoding="utf-8") as f:
                                src = f.read()
                    except FileNotFoundError:
                        if args.json:
                            json_print(
                                {
                                    "success": False,
                                    "error": f"Input file not found: {args.input_file}",
                                }
                            )
                        else:
                            error(f"Input file not found: {args.input_file}")
                        sys.exit(1)
                    with src:
                        input_messages = [line.rstrip("\r\n") for line in src]
                elif args.messages:
                    input_messages = args.messages
                cls.chat(
                    args.path,
                    args.environment,
                    args.variant,
                    args.channel,
                    input_lang=input_lang,
                    output_lang=output_lang,
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
                elif args.review_subcommand == "create":
                    cls.review(
                        base_path=args.path,
                        files=args.files,
                        version_hash=args.hash,
                        before=args.before,
                        after=args.after,
                        output_json=args.json,
                    )

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

                elif args.branch_subcommand == "merge":
                    cls.branch_merge(
                        args.path, args.message, args.json, args.interactive, args.resolutions
                    )

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

            elif args.command == "deployments":
                if args.deployments_subcommand == "list":
                    cls.deployments_list(
                        args.path,
                        args.env,
                        args.limit,
                        args.offset,
                        args.hash,
                        args.json,
                        args.details,
                    )

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
        files: list[str] = None,
        output_json: bool = False,
    ) -> None:
        """Revert changes in the project."""
        project = cls._load_project(base_path, output_json=output_json)

        # If relative paths are provided, convert them to absolute paths
        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]

        files_reverted = project.revert_changes(files=files)
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

    @classmethod
    def _compute_diff(
        cls,
        base_path: str,
        files: list[str] = None,
        before: str = None,
        after: str = None,
        output_json: bool = False,
    ) -> Optional[dict[str, str]]:
        """Compute the diffs between the project and the given versions or branches.

        If before and after are not specified, it will compute the diffs between the project and the remote version.
        If before and after are specified, it will compute the diffs between the two remote versions.
        If only after is specified, it will compare between after and the previous version.
        """
        project = cls._load_project(base_path, output_json=output_json)
        files = [os.path.abspath(os.path.join(os.getcwd(), file)) for file in files or []]
        if not (before or after):
            return project.get_diffs(all_files=not files, files=files)

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
                (
                    i
                    for i, v in enumerate(versions)
                    if (v.get("version_hash") or "")[:9] == after[:9]
                ),
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
        if version_hash and (before or after):
            error("Cannot specify both hash and before/after versions.")
            return

        if version_hash:
            after = version_hash

        diffs = cls._compute_diff(base_path, files, before, after, output_json=output_json)

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

    @classmethod
    def review(
        cls,
        base_path: str,
        files: list[str] = None,
        version_hash: str = None,
        before: str = None,
        after: str = None,
        output_json: bool = False,
    ) -> None:
        """Create a GitHub gist for reviewing changes, similar to a pull request.

        With no arguments, reviews local changes against the remote version.
        Pass a version hash to review that version against its predecessor.
        Use --before / --after to compare any two named versions or branches.

        Args:
            base_path: Base path for the project (used to read project config).
            files: Files to include in the review. If not specified, includes all changes.
            version_hash: Version hash to compare against its predecessor.
            before: Base version or branch name for comparison.
            after: Target version or branch name for comparison.
            output_json: If True, print result as JSON instead of rich text.
        """
        project_name = "/".join(os.path.abspath(base_path).split(os.sep)[-2:])
        if version_hash and (before or after):
            error("Cannot specify both hash and before/after versions.")
            return

        if version_hash:
            after = version_hash
            description = f"Poly ADK: {project_name}: {version_hash}"

        elif not (before or after):
            description = f"Poly ADK: {project_name}: local → remote"

        elif before and after:
            description = f"Poly ADK: {project_name}: {before} → {after}"

        elif after:
            description = f"Poly ADK: {project_name}: {after}"

        else:
            description = f"Poly ADK: {project_name}: {before} → local"

        diffs = cls._compute_diff(
            base_path, files=files, before=before, after=after, output_json=output_json
        )

        if not diffs:
            if output_json and diffs is not None:
                json_print({"success": False, "message": "No changes to review."})
            elif output_json:
                json_print({"success": False, "message": "Failed to compute diffs."})
            else:
                plain("[muted]No changes detected.[/muted]")
            return

        body = {}
        for file_path, diff in diffs.items():
            if not diff:
                continue
            # Use the file_path as-is (it's already relative or a file path)
            safe_name = file_path.replace(os.sep, "_")
            body[f"{safe_name}.diff"] = {"content": diff}

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

    @staticmethod
    def _merge_interactively(
        conflicts: list[dict[str, Any]],
        existing_resolutions: dict[str, dict[str, Any]],
        branch_display_name: str = "",
    ) -> list[dict[str, Any]]:
        """Resolve merge conflicts with questionary; expects API conflicts optionally enriched."""
        resolutions: list[dict[str, Any]] = []
        index_in_resource: dict[str, int] = {}
        branch_label = branch_display_name or "current branch"

        def _is_heavy_content(c: dict[str, Any]) -> bool:
            for key in ("baseValue", "theirsValue", "oursValue"):
                v = c.get(key, "")
                if not isinstance(v, str):
                    return True
                if "\n" in v:
                    return True
                if len(v) > _BRANCH_MERGE_LONG_LINE_THRESHOLD:
                    return True
            return False

        for conflict in conflicts:
            if conflict["path"][-1] in {"updatedAt", "createdAt"}:
                resolutions.append({"path": conflict["path"], "strategy": "theirs"})
                continue

            existing_resolution = existing_resolutions.get(conflict["path"])

            path = conflict["path"]
            clean_path = conflict.get("visual_path") or os.sep.join(path)
            merged_version = conflict.get("merged_value")
            if merged_version is None:
                merged_version = merge_strings(
                    conflict["baseValue"], conflict["theirsValue"], conflict["oursValue"]
                )
            auto_merged = conflict.get("can_auto_merge")
            if auto_merged is None:
                auto_merged = not contains_merge_conflict(merged_version)

            fk = conflict.get("file_key") or _branch_merge_conflict_file_key(path)
            index_in_resource[fk] = index_in_resource.get(fk, 0) + 1
            idx = index_in_resource[fk]
            total = int(conflict.get("conflicts_in_resource") or 1)
            heavy = _is_heavy_content(conflict)
            print_merge_conflict_interactive_header(
                field_path=clean_path,
                resource_key=fk,
                conflict_index=idx,
                conflict_total=total,
                auto_mergeable=auto_merged,
                heavy=heavy,
                base_value=str(conflict.get("baseValue", "")),
                branch_label=branch_label,
                branch_value=str(conflict.get("theirsValue", "")),
                main_value=str(conflict.get("oursValue", "")),
                existing_resolution=existing_resolution,
            )

            choices: list[dict[str, str]] = []
            if existing_resolution:
                er_strategy = existing_resolution.get("strategy", "")
                er_value = existing_resolution.get("value")
                if er_value is not None:
                    er_label = (
                        er_value if isinstance(er_value, str) and "\n" not in er_value else "value"
                    )
                else:
                    er_label = er_strategy
                choices.append({"name": f"Use resolution: {er_label}", "value": "existing"})
            if auto_merged:
                choices.append({"name": "Accept auto-merge", "value": "merged"})
            choices.extend(
                [
                    {"name": "Use main", "value": "ours"},
                    {"name": f"Use branch — {branch_label}", "value": "theirs"},
                    {"name": "Use original (base)", "value": "base"},
                    {"name": "Edit in editor", "value": "edit"},
                ]
            )

            extension = ".py" if path[-1] == "code" else ".txt"

            while True:
                answer = questionary.select("Select resolution", choices=choices).ask()
                if answer is None:
                    return []
                if answer == "existing":
                    resolutions.append(existing_resolution)
                    break
                if answer == "merged":
                    resolutions.append(_auto_merge_resolution(path, merged_version))
                    break
                if answer == "edit":
                    try:
                        if heavy:
                            edited = edit_in_editor(
                                merged_version, extension=extension, filename=fk
                            )
                        else:
                            edited_q = questionary.text(
                                "Custom resolution",
                                default=str(conflict.get("theirsValue", "")),
                                multiline=True,
                            ).ask()
                            if edited_q is None:
                                return []
                            edited = edited_q
                    except FileNotFoundError:
                        warning(
                            "Could not open the configured editor. Check your $EDITOR or "
                            "$VISUAL setting, then try Edit again."
                        )
                        continue
                    except subprocess.CalledProcessError:
                        warning(
                            "The editor exited with an error. Fix the issue and try Edit "
                            "again, or choose another resolution."
                        )
                        continue
                    except ValueError:
                        warning(
                            "Editor closed without saving; choose another option or try Edit again."
                        )
                        continue

                    if contains_merge_conflict(edited):
                        warning(
                            "Edited version still contains merge conflict markers. "
                            "Resolve them before continuing."
                        )
                        continue

                    resolutions.append({"path": path, "value": edited, "strategy": "theirs"})
                    break

                resolutions.append({"path": path, "strategy": answer})
                break

        return resolutions

    @classmethod
    def branch_merge(
        cls,
        base_path: str,
        message: str = None,
        output_json: bool = False,
        interactive: bool = False,
        resolutions_file: str = None,
    ):
        """Merge a branch into the current branch, with optional conflict resolutions."""
        if message is None or (isinstance(message, str) and not message.strip()):
            if output_json:
                json_print({"success": False, "error": "Merge message is required."})
            else:
                error("Merge message is required.")
            sys.exit(1)

        if interactive and output_json:
            json_print(
                {
                    "success": False,
                    "error": "--interactive and --json cannot be used together.",
                }
            )
            sys.exit(1)

        file_resolutions: list[dict[str, Any]] | None = None
        if resolutions_file:
            try:
                if resolutions_file == "-":
                    file_resolutions = json.load(sys.stdin)
                elif resolutions_file.lstrip().startswith("["):
                    file_resolutions = json.loads(resolutions_file)
                else:
                    with open(resolutions_file, encoding="utf-8") as f:
                        file_resolutions = json.load(f)
                if not isinstance(file_resolutions, list):
                    raise ValueError("Resolutions must be a JSON array.")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                if output_json:
                    json_print({"success": False, "error": f"Failed to parse resolutions: {exc}"})
                else:
                    error(f"Failed to parse resolutions: {exc}")
                sys.exit(1)

        project = cls._load_project(base_path, output_json=output_json)

        branch_name = project.get_current_branch()
        ctx = console.status("[info]Merging branch...[/info]") if not output_json else nullcontext()
        with ctx:
            merge_success, conflicts, errors = project.merge_branch(
                message=message, conflict_resolutions=file_resolutions
            )

        if output_json:
            output = {"success": merge_success}
            if conflicts or errors:
                output["conflicts"] = conflicts
                output["errors"] = errors
            json_print(output)
            if not merge_success:
                sys.exit(1)
        else:
            if merge_success:
                success(f"Branch '{branch_name}' merged successfully.")
                info('Switched to "main" branch after merge.')
            else:
                error(f"Failed to merge branch '{branch_name}'.")
                if errors:
                    plain("\n[red]Errors:[/red]")
                    for err in errors:
                        error(f"- {err['path']}: {err['message']}")

                enriched = enrich_branch_merge_conflicts(conflicts) if conflicts else []
                display_conflict = [
                    c
                    for c in enriched
                    if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
                ]
                if display_conflict:
                    output_merge_conflict_table(
                        display_conflict, show_type=True, resolutions=file_resolutions
                    )

                if errors:
                    sys.exit(1)

                if not interactive and not resolutions_file:
                    plain(
                        "Merge conflicts detected. To resolve:\n"
                        "- Use 'poly branch merge -i <message>' to resolve conflicts interactively\n"
                        "- Use 'poly branch merge --resolutions <file.json> <message>' to provide pre-defined resolutions\n"
                        "- Merge manually on Agent Studio"
                    )

                resolutions: list[dict[str, Any]] = []
                existing_resolutions = {
                    r["path"]: r for r in (file_resolutions or []) if "path" in r
                }
                if interactive and conflicts:
                    while True:
                        batch = cls._merge_interactively(
                            enriched, existing_resolutions, branch_name
                        )
                        if not batch:
                            warning("No resolutions provided. Exiting.")
                            sys.exit(1)
                        resolutions.extend(batch)
                        ctx2 = (
                            console.status("[info]Merging branch...[/info]")
                            if not output_json
                            else nullcontext()
                        )
                        with ctx2:
                            merge_success, conflicts, errors = project.merge_branch(
                                message=message, conflict_resolutions=resolutions
                            )
                        if merge_success:
                            success(f"Branch '{branch_name}' merged successfully.")
                            info('Switched to "main" branch after merge.')
                            break
                        if errors:
                            error(
                                f"Failed to merge branch '{branch_name}' after conflict resolution."
                            )
                            plain("\n[red]Errors:[/red]")
                            for err in errors:
                                error(f"- {err['path']}: {err['message']}")
                            sys.exit(1)
                        if not conflicts:
                            error(
                                f"Failed to merge branch '{branch_name}' after conflict resolution "
                                "(no conflicts or errors returned)."
                            )
                            sys.exit(1)
                        warning("Merge still blocked; resolve the remaining conflicts below.")
                        enriched = enrich_branch_merge_conflicts(conflicts)
                        display_conflict = [
                            c
                            for c in enriched
                            if c.get("path") and c["path"][-1] not in {"updatedAt", "createdAt"}
                        ]
                        if display_conflict:
                            output_merge_conflict_table(
                                display_conflict,
                                show_type=True,
                                panel_title="Remaining merge conflicts",
                            )
                elif not merge_success:
                    sys.exit(1)

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
        input_lang: str = None,
        push_before_chat: bool = False,
        output_lang: str = None,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
        output_json: bool = False,
        input_messages: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Start an interactive chat session with the agent."""
        project = cls._load_project(base_path)

        json_output = {}

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

            if push_success:
                if not output_json:
                    success("Project pushed successfully.")
                else:
                    json_output["push"] = {"success": True, "message": output}

            if not push_success:
                if output_json:
                    json_output["push"] = {
                        "success": False,
                        "message": "Failed to push project before chat session.",
                        "error": output,
                    }
                    json_print(json_output)
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

        conversations: list[dict] = []
        while True:
            if conversation_id:
                if not output_json:
                    info(f"Resuming chat session (conversation: {conversation_id})...")
                response = None
            else:
                if environment == "draft" and not output_json:
                    info("Preparing branch deployment...")
                try:
                    response = project.create_chat_session(
                        environment,
                        channel,
                        variant,
                        input_lang,
                        output_lang,
                    )
                except (requests.HTTPError, ValueError) as e:
                    if output_json:
                        json_output["success"] = False
                        json_output["error"] = str(e)
                        json_print(json_output)
                    else:
                        error(f"Failed to create chat session: {e}")
                    return

                conversation_id = response.get("conversation_id")
                if not conversation_id:
                    if output_json:
                        json_output["success"] = False
                        json_output["error"] = "No conversation_id in response"
                        json_output["response"] = response
                        json_print(json_output)
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
                input_lang=input_lang,
                output_lang=output_lang,
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
                    json_output["conversations"] = conversations
                    json_print(json_output)
                return
            if not output_json:
                info("Restarting chat session...")

            # Create a new chat session in the next loop iteration
            conversation_id = None

    @classmethod
    def _run_chat_loop(
        cls,
        project: AgentStudioProject,
        conversation_id: str,
        environment: str,
        input_lang: str = None,
        output_lang: str = None,
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
        url = project.get_conversation_url(conversation_id)
        turns: list[dict] = (
            [
                {
                    "input": None,
                    **cls._process_json_chat_reply(
                        initial_response, show_functions, show_flow, show_state
                    ),
                }
            ]
            if output_json and initial_response is not None
            else []
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

                if user_input is None:
                    continue
                if user_input.lower() == "/exit":
                    break
                if user_input.lower() == "/restart":
                    restart = True
                    break

                try:
                    reply = project.send_message(
                        conversation_id, user_input, environment, input_lang, output_lang
                    )
                except requests.HTTPError as e:
                    if output_json:
                        turns.append({"input": user_input, "error": str(e)})
                    else:
                        error(f"Failed to send message: {e}")
                    continue

                if output_json:
                    # Filter reply for relevant fields to avoid dumping large state
                    processed_reply = cls._process_json_chat_reply(
                        reply, show_functions, show_flow, show_state
                    )
                    turns.append({"input": user_input, **processed_reply})
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
                    if not output_json:
                        info(f"Chat session ended (conversation: {conversation_id})")
                        plain(f"[info]Call Link:[/info] [link={url}]{url}[/link]")
                except requests.HTTPError:
                    if not output_json:
                        warning("Failed to end chat session on server.")

        if input_messages and not restart:
            # If the conversation ended, but there is still a restart queued in input messages
            # Pop the remaining messages until we get to a restart
            while input_messages:
                msg = input_messages.pop(0).strip()
                if msg.lower() == "/restart":
                    restart = True
                    break

        return restart, {"conversation_id": conversation_id, "url": url, "turns": turns}

    @staticmethod
    def _process_json_chat_reply(
        reply: dict, show_functions: bool, show_flow: bool, show_state: bool
    ) -> dict:
        """Process the raw reply from the chat API to extract relevant information based on the flags."""
        processed_json = dict(
            response=reply.get("response"),
            conversation_ended=reply.get("conversation_ended", False),
        )
        turn_metadata = reply.get("metadata") or {}
        if show_functions:
            function_replies = []
            for function_event in turn_metadata.get("function_events") or []:
                function_reply = {
                    "name": function_event.get("name"),
                    "arguments": function_event.get("arguments"),
                    "utterance": function_event.get("utterance"),
                    "hangup": function_event.get("hangup"),
                    "handoff": function_event.get("handoff"),
                    "error": function_event.get("error"),
                    "logs": function_event.get("logs"),
                    "transition": function_event.get("transition"),
                }
                filtered_function_reply = {k: v for k, v in function_reply.items() if v is not None}
                function_replies.append(filtered_function_reply)

            processed_json["function_events"] = function_replies

        if show_flow:
            flow_reply = {}
            in_flow = turn_metadata.get("in_flow")
            in_step = turn_metadata.get("in_step")
            if in_flow:
                flow_reply["in_flow"] = in_flow
            if in_step:
                flow_reply["in_step"] = in_step
            if flow_reply:
                processed_json["flow"] = flow_reply

        if show_state:
            state_reply = []
            for function_event in turn_metadata.get("function_events") or []:
                sc = function_event.get("state_changes") or {}
                added = sc.get("added", {})
                updated = sc.get("updated", {})
                removed = sc.get("removed", [])
                if added or updated or removed:
                    event_state_reply = {}
                    if added:
                        event_state_reply["added"] = added
                    if updated:
                        event_state_reply["updated"] = updated
                    if removed:
                        event_state_reply["removed"] = removed
                    state_reply.append(event_state_reply)
            if state_reply:
                processed_json["state_changes"] = state_reply

        return processed_json

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

    @classmethod
    def deployments_list(
        cls,
        base_path: str,
        environment: str = "sandbox",
        limit: int = 10,
        offset: int = 0,
        version_hash: str = None,
        output_json: bool = False,
        details: bool = False,
    ) -> None:
        """List deployment history for the project.

        By default shows the 10 most recent deployments for the sandbox environment.
        Pass version_hash to start the listing from a specific version. Use details for
        full per-deployment metadata.

        Args:
            base_path: Base path for the project.
            environment: Environment to query — sandbox, pre-release, or live.
            limit: Maximum number of versions to show.
            offset: Number of versions to skip before showing results.
            version_hash: Start listing from this version hash (overrides offset).
            output_json: If True, print result as JSON instead of rich text.
            details: If True, print full metadata for each deployment.
        """
        project = cls._load_project(base_path)
        versions, active_deployment_hashes = project.get_deployments(client_env=environment)

        if not versions:
            error("No versions found.")
            return

        if version_hash:
            version_hash = version_hash[:9]
            version_idx = next(
                (
                    i
                    for i, v in enumerate(versions)
                    if (v.get("version_hash") or "")[:9] == version_hash
                ),
                None,
            )
            if version_idx is None:
                error(f"Version hash '{version_hash}' not found.")
                return
            offset = version_idx

        versions = versions[offset : offset + limit]
        if output_json:
            json_output = {
                "versions": versions,
                "active_deployment_hashes": active_deployment_hashes,
            }
            json_print(json_output)
        else:
            print_deployments(versions, active_deployment_hashes, details=details)


def main():
    """Entry point for the CLI tool."""
    AgentStudioCLI.main()
