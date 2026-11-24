"""Account secrets commands.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import TYPE_CHECKING

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print

if TYPE_CHECKING:
    from poly.project import AgentStudioProject


class SecretsCommand(BaseCommand):
    """Manage account secrets without reading stored values."""

    command = "secrets"
    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register list, set and delete operations."""
        parser = subparsers.add_parser(
            cls.command,
            parents=[parents.verbose],
            help="Manage account secrets",
            description=(
                "Manage account secrets\n"
                "Changes take effect immediately for projects with access, including live.\n\n"
                "Examples:\n"
                "  poly secrets list\n"
                "  poly secrets set <secret_name>\n"
                "  poly secrets set <secret_name> --description 'Updated description'\n"
                "  poly secrets delete <secret_name> --yes"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        actions = parser.add_subparsers(dest="secrets_subcommand", required=True)
        list_parser = actions.add_parser(
            "list",
            parents=[parents.path, parents.json],
            help="List metadata for account secrets; values are never shown.",
        )
        list_parser.add_argument(
            "--project", action="store_true", help="Only show secrets this project can use."
        )
        set_parser = actions.add_parser(
            "set",
            parents=[parents.path, parents.json],
            help="Create or update an account secret immediately, including live.",
            description=(
                "Create or update an account secret immediately for all projects with access, including live. "
                "Values come from a hidden prompt or stdin, never command arguments. "
                "Changing type requires a complete replacement value."
            ),
        )
        set_parser.add_argument(
            "name",
            nargs="?",
            metavar="<secret_name>",
            help="Secret display name. Omit to choose interactively.",
        )
        set_parser.add_argument(
            "--yes", action="store_true", help="Skip the live save confirmation."
        )
        set_parser.add_argument("--description", default=None, help="Set the description.")
        set_parser.add_argument(
            "--type",
            dest="value_type",
            choices=("single", "key-value"),
            help="Set the secret type. New secrets default to single.",
        )
        access = set_parser.add_mutually_exclusive_group()
        access.add_argument(
            "--project",
            dest="projects",
            action="append",
            default=None,
            metavar="PROJECT_ID",
            help="Replace access with these project IDs; repeat for multiple projects.",
        )
        access.add_argument(
            "--no-projects", action="store_true", help="Give no projects access to this secret."
        )
        set_parser.add_argument(
            "--grant",
            action="append",
            metavar="PROJECT_ID",
            help="Grant access to an existing secret.",
        )
        set_parser.add_argument(
            "--revoke",
            action="append",
            metavar="PROJECT_ID",
            help="Revoke access to an existing secret.",
        )
        set_parser.add_argument(
            "--replace-value",
            action="store_true",
            help="Also prompt for a value or key updates when changing metadata.",
        )
        set_parser.add_argument(
            "--delete-key",
            dest="delete_keys",
            action="append",
            metavar="KEY",
            help="Delete a key from an existing key-value secret; repeat for multiple keys.",
        )
        delete_parser = actions.add_parser(
            "delete",
            parents=[parents.path, parents.json],
            help="Delete account secrets immediately for every project with access, including live.",
        )
        delete_parser.add_argument(
            "names",
            metavar="<secret_name>",
            nargs="*",
            help="Secret display names. Omit to select interactively.",
        )
        delete_parser.add_argument("--yes", action="store_true", help="Skip confirmation.")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the selected operation."""
        getattr(cls, f"secrets_{args.secrets_subcommand}")(args)

    @staticmethod
    def _project_names(project: "AgentStudioProject") -> dict[str, str]:
        from requests import HTTPError

        try:
            return project.get_account_projects()
        except HTTPError as error:
            if error.response is None or error.response.status_code != 403:
                raise
            from poly.output.console import info

            info("Project names are unavailable with this API key. Showing stored project IDs.")
            return {}

    @classmethod
    def secrets_list(cls, args: Namespace) -> None:
        """List metadata in human or JSON form."""
        project = load_project(args.path, output_json=args.json)
        secrets = project.list_secrets(project_only=args.project)
        if args.json:
            json_print({"success": True, "secrets": secrets})
        else:
            from poly.output.console import print_secrets

            projects = (
                cls._project_names(project) if any(s.get("access_config") for s in secrets) else {}
            )
            print_secrets(secrets, projects)

    @staticmethod
    def _edit_options(args: Namespace) -> dict:
        return {
            "description": args.description,
            "value_type": args.value_type,
            "projects": args.projects,
            "no_projects": args.no_projects,
            "grant": args.grant,
            "revoke": args.revoke,
            "delete_keys": args.delete_keys,
        }

    @classmethod
    def secrets_set(cls, args: Namespace) -> None:
        """Read a value safely and save the secret through the project layer."""
        project = load_project(args.path, output_json=args.json)
        interactive = sys.stdin.isatty() and not args.json
        if not args.name and not interactive:
            raise ValueError("Provide a secret name when running noninteractively.")
        if not interactive and not (args.yes or args.json):
            raise ValueError("Use --yes or --json to confirm a noninteractive save to live.")
        if args.name is not None:
            existing = project.get_secret_metadata(args.name)
        else:
            from poly.cli_commands.secrets_prompts import pick_secret

            records = project.list_secrets()
            args.name = pick_secret(records)
            existing = next((r for r in records if r["display_name"] == args.name), None)

        account_projects = cls._project_names(project) if interactive else None
        options = cls._edit_options(args)
        update = project.prepare_secret_update(
            args.name, existing, account_projects=account_projects, **options
        )
        if interactive:
            from poly.cli_commands import secrets_prompts
            from poly.output.console import info

            if not secrets_prompts.prompt_fields(
                args, existing, account_projects, project.project_id
            ):
                info("No changes selected.")
                return
            selected_options = cls._edit_options(args)
            if selected_options != options:
                update = project.prepare_secret_update(
                    args.name, existing, account_projects=account_projects, **selected_options
                )
        needs_value = (
            existing is None
            or update.type_changed
            or args.replace_value
            or not (update.access_requested or args.description is not None or args.delete_keys)
        )
        if interactive:
            import questionary

            from poly.output.console import print_secret_summary

            value = secrets_prompts.prompt_value(update) if needs_value else None
            if value is None and not (
                update.delete_keys or update.access_requested or args.description is not None
            ):
                info("No changes selected.")
                return
            print_secret_summary(update, value, account_projects)
            if (
                not args.yes
                and not questionary.confirm(
                    "Save to every environment, including live?", default=False
                ).ask()
            ):
                info("Save cancelled.")
                return
        else:
            value = cls._read_stdin(update.value_type, needs_value)
        metadata = project.save_secret_update(update, value)
        if args.json:
            json_print({"success": True, "secret": metadata})
        else:
            from poly.output.console import success

            success(f"Saved account secret '{args.name}'.")

    @staticmethod
    def _read_stdin(value_type: str, required: bool) -> str | dict | None:
        """Read scripted input without exposing it in parse errors."""
        if sys.stdin.isatty():
            if required:
                raise ValueError("Provide the secret value on stdin when using --json.")
            return None
        raw = sys.stdin.read()
        if not raw:
            if required:
                raise ValueError("A secret value is required on stdin.")
            return None
        if value_type == "single":
            return raw
        try:
            value = json.loads(raw)
        except ValueError:
            raise ValueError("Key-value input must be a JSON object.") from None
        if not isinstance(value, dict):
            raise ValueError("Key-value input must be a JSON object.")
        return value

    @classmethod
    def secrets_delete(cls, args: Namespace) -> None:
        """Confirm deletion when interactive, then remove the named account secrets."""
        project = load_project(args.path, output_json=args.json)
        if not args.names:
            if args.json or not sys.stdin.isatty():
                raise ValueError("Provide secret names when running noninteractively.")
            from poly.cli_commands.secrets_prompts import pick_secrets_to_delete

            args.names = pick_secrets_to_delete(project.list_secrets())
            if not args.names:
                return
        if not args.yes and not args.json:
            import questionary

            from poly.output.console import info

            if not sys.stdin.isatty():
                raise ValueError("Use --yes or --json to confirm a noninteractive deletion.")
            if not questionary.confirm(
                "Delete these account secrets for every project with access, including live? "
                + ", ".join(args.names),
                default=False,
            ).ask():
                info("Deletion cancelled.")
                return
        deleted = project.delete_secrets(args.names)
        if args.json:
            json_print({"success": True, "deleted": deleted})
        else:
            from poly.output.console import success

            success(f"Deleted {len(deleted)} account secret(s).")
