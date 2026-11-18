"""Copyright PolyAI Limited"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Callable

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
        """Dispatch to the chosen `campaign` subcommand, keeping stdout JSON under `--json`."""
        try:
            cls._dispatch(args)
        except KeyboardInterrupt:
            if not args.json:
                raise
            json_print({"success": False, "error": "Stopped.", "campaign": args.name})
            sys.exit(130)

    @classmethod
    def _dispatch(cls, args: Namespace) -> None:
        cls.campaign_validate(args.path, args.name, output_json=args.json)

    @staticmethod
    def _fail(message: str, output_json: bool, exit_code: int = 1, **details: Any) -> None:
        from poly.output.console import error

        if output_json:
            json_print({"success": False, "error": message, **details})
        else:
            error(message)
        sys.exit(exit_code)

    @classmethod
    def _call(cls, output_json: bool, operation: Callable[[], Any], **details: Any) -> Any:
        try:
            return operation()
        except (ValueError, SourcererAPIError) as e:
            cls._fail(str(e), output_json, **details)

    @staticmethod
    def _node_labels(project: Any, name: str) -> dict[str, str]:
        try:
            return project.campaign_node_names(project.get_campaign(name))
        except (ValueError, SourcererAPIError):
            return {}

    @staticmethod
    def _name_nodes(text: str, labels: dict[str, str]) -> str:
        for node_id in sorted(labels, key=len, reverse=True):
            if labels[node_id]:
                text = text.replace(node_id, labels[node_id])
        return text

    @classmethod
    def _branch_note(cls, project: Any, name: str, output_json: bool) -> dict[str, str]:
        from poly.output.console import warning

        if not cls._call(output_json, project.campaign_branch_is_gone, campaign=name):
            return {}
        if not output_json:
            warning("Your branch no longer exists, so this ran on main.")
        return {"branch": "main"}

    @classmethod
    def campaign_validate(cls, base_path: str, name: str, output_json: bool = False) -> None:
        """Validate a pushed campaign on the current branch and report its issues. Exits 1 if invalid."""
        from poly.output.console import error, success, warning

        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json, campaign=name)
        branch = cls._branch_note(project, name, output_json)
        result = cls._call(output_json, lambda: project.validate_campaign(name), campaign=name)
        valid = bool(result.get("valid"))
        if output_json:
            outcome = {"success": valid, "campaign": name, **branch, "result": result}
            if not valid:
                outcome["error"] = f"Campaign '{name}' is not valid."
            json_print(outcome)
            if not valid:
                sys.exit(1)
            return

        labels = cls._node_labels(project, name)

        def describe(issue: dict) -> str:
            where = labels.get(issue.get("node_id"), issue.get("node_id"))
            prefix = f"{where}: " if where else ""
            if issue.get("field"):
                prefix += f"{issue['field']}: "
            return f"{prefix}{cls._name_nodes(str(issue.get('message')), labels)}"

        for issue in result.get("warnings") or []:
            warning(describe(issue))
        if valid:
            success(f"Campaign '{name}' is valid.")
            return
        for issue in result.get("errors") or []:
            error(describe(issue))
        error(f"Campaign '{name}' is not valid.")
        sys.exit(1)
