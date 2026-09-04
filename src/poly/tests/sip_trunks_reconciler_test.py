"""Tests for SIP trunk planning and reconciliation.

Copyright PolyAI Limited
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from poly.handlers.sip_trunking_api import SIPTrunkingAPIHandler
from poly.sip_trunks.config import file_digest
from poly.sip_trunks.reconciler import (
    apply_manage_plan,
    build_manage_plan,
    managed_trunk_data,
    normalized_extensions,
)


class SIPTrunkReconcilerTest(unittest.TestCase):
    @patch.object(SIPTrunkingAPIHandler, "delete_extension")
    @patch.object(SIPTrunkingAPIHandler, "update_extension")
    @patch.object(SIPTrunkingAPIHandler, "create_extension")
    @patch.object(SIPTrunkingAPIHandler, "list_extensions")
    @patch.object(SIPTrunkingAPIHandler, "update_trunk")
    @patch.object(SIPTrunkingAPIHandler, "create_trunk")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_apply_executes_the_previewed_snapshot_without_listing_again(
        self,
        list_trunks,
        create_trunk,
        update_trunk,
        list_extensions,
        create_extension,
        update_extension,
        delete_extension,
    ):
        trunk = {
            "id": "tr-123",
            "name": "Primary carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
            "encrypted": True,
            "inbound": {"hostname": "tr-123.example"},
        }
        list_trunks.return_value = {"sip_trunks": [trunk]}
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
        desired = [
            {
                "id": "tr-123",
                "name": "Primary carrier",
                "hostname": "tr-123.example",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
                "encrypted": True,
                "extensions": [
                    {
                        "extension": "1000",
                        "agent_id": "agent-one",
                        "client_env": "live",
                    }
                ],
            }
        ]

        plan = build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)
        self.assertEqual(
            [change.as_dict() for change in plan.changes],
            [
                {
                    "action": "delete",
                    "resource": "extension 2000",
                    "diff": "- from trunk tr-123",
                }
            ],
        )

        prompt = MagicMock()
        persist = MagicMock(return_value=False)
        result = apply_manage_plan(
            plan,
            prompt_auth_secret=prompt,
            persist_trunk_response=persist,
        )

        list_trunks.assert_called_once_with("uk-1", "acct-123")
        list_extensions.assert_called_once_with("uk-1", "acct-123", "tr-123")
        delete_extension.assert_called_once_with("uk-1", "acct-123", "tr-123", "2000")
        create_trunk.assert_not_called()
        update_trunk.assert_not_called()
        create_extension.assert_not_called()
        update_extension.assert_not_called()
        prompt.assert_not_called()
        self.assertEqual(result["trunks"][0]["extensions_deleted"], 1)

    @patch.object(SIPTrunkingAPIHandler, "list_extensions")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_unchanged_authoritative_extensions_are_counted(self, list_trunks, list_extensions):
        list_trunks.return_value = {
            "sip_trunks": [
                {
                    "id": "tr-123",
                    "name": "Primary carrier",
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
                    "agent": {"agent_id": "charging-support", "client_env": "live"},
                }
            ]
        }

        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [
                {
                    "id": "tr-123",
                    "name": "Primary carrier",
                    "hostname": "tr-123.example",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "encrypted": True,
                    "extensions": [
                        {
                            "extension": "1000",
                            "agent_id": "charging-support",
                            "client_env": "live",
                        }
                    ],
                }
            ],
        )

        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.trunks[0].extensions_total, 1)
        self.assertEqual(plan.trunks[0].extension_operations, ())

    @patch.object(SIPTrunkingAPIHandler, "list_extensions")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_omitted_extensions_leave_remote_extensions_unmanaged(
        self, list_trunks, list_extensions
    ):
        list_trunks.return_value = {
            "sip_trunks": [{"id": "tr-123", "name": "Primary carrier", "inbound": {}}]
        }

        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [{"id": "tr-123", "name": "Primary carrier"}],
        )

        list_extensions.assert_not_called()
        self.assertEqual(plan.trunks[0].extension_operations, ())
        self.assertEqual(plan.trunks[0].extensions_total, 0)

    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_all_local_entries_are_validated_before_remote_discovery(self, list_trunks):
        desired = [
            {
                "name": "Valid trunk",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
            {
                "name": "Invalid trunk",
                "sip_cidr": ["192.0.2.0/24"],
                "rtp_cidr": ["192.0.2.0/24"],
                "extensions": [{"extension": "1000", "client_env": "live"}],
            },
        ]

        with self.assertRaisesRegex(ValueError, "missing required field.*agent_id"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(SIPTrunkingAPIHandler, "list_trunks", return_value={"sip_trunks": []})
    def test_plan_requires_but_never_contains_a_digest_password(self, _list_trunks):
        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [
                {
                    "name": "Primary carrier",
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "inbound_auth": {"type": "digest", "username": "alice"},
                }
            ],
        )

        operation = plan.trunks[0]
        self.assertTrue(operation.credential_required)
        self.assertEqual(operation.payload["inbound"]["sip_auth"], {"username": "alice"})
        self.assertNotIn("password", repr(plan))

    def test_legacy_extension_mapping_rejects_non_mapping_values(self):
        with self.assertRaisesRegex(ValueError, "Every extension value must be a mapping"):
            normalized_extensions({"1000": "agent-one"})

    def test_extension_number_must_not_be_null_blank_or_boolean(self):
        for extension in (None, "", "  ", False, True):
            with self.subTest(extension=extension):
                with self.assertRaisesRegex(ValueError, "non-empty 'extension'"):
                    normalized_extensions(
                        [
                            {
                                "extension": extension,
                                "agent_id": "agent-one",
                                "client_env": "live",
                            }
                        ]
                    )

    def test_all_secret_fields_are_rejected_for_every_auth_type(self):
        for secret_field in ("password", "password_env", "token", "token_env"):
            with self.subTest(secret_field=secret_field):
                with self.assertRaisesRegex(ValueError, secret_field):
                    managed_trunk_data(
                        "Primary carrier",
                        {"inbound_auth": {"type": "none", secret_field: "secret"}},
                        create=False,
                    )

    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_duplicate_trunk_ids_are_rejected_before_remote_discovery(self, list_trunks):
        desired = [
            {"id": "tr-123", "name": "First"},
            {"id": "tr-123", "name": "Second"},
        ]

        with self.assertRaisesRegex(ValueError, "ID 'tr-123'.*more than once"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_duplicate_idless_trunk_names_are_rejected_before_remote_discovery(self, list_trunks):
        desired = [
            {
                "name": "Primary carrier",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
            {
                "name": "Primary carrier",
                "sip_cidr": ["192.0.2.0/24"],
                "rtp_cidr": ["192.0.2.0/24"],
            },
        ]

        with self.assertRaisesRegex(ValueError, "name 'Primary carrier'.*more than once"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(SIPTrunkingAPIHandler, "list_trunks", return_value={"sip_trunks": []})
    def test_unknown_remote_trunk_id_explains_how_to_update_config(self, _list_trunks):
        with self.assertRaises(ValueError) as context:
            build_manage_plan(
                "/account/sip-trunks.yaml",
                "uk-1",
                "acct-123",
                [{"id": "tr-deleted", "name": "Deleted trunk"}],
            )

        self.assertEqual(
            str(context.exception),
            "SIP trunk 'tr-deleted' references unknown remote ID 'tr-deleted'. "
            "If the trunk was deleted, remove its entry from sip-trunks.yaml.",
        )

    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_remote_trunk_cannot_be_targeted_by_id_and_old_name(self, list_trunks):
        list_trunks.return_value = {
            "sip_trunks": [{"id": "tr-123", "name": "Old name", "inbound": {}}]
        }

        with self.assertRaisesRegex(ValueError, "targeted by more than one YAML entry"):
            build_manage_plan(
                "/account/sip-trunks.yaml",
                "uk-1",
                "acct-123",
                [
                    {"id": "tr-123", "name": "New name"},
                    {
                        "name": "Old name",
                        "sip_cidr": ["203.0.113.0/24"],
                        "rtp_cidr": ["198.51.100.0/24"],
                    },
                ],
            )

    @patch.object(SIPTrunkingAPIHandler, "list_extensions")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks")
    def test_malformed_remote_extension_is_rejected(self, list_trunks, list_extensions):
        list_trunks.return_value = {
            "sip_trunks": [{"id": "tr-123", "name": "Primary carrier", "inbound": {}}]
        }
        list_extensions.return_value = {"extensions": [{"agent": {}}]}

        with self.assertRaisesRegex(ValueError, "missing its extension"):
            build_manage_plan(
                "/account/sip-trunks.yaml",
                "uk-1",
                "acct-123",
                [
                    {
                        "id": "tr-123",
                        "name": "Primary carrier",
                        "extensions": [],
                    }
                ],
            )

    @patch.object(SIPTrunkingAPIHandler, "create_trunk")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks", return_value={"sip_trunks": []})
    def test_apply_rejects_yaml_changed_since_preview(self, _list_trunks, create_trunk):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sip-trunks.yaml"
            config_path.write_text("- name: Primary carrier\n", encoding="utf-8")
            plan = build_manage_plan(
                str(config_path),
                "uk-1",
                "acct-123",
                [
                    {
                        "name": "Primary carrier",
                        "sip_cidr": ["203.0.113.0/24"],
                        "rtp_cidr": ["198.51.100.0/24"],
                    }
                ],
                source_digest=file_digest(str(config_path)),
            )
            config_path.write_text("- name: Changed carrier\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "changed after.*preview"):
                apply_manage_plan(
                    plan,
                    prompt_auth_secret=MagicMock(),
                    persist_trunk_response=MagicMock(),
                )

        create_trunk.assert_not_called()

    @patch.object(SIPTrunkingAPIHandler, "create_trunk")
    @patch.object(SIPTrunkingAPIHandler, "list_trunks", return_value={"sip_trunks": []})
    def test_all_credentials_are_collected_before_remote_mutation(self, _list_trunks, create_trunk):
        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [
                {
                    "name": name,
                    "sip_cidr": ["203.0.113.0/24"],
                    "rtp_cidr": ["198.51.100.0/24"],
                    "inbound_auth": {"type": "digest", "username": "alice"},
                }
                for name in ("Primary carrier", "Backup carrier")
            ],
        )
        prompt = MagicMock(side_effect=[True, False])

        with self.assertRaisesRegex(ValueError, "credential is required"):
            apply_manage_plan(
                plan,
                prompt_auth_secret=prompt,
                persist_trunk_response=MagicMock(),
            )

        self.assertEqual(prompt.call_count, 2)
        create_trunk.assert_not_called()


if __name__ == "__main__":
    unittest.main()
