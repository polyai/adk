"""Manage API integration credentials without writing secrets to project files.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from poly.cli_commands.auth import _signin
from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.console import success
from poly.output.json_output import json_print
from poly.project import INTEGRATION_CREDENTIAL_FIELDS as FIELDS
from poly.utils import apikey_session


def _studio_token(region: str, interactive: bool) -> str:
    """Reuse the regional browser session shared with ``poly apikey``."""
    if session := apikey_session.load(region):
        return session.token
    if not interactive:
        raise ValueError(
            f"No unexpired sign-in for {region}. Run `poly apikey --region {region}` first, "
            "or configure this integration interactively."
        )
    token = _signin(region)
    apikey_session.save(region, token)
    return token


def _prompt_credentials(auth_type: str, existing: dict) -> dict:
    """Prompt with masked saved values, required-field retries, and constrained choices."""
    import questionary

    from poly.output.console import warning

    labels = {
        "client_id": "Client ID",
        "client_secret": "Client Secret",
        "access_token_url": "Token URL",
        "credentials_location": "Credentials location",
        "auth_header_name": "Auth header name",
        "token_prefix": "Token prefix",
    }
    choices = {
        "credentials_location": ["header", "body"],
        "location": ["header", "query_param"],
    }
    values = {}
    for field, _, default in FIELDS[auth_type]:
        saved = existing.get(field)
        label = labels.get(field, field.replace("_", " ").capitalize())
        if field in choices:
            selected = saved if saved in choices[field] else default
            value = questionary.select(f"{label}:", choices=choices[field], default=selected).ask()
            if value is None:
                raise KeyboardInterrupt
        elif default == "":
            prompt = (
                f"{label} [{saved}] (Enter to keep, - to clear): "
                if saved
                else f"{label} (optional, Enter to skip): "
            )
            entered = input(prompt)
            value = "" if entered == "-" else entered or saved or ""
        else:
            # Short saved values stay fully masked; never put real defaults in editable input.
            masked = "******" + saved[-3:] if saved and len(saved) > 3 else "******"
            if field == "access_token_url":
                masked = saved
            prompt = f"{label}" + (f" [{masked}]" if saved else "") + ": "
            while True:
                entered = input(prompt)
                value = entered or saved or default
                if isinstance(value, str) and value.strip():
                    break
                warning(f"{label} is required.")
        values[field] = value
    return values


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
        setter.add_argument(
            "integration",
            metavar="api_name",
            help="API integration name or ID on the current branch.",
        )
        setter.add_argument("--env", required=True, choices=["sandbox", "pre-release", "live"])
        setter.add_argument("--stdin", action="store_true", help="Read a JSON object from stdin.")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Collect credentials and configure the selected API integration."""
        project = load_project(args.path, output_json=args.json)
        integration = project.get_api_integration(args.integration, args.env)
        config = getattr(integration.environments, args.env.replace("-", "_"))
        interactive = sys.stdin.isatty() and not args.stdin and not args.json
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
            from poly.output.console import info

            token = _studio_token(project.region, interactive=True)
            existing = project.get_api_integration_credential_defaults(
                args.integration, args.env, token
            )
            info(
                f"Configure credentials for {integration.name} ({args.env}); updates apply directly."
            )
            values = _prompt_credentials(config.auth_type, existing)
        project.build_api_integration_credentials(config.auth_type, values)
        if args.stdin:
            token = _studio_token(project.region, interactive=False)
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
