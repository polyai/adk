"""Copyright PolyAI Limited"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, require_outbound_campaigns_enabled
from poly.handlers.sdk import SourcererAPIError
from poly.output.json_output import json_print

LIFECYCLE_ACTIONS = {
    "publish": (
        "Publish the campaign's draft to live. It starts contacting people unless the "
        "campaign is paused.",
        "Publish campaign '{name}' to live? It starts contacting people unless the campaign is "
        "paused.",
        "Published campaign '{name}'.",
    ),
    "pause": (
        "Pause the live campaign.",
        "Pause live campaign '{name}'?",
        "Paused campaign '{name}'.",
    ),
    "resume": (
        "Resume the paused live campaign.",
        "Resume live campaign '{name}'? It starts contacting people again.",
        "Resumed campaign '{name}'.",
    ),
    "archive": (
        "Archive the campaign. It must be a draft or paused; archiving cannot be undone.",
        "Archive campaign '{name}'? This cannot be undone.",
        "Archived campaign '{name}'.",
    ),
}


class CampaignCommand(BaseCommand):
    """`poly campaign`: check and run outbound campaigns."""

    command = "campaign"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the `campaign` subcommands and their flags."""
        campaign_parser = subparsers.add_parser(
            "campaign",
            parents=[parents.verbose],
            help="Validate and run outbound campaigns.",
            description=(
                "Validate and run outbound campaigns.\n\n"
                "Edit a campaign in outbound_campaigns/<campaign>/ and `poly push` it\n"
                "first: these commands act on the campaign as pushed, not your files.\n\n"
                "Examples:\n"
                "  poly campaign validate 'Appointment reminders'\n"
                "  poly campaign publish 'Appointment reminders'\n"
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

        for action, (help_text, _, _) in LIFECYCLE_ACTIONS.items():
            lifecycle_parser = campaign_subparsers.add_parser(
                action,
                parents=common,
                help=f"{help_text} Acts on live.",
                description=(
                    f"{help_text}\n\n"
                    "Acts on the live campaign, on main, whatever branch you are on: a\n"
                    "campaign made on a branch must be merged first. Asks for confirmation\n"
                    "unless --force or --json is given. If the change is not confirmed,\n"
                    "the error says how to settle it.\n\n"
                    "Examples:\n"
                    f"  poly campaign {action} 'Appointment reminders'\n"
                ),
                formatter_class=RawTextHelpFormatter,
            )
            cls._add_name(lifecycle_parser)
            cls._add_force(lifecycle_parser, f"{action.capitalize()} without confirmation.")

    @staticmethod
    def _add_name(parser: ArgumentParser) -> None:
        parser.add_argument("name", type=str, help="The campaign's name or folder.")

    @staticmethod
    def _add_force(parser: ArgumentParser, help_text: str) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help=f"{help_text} This is default in non-interactive mode (e.g. when --json is used)",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the chosen `campaign` subcommand; a failure prints its error and exits 1."""
        from poly.output.console import error
        from poly.project import CampaignOutcomeUnconfirmed

        details: dict[str, Any] = {"campaign": args.name}
        if args.campaign_subcommand in LIFECYCLE_ACTIONS:
            details["action"] = args.campaign_subcommand
        try:
            if args.campaign_subcommand == "validate":
                cls.campaign_validate(args.path, args.name, output_json=args.json)
            else:
                cls.campaign_lifecycle(
                    args.path,
                    args.campaign_subcommand,
                    args.name,
                    force=args.force,
                    output_json=args.json,
                )
        except (ValueError, SourcererAPIError) as e:
            if isinstance(e, CampaignOutcomeUnconfirmed):
                details["unconfirmed"] = True
            if args.json:
                json_print({"success": False, "error": str(e), **details})
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

    @classmethod
    def campaign_lifecycle(
        cls,
        base_path: str,
        action: str,
        name: str,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Publish, pause, resume or archive a live campaign after confirming."""
        import questionary

        from poly.output.console import success, warning

        _, prompt, done_message = LIFECYCLE_ACTIONS[action]
        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json, campaign=name)
        campaign = project.get_live_campaign(name)
        if not output_json and not force:
            if not questionary.confirm(
                prompt.format(name=campaign.name), default=False, auto_enter=False
            ).ask():
                warning("Aborted.")
                sys.exit(0)

        getattr(project, f"{action}_campaign")(name)
        if output_json:
            json_print({"success": True, "campaign": name, "action": action})
        else:
            success(done_message.format(name=campaign.name))
