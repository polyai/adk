"""Tests for the `_signin` wrapper in cli_commands.auth.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.auth import _authenticate_and_save_key, _signin, authorise_or_explain
from poly.handlers.auth0_handler import REGION_TO_AUTH_DETAILS


def _http_error(status: int) -> requests.HTTPError:
    """Build an HTTPError whose response carries ``status``."""
    response = MagicMock()
    response.status_code = status
    return requests.HTTPError(f"{status} Client Error", response=response)


class AuthoriseOrExplain(unittest.TestCase):
    """Tests for the shared 403 rewrite on enterprise regions."""

    def test_403_on_enterprise_region_becomes_value_error_with_hint(self):
        """A 403 on us-1 becomes a ValueError that names the region and the hint."""
        api = MagicMock()
        api.authorise.side_effect = _http_error(403)

        with self.assertRaises(ValueError) as ctx:
            authorise_or_explain(api, "us-1", "tok", self_serve_hint="run `poly login`")

        self.assertIn("No account is provisioned for you on us-1", str(ctx.exception))
        self.assertIn("run `poly login`", str(ctx.exception))

    def test_403_on_studio_propagates(self):
        """On studio a 403 is a genuine auth error and is not rewritten."""
        api = MagicMock()
        api.authorise.side_effect = _http_error(403)

        with self.assertRaises(requests.HTTPError):
            authorise_or_explain(api, "studio", "tok", self_serve_hint="x")

    def test_other_errors_propagate(self):
        """A non-403 error on an enterprise region is not rewritten."""
        api = MagicMock()
        api.authorise.side_effect = _http_error(500)

        with self.assertRaises(requests.HTTPError):
            authorise_or_explain(api, "uk-1", "tok", self_serve_hint="x")

    def test_success_returns_the_user_record(self):
        """The authorise response passes through untouched."""
        api = MagicMock()
        api.authorise.return_value = {"email": "a@b.c"}

        self.assertEqual(
            authorise_or_explain(api, "euw-1", "tok", self_serve_hint="x"), {"email": "a@b.c"}
        )


class AuthenticateAndSaveKey(unittest.TestCase):
    """Tests for the login/setup sign-in helper's handling of an unprovisioned user."""

    @patch("poly.cli_commands.auth.AgentStudioInterface")
    def test_unprovisioned_enterprise_user_exits_with_message(self, mock_interface):
        """A 403 from authorise on us-1 exits(1) with the provisioning message, no traceback."""
        mock_interface.return_value.authorise.side_effect = _http_error(403)

        with patch("poly.output.console.error") as mock_error:
            with self.assertRaises(SystemExit) as ctx:
                _authenticate_and_save_key("tok", region="us-1")

        self.assertEqual(ctx.exception.code, 1)
        message = mock_error.call_args.args[0]
        self.assertIn("No account is provisioned for you on us-1", message)
        self.assertIn("poly login --region studio", message)
        mock_interface.return_value.get_pats.assert_not_called()


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
