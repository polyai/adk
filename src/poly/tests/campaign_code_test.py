"""Unit tests for matching and planning campaign code merges on pull.

Copyright PolyAI Limited
"""

import os
import unittest

from poly.resources.outbound_campaign import OutboundCampaignNode
from poly.utils.campaign_code import LocalCampaignCode, claim, plan

ROOT = os.path.join(os.sep, "project")


def _node(node_id: str, name: str, node_type: str, folder: str = "reminders"):
    return OutboundCampaignNode(
        resource_id=f"CMPGN-ONE:{node_id}",
        name=name,
        campaign_folder=folder,
        data={"type": node_type},
    )


def _nodes(*nodes: OutboundCampaignNode) -> dict[str, OutboundCampaignNode]:
    return {node.resource_id: node for node in nodes}


def _path(stem: str, folder: str = "reminders") -> str:
    return os.path.join(ROOT, "outbound_campaigns", folder, "functions", f"{stem}.py")


class RemovedOwnerTest(unittest.TestCase):
    def test_only_a_saved_node_missing_locally_owns_its_saved_file(self):
        saved = _nodes(_node("call-1", "First call", "call"), _node("sms-1", "Text", "sms"))
        local = LocalCampaignCode(kept={"CMPGN-ONE:sms-1": _path("text")})

        self.assertEqual(local.removed_owner(_path("first_call"), saved, ROOT), "CMPGN-ONE:call-1")
        self.assertIsNone(local.removed_owner(_path("text"), saved, ROOT))
        self.assertIsNone(local.removed_owner(_path("stray"), saved, ROOT))


class ClaimTest(unittest.TestCase):
    def test_a_kept_node_claims_the_file_it_reads(self):
        nodes = _nodes(_node("call-1", "First call", "call"))
        local = LocalCampaignCode(kept={"CMPGN-ONE:call-1": _path("dial")})

        self.assertEqual(claim(nodes, nodes, local, ROOT), {"CMPGN-ONE:call-1": _path("dial")})

    def test_a_saved_trigger_missing_locally_claims_the_one_local_trigger(self):
        nodes = _nodes(_node("trigger-1", "Trigger", "trigger"))
        one = LocalCampaignCode(new={_path("start"): "trigger", _path("wait"): "wait"})
        two = LocalCampaignCode(new={_path("start"): "trigger", _path("begin"): "trigger"})
        elsewhere = LocalCampaignCode(new={_path("start", "other"): "trigger"})

        self.assertEqual(claim(nodes, nodes, one, ROOT), {"CMPGN-ONE:trigger-1": _path("start")})
        self.assertEqual(claim(nodes, nodes, two, ROOT), {})
        self.assertEqual(claim(nodes, nodes, elsewhere, ROOT), {})

    def test_a_trigger_new_in_agent_studio_claims_no_local_trigger(self):
        incoming = _nodes(_node("trigger-1", "Trigger", "trigger"))
        local = LocalCampaignCode(new={_path("start"): "trigger"})

        self.assertEqual(claim(incoming, {}, local, ROOT), {})

    def test_a_node_added_locally_at_the_same_path_is_claimed_only_by_its_type(self):
        incoming = _nodes(_node("call-1", "Dial", "call"))

        for node_type, expected in (("call", {"CMPGN-ONE:call-1": _path("dial")}), ("sms", {})):
            with self.subTest(node_type=node_type):
                local = LocalCampaignCode(new={_path("dial"): node_type})
                self.assertEqual(claim(incoming, incoming, local, ROOT), expected)

    def test_trigger_heirs_are_resolved_before_path_claims_in_any_order(self):
        """Locally First call became Dial and Trigger became First call."""
        trigger = _node("trigger-1", "Trigger", "trigger")
        call = _node("call-1", "First call", "call")
        local = LocalCampaignCode(new={_path("dial"): "call", _path("first_call"): "trigger"})

        for nodes in (_nodes(trigger, call), _nodes(call, trigger)):
            with self.subTest(order=list(nodes)):
                self.assertEqual(
                    claim(nodes, nodes, local, ROOT),
                    {"CMPGN-ONE:trigger-1": _path("first_call")},
                )


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.saved = _nodes(_node("trigger-1", "Trigger", "trigger"))

    def _plan(self, remote_name: str, local_stem: str, force: bool = False) -> list[str]:
        incoming = _nodes(_node("trigger-1", remote_name, "trigger"))
        claimed = {"CMPGN-ONE:trigger-1": _path(local_stem)}
        return plan(incoming, self.saved, claimed, ROOT, force)["CMPGN-ONE:trigger-1"]

    def test_force_writes_only_the_incoming_file(self):
        self.assertEqual(self._plan("Trigger", "start", force=True), [_path("trigger")])
        self.assertEqual(self._plan("Begin", "start", force=True), [_path("begin")])

    def test_a_rename_on_one_side_writes_that_side_file(self):
        self.assertEqual(self._plan("Trigger", "start"), [_path("start")])
        self.assertEqual(self._plan("Begin", "trigger"), [_path("begin")])
        self.assertEqual(self._plan("Begin", "begin"), [_path("begin")])

    def test_different_renames_on_each_side_write_both_files(self):
        self.assertEqual(self._plan("Begin", "start"), [_path("begin"), _path("start")])

    def test_a_node_new_or_unclaimed_writes_its_incoming_file(self):
        incoming = _nodes(_node("call-1", "Dial", "call"))

        self.assertEqual(plan(incoming, {}, {}, ROOT, False), {"CMPGN-ONE:call-1": [_path("dial")]})


if __name__ == "__main__":
    unittest.main()
