"""Library command family

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from collections.abc import Callable
from typing import Any

from poly.cli_commands.auth import REGION_CHOICES, region_type
from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.library import Library
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

    group = BUILDER_API_GROUP

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

        library_refresh_parser = library_subparsers.add_parser(
            "refresh",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Refresh the library of models available in the project's region.",
            description=(
                "Refresh the library of models available in the project's region.\n\n"
                "Examples:\n  poly library refresh\n  poly library refresh --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_refresh_parser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            help="Specify the region to refresh the library for. Without this option, will read from the project's configuration.",
        )

        library_asr_subparser = library_subparsers.add_parser(
            "asr",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List the ASR models available in the project's region.",
            description=(
                "List the ASR models available in the project's region.\n\n"
                "Examples:\n  poly library asr\n  poly library asr --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        library_asr_subparser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            help="Specify the region to list ASR models for. Without this option, will read from the project's configuration.",
        )

        library_asr_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the ASR models before listing them.",
        )

        library_llm_subparser = library_subparsers.add_parser(
            "llm",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List the Language models available in the project's region.",
            description=(
                "List the Language models available in the project's region.\n\n"
                "Examples:\n  poly library llm\n  poly library llm --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_llm_subparser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            help="Specify the region to list Language models for. Without this option, will read from the project's configuration.",
        )
        library_llm_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the Language models before listing them.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Execute the ``library`` command."""
        if args.library_subcommand == "refresh":
            cls.refresh_library(args.path, args.region, output_json=args.json)
        elif args.library_subcommand == "asr":
            cls.list_asr_models(args.path, args.region, refresh=args.refresh, output_json=args.json)
        elif args.library_subcommand == "llm":
            cls.list_llm_models(args.path, args.region, refresh=args.refresh, output_json=args.json)

    @classmethod
    def _refresh_library(cls, base_path: str, region: str, output_json: bool = False) -> Library:
        """Internal method to refresh the library and return it."""
        from poly.handlers.interface import AgentStudioInterface

        if region is None:
            project = load_project(base_path, output_json=output_json)
            library = project.refresh_library(force_refresh=True)
        else:
            asr_models = AgentStudioInterface.get_asr_models(region)
            llm_models = AgentStudioInterface.get_llm_models(region)
            library = Library.build_library(region, asr_models, llm_models)
            library.save_library()

        return library

    @classmethod
    def refresh_library(
        cls,
        base_path: str,
        region: str,
        output_json: bool = False,
    ) -> None:
        """Refresh the library of models available in the project's region."""
        library = cls._refresh_library(base_path, region, output_json=output_json)

        n_asr_models = len(library.asr_models)
        n_llm_models = len(library.llm_models)
        if output_json:
            json_print(
                {
                    "success": True,
                    "number_of_asr_models": n_asr_models,
                    "number_of_llm_models": n_llm_models,
                }
            )
        else:
            from poly.output.console import success

            success(
                f"Library refreshed successfully. {n_asr_models} ASR models and {n_llm_models} LLM models available."
            )

    @classmethod
    def _load_library(cls, region: str, base_path: str, output_json: bool = False) -> Library:
        try:
            if region is None:
                project = load_project(base_path, output_json=output_json)
                library = project.library
            else:
                from poly.library import Library

                library = Library.load_library_from_file(region)
        except Exception:
            library = None

        if library is None:
            library = cls._refresh_library(base_path, region, output_json=output_json)
        return library

    @classmethod
    def list_asr_models(
        cls, base_path: str, region: str, refresh: bool = False, output_json: bool = False
    ) -> None:
        """List the ASR models available in the project's region."""
        from poly.output.console import paged_output, print_asr_models, success

        if refresh:
            cls._refresh_library(base_path, region, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")

        library = cls._load_library(region, base_path, output_json=output_json)

        asr_models_json = [asr_model.to_dict() for asr_model in library.asr_models]

        sorted_asr_models = _poly_first(asr_models_json, _is_poly_asr)

        if output_json:
            json_print(sorted_asr_models)

        else:
            with paged_output():
                print_asr_models(sorted_asr_models, is_poly=_is_poly_asr)

    @classmethod
    def list_llm_models(
        cls, base_path: str, region: str, refresh: bool = False, output_json: bool = False
    ) -> None:
        """List the language models available in the project's region."""
        from poly.output.console import paged_output, print_llm_models, success

        if refresh:
            library = cls._refresh_library(base_path, region, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")

        library = cls._load_library(region, base_path, output_json=output_json)

        llm_models = [llm_model.to_dict() for llm_model in library.llm_models]

        sorted_llm_models = _poly_first(llm_models, _is_poly_llm)

        if output_json:
            json_print(sorted_llm_models)

        else:
            with paged_output():
                print_llm_models(sorted_llm_models, is_poly=_is_poly_llm)
