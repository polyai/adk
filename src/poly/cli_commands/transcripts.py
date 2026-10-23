"""Transcripts command family: search transcripts and read one in full.

Copyright PolyAI Limited
"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction

import requests

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import add_window_arguments, describe_data_api_error, load_project
from poly.constants import (
    DATA_MAX_LIMIT,
    DATA_MAX_OFFSET,
    DATA_TRANSCRIPT_MAX_CONTEXT_TURNS,
    DATA_TRANSCRIPT_QUERY_MAX_CHARS,
    DATA_TRANSCRIPT_QUERY_MIN_CHARS,
)
from poly.output.json_output import json_print


class TranscriptsCommand(BaseCommand):
    """Search transcripts and read one conversation's transcript."""

    command = "transcripts"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``transcripts`` subcommand tree."""
        transcripts_parser = subparsers.add_parser(
            "transcripts",
            parents=[parents.verbose],
            help="Search transcripts for a phrase, or read one conversation's transcript.",
            description=(
                "Search what was said across the project's conversations, or print one\n"
                "conversation turn by turn. Transcripts are PII: the API key needs PII read\n"
                "permission on the project, otherwise the Data API answers 403.\n\n"
                "Examples:\n"
                '  poly transcripts search "cancel my booking"\n'
                '  poly transcripts search "speak to a human" --from 2026-09-01 --context 2\n'
                "  poly transcripts get <conversation_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        transcripts_subparsers = transcripts_parser.add_subparsers(
            dest="transcripts_subcommand", required=True
        )

        search_parser = transcripts_subparsers.add_parser(
            "search",
            parents=[parents.path, parents.json, parents.verbose],
            help="Find conversations by what was said.",
            description=(
                "Full-text search over transcript turns. Each match is shown with the\n"
                "turns around it; use --context to widen or drop that window.\n\n"
                "Examples:\n"
                '  poly transcripts search "cancel my booking"\n'
                '  poly transcripts search "refund" --from 2026-09-01 --to 2026-09-30 --context 0\n'
                '  poly transcripts search "refund" --english --json\n'
            ),
            formatter_class=RawTextHelpFormatter,
        )
        search_parser.add_argument(
            "query",
            type=str,
            help=(
                "Phrase to search for, "
                f"{DATA_TRANSCRIPT_QUERY_MIN_CHARS} to {DATA_TRANSCRIPT_QUERY_MAX_CHARS} characters."
            ),
        )
        add_window_arguments(search_parser, default_help="Defaults to no lower bound.")
        search_parser.add_argument(
            "--context",
            type=int,
            default=1,
            choices=range(0, DATA_TRANSCRIPT_MAX_CONTEXT_TURNS + 1),
            metavar="N",
            help=(
                "Turns of context to show on each side of a match, 0 to "
                f"{DATA_TRANSCRIPT_MAX_CONTEXT_TURNS}. Defaults to 1."
            ),
        )
        search_parser.add_argument(
            "--english",
            action="store_true",
            default=False,
            help="Show the English translation of non-English turns where available.",
        )
        search_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help=f"Conversations per page, 1 to {DATA_MAX_LIMIT}.",
        )
        search_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help=f"Conversations to skip, up to {DATA_MAX_OFFSET}.",
        )

        get_parser = transcripts_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Print one conversation's full transcript.",
            description=(
                "Print every turn of a conversation with speaker and timestamp.\n"
                "For call metadata (channel, handoff, summary) use\n"
                "`poly conversations get <conversation_id>`.\n\n"
                "Examples:\n"
                "  poly transcripts get <conversation_id>\n"
                "  poly transcripts get <conversation_id> --english\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        get_parser.add_argument("conversation_id", type=str, help="The conversation ID.")
        get_parser.add_argument(
            "--english",
            action="store_true",
            default=False,
            help="Show the English translation of non-English turns where available.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching transcripts sub-handler."""
        if args.transcripts_subcommand == "search":
            cls.transcripts_search(args.path, args, output_json=args.json)
        elif args.transcripts_subcommand == "get":
            cls.transcripts_get(
                args.path, args.conversation_id, english=args.english, output_json=args.json
            )

    @classmethod
    def transcripts_search(cls, base_path: str, args: Namespace, output_json: bool = False) -> None:
        """Search transcript turns for a phrase and print matches with context.

        Args:
            base_path: Base path for the project.
            args: Parsed ``search`` flags.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, paged_output, print_transcript_matches

        project = load_project(base_path, output_json=output_json)
        try:
            result = project.search_transcripts(
                args.query,
                from_dt=args.from_dt,
                to_dt=args.to_dt,
                context_turns=args.context,
                limit=args.limit,
                offset=args.offset,
            )
        except ValueError as e:
            cls._fail(str(e), output_json)
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e, needs_pii=True), output_json)

        if output_json:
            json_print(result)
            return
        if not result.get("results"):
            info(f"No transcripts mention {args.query!r}.")
            return
        with paged_output():
            print_transcript_matches(
                result,
                args.query,
                english=args.english,
                url_builder=project.get_conversation_url,
            )

    @classmethod
    def transcripts_get(
        cls,
        base_path: str,
        conversation_id: str,
        english: bool = False,
        output_json: bool = False,
    ) -> None:
        """Print one conversation's transcript.

        Args:
            base_path: Base path for the project.
            conversation_id: The conversation ID.
            english: Prefer English translations of non-English turns.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import paged_output, print_transcript

        project = load_project(base_path, output_json=output_json)
        try:
            transcript = project.get_transcript(conversation_id)
        except ValueError as e:
            cls._fail(str(e), output_json)
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e, needs_pii=True), output_json)

        if output_json:
            json_print(transcript)
            return
        with paged_output():
            print_transcript(
                transcript,
                english=english,
                studio_url=project.get_conversation_url(conversation_id),
            )

    @staticmethod
    def _fail(message: str, output_json: bool) -> None:
        """Report an error in the requested format and exit."""
        from poly.output.console import error

        if output_json:
            json_print({"success": False, "error": message})
        else:
            error(message)
        sys.exit(1)
