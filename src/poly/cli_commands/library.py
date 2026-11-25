"""Library command family

Copyright PolyAI Limited
"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from collections.abc import Callable
from typing import Any, Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import REGION_CHOICES, fail, load_project, region_type
from poly.library import Library, TTSVoice
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
            help="List the language models available in the project's region.",
            description=(
                "List the language models available in the project's region.\n\n"
                "Examples:\n  poly library llm\n  poly library llm --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_llm_subparser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            help="Specify the region to list language models for. Without this option, will read from the project's configuration.",
        )
        library_llm_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the language models before listing them.",
        )

        library_voice_parser = library_subparsers.add_parser(
            "voice",
            parents=[parents.verbose, parents.debug],
            help="Manage the TTS voices available in the project's region.",
            description=(
                "Manage the TTS voices available in the project's region.\n\n"
                "Examples:\n  poly library voice list\n  poly library voice list --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_voice_subparsers = library_voice_parser.add_subparsers(
            dest="library_voice_subcommand", required=True
        )
        library_voice_list_subparser = library_voice_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List the TTS voices available in the project's region.",
            description=(
                "List the TTS voices available in the project's region.\n\n"
                "Examples:\n  poly library voice list\n  poly library voice list --owner account\n"
                "  poly library voice list --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_voice_list_subparser.add_argument(
            "--name",
            type=str,
            help="Filter TTS voices by name.",
        )
        library_voice_list_subparser.add_argument(
            "--language",
            type=str,
            help="Filter TTS voices by language/accent.",
        )
        library_voice_list_subparser.add_argument(
            "--gender",
            type=str,
            choices=["male", "female", "neutral"],
            help="Filter TTS voices by gender.",
        )
        library_voice_list_subparser.add_argument(
            "--poly",
            action="store_true",
            help="Filter TTS voices to only include PolyAI voices.",
        )
        library_voice_list_subparser.add_argument(
            "--owner",
            choices=["global", "account"],
            help="Only voices from the shared library (global), or only the account's own (account).",
        )
        library_voice_list_subparser.add_argument(
            "--archived",
            action="store_true",
            help="Include archived voices, and internal ones (dev-only or tagged Test).",
        )
        library_voice_list_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the TTS voices before listing them.",
        )

        library_voice_show_subparser = library_voice_subparsers.add_parser(
            "show",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Show the details of a TTS voice in the project's account.",
            description=(
                "Show the details of a TTS voice in the project's account.\n\n"
                "Examples:\n  poly library voice show Anne\n"
                "  poly library voice show Pierre --language fr-CA\n"
                "  poly library voice show VOICE-6fad73f6 --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_voice_show_subparser.add_argument(
            "voice",
            type=str,
            help="The voice's name, or its VOICE- ID.",
        )
        library_voice_show_subparser.add_argument(
            "--language",
            type=str,
            help="The voice's language, for a name more than one language uses (e.g. fr-CA).",
        )
        library_voice_show_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the TTS voice details before retrieving them.",
        )

        library_voice_play_subparser = library_voice_subparsers.add_parser(
            "play",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Play a TTS voice's recording.",
            description=(
                "Play a TTS voice's recording through your speaker.\n\n"
                "Examples:\n  poly library voice play Anne\n"
                "  poly library voice play Pierre --language fr-CA\n"
                "  poly library voice play VOICE-6fad73f6 --json\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        library_voice_play_subparser.add_argument(
            "voice",
            type=str,
            help="The voice's name, or its VOICE- ID.",
        )
        library_voice_play_subparser.add_argument(
            "--language",
            type=str,
            help="The voice's language, for a name more than one language uses (e.g. fr-CA).",
        )
        library_voice_play_subparser.add_argument(
            "--refresh",
            action="store_true",
            help="Refresh the TTS voice details before playing it.",
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
        elif args.library_subcommand == "voice":
            if args.library_voice_subcommand == "list":
                cls.list_tts_voices(
                    args.path,
                    refresh=args.refresh,
                    output_json=args.json,
                    name=args.name,
                    language=args.language,
                    gender=args.gender,
                    is_poly_voice=args.poly,
                    owner=args.owner,
                    archived=args.archived,
                )
            elif args.library_voice_subcommand == "show":
                cls.show_tts_voice(
                    args.path,
                    args.voice,
                    language=args.language,
                    refresh=args.refresh,
                    output_json=args.json,
                )
            elif args.library_voice_subcommand == "play":
                cls.play_tts_voice(
                    args.path,
                    args.voice,
                    language=args.language,
                    refresh=args.refresh,
                    output_json=args.json,
                )

    @classmethod
    def _refresh_library(
        cls, base_path: str, region: Optional[str] = None, output_json: bool = False
    ) -> Library:
        """Internal method to refresh the library and return it.

        Args:
            base_path (str): The base path of the project.
            region (str): The region to refresh the library for.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            Library: The refreshed library of models.
        """
        account_id: Optional[str] = None

        if region is None:
            project = load_project(base_path, output_json=output_json)
            region = project.region
            account_id = project.account_id

        return Library.load_library_from_api(region, account_id)

    @classmethod
    def refresh_library(
        cls,
        base_path: str,
        region: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Refresh the library of models available in the project's region.

        Args:
            base_path (str): The base path of the project.
            region (str): The region to refresh the library for.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
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
                f"Library refreshed successfully. {n_asr_models} ASR models and {n_llm_models} language models available."
            )

    @classmethod
    def _load_library(
        cls, base_path: str, region: Optional[str] = None, output_json: bool = False
    ) -> Library:
        """Load the library of models for the project's region, refreshing if necessary.

        Args:
            base_path (str): The base path of the project.
            region (Optional[str]): The region to load the library for. If None, the project's region is used.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            Library: The loaded library of models.
        """
        try:
            if region is None:
                project = load_project(base_path, output_json=output_json)
                library = project.library
            else:
                library = Library.load_library_from_file(region)
        except Exception:
            library = None

        if library is None or library.is_stale:
            try:
                library = cls._refresh_library(base_path, region, output_json=output_json)
            except Exception as e:
                if library is None:
                    raise
                if not output_json:
                    from poly.output.console import warning

                    warning(f"Failed to refresh library: {e}. Using previously loaded library.")
        return library

    @classmethod
    def list_asr_models(
        cls,
        base_path: str,
        region: Optional[str] = None,
        refresh: bool = False,
        output_json: bool = False,
    ) -> None:
        """List the ASR models available in the project's region.

        Args:
            base_path (str): The base path of the project.
            region (Optional[str]): The region to list the ASR models for. If None, the project's region is used.
            refresh (bool, optional): Whether to refresh the library before listing. Defaults to False.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
        from poly.output.console import paged_output, print_asr_models, success

        if refresh:
            library = cls._refresh_library(base_path, region, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")
        else:
            library = cls._load_library(base_path, region, output_json=output_json)

        asr_models_json = [asr_model.to_dict() for asr_model in library.asr_models]

        sorted_asr_models = _poly_first(asr_models_json, _is_poly_asr)

        if output_json:
            json_print({"success": True, "asr_models": sorted_asr_models})

        else:
            with paged_output():
                print_asr_models(sorted_asr_models, is_poly=_is_poly_asr)

    @classmethod
    def list_llm_models(
        cls,
        base_path: str,
        region: Optional[str] = None,
        refresh: bool = False,
        output_json: bool = False,
    ) -> None:
        """List the language models available in the project's region.

        Args:
            base_path (str): The base path of the project.
            region (Optional[str]): The region to list the language models for. If None, the project's region is used.
            refresh (bool, optional): Whether to refresh the library before listing. Defaults to False.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
        from poly.output.console import paged_output, print_llm_models, success

        if refresh:
            library = cls._refresh_library(base_path, region, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")
        else:
            library = cls._load_library(base_path, region, output_json=output_json)

        llm_models = [llm_model.to_dict() for llm_model in library.llm_models]

        sorted_llm_models = _poly_first(llm_models, _is_poly_llm)

        if output_json:
            json_print({"success": True, "llm_models": sorted_llm_models})

        else:
            with paged_output():
                print_llm_models(sorted_llm_models, is_poly=_is_poly_llm)

    @classmethod
    def list_tts_voices(
        cls,
        base_path: str,
        refresh: bool = False,
        output_json: bool = False,
        name: Optional[str] = None,
        language: Optional[str] = None,
        gender: Optional[str] = None,
        is_poly_voice: Optional[bool] = None,
        owner: Optional[str] = None,
        archived: bool = False,
    ) -> None:
        """List the TTS voices available in the project's region.

        Args:
            base_path (str): The base path of the project.
            refresh (bool, optional): Whether to refresh the library before listing. Defaults to False.
            name (Optional[str]): The name of the TTS voice.
            language (Optional[str]): The language of the TTS voice.
            gender (Optional[str]): The gender of the TTS voice.
            archived (Optional[bool]): Whether to include archived voices.
            is_poly_voice (Optional[bool]): Whether the voice is a PolyAI voice.
            owner (Optional[str]): "global" for the shared library's voices only, "account" for
                the account's own only. Defaults to both.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
        from poly.output.console import paged_output, print_tts_voices, success

        if refresh:
            library = cls._refresh_library(base_path, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")
        else:
            library = cls._load_library(base_path, output_json=output_json)

        tts_voices = [
            tts_voice
            for tts_voice in library.tts_voices
            if (name is None or name.lower() in tts_voice.name.lower())
            and (
                language is None
                or (tts_voice.metadata.get("accent") or "").lower().startswith(language.lower())
            )
            and (gender is None or tts_voice.metadata.get("gender") == gender)
            and (archived or not tts_voice.metadata.get("archived"))
            and (archived or not tts_voice.is_internal)
            and (not is_poly_voice or tts_voice.poly_ai_voice)
            and (owner is None or tts_voice.owner == owner)
        ]

        # Agent Studio's order, so the first voices are the ones its Recommended shelf shows.
        sorted_tts_voices = sorted(tts_voices, key=lambda tts_voice: tts_voice.rank_key())

        if output_json:
            json_print(
                {"success": True, "voices": [voice.to_dict() for voice in sorted_tts_voices]}
            )

        else:
            with paged_output(title="TTS voices", header_lines=1):
                print_tts_voices(sorted_tts_voices)

    @staticmethod
    def _find_tts_voice(
        library: Library, voice: str, language: Optional[str], output_json: bool = False
    ) -> TTSVoice:
        """Find a voice by name or ID, or report why it can't be found and exit 1."""
        try:
            return library.find_tts_voice(voice, language=language)
        except ValueError as e:
            fail(str(e), output_json)

    @classmethod
    def show_tts_voice(
        cls,
        base_path: str,
        voice: str,
        language: Optional[str] = None,
        refresh: bool = False,
        output_json: bool = False,
    ) -> None:
        """Show a TTS voice in the project's account.

        Args:
            base_path (str): The base path of the project.
            voice (str): The voice's name or ID.
            language (Optional[str]): The voice's language, for a name more than one uses.
            refresh (bool, optional): Whether to refresh the library before listing. Defaults to False.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
        from poly.output.console import print_tts_voice, success

        if refresh:
            library = cls._refresh_library(base_path, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")
        else:
            library = cls._load_library(base_path, output_json=output_json)

        tts_voice = cls._find_tts_voice(library, voice, language, output_json=output_json)

        if output_json:
            json_print({"success": True, "voice": tts_voice.to_dict()})
        else:
            print_tts_voice(tts_voice)

    @classmethod
    def play_tts_voice(
        cls,
        base_path: str,
        voice: str,
        language: Optional[str] = None,
        refresh: bool = False,
        output_json: bool = False,
    ) -> None:
        """Play a TTS voice's recording.

        Args:
            base_path (str): The base path of the project.
            voice (str): The voice's name or ID.
            language (Optional[str]): The voice's language, for a name more than one uses.
            refresh (bool, optional): Whether to refresh the library before playing. Defaults to False.
            output_json (bool, optional): Whether to output the result in JSON format. Defaults to False.

        Returns:
            None
        """
        from poly.output.console import error, info, success

        if refresh:
            library = cls._refresh_library(base_path, output_json=output_json)
            if not output_json:
                success("Library refreshed successfully.")
        else:
            library = cls._load_library(base_path, output_json=output_json)

        tts_voice = cls._find_tts_voice(library, voice, language, output_json=output_json)

        samples = tts_voice.metadata.get("sample_voice") or []
        sample_url = samples[0] if samples else None
        if sample_url is None:
            fail(f"{tts_voice.name} has no recording to play.", output_json)

        if output_json:
            json_print(
                {
                    "success": True,
                    "voice_id": tts_voice.voice_id,
                    "name": tts_voice.name,
                    "sample_voice_url": sample_url,
                }
            )
            return

        # The audio stack ships in the optional [call] extra; import it only when playing.
        try:
            from poly.call.playback import PlaybackError, play_audio_url
        except (ImportError, OSError):
            from rich.markup import escape

            from poly.cli_commands.call import voice_deps_hint

            error(escape(voice_deps_hint("poly library voice play")))
            sys.exit(1)

        info(f"Playing {tts_voice.name}. Press Ctrl+C to stop.")
        try:
            play_audio_url(sample_url)
        except PlaybackError as e:
            error(str(e))
            sys.exit(1)
