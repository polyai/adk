"""Tests for the shared CLI helpers: region aliases on every --region flag.

Copyright PolyAI Limited
"""

import argparse
import unittest
from io import StringIO
from unittest.mock import patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.shared import REGION_ALIASES, REGION_ALIASES_HELP, region_type
from poly.handlers.interface import REGIONS


def _parser():
    cli = AgentStudioCLI()
    cli.register_commands()
    return cli._create_parser()


class RegionTypeTest(unittest.TestCase):
    """The argparse converter shared by every --region flag."""

    def test_aliases_map_to_canonical_regions(self):
        self.assertEqual(REGION_ALIASES, {"uk": "uk-1", "us": "us-1", "eu": "euw-1"})
        for alias, canonical in REGION_ALIASES.items():
            self.assertEqual(region_type(alias), canonical)
            self.assertIn(canonical, REGIONS)

    def test_canonical_regions_pass_through(self):
        for region in REGIONS:
            self.assertEqual(region_type(region), region)

    def test_is_case_insensitive(self):
        self.assertEqual(region_type("UK"), "uk-1")
        self.assertEqual(region_type("Eu"), "euw-1")
        self.assertEqual(region_type("UK-1"), "uk-1")
        self.assertEqual(region_type("Studio"), "studio")

    def test_euw_is_not_an_alias(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            region_type("euw")

    def test_unknown_region_raises_with_canonical_names(self):
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            region_type("europe")

        self.assertEqual(
            str(ctx.exception),
            "'europe' is not a region. Use one of: us-1, euw-1, uk-1, studio, staging, dev "
            "(aliases: uk, us, eu).",
        )


# Every `--region` site in the CLI: (label, argv up to and including the alias).
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


class RegionAliasParseTest(unittest.TestCase):
    """`--region uk` lands as `uk-1` on every command that takes --region."""

    def setUp(self):
        self.parser = _parser()

    def test_alias_resolves_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                args = self.parser.parse_args(argv)
                self.assertEqual(args.region, "uk-1")

    def test_other_aliases_resolve_on_init(self):
        self.assertEqual(self.parser.parse_args(["init", "--region", "us"]).region, "us-1")
        self.assertEqual(self.parser.parse_args(["init", "--region", "eu"]).region, "euw-1")
        self.assertEqual(self.parser.parse_args(["init", "--region", "UK"]).region, "uk-1")

    def test_canonical_region_still_accepted_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                canonical = [a if a != "uk" else "uk-1" for a in argv]
                self.assertEqual(self.parser.parse_args(canonical).region, "uk-1")

    def test_unknown_region_is_rejected_with_canonical_names(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                garbage = [a if a != "uk" else "europe" for a in argv]
                stderr = StringIO()
                with patch("sys.stderr", stderr), self.assertRaises(SystemExit) as ctx:
                    self.parser.parse_args(garbage)
                self.assertEqual(ctx.exception.code, 2)
                self.assertIn("'europe' is not a region. Use one of: us-1, euw-1", stderr.getvalue())

    def test_help_shows_alias_line_on_every_site(self):
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                stdout = StringIO()
                with patch("sys.stdout", stdout), self.assertRaises(SystemExit):
                    self.parser.parse_args(_help_argv(argv))
                self.assertIn(REGION_ALIASES_HELP, stdout.getvalue())

    def test_region_choices_still_canonical_for_completion(self):
        """argcomplete reads `choices`; the converter must not replace them."""
        for label, argv in REGION_SITES:
            with self.subTest(site=label):
                subparser = _subparser_for(self.parser, argv)
                action = next(a for a in subparser._actions if "--region" in a.option_strings)
                self.assertEqual(list(action.choices), REGIONS)
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
