"""Agent Development Kit (ADK) CLI for managing Agent Studio projects.

Copyright PolyAI Limited
"""

import logging
import os
import sys
import traceback
from argparse import ArgumentParser
from importlib.metadata import version as get_package_version

import argcomplete

from poly.cli_commands.audio_cache import AudioCacheCommand
from poly.cli_commands.auth import LoginCommand, StartCommand
from poly.cli_commands.base import (
    COMMAND_GROUP_ORDER,
    BaseCommand,
    GroupedHelpFormatter,
    Parents,
    add_grouped_subparsers,
    group_subcommands,
)
from poly.cli_commands.branch import BranchCommand
from poly.cli_commands.chat import ChatCommand
from poly.cli_commands.conversations import ConversationsCommand
from poly.cli_commands.deployments import DeploymentsCommand
from poly.cli_commands.functions import FunctionsCommand
from poly.cli_commands.project import InitCommand, ProjectCommand, StudioCommand
from poly.cli_commands.review import ReviewCommand
from poly.cli_commands.rtc import RTCCommand
from poly.cli_commands.sync import (
    DiffCommand,
    FetchCommand,
    FormatCommand,
    PullCommand,
    PushCommand,
    RevertCommand,
    StatusCommand,
    ValidateCommand,
)
from poly.cli_commands.template import TemplateCommand
from poly.cli_commands.testing import TestingCommand
from poly.cli_commands.utils import CompletionCommand, DocsCommand
from poly.handlers.interface import REGIONS
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

COMMANDS = [
    InitCommand,
    StartCommand,
    LoginCommand,
    StudioCommand,
    ProjectCommand,
    TemplateCommand,
    FetchCommand,
    PullCommand,
    PushCommand,
    StatusCommand,
    RevertCommand,
    FormatCommand,
    ValidateCommand,
    DiffCommand,
    ReviewCommand,
    BranchCommand,
    DeploymentsCommand,
    ConversationsCommand,
    AudioCacheCommand,
    FunctionsCommand,
    TestingCommand,
    RTCCommand,
    ChatCommand,
    DocsCommand,
    CompletionCommand,
]


class AgentStudioCLI:
    """Agent Development Kit (ADK) CLI for managing Agent Studio projects."""

    commands: list[type[BaseCommand]] = []

    def register_commands(self):
        """Register commands to the CLI."""
        self.commands = COMMANDS

    def _create_parser(self):
        try:
            _version = get_package_version("polyai-adk")
        except Exception:
            _version = "unknown"
        parser = ArgumentParser(formatter_class=GroupedHelpFormatter)
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

        path_parent = ArgumentParser(add_help=False)
        path_parent.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        scope_parent = ArgumentParser(add_help=False)
        scope_parent.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            default=None,
            help="Region, for headless use without a local project. Requires "
            "--project_id and --branch_id.",
        )
        scope_parent.add_argument(
            "--project_id",
            type=str,
            default=None,
            help="Project ID (agent ID), for headless use without a local project. "
            "Requires --region and --branch_id.",
        )
        scope_parent.add_argument(
            "--branch_id",
            type=str,
            default=None,
            help="Branch ID, for headless use without a local project. Requires "
            "--region and --project_id.",
        )

        parents = Parents(
            verbose=verbose_parent,
            json=json_parent,
            debug=debug_parent,
            path=path_parent,
            scope=scope_parent,
        )

        subparsers = add_grouped_subparsers(parser, dest="command", metavar="<command>")

        for command in self.commands:
            command.add_arguments(subparsers, parents=parents)

        # Split the (long) flat command list into titled sections for --help.
        group_subcommands(
            subparsers,
            {command.command: command.group for command in self.commands},
            COMMAND_GROUP_ORDER,
        )

        return parser

    def _run_command(self, args):
        """Run the command based on parsed arguments."""
        if hasattr(args, "debug") and args.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.WARNING)

        try:
            for command in self.commands:
                if args.command == command.command:
                    command.run(args)
                    return
        except Exception as e:
            if hasattr(args, "json") and args.json:
                json_print({"success": False, "error": str(e), "traceback": traceback.format_exc()})
                sys.exit(1)
            else:
                raise

        raise ValueError(f"Unknown command: {args.command}")

    def main(self, sys_args=None):
        """Main entry point for the CLI tool."""
        self.register_commands()
        parser = self._create_parser()
        argcomplete.autocomplete(parser, always_complete_options=False)

        try:
            if sys_args:
                args = parser.parse_args(args=sys_args)
            else:
                args = parser.parse_args()

            from poly.output.console import set_verbose

            set_verbose(getattr(args, "verbose", False))
            self._run_command(args)
        except SystemExit:
            raise
        except KeyboardInterrupt:
            from poly.output.console import plain

            plain("\nAborted.")
            sys.exit(130)
        except Exception as e:
            from poly.output.console import handle_exception

            handle_exception(e)


def main():
    """Entry point for the CLI tool."""
    AgentStudioCLI().main()
