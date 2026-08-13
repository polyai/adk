"""SIP Trunking command family.

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from getpass import getpass
from typing import Any

from poly.cli_commands.base import BaseCommand, Parents
from poly.handlers.sip_trunking_api import SIPTrunkingAPIHandler
from poly.output.json_output import json_print
from poly.sip_trunks import config as sip_trunk_config
from poly.sip_trunks.reconciler import (
    ManagePlan,
    apply_manage_plan,
    build_manage_plan,
    export_config,
)


class SIPTrunksCommand(BaseCommand):
    """Manage account-level SIP trunks and their extensions."""

    command = "sip-trunks"

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
            type=sip_trunk_config.normalize_sip_trunk_region,
            choices=sip_trunk_config.SIP_TRUNK_REGIONS,
            help="Account region (eu, uk, or us). Defaults to the current project's region.",
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
            const=sip_trunk_config.ACCOUNT_DEFAULT_OUTPUT,
            help=(
                "Write reusable YAML to FILE. When passed without FILE, writes "
                "sip-trunks.yaml in the account directory."
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
            "-f",
            "--file",
            dest="file_path",
            help=(
                "Configuration file. Defaults to the nearest sip-trunks.yaml "
                "found from --path towards the filesystem root."
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
            "-y",
            "--yes",
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
            "-y",
            "--yes",
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
    def _write_export(args: Namespace, account_id: str, data: dict[str, Any]) -> str:
        return sip_trunk_config.write_export(
            args.path,
            account_id,
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
    def _build_manage_plan(cls, args: Namespace) -> ManagePlan:
        loaded = sip_trunk_config.load_manage_config(
            args.path,
            file_path=args.file_path,
            account_id=args.account_id,
            region=args.region,
        )
        return build_manage_plan(
            loaded.path,
            loaded.region,
            loaded.account_id,
            loaded.trunks,
            rotate_auth=getattr(args, "rotate_auth", None),
            source_digest=loaded.source_digest,
        )

    @classmethod
    def _apply_manage_plan(cls, plan: ManagePlan) -> dict[str, Any]:
        return apply_manage_plan(
            plan,
            prompt_auth_secret=cls._prompt_auth_secret,
            persist_trunk_response=sip_trunk_config.persist_trunk_response,
        )

    @staticmethod
    def _print_manage_diff(changes: list[dict[str, str]]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        table = Table(title="SIP trunk changes", box=box.SIMPLE, header_style="bold")
        table.add_column("Action")
        table.add_column("Resource")
        table.add_column("Diff")
        for change in changes:
            table.add_row(change["action"], change["resource"], change["diff"])
        console.print(table)

    @staticmethod
    def _print_result(result: dict[str, Any], *, output_json: bool) -> None:
        if output_json:
            json_print(result)
            return
        from poly.output.console import console

        console.print_json(data=result)

    @staticmethod
    def _print_manage_result(result: dict[str, Any], *, output_json: bool) -> None:
        if output_json:
            json_print(result)
            return
        from rich import box
        from rich.table import Table

        from poly.output.console import console, info

        changed_trunks = [trunk for trunk in result["trunks"] if trunk["status"] != "unchanged"]
        if not changed_trunks:
            info("Nothing changed.")
            return

        info(f"Managed SIP trunks from {result['config_file']}")
        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("Key")
        table.add_column("Status")
        table.add_column("Trunk ID")
        table.add_column("Hostname")
        table.add_column("Extensions")
        table.add_column("Changes")
        for trunk in changed_trunks:
            extension_changes = (
                trunk["extensions_created"]
                + trunk["extensions_updated"]
                + trunk.get("extensions_deleted", 0)
            )
            table.add_row(
                trunk["key"],
                trunk["status"],
                trunk["id"] or "—",
                trunk["hostname"] or "—",
                str(trunk["extensions_total"]),
                str(extension_changes),
            )
        console.print(table)

    @staticmethod
    def _auth_summary(inbound: dict[str, Any]) -> str:
        sip_auth = inbound.get("sip_auth") or {}
        token_auth = inbound.get("sip_token_auth") or {}
        if sip_auth.get("enabled"):
            username = sip_auth.get("username")
            return f"digest ({username})" if username else "digest"
        if token_auth.get("enabled"):
            return "token"
        return "none"

    @classmethod
    def _print_list_table(cls, config: dict[str, Any]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        table = Table(box=box.SIMPLE, header_style="bold")
        table.add_column("Name")
        table.add_column("Trunk ID")
        table.add_column("Hostname")
        table.add_column("Encrypted")
        table.add_column("Auth")
        table.add_column("Extensions", justify="right")
        for trunk in config["sip_trunks"]:
            auth = trunk.get("inbound_auth") or {"type": "none"}
            auth_summary = str(auth.get("type", "none"))
            if auth_summary == "digest" and auth.get("username"):
                auth_summary += f" ({auth['username']})"
            table.add_row(
                trunk.get("name") or "—",
                trunk.get("id") or "—",
                trunk.get("hostname") or "—",
                "yes" if trunk.get("encrypted") else "no",
                auth_summary,
                str(len(trunk.get("extensions") or [])),
            )
        console.print(table)

    @classmethod
    def _print_get_table(cls, trunk: dict[str, Any], extensions: list[dict[str, Any]]) -> None:
        from rich import box
        from rich.table import Table

        from poly.output.console import console

        inbound = trunk.get("inbound") or {}
        details = Table(box=box.SIMPLE, show_header=False)
        details.add_column("Field", style="bold")
        details.add_column("Value")
        details.add_row("Name", str(trunk.get("name") or "—"))
        details.add_row("Trunk ID", str(trunk.get("id") or "—"))
        details.add_row("Hostname", str(inbound.get("hostname") or "—"))
        details.add_row("Encrypted", "yes" if trunk.get("encrypted") else "no")
        details.add_row("Authentication", cls._auth_summary(inbound))
        details.add_row("SIP CIDRs", ", ".join(trunk.get("sip_cidr") or []) or "—")
        details.add_row("RTP CIDRs", ", ".join(trunk.get("rtp_cidr") or []) or "—")
        details.add_row("Created", str(trunk.get("created_at") or "—"))
        details.add_row("Updated", str(trunk.get("updated_at") or "—"))
        console.print(details)

        extension_table = Table(
            title="Extensions", box=box.SIMPLE, header_style="bold", title_justify="left"
        )
        extension_table.add_column("Extension")
        extension_table.add_column("Agent ID")
        extension_table.add_column("Environment")
        extension_table.add_column("Variant")
        for extension in extensions:
            agent = extension.get("agent") or {}
            extension_table.add_row(
                str(extension.get("extension") or "—"),
                str(agent.get("agent_id") or "—"),
                str(agent.get("client_env") or "—"),
                str(agent.get("variant_id") or "—"),
            )
        console.print(extension_table)

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to a SIP trunk API operation."""
        action = args.sip_trunks_subcommand
        if action == "manage":
            plan = cls._build_manage_plan(args)
            changes = [change.as_dict() for change in plan.changes]
            if not changes:
                if args.json:
                    json_print({"success": True, "changed": False, "trunks": []})
                else:
                    from poly.output.console import info

                    info("Nothing changed.")
                return
            if args.json and not args.yes:
                raise ValueError("sip-trunks manage --json requires --yes when changes exist.")
            if not args.json:
                cls._print_manage_diff(changes)
            if not args.yes:
                import questionary

                confirmed = questionary.confirm(
                    "Apply these SIP trunk changes?", default=False, auto_enter=False
                ).ask()
                if not confirmed:
                    from poly.output.console import info

                    info("Aborted. No changes were applied.")
                    return
            result = cls._apply_manage_plan(plan)
            cls._print_manage_result(result, output_json=args.json)
            return

        if action == "delete" and args.json and not args.yes:
            raise ValueError("sip-trunks delete --json requires --yes.")

        region, account_id = cls._resolve_context(args)
        if action == "list":
            result = export_config(region, account_id)
            if args.output:
                output_path = cls._write_export(args, account_id, result)
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
                cls._print_list_table(result)
            return
        if action == "get":
            result = SIPTrunkingAPIHandler.get_trunk(region, account_id, args.trunk_id)
            if not args.json:
                extension_response = SIPTrunkingAPIHandler.list_extensions(
                    region, account_id, args.trunk_id
                )
                extensions = extension_response.get("extensions", [])
                if not isinstance(extensions, list):
                    raise ValueError("Expected the SIP Trunking API to return an extensions list.")
                cls._print_get_table(result, extensions)
                return
        else:
            if not args.yes:
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
            SIPTrunkingAPIHandler.delete_trunk(region, account_id, args.trunk_id)
            result = {"success": True, "trunk_id": args.trunk_id}
            if not args.json:
                from poly.output.console import success

                success(f"Deleted SIP trunk {args.trunk_id}.")
                return

        cls._print_result(result, output_json=args.json)
