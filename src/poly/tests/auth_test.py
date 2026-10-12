"""Tests for the `_signin` wrapper in cli_commands.auth.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import patch

from poly.cli_commands.auth import _signin
from poly.handlers.auth0_handler import REGION_TO_AUTH_DETAILS


class Signin(unittest.TestCase):
    """Tests for _signin's delegation to the shared device flow."""

    @patch("poly.cli_commands.auth.signin_with_device_flow")
    def test_delegates_to_shared_flow_with_region_auth_details(self, mock_signin):
        """_signin resolves the region's AuthDetails and returns the shared flow's token."""
        mock_signin.return_value = "tok-1"

        token = _signin("studio")

        self.assertEqual(token, "tok-1")
        mock_signin.assert_called_once_with(REGION_TO_AUTH_DETAILS["studio"])

    def test_unknown_region_exits_with_error(self):
        """An unknown region exits(1) without calling the device flow."""
        with self.assertRaises(SystemExit) as ctx:
            _signin("mars-1")
        self.assertEqual(ctx.exception.code, 1)

    @patch("poly.cli_commands.auth.signin_with_device_flow")
    def test_device_flow_error_exits_with_error(self, mock_signin):
        """A DeviceFlowError from the shared flow exits(1) instead of propagating."""
        from poly.auth.device_flow import DeviceFlowError

        mock_signin.side_effect = DeviceFlowError("Authorization timed out. Please try again.")

        with self.assertRaises(SystemExit) as ctx:
            _signin("studio")
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
