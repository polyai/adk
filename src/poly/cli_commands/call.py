"""Call command: interactive voice call with the agent.

Copyright PolyAI Limited
"""

import asyncio
import os
import sys
import uuid
from argparse import (
    ArgumentParser,
    BooleanOptionalAction,
    Namespace,
    RawTextHelpFormatter,
    _SubParsersAction,
)
from typing import Optional

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project

# Shown if the voice dependencies fail to import (a broken install — they ship with ADK).
_VOICE_DEPS_HINT = (
    "Voice calling dependencies failed to load. Reinstall ADK with:\n"
    "    pip install --force-reinstall polyai-adk"
)


def new_call_sid() -> str:
    """Generate a unique call SID."""
    return f"ADK-{uuid.uuid4()}"


class CallCommand(BaseCommand):
    """Start an interactive voice call with the agent."""

    command = "call"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``call`` subcommand."""
        call_parser = subparsers.add_parser(
            "call",
            parents=[parents.verbose, parents.debug],
            help="Start an interactive voice call with the agent.",
            description=(
                "Start an interactive voice call with the agent using your "
                "microphone and speaker.\n\n"
                "Only draft/branch calls are supported: switch to a non-main "
                "branch and push your changes, then call the draft build.\n\n"
                "Examples:\n"
                "  poly call\n"
                "  poly call --push\n"
                "  poly call --variant my-variant\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        call_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )
        call_parser.add_argument(
            "--environment",
            "-e",
            type=str,
            default="draft",
            choices=["draft"],
            help="Environment to call. Only the current branch's draft build is supported.",
        )
        call_parser.add_argument(
            "--variant",
            type=str,
            default=None,
            help="Name of variant to use for the call.",
        )
        call_parser.add_argument(
            "--push",
            action="store_true",
            help="Push the project before calling, so the draft build includes local changes.",
        )
        call_parser.add_argument(
            "--echo-cancellation",
            dest="aec",
            action=BooleanOptionalAction,
            default=True,
            help="Echo cancellation, on by default so the agent doesn't hear itself on a "
            "speaker. Use --no-echo-cancellation to disable.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the call handler."""
        cls.call(
            args.path,
            environment=args.environment,
            variant=args.variant,
            push_before_call=args.push,
            aec=args.aec,
        )

    @classmethod
    def call(
        cls,
        base_path: str,
        environment: str = "draft",
        variant: Optional[str] = None,
        push_before_call: bool = False,
        aec: bool = True,
    ) -> None:
        """Start an interactive voice call with the agent's draft build."""
        from poly.output.console import error, info, success, warning

        project = load_project(base_path)
        branch_label = project.get_current_branch() or project.branch_id

        if environment != "draft" or not project.branch_id or branch_label == "main":
            error("`poly call` supports only draft calls.")
            sys.exit(1)

        if push_before_call:
            info("Pushing project before the call...")
            push_success, output, _ = project.push_project(
                force=False, skip_validation=False, dry_run=False, format=False
            )
            if not push_success and output != "No changes detected":
                error(f"Failed to push before calling: {output}")
                sys.exit(1)
            success("Project pushed.")

        # Import the voice stack lazily so other commands don't load the WebRTC/audio stack.
        try:
            from poly.call.client import CallError, run_call
        except ImportError:
            error(_VOICE_DEPS_HINT)
            sys.exit(1)

        # AEC is on by default; if the WebRTC APM isn't available, warn and continue
        # without it rather than blocking the call.
        if aec:
            try:
                from poly.call.aec import EchoCanceller
                from poly.call.media import SAMPLE_RATE

                EchoCanceller(SAMPLE_RATE)
            except Exception:
                warning(
                    "Echo cancellation unavailable (reinstall ADK to restore it); "
                    "continuing without it."
                )
                aec = False

        try:
            session = project.create_call_session("draft", variant=variant)
        except (ValueError, NotImplementedError) as exc:
            error(str(exc))
            sys.exit(1)

        caller = os.environ.get("ADK_COMMAND_USER_OVERRIDE") or "adk-user"
        call_sid = new_call_sid()
        call_url = project.get_conversation_url(call_sid)
        info(
            f"Calling [bold]{project.account_id}/{project.project_id}[/bold] "
            f"on branch [bold]{branch_label}[/bold]. "
            "Press Ctrl+C to hang up."
        )

        try:
            asyncio.run(run_call(session, caller, aec=aec, call_sid=call_sid))
        except CallError as exc:
            error(f"Call failed: {exc}")
            sys.exit(1)
        except KeyboardInterrupt:
            # Fallback
            pass

        success("Call ended.")
        info(f"Review this call in Agent Studio: [link={call_url}]{call_url}[/link]")
