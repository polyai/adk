"""Tests for the SIP Trunking API client and CLI commands.

Copyright PolyAI Limited
"""

import os
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.sip_trunks import SIPTrunksCommand
from poly.handlers.sip_trunking_api import SIPTrunkingAPIHandler


class SIPTrunkingAPIHandlerTest(unittest.TestCase):
    @patch("poly.handlers.sip_trunking_api.PlatformAPIHandler.make_request")
    def test_create_trunk_uses_account_endpoint(self, make_request):
        body = {
            "name": "carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
        }
        make_request.return_value = {"id": "tr-123"}

        result = SIPTrunkingAPIHandler.create_trunk("euw-1", "acct-123", body)

        self.assertEqual(result, {"id": "tr-123"})
        make_request.assert_called_once_with(
            "euw-1",
            "/v1/accounts/acct-123/telephony/sip-trunks",
            "POST",
            data=body,
        )

    @patch("poly.handlers.sip_trunking_api.PlatformAPIHandler.make_request")
    def test_extension_is_url_encoded(self, make_request):
        SIPTrunkingAPIHandler.get_extension("uk-1", "acct-123", "tr-123", "+44/100")

        make_request.assert_called_once_with(
            "uk-1",
            "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions/%2B44%2F100",
        )

    @patch("poly.handlers.sip_trunking_api.PlatformAPIHandler.make_request")
    def test_delete_extension_uses_delete(self, make_request):
        SIPTrunkingAPIHandler.delete_extension("us-1", "acct-123", "tr-123", "1000")

        make_request.assert_called_once_with(
            "us-1",
            "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions/1000",
            "DELETE",
        )


class SIPTrunksCommandTest(unittest.TestCase):
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
                "eu",
                "--output",
                "export.yaml",
                "--force",
            ]
        )

        self.assertEqual(args.command, "sip-trunks")
        self.assertEqual(args.sip_trunks_subcommand, "list")
        self.assertEqual(args.output, "export.yaml")
        self.assertTrue(args.force)

    def test_parser_registers_explicit_auth_rotation(self):
        args = self._parser().parse_args(
            ["sip-trunks", "manage", "--rotate-auth", "tr-123"]
        )

        self.assertEqual(args.rotate_auth, "tr-123")

    def test_parser_registers_yes_for_non_interactive_manage(self):
        args = self._parser().parse_args(["sip-trunks", "manage", "--yes"])

        self.assertTrue(args.yes)

    @patch.object(SIPTrunksCommand, "manage")
    @patch.object(SIPTrunksCommand, "_print_manage_diff")
    @patch.object(SIPTrunksCommand, "_preview_manage")
    @patch("questionary.confirm")
    def test_manage_displays_diff_and_aborts_when_not_confirmed(
        self, confirm, preview_manage, print_diff, manage
    ):
        changes = [{"action": "update", "resource": "trunk tr-123", "diff": "name"}]
        preview_manage.return_value = changes
        confirm.return_value.ask.return_value = False
        args = self._parser().parse_args(["sip-trunks", "manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        confirm.assert_called_once_with(
            "Apply these SIP trunk changes?", default=False, auto_enter=False
        )
        manage.assert_not_called()

    @patch.object(SIPTrunksCommand, "_print_manage_result")
    @patch.object(SIPTrunksCommand, "manage")
    @patch.object(SIPTrunksCommand, "_print_manage_diff")
    @patch.object(SIPTrunksCommand, "_preview_manage")
    @patch("questionary.confirm")
    def test_manage_applies_changes_after_confirmation(
        self, confirm, preview_manage, print_diff, manage, print_result
    ):
        changes = [{"action": "create", "resource": "trunk Example", "diff": "+ trunk"}]
        result = {"success": True, "trunks": []}
        preview_manage.return_value = changes
        confirm.return_value.ask.return_value = True
        manage.return_value = result
        args = self._parser().parse_args(["sip-trunks", "manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        manage.assert_called_once_with(args)
        print_result.assert_called_once_with(result, output_json=False)

    @patch.object(SIPTrunksCommand, "_print_list_table")
    @patch.object(SIPTrunksCommand, "export_config")
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
                "uk",
            ]
        )

        SIPTrunksCommand.run(args)

        export_config.assert_called_once_with("uk-1", "acct-123")
        print_list_table.assert_called_once_with(export)

    @patch.object(SIPTrunksCommand, "_print_get_table")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.get_trunk")
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
                "uk",
            ]
        )

        SIPTrunksCommand.run(args)

        get_trunk.assert_called_once_with("uk-1", "acct-123", "tr-123")
        list_extensions.assert_called_once_with("uk-1", "acct-123", "tr-123")
        print_get_table.assert_called_once_with(trunk, extensions)

    @patch.object(SIPTrunksCommand, "_print_result")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.delete_trunk")
    def test_delete_returns_machine_readable_success(self, delete_trunk, print_result):
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "delete",
                "tr-123",
                "--account-id",
                "acct-123",
                "--region",
                "us",
                "--json",
            ]
        )

        SIPTrunksCommand.run(args)

        delete_trunk.assert_called_once_with("us-1", "acct-123", "tr-123")
        print_result.assert_called_once_with(
            {"success": True, "trunk_id": "tr-123"}, output_json=True
        )

    @patch("poly.cli_commands.sip_trunks.read_project_config")
    def test_context_defaults_to_current_project(self, read_project_config):
        read_project_config.return_value = MagicMock(
            account_id="acct-123", region="euw-1", root_path="/account/project"
        )
        args = Namespace(account_id=None, region=None, path="/project", json=False)

        result = SIPTrunksCommand._resolve_context(args)

        self.assertEqual(result, ("euw-1", "acct-123"))
        read_project_config.assert_called_once_with(os.path.abspath(args.path))

    def test_context_is_inferred_from_account_child_projects(self):
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "acct-123"
            project_dir = account_dir / "project-one"
            project_dir.mkdir(parents=True)
            (project_dir / "project.yaml").write_text(
                "project_id: project-one\naccount_id: acct-123\nregion: uk-1\n",
                encoding="utf-8",
            )

            result = SIPTrunksCommand._infer_account_context(str(account_dir))

        self.assertEqual(result, ("uk-1", "acct-123"))

    def test_conflicting_account_project_regions_are_rejected(self):
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "acct-123"
            for project_id, region in (("one", "uk-1"), ("two", "us-1")):
                project_dir = account_dir / project_id
                project_dir.mkdir(parents=True)
                (project_dir / "project.yaml").write_text(
                    f"project_id: {project_id}\naccount_id: acct-123\nregion: {region}\n",
                    encoding="utf-8",
                )

            with self.assertRaisesRegex(ValueError, "disagree on region"):
                SIPTrunksCommand._infer_account_context(str(account_dir))

    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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

        result = SIPTrunksCommand.export_config("uk-1", "pod-point-uk")

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

    def test_export_refuses_to_overwrite_without_force(self):
        with TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "sip-trunks.yaml"
            output.write_text("existing", encoding="utf-8")
            args = Namespace(output=str(output), force=False, path=temp_dir)

            with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                SIPTrunksCommand._write_export(
                    args,
                    "pod-point-uk",
                    {"account_id": "pod-point-uk", "sip_trunks": {}},
                )

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
            SIPTrunksCommand._write_export(args, "pod-point-uk", data)
            exported_text = output.read_text(encoding="utf-8")
            manage_args = Namespace(
                path=str(account_dir),
                file_path=None,
                account_id=None,
                region=None,
                json=False,
            )

            _, region, account_id, trunks = SIPTrunksCommand._load_manage_config(manage_args)

        self.assertEqual(region, "uk-1")
        self.assertEqual(account_id, "pod-point-uk")
        self.assertEqual(trunks[0]["id"], "tr-123")
        self.assertTrue(exported_text.startswith("- id: tr-123\n"))
        self.assertNotIn("sip_trunks:", exported_text)
        self.assertNotIn("account_id:", exported_text)

    def test_manage_rejects_region_in_yaml(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text("region: uk\nsip_trunks: []\n", encoding="utf-8")
            args = Namespace(
                path=temp_dir,
                file_path=None,
                account_id="acct-123",
                region="uk",
                json=False,
            )

            with self.assertRaisesRegex(ValueError, "Do not set 'region'"):
                SIPTrunksCommand._load_manage_config(args)

    def test_environment_secret_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "password_env.*prompted"):
            SIPTrunksCommand._managed_trunk_data(
                "tr-123",
                {
                    "inbound_auth": {
                        "type": "digest",
                        "username": "alice",
                        "password_env": "CARRIER_SIP_PASSWORD",
                    },
                },
                create=False,
            )

    @patch("poly.cli_commands.sip_trunks.getpass")
    @patch("poly.cli_commands.sip_trunks.read_project_config", return_value=None)
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
    def test_preview_validates_extensions_before_prompting_or_writing(
        self, list_trunks, _read_project, prompt
    ):
        list_trunks.return_value = {"sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text(
                """- name: Example Trunk
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
                file_path=None,
                account_id="acct-123",
                region="uk",
                json=False,
                rotate_auth=None,
            )

            with self.assertRaisesRegex(ValueError, "missing required field.*agent_id"):
                SIPTrunksCommand._preview_manage(args)

        prompt.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.read_project_config", return_value=None)
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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
                file_path=None,
                account_id="acct-123",
                region="uk",
                json=False,
                rotate_auth=None,
            )

            changes = SIPTrunksCommand._preview_manage(args)

        self.assertIn(
            {
                "action": "delete",
                "resource": "extension 2000",
                "diff": "- from trunk tr-123",
            },
            changes,
        )

    @patch("poly.cli_commands.sip_trunks.getpass", return_value="secret")
    def test_new_digest_auth_prompts_for_password(self, prompt):
        desired, _ = SIPTrunksCommand._managed_trunk_data(
            "Primary carrier",
            {
                "name": "Primary carrier",
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

    @patch("poly.cli_commands.sip_trunks.getpass")
    def test_existing_digest_auth_does_not_prompt_or_resend_password(self, prompt):
        desired, _ = SIPTrunksCommand._managed_trunk_data(
            "tr-123",
            {"inbound_auth": {"type": "digest", "username": "alice"}},
            create=False,
        )
        current = {
            "id": "tr-123",
            "inbound": {"sip_auth": {"enabled": True, "username": "alice"}},
        }

        supplied = SIPTrunksCommand._prompt_auth_secret(
            "tr-123", current, desired, rotate=False
        )

        self.assertFalse(supplied)
        self.assertNotIn("password", desired["inbound"]["sip_auth"])
        prompt.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.getpass", return_value="rotated")
    def test_explicit_rotation_prompts_for_existing_digest_auth(self, prompt):
        desired, _ = SIPTrunksCommand._managed_trunk_data(
            "tr-123",
            {"inbound_auth": {"type": "digest", "username": "alice"}},
            create=False,
        )
        current = {
            "id": "tr-123",
            "inbound": {"sip_auth": {"enabled": True, "username": "alice"}},
        }

        supplied = SIPTrunksCommand._prompt_auth_secret(
            "tr-123", current, desired, rotate=True
        )

        self.assertTrue(supplied)
        self.assertEqual(desired["inbound"]["sip_auth"]["password"], "rotated")
        prompt.assert_called_once()

    def test_auth_type_none_disables_current_auth(self):
        desired, _ = SIPTrunksCommand._managed_trunk_data(
            "tr-123", {"inbound_auth": {"type": "none"}}, create=False
        )
        patch_data = SIPTrunksCommand._trunk_patch(
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

    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.update_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.create_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.delete_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    def test_unchanged_extensions_report_total_without_changes(
        self, list_extensions, delete_extension, create_extension, update_extension
    ):
        list_extensions.return_value = {
            "extensions": [
                {
                    "extension": "1000",
                    "agent": {
                        "agent_id": "charging-support",
                        "client_env": "live",
                    },
                }
            ]
        }

        result = SIPTrunksCommand._manage_extensions(
            "uk-1",
            "pod-point-uk",
            "tr-123",
            [
                {
                    "extension": "1000",
                    "agent_id": "charging-support",
                    "client_env": "live",
                }
            ],
        )

        self.assertEqual(result, (1, 0, 0, 0))
        create_extension.assert_not_called()
        update_extension.assert_not_called()
        delete_extension.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.update_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.create_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.delete_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    def test_manage_extensions_deletes_entries_omitted_from_present_list(
        self, list_extensions, delete_extension, create_extension, update_extension
    ):
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

        result = SIPTrunksCommand._manage_extensions(
            "uk-1",
            "pod-point-uk",
            "tr-123",
            [{"extension": "1000", "agent_id": "agent-one", "client_env": "live"}],
        )

        self.assertEqual(result, (1, 0, 0, 1))
        delete_extension.assert_called_once_with(
            "uk-1", "pod-point-uk", "tr-123", "2000"
        )
        create_extension.assert_not_called()
        update_extension.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.delete_extension")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    def test_omitted_extensions_key_leaves_extensions_unmanaged(
        self, list_extensions, delete_extension
    ):
        result = SIPTrunksCommand._manage_extensions(
            "uk-1", "pod-point-uk", "tr-123", None
        )

        self.assertEqual(result, (0, 0, 0, 0))
        list_extensions.assert_not_called()
        delete_extension.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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

        result = SIPTrunksCommand.export_config("uk-1", "acct-123")

        self.assertEqual(result["sip_trunks"][0]["extensions"], [])

    @patch("poly.output.console.console")
    @patch("poly.output.console.info")
    def test_manage_prints_nothing_changed_without_table(self, info, console):
        SIPTrunksCommand._print_manage_result(
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
            output_json=False,
        )

        info.assert_called_once_with("Nothing changed.")
        console.print.assert_not_called()

    def test_manage_file_is_discovered_at_account_level(self):
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "pod-point-uk"
            project_dir = account_dir / "charging-support"
            project_dir.mkdir(parents=True)
            config_file = account_dir / "sip-trunks.yaml"
            config_file.write_text("sip_trunks: []\n", encoding="utf-8")

            result = SIPTrunksCommand._find_manage_file(str(project_dir), None)

            self.assertEqual(result, str(config_file))

    @patch("poly.cli_commands.sip_trunks.read_project_config", return_value=None)
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.create_trunk")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=str(account_dir),
                file_path=None,
                account_id=None,
                region="uk",
                json=False,
            )

            result = SIPTrunksCommand.manage(args)
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

    def test_persist_trunk_response_preserves_comments_and_adds_useful_fields(self):
        with TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text(
                """# Carrier connection
- name: "Primary carrier"
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  inbound_auth:
    type: digest
    username: carrier-user
""",
                encoding="utf-8",
            )

            SIPTrunksCommand._persist_trunk_response(
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

    @patch("poly.cli_commands.sip_trunks.getpass", return_value="rotated-secret")
    @patch("poly.cli_commands.sip_trunks.read_project_config", return_value=None)
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_extensions")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.update_trunk")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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
                """sip_trunks:
  - id: tr-123
    name: Primary carrier
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
                file_path=None,
                account_id=None,
                region="uk",
                json=False,
                rotate_auth="tr-123",
            )

            result = SIPTrunksCommand.manage(args)

        prompt.assert_called_once_with("SIP password for tr-123: ")
        update_trunk.assert_called_once_with(
            "uk-1",
            "pod-point-uk",
            "tr-123",
            {
                "inbound": {
                    "sip_auth": {"username": "alice", "password": "rotated-secret"}
                }
            },
        )
        self.assertEqual(result["trunks"][0]["status"], "updated")

    @patch("poly.cli_commands.sip_trunks.read_project_config", return_value=None)
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.delete_trunk")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.update_trunk")
    @patch("poly.cli_commands.sip_trunks.SIPTrunkingAPIHandler.list_trunks")
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
                """sip_trunks:
  - id: tr-managed
    name: Primary carrier
    sip_cidr: [203.0.113.0/24]
    rtp_cidr: [198.51.100.0/24]
    encrypted: false
""",
                encoding="utf-8",
            )
            args = Namespace(
                path=str(account_dir),
                file_path=None,
                account_id=None,
                region="uk",
                json=False,
            )

            result = SIPTrunksCommand.manage(args)

        update_trunk.assert_called_once_with(
            "uk-1", "pod-point-uk", "tr-managed", {"encrypted": False}
        )
        delete_trunk.assert_not_called()
        self.assertEqual([item["id"] for item in result["trunks"]], ["tr-managed"])
