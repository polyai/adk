"""Utility command family: docs and shell completion.

Copyright PolyAI Limited
"""

import os
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

import argcomplete

from poly.cli_commands.base import OTHER_GROUP, BaseCommand, Parents
from poly.project import AgentStudioProject

DOCUMENT_CHOICES = AgentStudioProject.discover_docs()


class DocsCommand(BaseCommand):
    """Output documentation for a given topic."""

    command = "docs"

    group = OTHER_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``docs`` subcommand."""
        docs_parser = subparsers.add_parser(
            "docs",
            parents=[parents.verbose],
            help="Outputs documentation for a given topic.",
            description="Generate documentation",
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

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the docs handler."""
        cls.docs(
            documents=args.documents,
            all_documents=getattr(args, "all", False),
            output=getattr(args, "output", None),
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

    group = OTHER_GROUP

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
