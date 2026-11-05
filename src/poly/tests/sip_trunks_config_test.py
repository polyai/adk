"""Tests for SIP trunk configuration discovery and persistence.

Copyright PolyAI Limited
"""

import unittest
from argparse import Namespace
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory

from poly.resources.resource_utils import dump_yaml, load_yaml
from poly.sip_trunks.config import (
    default_export_path,
    find_manage_file,
    load_manage_config,
    persist_trunk_response,
    resolve_account_context,
    validate_sip_trunk_region,
)


class SIPTrunksConfigTest(unittest.TestCase):
    """Configuration discovery, validation and YAML metadata persistence."""

    @staticmethod
    def _write_project_config(path, account_id="acct-123", region="uk-1"):
        path.mkdir(parents=True, exist_ok=True)
        (path / "project.yaml").write_text(
            f"project_id: {path.name}\naccount_id: {account_id}\nregion: {region}\n",
            encoding="utf-8",
        )
        return path

    def test_sip_region_validation_rejects_noncanonical_and_unsupported_regions(self):
        regions = (
            "eu", "uk", "us", "EUW-1", "UK-1", "US-1", "studio", "staging", "dev", "unknown"
        )
        for region in regions:
            with self.subTest(region=region):
                with self.assertRaisesRegex(ValueError, "Unsupported SIP Trunking region"):
                    validate_sip_trunk_region(region)

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

            with self.assertRaisesRegex(ValueError, "No project configuration found.*--path"):
                resolve_account_context(str(account_dir))

    def test_context_accepts_supported_regions_from_project_metadata(self):
        with TemporaryDirectory() as temp_dir:
            for region in ("us-1", "euw-1", "uk-1"):
                with self.subTest(region=region):
                    project_dir = self._write_project_config(Path(temp_dir) / region, region=region)
                    context = resolve_account_context(str(project_dir))
                    self.assertEqual((context.region, context.account_id), (region, "acct-123"))

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

    def test_manage_requires_a_project_even_with_an_explicit_file(self):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sip-trunks.yaml"
            config_path.write_text("[]\n", encoding="utf-8")

            for file_path in (None, str(config_path)):
                with self.subTest(file_path=file_path):
                    with self.assertRaisesRegex(ValueError, "No project configuration found.*--path"):
                        load_manage_config(temp_dir, file_path=file_path)

    def test_default_export_uses_project_root_from_nested_directory(self):
        with TemporaryDirectory() as temp_dir:
            project_dir = self._write_project_config(Path(temp_dir) / "project")
            nested_dir = project_dir / "flows" / "greeting"
            nested_dir.mkdir(parents=True)

            result = default_export_path(str(nested_dir))

        self.assertEqual(result, str(project_dir / "sip-trunks.yaml"))

    def test_default_export_requires_a_project(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "No project configuration found.*--path"):
                default_export_path(temp_dir)

    def test_manage_rejects_region_in_yaml(self):
        with TemporaryDirectory() as temp_dir:
            self._write_project_config(Path(temp_dir))
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            config_file.write_text("region: uk-1\nsip_trunks: []\n", encoding="utf-8")
            args = Namespace(
                path=temp_dir,
                file_path=str(config_file),
                json=False,
            )

            with self.assertRaisesRegex(ValueError, "Do not set 'region'"):
                load_manage_config(
                    args.path,
                    file_path=args.file_path,
                )

    def test_manage_rejects_wrapped_and_non_list_formats(self):
        with TemporaryDirectory() as temp_dir:
            self._write_project_config(Path(temp_dir))
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
                        )

    def test_empty_manage_files_declare_no_trunks(self):
        with TemporaryDirectory() as temp_dir:
            self._write_project_config(Path(temp_dir))
            config_file = Path(temp_dir) / "sip-trunks.yaml"
            for source in ("", "# No trunks managed\n", "[]\n"):
                with self.subTest(source=source):
                    config_file.write_text(source, encoding="utf-8")
                    loaded = load_manage_config(
                        temp_dir, file_path=str(config_file)
                    )
                    self.assertEqual(loaded.trunks, [])

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
        self.assertEqual(dump_yaml({"value": None}), "value:\n")
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
  extensions:
    - extension: "0010"  # Keep the leading zeroes
      agent_id: my-project
      client_env: live
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
        self.assertIn("default_route: null\n", saved)
        self.assertIn("outbound: null\n", saved)
        self.assertIn('extension: "0010"', saved)
        self.assertIn("# Keep the leading zeroes", saved)
        self.assertIsNone(load_yaml(saved)[0]["default_route"])
        self.assertIsNone(load_yaml(saved)[0]["outbound"])
        self.assertIn("id: tr-123", saved)
        self.assertIn("hostname: tr-123.sbc.sip.uk.poly.ai", saved)
        self.assertIn("realm: sbc.sip.uk.poly.ai", saved)
        self.assertNotIn("created_at", saved)
        self.assertNotIn("updated_at", saved)
        self.assertEqual(dump_yaml({"value": None}), "value:\n")
