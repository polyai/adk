"""Tests for select_reusable_api_key.

Copyright PolyAI Limited
"""

import unittest
from datetime import datetime, timedelta, timezone

from poly.utils.api_keys import select_reusable_api_key

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _key(
    key: str = "sk-1",
    active: bool = True,
    expires_at: str | None = None,
    name: str = "onboard-key",
    created_at: str = "2026-01-01T00:00:00Z",
) -> dict:
    """Build a key record shaped like the accounts API response."""
    return {
        "key": key,
        "active": active,
        "expires_at": expires_at,
        "policies": [{"name": name}],
        "created_at": created_at,
    }


class SelectReusableApiKey(unittest.TestCase):
    """Tests for select_reusable_api_key's matching rules."""

    def test_matches_on_policy_name_not_top_level_name(self):
        """The key name lives under policies[0].name, not the key's own `name` field."""
        key = _key(name="onboard-key")
        key["name"] = ""  # top-level `name` comes back empty, per the real API.

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertEqual(result, "sk-1")

    def test_skips_inactive_keys(self):
        """An inactive key is never reused."""
        key = _key(active=False)

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertIsNone(result)

    def test_skips_expired_keys(self):
        """A key whose expires_at is in the past is never reused."""
        expired = (NOW - timedelta(days=1)).isoformat()
        key = _key(expires_at=expired)

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertIsNone(result)

    def test_keeps_key_expiring_in_the_future(self):
        """A key whose expires_at is still ahead of `now` is eligible."""
        future = (NOW + timedelta(days=1)).isoformat()
        key = _key(expires_at=future)

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertEqual(result, "sk-1")

    def test_missing_expires_at_is_treated_as_valid(self):
        """A key with no expires_at (or None) never expires."""
        key = _key(expires_at=None)

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertEqual(result, "sk-1")

    def test_skips_keys_with_a_different_policy_name(self):
        """A key created under a different name is not reused."""
        key = _key(name="some-other-key")

        result = select_reusable_api_key([key], "onboard-key", NOW)

        self.assertIsNone(result)

    def test_picks_the_newest_matching_key(self):
        """Among several matching keys, the one with the latest created_at wins."""
        older = _key(key="sk-old", created_at="2025-01-01T00:00:00Z")
        newer = _key(key="sk-new", created_at="2026-01-01T00:00:00Z")

        result = select_reusable_api_key([older, newer], "onboard-key", NOW)

        self.assertEqual(result, "sk-new")

    def test_empty_list_returns_none(self):
        """An empty key list has nothing to reuse."""
        result = select_reusable_api_key([], "onboard-key", NOW)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
