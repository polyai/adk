"""Tests for the shared CLI helpers: region names on every --region flag.

Copyright PolyAI Limited
"""

import argparse
import unittest
from io import StringIO
from unittest.mock import patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.shared import REGION_CHOICES, region_type
from poly.constants import REGION_NAMES
from poly.handlers.interface import REGIONS


def _parser():
    cli = AgentStudioCLI()
    cli.register_commands()
    return cli._create_parser()


class RegionTypeTest(unittest.TestCase):
    """The argparse converter shared by every --region flag."""

    def test_advertised_names_map_to_internal_regions(self):
        self.assertEqual(
            REGION_NAMES, {"us": "us-1", "eu": "euw-1", "uk": "uk-1", "studio": "studio"}
        )
        for name, internal in REGION_NAMES.items():
            self.assertEqual(region_type(name), internal)
            self.assertIn(internal, REGIONS)

    def test_older_spellings_still_accepted(self):
        """``us-1``/``euw-1``/``uk-1`` and the internal ``staging``/``dev`` keep working."""
        for region in REGIONS:
            self.assertEqual(region_type(region), region)

    def test_is_case_insensitive(self):
        self.assertEqual(region_type("UK"), "uk-1")
        self.assertEqual(region_type("Eu"), "euw-1")
        self.assertEqual(region_type("UK-1"), "uk-1")
        self.assertEqual(region_type("Studio"), "studio")

    def test_euw_is_not_a_region(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            region_type("euw")

    def test_unknown_region_raises_with_advertised_names(self):
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            region_type("europe")

        self.assertEqual(
            str(ctx.exception), "'europe' is not a region. Use one of: us, eu, uk, studio."
        )

    def test_choices_advertise_short_names_but_accept_internal(self):
        """argparse checks ``choices`` after ``type``, so the internal ids must pass."""
        self.assertEqual(list(REGION_CHOICES), ["us", "eu", "uk", "studio"])
        for region in REGIONS:
            self.assertIn(region, REGION_CHOICES)
        self.assertNotIn("europe", REGION_CHOICES)


# Every `--region` site in the CLI: (label, argv up to and including the region).
# `functions execute` and `functions validate` inherit --region from the shared
# headless scope parent in cli.py, so they are covered here as well.
REGION_SITES = [
    ("init", ["init", "--region", "uk"]),
    ("setup", ["setup", "--region", "uk"]),
    ("login", ["login", "--region", "uk"]),
    ("apikey", ["apikey", "--region", "uk"]),
    ("project list", ["project", "list", "--region", "uk"]),
    ("project create", ["project", "create", "--region", "uk"]),
    ("project delete", ["project", "delete", "--region", "uk"]),
    ("project duplicate", ["project", "duplicate", "--region", "uk"]),
    ("template list", ["template", "list", "--region", "uk"]),
    ("template load", ["template", "load", "--region", "uk"]),
    ("functions execute", ["functions", "execute", "fn", "--region", "uk"]),
    ("functions validate", ["functions", "validate", "--region", "uk"]),
]


class RegionParseTest(unittest.TestCase):
    """`--region uk` lands as `uk-1` on every command that takes --region."""

    def setUp(self):
        self.parser = _parser()

    def test_name_resolves_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                args = self.parser.parse_args(argv)
                self.assertEqual(args.region, "uk-1")

    def test_other_names_resolve_on_init(self):
        self.assertEqual(self.parser.parse_args(["init", "--region", "us"]).region, "us-1")
        self.assertEqual(self.parser.parse_args(["init", "--region", "eu"]).region, "euw-1")
        self.assertEqual(self.parser.parse_args(["init", "--region", "UK"]).region, "uk-1")

    def test_older_spelling_still_accepted_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                canonical = [a if a != "uk" else "uk-1" for a in argv]
                self.assertEqual(self.parser.parse_args(canonical).region, "uk-1")

    def test_unknown_region_is_rejected_with_advertised_names(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                garbage = [a if a != "uk" else "europe" for a in argv]
                stderr = StringIO()
                with patch("sys.stderr", stderr), self.assertRaises(SystemExit) as ctx:
                    self.parser.parse_args(garbage)
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn(
                    "'europe' is not a region. Use one of: us, eu, uk, studio.", stderr.getvalue()
                )

    def test_help_advertises_only_short_names_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                stdout = StringIO()
                with patch("sys.stdout", stdout), self.assertRaises(SystemExit):
                    self.parser.parse_args(_help_argv(argv))
                help_text = stdout.getvalue()
                self.assertIn("{us,eu,uk,studio}", help_text)
                for older in ("us-1", "euw-1", "uk-1"):
                    self.assertNotIn(older, help_text)

    def test_region_choices_are_short_names_for_completion(self):
        """argcomplete reads `choices`; it should offer the advertised names only."""
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                subparser = _subparser_for(self.parser, argv)
                action = next(a for a in subparser._actions if "--region" in a.option_strings)
                self.assertEqual(list(action.choices), ["us", "eu", "uk", "studio"])
                self.assertIs(action.type, region_type)


def _help_argv(argv: list[str]) -> list[str]:
    """`<command> [<subcommand>] --help` for a REGION_SITES entry."""
    command = argv[: argv.index("--region")]
    if command and command[0] == "functions":
        command = command[:2]
    return command + ["--help"]


def _subparser_for(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.ArgumentParser:
    """Walk the subparser tree down to the parser that owns the command in argv."""
    current = parser
    for word in argv[: argv.index("--region")]:
        subparsers = next(
            (a for a in current._actions if isinstance(a, argparse._SubParsersAction)), None
        )
        if subparsers is None or word not in subparsers.choices:
            break
        current = subparsers.choices[word]
    return current


if __name__ == "__main__":
    unittest.main()
