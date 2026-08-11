"""Utility command family: docs and shell completion.

Copyright PolyAI Limited
"""

import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

import argcomplete

from poly.cli_commands.base import BaseCommand, Parents
from poly.project import AgentStudioProject
from poly.utils.agent_setup import (
    MEMORY_FILE,
    SKILL_NAME,
    ClaudeCodePlan,
    apply_claude_code_setup,
    plan_claude_code_setup,
)

DOCUMENT_CHOICES = AgentStudioProject.discover_docs()


class DocsCommand(BaseCommand):
    """Output documentation for a given topic."""

    command = "docs"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``docs`` subcommand."""
        docs_parser = subparsers.add_parser(
            "docs",
            parents=[parents.verbose, parents.path],
            help="Outputs documentation for a given topic.",
            description=(
                "Generate documentation.\n\n"
                "With no arguments, prints the top-level docs. Pass topic names or --all for\n"
                "more. Pass --claude-code to install this documentation into the project as\n"
                "Claude Code memory and skill files instead of printing it."
            ),
            formatter_class=RawTextHelpFormatter,
        )
        docs_parser.add_argument(
            "documents",
            nargs="*",
            choices=DOCUMENT_CHOICES,
            help=f"Output documentation for the given topics. Choices: {', '.join(DOCUMENT_CHOICES)}",
        )
        docs_parser.add_argument(
            "--all",
            action="store_true",
            help="Output documentation for all topics.",
        )
        docs_parser.add_argument(
            "--output",
            "--write",
            "-o",
            type=str,
            metavar="FILE_PATH",
            dest="output",
            help="Write output to FILE_PATH instead of stdout.",
        )
        docs_parser.add_argument(
            "--claude-code",
            action="store_true",
            dest="claude_code",
            help=(
                "Set up Claude Code for this project: install the poly-adk skill into\n"
                ".claude/skills/ and a poly-adk section into CLAUDE.md."
            ),
        )
        docs_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite existing agent setup files without confirmation.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the docs handler."""
        if getattr(args, "claude_code", False):
            cls._reject_claude_code_conflicts(args)
            cls.setup_claude_code(
                path=getattr(args, "path", os.getcwd()),
                force=getattr(args, "force", False),
            )
            return

        cls.docs(
            documents=args.documents,
            all_documents=getattr(args, "all", False),
            output=getattr(args, "output", None),
        )

    @classmethod
    def _reject_claude_code_conflicts(cls, args: Namespace) -> None:
        """Exit if --claude-code is combined with the printing arguments.

        --claude-code installs files rather than printing, so topic names, --all
        and --output have nothing to act on. Silently ignoring them would look
        like the requested documentation had been written somewhere.

        Args:
            args: Parsed CLI arguments.
        """
        from poly.output.console import error

        conflicting: list[str] = []
        if args.documents:
            conflicting.append(" ".join(args.documents))
        if getattr(args, "all", False):
            conflicting.append("--all")
        if getattr(args, "output", None):
            conflicting.append("--output")

        if conflicting:
            error(
                f"--claude-code cannot be combined with {', '.join(conflicting)}. "
                "It installs the skill and CLAUDE.md instead of printing documentation. "
                "Run the two commands separately."
            )
            sys.exit(1)

    @classmethod
    def setup_claude_code(cls, path: str, force: bool = False) -> None:
        """Install the poly-adk skill and CLAUDE.md memory into a project.

        Args:
            path: Project directory to install into.
            force: Overwrite existing files without asking.
        """
        from poly.output.console import info, plain, success, warning

        plan = plan_claude_code_setup(path)

        if plan.is_noop:
            success(f"Claude Code setup is already up to date in {plan.target_dir}")
            return

        cls._print_claude_code_plan(plan)

        if plan.needs_confirmation and not force:
            if not sys.stdin.isatty():
                warning(
                    "Existing files would be overwritten or removed. "
                    "Re-run with --force to proceed."
                )
                sys.exit(1)

            import questionary

            confirmed = questionary.confirm(
                "Apply these changes? The existing files listed above are overwritten or removed.",
                default=False,
            ).ask()
            if not confirmed:
                warning("Aborted. Nothing was written.")
                return

        applied, removed = apply_claude_code_setup(plan)

        success(f"Claude Code setup written to {plan.target_dir}")
        info(f"{len(applied)} file(s) written, {len(removed)} removed.")
        plain(
            f"\nStart Claude Code in this directory. It reads {MEMORY_FILE} on every session "
            f"and loads the '{SKILL_NAME}' skill when you work on agent resources.\n"
            "Re-run this command after upgrading the CLI to refresh both."
        )

    @classmethod
    def _print_claude_code_plan(cls, plan: ClaudeCodePlan) -> None:
        """Show the user which files a Claude Code setup plan touches."""
        from poly.output.console import print_file_list

        def relative(path: str) -> str:
            return os.path.relpath(path, plan.target_dir)

        by_action: dict[str, list[str]] = {}
        for write in plan.pending:
            by_action.setdefault(write.action, []).append(relative(write.path))

        styles = {"create": "green", "append": "cyan", "overwrite": "yellow"}
        titles = {
            "create": "New files",
            "append": f"Appending the poly-adk section to {MEMORY_FILE}",
            "overwrite": "Existing files that will be overwritten",
        }
        for action, style in styles.items():
            if by_action.get(action):
                print_file_list(titles[action], sorted(by_action[action]), style)

        if plan.removals:
            print_file_list(
                "Stale skill files that will be removed",
                sorted(relative(path) for path in plan.removals),
                "red",
            )

    @classmethod
    def docs(
        cls,
        documents: list[str] = None,
        all_documents: bool = False,
        output: Optional[str] = None,
    ) -> None:
        """Generate documentation for the project."""
        from poly.output.console import plain, success

        parts: list[str] = []
        if not documents and not all_documents:
            parts.append(AgentStudioProject.load_docs("docs"))
        if all_documents:
            parts.append(AgentStudioProject.load_docs("docs"))
            parts.extend([AgentStudioProject.load_docs(doc) for doc in DOCUMENT_CHOICES])
        else:
            parts.extend([AgentStudioProject.load_docs(doc) for doc in documents])

        content: str = "\n\n".join(parts)

        if output:
            output_path = os.path.abspath(output)
            parent = os.path.dirname(output_path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
            success(f"Documentation written to {output_path}")
        else:
            plain(content)


class CompletionCommand(BaseCommand):
    """Generate shell completion scripts for poly/adk."""

    command = "completion"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``completion`` subcommand."""
        completion_parser = subparsers.add_parser(
            "completion",
            formatter_class=RawTextHelpFormatter,
            help="Generate shell completion scripts",
            description=(
                "Output a shell completion script for poly/adk.\n\n"
                "Add the output to your shell configuration to enable tab completion:\n\n"
                '  Bash:  eval "$(poly completion bash)"\n'
                "         # or: poly completion bash >> ~/.bash_completion\n\n"
                '  Zsh:   eval "$(poly completion zsh)"\n'
                "         # or: poly completion zsh > ~/.zsh/completions/_poly\n\n"
                "  Fish:  poly completion fish | source\n"
                "         # or: poly completion fish > ~/.config/fish/completions/poly.fish\n"
            ),
        )
        completion_parser.add_argument(
            "shell",
            choices=["bash", "zsh", "fish"],
            help="Shell type to generate completions for.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the completion handler."""
        cls.print_completion(args.shell)

    @classmethod
    def print_completion(cls, shell: str) -> None:
        """Print a shell completion script for poly/adk.

        Args:
            shell: Target shell — one of 'bash', 'zsh', or 'fish'.
        """
        script = argcomplete.shellcode(["poly", "adk"], shell=shell)
        print(script)
