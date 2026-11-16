"""Library command family

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from collections.abc import Callable
from typing import Any

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print

# ASR models carry no PolyAI flag, so this follows Agent Studio's rule for them.
_POLY_ASR_PROVIDERS = ("poly", "raven")
_POLY_ASR_MODEL_PREFIX = "poly-"


def _is_poly_llm(model: dict[str, Any]) -> bool:
    return bool(model.get("polyaiModel"))


def _is_poly_asr(model: dict[str, Any]) -> bool:
    provider = (model.get("provider") or "").lower()
    model_id = (model.get("model") or "").lower()
    return provider in _POLY_ASR_PROVIDERS or model_id.startswith(_POLY_ASR_MODEL_PREFIX)


def _poly_first(
    models: list[dict[str, Any]], is_poly: Callable[[dict[str, Any]], bool]
) -> list[dict[str, Any]]:
    """Sort PolyAI's own models first, then each group by name."""
    return sorted(models, key=lambda m: (not is_poly(m), (m.get("name") or "").lower()))


class LibraryCommand(BaseCommand):
    """Library command family."""

    command = "library"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``library`` subcommand tree."""
        library_parser = subparsers.add_parser(
            "library",
            parents=[parents.verbose, parents.debug],
            help="Browse the models available in Agent Studio.",
            description=(
                "Browse the models available in Agent Studio.\n\n"
                "Examples:\n  poly library asr\n  poly library llm\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_subparsers = library_parser.add_subparsers(dest="library_subcommand", required=True)

        library_subparsers.add_parser(
            "asr",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List the ASR models available in the project's region.",
            description=(
                "List the ASR models available in the project's region.\n\n"
                "Examples:\n  poly library asr\n  poly library asr --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        library_subparsers.add_parser(
            "llm",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List the language models available in the project's region.",
            description=(
                "List the language models available in the project's region.\n\n"
                "Examples:\n  poly library llm\n  poly library llm --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the ``library`` command."""
        if args.library_subcommand == "asr":
            cls.list_asr_models(args.path, output_json=args.json)
        elif args.library_subcommand == "llm":
            cls.list_llm_models(args.path, output_json=args.json)

    @classmethod
    def list_asr_models(cls, base_path: str, output_json: bool = False) -> None:
        """List the ASR models available in the project's region."""
        from poly.output.console import paged_output, print_asr_models

        project = load_project(base_path)
        asr_models = _poly_first(project.get_asr_models(), _is_poly_asr)

        if output_json:
            json_print(asr_models)

        else:
            with paged_output():
                print_asr_models(asr_models, is_poly=_is_poly_asr)

    @classmethod
    def list_llm_models(cls, base_path: str, output_json: bool = False) -> None:
        """List the language models available in the project's region."""
        from poly.output.console import paged_output, print_llm_models

        project = load_project(base_path)
        llm_models = _poly_first(project.get_llm_models(), _is_poly_llm)

        if output_json:
            json_print(llm_models)

        else:
            with paged_output():
                print_llm_models(llm_models, is_poly=_is_poly_llm)
