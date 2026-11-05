"""Tests for the SIP trunk CLI commands.

Copyright PolyAI Limited
"""

import unittest
from argparse import Namespace
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from poly.cli import AgentStudioCLI
from poly.cli_commands.shared import load_project
from poly.cli_commands.sip_trunks import SIPTrunksCommand
from poly.handlers.interface import AgentStudioInterface
from poly.project import AgentStudioProject
from poly.resources.resource_utils import dump_yaml, load_yaml
from poly.sip_trunks.config import (
    load_manage_config,
)
from poly.sip_trunks.reconciler import (
    PlanChange,
    managed_trunk_data,
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

    def _project_args(self, arguments, *, region="uk-1"):
        temp_dir = self.enterContext(TemporaryDirectory())
        project_dir = self._write_project_config(Path(temp_dir) / "project", region=region)
        return self._parser().parse_args(["sip-trunks", *arguments, "--path", str(project_dir)])

    def test_parser_registers_yaml_export_options(self):
        args = self._parser().parse_args(
            [
                "sip-trunks",
                "list",
                "--output",
                "export.yaml",
                "--force",
            ]
        )

        self.assertEqual(args.command, "sip-trunks")
        self.assertEqual(args.sip_trunks_subcommand, "list")
        self.assertEqual(args.output, "export.yaml")
        self.assertTrue(args.force)

    def test_parser_rejects_account_and_region_overrides_for_all_actions(self):
        parser = self._parser()
        for action in (["list"], ["manage"], ["get", "tr-123"], ["delete", "tr-123"]):
            for flag, value in (
                ("--account-id", "acct-123"), ("--account_id", "acct-123"), ("--region", "uk-1"),
            ):
                with self.subTest(action=action[0], flag=flag), patch("sys.stderr"):
                    with self.assertRaises(SystemExit) as error:
                        parser.parse_args(["sip-trunks", *action, flag, value])
                    self.assertEqual(error.exception.code, 2)

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

    @patch.object(AgentStudioProject, "apply_sip_trunk_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(AgentStudioProject, "build_sip_trunk_plan")
    @patch("questionary.confirm")
    def test_manage_displays_diff_and_aborts_when_not_confirmed(
        self, confirm, build_plan, print_diff, apply_plan
    ):
        changes = [{"action": "update", "resource": "trunk tr-123", "diff": "name"}]
        plan = MagicMock(changes=(PlanChange(**changes[0]),))
        build_plan.return_value = plan
        confirm.return_value.ask.return_value = False
        args = self._project_args(["manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        confirm.assert_called_once_with(
            "Apply these SIP trunk changes?", default=False, auto_enter=False
        )
        apply_plan.assert_not_called()

    @patch("poly.output.console.print_sip_trunk_manage_result")
    @patch.object(AgentStudioProject, "apply_sip_trunk_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(AgentStudioProject, "build_sip_trunk_plan")
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
        args = self._project_args(["manage"])

        SIPTrunksCommand.run(args)

        print_diff.assert_called_once_with(changes)
        apply_plan.assert_called_once_with(
            plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
        )
        print_result.assert_called_once_with(result)

    @patch("poly.output.console.print_sip_trunk_manage_result")
    @patch.object(AgentStudioProject, "apply_sip_trunk_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(AgentStudioProject, "build_sip_trunk_plan")
    @patch("questionary.confirm")
    def test_manage_force_applies_without_confirmation(
        self, confirm, build_plan, print_diff, apply_plan, print_result
    ):
        plan = MagicMock(changes=(PlanChange("create", "trunk Example", "+ trunk"),))
        result = {"success": True, "trunks": []}
        build_plan.return_value = plan
        apply_plan.return_value = result
        args = self._project_args(["manage", "--force"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        print_diff.assert_called_once_with([change.as_dict() for change in plan.changes])
        apply_plan.assert_called_once_with(
            plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
        )
        print_result.assert_called_once_with(result)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "apply_sip_trunk_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(AgentStudioProject, "build_sip_trunk_plan")
    @patch("questionary.confirm")
    def test_manage_json_applies_without_confirmation(
        self, confirm, build_plan, print_diff, apply_plan, json_print
    ):
        plan = MagicMock(changes=(PlanChange("create", "trunk Example", "+ trunk"),))
        result = {"success": True, "trunks": []}
        build_plan.return_value = plan
        apply_plan.return_value = result
        args = self._project_args(["manage", "--json"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        print_diff.assert_not_called()
        apply_plan.assert_called_once_with(
            plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
        )
        json_print.assert_called_once_with(result)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "apply_sip_trunk_plan")
    @patch("poly.output.console.print_sip_trunk_changes")
    @patch.object(AgentStudioProject, "build_sip_trunk_plan")
    @patch("questionary.confirm")
    def test_manage_json_with_no_changes_does_not_apply(
        self, confirm, build_plan, print_diff, apply_plan, json_print
    ):
        build_plan.return_value = MagicMock(changes=())
        args = self._project_args(["manage", "--json"])

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
        args = self._project_args(["list"])

        SIPTrunksCommand.run(args)

        export_config.assert_called_once_with()
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
        args = self._project_args(["get", "tr-123"])

        SIPTrunksCommand.run(args)

        get_trunk.assert_called_once_with("tr-123")
        list_extensions.assert_called_once_with("tr-123")
        print_get_table.assert_called_once_with(trunk, extensions)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    def test_delete_returns_machine_readable_success(self, delete_trunk, print_result):
        args = self._project_args(["delete", "tr-123", "--force", "--json"], region="us-1")

        SIPTrunksCommand.run(args)

        delete_trunk.assert_called_once_with("tr-123")
        print_result.assert_called_once_with(
            {"success": True, "trunk_id": "tr-123"}
        )

    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_aborts_when_not_confirmed(self, confirm, delete_trunk):
        confirm.return_value.ask.return_value = False
        args = self._project_args(["delete", "tr-123"])

        SIPTrunksCommand.run(args)

        confirm.assert_called_once_with("Delete SIP trunk tr-123?", default=False, auto_enter=False)
        delete_trunk.assert_not_called()

    @patch("poly.output.console.success")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_confirms_and_prints_human_success(self, confirm, delete_trunk, success):
        confirm.return_value.ask.return_value = True
        args = self._project_args(["delete", "tr-123"])

        SIPTrunksCommand.run(args)

        delete_trunk.assert_called_once_with("tr-123")
        success.assert_called_once_with("Deleted SIP trunk tr-123.")

    @patch("poly.output.console.success")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_force_deletes_without_confirmation(self, confirm, delete_trunk, success):
        args = self._project_args(["delete", "tr-123", "-f"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        delete_trunk.assert_called_once_with("tr-123")
        success.assert_called_once_with("Deleted SIP trunk tr-123.")

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "delete_sip_trunk")
    @patch("questionary.confirm")
    def test_delete_json_deletes_without_confirmation(self, confirm, delete_trunk, json_print):
        args = self._project_args(["delete", "tr-123", "--json"])

        SIPTrunksCommand.run(args)

        confirm.assert_not_called()
        delete_trunk.assert_called_once_with("tr-123")
        json_print.assert_called_once_with({"success": True, "trunk_id": "tr-123"})

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch("poly.cli_commands.sip_trunks.load_project")
    def test_command_uses_the_selected_project(self, load_selected_project, json_print):
        project = load_selected_project.return_value
        export = {"account_id": "acct-123", "sip_trunks": []}
        project.export_sip_trunks.return_value = export
        args = self._parser().parse_args(
            ["sip-trunks", "list", "--path", "relative-project", "--json"]
        )

        SIPTrunksCommand.run(args)

        load_selected_project.assert_called_once_with("relative-project", output_json=True)
        project.export_sip_trunks.assert_called_once_with()
        json_print.assert_called_once_with(export)

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_list_default_export_uses_project_root_and_scope(self, export_config, json_print):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            nested_dir = project_dir / "flows"
            nested_dir.mkdir()
            args = self._parser().parse_args(
                ["sip-trunks", "list", "--path", str(nested_dir), "--output", "--json"]
            )

            SIPTrunksCommand.run(args)

            output = project_dir / "sip-trunks.yaml"
            self.assertEqual(output.read_text(encoding="utf-8"), "[]\n")
            self.assertFalse((Path(temp_dir) / "sip-trunks.yaml").exists())

        export_config.assert_called_once_with()
        json_print.assert_called_once_with(
            {"success": True, "output_path": str(output), "trunk_count": 0}
        )

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_commands_require_a_project_before_api_calls_or_output(self, export_config, json_print):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sip-trunks.yaml"
            config_path.write_text("[]\n", encoding="utf-8")
            output = Path(temp_dir) / "selected.yaml"
            commands = (
                ["list"], ["list", "--output"], ["list", "--output", str(output)],
                ["manage"], ["manage", "--file", str(config_path)],
                ["get", "tr-123"], ["delete", "tr-123"],
            )
            with patch("poly.handlers.platform_api.PlatformAPIHandler.make_request") as request:
                for command in commands:
                    with self.subTest(command=command):
                        args = self._parser().parse_args(
                            ["sip-trunks", *command, "--path", temp_dir, "--json"]
                        )
                        with self.assertRaises(SystemExit) as error:
                            SIPTrunksCommand.run(args)
                        self.assertEqual(error.exception.code, 1)
                        request.assert_not_called()
                        export_config.assert_not_called()
                        json_print.assert_not_called()
                        self.assertFalse(output.exists())
                        self.assertEqual(config_path.read_text(encoding="utf-8"), "[]\n")

    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_export_refuses_to_overwrite_without_force(self, export_config):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            self._write_project_config(Path(temp_dir))
            output = Path(temp_dir) / "sip-trunks.yaml"
            output.write_text("existing", encoding="utf-8")
            for flags in ([], ["--json"]):
                with self.subTest(flags=flags):
                    args = self._parser().parse_args(
                        [
                            "sip-trunks", "list", "--path", temp_dir,
                            "--output", str(output), *flags,
                        ]
                    )

                    with self.assertRaisesRegex(FileExistsError, "Refusing to overwrite"):
                        SIPTrunksCommand.run(args)

                    self.assertEqual(output.read_text(encoding="utf-8"), "existing")

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_export_rejects_directory_targets_even_with_force(self, export_config, json_print):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            project_dir = self._write_project_config(root / "project")
            marker = root / "keep.txt"
            marker.write_text("keep this file", encoding="utf-8")
            project_config = (project_dir / "project.yaml").read_bytes()
            for flags in ([], ["--force"], ["--json"], ["--force", "--json"]):
                with self.subTest(flags=flags), chdir(project_dir):
                    args = self._parser().parse_args(
                        ["sip-trunks", "list", "--output", "..", *flags]
                    )

                    with self.assertRaisesRegex(ValueError, "Output path is a directory") as error:
                        SIPTrunksCommand.run(args)

                    self.assertIn(str(root / "sip-trunks.yaml"), str(error.exception))
                    self.assertNotIn("--force", str(error.exception))
                    self.assertEqual(sorted(path.name for path in root.iterdir()), ["keep.txt", "project"])
                    self.assertEqual(marker.read_text(encoding="utf-8"), "keep this file")
                    self.assertEqual((project_dir / "project.yaml").read_bytes(), project_config)
                    json_print.assert_not_called()

    @patch("poly.cli_commands.sip_trunks.json_print")
    @patch.object(AgentStudioProject, "export_sip_trunks")
    def test_export_accepts_a_filename_in_the_project_parent(self, export_config, _json_print):
        export_config.return_value = {"account_id": "acct-123", "sip_trunks": []}
        for flags in ([], ["--json"], ["--force"], ["--force", "--json"]):
            with self.subTest(flags=flags), TemporaryDirectory() as temp_dir:
                root = Path(temp_dir).resolve()
                project_dir = self._write_project_config(root / "project")
                marker = root / "keep.txt"
                marker.write_text("keep this file", encoding="utf-8")
                output = root / "sip-trunks.yaml"
                if "--force" in flags:
                    output.write_text("old export", encoding="utf-8")
                with chdir(project_dir):
                    args = self._parser().parse_args(
                        ["sip-trunks", "list", "--output", "../sip-trunks.yaml", *flags]
                    )

                    SIPTrunksCommand.run(args)

                self.assertEqual(output.read_text(encoding="utf-8"), "[]\n")
                self.assertEqual(marker.read_text(encoding="utf-8"), "keep this file")
                self.assertFalse((project_dir / "sip-trunks.yaml").exists())

    def test_exported_yaml_can_be_loaded_by_manage(self):
        data = {
            "account_id": "acct-123",
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
                            "agent_id": "agent-1",
                            "client_env": "live",
                        }
                        for extension in ("0010", "1000", "+44/2000", "*123", "true")
                    ],
                }
            ],
        }
        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "acct-123"
            account_dir.mkdir()
            project_dir = account_dir / "agent-1"
            project_dir.mkdir()
            (project_dir / "project.yaml").write_text(
                "project_id: agent-1\naccount_id: acct-123\nregion: uk-1\n",
                encoding="utf-8",
            )
            output = account_dir / "sip-trunks.yaml"
            args = Namespace(output=str(output), force=False, path=str(project_dir))
            project = load_project(args.path)
            project.write_sip_trunk_export(data, output=args.output, force=args.force)
            exported_text = output.read_text(encoding="utf-8")
            manage_args = Namespace(
                path=str(project_dir),
                file_path=None,
                json=False,
            )

            loaded = load_manage_config(
                load_project(manage_args.path),
                file_path=manage_args.file_path,
            )

        self.assertEqual(loaded.region, "uk-1")
        self.assertEqual(loaded.account_id, "acct-123")
        self.assertEqual(loaded.trunks, data["sip_trunks"])
        self.assertTrue(exported_text.startswith("- id: tr-123\n"))
        self.assertNotIn("sip_trunks:", exported_text)
        self.assertNotIn("account_id:", exported_text)

    def test_export_writes_explicit_nulls_without_changing_generic_yaml_formatting(self):
        self.assertEqual(dump_yaml({"value": None}), "value:\n")
        data = {
            "account_id": "acct-123",
            "sip_trunks": [{
                "id": "tr-123", "name": "Primary carrier",
                "default_route": None, "outbound": None,
            }],
        }
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            output = project_dir / "sip-trunks.yaml"
            args = Namespace(path=str(project_dir), output=str(output), force=False)

            project = load_project(args.path)
            project.write_sip_trunk_export(data, output=args.output, force=args.force)

            exported = output.read_text(encoding="utf-8")
            self.assertIn("default_route: null\n", exported)
            self.assertIn("outbound: null\n", exported)
            self.assertEqual(load_yaml(exported), data["sip_trunks"])
            self.assertEqual(load_manage_config(load_project(str(project_dir))).trunks, data["sip_trunks"])

            # Blank values remain a valid spelling of null in user-authored files.
            output.write_text(exported.replace(": null\n", ":\n"), encoding="utf-8")
            self.assertEqual(load_manage_config(load_project(str(project_dir))).trunks, data["sip_trunks"])

        self.assertEqual(dump_yaml({"value": None}), "value:\n")

    @patch("getpass.getpass")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_preview_validates_extensions_before_prompting_or_writing(
        self, list_trunks, prompt
    ):
        list_trunks.return_value = {"sip_trunks": []}
        with TemporaryDirectory() as temp_dir:
            self._write_project_config(Path(temp_dir))
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
                json=False,
                rotate_auth=None,
            )

            with self.assertRaisesRegex(ValueError, "missing required field.*agent_id"):
                project = load_project(args.path, output_json=args.json)
                project.build_sip_trunk_plan(file_path=args.file_path)

        prompt.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_preview_shows_extension_removed_from_present_list(
        self, list_trunks, list_extensions
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
            self._write_project_config(Path(temp_dir))
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
                json=False,
                rotate_auth=None,
            )

            project = load_project(args.path, output_json=args.json)
            plan = project.build_sip_trunk_plan(file_path=args.file_path)
            changes = [change.as_dict() for change in plan.changes]

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

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "create_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_creates_trunk_and_reports_hostname(
        self, list_trunks, create_trunk, list_extensions
    ):
        list_trunks.return_value = {"sip_trunks": []}
        create_trunk.return_value = {
            "id": "tr-123",
            "account_id": "acct-123",
            "name": "Primary carrier",
            "inbound": {"hostname": "tr-123.sbc.sip.uk.poly.ai"},
            "created_at": "2026-08-12T12:00:00Z",
            "updated_at": "2026-08-12T12:01:00Z",
        }
        list_extensions.return_value = {"extensions": []}

        with TemporaryDirectory() as temp_dir:
            account_dir = Path(temp_dir) / "acct-123"
            self._write_project_config(account_dir, account_id="acct-123")
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
                json=False,
            )

            project = load_project(args.path, output_json=args.json)
            plan = project.build_sip_trunk_plan(
                file_path=args.file_path, rotate_auth=getattr(args, "rotate_auth", None)
            )
            result = project.apply_sip_trunk_plan(
                plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
            )
            saved_config = config_file.read_text(encoding="utf-8")

        create_trunk.assert_called_once_with(
            "uk-1",
            "acct-123",
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

    @patch("getpass.getpass", return_value="rotated-secret")
    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "update_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_rotates_auth_only_when_explicitly_requested(
        self, list_trunks, update_trunk, list_extensions, prompt
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
            account_dir = Path(temp_dir) / "acct-123"
            self._write_project_config(account_dir, account_id="acct-123")
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
                json=False,
                rotate_auth="tr-123",
            )

            project = load_project(args.path, output_json=args.json)
            plan = project.build_sip_trunk_plan(
                file_path=args.file_path, rotate_auth=getattr(args, "rotate_auth", None)
            )
            result = project.apply_sip_trunk_plan(
                plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
            )

        prompt.assert_called_once_with("SIP password for tr-123: ")
        update_trunk.assert_called_once_with(
            "uk-1",
            "acct-123",
            "tr-123",
            {"inbound": {"sip_auth": {"username": "alice", "password": "rotated-secret"}}},
        )
        self.assertEqual(result["trunks"][0]["status"], "updated")

    @patch.object(AgentStudioInterface, "delete_sip_trunk")
    @patch.object(AgentStudioInterface, "update_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_manage_updates_declared_trunk_without_deleting_omitted_trunks(
        self, list_trunks, update_trunk, delete_trunk
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
            account_dir = Path(temp_dir) / "acct-123"
            self._write_project_config(account_dir, account_id="acct-123")
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
                json=False,
            )

            project = load_project(args.path, output_json=args.json)
            plan = project.build_sip_trunk_plan(
                file_path=args.file_path, rotate_auth=getattr(args, "rotate_auth", None)
            )
            result = project.apply_sip_trunk_plan(
                plan, prompt_auth_secret=SIPTrunksCommand._prompt_auth_secret
            )

        update_trunk.assert_called_once_with(
            "uk-1", "acct-123", "tr-managed", {"encrypted": False}
        )
        delete_trunk.assert_not_called()
        self.assertEqual([item["id"] for item in result["trunks"]], ["tr-managed"])
