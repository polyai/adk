"""Chat command family: interactive chat sessions with the agent.

Copyright PolyAI Limited
"""

import json
import os
import sys
from argparse import (
    ArgumentParser,
    ArgumentTypeError,
    Namespace,
    RawTextHelpFormatter,
    _SubParsersAction,
)
from contextlib import nullcontext
from typing import Optional

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print
from poly.project import AgentStudioProject


def _parse_sip_header(value: str) -> tuple[str, str]:
    """Parse a SIP header supplied as NAME=VALUE."""
    name, separator, header_value = value.partition("=")
    name = name.strip()
    if not separator or not name:
        raise ArgumentTypeError("SIP headers must use NAME=VALUE format")
    if "\r" in value or "\n" in value:
        raise ArgumentTypeError("SIP headers cannot contain newlines")
    return name, header_value


class ChatCommand(BaseCommand):
    """Start an interactive chat session with the agent."""

    command = "chat"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``chat`` subcommand."""
        chat_parser = subparsers.add_parser(
            "chat",
            parents=[parents.verbose, parents.debug, parents.json],
            help="Start an interactive chat session with the agent.",
            description=(
                "Start an interactive chat session with the agent.\n\n"
                "Examples:\n"
                "  poly chat\n"
                "  poly chat --environment live\n"
                "  poly chat --path /path/to/project -e sandbox\n"
                "  poly chat --sip-header X-Customer-ID=12345\n"
                "  poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB\n"
                "\n"
                "Non-interactive (scripted) mode:\n"
                "  poly chat -m 'Hello' -m 'What can you help with?'\n"
                "  poly chat --input-file ./script.txt\n"
                "  echo -e 'Hello\\nGoodbye' | poly chat --input-file -\n"
                "\n"
                "Resume an existing conversation:\n"
                "  poly chat --conv-id <conversation_id>\n"
                "  poly chat --conv-id <conversation_id> -m 'Follow-up message'\n"
                "\n"
                "Machine-readable output (emits a single JSON object when done):\n"
                "  poly chat --json -m 'Hello'\n"
                "  poly chat --json --input-file ./script.txt\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        chat_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )
        chat_parser.add_argument(
            "--environment",
            "-e",
            type=str,
            default="branch",
            choices=["branch", "sandbox", "pre-release", "live"],
            help="Environment to chat against. Defaults to current branch.",
        )
        chat_parser.add_argument(
            "--variant",
            type=str,
            default=None,
            help="Name of variant to use for the chat session.",
        )
        chat_parser.add_argument(
            "--lang",
            type=str,
            help="Language tag for both input and output messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--input-lang",
            type=str,
            help="Language tag for input messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--output-lang",
            type=str,
            help="Language tag for output messages (e.g. en-US, fr-FR). If not specified use default for project",
        )
        chat_parser.add_argument(
            "--channel",
            type=str,
            default="voice",
            choices=["voice", "webchat"],
            help="Channel to chat against. Defaults to voice.",
        )
        chat_parser.add_argument(
            "--sip-header",
            dest="sip_headers",
            action="append",
            type=_parse_sip_header,
            metavar="NAME=VALUE",
            help=("Simulate a SIP header at conversation start. Repeat for multiple headers."),
        )
        chat_parser.add_argument(
            "--functions",
            action="store_true",
            default=False,
            help="Show function/tool calls made each turn.",
        )
        chat_parser.add_argument(
            "--flows",
            action="store_true",
            default=False,
            help="Show the active flow and step each turn.",
        )
        chat_parser.add_argument(
            "--state",
            action="store_true",
            default=False,
            help="Show per-turn state variable changes.",
        )
        chat_parser.add_argument(
            "--metadata",
            action="store_true",
            default=False,
            help="Show all metadata (functions, flows, and state). Equivalent to --functions --flows --state.",
        )
        chat_parser.add_argument(
            "--push",
            action="store_true",
            default=False,
            help="Push the project before starting the chat session.",
        )
        chat_parser.add_argument(
            "--message",
            "-m",
            action="append",
            dest="messages",
            metavar="MSG",
            help="Send a message non-interactively (repeatable).",
        )
        chat_parser.add_argument(
            "--input-file",
            type=str,
            default=None,
            metavar="FILE",
            help="Read messages line-by-line from a file (- for stdin).",
        )
        chat_parser.add_argument(
            "--conversation-id",
            "--conv-id",
            type=str,
            default=None,
            help="Reuse an existing conversation ID instead of starting a new conversation.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the chat handler, reading input file/stdin if needed."""
        from poly.output.console import error

        show_all = args.metadata
        input_messages = None
        input_lang = args.input_lang or args.lang
        output_lang = args.output_lang or args.lang
        if args.input_file:
            try:
                if args.input_file == "-":
                    with nullcontext(sys.stdin) as f:
                        src = f.read()
                else:
                    with open(args.input_file, "r", encoding="utf-8") as f:
                        src = f.read()
            except FileNotFoundError:
                if args.json:
                    json_print(
                        {
                            "success": False,
                            "error": f"Input file not found: {args.input_file}",
                        }
                    )
                else:
                    error(f"Input file not found: {args.input_file}")
                sys.exit(1)
            with src:
                input_messages = [line.rstrip("\r\n") for line in src]
        elif args.messages:
            input_messages = args.messages
        cls.chat(
            args.path,
            args.environment,
            args.variant,
            args.channel,
            input_lang=input_lang,
            output_lang=output_lang,
            sip_headers=dict(args.sip_headers or []) or None,
            show_functions=show_all or args.functions,
            show_flow=show_all or args.flows,
            show_state=show_all or args.state,
            push_before_chat=args.push,
            input_messages=input_messages,
            conversation_id=args.conversation_id,
            output_json=args.json,
        )

    @classmethod
    def chat(
        cls,
        base_path: str,
        environment: str = None,
        variant: str = None,
        channel: str = None,
        input_lang: str = None,
        push_before_chat: bool = False,
        output_lang: str = None,
        sip_headers: Optional[dict[str, str]] = None,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
        output_json: bool = False,
        input_messages: Optional[list[str]] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Start an interactive chat session with the agent."""
        import requests

        from poly.output.console import error, info, plain, print_turn_metadata, success

        project = load_project(base_path)

        json_output = {}

        if push_before_chat:
            if not output_json:
                info("Pushing project before starting chat session...")
            push_success, output, _ = project.push_project(
                force=False,
                skip_validation=False,
                dry_run=False,
                format=False,
            )
            if output == "No changes detected":
                push_success = True  # Not an error if there are no changes to push

            if push_success:
                if not output_json:
                    success("Project pushed successfully.")
                else:
                    json_output["push"] = {"success": True, "message": output}

            if not push_success:
                if output_json:
                    json_output["push"] = {
                        "success": False,
                        "message": "Failed to push project before chat session.",
                        "error": output,
                    }
                    json_print(json_output)
                else:
                    error(
                        f"Failed to push {project.account_id}/{project.project_id} to Agent Studio."
                    )
                    plain(output)
                sys.exit(1)

        branch_id = project.branch_id
        branch_label = None

        if environment == "branch":
            if branch_id and branch_id != "main":
                branch_label = project.get_current_branch() or branch_id
                environment = "draft" if branch_label != "main" else "sandbox"
            else:
                environment = "sandbox"
        else:
            environment = environment or "sandbox"

        channel_map = {"voice": "chat.polyai", "webchat": "webchat.polyai"}
        channel = channel_map.get(channel, "chat.polyai")

        label = f"[bold]{project.account_id}/{project.project_id}[/bold]"
        if branch_label:
            label += f" branch=[bold]{branch_label}[/bold]"
        else:
            label += f" ({environment})"
        if variant:
            label += f" variant=[bold]{variant}[/bold]"
        if not output_json:
            info(f"Starting chat for {label}...")

        conversations: list[dict] = []
        while True:
            if conversation_id:
                if not output_json:
                    info(f"Resuming chat session (conversation: {conversation_id})...")
                response = None
            else:
                if environment == "draft" and not output_json:
                    info("Preparing branch deployment...")
                try:
                    response = project.create_chat_session(
                        environment,
                        channel,
                        variant,
                        input_lang,
                        output_lang,
                        sip_headers=sip_headers,
                    )
                except (requests.HTTPError, ValueError) as e:
                    if output_json:
                        json_output["success"] = False
                        json_output["error"] = str(e)
                        json_print(json_output)
                    else:
                        error(f"Failed to create chat session: {e}")
                    return

                conversation_id = response.get("conversation_id")
                if not conversation_id:
                    if output_json:
                        json_output["success"] = False
                        json_output["error"] = "No conversation_id in response"
                        json_output["response"] = response
                        json_print(json_output)
                    else:
                        error(f"Unexpected response when creating chat: {response}")
                    return

                url = project.get_conversation_url(conversation_id)
                greeting = response.get("response", "")
                if not output_json:
                    success(
                        f"Chat session started (conversation: [link={url}]{conversation_id}[/link])"
                    )
                    print_turn_metadata(response, show_functions, show_flow, show_state)
                    if greeting:
                        plain(f"\n[bold]Agent:[/bold] {greeting}")

                if response.get("conversation_ended"):
                    if not output_json:
                        plain("[muted]Conversation ended by agent.[/muted]")
                    return

            if not output_json:
                plain(
                    "[muted]Type your messages below. "
                    "Press Ctrl+C or type '/exit' to quit. "
                    "Type '/restart' to begin a new chat.[/muted]"
                )

            restart, conversation = cls._run_chat_loop(
                project,
                conversation_id,
                environment,
                input_lang=input_lang,
                output_lang=output_lang,
                show_functions=show_functions,
                show_flow=show_flow,
                show_state=show_state,
                input_messages=input_messages,
                output_json=output_json,
                initial_response=response,
            )

            if output_json:
                conversations.append(conversation)

            if not restart:
                if output_json:
                    json_output["conversations"] = conversations
                    json_print(json_output)
                return
            if not output_json:
                info("Restarting chat session...")

            # Create a new chat session in the next loop iteration
            conversation_id = None

    @classmethod
    def _run_chat_loop(
        cls,
        project: AgentStudioProject,
        conversation_id: str,
        environment: str,
        input_lang: str = None,
        output_lang: str = None,
        show_functions: bool = False,
        show_flow: bool = False,
        show_state: bool = False,
        input_messages: Optional[list[str]] = None,
        output_json: bool = False,
        initial_response: Optional[dict] = None,
    ) -> tuple[bool, dict]:
        """Run the interactive message loop.

        Returns:
            A tuple of (restart, conversation) where restart is True if the user
            requested a new session, and conversation is a dict with conversation_id,
            url, and turns (populated when output_json=True).
        """
        import requests

        from poly.output.console import error, info, plain, print_turn_metadata, warning

        conversation_ended = False
        restart = False
        url = project.get_conversation_url(conversation_id)
        turns: list[dict] = (
            [
                {
                    "input": None,
                    **cls._process_json_chat_reply(
                        initial_response, show_functions, show_flow, show_state
                    ),
                }
            ]
            if output_json and initial_response is not None
            else []
        )
        end_call = False
        try:
            while True:
                if input_messages is not None:
                    if not input_messages:
                        break
                    user_input = input_messages.pop(0).strip()
                    if not output_json:
                        plain(f"\n[muted]You:[/muted] {user_input}")
                else:
                    try:
                        user_input = input("\nYou: ").strip()
                    except (KeyboardInterrupt, EOFError):
                        if not output_json:
                            plain("")
                        break

                if user_input is None:
                    continue
                if user_input.lower() == "/exit":
                    end_call = True
                    break
                if user_input.lower() == "/restart":
                    restart = True
                    end_call = True
                    break

                try:
                    reply = project.send_message(
                        conversation_id, user_input, environment, input_lang, output_lang
                    )
                except requests.HTTPError as e:
                    if output_json:
                        turns.append({"input": user_input, "error": str(e)})
                    else:
                        error(f"Failed to send message: {e}")
                    continue

                if output_json:
                    # Filter reply for relevant fields to avoid dumping large state
                    processed_reply = cls._process_json_chat_reply(
                        reply, show_functions, show_flow, show_state
                    )
                    turns.append({"input": user_input, **processed_reply})
                else:
                    print_turn_metadata(reply, show_functions, show_flow, show_state)
                    agent_text = reply.get("response") or json.dumps(reply, indent=2)
                    plain(f"\n[bold]Agent:[/bold] {agent_text}")

                if reply.get("conversation_ended"):
                    conversation_ended = True
                    if not output_json:
                        plain("[muted]Conversation ended by agent.[/muted]")
                    break
        finally:
            if end_call or (not conversation_ended and not output_json):
                try:
                    project.end_chat(conversation_id, environment)
                    if not output_json:
                        info(f"Chat session ended (conversation: {conversation_id})")
                        plain(f"[info]Call Link:[/info] [link={url}]{url}[/link]")
                except requests.HTTPError:
                    if not output_json:
                        warning("Failed to end chat session on server.")

        if input_messages and not restart:
            # If the conversation ended, but there is still a restart queued in input messages
            # Pop the remaining messages until we get to a restart
            while input_messages:
                msg = input_messages.pop(0).strip()
                if msg.lower() == "/restart":
                    restart = True
                    break

        return restart, {"conversation_id": conversation_id, "url": url, "turns": turns}

    @staticmethod
    def _process_json_chat_reply(
        reply: dict, show_functions: bool, show_flow: bool, show_state: bool
    ) -> dict:
        """Process the raw reply from the chat API to extract relevant information based on the flags."""
        processed_json = dict(
            response=reply.get("response"),
            conversation_ended=reply.get("conversation_ended", False),
        )
        turn_metadata = reply.get("metadata") or {}
        if show_functions:
            function_replies = []
            for function_event in turn_metadata.get("function_events") or []:
                function_reply = {
                    "name": function_event.get("name"),
                    "arguments": function_event.get("arguments"),
                    "utterance": function_event.get("utterance"),
                    "hangup": function_event.get("hangup"),
                    "handoff": function_event.get("handoff"),
                    "error": function_event.get("error"),
                    "logs": function_event.get("logs"),
                    "transition": function_event.get("transition"),
                }
                filtered_function_reply = {k: v for k, v in function_reply.items() if v is not None}
                function_replies.append(filtered_function_reply)

            processed_json["function_events"] = function_replies

        if show_flow:
            flow_reply = {}
            in_flow = turn_metadata.get("in_flow")
            in_step = turn_metadata.get("in_step")
            if in_flow:
                flow_reply["in_flow"] = in_flow
            if in_step:
                flow_reply["in_step"] = in_step
            if flow_reply:
                processed_json["flow"] = flow_reply

        if show_state:
            state_reply = []
            for function_event in turn_metadata.get("function_events") or []:
                sc = function_event.get("state_changes") or {}
                added = sc.get("added", {})
                updated = sc.get("updated", {})
                removed = sc.get("removed", [])
                if added or updated or removed:
                    event_state_reply = {}
                    if added:
                        event_state_reply["added"] = added
                    if updated:
                        event_state_reply["updated"] = updated
                    if removed:
                        event_state_reply["removed"] = removed
                    state_reply.append(event_state_reply)
            if state_reply:
                processed_json["state_changes"] = state_reply

        return processed_json
