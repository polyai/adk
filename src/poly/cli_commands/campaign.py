"""Copyright PolyAI Limited"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, require_outbound_campaigns_enabled
from poly.handlers.sdk import SourcererAPIError
from poly.output.json_output import json_print


class CampaignCommand(BaseCommand):
    """`poly campaign`: check outbound campaigns with the platform."""

    command = "campaign"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the `campaign` subcommands and their flags."""
        campaign_parser = subparsers.add_parser(
            "campaign",
            parents=[parents.verbose],
            help="Validate outbound campaigns.",
            description=(
                "Validate outbound campaigns.\n\n"
                "Edit a campaign in outbound_campaigns/<campaign>/ and `poly push` it\n"
                "first: these commands act on the campaign as pushed, not your files.\n\n"
                "Examples:\n"
                "  poly campaign validate 'Appointment reminders'\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        campaign_subparsers = campaign_parser.add_subparsers(
            dest="campaign_subcommand", required=True
        )
        common = [parents.path, parents.json, parents.verbose, parents.debug]

        validate_parser = campaign_subparsers.add_parser(
            "validate",
            parents=common,
            help="Check a campaign's graph with the platform.",
            description=(
                "Check a campaign as pushed to your current branch: one trigger, routes\n"
                "to nodes that exist, every node reachable, and each node function's\n"
                "def line. `poly validate` checks the files' shape locally; this asks\n"
                "the platform about the graph.\n\n"
                "Examples:\n"
                "  poly campaign validate 'Appointment reminders'\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        cls._add_name(validate_parser)

    @staticmethod
    def _add_name(parser: ArgumentParser) -> None:
        parser.add_argument("name", type=str, help="The campaign's name or folder.")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the chosen `campaign` subcommand; a failure prints its error and exits 1."""
        from poly.output.console import error

        try:
            cls.campaign_validate(args.path, args.name, output_json=args.json)
        except (ValueError, SourcererAPIError) as e:
            if args.json:
                json_print({"success": False, "error": str(e), "campaign": args.name})
            else:
                error(str(e))
            sys.exit(1)

    @staticmethod
    def _describe(issue: dict[str, Any]) -> str:
        where = issue.get("node") or issue.get("node_id")
        prefix = f"{where}: " if where else ""
        if issue.get("field"):
            prefix += f"{issue['field']}: "
        return f"{prefix}{issue.get('message')}"

    @classmethod
    def campaign_validate(cls, base_path: str, name: str, output_json: bool = False) -> None:
        """Validate a pushed campaign on the current branch and report its issues. Exits 1 if invalid."""
        from poly.output.console import error, success, warning

        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json, campaign=name)
        result = project.validate_campaign(name)
        valid = bool(result.get("valid"))
        if output_json:
            outcome = {"success": valid, "campaign": name, "result": result}
            if not valid:
                outcome["error"] = f"Campaign '{name}' is not valid."
            json_print(outcome)
            if not valid:
                sys.exit(1)
            return

        for issue in result.get("warnings") or []:
            warning(cls._describe(issue))
        if valid:
            success(f"Campaign '{name}' is valid.")
            return
        for issue in result.get("errors") or []:
            error(cls._describe(issue))
        error(f"Campaign '{name}' is not valid.")
        sys.exit(1)
