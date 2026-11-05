"""SIP Trunking command family.

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print
from poly.sip_trunks.config import PROJECT_DEFAULT_OUTPUT


class SIPTrunksCommand(BaseCommand):
    """Manage account-level SIP trunks and their extensions."""

    command = "sip-trunks"
    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``sip-trunks`` subcommand tree."""
        parser = subparsers.add_parser(
            cls.command,
            parents=[parents.verbose],
            help="Manage SIP trunks and extensions.",
            description=(
                "Manage account-level SIP trunks and extension routing.\n\n"
                "Account and region are read from the selected ADK project.\n\n"
                "Examples:\n"
                "  poly sip-trunks manage\n"
                "  poly sip-trunks list --output\n"
                "  poly sip-trunks get <trunk-id>\n"
                "  poly sip-trunks delete <trunk-id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        actions = parser.add_subparsers(dest="sip_trunks_subcommand", required=True)
        leaf_parents = [parents.path, parents.json, parents.verbose]

        list_parser = actions.add_parser("list", parents=leaf_parents, help="List SIP trunks.")
        list_parser.add_argument(
            "-o",
            "--output",
            nargs="?",
            const=PROJECT_DEFAULT_OUTPUT,
            help=(
                "Write reusable YAML to FILE, relative to the current working directory. "
                "When passed without FILE, writes "
                "sip-trunks.yaml in the project root."
            ),
        )
        list_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Overwrite an existing output file.",
        )

        manage_parser = actions.add_parser(
            "manage",
            parents=leaf_parents,
            help="Create or update SIP trunks from an account-level YAML file.",
            description=(
                "Create or update SIP trunks declared in sip-trunks.yaml.\n"
                "Resources omitted from the file are left unchanged."
            ),
        )
        manage_parser.add_argument(
            "--file",
            dest="file_path",
            help=(
                "Configuration file, relative to the current working directory. "
                "Defaults to sip-trunks.yaml in the project root "
                "or its immediate parent, in that order."
            ),
        )
        manage_parser.add_argument(
            "--rotate-auth",
            metavar="TRUNK_ID",
            help=(
                "Prompt for and rotate credentials for this YAML-declared trunk. "
                "Normal manage operations never resend existing credentials."
            ),
        )
        manage_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Apply the displayed changes without prompting for confirmation.",
        )

        get_parser = actions.add_parser("get", parents=leaf_parents, help="Get a SIP trunk.")
        get_parser.add_argument("trunk_id", help="SIP trunk ID.")

        delete_parser = actions.add_parser(
            "delete", parents=leaf_parents, help="Delete a SIP trunk."
        )
        delete_parser.add_argument("trunk_id", help="SIP trunk ID.")
        delete_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Delete without prompting for confirmation.",
        )

    @staticmethod
    def _prompt_auth_secret(
        local_name: str,
        current: dict[str, Any] | None,
        desired: dict[str, Any],
        *,
        rotate: bool,
    ) -> bool:
        """Prompt and add a secret only when the planned operation requires one."""
        from getpass import getpass

        desired_inbound = desired.get("inbound")
        if not desired_inbound:
            if rotate:
                raise ValueError(
                    f"SIP trunk '{local_name}' must declare digest or token authentication "
                    "to rotate credentials."
                )
            return False

        current_inbound = (current or {}).get("inbound") or {}
        if "sip_auth" in desired_inbound:
            desired_auth = desired_inbound["sip_auth"]
            current_auth = current_inbound.get("sip_auth") or {}
            required = (
                current is None
                or rotate
                or not current_auth.get("enabled")
                or current_auth.get("username") != desired_auth.get("username")
            )
            if not required:
                return False
            secret = getpass(f"SIP password for {local_name}: ")
            if not secret:
                raise ValueError(f"A SIP password is required for trunk '{local_name}'.")
            desired_auth["password"] = secret
            return True

        if "sip_token_auth" in desired_inbound:
            current_auth = current_inbound.get("sip_token_auth") or {}
            required = current is None or rotate or not current_auth.get("enabled")
            if not required:
                return False
            secret = getpass(f"SIP token for {local_name}: ")
            if not secret:
                raise ValueError(f"A SIP token is required for trunk '{local_name}'.")
            desired_inbound["sip_token_auth"]["token"] = secret
            return True

        if rotate:
            raise ValueError(
                f"SIP trunk '{local_name}' must declare digest or token authentication "
                "to rotate credentials."
            )
        return False

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching SIP trunk action."""
        action = args.sip_trunks_subcommand
        if action == "manage":
            cls.sip_trunks_manage(args)
        elif action == "list":
            cls.sip_trunks_list(args)
        elif action == "get":
            cls.sip_trunks_get(args)
        elif action == "delete":
            cls.sip_trunks_delete(args)

    @classmethod
    def sip_trunks_manage(cls, args: Namespace) -> None:
        """Preview and apply the SIP trunks declared in a YAML file."""
        project = load_project(args.path, output_json=args.json)
        plan = project.build_sip_trunk_plan(
            file_path=args.file_path, rotate_auth=getattr(args, "rotate_auth", None)
        )
        changes = [change.as_dict() for change in plan.changes]
        if not changes:
            if args.json:
                json_print({"success": True, "changed": False, "trunks": []})
            else:
                from poly.output.console import info

                info("Nothing changed.")
            return
        if not args.json:
            from poly.output.console import print_sip_trunk_changes

            print_sip_trunk_changes(changes)
        if not args.json and not args.force:
            import questionary

            confirmed = questionary.confirm(
                "Apply these SIP trunk changes?", default=False, auto_enter=False
            ).ask()
            if not confirmed:
                from poly.output.console import info

                info("Aborted. No changes were applied.")
                return
        result = project.apply_sip_trunk_plan(plan, prompt_auth_secret=cls._prompt_auth_secret)
        if args.json:
            json_print(result)
        else:
            from poly.output.console import print_sip_trunk_manage_result

            print_sip_trunk_manage_result(result)

    @classmethod
    def sip_trunks_list(cls, args: Namespace) -> None:
        """List account SIP trunks or export their configuration to YAML."""
        project = load_project(args.path, output_json=args.json)
        result = project.export_sip_trunks()
        if args.output:
            output_path = project.write_sip_trunk_export(
                result, output=args.output, force=args.force
            )
            if args.json:
                json_print(
                    {
                        "success": True,
                        "output_path": output_path,
                        "trunk_count": len(result["sip_trunks"]),
                    }
                )
            else:
                from poly.output.console import success

                success(f"Wrote {len(result['sip_trunks'])} SIP trunk(s) to {output_path}")
        elif args.json:
            json_print(result)
        else:
            from poly.output.console import print_sip_trunks

            print_sip_trunks(result)

    @classmethod
    def sip_trunks_get(cls, args: Namespace) -> None:
        """Show a SIP trunk and its extension routing."""
        project = load_project(args.path, output_json=args.json)
        result = project.get_sip_trunk(args.trunk_id)
        if not args.json:
            extension_response = project.list_sip_trunk_extensions(args.trunk_id)
            extensions = extension_response.get("extensions", [])
            from poly.output.console import print_sip_trunk_detail

            print_sip_trunk_detail(result, extensions)
            return

        json_print(result)

    @classmethod
    def sip_trunks_delete(cls, args: Namespace) -> None:
        """Delete a SIP trunk after confirmation when required."""
        project = load_project(args.path, output_json=args.json)
        if not args.json and not args.force:
            import questionary

            confirmed = questionary.confirm(
                f"Delete SIP trunk {args.trunk_id}?",
                default=False,
                auto_enter=False,
            ).ask()
            if not confirmed:
                from poly.output.console import info

                info("Aborted. SIP trunk was not deleted.")
                return
        project.delete_sip_trunk(args.trunk_id)
        result = {"success": True, "trunk_id": args.trunk_id}
        if not args.json:
            from poly.output.console import success

            success(f"Deleted SIP trunk {args.trunk_id}.")
            return

        json_print(result)
