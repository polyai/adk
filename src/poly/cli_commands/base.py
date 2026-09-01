"""Base abstractions for CLI command families.

``Parents`` carries the shared parent parsers; ``BaseCommand`` is the contract
each command family implements. Command modules import these directly
(e.g. ``from poly.cli_commands.base import BaseCommand, Parents``).

Copyright PolyAI Limited
"""

import re
from abc import ABC, abstractmethod
from argparse import (
    SUPPRESS,
    Action,
    ArgumentParser,
    HelpFormatter,
    Namespace,
    RawTextHelpFormatter,
    _SubParsersAction,
)
from dataclasses import dataclass

# Section headers for ``poly --help``, in the order they are displayed. Every
# command's ``group`` must be one of these; ``OTHER_GROUP`` collects anything
# that has not been assigned a group yet so a new command is never dropped from
# the help output.
GETTING_STARTED_GROUP = "Getting started"
PROJECT_SYNC_GROUP = "Project sync"
BUILDER_API_GROUP = "Builder API"
OTHER_GROUP = "Other"

COMMAND_GROUP_ORDER = [
    GETTING_STARTED_GROUP,
    PROJECT_SYNC_GROUP,
    BUILDER_API_GROUP,
    OTHER_GROUP,
]


@dataclass
class Parents:
    """Shared parent parsers reused by subcommands across families."""

    verbose: ArgumentParser
    json: ArgumentParser
    debug: ArgumentParser
    path: ArgumentParser
    scope: ArgumentParser


class BaseCommand(ABC):
    """Base class for CLI commands."""

    command: str = "base"
    group: str = OTHER_GROUP

    @classmethod
    @abstractmethod
    def add_arguments(
        cls, subparsers: "_SubParsersAction[ArgumentParser]", parents: "Parents"
    ) -> None:
        """Register this command's subparser(s) on the root subparsers action."""
        pass

    @classmethod
    @abstractmethod
    def run(cls, args: Namespace) -> None:
        """Run the command with the provided arguments."""
        pass


class _GroupHeaderAction(Action):
    """A help-only pseudo-action that renders a section header.

    argparse has no notion of grouped subcommands, but it does render one line
    per entry in a subparsers action's help list. A header is therefore just an
    entry whose displayed name is a blank line followed by the group title, and
    which carries no help text of its own — so argparse prints it flush left,
    the same way it prints ``options:``.
    """

    def __init__(self, title: str):
        super().__init__(option_strings=[], dest=title, help=None, metavar=f"\n{title}:")

    def __call__(self, *args: object, **kwargs: object) -> None:
        """Never invoked — this action exists only to be formatted into help."""
        raise NotImplementedError("group headers are display-only")


class _GroupedHelpMixin:
    """Help-formatting half of the grouped-subcommand mechanism.

    Mixed into a concrete argparse formatter so the same behaviour can be
    combined with either the default or the raw-text description handling.
    """

    def _format_action(self, action: Action) -> str:
        """Format an action, hiding the subparsers placeholder line.

        The subparsers action would otherwise print its own ``<command>``
        metavar line above the commands. The group headers already title each
        section, so that line is redundant — drop it and keep the entries.
        """
        formatted = super()._format_action(action)
        if isinstance(action, _SubParsersAction):
            _placeholder, _, entries = formatted.partition("\n")
            return entries
        return formatted

    def format_help(self) -> str:
        """Format the help text, tidying up whitespace around the headers.

        Each header carries a leading newline to escape argparse's indentation,
        which leaves the indent stranded as trailing whitespace on the blank
        line before it, and doubles up the blank line after the usage block.
        """
        text = "\n".join(line.rstrip() for line in super().format_help().split("\n"))
        return re.sub(r"\n{3,}", "\n\n", text)


class GroupedHelpFormatter(_GroupedHelpMixin, HelpFormatter):
    """Formatter for a grouped parser whose help text should wrap normally."""


class GroupedRawTextHelpFormatter(_GroupedHelpMixin, RawTextHelpFormatter):
    """Formatter for a grouped parser with a hand-formatted description block."""


def add_grouped_subparsers(
    parser: ArgumentParser,
    dest: str,
    metavar: str,
    required: bool = True,
) -> "_SubParsersAction[ArgumentParser]":
    """Add a subparsers action whose ``--help`` listing carries group headers.

    The parser must use ``GroupedHelpFormatter`` or
    ``GroupedRawTextHelpFormatter``. Register the subparsers as usual, then call
    ``group_subcommands`` once they all exist.

    Args:
        parser: The parser to add the subparsers action to.
        dest: Namespace attribute the chosen subcommand is stored under.
        metavar: Placeholder shown in the usage line, e.g. ``"<command>"``.
        required: Whether a subcommand must be supplied.

    Returns:
        The subparsers action to register subcommands on.
    """
    # title=SUPPRESS drops the outer "positional arguments:" heading, since the
    # per-group headers act as the section titles. argparse appends the group it
    # creates, which would put the subcommands below the options — so hoist it
    # above the (now-empty) default positional and optional groups.
    subparsers = parser.add_subparsers(
        title=SUPPRESS, dest=dest, required=required, metavar=metavar
    )
    parser._action_groups.insert(0, parser._action_groups.pop())
    return subparsers


def group_subcommands(
    subparsers: "_SubParsersAction[ArgumentParser]",
    group_by_command: dict[str, str],
    group_order: list[str],
    fallback_group: str = OTHER_GROUP,
) -> None:
    """Reorder a subparsers action's help entries into titled sections.

    Call once, after every subparser has been registered. The parser must use
    ``GroupedHelpFormatter`` or ``GroupedRawTextHelpFormatter`` for the headers
    to render correctly. Parsing behaviour is untouched — only the ``--help``
    listing changes.

    Args:
        subparsers: The subparsers action the subcommands were registered on.
        group_by_command: Maps subcommand name to the section it belongs under.
        group_order: The section titles, in display order. Sections with no
            members are skipped.
        fallback_group: Section for subcommands missing from
            ``group_by_command``, or whose group is absent from ``group_order``.

    Returns:
        None. ``subparsers`` is modified in place.
    """
    entries = list(subparsers._choices_actions)

    grouped: list[Action] = []
    for title in group_order:
        members = [
            entry for entry in entries if group_by_command.get(entry.dest, fallback_group) == title
        ]
        if not members:
            continue
        grouped.append(_GroupHeaderAction(title))
        grouped.extend(members)

    # A subcommand whose group is missing from group_order would otherwise be
    # dropped from the listing, so surface it rather than hiding a working
    # subcommand behind a typo.
    ungrouped = [entry for entry in entries if entry not in grouped]
    if ungrouped:
        grouped.append(_GroupHeaderAction(fallback_group))
        grouped.extend(ungrouped)

    subparsers._choices_actions[:] = grouped
