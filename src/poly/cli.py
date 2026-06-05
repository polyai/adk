"""Agent Development Kit (ADK) CLI for managing Agent Studio projects.

Copyright PolyAI Limited
"""

import json
import logging
import os
import sys
import traceback
from argparse import ArgumentParser, RawTextHelpFormatter
from importlib.metadata import version as get_package_version

import argcomplete
import questionary
import requests

from poly.cli_commands.auth import LoginCommand, StartCommand
from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.branch import BranchCommand
from poly.cli_commands.chat import ChatCommand
from poly.cli_commands.conversations import ConversationsCommand
from poly.cli_commands.deployments import DeploymentsCommand
from poly.cli_commands.project import InitCommand, ProjectCommand, StudioCommand
from poly.cli_commands.review import ReviewCommand
from poly.cli_commands.shared import load_project
from poly.cli_commands.sync import (
    DiffCommand,
    FormatCommand,
    PullCommand,
    PushCommand,
    RevertCommand,
    StatusCommand,
    ValidateCommand,
)
from poly.cli_commands.testing import TestingCommand
from poly.cli_commands.utils import CompletionCommand, DocsCommand
from poly.handlers.interface import AgentStudioInterface
from poly.output.console import error, info, success
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

COMMANDS = [
    InitCommand,
    StartCommand,
    LoginCommand,
    StudioCommand,
    ProjectCommand,
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
    TestingCommand,
    ChatCommand,
    DocsCommand,
    CompletionCommand,
]

# RTC environment name mapping
RTC_ENV_TO_DIR = {
    "sandbox": "draft_and_sandbox",
    "pre-release": "pre_release",
    "live": "live",
}
RTC_DIR_TO_ENV = {v: k for k, v in RTC_ENV_TO_DIR.items()}


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

        path_parent = ArgumentParser(add_help=False)
        path_parent.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        parents = Parents(
            verbose=verbose_parent, json=json_parent, debug=debug_parent, path=path_parent
        )

        subparsers = parser.add_subparsers(dest="command", required=True)

        for command in self.commands:
            command.add_arguments(subparsers, parents=parents)

        # RTC
        rtc_path_parent = ArgumentParser(add_help=False)
        rtc_path_parent.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

        rtc_parser = subparsers.add_parser(
            "rtc",
            parents=[verbose_parent],
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
            parents=[rtc_path_parent, json_parent, verbose_parent],
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
            parents=[rtc_path_parent, json_parent, verbose_parent],
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
            help="Skip confirmation prompt (required for live).",
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

            if args.command == "rtc":
                if args.rtc_subcommand == "pull":
                    AgentStudioCLI.rtc_pull(args.path, args.env, args.json)
                elif args.rtc_subcommand == "push":
                    AgentStudioCLI.rtc_push(
                        args.path, args.env, getattr(args, "force", False), args.json
                    )
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

    @staticmethod
    def rtc_pull(
        base_path: str,
        env: str = "all",
        output_json: bool = False,
    ) -> None:
        """Pull RTC from Agent Studio and write to local files.

        Args:
            base_path: Base path for the project.
            env: Environment(s) to pull — sandbox, pre-release, live, or all.
            output_json: If True, emit machine-readable JSON.
        """
        project = load_project(base_path, output_json=output_json)

        if env == "all":
            envs_to_fetch = ["sandbox", "pre-release", "live"]
        else:
            envs_to_fetch = [env]

        rtc_root = os.path.join(base_path, "real_time_configuration")
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
                schema_path = os.path.join(env_dir, "schema.json")
                with open(schema_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2)

                variables = config.get("variables", {})
                data_path = os.path.join(env_dir, "data.json")
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(variables, f, indent=2)

                results.append(
                    {
                        "environment": client_env,
                        "schema_file": schema_path,
                        "data_file": data_path,
                    }
                )

            if output_json:
                json_print({"success": True, "files_written": results})
            else:
                for result in results:
                    success(f"Pulled {result['environment']} — {result['schema_file']}")
                    success(f"Pulled {result['environment']} — {result['data_file']}")

        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
                sys.exit(1)
            else:
                raise

    @staticmethod
    def rtc_push(
        base_path: str,
        env: str,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Push RTC from local files to Agent Studio.

        Args:
            base_path: Base path for the project.
            env: Environment to push to — sandbox, pre-release, or live.
            force: If True, skip confirmation for live environment.
            output_json: If True, emit machine-readable JSON.
        """
        project = load_project(base_path, output_json=output_json)

        dir_name = RTC_ENV_TO_DIR[env]
        env_dir = os.path.join(base_path, "real_time_configuration", dir_name)

        schema_path = os.path.join(env_dir, "schema.json")
        data_path = os.path.join(env_dir, "data.json")

        if not os.path.exists(schema_path):
            msg = f"schema.json not found at {schema_path}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        if not os.path.exists(data_path):
            msg = f"data.json not found at {data_path}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        with open(data_path, "r", encoding="utf-8") as f:
            variables = json.load(f)

        if env == "live" and not force and not output_json:
            confirm = questionary.confirm(
                f"Push RTC to {env}? This will update live configuration.",
                auto_enter=False,
                default=False,
            ).ask()
            if not confirm:
                info("Push cancelled.")
                return

        try:
            AgentStudioInterface.put_rtc_schema(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
                schema=schema,
            )

            AgentStudioInterface.patch_rtc_variables(
                region=project.region,
                project_id=project.project_id,
                client_env=env,
                variables=variables,
            )

            if output_json:
                json_print(
                    {
                        "success": True,
                        "environment": env,
                        "schema_file": schema_path,
                        "data_file": data_path,
                    }
                )
            else:
                success(f"Pushed RTC to {env}")

        except requests.HTTPError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
                sys.exit(1)
            else:
                raise


def main():
    """Entry point for the CLI tool."""
    AgentStudioCLI().main()
