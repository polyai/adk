"""Tests for poly.auth.account_key, the account-key minting shared by apikey and setup.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.auth.account_key import (
    ACCOUNT_POLL_ATTEMPTS,
    MultipleAccountsError,
    key_name_for_region,
    mint_account_key,
    resolve_account_id,
    wait_for_key_active,
)

JWT = "jwt-token"


def _key(name: str, secret: str, active: bool = True) -> dict:
    return {"key": secret, "active": active, "policies": [{"name": name}]}


class KeyNameForRegionTest(unittest.TestCase):
    """Tests for key_name_for_region."""

    def test_studio_keeps_the_bare_name(self):
        self.assertEqual(key_name_for_region("setup-key", "studio"), "setup-key")

    def test_other_regions_get_a_suffix(self):
        self.assertEqual(key_name_for_region("setup-key", "us-1"), "setup-key-us-1")


class ResolveAccountIdTest(unittest.TestCase):
    """Tests for resolve_account_id."""

    def setUp(self):
        self.api = MagicMock()
        patch("poly.auth.account_key.time.sleep").start()
        self.addCleanup(patch.stopall)

    def test_explicit_account_id_is_returned_without_a_lookup(self):
        account = resolve_account_id(self.api, "studio", JWT, "acc-9", source="setup")

        self.assertEqual(account, "acc-9")
        self.api.get_accounts_internal.assert_not_called()

    def test_single_account_is_chosen(self):
        self.api.get_accounts_internal.return_value = [{"id": "acc-1"}]

        self.assertEqual(resolve_account_id(self.api, "studio", JWT, None, source="setup"), "acc-1")
        self.api.get_accounts_internal.assert_called_once_with(
            region="studio", jwt_token=JWT, source="setup"
        )

    def test_several_accounts_use_the_picker_when_given(self):
        self.api.get_accounts_internal.return_value = [{"id": "acc-1"}, {"id": "acc-2"}]
        pick = MagicMock(return_value="acc-2")

        account = resolve_account_id(self.api, "studio", JWT, None, source="setup", pick=pick)

        self.assertEqual(account, "acc-2")
        pick.assert_called_once_with([{"id": "acc-1"}, {"id": "acc-2"}])

    def test_several_accounts_without_a_picker_raise_with_the_list(self):
        self.api.get_accounts_internal.return_value = [
            {"id": "acc-1", "name": "Acme"},
            {"id": "acc-2", "name": "Globex"},
        ]

        with self.assertRaises(MultipleAccountsError) as ctx:
            resolve_account_id(self.api, "studio", JWT, None, source="setup")

        self.assertEqual([a["id"] for a in ctx.exception.accounts], ["acc-1", "acc-2"])
        self.assertIn("--account-id", str(ctx.exception))

    def test_polls_until_the_account_appears(self):
        self.api.get_accounts_internal.side_effect = [[], [], [{"id": "acc-1"}]]

        self.assertEqual(resolve_account_id(self.api, "studio", JWT, None, source="setup"), "acc-1")
        self.assertEqual(self.api.get_accounts_internal.call_count, 3)

    def test_no_account_after_the_poll_window_raises(self):
        self.api.get_accounts_internal.return_value = []

        with self.assertRaises(ValueError) as ctx:
            resolve_account_id(self.api, "studio", JWT, None, source="setup")

        self.assertEqual(self.api.get_accounts_internal.call_count, ACCOUNT_POLL_ATTEMPTS)
        self.assertIn("--account-id", str(ctx.exception))


class MintAccountKeyTest(unittest.TestCase):
    """Tests for mint_account_key."""

    def setUp(self):
        self.api = MagicMock()
        self.api.list_account_api_keys_internal.return_value = []
        self.api.create_account_api_key_internal.return_value = {"key": "sk-new"}

    def _mint(self, **kwargs):
        return mint_account_key(self.api, "studio", JWT, "acc-1", "setup-key", source="setup", **kwargs)

    def test_creates_a_key_with_the_requested_name_when_none_matches(self):
        self.assertEqual(self._mint(), ("sk-new", False, "setup-key"))
        self.api.create_account_api_key_internal.assert_called_once_with(
            region="studio", jwt_token=JWT, account_id="acc-1", name="setup-key", source="setup"
        )

    def test_reuses_a_key_with_the_requested_name(self):
        self.api.list_account_api_keys_internal.return_value = [_key("setup-key", "sk-old")]

        self.assertEqual(self._mint(), ("sk-old", True, "setup-key"))
        self.api.create_account_api_key_internal.assert_not_called()

    def test_reuses_an_also_reuse_name_before_creating(self):
        """A key `poly apikey` made is reused rather than a second one created."""
        self.api.list_account_api_keys_internal.return_value = [_key("cli-generated-key", "sk-cli")]

        result = self._mint(also_reuse=["cli-generated-key"])

        self.assertEqual(result, ("sk-cli", True, "cli-generated-key"))
        self.api.create_account_api_key_internal.assert_not_called()

    def test_requested_name_wins_over_also_reuse_names(self):
        self.api.list_account_api_keys_internal.return_value = [
            _key("cli-generated-key", "sk-cli"),
            _key("setup-key", "sk-setup"),
        ]

        self.assertEqual(self._mint(also_reuse=["cli-generated-key"])[0], "sk-setup")

    def test_inactive_keys_are_not_reused(self):
        self.api.list_account_api_keys_internal.return_value = [
            _key("setup-key", "sk-dead", active=False)
        ]

        self.assertEqual(self._mint()[0], "sk-new")

    def test_create_without_a_key_in_the_response_raises(self):
        self.api.create_account_api_key_internal.return_value = {}

        with self.assertRaises(ValueError):
            self._mint()


class WaitForKeyActiveTest(unittest.TestCase):
    """Tests for wait_for_key_active."""

    def setUp(self):
        self.api = MagicMock()
        patch("poly.auth.account_key.time.sleep").start()
        self.addCleanup(patch.stopall)

    def test_returns_true_once_the_key_authenticates(self):
        self.api.get_accounts_with_key.side_effect = [RuntimeError("401"), {"acc-1": "Acme"}]

        self.assertTrue(wait_for_key_active(self.api, "studio", "sk-new"))
        self.api.get_accounts_with_key.assert_called_with(region="studio", api_key="sk-new")

    def test_returns_false_when_the_key_never_activates(self):
        self.api.get_accounts_with_key.side_effect = RuntimeError("401")

        self.assertFalse(wait_for_key_active(self.api, "studio", "sk-new"))
        self.assertEqual(self.api.get_accounts_with_key.call_count, ACCOUNT_POLL_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
