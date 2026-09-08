"""Project command family: manage, create, delete, duplicate projects; init and studio.

Copyright PolyAI Limited
"""

import os
import re
import sys
from argparse import SUPPRESS, ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from contextlib import nullcontext

from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project, parse_from_projection_json
from poly.handlers.interface import REGIONS, AgentStudioInterface
from poly.output.json_output import json_print
from poly.project import AgentStudioProject


class ProjectCommand(BaseCommand):
    """Manage Agent Studio projects (list, create, delete, duplicate)."""

    command = "project"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``project`` subcommand tree."""
        # PROJECT
        project_parser = subparsers.add_parser(
            "project",
            parents=[],
            help="Manage Agent Studio projects.",
            description=(
                "Manage Agent Studio projects.\n\n"
                "Examples:\n"
                "  poly project list\n"
                "  poly project create\n"
                "  poly project delete\n"
                "  poly project duplicate\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        project_subparsers = project_parser.add_subparsers(dest="project_subcommand", required=True)

        # PROJECT LIST
        project_list_parser = project_subparsers.add_parser(
            "list",
            parents=[parents.verbose, parents.json, parents.debug],
            help="List Agent Studio projects in an account.",
            description=(
                "List Agent Studio projects in an account.\n\n"
                "Examples:\n"
                "  poly project list\n"
                "  poly project list --region us-1 --account_id my-account\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        project_list_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        project_list_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )

        # PROJECT CREATE
        project_create_parser = project_subparsers.add_parser(
            "create",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Create a new Agent Studio project under an account.",
            description=(
                "Create a new Agent Studio project under an interactively selected account.\n\n"
                "Examples:\n"
                "  poly project create\n"
                "  poly project create --region us-1 --account_id my-account --name my-project\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        project_create_parser.add_argument(
            "--base-path",
            type=str,
            default=os.getcwd(),
            help="Base path to initialize the project. Defaults to current working directory.",
        )
        project_create_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        project_create_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )
        project_create_parser.add_argument(
            "--name",
            type=str,
            dest="project_name",
            help="Name for the new project.",
        )
        project_create_parser.add_argument(
            "--id",
            "--project_id",
            type=str,
            dest="project_id",
            help="Optional unique slug/ID for the project. If not provided the platform will generate one",
        )
        project_create_parser.add_argument(
            "--greeting",
            type=str,
            default="Hello, how can I help you?",
            help="Initial greeting message for the agent.",
        )
        project_create_parser.add_argument(
            "--voice-id",
            type=str,
            dest="voice_id",
            help="Voice ID for the agent. Defaults to a region-specific voice.",
        )

        # PROJECT DELETE
        project_delete_parser = project_subparsers.add_parser(
            "delete",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Delete an Agent Studio project.",
            description=(
                "Delete an Agent Studio project.\n\n"
                "Examples:\n"
                "  poly project delete\n"
                "  poly project delete --region us-1 --account_id my-account"
                " --project_id my-project\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        project_delete_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        project_delete_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )
        project_delete_parser.add_argument(
            "--project_id",
            type=str,
            help="Project ID to delete.",
        )
        project_delete_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            default=False,
            help="Skip the confirmation prompt.",
        )

        # PROJECT DUPLICATE
        project_duplicate_parser = project_subparsers.add_parser(
            "duplicate",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Duplicate an Agent Studio project.",
            description=(
                "Duplicate an Agent Studio project.\n\n"
                "Examples:\n"
                "  poly project duplicate\n"
                "  poly project duplicate --region us-1 --account_id my-account"
                " --project_id my-project --name my-copy\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        project_duplicate_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        project_duplicate_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )
        project_duplicate_parser.add_argument(
            "--project_id",
            type=str,
            help="Project ID to duplicate.",
        )
        project_duplicate_parser.add_argument(
            "--name",
            type=str,
            dest="new_name",
            help="Name for the duplicated project.",
        )
        project_duplicate_parser.add_argument(
            "--id",
            "--new_project_id",
            type=str,
            dest="new_project_id",
            help="Optional unique slug/ID for the new project."
            " If not provided the platform will generate one.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching project sub-handler."""
        if args.project_subcommand == "list":
            cls.list_projects(
                region=args.region,
                account_id=args.account_id,
                output_json=args.json,
            )
        elif args.project_subcommand == "create":
            cls.create_project(
                args.base_path,
                region=args.region,
                account_id=args.account_id,
                project_name=args.project_name,
                project_id=args.project_id,
                greeting=args.greeting,
                voice_id=args.voice_id,
                output_json=args.json,
            )
        elif args.project_subcommand == "delete":
            cls.delete_project(
                region=args.region,
                account_id=args.account_id,
                project_id=args.project_id,
                force=args.force,
                output_json=args.json,
            )
        elif args.project_subcommand == "duplicate":
            cls.duplicate_project(
                region=args.region,
                account_id=args.account_id,
                project_id=args.project_id,
                new_name=args.new_name,
                new_project_id=args.new_project_id,
                output_json=args.json,
            )

    @classmethod
    def create_project(
        cls,
        base_path: str,
        region: str = None,
        account_id: str = None,
        project_name: str = None,
        project_id: str = None,
        greeting: str = "Hello, how can I help you?",
        voice_id: str = None,
        output_json: bool = False,
    ) -> None:
        """Create a new Agent Studio project under an interactively selected account."""
        import questionary

        from poly.output.console import console, error, info, success, warning

        if output_json and not (region and account_id and project_name):
            json_print(
                {
                    "success": False,
                    "error": (
                        "create project with --json requires --region, --account_id, and --name."
                    ),
                }
            )
            sys.exit(1)

        api_handler = AgentStudioInterface()

        if not region:
            with console.status("[info]Fetching available regions...[/info]"):
                regions = api_handler.get_accessible_regions()
            if not regions:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accessible regions found for your API key.",
                        }
                    )
                else:
                    error("No accessible regions found for your API key.")
                sys.exit(1)
            if len(regions) == 1:
                region = regions[0]
                if not output_json:
                    info(f"Auto-selected region [bold]{region}[/bold].")
            else:
                region = questionary.select("Select Region", choices=regions).ask()
                if not region:
                    warning("No region selected. Exiting.")
                    return

        if not account_id:
            accounts = api_handler.get_accounts(region)
            if not accounts:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accounts found in the selected region.",
                        }
                    )
                else:
                    error("No accounts found in the selected region.")
                sys.exit(1)
            if len(accounts) == 1:
                account_id, account_name = next(iter(accounts.items()))
                if not output_json:
                    info(f"Auto-selected account [bold]{account_name}[/bold].")
            else:
                account_choices = [
                    questionary.Choice(title=f"{name} ({acc_id})", value=acc_id)
                    for acc_id, name in accounts.items()
                ]
                account_id = questionary.select(
                    "Select Account",
                    choices=account_choices,
                    use_search_filter=True,
                    use_jk_keys=False,
                ).ask()
                if not account_id:
                    if output_json:
                        json_print({"success": False, "error": "No account selected."})
                        sys.exit(1)
                    warning("No account selected. Exiting.")
                    return

        if not project_name:
            project_name = questionary.text("Enter project name:").ask()
            if not project_name or not project_name.strip():
                warning("No project name provided. Exiting.")
                return
            project_name = project_name.strip()

        if not project_id and region != "studio" and not output_json:
            project_id = questionary.text(
                "Enter project ID (leave empty to let the platform generate one):",
                validate=lambda val: (
                    True
                    if not val or re.fullmatch(r"[a-zA-Z0-9-]+", val)
                    else "Project ID can only contain alphanumeric characters and dashes."
                ),
            ).ask()
            if project_id is None:
                return
            project_id = project_id.strip() or None

        ctx = (
            console.status(
                f"[info]Creating project [bold]{project_name}[/bold]"
                f" under account {account_id}...[/info]"
            )
            if not output_json
            else nullcontext()
        )

        with ctx:
            try:
                result = api_handler.create_project(
                    region, account_id, project_name, project_id, greeting, voice_id
                )
            except Exception as e:
                if output_json:
                    json_print({"success": False, "error": str(e)})
                else:
                    error(f"Failed to create project: {e}")
                sys.exit(1)

        project_id = result.get("id")
        if not project_id:
            if output_json:
                json_print({"success": False, "error": "No project ID returned by API."})
            else:
                error("No project ID returned by API.")
            sys.exit(1)

        if not output_json:
            success(f"Created project [bold]{project_name}[/bold] ({project_id})")

        InitCommand.init_project(
            base_path,
            region=region,
            account_id=account_id,
            project_id=project_id,
            output_json=output_json,
        )

        if not output_json and sys.stdin.isatty():
            try:
                from poly.cli_commands.template import TemplateCommand

                project_path = os.path.join(base_path, account_id, project_id)
                TemplateCommand.offer_template_on_create(project_path, region)
            except Exception:
                pass

    @classmethod
    def list_projects(
        cls,
        region: str = None,
        account_id: str = None,
        output_json: bool = False,
    ) -> None:
        """List Agent Studio projects in an account."""
        import questionary

        from poly.output.console import console, error, info, print_agents, warning

        if output_json and not (region and account_id):
            json_print(
                {
                    "success": False,
                    "error": "project list with --json requires --region and --account_id.",
                }
            )
            sys.exit(1)

        api_handler = AgentStudioInterface()

        if not region:
            with console.status("[info]Fetching available regions...[/info]"):
                regions = api_handler.get_accessible_regions()
            if not regions:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accessible regions found for your API key.",
                        }
                    )
                else:
                    error("No accessible regions found for your API key.")
                sys.exit(1)
            if len(regions) == 1:
                region = regions[0]
                if not output_json:
                    info(f"Auto-selected region [bold]{region}[/bold].")
            else:
                region = questionary.select("Select Region", choices=regions).ask()
                if not region:
                    return

        if not account_id:
            accounts = api_handler.get_accounts(region)
            if not accounts:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accounts found in the selected region.",
                        }
                    )
                else:
                    error("No accounts found in the selected region.")
                sys.exit(1)
            if len(accounts) == 1:
                account_id, account_name = next(iter(accounts.items()))
                if not output_json:
                    info(f"Auto-selected account [bold]{account_name}[/bold].")
            else:
                account_choices = [
                    questionary.Choice(title=f"{name} ({acc_id})", value=acc_id)
                    for acc_id, name in accounts.items()
                ]
                account_id = questionary.select(
                    "Select Account",
                    choices=account_choices,
                    use_search_filter=True,
                    use_jk_keys=False,
                ).ask()
                if not account_id:
                    if output_json:
                        json_print({"success": False, "error": "No account selected."})
                        sys.exit(1)
                    warning("No account selected. Exiting.")
                    return

        with (
            console.status("[info]Fetching agents...[/info]") if not output_json else nullcontext()
        ):
            agents = api_handler.list_agents(region, account_id)

        if output_json:
            json_print(
                {
                    "success": True,
                    "agents": [
                        {
                            "project_id": a.get("project_id"),
                            "agent_name": a.get("agentName"),
                            "updated_at": a.get("updatedAt"),
                            "branch_count": a.get("branchCount"),
                        }
                        for a in agents
                    ],
                }
            )
        elif not agents:
            warning("No agents found in this account.")
        else:
            print_agents(agents)

    @classmethod
    def delete_project(
        cls,
        region: str = None,
        account_id: str = None,
        project_id: str = None,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Delete an Agent Studio project."""
        import questionary

        from poly.output.console import console, error, info, success, warning

        if output_json and not (region and account_id and project_id):
            json_print(
                {
                    "success": False,
                    "error": (
                        "project delete with --json requires"
                        " --region, --account_id, and --project_id."
                    ),
                }
            )
            sys.exit(1)

        api_handler = AgentStudioInterface()

        if not region:
            with console.status("[info]Fetching available regions...[/info]"):
                regions = api_handler.get_accessible_regions()
            if not regions:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accessible regions found for your API key.",
                        }
                    )
                else:
                    error("No accessible regions found for your API key.")
                sys.exit(1)
            if len(regions) == 1:
                region = regions[0]
                if not output_json:
                    info(f"Auto-selected region [bold]{region}[/bold].")
            else:
                region = questionary.select("Select Region", choices=regions).ask()
                if not region:
                    warning("No region selected. Exiting.")
                    return

        if not account_id:
            accounts = api_handler.get_accounts(region)
            if not accounts:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accounts found in the selected region.",
                        }
                    )
                else:
                    error("No accounts found in the selected region.")
                sys.exit(1)
            if len(accounts) == 1:
                account_id, account_name = next(iter(accounts.items()))
                if not output_json:
                    info(f"Auto-selected account [bold]{account_name}[/bold].")
            else:
                account_choices = [
                    questionary.Choice(title=f"{name} ({acc_id})", value=acc_id)
                    for acc_id, name in accounts.items()
                ]
                account_id = questionary.select(
                    "Select Account",
                    choices=account_choices,
                    use_search_filter=True,
                    use_jk_keys=False,
                ).ask()
                if not account_id:
                    if output_json:
                        json_print({"success": False, "error": "No account selected."})
                        sys.exit(1)
                    warning("No account selected. Exiting.")
                    return

        if not project_id:
            agents = api_handler.get_agents(region, account_id)
            if not agents:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No agents found in the selected account.",
                        }
                    )
                else:
                    error("No agents found in the selected account.")
                sys.exit(1)
            agent_choices = [
                questionary.Choice(title=f"{name} ({aid})", value=aid)
                for aid, name in agents.items()
            ]
            project_id = questionary.select(
                "Select Agent",
                choices=agent_choices,
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not project_id:
                warning("No agent selected. Exiting.")
                return
            agent_name = agents.get(project_id)
        else:
            agents = api_handler.get_agents(region, account_id)
            agent_name = agents.get(project_id)

        display_name = f"{agent_name} ({project_id})" if agent_name else project_id

        if not force and not output_json:
            confirmed = questionary.confirm(
                f"Are you sure you want to delete project '{display_name}'?"
                " This action cannot be undone.",
                default=False,
                auto_enter=False,
            ).ask()
            if not confirmed:
                warning("Aborted.")
                return

        ctx = (
            console.status(f"[info]Deleting project [bold]{display_name}[/bold]...[/info]")
            if not output_json
            else nullcontext()
        )

        with ctx:
            try:
                api_handler.delete_project(region, project_id)
            except Exception as e:
                if output_json:
                    json_print({"success": False, "error": str(e)})
                else:
                    error(f"Failed to delete project: {e}")
                sys.exit(1)

        if output_json:
            json_print({"success": True, "project_id": project_id})
        else:
            success(f"Deleted project [bold]{display_name}[/bold].")

    @classmethod
    def duplicate_project(
        cls,
        region: str = None,
        account_id: str = None,
        project_id: str = None,
        new_name: str = None,
        new_project_id: str = None,
        output_json: bool = False,
    ) -> None:
        """Duplicate an Agent Studio project."""
        import questionary

        from poly.output.console import console, error, info, success, warning

        if output_json and not (region and account_id and project_id and new_name):
            json_print(
                {
                    "success": False,
                    "error": (
                        "project duplicate with --json requires"
                        " --region, --account_id, --project_id, and --name."
                    ),
                }
            )
            sys.exit(1)

        api_handler = AgentStudioInterface()

        if not region:
            with console.status("[info]Fetching available regions...[/info]"):
                regions = api_handler.get_accessible_regions()
            if not regions:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accessible regions found for your API key.",
                        }
                    )
                else:
                    error("No accessible regions found for your API key.")
                sys.exit(1)
            if len(regions) == 1:
                region = regions[0]
                if not output_json:
                    info(f"Auto-selected region [bold]{region}[/bold].")
            else:
                region = questionary.select("Select Region", choices=regions).ask()
                if not region:
                    warning("No region selected. Exiting.")
                    return

        if not account_id:
            accounts = api_handler.get_accounts(region)
            if not accounts:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accounts found in the selected region.",
                        }
                    )
                else:
                    error("No accounts found in the selected region.")
                sys.exit(1)
            if len(accounts) == 1:
                account_id, account_name = next(iter(accounts.items()))
                if not output_json:
                    info(f"Auto-selected account [bold]{account_name}[/bold].")
            else:
                account_choices = [
                    questionary.Choice(title=f"{name} ({acc_id})", value=acc_id)
                    for acc_id, name in accounts.items()
                ]
                account_id = questionary.select(
                    "Select Account",
                    choices=account_choices,
                    use_search_filter=True,
                    use_jk_keys=False,
                ).ask()
                if not account_id:
                    if output_json:
                        json_print({"success": False, "error": "No account selected."})
                        sys.exit(1)
                    warning("No account selected. Exiting.")
                    return

        if not project_id:
            agents = api_handler.get_agents(region, account_id)
            if not agents:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No agents found in the selected account.",
                        }
                    )
                else:
                    error("No agents found in the selected account.")
                sys.exit(1)
            agent_choices = [
                questionary.Choice(title=f"{name} ({aid})", value=aid)
                for aid, name in agents.items()
            ]
            project_id = questionary.select(
                "Select Agent",
                choices=agent_choices,
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not project_id:
                warning("No agent selected. Exiting.")
                return
            agent_name = agents.get(project_id)
        else:
            agents = api_handler.get_agents(region, account_id)
            agent_name = agents.get(project_id)

        display_name = f"{agent_name} ({project_id})" if agent_name else project_id

        if not new_name:
            default_name = f"{agent_name} (copy)" if agent_name else ""
            new_name = questionary.text(
                "Enter name for the duplicated project:", default=default_name
            ).ask()
            if not new_name or not new_name.strip():
                warning("No project name provided. Exiting.")
                return
            new_name = new_name.strip()

        if not new_project_id:
            new_project_id = questionary.text(
                "Enter project ID for the duplicate (leave empty to auto-generate):",
                validate=lambda val: (
                    True
                    if not val or re.fullmatch(r"[a-zA-Z0-9-]+", val)
                    else "Project ID can only contain alphanumeric characters and dashes."
                ),
            ).ask()
            if new_project_id is None:
                return
            new_project_id = new_project_id.strip() or None

        ctx = (
            console.status(f"[info]Duplicating project [bold]{display_name}[/bold]...[/info]")
            if not output_json
            else nullcontext()
        )

        with ctx:
            try:
                result = api_handler.duplicate_project(region, project_id, new_name, new_project_id)
            except Exception as e:
                if output_json:
                    json_print({"success": False, "error": str(e)})
                else:
                    error(f"Failed to duplicate project: {e}")
                sys.exit(1)

        new_id = result.get("id")
        new_display = result.get("name", new_name)

        if output_json:
            json_print({"success": True, "project_id": new_id, "agent_name": new_display})
        else:
            success(
                f"Duplicated [bold]{display_name}[/bold] → [bold]{new_display}[/bold] ({new_id})"
            )


class InitCommand(BaseCommand):
    """Initialize a new Agent Studio project."""

    command = "init"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``init`` subcommand."""
        init_parser = subparsers.add_parser(
            "init",
            parents=[parents.verbose, parents.json, parents.debug],
            help="Initialize a new Agent Studio project.",
            description="Initialize a new Agent Studio project.\n\nExamples:\n  poly init --region eu-west-1 --account_id 123 --project_id my_project\n  poly init  # (interactive selection)",
            formatter_class=RawTextHelpFormatter,
        )
        init_parser.add_argument(
            "--base-path",
            type=str,
            default=os.getcwd(),
            help="Base path to initialize the project. Defaults to current working directory.",
        )
        init_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
            help="Region for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--account_id",
            type=str,
            help="Account ID for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--project_id",
            type=str,
            help="Project ID for the Agent Studio project.",
        )
        init_parser.add_argument(
            "--format", action="store_true", help="Format resources after init."
        )
        init_parser.add_argument(
            "--from-projection",
            type=str,
            metavar="JSON|-",
            help=SUPPRESS,
            default=None,
        )
        init_parser.add_argument(
            "--output-json-projection",
            action="store_true",
            help=SUPPRESS,
            default=False,
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the init handler."""
        cls.init_project(
            args.base_path,
            args.region,
            args.account_id,
            args.project_id,
            args.format,
            args.from_projection,
            output_json=args.json,
            output_json_projection=args.output_json_projection,
        )

    @classmethod
    def init_project(
        cls,
        base_path: str,
        region: str = None,
        account_id: str = None,
        project_id: str = None,
        format: bool = False,
        from_projection: str = None,
        output_json: bool = False,
        output_json_projection: bool = False,
    ) -> None:
        """Initialize a new Agent Studio project."""
        import questionary

        from poly.output.console import console, error, info, success, warning

        if output_json and not (region and account_id and project_id):
            json_print(
                {
                    "success": False,
                    "error": "init with --json requires --region, --account_id, and --project_id.",
                }
            )
            sys.exit(1)

        api_handler = AgentStudioInterface()

        if not region:
            with console.status("[info]Fetching available regions...[/info]"):
                regions = api_handler.get_accessible_regions()
            if not regions:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accessible regions found for your API key.",
                        }
                    )
                else:
                    error("No accessible regions found for your API key.")
                sys.exit(1)
            if len(regions) == 1:
                region = regions[0]
                if not output_json:
                    info(f"Auto-selected region [bold]{region}[/bold].")
            else:
                region = questionary.select("Select Region", choices=regions).ask()

        account_name = None
        if not account_id:
            accounts = api_handler.get_accounts(region)
            if not accounts:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No accounts found in the selected region.",
                        }
                    )
                else:
                    error("No accounts found in the selected region.")
                sys.exit(1)
            if len(accounts) == 1:
                account_id, account_name = next(iter(accounts.items()))
                if not output_json:
                    info(f"Auto-selected account [bold]{account_name}[/bold].")
            else:
                account_choices = [
                    questionary.Choice(title=f"{name} ({acc_id})", value=acc_id)
                    for acc_id, name in accounts.items()
                ]
                account_id = questionary.select(
                    "Select Account",
                    choices=account_choices,
                    use_search_filter=True,
                    use_jk_keys=False,
                ).ask()
                if not account_id:
                    if output_json:
                        json_print(
                            {
                                "success": False,
                                "error": "No account selected.",
                            }
                        )
                        sys.exit(1)
                    warning("No account selected. Exiting.")
                    return
                account_name = accounts[account_id]
        else:
            accounts = api_handler.get_accounts(region)
            account_name = accounts.get(account_id)

        if not project_id:
            projects = api_handler.get_projects(region, account_id)

            if not projects:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No projects found in the selected account.",
                        }
                    )
                    sys.exit(1)

                should_create = questionary.confirm(
                    "No projects found in this account. Would you like to create one?"
                ).ask()
                if not should_create:
                    return

                ProjectCommand.create_project(
                    base_path,
                    region=region,
                    account_id=account_id,
                    output_json=False,
                )
                return

            project_choices = [
                questionary.Choice(title=f"{name} ({proj_id})", value=proj_id)
                for proj_id, name in projects.items()
            ]

            project_id = questionary.select(
                "Select Project",
                choices=project_choices,
                use_search_filter=True,
                use_jk_keys=False,
            ).ask()
            if not project_id:
                if output_json:
                    json_print(
                        {
                            "success": False,
                            "error": "No project selected.",
                        }
                    )
                    sys.exit(1)
                warning("No project selected. Exiting.")
                return

            project_name = projects.get(project_id)
        else:
            # project_id was passed directly — look up the name
            projects = api_handler.get_projects(region, account_id)
            project_name = projects.get(project_id)

        projection_json = parse_from_projection_json(
            from_projection,
            json_errors=output_json or output_json_projection,
        )

        ctx = (
            console.status(f"[info]Initializing project {account_id}/{project_id}...[/info]")
            if not output_json
            else nullcontext()
        )
        on_save = None

        with ctx as status:
            if status:

                def on_save(current: int, total: int) -> None:
                    status.update(f"[info]Saving resources ({current}/{total})...[/info]")

            project, projection = AgentStudioProject.init_project(
                base_path=base_path,
                region=region,
                account_id=account_id,
                project_id=project_id,
                project_name=project_name,
                account_name=account_name,
                format=format,
                projection_json=projection_json,
                on_save=on_save,
            )

        if not project:
            if output_json:
                json_print({"success": False, "error": "Failed to initialize the project."})
            else:
                error("Failed to initialize the project.")
            sys.exit(1)

        if output_json or output_json_projection:
            json_output = {
                "success": True,
                "root_path": project.root_path,
            }
            if output_json_projection:
                json_output["projection"] = projection
            json_print(json_output)
        else:
            success(f"Project initialized at {project.root_path}")
            info(
                f'Change your working directory to your project\'s directory to continue. "cd {project.root_path}"'
            )


class StudioCommand(BaseCommand):
    """Open the current project in Agent Studio (web)."""

    command = "studio"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``studio`` subcommand."""
        studio_parser = subparsers.add_parser(
            "studio",
            parents=[parents.verbose, parents.json],
            help="Open the current project in Agent Studio (web).",
            description=(
                "Open the project in the Agent Studio web application using the default browser."
            ),
            formatter_class=RawTextHelpFormatter,
        )
        studio_parser.add_argument(
            "--path",
            type=str,
            default=os.getcwd(),
            help="Base path to the project. Defaults to current working directory.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the studio handler."""
        cls.open_agent_studio(base_path=args.path, output_json=args.json)

    @classmethod
    def open_agent_studio(cls, base_path: str = "", output_json: bool = False) -> None:
        """Open the current project in the Agent Studio web UI."""
        import webbrowser

        from poly.output.console import info

        project = load_project(base_path or os.getcwd(), output_json=output_json)
        url = f"{project.studio_base_url}/home?branchId={project.branch_id}"
        if output_json:
            json_print({"url": url})
        else:
            info(f"Opening {url}")
            webbrowser.open(url)
