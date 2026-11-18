"""Copyright PolyAI Limited"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Callable, Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, require_outbound_campaigns_enabled
from poly.handlers.sdk import InterruptedBeforeSending, SourcererAPIError
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

    @staticmethod
    def _fail(message: str, output_json: bool, exit_code: int = 1, **details: Any) -> None:
        from poly.output.console import error

        if output_json:
            json_print({"success": False, "error": message, **details})
        else:
            error(message)
        sys.exit(exit_code)

    @classmethod
    def _call(
        cls,
        output_json: bool,
        operation: Callable[[], Any],
        interrupted: Optional[str] = None,
        interrupted_unconfirmed: bool = False,
        **details: Any,
    ) -> Any:
        from poly.project import CampaignOutcomeUnconfirmed

        try:
            return operation()
        except CampaignOutcomeUnconfirmed as e:
            cls._fail(str(e), output_json, **details, unconfirmed=True)
        except (ValueError, SourcererAPIError) as e:
            cls._fail(str(e), output_json, **details)
        except InterruptedBeforeSending:
            cls._fail("Stopped before anything was sent.", output_json, exit_code=130, **details)
        except KeyboardInterrupt:
            if interrupted is None:
                raise
            if interrupted_unconfirmed:
                details["unconfirmed"] = True
            cls._fail(interrupted, output_json, exit_code=130, **details)

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
        campaign = cls._call(output_json, lambda: project.get_live_campaign(name), campaign=name)
        if not output_json and not force:
            if not questionary.confirm(
                prompt.format(name=campaign.name), default=False, auto_enter=False
            ).ask():
                warning("Aborted.")
                sys.exit(0)

        method = getattr(project, f"{action}_campaign")
        cls._call(
            output_json,
            lambda: method(name),
            interrupted=project.campaign_change_unconfirmed(
                "You stopped the command while it was being sent", action, campaign.name
            ),
            interrupted_unconfirmed=True,
            campaign=name,
            action=action,
        )
        if output_json:
            json_print({"success": True, "campaign": name, "action": action})
        else:
            success(done_message.format(name=campaign.name))
