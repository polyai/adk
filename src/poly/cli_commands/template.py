"""Template command family: browse and load example project templates.

Copyright PolyAI Limited
"""

import logging
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from contextlib import nullcontext

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project, read_project_config
from poly.handlers.interface import REGIONS
from poly.output.json_output import json_print
from poly.project import AgentStudioProject

logger = logging.getLogger(__name__)


class TemplateCommand(BaseCommand):
    """Browse and load example project templates."""

    command = "template"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``template`` subcommand tree."""
        template_parser = subparsers.add_parser(
            "template",
            parents=[],
            help="Browse and load example project templates.",
            description=(
                "Browse and load example project templates.\n\n"
                "Examples:\n"
                "  poly template list\n"
                "  poly template load restaurant-booking\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        template_subparsers = template_parser.add_subparsers(
            dest="template_subcommand", required=True
        )

        # TEMPLATE LIST
        template_list_parser = template_subparsers.add_parser(
            "list",
            parents=[parents.verbose, parents.json, parents.debug],
            help="List available example project templates.",
            description=(
                "List available example project templates.\n\n"
                "Examples:\n"
                "  poly template list\n"
                "  poly template list --region us-1\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        template_list_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region to query for templates. Defaults to the current project's region.",
        )

        # TEMPLATE LOAD
        template_load_parser = template_subparsers.add_parser(
            "load",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Load an example template into the current project.",
            description=(
                "Load an example template into the current project.\n\n"
                "WARNING: This overwrites your local project resources with the template"
                " contents.\n\n"
                "Examples:\n"
                "  poly template load\n"
                "  poly template load restaurant-booking\n"
                "  poly template load restaurant-booking --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        template_load_parser.add_argument(
            "template_name",
            nargs="?",
            type=str,
            help="Name of the template to load. If omitted, an interactive picker is shown.",
        )
        template_load_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Path to the project. Defaults to current working directory.",
        )
        template_load_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region to query for templates. Defaults to the current project's region.",
        )
        template_load_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            default=False,
            help="Skip the overwrite confirmation prompt.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching template sub-handler."""
        if args.template_subcommand == "list":
            cls.list_templates(
                region=args.region,
                output_json=args.json,
            )
        elif args.template_subcommand == "load":
            cls.load_template(
                path=args.path,
                template_name=args.template_name,
                region=args.region,
                force=args.force,
                output_json=args.json,
            )

    @classmethod
    def _resolve_region_for_templates(cls, region: str | None) -> str:
        """Resolve a region for template commands when none is provided.

        Tries --region flag first, then the current project, then defaults to
        "studio"
        """
        if region:
            return region

        project = read_project_config(os.getcwd())
        if project:
            return project.region

        return "studio"

    @classmethod
    def _fetch_templates(cls, region: str) -> list[dict]:
        """Fetch template projects from the API."""
        return AgentStudioProject.list_templates(region)

    @classmethod
    def _pick_template(cls, templates: list[dict]) -> str | None:
        """Show an interactive template picker. Returns the template display name."""
        import questionary

        choices = []
        for t in templates:
            display = t.get("displayName", "")
            desc = t.get("description", "").strip()
            title = f"{display} — {desc}" if desc else display
            choices.append(questionary.Choice(title=title, value=display))

        return questionary.select(
            "Select a template",
            choices=choices,
            use_search_filter=True,
            use_jk_keys=False,
        ).ask()

    @classmethod
    def list_templates(
        cls,
        region: str | None = None,
        output_json: bool = False,
    ) -> None:
        """List available example project templates."""
        from poly.output.console import error, info, plain

        region = cls._resolve_region_for_templates(region)
        try:
            templates = cls._fetch_templates(region)
        except Exception as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(f"Failed to fetch templates: {e}")
            return

        if output_json:
            json_print({"success": True, "templates": templates})
            return

        if not templates:
            info("No templates available.")
            return

        info(f"Available templates ({len(templates)}):\n")
        for t in templates:
            display = t.get("displayName", "unknown")
            desc = t.get("description", "").strip()
            plain(f"  [bold]{display}[/bold]")
            if desc:
                plain(f"    {desc}")
        plain("")

    @classmethod
    def load_template(
        cls,
        path: str,
        template_name: str | None = None,
        region: str | None = None,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Load a template into the current project via the projection API."""
        from poly.output.console import console, error, info, success, warning

        project = load_project(path, output_json=output_json)
        region = region or project.region

        try:
            templates = cls._fetch_templates(region)
        except Exception as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(f"Failed to fetch templates: {e}")
            return

        if not templates:
            if output_json:
                json_print({"success": False, "error": "No templates available."})
            else:
                info("No templates available.")
            return

        if not template_name:
            if output_json:
                json_print(
                    {
                        "success": False,
                        "error": "template_name is required with --json.",
                    }
                )
                sys.exit(1)
            template_name = cls._pick_template(templates)
            if not template_name:
                warning("No template selected. Exiting.")
                return

        query = template_name.lower()
        template = None
        for t in templates:
            name = t.get("displayName", "")
            if name.lower() == query:
                template = t
                break
        if not template:
            msg = f"Template '{template_name}' not found."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        template_id = template["id"]
        display_name = template.get("displayName", template_id)

        if not force and not output_json:
            import questionary

            confirmed = questionary.confirm(
                f"Loading '{display_name}' will overwrite local project resources. Continue?",
                default=False,
                auto_enter=False,
            ).ask()
            if not confirmed:
                info("Cancelled.")
                return

        ctx = (
            console.status(f"[info]Loading template [bold]{display_name}[/bold]...[/info]")
            if not output_json
            else nullcontext()
        )
        with ctx:
            try:
                project.load_template(region, template_id)
            except Exception as e:
                if output_json:
                    json_print({"success": False, "error": str(e)})
                else:
                    error(str(e))
                sys.exit(1)

        if output_json:
            json_print({"success": True, "template": display_name})
        else:
            success(
                f"Loaded template [bold]{display_name}[/bold]"
                f" into {project.account_id}/{project.project_id}"
            )

    @classmethod
    def offer_template_on_create(cls, path: str, region: str) -> None:
        """Offer to load a template right after project creation."""
        import questionary

        templates = cls._fetch_templates(region)
        if not templates:
            return

        should_load = questionary.confirm(
            "Would you like to load a template into this project?",
            default=False,
            auto_enter=False,
        ).ask()
        if not should_load:
            return

        cls.load_template(
            path=path,
            region=region,
            force=True,
            output_json=False,
        )
