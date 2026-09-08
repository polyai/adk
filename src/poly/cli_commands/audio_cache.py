"""Audio cache command family: manage an agent's cached TTS audio via the
public Audio Cache API.

Copyright PolyAI Limited
"""

import json
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Optional

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.output.json_output import json_print


class AudioCacheCommand(BaseCommand):
    """Manage an agent's cached TTS audio entries."""

    command = "audio-cache"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``audio-cache`` subcommand tree."""
        audio_cache_parser = subparsers.add_parser(
            "audio-cache",
            parents=[parents.verbose],
            help="Manage cached TTS audio via the Audio Cache API.",
            description=(
                "Manage an agent's cached TTS audio entries.\n\n"
                "Examples:\n"
                "  poly audio-cache list\n"
                "  poly audio-cache get-file <entry_id> -o cached.wav\n"
                "  poly audio-cache update-file <entry_id> --file replacement.wav\n"
                "  poly audio-cache synthesize <entry_id> --text 'Hello there' -o preview.wav\n"
                "  poly audio-cache delete <entry_id>\n"
                "  poly audio-cache bulk-delete --ids id1,id2,id3\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        audio_cache_subparsers = audio_cache_parser.add_subparsers(
            dest="audio_cache_subcommand", required=True
        )

        list_parser = audio_cache_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose],
            help="List cached audio entries for the agent.",
            description=(
                "List cached TTS audio entries with metadata (transcript, provider,\n"
                "voice, duration, hit count).\n\n"
                "Examples:\n"
                "  poly audio-cache list\n"
                "  poly audio-cache list --limit 20 --offset 10\n"
                "  poly audio-cache list --sort hit_count:desc\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        list_parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Max number of entries to return (1-200). Defaults to 50.",
        )
        list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of entries to skip. Defaults to 0.",
        )
        list_parser.add_argument(
            "--sort",
            type=str,
            default=None,
            help="Sort expression, e.g. 'hit_count:desc' or 'duration:asc'.",
        )

        get_file_parser = audio_cache_subparsers.add_parser(
            "get-file",
            parents=[parents.path, parents.json, parents.verbose],
            help="Download the cached audio file for an entry.",
            description=(
                "Download the cached WAV audio file for a cache entry.\n\n"
                "Examples:\n"
                "  poly audio-cache get-file <entry_id>\n"
                "  poly audio-cache get-file <entry_id> -o cached.wav\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        get_file_parser.add_argument("entry_id", type=str, help="The audio cache entry ID.")
        get_file_parser.add_argument(
            "-o",
            "--output",
            type=str,
            default=None,
            help="Output file path. Defaults to <entry_id>.wav.",
        )

        update_file_parser = audio_cache_subparsers.add_parser(
            "update-file",
            parents=[parents.path, parents.json, parents.verbose],
            help="Replace the audio file for a cache entry.",
            description=(
                "Replace the audio file for an existing cache entry. Maximum file\n"
                "size is 6MB.\n\n"
                "Examples:\n"
                "  poly audio-cache update-file <entry_id> --file replacement.wav\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        update_file_parser.add_argument("entry_id", type=str, help="The audio cache entry ID.")
        update_file_parser.add_argument(
            "--file",
            type=str,
            required=True,
            metavar="FILE",
            dest="file_path",
            help="Path to the replacement WAV file.",
        )
        update_file_parser.add_argument(
            "--filename",
            type=str,
            default=None,
            help="Filename to record for the uploaded audio. Defaults to <entry_id>.wav.",
        )

        update_details_parser = audio_cache_subparsers.add_parser(
            "update-details",
            parents=[parents.path, parents.json, parents.verbose],
            help="Replace the audio file and voice tuning settings for a cache entry.",
            description=(
                "Replace both the audio file and voice tuning settings for a cache\n"
                "entry. Maximum file size is 6MB.\n\n"
                "Examples:\n"
                "  poly audio-cache update-details <entry_id> --file r.wav --text 'Hi there'\n"
                "  poly audio-cache update-details <entry_id> --file r.wav --text 'Hi'"
                " --config '{\"stability\": 0.5}'\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        update_details_parser.add_argument("entry_id", type=str, help="The audio cache entry ID.")
        update_details_parser.add_argument(
            "--file",
            type=str,
            required=True,
            metavar="FILE",
            dest="file_path",
            help="Path to the replacement WAV file.",
        )
        update_details_parser.add_argument(
            "--text",
            type=str,
            required=True,
            help="Transcript text associated with the audio.",
        )
        update_details_parser.add_argument(
            "--config",
            type=str,
            default="{}",
            help="JSON object of provider-specific voice tuning settings.",
        )

        delete_parser = audio_cache_subparsers.add_parser(
            "delete",
            parents=[parents.path, parents.json, parents.verbose],
            help="Delete a cached audio entry.",
            description=(
                "Permanently delete a cached audio entry and its audio file.\n\n"
                "Examples:\n"
                "  poly audio-cache delete <entry_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        delete_parser.add_argument("entry_id", type=str, help="The audio cache entry ID.")

        bulk_delete_parser = audio_cache_subparsers.add_parser(
            "bulk-delete",
            parents=[parents.path, parents.json, parents.verbose],
            help="Delete multiple cached audio entries by ID.",
            description=(
                "Delete multiple audio cache entries in a single request. Best-effort:\n"
                "reports which IDs succeeded and which failed. Maximum 20 IDs.\n\n"
                "Examples:\n"
                "  poly audio-cache bulk-delete --ids id1,id2,id3\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        bulk_delete_parser.add_argument(
            "--ids",
            type=str,
            required=True,
            help="Comma-separated list of audio cache entry IDs to delete (max 20).",
        )

        synthesize_parser = audio_cache_subparsers.add_parser(
            "synthesize",
            parents=[parents.path, parents.json, parents.verbose],
            help="Preview TTS audio using an existing cache entry's voice config.",
            description=(
                "Generate a TTS audio preview using an existing cache entry's voice\n"
                "and provider configuration, without saving it to the cache.\n\n"
                "Examples:\n"
                "  poly audio-cache synthesize <entry_id> --text 'Hello there'\n"
                "  poly audio-cache synthesize <entry_id> --text 'Hi' --language en-US -o out.wav\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        synthesize_parser.add_argument("entry_id", type=str, help="The audio cache entry ID.")
        synthesize_parser.add_argument(
            "--text",
            type=str,
            required=True,
            help="Text to synthesize.",
        )
        synthesize_parser.add_argument(
            "--config",
            type=str,
            default="{}",
            help="JSON object of provider-specific voice tuning settings.",
        )
        synthesize_parser.add_argument(
            "--language",
            type=str,
            default=None,
            help="BCP-47 language tag, e.g. 'en-US'.",
        )
        synthesize_parser.add_argument(
            "-o",
            "--output",
            type=str,
            default=None,
            help="Output file path. Defaults to <entry_id>-preview.wav.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching audio-cache sub-handler."""
        if args.audio_cache_subcommand == "list":
            cls.audio_cache_list(
                args.path,
                limit=args.limit,
                offset=args.offset,
                sort=args.sort,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "get-file":
            cls.audio_cache_get_file(
                args.path,
                args.entry_id,
                output_path=args.output,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "update-file":
            cls.audio_cache_update_file(
                args.path,
                args.entry_id,
                args.file_path,
                filename=args.filename,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "update-details":
            cls.audio_cache_update_details(
                args.path,
                args.entry_id,
                args.file_path,
                args.text,
                args.config,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "delete":
            cls.audio_cache_delete(
                args.path,
                args.entry_id,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "bulk-delete":
            cls.audio_cache_bulk_delete(
                args.path,
                args.ids,
                output_json=args.json,
            )
        elif args.audio_cache_subcommand == "synthesize":
            cls.audio_cache_synthesize(
                args.path,
                args.entry_id,
                args.text,
                args.config,
                language=args.language,
                output_path=args.output,
                output_json=args.json,
            )

    @classmethod
    def audio_cache_list(
        cls,
        base_path: str,
        limit: int = 50,
        offset: int = 0,
        sort: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """List cached audio entries for the agent.

        Args:
            base_path: Base path for the project.
            limit: Max number of entries to return.
            offset: Number of entries to skip.
            sort: Optional sort expression, e.g. "hit_count:desc".
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, print_audio_cache_entries

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.list_audio_cache(
            region=project.region,
            project_id=project.project_id,
            limit=limit,
            offset=offset,
            sort=sort,
        )
        entries = result.get("entries", [])

        if output_json:
            json_print(result)
        else:
            if not entries:
                info("No audio cache entries found.")
                return
            print_audio_cache_entries(entries)

    @classmethod
    def audio_cache_get_file(
        cls,
        base_path: str,
        entry_id: str,
        output_path: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Download the cached audio file for an entry.

        Args:
            base_path: Base path for the project.
            entry_id: The audio cache entry ID.
            output_path: Output file path. Defaults to <entry_id>.wav.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        audio_data = AgentStudioInterface.get_audio_cache_file(
            region=project.region,
            project_id=project.project_id,
            entry_id=entry_id,
        )

        if output_path is None:
            output_path = f"{entry_id}.wav"

        with open(output_path, "wb") as f:
            f.write(audio_data)

        size_bytes = len(audio_data)
        if output_json:
            json_print(
                {
                    "success": True,
                    "entry_id": entry_id,
                    "output_path": output_path,
                    "size_bytes": size_bytes,
                }
            )
        else:
            size_mb = size_bytes / 1_000_000
            success(f"Audio saved to {output_path} ({size_mb:.1f} MB)")

    @classmethod
    def audio_cache_update_file(
        cls,
        base_path: str,
        entry_id: str,
        file_path: str,
        filename: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Replace the audio file for a cache entry.

        Args:
            base_path: Base path for the project.
            entry_id: The audio cache entry ID.
            file_path: Local path to the replacement WAV file.
            filename: Optional filename to record for the uploaded audio.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        AgentStudioInterface.update_audio_cache_file(
            region=project.region,
            project_id=project.project_id,
            entry_id=entry_id,
            audio_bytes=audio_bytes,
            filename=filename or os.path.basename(file_path),
        )

        if output_json:
            json_print({"success": True, "entry_id": entry_id, "size_bytes": len(audio_bytes)})
        else:
            success(f"Updated audio file for entry {entry_id}.")

    @classmethod
    def audio_cache_update_details(
        cls,
        base_path: str,
        entry_id: str,
        file_path: str,
        text: str,
        config: str,
        output_json: bool = False,
    ) -> None:
        """Replace the audio file and voice tuning settings for a cache entry.

        Args:
            base_path: Base path for the project.
            entry_id: The audio cache entry ID.
            file_path: Local path to the replacement WAV file.
            text: Transcript text associated with the audio.
            config: JSON string of provider-specific voice tuning settings.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)
        try:
            parsed_config = json.loads(config)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in --config: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        with open(file_path, "rb") as f:
            audio_bytes = f.read()

        AgentStudioInterface.update_audio_cache_details(
            region=project.region,
            project_id=project.project_id,
            entry_id=entry_id,
            audio_bytes=audio_bytes,
            settings={"text": text, "config": parsed_config},
            filename=os.path.basename(file_path),
        )

        if output_json:
            json_print({"success": True, "entry_id": entry_id, "size_bytes": len(audio_bytes)})
        else:
            success(f"Updated audio and details for entry {entry_id}.")

    @classmethod
    def audio_cache_delete(
        cls,
        base_path: str,
        entry_id: str,
        output_json: bool = False,
    ) -> None:
        """Delete a cached audio entry.

        Args:
            base_path: Base path for the project.
            entry_id: The audio cache entry ID.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.delete_audio_cache_entry(
            region=project.region,
            project_id=project.project_id,
            entry_id=entry_id,
        )

        if output_json:
            json_print(result)
        else:
            success(f"Deleted audio cache entry {entry_id}.")

    @classmethod
    def audio_cache_bulk_delete(
        cls,
        base_path: str,
        ids: str,
        output_json: bool = False,
    ) -> None:
        """Delete multiple cached audio entries by ID.

        Args:
            base_path: Base path for the project.
            ids: Comma-separated list of audio cache entry IDs.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)
        id_list = [i.strip() for i in ids.split(",") if i.strip()]

        result = AgentStudioInterface.bulk_delete_audio_cache(
            region=project.region,
            project_id=project.project_id,
            ids=id_list,
        )

        if output_json:
            json_print(result)
            return

        deleted = result.get("deleted", [])
        failed = result.get("failed", [])
        if deleted:
            success(f"Deleted {len(deleted)} entries: {', '.join(deleted)}")
        if failed:
            error(f"Failed to delete {len(failed)} entries: {', '.join(failed)}")

    @classmethod
    def audio_cache_synthesize(
        cls,
        base_path: str,
        entry_id: str,
        text: str,
        config: str,
        language: Optional[str] = None,
        output_path: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Generate a TTS audio preview using an existing cache entry's voice config.

        Args:
            base_path: Base path for the project.
            entry_id: The audio cache entry ID whose voice/provider config to use.
            text: Text to synthesize.
            config: JSON string of provider-specific voice tuning settings.
            language: Optional BCP-47 language tag.
            output_path: Output file path. Defaults to <entry_id>-preview.wav.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)
        try:
            parsed_config = json.loads(config)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in --config: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        audio_data = AgentStudioInterface.synthesize_audio_cache(
            region=project.region,
            project_id=project.project_id,
            entry_id=entry_id,
            text=text,
            config=parsed_config,
            language=language,
        )

        if output_path is None:
            output_path = f"{entry_id}-preview.wav"

        with open(output_path, "wb") as f:
            f.write(audio_data)

        size_bytes = len(audio_data)
        if output_json:
            json_print(
                {
                    "success": True,
                    "entry_id": entry_id,
                    "output_path": output_path,
                    "size_bytes": size_bytes,
                }
            )
        else:
            size_mb = size_bytes / 1_000_000
            success(f"Preview audio saved to {output_path} ({size_mb:.1f} MB)")
