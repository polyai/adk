"""SIP Trunking command family.

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import TYPE_CHECKING, Any

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.output.json_output import json_print
from poly.sip_trunks import config as sip_trunk_config

if TYPE_CHECKING:
    from poly.sip_trunks.reconciler import ManagePlan


class SIPTrunksCommand(BaseCommand):
    """Manage account-level SIP trunks and their extensions."""

    command = "sip-trunks"
    group = BUILDER_API_GROUP

    @staticmethod
    def _add_context_arguments(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--account-id",
            "--account_id",
            dest="account_id",
            help="PolyAI account ID. Defaults to the current project's account.",
        )
        parser.add_argument(
            "--region",
            type=str,
            choices=sip_trunk_config.SIP_TRUNK_REGIONS,
            help="Account region (euw-1, uk-1, or us-1). Defaults to the current project's region.",
        )

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``sip-trunks`` subcommand tree."""
        parser = subparsers.add_parser(
            cls.command,
            parents=[parents.verbose],
            help="Manage SIP trunks and extensions.",
            description=(
                "Manage account-level SIP trunks and extension routing.\n\n"
                "Account and region default to the current ADK project.\n\n"
                "Examples:\n"
                "  adk sip-trunks manage\n"
                "  adk sip-trunks list --output\n"
                "  adk sip-trunks get <trunk-id>\n"
                "  adk sip-trunks delete <trunk-id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        actions = parser.add_subparsers(dest="sip_trunks_subcommand", required=True)
        leaf_parents = [parents.path, parents.json, parents.verbose]

        list_parser = actions.add_parser("list", parents=leaf_parents, help="List SIP trunks.")
        cls._add_context_arguments(list_parser)
        list_parser.add_argument(
            "-o",
            "--output",
            nargs="?",
            const=sip_trunk_config.PROJECT_DEFAULT_OUTPUT,
            help=(
                "Write reusable YAML to FILE, relative to the current working directory. "
                "When passed without FILE, writes "
                "sip-trunks.yaml in the project root."
            ),
        )
        list_parser.add_argument(
            "--force",
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
        cls._add_context_arguments(manage_parser)
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
        cls._add_context_arguments(get_parser)
        get_parser.add_argument("trunk_id", help="SIP trunk ID.")

        delete_parser = actions.add_parser(
            "delete", parents=leaf_parents, help="Delete a SIP trunk."
        )
        cls._add_context_arguments(delete_parser)
        delete_parser.add_argument("trunk_id", help="SIP trunk ID.")
        delete_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Delete without prompting for confirmation.",
        )

    @staticmethod
    def _resolve_context(args: Namespace) -> tuple[str, str]:
        context = sip_trunk_config.resolve_account_context(
            args.path,
            account_id=args.account_id,
            region=args.region,
        )
        return context.region, context.account_id

    @staticmethod
    def _write_export(args: Namespace, data: dict[str, Any]) -> str:
        return sip_trunk_config.write_export(
            args.path,
            data,
            output=args.output,
            force=args.force,
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
    def _build_manage_plan(cls, args: Namespace) -> "ManagePlan":
        from poly.project import AgentStudioProject

        loaded = sip_trunk_config.load_manage_config(
            args.path,
            file_path=args.file_path,
            account_id=args.account_id,
            region=args.region,
        )
        return AgentStudioProject.build_sip_trunk_plan(
            loaded.path,
            loaded.region,
            loaded.account_id,
            loaded.trunks,
            rotate_auth=getattr(args, "rotate_auth", None),
            source_digest=loaded.source_digest,
        )

    @classmethod
    def _apply_manage_plan(cls, plan: "ManagePlan") -> dict[str, Any]:
        from poly.project import AgentStudioProject

        return AgentStudioProject.apply_sip_trunk_plan(
            plan,
            prompt_auth_secret=cls._prompt_auth_secret,
        )

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
        plan = cls._build_manage_plan(args)
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
        result = cls._apply_manage_plan(plan)
        if args.json:
            json_print(result)
        else:
            from poly.output.console import print_sip_trunk_manage_result

            print_sip_trunk_manage_result(result)

    @classmethod
    def sip_trunks_list(cls, args: Namespace) -> None:
        """List account SIP trunks or export their configuration to YAML."""
        from poly.project import AgentStudioProject

        region, account_id = cls._resolve_context(args)
        if args.output == sip_trunk_config.PROJECT_DEFAULT_OUTPUT:
            args.output = sip_trunk_config.default_export_path(args.path)
        result = AgentStudioProject.export_sip_trunks(region, account_id)
        if args.output:
            output_path = cls._write_export(args, result)
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
        from poly.project import AgentStudioProject

        region, account_id = cls._resolve_context(args)
        result = AgentStudioProject.get_sip_trunk(region, account_id, args.trunk_id)
        if not args.json:
            extension_response = AgentStudioProject.list_sip_trunk_extensions(
                region, account_id, args.trunk_id
            )
            extensions = extension_response.get("extensions", [])
            if not isinstance(extensions, list):
                raise ValueError("Expected the SIP Trunking API to return an extensions list.")
            from poly.output.console import print_sip_trunk_detail

            print_sip_trunk_detail(result, extensions)
            return

        json_print(result)

    @classmethod
    def sip_trunks_delete(cls, args: Namespace) -> None:
        """Delete a SIP trunk after confirmation when required."""
        from poly.project import AgentStudioProject

        region, account_id = cls._resolve_context(args)
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
        AgentStudioProject.delete_sip_trunk(region, account_id, args.trunk_id)
        result = {"success": True, "trunk_id": args.trunk_id}
        if not args.json:
            from poly.output.console import success

            success(f"Deleted SIP trunk {args.trunk_id}.")
            return

        json_print(result)
