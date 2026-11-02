"""Copyright PolyAI Limited"""

import json
import os
import shlex
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Callable, Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, require_outbound_campaigns_enabled
from poly.handlers.sdk import SourcererAPIError
from poly.output.json_output import json_print, json_progress

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
                "      --sample-outputs outputs.json --start-node 'Reminder call' \\\n"
                "      --result no_answer\n"
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
        cls._add_field(
            preview_parser,
            "Another contact column, as KEY=VALUE, the value read as JSON when it parses. "
            "Repeatable.",
        )
        preview_parser.add_argument(
            "--sample-outputs",
            type=str,
            default=None,
            help="JSON file of what each node's function returns, keyed by node name.",
        )
        cls._add_continue_flags(preview_parser)
        preview_parser.add_argument(
            "--last-send",
            type=str,
            default=None,
            help="The last_send the previous step printed: a JSON object or a JSON file.",
        )
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
                "The first step starts at the trigger. To carry on, pass the node and\n"
                "the run it printed; after a call or a text, also say how it went\n"
                "with --result.\n\n"
                "Examples:\n"
                "  poly campaign test 'Appointment reminders' --phone +15550100\n"
                "  poly campaign test 'Appointment reminders' --phone +15550100 \\\n"
                "      --start-node 'Reminder call' --run run.json --result no_answer\n"
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
        cls._add_field(
            test_parser,
            "A metadata column, as KEY=VALUE, the value read as JSON when it parses. Repeatable.",
        )
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
        parser.add_argument("name", type=str, help="The campaign's name or folder.")

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
            "--start-node", type=str, default=None, help="Name of the node to carry on from."
        )
        parser.add_argument(
            "--result",
            type=str,
            default=None,
            help="How the call or text at --start-node went, e.g. no_answer or replied.",
        )
        parser.add_argument(
            "--state",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help="A value that call or text reported back, as KEY=VALUE, the value read as JSON "
            "when it parses. Repeatable.",
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
                send_result=args.result,
                send_state=args.state,
                ask_branches=args.ask_branches,
                last_send=args.last_send,
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
                send_result=args.result,
                send_state=args.state,
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
        except (ValueError, SourcererAPIError, TimeoutError) as e:
            cls._fail(str(e), output_json, **details)
        except KeyboardInterrupt:
            if interrupted is None:
                raise
            if interrupted_unconfirmed:
                details["unconfirmed"] = True
            cls._fail(interrupted, output_json, exit_code=130, **details)

    @staticmethod
    def _read_json(value: str, what: str) -> Any:
        text = value
        if os.path.isfile(value):
            with open(value, encoding="utf-8") as file:
                text = file.read()
        elif not value.lstrip().startswith(("{", "[")) and (
            "/" in value or value.endswith(".json")
        ):
            raise ValueError(f"No file at {value} for {what}.")
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
    def _node_labels(project: Any, name: str, live: bool = False) -> dict[str, str]:
        try:
            campaign = project.get_live_campaign(name) if live else project.get_campaign(name)
            return project.campaign_node_names(campaign, live=live)
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
    def _print_steps(
        cls, labels: dict[str, str], result: dict, carry_on_values: dict[str, Any]
    ) -> None:
        from poly.output.console import error, info, plain

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
        carry_on = cls._carry_on_flags(result, labels, carry_on_values)
        if carry_on:
            info(f"Carry on with: {carry_on}")
        if result.get("error"):
            failure = result["error"]
            where = labels.get(failure.get("node_id"), failure.get("node_id"))
            error(f"{failure.get('error')}" + (f" at {where}" if where else ""))
        for note in result.get("notes") or []:
            plain(f"note: {note}")

    @staticmethod
    def _stopped_at_error(result: Optional[dict[str, Any]]) -> bool:
        return (result or {}).get("stop_reason") == "error"

    @classmethod
    def _preview_failure(cls, result: dict[str, Any]) -> Optional[str]:
        if cls._stopped_at_error(result):
            failure = result.get("error") or {}
            return f"The preview stopped at an error: {failure.get('error') or 'unknown'}."
        if result.get("stop_reason") == "step_cap":
            return "The path hit the step cap, which usually means the campaign loops."
        return None

    @classmethod
    def _test_failure(cls, step: dict[str, Any]) -> Optional[str]:
        status = step.get("status")
        failure = (step.get("error") or {}).get("error")
        if status == "done":
            if (step.get("result") or {}).get("stop_reason") == "step_cap":
                return "Test step hit the step cap, which usually means the campaign loops."
            if not cls._stopped_at_error(step.get("result")):
                return None
            failure = ((step.get("result") or {}).get("error") or {}).get("error")
            return "Test step stopped at an error" + (f": {failure}." if failure else ".")
        if status == "interrupted":
            return (
                "Test step was interrupted"
                + (f" ({failure})" if failure else "")
                + ". A call or text may already have gone out."
            )
        return f"Test step {status}" + (f": {failure}." if failure else ".")

    @staticmethod
    def _carry_on_flags(
        result: dict[str, Any],
        labels: dict[str, str],
        values: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        def node(node_id: str) -> str:
            return shlex.quote(labels.get(node_id, node_id))

        stop_reason = result.get("stop_reason")
        stopped_at = result.get("stopped_at")
        if stop_reason in ("call", "reply") and stopped_at:
            flags, after = [f"--start-node {node(stopped_at)}", "--result <how it went>"], ""
        elif stop_reason == "condition" and stopped_at:
            flags, after = (
                [f"--start-node {node(stopped_at)}"],
                ", with its branch in --sample-outputs",
            )
        elif stop_reason == "wait" and result.get("resume_node_id"):
            flags, after = [f"--start-node {node(result['resume_node_id'])}"], ""
        else:
            return None
        for flag, value in (values or {}).items():
            if value is not None:
                flags.append(f"--{flag} {shlex.quote(json.dumps(value))}")
        return " ".join(flags) + after

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
        send_result: Optional[str] = None,
        send_state: Optional[list[str]] = None,
        ask_branches: Optional[bool] = None,
        last_send: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Dry-run a made-up contact through a campaign and print the steps. Nothing is sent."""
        from poly.output.console import error

        def build_inputs() -> tuple[dict, Optional[dict], dict, Optional[dict]]:
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
            previous_send = cls._read_json(last_send, "--last-send") if last_send else None
            return contact, outputs, cls._parse_fields(send_state or []), previous_send

        contact, outputs, state, previous_send = cls._call(output_json, build_inputs, campaign=name)
        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json, campaign=name)
        branch = cls._branch_note(project, name, output_json)
        result = cls._call(
            output_json,
            lambda: project.preview_campaign(
                name,
                contact,
                sample_outputs=outputs,
                start_node=start_node,
                send_result=send_result,
                send_state=state,
                ask_branches=ask_branches,
                last_send=previous_send,
            ),
            campaign=name,
        )
        failure = cls._preview_failure(result)
        if output_json:
            outcome = {"success": failure is None, "campaign": name, **branch, "result": result}
            if failure:
                outcome["error"] = failure
            json_print(outcome)
        else:
            cls._print_steps(
                cls._node_labels(project, name),
                result,
                {"last-send": result.get("last_send")},
            )
            if result.get("stop_reason") == "step_cap":
                error(failure)
        if failure:
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
        send_result: Optional[str] = None,
        send_state: Optional[list[str]] = None,
        timeout: float = 600,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Run one real test step on the live campaign and wait for its result."""
        import questionary

        from poly.output.console import error, info, success, warning

        def build_inputs() -> tuple[dict, Optional[dict], dict]:
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
                if not isinstance(contact.get("metadata") or {}, dict):
                    raise ValueError("--contact's metadata must be a JSON object to add --field.")
                contact["metadata"] = {
                    **(contact.get("metadata") or {}),
                    **cls._parse_fields(fields),
                }
            previous_run = cls._read_json(run, "--run") if run else None
            if previous_run is not None and not isinstance(previous_run, dict):
                raise ValueError("--run must be a JSON object.")
            return contact, previous_run, cls._parse_fields(send_state or [])

        contact, previous_run, state = cls._call(output_json, build_inputs, campaign=name)
        project = load_project(base_path, output_json=output_json)
        require_outbound_campaigns_enabled(project, output_json=output_json, campaign=name)
        campaign = cls._call(output_json, lambda: project.get_live_campaign(name), campaign=name)
        body = cls._call(
            output_json,
            lambda: project.check_campaign_test(
                name,
                contact,
                start_node=start_node,
                run=previous_run,
                send_result=send_result,
                send_state=state,
            ),
            campaign=name,
        )

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
            lambda: project.start_campaign_test(name, contact, body=body),
            interrupted=project.campaign_test_unconfirmed(
                "You stopped the command while the step was starting",
                campaign.name,
                contact.get("phone"),
            ),
            interrupted_unconfirmed=True,
            campaign=name,
        )
        step_id, run_started = started.get("step_id"), started.get("run")
        if output_json:
            json_progress({"step_id": step_id, "run": run_started})
        else:
            info(f"Started test step {step_id} of campaign '{campaign.name}'.")
            info(f"Run: {shlex.quote(json.dumps(run_started))}")
        if not step_id:
            cls._fail(
                "The test step started, but the platform did not say which step it is.",
                output_json,
                campaign=name,
                step_id=step_id,
                run=run_started,
            )
        step = cls._call(
            output_json,
            lambda: project.wait_for_campaign_test_step(name, step_id, timeout=timeout),
            interrupted=f"Stopped waiting for test step {step_id}. The step carries on.",
            campaign=name,
            step_id=step_id,
            run=run_started,
        )
        failure = cls._test_failure(step)
        done = failure is None
        if output_json:
            outcome = {"success": done, "campaign": name, "test_step": step}
            if failure:
                outcome["error"] = failure
            json_print(outcome)
        else:
            if step.get("result"):
                cls._print_steps(
                    cls._node_labels(project, name, live=True),
                    step["result"],
                    {"run": step.get("run") or run_started},
                )
            if done:
                success("Test step finished.")
            else:
                error(failure)
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
