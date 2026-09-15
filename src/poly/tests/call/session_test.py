"""Tests for the CallSession data model.

Copyright PolyAI Limited
"""

import dataclasses
import unittest

from poly.call.session import DEFAULT_CALL_MODE, CallSession


class CallSessionTest(unittest.TestCase):
    """Tests for the CallSession dataclass."""

    @staticmethod
    def _make(**overrides) -> CallSession:
        fields = {
            "account_id": "acc-1",
            "project_id": "proj-1",
            "variant_id": "",
            "artifact_version": "artifact-v1",
            "lambda_deployment_version": "lambda-v1",
            "auth_token": "studio-token",
            "gateway_ws_url": "wss://gw",
        }
        fields.update(overrides)
        return CallSession(**fields)

    def test_mode_defaults_to_traditional(self):
        # Matches the WebRTC gateway's fallback when LLeMur config can't be resolved.
        self.assertEqual(self._make().mode, DEFAULT_CALL_MODE)
        self.assertEqual(DEFAULT_CALL_MODE, "traditional")

    def test_holds_all_offer_fields(self):
        session = self._make(variant_id="VARIANT-x", mode="echo")
        self.assertEqual(session.account_id, "acc-1")
        self.assertEqual(session.project_id, "proj-1")
        self.assertEqual(session.variant_id, "VARIANT-x")
        self.assertEqual(session.artifact_version, "artifact-v1")
        self.assertEqual(session.lambda_deployment_version, "lambda-v1")
        self.assertEqual(session.auth_token, "studio-token")
        self.assertEqual(session.gateway_ws_url, "wss://gw")
        self.assertEqual(session.mode, "echo")

    def test_is_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self._make().account_id = "changed"


if __name__ == "__main__":
    unittest.main()
