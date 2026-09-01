"""Conversations command family: list and inspect conversations.

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.output.json_output import json_print


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

        conv_get_parser = conversations_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Get details for a specific conversation.",
            description=(
                "Get detailed information for a conversation including turns.\n\n"
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
