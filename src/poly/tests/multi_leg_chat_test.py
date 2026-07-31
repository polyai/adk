"""Tests for multi-leg chat supervision.

Copyright PolyAI Limited
"""

import base64
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from poly.cli_commands.multi_leg_chat import (
    DIAL_ID_HEADER,
    PARENT_CONVERSATION_HEADER,
    MultiLegChatSupervisor,
)
from poly.project import AgentStudioProject


def _reply(
    text: str = "",
    *,
    dials: list[dict] = None,
    bridge: dict = None,
    function_events: list[dict] = None,
    ended: bool = False,
) -> dict:
    """Build a compact chat API reply for supervisor tests."""
    return {
        "response": text,
        "conversation_ended": ended,
        "metadata": {
            "agentic_dials": dials,
            "bridge": bridge,
            "function_events": function_events or [],
        },
    }


def _dial(dial_id: str = "dial-1", destination: str = "billing") -> dict:
    """Build a sanitized agentic-dial control instruction."""
    return {
        "dial_id": dial_id,
        "outbound_agent": "brightree-usp-outbound-sandbox",
        "destination": destination,
        "target": {
            "account_id": "brightree-us",
            "project_id": "brightree-usp-outbound",
            "client_env": "sandbox",
            "variant_id": "English",
        },
        "integration_attributes": {"patient_first_name": "Ada"},
        "custom_sip_headers": {"X-Trace": "trace-123"},
    }


class MultiLegChatSupervisorTest(unittest.TestCase):
    """Exercise parent/child lifecycle and bridge routing."""

    def setUp(self) -> None:
        self.parent = MagicMock(spec=AgentStudioProject)
        self.parent.account_id = "brightree-us"
        self.parent.project_id = "brightree-usp"
        self.parent.region = "us-1"
        self.parent.root_path = "/workspace/brightree-usp"
        self.parent.branch_id = "parent-branch"
        self.parent.get_conversation_url.side_effect = (
            lambda conversation_id: f"https://example.com/{conversation_id}"
        )

        self.child = MagicMock(spec=AgentStudioProject)
        self.child.account_id = "brightree-us"
        self.child.project_id = "brightree-usp-outbound"
        self.child.region = "us-1"
        self.child.root_path = "/workspace/brightree-usp-outbound"
        self.child.branch_id = "child-branch"
        self.child.get_conversation_url.side_effect = (
            lambda conversation_id: f"https://example.com/{conversation_id}"
        )

        self.supervisor = MultiLegChatSupervisor(
            project=self.parent,
            environment="draft",
            channel="chat.polyai",
            output_json=True,
        )
        self.project_patcher = patch.object(
            self.supervisor,
            "_resolve_project",
            return_value=(self.child, True),
        )
        self.project_patcher.start()

    def tearDown(self) -> None:
        self.project_patcher.stop()

    def test_dial_starts_local_child_branch_and_answers_parent(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply("Please hold", dials=[_dial()]),
        }
        self.parent.send_message.return_value = _reply("The other line answered")
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply("Hello, this is Ada"),
        }

        _, result = self.supervisor.run(input_messages=[])

        self.assertEqual(result["active_leg"], "dial-1")
        self.assertEqual(self.supervisor.legs["parent"].status, "holding")
        self.assertEqual(self.supervisor.legs["dial-1"].status, "active")
        self.child.create_chat_session.assert_called_once_with(
            "draft",
            "chat.polyai",
            "English",
            None,
            None,
            integration_attributes={"patient_first_name": "Ada"},
            custom_sip_headers={
                "X-Trace": "trace-123",
                PARENT_CONVERSATION_HEADER: "parent-conv",
                DIAL_ID_HEADER: "dial-1",
            },
        )
        answered_event = self.parent.send_message.call_args.kwargs["external_events"][0]
        self.assertEqual(answered_event["ext_event_id"], "dial-1")
        self.assertEqual(json.loads(answered_event["data"])["status"], "answered")

    def test_child_ready_bridges_without_dropping_when_child_response_ends(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply("Please hold", dials=[_dial()]),
        }
        self.parent.send_message.side_effect = [
            _reply("The other line answered"),
            _reply(bridge={"dial_id": "dial-1"}, ended=True),
        ]
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply(
                function_events=[
                    {
                        "agentic_dial": {
                            "messages_to_parent": [{"content": "READY"}],
                        }
                    }
                ],
                ended=True,
            ),
        }

        _, result = self.supervisor.run(input_messages=[])

        self.assertEqual(result["bridged_dial_id"], "dial-1")
        self.assertEqual(self.supervisor.legs["parent"].status, "bridged")
        self.assertEqual(self.supervisor.legs["dial-1"].status, "bridged")
        self.assertFalse(self.supervisor.finished)
        ready_event = self.parent.send_message.call_args_list[1].kwargs["external_events"][0]
        self.assertEqual(json.loads(ready_event["data"]), {"event_type": "message", "content": "READY"})

    def test_child_end_reports_only_that_leg_and_returns_to_parent(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply("Please hold", dials=[_dial()]),
        }
        self.parent.send_message.side_effect = [
            _reply("The other line answered"),
            _reply("I could not reach them"),
        ]
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply(ended=True),
        }

        _, result = self.supervisor.run(input_messages=[])

        self.assertEqual(result["active_leg"], "parent")
        self.assertEqual(self.supervisor.legs["parent"].status, "active")
        self.assertEqual(self.supervisor.legs["dial-1"].status, "ended")
        self.assertFalse(self.supervisor.finished)
        hangup_event = self.parent.send_message.call_args_list[1].kwargs["external_events"][0]
        self.assertEqual(json.loads(hangup_event["data"])["status"], "hangup")

    def test_fail_busy_closes_child_and_keeps_parent_available(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply(dials=[_dial()]),
        }
        self.parent.send_message.side_effect = [
            _reply(),
            _reply("That line is busy"),
        ]
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply(),
        }

        self.supervisor.run(input_messages=["/fail busy"])

        self.child.end_chat.assert_called_once_with("child-conv", "draft")
        self.assertEqual(self.supervisor.legs["dial-1"].status, "failed")
        self.assertEqual(self.supervisor.legs["parent"].status, "active")
        busy_event = self.parent.send_message.call_args_list[1].kwargs["external_events"][0]
        self.assertEqual(json.loads(busy_event["data"])["status"], "busy")

    def test_hangup_after_bridge_triggers_callback_and_closes_both_legs(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply(dials=[_dial()]),
        }
        self.parent.send_message.side_effect = [
            _reply(),
            _reply(bridge={"dial_id": "dial-1"}),
        ]
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply(
                function_events=[
                    {
                        "agentic_dial": {
                            "messages_to_parent": [{"content": "READY"}],
                        }
                    }
                ]
            ),
        }

        self.supervisor.run(input_messages=["/hangup"])

        self.parent.bridge_ended.assert_called_once()
        self.child.end_chat.assert_called_once_with("child-conv", "draft")
        self.parent.end_chat.assert_called_once_with("parent-conv", "draft")
        self.assertTrue(self.supervisor.finished)

    def test_parent_to_child_message_uses_child_inbox(self):
        self.parent.create_chat_session.return_value = {
            "conversation_id": "parent-conv",
            **_reply(dials=[_dial()]),
        }
        self.parent.send_message.return_value = _reply(
            function_events=[
                {
                    "agentic_dial": {
                        "messages_to_children": [
                            {"destination": "billing", "content": "CALLER_HUNG_UP"}
                        ]
                    }
                }
            ]
        )
        self.child.create_chat_session.return_value = {
            "conversation_id": "child-conv",
            **_reply(),
        }
        self.child.send_message.return_value = _reply()

        self.supervisor.run(input_messages=[])

        child_event = self.child.send_message.call_args.kwargs["external_events"][0]
        self.assertEqual(child_event["ext_event_id"], "dial-1:child-inbox")
        self.assertEqual(json.loads(child_event["data"])["content"], "CALLER_HUNG_UP")


class ChildEnvironmentTest(unittest.TestCase):
    """Tests for selecting branch or deployed child environments."""

    def test_parent_draft_prefers_matching_local_child_branch(self):
        project = MagicMock(branch_id="child-branch")

        environment = MultiLegChatSupervisor._child_environment(
            "draft",
            project,
            "sandbox",
            local_project=True,
        )

        self.assertEqual(environment, "draft")

    def test_deployed_parent_uses_connector_environment(self):
        project = MagicMock(branch_id="child-branch")

        environment = MultiLegChatSupervisor._child_environment(
            "live",
            project,
            "prelive",
            local_project=True,
        )

        self.assertEqual(environment, "pre-release")


class LocalProjectDiscoveryTest(unittest.TestCase):
    """Tests for locating a checked-out outbound project beside its parent."""

    def test_resolves_sibling_project_with_its_own_branch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            account_root = Path(temp_dir)
            parent_root = account_root / "brightree-usp"
            child_root = account_root / "brightree-usp-outbound"
            parent_root.mkdir()
            (child_root / "_gen").mkdir(parents=True)
            (child_root / "project.yaml").write_text(
                "project_id: brightree-usp-outbound\n"
                "account_id: brightree-us\n"
                "region: us-1\n",
                encoding="utf-8",
            )
            status = base64.b64encode(
                json.dumps(
                    {
                        "branch_id": "outbound-feature-branch",
                        "resources": {},
                        "migration_flags": [],
                    }
                ).encode()
            )
            (child_root / "_gen" / ".agent_studio_config").write_bytes(status)
            parent = AgentStudioProject(
                region="us-1",
                account_id="brightree-us",
                project_id="brightree-usp",
                root_path=str(parent_root),
                resources={},
                last_updated=datetime.now(),
                branch_id="parent-feature-branch",
            )
            supervisor = MultiLegChatSupervisor(
                project=parent,
                environment="draft",
                channel="chat.polyai",
                output_json=True,
            )

            project, local = supervisor._resolve_project(
                parent,
                {
                    "account_id": "brightree-us",
                    "project_id": "brightree-usp-outbound",
                    "client_env": "sandbox",
                },
            )

            self.assertTrue(local)
            self.assertEqual(project.root_path, str(child_root))
            self.assertEqual(project.branch_id, "outbound-feature-branch")


if __name__ == "__main__":
    unittest.main()
