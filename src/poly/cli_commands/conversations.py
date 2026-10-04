"""Conversations command family: list and inspect conversations.

Copyright PolyAI Limited
"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Optional

import requests

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import (
    add_cohort_arguments,
    add_window_arguments,
    describe_data_api_error,
    load_project,
    parse_datetime_flag,
    parse_filter_flags,
    parse_sort_flag,
)
from poly.handlers.interface import AgentStudioInterface
from poly.output.json_output import json_print

SEARCH_DEFAULT_FIELDS = ["poly_score", "duration", "channel"]
SEARCH_SORT_FIELDS = ["started_at", "duration", "conversation_id"]


class ConversationsCommand(BaseCommand):
    """List and inspect conversations for the project."""

    command = "conversations"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``conversations`` subcommand tree."""
        conversations_parser = subparsers.add_parser(
            "conversations",
            parents=[parents.verbose],
            help="List and inspect conversations.",
            description=(
                "List and inspect conversations for the project.\n\n"
                "Examples:\n"
                "  poly conversations list\n"
                "  poly conversations get <conversation_id>\n"
                "  poly conversations get-audio <conversation_id> -o recording.wav\n"
                "  poly conversations search --filter poly_score lt 3 --env live\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        conversations_subparsers = conversations_parser.add_subparsers(
            dest="conversations_subcommand", required=True
        )

        conv_list_parser = conversations_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose],
            help="List conversations for the project.",
            description=(
                "List conversations for the project.\n\n"
                "Examples:\n"
                "  poly conversations list\n"
                "  poly conversations list --limit 20 --offset 10\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        conv_list_parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Max number of conversations to return. Defaults to 50.",
        )
        conv_list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of conversations to skip. Defaults to 0.",
        )

        search_parser = conversations_subparsers.add_parser(
            "search",
            parents=[parents.path, parents.json, parents.verbose],
            help="Find conversations by metric values, channel, environment and time.",
            description=(
                "Search the project's conversations through the Data API, filtering on\n"
                "metric values (names from `poly metrics available`), channel, environment\n"
                "and start time. Each row carries the metric fields you ask for with\n"
                "--field. Free-text fields such as call_summary are returned only when the\n"
                "API key has PII read permission.\n\n"
                "Examples:\n"
                "  poly conversations search --from 2026-09-01 --to 2026-09-30\n"
                "  poly conversations search --filter poly_score lt 3 --env live\n"
                "  poly conversations search --filter handoff eq true --field handoff_reason\n"
                "  poly conversations search --filter conversation_id in id1,id2 --field call_summary\n"
                "  poly conversations search --sort duration:desc --limit 5 --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        add_window_arguments(search_parser, default_help="Defaults to no lower bound.")
        search_parser.add_argument(
            "--filter",
            action="append",
            nargs=3,
            metavar=("METRIC", "OP", "VALUE"),
            default=None,
            help=(
                "Only conversations where METRIC OP VALUE. OP is one of eq, gt, gte, lt, lte,\n"
                "in, ex, contains, not_contains, exists (in/ex take a comma-separated list).\n"
                "METRIC may also be conversation_id or CUSTOM_SCORE_<id>. Repeatable."
            ),
        )
        search_parser.add_argument(
            "--any",
            action="store_true",
            default=False,
            help="Match conversations that satisfy any filter instead of all.",
        )
        add_cohort_arguments(search_parser, deployments=False)
        search_parser.add_argument(
            "--field",
            action="append",
            default=None,
            metavar="METRIC",
            help=(
                "Metric field to show per conversation. Repeatable. Defaults to "
                f"{', '.join(SEARCH_DEFAULT_FIELDS)}."
            ),
        )
        search_parser.add_argument(
            "--sort",
            type=str,
            default=None,
            metavar="FIELD[:asc|desc]",
            help=(f"Sort by one of {', '.join(SEARCH_SORT_FIELDS)}. Defaults to started_at:desc."),
        )
        search_parser.add_argument(
            "--limit", type=int, default=20, help="Conversations per page, 1 to 100."
        )
        search_parser.add_argument(
            "--offset", type=int, default=0, help="Conversations to skip, up to 1000."
        )

        conv_get_parser = conversations_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Get details for a specific conversation.",
            description=(
                "Get detailed information for a conversation including turns.\n"
                "For the full transcript with per-turn timestamps, use\n"
                "`poly transcripts get <conversation_id>`.\n\n"
                "Examples:\n"
                "  poly conversations get <conversation_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        conv_get_parser.add_argument(
            "conversation_id",
            type=str,
            help="The conversation ID.",
        )

        conv_audio_parser = conversations_subparsers.add_parser(
            "get-audio",
            parents=[parents.path, parents.json, parents.verbose],
            help="Download audio recording for a conversation.",
            description=(
                "Download the audio recording for a conversation as a WAV file.\n\n"
                "Examples:\n"
                "  poly conversations get-audio <conversation_id>\n"
                "  poly conversations get-audio <conversation_id> --direction user\n"
                "  poly conversations get-audio <conversation_id> --redacted -o redacted.wav\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        conv_audio_parser.add_argument(
            "conversation_id",
            type=str,
            help="The conversation ID.",
        )
        conv_audio_parser.add_argument(
            "--direction",
            type=str,
            default="combined",
            choices=["combined", "user", "agent"],
            help="Audio direction. Defaults to combined.",
        )
        conv_audio_parser.add_argument(
            "--redacted",
            action="store_true",
            help="Download redacted audio.",
        )
        conv_audio_parser.add_argument(
            "-o",
            "--output",
            type=str,
            help="Output file path. Defaults to <conversation_id>.wav.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching conversations sub-handler."""
        if args.conversations_subcommand == "list":
            cls.conversations_list(
                args.path,
                args.limit,
                args.offset,
                output_json=args.json,
            )
        elif args.conversations_subcommand == "search":
            cls.conversations_search(args.path, args, output_json=args.json)
        elif args.conversations_subcommand == "get":
            cls.conversations_get(
                args.path,
                args.conversation_id,
                output_json=args.json,
            )
        elif args.conversations_subcommand == "get-audio":
            cls.conversations_get_audio(
                args.path,
                args.conversation_id,
                direction=args.direction,
                redacted=args.redacted,
                output_path=args.output,
                output_json=args.json,
            )

    @classmethod
    def conversations_list(
        cls,
        base_path: str,
        limit: int = 50,
        offset: int = 0,
        output_json: bool = False,
    ) -> None:
        """List conversations for the project.

        Args:
            base_path: Base path for the project.
            limit: Max number of conversations to return.
            offset: Number of conversations to skip.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, paged_output, print_conversations

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.list_conversations(
            region=project.region,
            project_id=project.project_id,
            limit=limit,
            offset=offset,
        )
        conversations = result.get("conversations", [])

        if output_json:
            json_print(result)
        else:
            if not conversations:
                info("No conversations found.")
                return
            with paged_output():
                print_conversations(conversations, url_builder=project.get_conversation_url)

    @classmethod
    def conversations_search(
        cls, base_path: str, args: Namespace, output_json: bool = False
    ) -> None:
        """Search conversations through the Data API and print them with metric columns.

        Args:
            base_path: Base path for the project.
            args: Parsed ``search`` flags.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, paged_output, print_conversation_search

        try:
            body = cls._build_search_body(args)
        except ValueError as e:
            cls._fail(str(e), output_json)

        project = load_project(base_path, output_json=output_json)
        body["project_id"] = project.project_id
        try:
            result = AgentStudioInterface.search_conversations(region=project.region, body=body)
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e), output_json)

        if output_json:
            json_print(result)
            return
        conversations = result.get("conversations") or []
        if not conversations:
            info("No conversations match.")
            return
        with paged_output():
            print_conversation_search(
                result, fields=body["fields"], url_builder=project.get_conversation_url
            )

    @classmethod
    def _build_search_body(cls, args: Namespace) -> dict[str, Any]:
        """Translate parsed ``search`` flags into a Data API request body.

        Raises:
            ValueError: On a malformed date, filter or sort flag.
        """
        sort = parse_sort_flag(args.sort)
        if sort and sort["field"] not in SEARCH_SORT_FIELDS:
            raise ValueError(f"--sort field must be one of: {', '.join(SEARCH_SORT_FIELDS)}.")
        body: dict[str, Any] = {
            "fields": args.field or list(SEARCH_DEFAULT_FIELDS),
            "limit": args.limit,
            "offset": args.offset,
        }
        optional = {
            "from_datetime": parse_datetime_flag(args.from_dt) if args.from_dt else None,
            "to_datetime": parse_datetime_flag(args.to_dt, exclusive_end=True)
            if args.to_dt
            else None,
            "filters": parse_filter_flags(args.filter) or None,
            "channel": args.channel,
            "client_env": args.env,
            "sort": sort,
        }
        if args.any:
            optional["filter_operator"] = "or"
        body.update({k: v for k, v in optional.items() if v is not None})
        return body

    @staticmethod
    def _fail(message: str, output_json: bool) -> None:
        """Report an error in the requested format and exit."""
        from poly.output.console import error

        if output_json:
            json_print({"success": False, "error": message})
        else:
            error(message)
        sys.exit(1)

    @classmethod
    def conversations_get(
        cls,
        base_path: str,
        conversation_id: str,
        output_json: bool = False,
    ) -> None:
        """Get details for a specific conversation.

        Args:
            base_path: Base path for the project.
            conversation_id: The conversation ID to look up.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_conversation_detail

        project = load_project(base_path, output_json=output_json)
        conversation = AgentStudioInterface.get_conversation(
            region=project.region,
            project_id=project.project_id,
            conversation_id=conversation_id,
        )

        if output_json:
            json_print(conversation)
        else:
            studio_url = project.get_conversation_url(conversation_id)
            print_conversation_detail(conversation, studio_url=studio_url)

    @classmethod
    def conversations_get_audio(
        cls,
        base_path: str,
        conversation_id: str,
        direction: str = "combined",
        redacted: bool = False,
        output_path: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Download audio recording for a conversation.

        Args:
            base_path: Base path for the project.
            conversation_id: The conversation ID.
            direction: Audio direction — combined, user, or agent.
            redacted: Whether to download redacted audio.
            output_path: Output file path. Defaults to <conversation_id>.wav.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        audio_data = AgentStudioInterface.get_conversation_audio(
            region=project.region,
            project_id=project.project_id,
            conversation_id=conversation_id,
            direction=direction,
            redacted=redacted,
        )

        if output_path is None:
            output_path = f"{conversation_id}.wav"

        with open(output_path, "wb") as f:
            f.write(audio_data)

        size_bytes = len(audio_data)
        if output_json:
            json_print(
                {
                    "success": True,
                    "conversation_id": conversation_id,
                    "direction": direction,
                    "redacted": redacted,
                    "output_path": output_path,
                    "size_bytes": size_bytes,
                }
            )
        else:
            size_mb = size_bytes / 1_000_000
            success(f"Audio saved to {output_path} ({size_mb:.1f} MB)")
