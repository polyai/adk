"""Tests for the CallSession data model.

Copyright PolyAI Limited
"""

import dataclasses
import unittest

from poly.call.session import CallSession


class CallSessionTest(unittest.TestCase):
    """Tests for the CallSession dataclass."""

    @staticmethod
    def _make(**overrides) -> CallSession:
        fields = {
            "account_id": "acc-1",
            "project_id": "proj-1",
            "variant_id": "",
            "auth_token": "studio-token",
            "region": "us-1",
        }
        fields.update(overrides)
        return CallSession(**fields)

    def test_holds_everything_the_call_needs(self):
        session = self._make(variant_id="VARIANT-x")
        self.assertEqual(session.account_id, "acc-1")
        self.assertEqual(session.project_id, "proj-1")
        self.assertEqual(session.variant_id, "VARIANT-x")
        self.assertEqual(session.auth_token, "studio-token")
        self.assertEqual(session.region, "us-1")

    def test_is_frozen(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            self._make().account_id = "changed"


if __name__ == "__main__":
    unittest.main()
