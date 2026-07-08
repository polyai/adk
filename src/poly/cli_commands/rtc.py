"""RTC command family: pull and push Real-Time Configuration.

Copyright PolyAI Limited
"""

import json
import logging
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

import questionary
import requests

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.output.console import error, info, success
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

RTC_ENV_TO_DIR = {
    "sandbox": "draft_and_sandbox",
    "pre-release": "pre_release",
    "live": "live",
}
RTC_DIR_TO_ENV = {v: k for k, v in RTC_ENV_TO_DIR.items()}


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
            help="Skip confirmation prompt (required for live).",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching RTC sub-handler."""
        if args.rtc_subcommand == "pull":
            result = cls.rtc_pull(args.path, args.env)
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
            result = cls.rtc_push(args.path, args.env, getattr(args, "force", False), args.json)
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
                schema_path = os.path.join(env_dir, "schema.json")
                with open(schema_path, "w", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2)
                    f.write("\n")

                variables = config.get("variables", {})
                data_path = os.path.join(env_dir, "data.json")
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(variables, f, indent=2)
                    f.write("\n")

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
    ) -> Optional[dict]:
        """Push RTC from local files to Agent Studio.

        Args:
            base_path: Base path for the project.
            env: Environment to push to — sandbox, pre-release, or live.
            force: If True, skip confirmation for live environment.
            output_json: If True, format errors as JSON on failure.

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
            AgentStudioInterface.patch_rtc_variables(
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

        return {
            "success": True,
            "environment": env,
            "schema_file": schema_path,
            "data_file": data_path,
        }
