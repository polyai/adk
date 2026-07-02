"""Base abstractions for CLI command families.

``Parents`` carries the shared parent parsers; ``BaseCommand`` is the contract
each command family implements. Command modules import these directly
(e.g. ``from poly.cli_commands.base import BaseCommand, Parents``).

Copyright PolyAI Limited
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser
from dataclasses import dataclass


@dataclass
class Parents:
    """Shared parent parsers reused by subcommands across families."""

    verbose: ArgumentParser
    json: ArgumentParser
    debug: ArgumentParser


class BaseCommand(ABC):
    """Base class for CLI commands."""

    command: str = "base"

    @classmethod
    @abstractmethod
    def add_arguments(cls, subparsers, parents: "Parents") -> None:
        """Register this command's subparser(s) on the root subparsers action."""
        pass

    @classmethod
    @abstractmethod
    def run(cls, args) -> None:
        """Run the command with the provided arguments."""
        pass
