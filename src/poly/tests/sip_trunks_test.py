"""Tests for the SIP Trunking API client and CLI commands.

Copyright PolyAI Limited
"""

import os
import unittest
from argparse import Namespace
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.sip_trunks import SIPTrunksCommand
from poly.handlers.interface import AgentStudioInterface
from poly.project import AgentStudioProject
from poly.sip_trunks.config import (
    default_export_path,
    find_manage_file,
    load_manage_config,
    persist_trunk_response,
    resolve_account_context,
    validate_sip_trunk_region,
)
from poly.sip_trunks.reconciler import (
    PlanChange,
    export_config,
    managed_trunk_data,
    trunk_patch,
)


class SIPTrunkingInterfaceTest(unittest.TestCase):
    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_create_trunk_uses_account_endpoint(self, make_request):
        body = {
            "name": "carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
        }
        make_request.return_value = {"id": "tr-123"}

        result = AgentStudioInterface.create_sip_trunk("euw-1", "acct-123", body)

        self.assertEqual(result, {"id": "tr-123"})
        make_request.assert_called_once_with(
            "euw-1",
            "/v1/accounts/acct-123/telephony/sip-trunks",
            "POST",
            data=body,
        )

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_extension_is_url_encoded(self, make_request):
        AgentStudioInterface.get_sip_trunk_extension("uk-1", "acct-123", "tr-123", "+44/100")

        make_request.assert_called_once_with(
            "uk-1",
            "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions/%2B44%2F100",
        )

    @patch("poly.handlers.platform_api.PlatformAPIHandler.make_request")
    def test_delete_extension_uses_delete(self, make_request):
        AgentStudioInterface.delete_sip_trunk_extension("us-1", "acct-123", "tr-123", "1000")

        make_request.assert_called_once_with(
            "us-1",
            "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions/1000",
            "DELETE",
        )


class SIPTrunksCommandTest(unittest.TestCase):
    @staticmethod
    def _write_project_config(path, account_id="acct-123", region="uk-1"):
        path.mkdir(parents=True, exist_ok=True)
        (path / "project.yaml").write_text(
            f"project_id: {path.name}\naccount_id: {account_id}\nregion: {region}\n",
            encoding="utf-8",
        )
        return path

    def _parser(self):
        cli = AgentStudioCLI()
        cli.register_commands()
        return cli._create_parser()

    def test_parser_registers_yaml_export_options(self):
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "list",
                "--account-id",
                "acct-123",
                "--region",
                "euw-1",
                "--output",
                "export.yaml",
                "--force",
            ]
        )

        self.assertEqual(args.command, "sip-trunks")
        self.assertEqual(args.sip_trunks_subcommand, "list")
        self.assertEqual(args.output, "export.yaml")
        self.assertTrue(args.force)

    def test_parser_accepts_canonical_regions_for_all_actions(self):
        parser = self._parser()
        for action in (["list"], ["manage"], ["get", "tr-123"], ["delete", "tr-123"]):
            for region in ("us-1", "euw-1", "uk-1"):
                with self.subTest(action=action[0], region=region):
                    args = parser.parse_args(["sip-trunks", *action, "--region", region])
                    self.assertEqual(args.region, region)

    def test_parser_rejects_noncanonical_and_unsupported_regions(self):
        parser = self._parser()
        for action in (["list"], ["manage"], ["get", "tr-123"], ["delete", "tr-123"]):
            for region in ("eu", "uk", "us", "EUW-1", "UK-1", "US-1", "studio", "staging", "dev"):
                with self.subTest(action=action[0], region=region), patch("sys.stderr"):
                    with self.assertRaises(SystemExit) as error:
                        parser.parse_args(["sip-trunks", *action, "--region", region])
                    self.assertEqual(error.exception.code, 2)

    def test_sip_region_validation_rejects_noncanonical_and_unsupported_regions(self):
        regions = (
            "eu", "uk", "us", "EUW-1", "UK-1", "US-1", "studio", "staging", "dev", "unknown"
        )
        for region in regions:
            with self.subTest(region=region):
                with self.assertRaisesRegex(ValueError, "Unsupported SIP Trunking region"):
                    validate_sip_trunk_region(region)

    def test_parser_accepts_legacy_account_id_spelling(self):
        args = self._parser().parse_args(
            ["sip-trunks", "list", "--account_id", "acct-123", "--region", "uk-1"]
        )

        self.assertEqual(args.account_id, "acct-123")

    def test_parser_registers_explicit_auth_rotation(self):
        args = self._parser().parse_args(["sip-trunks", "manage", "--rotate-auth", "tr-123"])

        self.assertEqual(args.rotate_auth, "tr-123")

    def test_parser_registers_force_for_non_interactive_manage(self):
        for flag in ("--force", "-f"):
            with self.subTest(flag=flag):
                args = self._parser().parse_args(
                    ["sip-trunks", "manage", "--file", "custom.yaml", flag]
                )
                self.assertTrue(args.force)
                self.assertEqual(args.file_path, "custom.yaml")

    def test_parser_registers_force_for_non_interactive_delete(self):
        for flag in ("--force", "-f"):
            with self.subTest(flag=flag):
                args = self._parser().parse_args(["sip-trunks", "delete", "tr-123", flag])
                self.assertTrue(args.force)

    @patch.object(SIPTrunksCommand, "_apply_manage_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(SIPTrunksCommand, "_build_manage_plan")
    @patch("questionary.confirm")
    def test_manage_displays_diff_and_aborts_when_not_confirmed(
        self, confirm, build_plan, print_diff, apply_plan
    ):
        changes = [{"action": "update", "resource": "trunk tr-123", "diff": "name"}]
        plan = MagicMock(changes=(PlanChange(**changes[0]),))
        build_plan.return_value = plan
        confirm.return_value.ask.return_value = False
        args = self._parser().parse_args(["sip-trunks", "manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        confirm.assert_called_once_with(
            "Apply these SIP trunk changes?", default=False, auto_enter=False
        )
        apply_plan.assert_not_called()

    @patch("poly.output.console.print_sip_trunk_manage_result")
    @patch.object(SIPTrunksCommand, "_apply_manage_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(SIPTrunksCommand, "_build_manage_plan")
    @patch("questionary.confirm")
    def test_manage_applies_changes_after_confirmation(
        self, confirm, build_plan, print_diff, apply_plan, print_result
    ):
        changes = [{"action": "create", "resource": "trunk Example", "diff": "+ trunk"}]
        result = {"success": True, "trunks": []}
        plan = MagicMock(changes=(PlanChange(**changes[0]),))
        build_plan.return_value = plan
        confirm.return_value.ask.return_value = True
        apply_plan.return_value = result
        args = self._parser().parse_args(["sip-trunks", "manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        apply_plan.assert_called_once_with(plan)
        print_result.assert_called_once_with(result)

    @patch("poly.output.console.print_sip_trunk_manage_result")
    @patch.object(SIPTrunksCommand, "_apply_manage_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(SIPTrunksCommand, "_build_manage_plan")
    @patch("questionary.confirm")
    def test_manage_force_applies_without_confirmation(
        self, confirm, build_plan, print_diff, apply_plan, print_result
    ):
        plan = MagicMock(changes=(PlanChange("create", "trunk Example", "+ trunk"),))
        result = {"success": True, "trunks": []}
        build_plan.return_value = plan
        apply_plan.return_value = result
        args = self._parser().parse_args(["sip-trunks", "manage", "--force"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        print_diff.assert_called_once_with([change.as_dict() for change in plan.changes])
        apply_plan.assert_called_once_with(plan)
        print_result.assert_called_once_with(result)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(SIPTrunksCommand, "_apply_manage_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(SIPTrunksCommand, "_build_manage_plan")
    @patch("questionary.confirm")
    def test_manage_json_applies_without_confirmation(
        self, confirm, build_plan, print_diff, apply_plan, json_print
    ):
        plan = MagicMock(changes=(PlanChange("create", "trunk Example", "+ trunk"),))
        result = {"success": True, "trunks": []}
        build_plan.return_value = plan
        apply_plan.return_value = result
        args = self._parser().parse_args(["sip-trunks", "manage", "--json"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        print_diff.assert_not_called()
        apply_plan.assert_called_once_with(plan)
        json_print.assert_called_once_with(result)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(SIPTrunksCommand, "_apply_manage_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(SIPTrunksCommand, "_build_manage_plan")
    @patch("questionary.confirm")
    def test_manage_json_with_no_changes_does_not_apply(
        self, confirm, build_plan, print_diff, apply_plan, json_print
    ):
        build_plan.return_value = MagicMock(changes=())
        args = self._parser().parse_args(["sip-trunks", "manage", "--json"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        print_diff.assert_not_called()
        apply_plan.assert_not_called()
        json_print.assert_called_once_with({"success": True, "changed": False, "trunks": []})

    @patch("poly.output.console.print_sip_trunks")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_list_displays_table_by_default(self, export_config, print_list_table):
        export = {"account_id": "acct-123", "sip_trunks": []}
        export_config.return_value = export
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "list",
                "--account-id",
                "acct-123",
                "--region",
                "uk-1",
            ]
        )

        SIPTrunksCommand.run(args)

        export_config.assert_called_once_with("uk-1", "acct-123")
        print_list_table.assert_called_once_with(export)

    @patch("poly.output.console.print_sip_trunk_detail")
    @patch.object(AgentStudioProject, "list_sip_trunk_extensions")
    @patch.object(AgentStudioProject, "get_sip_trunk")
    def test_get_displays_details_and_extensions_table(
        self, get_trunk, list_extensions, print_get_table
    ):
        trunk = {"id": "tr-123", "name": "Primary"}
        extensions = [{"extension": "1000", "agent": {"agent_id": "agent-one"}}]
        get_trunk.return_value = trunk
        list_extensions.return_value = {"extensions": extensions}
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "get",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "uk-1",
            ]
        )

        SIPTrunksCommand.run(args)

        get_trunk.assert_called_once_with("uk-1", "acct-123", "tr-123")
        list_extensions.assert_called_once_with("uk-1", "acct-123", "tr-123")
        print_get_table.assert_called_once_with(trunk, extensions)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    def test_delete_returns_machine_readable_success(self, delete_trunk, print_result):
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "delete",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "us-1",
                "--force",
                "--json",
            ]
        )

        SIPTrunksCommand.run(args)

        delete_trunk.assert_called_once_with("us-1", "acct-123", "tr-123")
        print_result.assert_called_once_with(
            {"success": True, "trunk_id": "tr-123"}
        )

    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_aborts_when_not_confirmed(self, confirm, delete_trunk):
        confirm.return_value.ask.return_value = False
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "delete",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "uk-1",
            ]
        )

        SIPTrunksCommand.run(args)

        confirm.assert_called_once_with("Delete SIP trunk tr-123?", default=False, auto_enter=False)
        delete_trunk.assert_not_called()

    @patch("poly.output.console.success")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_confirms_and_prints_human_success(self, confirm, delete_trunk, success):
        confirm.return_value.ask.return_value = True
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "delete",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "uk-1",
            ]
        )

        SIPTrunksCommand.run(args)

        delete_trunk.assert_called_once_with("uk-1", "acct-123", "tr-123")
        success.assert_called_once_with("Deleted SIP trunk tr-123.")

    @patch("poly.output.console.success")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_force_deletes_without_confirmation(self, confirm, delete_trunk, success):
        args = self._parser().parse_args(
            [
                "sip-trunks", "delete", "tr-123", "--account-id", "acct-123",
                "--region", "uk-1", "-f",
            ]
        )

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        delete_trunk.assert_called_once_with("uk-1", "acct-123", "tr-123")
        success.assert_called_once_with("Deleted SIP trunk tr-123.")

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_json_deletes_without_confirmation(self, confirm, delete_trunk, json_print):
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "delete",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "uk-1",
                "--json",
            ]
        )

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        delete_trunk.assert_called_once_with("uk-1", "acct-123", "tr-123")
        json_print.assert_called_once_with({"success": True, "trunk_id": "tr-123"})

    @patch("poly.cli_commands.shared.read_project_config")
    def test_context_defaults_to_current_project(self, read_project_config):
        read_project_config.return_value = MagicMock(
            account_id="acct-123", region="euw-1", root_path="/account/project"
        )
        args = Namespace(account_id=None, region=None, path="relative-project", json=False)

        result = SIPTrunksCommand._resolve_context(args)

        self.assertEqual(result, ("euw-1", "acct-123"))
        read_project_config.assert_called_once_with(os.path.abspath(args.path))

    def test_current_project_context_ignores_sibling_accounts_and_regions(self):
        with TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "unrelated-folder-name"
            project_dir = self._write_project_config(parent / "current-project")
            self._write_project_config(parent / "same-account", region="us-1")
            self._write_project_config(
                parent / "other-account", account_id="acct-other", region="euw-1"
            )
            (parent / "sip-trunks.yaml").write_text("[]\n", encoding="utf-8")

            context = resolve_account_context(str(project_dir))
            loaded = load_manage_config(str(project_dir))

        self.assertEqual((context.region, context.account_id), ("uk-1", "acct-123"))
        self.assertEqual((loaded.region, loaded.account_id), ("uk-1", "acct-123"))

    def test_context_does_not_infer_account_from_directory_or_child_projects(self):
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "acct-123"
            self._write_project_config(account_dir / "child-project")

            for overrides in ({}, {"account_id": "acct-123"}, {"region": "uk-1"}):
                with self.subTest(overrides=overrides):
                    with self.assertRaisesRegex(ValueError, "pass both --account-id and --region"):
                        resolve_account_context(str(account_dir), **overrides)

            context = resolve_account_context(
                str(account_dir), account_id="explicit-account", region="us-1"
            )

        self.assertEqual((context.region, context.account_id), ("us-1", "explicit-account"))

    def test_explicit_scope_overrides_only_the_supplied_project_fields(self):
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            for overrides, expected in (
                ({"account_id": "acct-other"}, ("uk-1", "acct-other")),
                ({"region": "us-1"}, ("us-1", "acct-123")),
                ({"account_id": "acct-other", "region": "euw-1"}, ("euw-1", "acct-other")),
            ):
                with self.subTest(overrides=overrides):
                    context = resolve_account_context(str(project_dir), **overrides)
                    self.assertEqual((context.region, context.account_id), expected)

    def test_noncanonical_project_region_is_rejected(self):
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project", region="uk")

            with self.assertRaisesRegex(ValueError, "Unsupported SIP Trunking region: uk$"):
                resolve_account_context(str(project_dir))

    def test_explicit_file_from_another_account_keeps_current_project_context(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            current_project_dir = self._write_project_config(
                root / "account-b" / "project-b", account_id="account-b", region="us-1"
            )
            account_a = root / "account-a"
            self._write_project_config(
                account_a / "project-a", account_id="account-a", region="uk-1"
            )
            config_path = account_a / "sip-trunks.yaml"
            config_path.write_text("[]\n", encoding="utf-8")

            loaded = load_manage_config(str(current_project_dir), file_path=str(config_path))

        self.assertEqual(loaded.path, str(config_path))
        self.assertEqual(loaded.account_id, "account-b")
        self.assertEqual(loaded.region, "us-1")

    def test_explicit_file_is_relative_to_cwd_and_bypasses_discovery(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            project_dir = self._write_project_config(root / "project")
            (project_dir / "sip-trunks.yaml").write_text("[]\n", encoding="utf-8")
            selected = root / "selected.yaml"
            selected.write_text(
                "- name: Selected carrier\n  default_route: null\n  outbound: null\n", encoding="utf-8"
            )

            with chdir(root):
                loaded = load_manage_config(str(project_dir), file_path="selected.yaml")

        self.assertEqual(loaded.path, str(selected))
        self.assertEqual(loaded.trunks, [{"outbound": None, "name": "Selected carrier", "default_route": None}])
        self.assertEqual((loaded.region, loaded.account_id), ("uk-1", "acct-123"))

    def test_standalone_manage_requires_explicit_file_and_context(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sip-trunks.yaml"
            config_path.write_text("[]\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "pass --file"):
                load_manage_config(temp_dir, account_id="acct-123", region="uk-1")
            with self.assertRaisesRegex(ValueError, "pass both --account-id and --region"):
                load_manage_config(temp_dir, file_path=str(config_path))

            loaded = load_manage_config(
                temp_dir, file_path=str(config_path), account_id="acct-123", region="uk-1"
            )

        self.assertEqual(loaded.path, str(config_path))
        self.assertEqual((loaded.region, loaded.account_id), ("uk-1", "acct-123"))

    def test_default_export_uses_project_root_from_nested_directory(self):
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            nested_dir = project_dir / "flows" / "greeting"
            nested_dir.mkdir(parents=True)

            result = default_export_path(str(nested_dir))

        self.assertEqual(result, str(project_dir / "sip-trunks.yaml"))

    def test_default_export_requires_a_project(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "--output FILE"):
                default_export_path(temp_dir)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_list_default_export_uses_project_root_with_explicit_scope(
        self, export_config, json_print
    ):
        export_config.return_value = {"account_id": "acct-other", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            nested_dir = project_dir / "flows"
            nested_dir.mkdir()
            args = self._parser().parse_args(
                [
                    "sip-trunks", "list", "--path", str(nested_dir),
                    "--account-id", "acct-other", "--region", "us-1", "--output", "--json",
                ]
            )

            SIPTrunksCommand.run(args)

            output = project_dir / "sip-trunks.yaml"
            self.assertEqual(output.read_text(encoding="utf-8"), "[]\n")
            self.assertFalse((Path(temp_dir) / "sip-trunks.yaml").exists())

        export_config.assert_called_once_with("us-1", "acct-other")
        json_print.assert_called_once_with(
            {"success": True, "output_path": str(output), "trunk_count": 0}
        )

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_standalone_list_export_requires_an_explicit_output_path(
        self, export_config, json_print
    ):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            command = [
                "sip-trunks", "list", "--path", temp_dir,
                "--account-id", "acct-123", "--region", "uk-1", "--json", "--output",
            ]
            args = self._parser().parse_args(command)
            with self.assertRaisesRegex(ValueError, "--output FILE"):
                SIPTrunksCommand.run(args)
            export_config.assert_not_called()
            self.assertEqual(list(Path(temp_dir).iterdir()), [])

            output = Path(temp_dir) / "selected.yaml"
            args = self._parser().parse_args([*command, str(output)])
            SIPTrunksCommand.run(args)

            self.assertEqual(output.read_text(encoding="utf-8"), "[]\n")

        export_config.assert_called_once_with("uk-1", "acct-123")
        json_print.assert_called_once_with(
            {"success": True, "output_path": str(output), "trunk_count": 0}
        )

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_list_export_is_reusable_and_contains_extensions(self, list_trunks, list_extensions):
        list_trunks.return_value = {
            "sip_trunks": [
                {
                    "id": "tr-123",
                    "name": "Primary carrier",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "inbound": {
                        "hostname": "tr-123.sbc.sip.uk.poly.ai",
                        "sip_auth": {
                            "enabled": True,
                            "username": "alice",
                            "realm": "sbc.sip.uk.poly.ai",
                        },
                        "sip_token_auth": {"enabled": False},
                    },
                    "created_at": "2026-08-12T12:00:00Z",
                    "updated_at": "2026-08-12T12:01:00Z",
                }
            ]
        }
        list_extensions.return_value = {
            "extensions": [
                {
                    "extension": "1000",
                    "agent": {
                        "agent_id": "charging-support",
                        "client_env": "live",
                        "variant_id": "",
                    },
                }
            ]
        }

        result = export_config("uk-1", "pod-point-uk")

        self.assertNotIn("region", result)
        config = result["sip_trunks"][0]
        self.assertEqual(config["hostname"], "tr-123.sbc.sip.uk.poly.ai")
        self.assertEqual(
            config["inbound_auth"],
            {
                "type": "digest",
                "username": "alice",
                "realm": "sbc.sip.uk.poly.ai",
            },
        )
        self.assertNotIn("created_at", config)
        self.assertNotIn("updated_at", config)
        self.assertEqual(
            config["extensions"][0],
            {
                "extension": "1000",
                "agent_id": "charging-support",
                "client_env": "live",
                "variant_id": "",
            },
        )

    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_export_refuses_to_overwrite_without_force(self, export_config):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sip-trunks.yaml"
            output.write_text("existing", encoding="utf-8")
            for flags in ([], ["--json"]):
                with self.subTest(flags=flags):
                    args = self._parser().parse_args(
                        [
                            "sip-trunks", "list", "--account-id", "acct-123",
                            "--region", "uk-1", "--path", temp_dir,
                            "--output", str(output), *flags,
                        ]
                    )

                    with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                        SIPTrunksCommand.run(args)

                    self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    def test_exported_yaml_can_be_loaded_by_manage(self):
        data = {
            "account_id": "pod-point-uk",
            "sip_trunks": [
                {
                    "id": "tr-123",
                    "name": "Primary carrier",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "hostname": "tr-123.sbc.sip.uk.poly.ai",
                    "default_route": {"agent_id": "default-agent", "client_env": "live"},
                    "outbound": {
                        "sip_addresses": ["sip:carrier.example.com"],
                        "default_caller_id": "+442012345678",
                    },
                    "extensions": [
                        {
                            "extension": extension,
                            "agent_id": "charging-support",
                            "client_env": "live",
                        }
                        for extension in ("0010", "1000", "+44/2000", "*123", "true")
                    ],
                }
            ],
        }
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "pod-point-uk"
            account_dir.mkdir()
            project_dir = account_dir / "charging-support"
            project_dir.mkdir()
            (project_dir / "project.yaml").write_text(
                "project_id: charging-support\naccount_id: pod-point-uk\nregion: uk-1\n",
                encoding="utf-8",
            )
            output = account_dir / "sip-trunks.yaml"
            args = Namespace(output=str(output), force=False, path=str(account_dir))
            SIPTrunksCommand._write_export(args, data)
            exported_text = output.read_text(encoding="utf-8")
            manage_args = Namespace(
                path=str(project_dir),
                file_path=None,
                account_id=None,
                region=None,
                json=False,
            )

            loaded = load_manage_config(
                manage_args.path,
                file_path=manage_args.file_path,
                account_id=manage_args.account_id,
                region=manage_args.region,
            )

        self.assertEqual(loaded.region, "uk-1")
        self.assertEqual(loaded.account_id, "pod-point-uk")
        self.assertEqual(loaded.trunks, data["sip_trunks"])
        self.assertTrue(exported_text.startswith("- id: tr-123\n"))
        self.assertNotIn("sip_trunks:", exported_text)
        self.assertNotIn("account_id:", exported_text)

    def test_manage_rejects_region_in_yaml(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text("region: uk-1\nsip_trunks: []\n", encoding="utf-8")
            args = Namespace(
                path=temp_dir,
                file_path=str(config_file),
                account_id="acct-123",
                region="uk-1",
                json=False,
            )

            with self.assertRaisesRegex(ValueError, "Do not set 'region'"):
                load_manage_config(
                    args.path,
                    file_path=args.file_path,
                    account_id=args.account_id,
                    region=args.region,
                )

    def test_manage_rejects_wrapped_and_non_list_formats(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            sources = (
                "sip_trunks:\n  - name: Primary carrier\n",
                "sip_trunks:\n  Primary carrier:\n    sip_cidr: [203.0.113.0/24]\n",
                "account_id: acct-123\nsip_trunks: []\n",
                "sip_trunks: {}\n",
                "{}\n",
                "false\n",
                "0\n",
                "- invalid\n",
            )
            for source in sources:
                with self.subTest(source=source):
                    config_file.write_text(source, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "top-level list of SIP trunk mappings"):
                        load_manage_config(
                            temp_dir, file_path=str(config_file),
                            account_id="acct-123", region="uk-1",
                        )

    def test_empty_manage_files_declare_no_trunks(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            for source in ("", "# No trunks managed\n", "[]\n"):
                with self.subTest(source=source):
                    config_file.write_text(source, encoding="utf-8")
                    loaded = load_manage_config(
                        temp_dir, file_path=str(config_file), account_id="acct-123", region="uk-1"
                    )
                    self.assertEqual(loaded.trunks, [])

    def test_environment_secret_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "password_env.*prompted"):
            managed_trunk_data(
                "tr-123",
                {
                    "outbound": None,
                    "default_route": None,
                    "inbound_auth": {
                        "type": "digest",
                        "username": "alice",
                        "password_env": "CARRIER_SIP_PASSWORD",
                    },
                },
                create=False,
            )

    @patch("getpass.getpass")
    @patch("poly.cli_commands.shared.read_project_config", return_value=None)
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_preview_validates_extensions_before_prompting_or_writing(
        self, list_trunks, _read_project, prompt
    ):
        list_trunks.return_value = {"sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text(
                """- name: Example Trunk
  default_route: null
  outbound: null
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  inbound_auth:
    type: digest
    username: carrier-user
  extensions:
    - extension: "1000"
      client_env: live
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=temp_dir,
                file_path=str(config_file),
                account_id="acct-123",
                region="uk-1",
                json=False,
                rotate_auth=None,
            )

            with self.assertRaisesRegex(ValueError, "missing required field.*agent_id"):
                SIPTrunksCommand._build_manage_plan(args)

        prompt.assert_not_called()

    @patch("poly.cli_commands.shared.read_project_config", return_value=None)
    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_preview_shows_extension_removed_from_present_list(
        self, list_trunks, list_extensions, _read_project
    ):
        list_trunks.return_value = {
            "sip_trunks": [
                {
                    "id": "tr-123",
                    "name": "Example Trunk",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "inbound": {"hostname": "tr-123.example"},
                }
            ]
        }
        list_extensions.return_value = {
            "extensions": [
                {
                    "extension": "1000",
                    "agent": {"agent_id": "agent-one", "client_env": "live"},
                },
                {
                    "extension": "2000",
                    "agent": {"agent_id": "agent-two", "client_env": "live"},
                },
            ]
        }
        with TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "sip-trunks.yaml").write_text(
                """- id: tr-123
  name: Example Trunk
  default_route: null
  outbound: null
  hostname: tr-123.example
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  encrypted: true
  extensions:
    - extension: "1000"
      agent_id: agent-one
      client_env: live
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=temp_dir,
                file_path=str(Path(temp_dir) / "sip-trunks.yaml"),
                account_id="acct-123",
                region="uk-1",
                json=False,
                rotate_auth=None,
            )

            changes = [
                change.as_dict() for change in SIPTrunksCommand._build_manage_plan(args).changes
            ]

        self.assertIn(
            {
                "action": "delete",
                "resource": "extension 2000",
                "diff": "- from trunk tr-123",
            },
            changes,
        )

    @patch("getpass.getpass", return_value="secret")
    def test_new_digest_auth_prompts_for_password(self, prompt):
        desired = managed_trunk_data(
            "Primary carrier",
            {
                "outbound": None,
                "name": "Primary carrier",
                "default_route": None,
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
                "inbound_auth": {"type": "digest", "username": "alice"},
            },
            create=True,
        )

        supplied = SIPTrunksCommand._prompt_auth_secret(
            "Primary carrier", None, desired, rotate=False
        )

        self.assertTrue(supplied)
        self.assertEqual(
            desired["inbound"],
            {"sip_auth": {"username": "alice", "password": "secret"}},
        )
        prompt.assert_called_once_with("SIP password for Primary carrier: ")

    @patch("getpass.getpass")
    def test_existing_digest_auth_does_not_prompt_or_resend_password(self, prompt):
        desired = managed_trunk_data(
            "tr-123",
            {"outbound": None, "default_route": None, "inbound_auth": {"type": "digest", "username": "alice"}},
            create=False,
        )
        current = {
            "id": "tr-123",
            "inbound": {"sip_auth": {"enabled": True, "username": "alice"}},
        }

        supplied = SIPTrunksCommand._prompt_auth_secret("tr-123", current, desired, rotate=False)

        self.assertFalse(supplied)
        self.assertNotIn("password", desired["inbound"]["sip_auth"])
        prompt.assert_not_called()

    @patch("getpass.getpass", return_value="rotated")
    def test_explicit_rotation_prompts_for_existing_digest_auth(self, prompt):
        desired = managed_trunk_data(
            "tr-123",
            {"outbound": None, "default_route": None, "inbound_auth": {"type": "digest", "username": "alice"}},
            create=False,
        )
        current = {
            "id": "tr-123",
            "inbound": {"sip_auth": {"enabled": True, "username": "alice"}},
        }

        supplied = SIPTrunksCommand._prompt_auth_secret("tr-123", current, desired, rotate=True)

        self.assertTrue(supplied)
        self.assertEqual(desired["inbound"]["sip_auth"]["password"], "rotated")
        prompt.assert_called_once()

    def test_auth_type_none_disables_current_auth(self):
        desired = managed_trunk_data(
            "tr-123", {"outbound": None, "default_route": None, "inbound_auth": {"type": "none"}}, create=False
        )
        patch_data = trunk_patch(
            {
                "name": "tr-123",
                "inbound": {
                    "sip_auth": {"enabled": False},
                    "sip_token_auth": {"enabled": True},
                },
            },
            desired,
            secret_supplied=False,
        )

        self.assertEqual(patch_data, {"inbound": {"sip_token_auth": {"disable": True}}})

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_export_includes_empty_authoritative_extensions_list(
        self, list_trunks, list_extensions
    ):
        list_trunks.return_value = {
            "sip_trunks": [
                {
                    "id": "tr-123",
                    "name": "Example",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "inbound": {},
                }
            ]
        }
        list_extensions.return_value = {"extensions": []}

        result = export_config("uk-1", "acct-123")

        self.assertEqual(result["sip_trunks"][0]["extensions"], [])
        self.assertIsNone(result["sip_trunks"][0]["default_route"])
        self.assertIsNone(result["sip_trunks"][0]["outbound"])

    @patch("poly.output.console.console")
    @patch("poly.output.console.info")
    def test_manage_prints_nothing_changed_without_table(self, info, console):
        from poly.output.console import print_sip_trunk_manage_result

        print_sip_trunk_manage_result(
            {
                "config_file": "/account/sip-trunks.yaml",
                "trunks": [
                    {
                        "key": "tr-123",
                        "status": "unchanged",
                        "id": "tr-123",
                        "hostname": "tr-123.sbc.sip.uk.poly.ai",
                        "extensions_total": 1,
                        "extensions_created": 0,
                        "extensions_updated": 0,
                        "extensions_deleted": 0,
                    }
                ],
            },
        )

        info.assert_called_once_with("Nothing changed.")
        console.print.assert_not_called()

    def test_manage_file_is_discovered_in_project_parent(self):
        with TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "shared-projects"
            project_dir = self._write_project_config(parent / "project")
            config_file = parent / "sip-trunks.yaml"
            config_file.write_text("[]\n", encoding="utf-8")

            result = find_manage_file(str(project_dir), None)

            self.assertEqual(result, str(config_file))

    def test_manage_discovery_anchors_nested_paths_to_project_root(self):
        with TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir) / "shared-projects"
            project_dir = self._write_project_config(parent / "project")
            nested_dir = project_dir / "flows" / "greeting"
            nested_dir.mkdir(parents=True)
            for directory in (parent, project_dir, nested_dir):
                (directory / "sip-trunks.yaml").write_text("[]\n", encoding="utf-8")

            self.assertEqual(
                find_manage_file(str(nested_dir), None), str(project_dir / "sip-trunks.yaml")
            )
            (project_dir / "sip-trunks.yaml").unlink()
            self.assertEqual(
                find_manage_file(str(nested_dir), None), str(parent / "sip-trunks.yaml")
            )

    def test_manage_discovery_does_not_search_above_project_parent(self):
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "parent" / "project")
            (Path(temp_dir) / "sip-trunks.yaml").write_text("[]\n", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                find_manage_file(str(project_dir), None)

    @patch("poly.cli_commands.shared.read_project_config", return_value=None)
    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "create_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_creates_trunk_and_reports_hostname(
        self, list_trunks, create_trunk, list_extensions, _read_project
    ):
        list_trunks.return_value = {"sip_trunks": []}
        create_trunk.return_value = {
            "id": "tr-123",
            "account_id": "pod-point-uk",
            "name": "Primary carrier",
            "inbound": {"hostname": "tr-123.sbc.sip.uk.poly.ai"},
            "created_at": "2026-08-12T12:00:00Z",
            "updated_at": "2026-08-12T12:01:00Z",
        }
        list_extensions.return_value = {"extensions": []}

        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "pod-point-uk"
            account_dir.mkdir()
            config_file = account_dir / "sip-trunks.yaml"
            config_file.write_text(
                """- name: Primary carrier
  default_route: null
  outbound: null
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=str(account_dir),
                file_path=str(config_file),
                account_id="pod-point-uk",
                region="uk-1",
                json=False,
            )

            result = SIPTrunksCommand._apply_manage_plan(SIPTrunksCommand._build_manage_plan(args))
            saved_config = config_file.read_text(encoding="utf-8")

        create_trunk.assert_called_once_with(
            "uk-1",
            "pod-point-uk",
            {
                "name": "Primary carrier",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
        )
        self.assertEqual(result["trunks"][0]["status"], "created")
        self.assertEqual(result["trunks"][0]["hostname"], "tr-123.sbc.sip.uk.poly.ai")
        self.assertIn("- id: tr-123", saved_config)
        self.assertIn("name: Primary carrier", saved_config)
        self.assertIn("hostname: tr-123.sbc.sip.uk.poly.ai", saved_config)
        self.assertNotIn("created_at", saved_config)
        self.assertNotIn("updated_at", saved_config)

    def test_persist_trunk_response_rejects_wrapped_formats_without_modifying_file(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            for source in (
                "sip_trunks:\n  - name: Primary carrier\n",
                "sip_trunks:\n  Primary carrier: {}\n",
            ):
                with self.subTest(source=source):
                    config_file.write_text(source, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "top-level list of SIP trunk mappings"):
                        persist_trunk_response(
                            str(config_file), 0, "Primary carrier", {"id": "tr-123"}
                        )
                    self.assertEqual(config_file.read_text(encoding="utf-8"), source)

    def test_persist_trunk_response_preserves_comments_and_adds_useful_fields(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text(
                """# Carrier connection
- name: "Primary carrier"
  default_route: null
  outbound: null
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  inbound_auth:
    type: digest
    username: carrier-user
""",
                encoding="utf-8",
            )

            persist_trunk_response(
                str(config_file),
                0,
                "Primary carrier",
                {
                    "id": "tr-123",
                    "account_id": "pod-point-uk",
                    "inbound": {
                        "hostname": "tr-123.sbc.sip.uk.poly.ai",
                        "sip_auth": {"realm": "sbc.sip.uk.poly.ai"},
                    },
                    "created_at": "2026-08-12T12:00:00Z",
                    "updated_at": "2026-08-12T12:01:00Z",
                },
            )

            saved = config_file.read_text(encoding="utf-8")
        self.assertIn("# Carrier connection", saved)
        self.assertNotIn("account_id:", saved)
        self.assertIn('name: "Primary carrier"', saved)
        self.assertIn("id: tr-123", saved)
        self.assertIn("hostname: tr-123.sbc.sip.uk.poly.ai", saved)
        self.assertIn("realm: sbc.sip.uk.poly.ai", saved)
        self.assertNotIn("created_at", saved)
        self.assertNotIn("updated_at", saved)

    @patch("getpass.getpass", return_value="rotated-secret")
    @patch("poly.cli_commands.shared.read_project_config", return_value=None)
    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "update_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_rotates_auth_only_when_explicitly_requested(
        self, list_trunks, update_trunk, list_extensions, _read_project, prompt
    ):
        trunk = {
            "id": "tr-123",
            "name": "Primary carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
            "encrypted": True,
            "inbound": {
                "hostname": "tr-123.example",
                "sip_auth": {"enabled": True, "username": "alice"},
            },
        }
        list_trunks.return_value = {"sip_trunks": [trunk]}
        update_trunk.return_value = trunk
        list_extensions.return_value = {"extensions": []}

        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "pod-point-uk"
            account_dir.mkdir()
            (account_dir / "sip-trunks.yaml").write_text(
                """- id: tr-123
  name: Primary carrier
  default_route: null
  outbound: null
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  encrypted: true
  inbound_auth:
    type: digest
    username: alice
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=str(account_dir),
                file_path=str(account_dir / "sip-trunks.yaml"),
                account_id="pod-point-uk",
                region="uk-1",
                json=False,
                rotate_auth="tr-123",
            )

            result = SIPTrunksCommand._apply_manage_plan(SIPTrunksCommand._build_manage_plan(args))

        prompt.assert_called_once_with("SIP password for tr-123: ")
        update_trunk.assert_called_once_with(
            "uk-1",
            "pod-point-uk",
            "tr-123",
            {"inbound": {"sip_auth": {"username": "alice", "password": "rotated-secret"}}},
        )
        self.assertEqual(result["trunks"][0]["status"], "updated")

    @patch("poly.cli_commands.shared.read_project_config", return_value=None)
    @patch.object(AgentStudioInterface, "delete_sip_trunk")
    @patch.object(AgentStudioInterface, "update_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_updates_declared_trunk_without_deleting_omitted_trunks(
        self, list_trunks, update_trunk, delete_trunk, _read_project
    ):
        list_trunks.return_value = {
            "sip_trunks": [
                {
                    "id": "tr-managed",
                    "name": "Primary carrier",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "inbound": {"hostname": "managed.example"},
                },
                {
                    "id": "tr-omitted",
                    "name": "Do not delete",
                    "sip_cidr": ["192.0.2.0/24"],
                    "rtp_cidr": ["192.0.2.0/24"],
                    "encrypted": True,
                    "inbound": {"hostname": "omitted.example"},
                },
            ]
        }
        update_trunk.return_value = {
            "id": "tr-managed",
            "name": "Primary carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
            "encrypted": False,
            "inbound": {"hostname": "managed.example"},
        }

        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "pod-point-uk"
            account_dir.mkdir()
            config_file = account_dir / "sip-trunks.yaml"
            config_file.write_text(
                """- id: tr-managed
  name: Primary carrier
  default_route: null
  outbound: null
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  encrypted: false
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=str(account_dir),
                file_path=str(config_file),
                account_id="pod-point-uk",
                region="uk-1",
                json=False,
            )

            result = SIPTrunksCommand._apply_manage_plan(SIPTrunksCommand._build_manage_plan(args))

        update_trunk.assert_called_once_with(
            "uk-1", "pod-point-uk", "tr-managed", {"encrypted": False}
        )
        delete_trunk.assert_not_called()
        self.assertEqual([item["id"] for item in result["trunks"]], ["tr-managed"])
