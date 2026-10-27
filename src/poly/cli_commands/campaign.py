"""Copyright PolyAI Limited"""

import json
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Callable, Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, require_outbound_campaigns_enabled
from poly.handlers.sdk import SourcererAPIError
from poly.output.json_output import json_print

LIFECYCLE_ACTIONS = {
    "publish": (
        "Publish the campaign's draft to live and start it.",
        "Publish campaign '{name}' to live? It starts contacting people.",
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
    """`poly campaign`: check, preview, test and run outbound campaigns."""

    command = "campaign"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the `campaign` subcommands and their flags."""
        campaign_parser = subparsers.add_parser(
            "campaign",
            parents=[parents.verbose],
            help="Validate, preview, test and run outbound campaigns.",
            description=(
                "Validate, preview, test and run outbound campaigns.\n\n"
                "Edit a campaign in outbound_campaigns/<campaign>/ and `poly push` it\n"
                "first: these commands act on the campaign as pushed, not your files.\n\n"
                "Examples:\n"
                "  poly campaign validate 'Appointment reminders'\n"
                "  poly campaign preview 'Appointment reminders' --phone +15550100\n"
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

        preview_parser = campaign_subparsers.add_parser(
            "preview",
            parents=common,
            help="Dry-run a campaign with a made-up contact. Nothing is sent.",
            description=(
                "Walk a made-up contact through a campaign as pushed to your current\n"
                "branch, to the next call, condition or end. Nothing is called, texted\n"
                "or stored, and node functions are not run: give what each returns\n"
                "with --sample-outputs.\n\n"
                "Examples:\n"
                "  poly campaign preview 'Appointment reminders' --phone +15550100 \\\n"
                "      --field first_name=Ada\n"
                "  poly campaign preview 'Appointment reminders' --contact contact.json \\\n"
                "      --sample-outputs outputs.json --start-node call-1 --call-result no_answer\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        cls._add_name(preview_parser)
        preview_parser.add_argument(
            "--contact",
            type=str,
            default=None,
            help="JSON file with the contact's data, as an import would carry it.",
        )
        preview_parser.add_argument("--phone", type=str, default=None, help="Contact's phone.")
        preview_parser.add_argument(
            "--first-name", type=str, default=None, help="Contact's first name."
        )
        cls._add_field(preview_parser, "Another contact column, as KEY=VALUE. Repeatable.")
        preview_parser.add_argument(
            "--sample-outputs",
            type=str,
            default=None,
            help="JSON file of what each node's function returns, keyed by node id.",
        )
        cls._add_continue_flags(preview_parser)
        preview_parser.add_argument(
            "--ask-branches",
            action="store_true",
            default=None,
            help="Stop at a condition with no sample output instead of taking its default.",
        )

        test_parser = campaign_subparsers.add_parser(
            "test",
            parents=common,
            help="Run one step of a real test of the live campaign. This calls and texts.",
            description=(
                "Run one step of a test of the live campaign: the copy on main, not your\n"
                "branch. It calls and texts the test contact for real, a step at a time,\n"
                "and waits for the step to finish. Asks for confirmation unless --force\n"
                "or --json is given.\n\n"
                "The first step starts at the trigger. To carry on, pass the node it\n"
                "stopped at and the run it printed.\n\n"
                "Examples:\n"
                "  poly campaign test 'Appointment reminders' --phone +15550100\n"
                "  poly campaign test 'Appointment reminders' --phone +15550100 \\\n"
                "      --start-node call-1 --run run.json --call-result no_answer\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        cls._add_name(test_parser)
        test_parser.add_argument(
            "--contact",
            type=str,
            default=None,
            help="JSON file with the test contact: phone, firstName, lastName, externalId, "
            "metadata.",
        )
        test_parser.add_argument("--phone", type=str, default=None, help="Number to call/text.")
        test_parser.add_argument("--first-name", type=str, default=None, help="First name.")
        test_parser.add_argument("--last-name", type=str, default=None, help="Last name.")
        test_parser.add_argument(
            "--external-id", type=str, default=None, help="Contact's id in your own system."
        )
        cls._add_field(test_parser, "A metadata column, as KEY=VALUE. Repeatable.")
        cls._add_continue_flags(test_parser)
        test_parser.add_argument(
            "--run",
            type=str,
            default=None,
            help="The run the previous step printed: a JSON object or a JSON file.",
        )
        test_parser.add_argument(
            "--timeout",
            type=float,
            default=600,
            help="Seconds to wait for the step to finish. Defaults to 600.",
        )
        cls._add_force(test_parser, "Run the test without confirmation.")

        for action, (help_text, _, _) in LIFECYCLE_ACTIONS.items():
            lifecycle_parser = campaign_subparsers.add_parser(
                action,
                parents=common,
                help=f"{help_text} Acts on live.",
                description=(
                    f"{help_text}\n\n"
                    "Acts on the live campaign, on main, whatever branch you are on: a\n"
                    "campaign made on a branch must be merged first. Asks for confirmation\n"
                    "unless --force or --json is given.\n\n"
                    "Examples:\n"
                    f"  poly campaign {action} 'Appointment reminders'\n"
                ),
                formatter_class=RawTextHelpFormatter,
            )
            cls._add_name(lifecycle_parser)
            cls._add_force(lifecycle_parser, f"{action.capitalize()} without confirmation.")

    @staticmethod
    def _add_name(parser: ArgumentParser) -> None:
        parser.add_argument("name", type=str, help="The campaign's name.")

    @staticmethod
    def _add_field(parser: ArgumentParser, help_text: str) -> None:
        parser.add_argument(
            "--field", action="append", default=[], metavar="KEY=VALUE", help=help_text
        )

    @staticmethod
    def _add_force(parser: ArgumentParser, help_text: str) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help=f"{help_text} This is default in non-interactive mode (e.g. when --json is used)",
        )

    @staticmethod
    def _add_continue_flags(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--start-node", type=str, default=None, help="Node id to carry on from."
        )
        parser.add_argument(
            "--call-result",
            type=str,
            default=None,
            help="How the call being left ended, e.g. no_answer.",
        )
        parser.add_argument(
            "--tool-called",
            action="append",
            default=[],
            help="A tool the agent called on that call. Repeatable.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the chosen `campaign` subcommand."""
        if args.campaign_subcommand == "validate":
            cls.campaign_validate(args.path, args.name, output_json=args.json)
        elif args.campaign_subcommand == "preview":
            cls.campaign_preview(
                args.path,
                args.name,
                contact_file=args.contact,
                phone=args.phone,
                first_name=args.first_name,
                fields=args.field,
                sample_outputs_file=args.sample_outputs,
                start_node=args.start_node,
                call_result=args.call_result,
                tools_called=args.tool_called,
                ask_branches=args.ask_branches,
                output_json=args.json,
            )
        elif args.campaign_subcommand == "test":
            cls.campaign_test(
                args.path,
                args.name,
                contact_file=args.contact,
                phone=args.phone,
                first_name=args.first_name,
                last_name=args.last_name,
                external_id=args.external_id,
                fields=args.field,
                start_node=args.start_node,
                run=args.run,
                call_result=args.call_result,
                tools_called=args.tool_called,
                timeout=args.timeout,
                force=args.force,
                output_json=args.json,
            )
        else:
            cls.campaign_lifecycle(
                args.path,
                args.campaign_subcommand,
                args.name,
                force=args.force,
                output_json=args.json,
            )

    @staticmethod
    def _fail(message: str, output_json: bool) -> None:
        from poly.output.console import error

        if output_json:
            json_print({"success": False, "error": message})
        else:
            error(message)
        sys.exit(1)

    @classmethod
    def _call(cls, output_json: bool, action: Callable[[], Any]) -> Any:
        try:
            return action()
        except (ValueError, SourcererAPIError, TimeoutError) as e:
            cls._fail(str(e), output_json)

    @staticmethod
    def _read_json(value: str, what: str) -> Any:
        text = value
        if os.path.isfile(value):
            with open(value, encoding="utf-8") as file:
                text = file.read()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"{what} is not valid JSON: {e}") from e

    @staticmethod
    def _parse_fields(fields: list[str]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for item in fields:
            key, separator, value = item.partition("=")
            if not separator or not key:
                raise ValueError(f"--field expects KEY=VALUE, got '{item}'.")
            try:
                parsed[key] = json.loads(value)
            except json.JSONDecodeError:
                parsed[key] = value
        return parsed

    @staticmethod
    def _node_labels(project: Any, name: str) -> dict[str, str]:
        try:
            campaign = project.get_campaign(name)
        except ValueError:
            return {}
        return {
            node["id"]: node.get("label") or node["id"]
            for node in campaign.nodes or []
            if isinstance(node, dict) and node.get("id")
        }

    @classmethod
    def campaign_validate(cls, base_path: str, name: str, output_json: bool = False) -> None:
        """Validate a pushed campaign on the current branch and report its issues. Exits 1 if invalid."""
        from poly.output.console import error, success, warning

        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json)
        result = cls._call(output_json, lambda: project.validate_campaign(name))
        valid = bool(result.get("valid"))
        if output_json:
            json_print({"success": valid, "campaign": name, "result": result})
            if not valid:
                sys.exit(1)
            return

        labels = cls._node_labels(project, name)

        def describe(issue: dict) -> str:
            where = labels.get(issue.get("node_id"), issue.get("node_id"))
            prefix = f"{where}: " if where else ""
            if issue.get("field"):
                prefix += f"{issue['field']}: "
            return f"{prefix}{issue.get('message')}"

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
    def _print_steps(cls, project: Any, name: str, result: dict) -> None:
        from poly.output.console import error, info, plain

        labels = cls._node_labels(project, name)
        for number, step in enumerate(result.get("steps") or [], start=1):
            node = labels.get(step.get("node_id"), step.get("node_id"))
            line = f"{number}. {node} ({step.get('node_type')})"
            if step.get("dispatch_channel"):
                line += f" via {step['dispatch_channel']}"
            if step.get("branch_taken"):
                line += f", branch {step['branch_taken']}"
            if step.get("next_node_id"):
                line += f" -> {labels.get(step['next_node_id'], step['next_node_id'])}"
            plain(line)
            if step.get("resolved_message"):
                plain(f"   message: {step['resolved_message']}")
            if step.get("skipped_wait_seconds"):
                plain(f"   skipped a wait of {step['skipped_wait_seconds']}s")
            if step.get("exit_reason"):
                plain(f"   exit reason: {step['exit_reason']}")
        stopped_at = labels.get(result.get("stopped_at"), result.get("stopped_at"))
        info(f"Stopped: {result.get('stop_reason')}" + (f" at {stopped_at}" if stopped_at else ""))
        if result.get("resume_node_id"):
            info(f"Carries on from: {result['resume_node_id']}")
        if result.get("error"):
            failure = result["error"]
            where = labels.get(failure.get("node_id"), failure.get("node_id"))
            error(f"{failure.get('error')}" + (f" at {where}" if where else ""))
        for note in result.get("notes") or []:
            plain(f"note: {note}")

    @classmethod
    def campaign_preview(
        cls,
        base_path: str,
        name: str,
        contact_file: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        fields: Optional[list[str]] = None,
        sample_outputs_file: Optional[str] = None,
        start_node: Optional[str] = None,
        call_result: Optional[str] = None,
        tools_called: Optional[list[str]] = None,
        ask_branches: Optional[bool] = None,
        output_json: bool = False,
    ) -> None:
        """Dry-run a made-up contact through a campaign and print the steps. Nothing is sent."""

        def build_inputs() -> tuple[dict, Optional[dict]]:
            contact = cls._read_json(contact_file, "--contact") if contact_file else {}
            if not isinstance(contact, dict):
                raise ValueError("--contact must hold a JSON object.")
            contact.update({"phone": phone} if phone else {})
            contact.update({"first_name": first_name} if first_name else {})
            contact.update(cls._parse_fields(fields or []))
            outputs = (
                cls._read_json(sample_outputs_file, "--sample-outputs")
                if sample_outputs_file
                else None
            )
            return contact, outputs

        contact, outputs = cls._call(output_json, build_inputs)
        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json)
        result = cls._call(
            output_json,
            lambda: project.preview_campaign(
                name,
                contact,
                sample_outputs=outputs,
                start_node_id=start_node,
                call_result=call_result,
                tools_called=tools_called,
                ask_branches=ask_branches,
            ),
        )
        failed = result.get("stop_reason") == "error"
        if output_json:
            json_print({"success": not failed, "campaign": name, "result": result})
        else:
            cls._print_steps(project, name, result)
        if failed:
            sys.exit(1)

    @classmethod
    def campaign_test(
        cls,
        base_path: str,
        name: str,
        contact_file: Optional[str] = None,
        phone: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        external_id: Optional[str] = None,
        fields: Optional[list[str]] = None,
        start_node: Optional[str] = None,
        run: Optional[str] = None,
        call_result: Optional[str] = None,
        tools_called: Optional[list[str]] = None,
        timeout: float = 600,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Run one real test step on the live campaign and wait for its result."""
        import questionary

        from poly.output.console import error, info, success, warning

        def build_inputs() -> tuple[dict, Optional[dict]]:
            contact = cls._read_json(contact_file, "--contact") if contact_file else {}
            if not isinstance(contact, dict):
                raise ValueError("--contact must hold a JSON object.")
            for key, value in (
                ("phone", phone),
                ("firstName", first_name),
                ("lastName", last_name),
                ("externalId", external_id),
            ):
                if value:
                    contact[key] = value
            if fields:
                contact["metadata"] = {
                    **(contact.get("metadata") or {}),
                    **cls._parse_fields(fields),
                }
            previous_run = cls._read_json(run, "--run") if run else None
            if previous_run is not None and not isinstance(previous_run, dict):
                raise ValueError("--run must be a JSON object.")
            return contact, previous_run

        contact, previous_run = cls._call(output_json, build_inputs)
        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json)
        campaign = cls._call(output_json, lambda: project.get_campaign(name))

        if not output_json and not force:
            if not questionary.confirm(
                f"Test live campaign '{campaign.name}'? "
                f"This calls and texts {contact.get('phone')}.",
                default=False,
                auto_enter=False,
            ).ask():
                warning("Aborted.")
                sys.exit(0)

        started = cls._call(
            output_json,
            lambda: project.start_campaign_test(
                name,
                contact,
                start_node_id=start_node,
                run=previous_run,
                call_result=call_result,
                tools_called=tools_called,
            ),
        )
        if not output_json:
            info(f"Started test step {started.get('step_id')} of campaign '{campaign.name}'.")
        step = cls._call(
            output_json,
            lambda: project.wait_for_campaign_test_step(name, started["step_id"], timeout=timeout),
        )
        done = step.get("status") == "done"
        if output_json:
            json_print({"success": done, "campaign": name, "test_step": step})
        else:
            if step.get("result"):
                cls._print_steps(project, name, step["result"])
            if done:
                success(f"Test step finished. Run: {json.dumps(step.get('run'))}")
            else:
                failure = (step.get("error") or {}).get("error")
                error(f"Test step {step.get('status')}" + (f": {failure}" if failure else "."))
        if not done:
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
        require_outbound_campaigns_enabled(project, output_json=output_json)
        campaign = cls._call(output_json, lambda: project.get_campaign(name))
        if not output_json and not force:
            if not questionary.confirm(
                prompt.format(name=campaign.name), default=False, auto_enter=False
            ).ask():
                warning("Aborted.")
                sys.exit(0)

        method = getattr(project, f"{action}_campaign")
        cls._call(output_json, lambda: method(name))
        if output_json:
            json_print({"success": True, "campaign": name, "action": action})
        else:
            success(done_message.format(name=campaign.name))
