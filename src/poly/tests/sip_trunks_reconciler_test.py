"""Tests for SIP trunk planning and reconciliation.

Copyright PolyAI Limited
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from poly.handlers.interface import AgentStudioInterface
from poly.sip_trunks.config import file_digest
from poly.sip_trunks.reconciler import (
    apply_manage_plan,
    build_manage_plan,
    export_config,
    managed_trunk_data,
    normalized_extensions,
)


class SIPTrunkReconcilerTest(unittest.TestCase):
    @patch.object(AgentStudioInterface, "delete_sip_trunk_extension")
    @patch.object(AgentStudioInterface, "update_sip_trunk_extension")
    @patch.object(AgentStudioInterface, "create_sip_trunk_extension")
    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "update_sip_trunk")
    @patch.object(AgentStudioInterface, "create_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
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
                "outbound": None,
                "default_route": None,
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

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
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
                    "outbound": None,
                    "default_route": None,
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

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
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
            [{"outbound": None, "default_route": None, "id": "tr-123", "name": "Primary carrier"}],
        )

        list_extensions.assert_not_called()
        self.assertEqual(plan.trunks[0].extension_operations, ())
        self.assertEqual(plan.trunks[0].extensions_total, 0)

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_all_local_entries_are_validated_before_remote_discovery(self, list_trunks):
        desired = [
            {
                "outbound": None,
                "default_route": None,
                "name": "Valid trunk",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
            {
                "outbound": None,
                "default_route": None,
                "name": "Invalid trunk",
                "sip_cidr": ["192.0.2.0/24"],
                "rtp_cidr": ["192.0.2.0/24"],
                "extensions": [{"extension": "1000", "client_env": "live"}],
            },
        ]

        with self.assertRaisesRegex(ValueError, "missing required field.*agent_id"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": []})
    def test_plan_requires_but_never_contains_a_digest_password(self, _list_trunks):
        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [
                {
                    "outbound": None,
                    "default_route": None,
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

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_legacy_inbound_auth_is_rejected_before_remote_discovery(self, list_trunks):
        configs = [
            {"inbound": {"sip_auth": {"username": "alice"}}},
            {"inbound": {"sip_token_auth": {}}},
            {"inbound": {}},
            {"inbound": None},
            {
                "inbound": {"sip_auth": {"username": "alice"}},
                "inbound_auth": {"type": "none"},
            },
        ]
        for config in configs:
            with self.subTest(config=config):
                with self.assertRaisesRegex(
                    ValueError, "must use 'inbound_auth'.*instead of 'inbound'"
                ):
                    build_manage_plan(
                        "/account/sip-trunks.yaml",
                        "uk-1",
                        "acct-123",
                        [{"outbound": None, "default_route": None, "name": "Primary carrier", **config}],
                    )
                list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_extension_mappings_are_rejected_before_remote_discovery(self, list_trunks):
        for extensions in (
            {"1000": {"agent_id": "agent-one", "client_env": "live"}},
            {"1000": "agent-one"},
            {},
        ):
            with self.subTest(extensions=extensions):
                with self.assertRaisesRegex(
                    ValueError, "'extensions' must be a list of extension mappings"
                ):
                    build_manage_plan(
                        "/account/sip-trunks.yaml",
                        "uk-1",
                        "acct-123",
                        [{"outbound": None, "default_route": None, "name": "Primary carrier", "extensions": extensions}],
                    )
                list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_empty_extension_list_schedules_all_bindings_for_deletion(
        self, list_trunks, list_extensions
    ):
        list_trunks.return_value = {
            "sip_trunks": [{"id": "tr-123", "name": "Primary carrier", "inbound": {}}]
        }
        list_extensions.return_value = {
            "extensions": [
                {
                    "extension": extension,
                    "agent": {"agent_id": "agent-one", "client_env": "live"},
                }
                for extension in ("1000", "2000")
            ]
        }

        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [{"outbound": None, "default_route": None, "id": "tr-123", "name": "Primary carrier", "extensions": []}],
        )

        self.assertEqual(
            [
                (operation.action, operation.extension)
                for operation in plan.trunks[0].extension_operations
            ],
            [("delete", "1000"), ("delete", "2000")],
        )
        self.assertEqual(plan.trunks[0].extensions_total, 0)

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
                        {
                            "outbound": None,
                            "default_route": None,
                            "inbound_auth": {"type": "none", secret_field: "secret"},
                        },
                        create=False,
                    )

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_duplicate_trunk_ids_are_rejected_before_remote_discovery(self, list_trunks):
        desired = [
            {"outbound": None, "default_route": None, "id": "tr-123", "name": "First"},
            {"outbound": None, "default_route": None, "id": "tr-123", "name": "Second"},
        ]

        with self.assertRaisesRegex(ValueError, "ID 'tr-123'.*more than once"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_duplicate_idless_trunk_names_are_rejected_before_remote_discovery(self, list_trunks):
        desired = [
            {
                "outbound": None,
                "default_route": None,
                "name": "Primary carrier",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
            {
                "outbound": None,
                "default_route": None,
                "name": "Primary carrier",
                "sip_cidr": ["192.0.2.0/24"],
                "rtp_cidr": ["192.0.2.0/24"],
            },
        ]

        with self.assertRaisesRegex(ValueError, "name 'Primary carrier'.*more than once"):
            build_manage_plan("/account/sip-trunks.yaml", "uk-1", "acct-123", desired)

        list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": []})
    def test_unknown_remote_trunk_id_explains_how_to_update_config(self, _list_trunks):
        with self.assertRaises(ValueError) as context:
            build_manage_plan(
                "/account/sip-trunks.yaml",
                "uk-1",
                "acct-123",
                [{"outbound": None, "default_route": None, "id": "tr-deleted", "name": "Deleted trunk"}],
            )

        self.assertEqual(
            str(context.exception),
            "SIP trunk 'tr-deleted' references unknown remote ID 'tr-deleted'. "
            "If the trunk was deleted, remove its entry from sip-trunks.yaml.",
        )

    @patch.object(AgentStudioInterface, "list_sip_trunks")
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
                    {"outbound": None, "default_route": None, "id": "tr-123", "name": "New name"},
                    {
                        "outbound": None,
                        "default_route": None,
                        "name": "Old name",
                        "sip_cidr": ["203.0.113.0/24"],
                        "rtp_cidr": ["198.51.100.0/24"],
                    },
                ],
            )

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    @patch.object(AgentStudioInterface, "list_sip_trunks")
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
                        "outbound": None,
                        "default_route": None,
                        "id": "tr-123",
                        "name": "Primary carrier",
                        "extensions": [],
                    }
                ],
            )

    @patch.object(AgentStudioInterface, "create_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": []})
    def test_apply_rejects_yaml_changed_since_preview(self, _list_trunks, create_trunk):
        with TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "sip-trunks.yaml"
            config_path.write_text(
                "- name: Primary carrier\n  default_route: null\n  outbound: null\n", encoding="utf-8"
            )
            plan = build_manage_plan(
                str(config_path),
                "uk-1",
                "acct-123",
                [
                    {
                        "outbound": None,
                        "default_route": None,
                        "name": "Primary carrier",
                        "sip_cidr": ["203.0.113.0/24"],
                        "rtp_cidr": ["198.51.100.0/24"],
                    }
                ],
                source_digest=file_digest(str(config_path)),
            )
            config_path.write_text(
                "- name: Changed carrier\n  default_route: null\n  outbound: null\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "changed after.*preview"):
                apply_manage_plan(
                    plan,
                    prompt_auth_secret=MagicMock(),
                    persist_trunk_response=MagicMock(),
                )

        create_trunk.assert_not_called()

    @patch.object(AgentStudioInterface, "create_sip_trunk")
    @patch.object(AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": []})
    def test_all_credentials_are_collected_before_remote_mutation(self, _list_trunks, create_trunk):
        plan = build_manage_plan(
            "/account/sip-trunks.yaml",
            "uk-1",
            "acct-123",
            [
                {
                    "outbound": None,
                    "default_route": None,
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


class SIPTrunkDefaultRouteTest(unittest.TestCase):
    @staticmethod
    def _current(route=None, auth=None):
        inbound = {}
        if route is not None:
            inbound["default_route"] = {"agent": route}
        if auth:
            inbound.update(auth)
        return {
            "id": "tr-123",
            "name": "Primary carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
            "encrypted": True,
            "inbound": inbound,
        }

    def _plan(self, current, route, *, rotate=False, **config):
        with patch.object(
            AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": [current]}
        ):
            return build_manage_plan(
                "/project/sip-trunks.yaml", "uk-1", "acct-123",
                [{"outbound": None, "id": "tr-123", "name": "Primary carrier", "default_route": route, **config}],
                rotate_auth="tr-123" if rotate else None,
            )

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_every_trunk_requires_default_route_before_remote_discovery(self, list_trunks):
        for missing_index in (0, 1):
            for identified in (False, True):
                with self.subTest(missing_index=missing_index, identified=identified):
                    missing = {
                        "name": "Missing route",
                        "outbound": None,
                        "sip_cidr": ["203.0.113.0/24"],
                        "rtp_cidr": ["198.51.100.0/24"],
                    }
                    if identified:
                        missing["id"] = "tr-123"
                    valid = {**missing, "name": "Valid route", "default_route": None}
                    valid.pop("id", None)
                    trunks = [missing, valid] if missing_index == 0 else [valid, missing]

                    with self.assertRaisesRegex(ValueError, "missing required field 'default_route'"):
                        build_manage_plan("/project/sip-trunks.yaml", "uk-1", "acct-123", trunks)

                    list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_invalid_default_routes_are_rejected_before_remote_discovery(self, list_trunks):
        valid = {"agent_id": "agent-one", "client_env": "live"}
        invalid_routes = (
            False, "agent-one", [], {}, {"agent": valid}, {"disable": True},
            {"agent_id": "agent-one"}, {"client_env": "live"},
            {**valid, "agent_id": "  "}, {**valid, "agent_id": 123},
            {**valid, "agent_id": "a" * 256}, {**valid, "client_env": "pre_release"},
            {**valid, "variant_id": None}, {**valid, "variant_id": "v" * 256},
            {**valid, "unknown": "value"},
        )
        for route in invalid_routes:
            with self.subTest(route=route):
                with self.assertRaisesRegex(ValueError, "[Dd]efault[_ ]route"):
                    build_manage_plan(
                        "/project/sip-trunks.yaml", "uk-1", "acct-123",
                        [{"outbound": None, "name": "Primary carrier", "default_route": route}],
                    )
                list_trunks.assert_not_called()

    def test_route_only_changes_are_applied_without_resending_authentication(self):
        target = {"agent_id": "agent-new", "client_env": "pre-release", "variant_id": "variant-1"}
        auth = {"sip_auth": {"enabled": True, "username": "alice"}}
        for previous in (None, {"agent_id": "agent-old", "client_env": "live"}):
            with self.subTest(previous=previous):
                current = self._current(previous, auth)
                plan = self._plan(
                    current, target, inbound_auth={"type": "digest", "username": "alice"}
                )
                expected = {"inbound": {"default_route": {"agent": target}}}
                self.assertEqual(plan.trunks[0].payload, expected)
                self.assertFalse(plan.trunks[0].credential_required)
                self.assertEqual(len(plan.changes), 1)
                self.assertIn("default route", plan.changes[0].diff)
                self.assertNotIn("authentication", plan.changes[0].diff)
                prompt = MagicMock()
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=prompt,
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                update.assert_called_once_with("uk-1", "acct-123", "tr-123", expected)
                prompt.assert_not_called()

    def test_null_route_clears_existing_route_but_is_noop_when_absent(self):
        existing = {"agent_id": "agent-one", "client_env": "live"}
        for previous in (existing, None):
            with self.subTest(previous=previous):
                current = self._current(previous)
                plan = self._plan(current, None)
                prompt = MagicMock()
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=prompt,
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                if previous:
                    update.assert_called_once_with(
                        "uk-1", "acct-123", "tr-123",
                        {"inbound": {"default_route": {"disable": True}}},
                    )
                    self.assertIn("default route", plan.changes[0].diff)
                else:
                    self.assertEqual(plan.changes, ())
                    self.assertEqual(plan.trunks[0].payload, {})
                    update.assert_not_called()
                prompt.assert_not_called()

    def test_authentication_disable_and_route_update_are_both_applied(self):
        target = {"agent_id": "agent-new", "client_env": "live"}
        for auth_field in ("sip_auth", "sip_token_auth"):
            with self.subTest(auth_field=auth_field):
                current = self._current(auth={auth_field: {"enabled": True, "username": "alice"}})
                plan = self._plan(current, target, inbound_auth={"type": "none"})
                expected = {
                    "inbound": {
                        auth_field: {"disable": True},
                        "default_route": {"agent": {**target, "variant_id": ""}},
                    }
                }
                self.assertEqual(plan.trunks[0].payload, expected)
                self.assertEqual(len(plan.changes), 2)
                self.assertTrue(any("authentication" in change.diff for change in plan.changes))
                self.assertTrue(any("default route" in change.diff for change in plan.changes))
                prompt = MagicMock()
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=prompt,
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                update.assert_called_once_with("uk-1", "acct-123", "tr-123", expected)
                prompt.assert_not_called()

    def test_credentials_preserve_route_changes_without_resending_unchanged_routes(self):
        previous = {"agent_id": "agent-old", "client_env": "live"}
        replacement = {"agent_id": "agent-new", "client_env": "sandbox"}
        for auth_type, rotate in (("digest", False), ("digest", True), ("token", True)):
            for route in (previous, replacement, None):
                with self.subTest(auth_type=auth_type, rotate=rotate, route=route):
                    auth_field = "sip_auth" if auth_type == "digest" else "sip_token_auth"
                    secret_field = "password" if auth_type == "digest" else "token"
                    current = self._current(
                        previous, {auth_field: {"enabled": True, "username": "alice"}}
                    )
                    desired_auth = {"type": auth_type}
                    expected_auth = {secret_field: "secret-value"}
                    if auth_type == "digest":
                        desired_auth["username"] = "alice" if rotate else "bob"
                        expected_auth["username"] = desired_auth["username"]
                    plan = self._plan(current, route, rotate=rotate, inbound_auth=desired_auth)
                    expected_inbound = {auth_field: expected_auth}
                    if route != previous:
                        expected_inbound["default_route"] = (
                            {"agent": {**route, "variant_id": ""}}
                            if route is not None else {"disable": True}
                        )

                    def supply_secret(_name, _current, desired, *, rotate):
                        desired["inbound"][auth_field][secret_field] = "secret-value"
                        return True

                    prompt = MagicMock(side_effect=supply_secret)
                    with patch.object(
                        AgentStudioInterface, "update_sip_trunk", return_value=current
                    ) as update:
                        apply_manage_plan(
                            plan, prompt_auth_secret=prompt,
                            persist_trunk_response=MagicMock(return_value=False),
                        )
                    update.assert_called_once_with(
                        "uk-1", "acct-123", "tr-123", {"inbound": expected_inbound}
                    )
                    self.assertEqual(prompt.call_count, 1)
                    self.assertEqual(prompt.call_args.kwargs["rotate"], rotate)
                    self.assertNotIn("secret-value", repr(plan))

    def test_route_declaration_alone_does_not_allow_credential_rotation(self):
        for route in (None, {"agent_id": "agent-one", "client_env": "live"}):
            with self.subTest(route=route):
                with self.assertRaisesRegex(ValueError, "[Dd]igest or token authentication"):
                    self._plan(self._current(), route, rotate=True)

    def test_default_route_variant_is_part_of_the_complete_target(self):
        target = {"agent_id": "agent-one", "client_env": "live"}
        for current_fields, desired_fields, changed in (
            ({}, {}, False),
            ({"variant_id": None}, {}, False),
            ({"variant_id": ""}, {}, False),
            ({}, {"variant_id": ""}, False),
            ({"variant_id": "blue"}, {}, True),
            ({"variant_id": "blue"}, {"variant_id": "green"}, True),
        ):
            with self.subTest(current=current_fields, desired=desired_fields):
                desired = {**target, **desired_fields}
                plan = self._plan(self._current({**target, **current_fields}), desired)
                if changed:
                    self.assertEqual(
                        plan.trunks[0].payload,
                        {"inbound": {"default_route": {"agent": {"variant_id": "", **desired}}}},
                    )
                    self.assertTrue(plan.changes)
                else:
                    self.assertEqual(plan.trunks[0].payload, {})
                    self.assertEqual(plan.changes, ())

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions", return_value={"extensions": []})
    def test_exported_routes_and_null_reconcile_without_changes(self, _list_extensions):
        for route in (None, {"agent_id": "agent-one", "client_env": "live", "variant_id": "blue"}):
            with self.subTest(route=route):
                current = self._current(route)
                with patch.object(
                    AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": [current]}
                ):
                    exported = export_config("uk-1", "acct-123")
                    self.assertIn("default_route", exported["sip_trunks"][0])
                    self.assertEqual(exported["sip_trunks"][0]["default_route"], route)
                    plan = build_manage_plan(
                        "/project/sip-trunks.yaml", "uk-1", "acct-123", exported["sip_trunks"]
                    )
                self.assertEqual(plan.changes, ())
                self.assertEqual(plan.trunks[0].payload, {})

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions")
    def test_omitted_extension_variant_still_leaves_existing_variant_unmanaged(self, list_extensions):
        list_extensions.return_value = {
            "extensions": [{
                "extension": "1000",
                "agent": {"agent_id": "agent-one", "client_env": "live", "variant_id": "blue"},
            }]
        }
        plan = self._plan(
            self._current(), None,
            extensions=[{"extension": "1000", "agent_id": "agent-one", "client_env": "live"}],
        )

        self.assertEqual(plan.changes, ())
        self.assertEqual(plan.trunks[0].extension_operations, ())


class SIPTrunkOutboundTest(unittest.TestCase):
    @staticmethod
    def _current(**fields):
        return {
            "id": "tr-123",
            "name": "Primary carrier",
            "sip_cidr": ["203.0.113.0/24"],
            "rtp_cidr": ["198.51.100.0/24"],
            "encrypted": True,
            "inbound": {},
            **fields,
        }

    def _plan(self, current, outbound, *, rotate=False, **config):
        with patch.object(
            AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": [current]}
        ):
            return build_manage_plan(
                "/project/sip-trunks.yaml", "uk-1", "acct-123",
                [{
                    "id": "tr-123", "name": "Primary carrier",
                    "default_route": None, "outbound": outbound, **config,
                }],
                rotate_auth="tr-123" if rotate else None,
            )

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_every_trunk_requires_outbound_before_remote_discovery(self, list_trunks):
        for missing_index in (0, 1):
            for identified in (False, True):
                with self.subTest(missing_index=missing_index, identified=identified):
                    missing = {
                        "name": "Missing outbound", "default_route": None,
                        "sip_cidr": ["203.0.113.0/24"], "rtp_cidr": ["198.51.100.0/24"],
                    }
                    if identified:
                        missing["id"] = "tr-123"
                    valid = {**missing, "name": "Valid outbound", "outbound": None}
                    valid.pop("id", None)
                    trunks = [missing, valid] if missing_index == 0 else [valid, missing]
                    with self.assertRaisesRegex(ValueError, "missing required field 'outbound'"):
                        build_manage_plan("/project/sip-trunks.yaml", "uk-1", "acct-123", trunks)
                    list_trunks.assert_not_called()

    @patch.object(AgentStudioInterface, "list_sip_trunks")
    def test_invalid_outbound_is_rejected_before_remote_discovery(self, list_trunks):
        valid = {"sip_addresses": ["sip:carrier.example.com"]}
        invalid = [
            False, "sip:carrier.example.com", [], {}, {"disable": True},
            {"default_caller_id": "+442012345678"},
            {"sip_addresses": None}, {"sip_addresses": []},
            {"sip_addresses": "sip:carrier.example.com"},
            {"sip_addresses": ["sip:carrier.example.com"] * 5},
            {**valid, "default_caller_id": None}, {**valid, "default_caller_id": 123},
            {**valid, "default_caller_id": "1" * 129}, {**valid, "unknown": "value"},
        ]
        invalid.extend({"sip_addresses": [address]} for address in (
            None, 123, "https://carrier.example.com", "sip:", "sip::5060",
            "sip:;transport=tcp", "sip:user@carrier.example.com",
            "sip:carrier.example.com ", "sip:carrier.example.com\n",
            "sip:" + "a" * 252,
        ))
        for outbound in invalid:
            with self.subTest(outbound=outbound):
                with self.assertRaisesRegex(ValueError, "outbound"):
                    build_manage_plan(
                        "/project/sip-trunks.yaml", "uk-1", "acct-123",
                        [{"name": "Primary carrier", "default_route": None, "outbound": outbound}],
                    )
                list_trunks.assert_not_called()

    def test_outbound_creation_preserves_addresses_and_defaults_caller_id(self):
        addresses = [
            "sips:secure.example.com:5061", "sip:plain.example.com:5060;transport=tcp",
            "sip:[2001:db8::1]:5060", "sip:backup.example.com",
        ]
        payload = managed_trunk_data(
            "Primary carrier",
            {
                "default_route": None, "outbound": {"sip_addresses": addresses},
                "sip_cidr": ["203.0.113.0/24"], "rtp_cidr": ["198.51.100.0/24"],
            },
            create=True,
        )
        self.assertEqual(payload["outbound"], {
            "sip_addresses": addresses, "default_caller_id": "",
        })
        self.assertNotIn("inbound", payload)

    def test_updates_only_changed_outbound_fields(self):
        old_addresses = ["sip:old.example.com"]
        new_addresses = ["sips:second.example.com", "sip:first.example.com"]
        current = self._current(outbound={
            "sip_addresses": old_addresses, "default_caller_id": "+442012345678",
        })
        cases = (
            ({"sip_addresses": new_addresses, "default_caller_id": "+442012345678"},
             {"sip_addresses": new_addresses}),
            ({"sip_addresses": old_addresses, "default_caller_id": "+442087654321"},
             {"default_caller_id": "+442087654321"}),
            ({"sip_addresses": old_addresses}, {"default_caller_id": ""}),
        )
        for outbound, expected in cases:
            with self.subTest(outbound=outbound):
                plan = self._plan(current, outbound)
                self.assertEqual(plan.trunks[0].payload, {"outbound": expected})
                self.assertTrue(any("outbound" in change.diff for change in plan.changes))
                self.assertFalse(plan.trunks[0].credential_required)
                prompt = MagicMock()
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=prompt,
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                update.assert_called_once_with("uk-1", "acct-123", "tr-123", {"outbound": expected})
                prompt.assert_not_called()

    def test_null_outbound_clears_settings_but_does_not_write_when_already_disabled(self):
        states = (
            ({}, False), ({"outbound": None}, False), ({"outbound": {}}, False),
            ({"outbound": {"sip_addresses": [], "default_caller_id": ""}}, False),
            ({"outbound": {"sip_addresses": ["sip:carrier.example.com"]}}, True),
            ({"outbound": {"default_caller_id": "+442012345678"}}, True),
        )
        for fields, changed in states:
            with self.subTest(fields=fields):
                current = self._current(**fields)
                plan = self._plan(current, None)
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=MagicMock(),
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                if changed:
                    update.assert_called_once_with(
                        "uk-1", "acct-123", "tr-123", {"outbound": {"sip_addresses": []}},
                    )
                    self.assertTrue(plan.changes)
                else:
                    update.assert_not_called()
                    self.assertEqual(plan.trunks[0].payload, {})
                    self.assertEqual(plan.changes, ())

    def test_address_order_duplicates_and_absent_caller_id_do_not_cause_updates(self):
        addresses = ["sip:first.example.com", "sip:second.example.com"]
        for caller_fields in ({}, {"default_caller_id": ""}):
            for desired_addresses in (addresses, addresses[::-1], [*addresses, addresses[0]]):
                with self.subTest(caller_fields=caller_fields, addresses=desired_addresses):
                    current = self._current(outbound={"sip_addresses": addresses, **caller_fields})
                    plan = self._plan(current, {"sip_addresses": desired_addresses})
                    self.assertEqual(plan.trunks[0].payload, {})
                    self.assertEqual(plan.changes, ())

    def test_outbound_and_route_changes_survive_credential_rotation(self):
        existing = {"sip_addresses": ["sip:old.example.com"], "default_caller_id": "+442012345678"}
        replacement = {"sip_addresses": ["sip:new.example.com"], "default_caller_id": "+442012345678"}
        target = {"agent_id": "agent-new", "client_env": "live", "variant_id": ""}
        for outbound, expected_outbound in (
            (existing, None), (replacement, {"sip_addresses": replacement["sip_addresses"]}),
            (None, {"sip_addresses": []}),
        ):
            with self.subTest(outbound=outbound):
                current = self._current(outbound=existing, inbound={
                    "sip_auth": {"enabled": True, "username": "alice"},
                })
                plan = self._plan(
                    current, outbound, rotate=True, default_route=target,
                    inbound_auth={"type": "digest", "username": "alice"},
                )

                def supply_secret(_name, _current, desired, *, rotate):
                    desired["inbound"]["sip_auth"]["password"] = "secret-value"
                    return True

                prompt = MagicMock(side_effect=supply_secret)
                expected = {"inbound": {
                    "sip_auth": {"username": "alice", "password": "secret-value"},
                    "default_route": {"agent": target},
                }}
                if expected_outbound is not None:
                    expected["outbound"] = expected_outbound
                with patch.object(
                    AgentStudioInterface, "update_sip_trunk", return_value=current
                ) as update:
                    apply_manage_plan(
                        plan, prompt_auth_secret=prompt,
                        persist_trunk_response=MagicMock(return_value=False),
                    )
                update.assert_called_once_with("uk-1", "acct-123", "tr-123", expected)
                prompt.assert_called_once()
                self.assertNotIn("secret-value", repr(plan))

    @patch.object(AgentStudioInterface, "list_sip_trunk_extensions", return_value={"extensions": []})
    def test_exported_outbound_configuration_reconciles_without_changes(self, _list_extensions):
        addresses = ["sip:first.example.com", "sip:second.example.com"]
        states = (
            ({}, None), ({"outbound": None}, None),
            ({"outbound": {"sip_addresses": [], "default_caller_id": ""}}, None),
            ({"outbound": {"sip_addresses": addresses}}, {"sip_addresses": addresses}),
            ({"outbound": {"sip_addresses": addresses, "default_caller_id": ""}},
             {"sip_addresses": addresses}),
            ({"outbound": {"sip_addresses": addresses, "default_caller_id": "+442012345678"}},
             {"sip_addresses": addresses, "default_caller_id": "+442012345678"}),
        )
        for fields, expected in states:
            with self.subTest(fields=fields):
                current = self._current(**fields)
                with patch.object(
                    AgentStudioInterface, "list_sip_trunks", return_value={"sip_trunks": [current]}
                ):
                    exported = export_config("uk-1", "acct-123")
                    self.assertEqual(exported["sip_trunks"][0]["outbound"], expected)
                    plan = build_manage_plan(
                        "/project/sip-trunks.yaml", "uk-1", "acct-123", exported["sip_trunks"],
                    )
                self.assertEqual(plan.trunks[0].payload, {})
                self.assertEqual(plan.changes, ())


if __name__ == "__main__":
    unittest.main()
