"""Manage API integration credentials without writing secrets to project files.

Copyright PolyAI Limited
"""

import getpass
import json
import os
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from poly.cli_commands.auth import _signin
from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.console import success
from poly.output.json_output import json_print
from poly.project import INTEGRATION_CREDENTIAL_FIELDS as FIELDS


class ApiIntegrationsCommand(BaseCommand):
    """Manage credentials for existing API integrations."""

    command = "api-integrations"
    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents):
        """Register the API credential configuration command."""
        parser = subparsers.add_parser(cls.command, help="Manage API integration credentials.")
        commands = parser.add_subparsers(dest="api_integrations_subcommand", required=True)
        setter = commands.add_parser(
            "configure",
            parents=[parents.path, parents.json, parents.verbose],
            help="Configure credentials for one environment directly in Agent Studio (live changes across branches).",
        )
        setter.add_argument("integration", help="Integration name or ID on the current branch.")
        setter.add_argument("--env", required=True, choices=["sandbox", "pre-release", "live"])
        setter.add_argument("--stdin", action="store_true", help="Read a JSON object from stdin.")
        setter.add_argument("--private-key-file", help="Read the JWT signing key from a PEM file.")
        setter.add_argument(
            "--token-env",
            default="POLY_STUDIO_ACCESS_TOKEN",
            help="Environment variable containing a Studio access token; otherwise sign in.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Collect credentials and configure the selected API integration."""
        project = load_project(args.path, output_json=args.json)
        integration = project.get_api_integration(args.integration, args.env)
        config = getattr(integration.environments, args.env.replace("-", "_"))
        if args.private_key_file and config.auth_type != "jwt_client_assertion":
            raise ValueError("--private-key-file requires JWT client assertion authentication.")
        token = os.environ.get(args.token_env)
        interactive = sys.stdin.isatty() and not args.stdin and not args.json
        if not token and not interactive:
            raise ValueError(
                f"Set {args.token_env} to a Studio access token for non-interactive use."
            )
        if not interactive and not args.stdin:
            raise ValueError("Use --stdin to provide credentials non-interactively.")
        if args.stdin:
            try:
                values = json.load(sys.stdin)
            except (ValueError, UnicodeError):
                raise ValueError("stdin must contain a valid credentials JSON object.") from None
            if not isinstance(values, dict):
                raise ValueError("Credentials must be a JSON object.")
        else:
            values = {}
            for field, hidden, default in FIELDS[config.auth_type]:
                if field == "private_key" and args.private_key_file:
                    continue
                if field == "private_key":
                    raise ValueError("Use --private-key-file for an interactive JWT signing key.")
                prompt = (
                    f"{field} ({args.env})"
                    + (f" [{default}]" if default is not None else "")
                    + ": "
                )
                value = getpass.getpass(prompt) if hidden else input(prompt)
                values[field] = value if value else default
        if args.private_key_file:
            if "private_key" in values:
                raise ValueError(
                    "Provide the private key through stdin or --private-key-file, not both."
                )
            try:
                values["private_key"] = Path(args.private_key_file).read_text()
            except (OSError, UnicodeError):
                raise ValueError("Could not read the private key file.") from None
        project.build_api_integration_credentials(config.auth_type, values, config.base_url)
        token = token or _signin(project.region)
        project.configure_api_integration(args.integration, args.env, values, token)
        result = {
            "success": True,
            "integration": integration.name,
            "environment": args.env,
            "auth_type": config.auth_type,
        }
        if args.json:
            json_print(result)
        else:
            success(f"Credentials set for {integration.name} ({args.env}).")
