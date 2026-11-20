"""Account secrets commands.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print


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
            help="Manage account secrets without revealing stored values.",
            description=(
                "Manage account secrets without revealing stored values.\n"
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
                "Key-value updates preserve omitted keys; null deletes a key from an existing secret."
            ),
        )
        set_parser.add_argument("name", metavar="<secret_name>", help="Secret display name.")
        set_parser.add_argument("--description", default=None, help="Set the description.")
        set_parser.add_argument(
            "--key-value",
            action="store_true",
            help="Create a key-value secret using a JSON object.",
        )
        access = set_parser.add_mutually_exclusive_group()
        access.add_argument(
            "--project",
            dest="projects",
            action="append",
            default=None,
            metavar="ID",
            help="Replace access with these project IDs; repeat for multiple projects.",
        )
        access.add_argument(
            "--no-projects", action="store_true", help="Give no projects access to this secret."
        )
        set_parser.add_argument(
            "--grant", action="append", metavar="ID", help="Grant access to an existing secret."
        )
        set_parser.add_argument(
            "--revoke", action="append", metavar="ID", help="Revoke access to an existing secret."
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
            "names", metavar="<secret_name>", nargs="+", help="One or more secret display names."
        )
        delete_parser.add_argument("--yes", action="store_true", help="Skip confirmation.")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the selected operation."""
        getattr(cls, f"secrets_{args.secrets_subcommand}")(args)

    @classmethod
    def secrets_list(cls, args: Namespace) -> None:
        """List metadata in human or JSON form."""
        project = load_project(args.path, output_json=args.json)
        secrets = project.list_secrets(project_only=args.project)
        if args.json:
            json_print({"success": True, "secrets": secrets})
        else:
            from poly.output.console import print_secrets

            print_secrets(secrets)

    @classmethod
    def secrets_set(cls, args: Namespace) -> None:
        """Read a value safely and save the secret through the project layer."""
        project = load_project(args.path, output_json=args.json)
        existing = project.get_secret_metadata(args.name)
        if not args.json:
            from poly.output.console import info

            info(
                "Account secret changes affect every environment, including live, for projects with access."
            )
        key_value = args.key_value or bool(existing and existing["value_type"] == "key-value")
        metadata_change = (
            args.description is not None
            or args.projects is not None
            or args.no_projects
            or args.grant
            or args.revoke
        )
        needs_value = (
            existing is None or args.replace_value or not (metadata_change or args.delete_keys)
        )
        value = cls._read_value(key_value, needs_value, args.json)
        metadata = project.set_secret(
            args.name,
            value,
            description=args.description,
            key_value=args.key_value,
            projects=args.projects,
            no_projects=args.no_projects,
            grant=args.grant,
            revoke=args.revoke,
            delete_keys=args.delete_keys,
        )
        if args.json:
            json_print({"success": True, "secret": metadata})
        else:
            from poly.output.console import success

            success(f"Saved account secret '{args.name}'.")

    @staticmethod
    def _read_value(key_value: bool, required: bool, output_json: bool) -> str | dict | None:
        """Read hidden input or stdin without including a value in an error."""
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if not raw:
                if required:
                    raise ValueError("A secret value is required on stdin.")
                return None
            if not key_value:
                return raw
            try:
                value = json.loads(raw)
                if value is None:
                    raise ValueError("Key-value input must be a JSON object.")
                return value
            except ValueError:
                raise ValueError("Key-value input must be a JSON object.") from None
        if not required:
            return None
        if output_json:
            raise ValueError("Provide the secret value on stdin when using --json.")

        import getpass

        try:
            if not key_value:
                return getpass.getpass("Secret value (including live): ")

            import questionary

            from poly.output.console import info

            info("Enter keys to create or update. Omitted keys in existing secrets stay unchanged.")
            result = {}
            while True:
                key = questionary.text("Key (leave empty to finish):").ask()
                if key is None:
                    raise ValueError("Secret input cancelled.")
                if not key:
                    return result
                if key in result:
                    raise ValueError("Key names must be unique.")
                result[key] = getpass.getpass(f"Value for {key}: ")
        except (EOFError, KeyboardInterrupt):
            raise ValueError("Secret input cancelled.") from None

    @classmethod
    def secrets_delete(cls, args: Namespace) -> None:
        """Confirm deletion when interactive, then remove the named account secrets."""
        project = load_project(args.path, output_json=args.json)
        if not args.yes and not args.json:
            import questionary

            from poly.output.console import info

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
