"""Tests for ADK key resolution and the missing-key message.

Copyright PolyAI Limited
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from poly.utils import credentials
from poly.utils.credentials import (
    _missing_key_message,
    raise_if_no_credentials,
    retrieve_api_key,
)


class _CredentialsTestCase(unittest.TestCase):
    """Isolated credential file and a clean environment for every test."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.credentials_path = os.path.join(self.tmp.name, "credentials.json")
        patch.object(credentials, "CREDENTIALS_FILE_PATH", self.credentials_path).start()
        patch.dict(os.environ, {}, clear=True).start()

    def tearDown(self):
        patch.stopall()
        self.tmp.cleanup()

    def write_credentials(self, content) -> None:
        with open(self.credentials_path, "w", encoding="utf-8") as f:
            if isinstance(content, str):
                f.write(content)
            else:
                json.dump(content, f)


class MissingKeyMessageTest(_CredentialsTestCase):
    """The message raised when no ADK key resolves for a region."""

    def test_missing_key_message_names_region_and_sources(self):
        """What is missing, how `poly login` fixes it, and the CI alternative, in that order."""
        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")

        message = str(ctx.exception)
        self.assertEqual(
            message,
            "No ADK key found for region 'uk'. ADK commands need an ADK key, which "
            "`poly login` creates and saves to ~/.poly/credentials.json. Run "
            "`poly login --region uk` to sign in to that region. "
            "(CI or scripts: set POLY_ADK_KEY or POLY_ADK_KEY_UK instead.)",
        )
        self.assertNotIn("PAT", message)
        self.assertNotIn("Personal Access Token", message)
        self.assertNotIn("environment variable is not set", message)

    def test_missing_key_message_lists_other_regions_in_credentials_file(self):
        """A key stored for another region is named, with a `--region` suggestion."""
        self.write_credentials({"studio": "stored-studio-key"})

        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")

        message = str(ctx.exception)
        self.assertIn(
            "You already have an ADK key for: studio — re-run with `--region studio` "
            "if that is the workspace you meant.",
            message,
        )
        # Sentence order: how to get it, then what you already have, then the CI clause.
        self.assertLess(message.index("Run `poly login --region uk`"), message.index("You already"))
        self.assertLess(message.index("You already"), message.index("(CI or scripts"))

    def test_missing_key_message_lists_other_regions_from_env_vars(self):
        """A per-region env var for another region counts as a key you already have."""
        os.environ["POLY_ADK_KEY_US"] = "us-env-key"
        os.environ["POLY_ADK_KEY_STUDIO"] = "studio-env-key"

        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("euw-1")

        message = str(ctx.exception)
        self.assertIn("You already have an ADK key for: us, studio", message)
        self.assertIn("re-run with `--region <one of those>`", message)

    def test_missing_key_message_combines_file_and_env_var_regions(self):
        """Both sources are walked once; the requested region is never listed as 'other'."""
        self.write_credentials({"studio": "stored", "uk-1": ""})
        os.environ["POLY_ADK_KEY_EUW"] = "eu-env-key"

        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")

        self.assertIn("You already have an ADK key for: eu, studio", str(ctx.exception))

    def test_missing_key_message_omits_other_regions_when_file_empty_or_absent(self):
        """No other-region sentence when there is nothing to point at."""
        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")
        self.assertNotIn("You already have", str(ctx.exception))

        self.write_credentials({})
        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")
        self.assertNotIn("You already have", str(ctx.exception))

    def test_missing_key_message_ignores_unparseable_credentials_file(self):
        """A corrupt credentials file contributes nothing instead of crashing the message."""
        self.write_credentials("{not json")

        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")

        self.assertNotIn("You already have", str(ctx.exception))

    def test_missing_key_message_mentions_poly_api_key_only_when_set(self):
        """POLY_API_KEY is called out as an account API key only when it is exported."""
        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")
        self.assertNotIn("POLY_API_KEY", str(ctx.exception))

        os.environ["POLY_API_KEY"] = "account-key"
        with self.assertRaises(ValueError) as ctx:
            retrieve_api_key("uk-1")

        message = str(ctx.exception)
        self.assertIn(
            "POLY_API_KEY is set, but that is an account API key for the PolyAI APIs and "
            "the ADK does not use it.",
            message,
        )
        self.assertLess(message.index("POLY_API_KEY is set"), message.index("(CI or scripts"))

    def test_missing_key_message_uses_generic_env_var_for_unknown_region(self):
        """A region with no suffix mapping falls back to a placeholder in the CI clause."""
        message = _missing_key_message("nowhere-9")
        self.assertIn("No ADK key found for region 'nowhere-9'.", message)
        self.assertIn("set POLY_ADK_KEY or POLY_ADK_KEY_<REGION> instead", message)


class ResolutionOrderTest(_CredentialsTestCase):
    """The lookup order is unchanged: file, per-region env var, generic env var."""

    def test_credentials_file_still_wins(self):
        self.write_credentials({"uk-1": "stored-key"})
        os.environ["POLY_ADK_KEY_UK"] = "per-region-env-key"
        os.environ["POLY_ADK_KEY"] = "generic-env-key"

        self.assertEqual(retrieve_api_key("uk-1"), "stored-key")

    def test_per_region_env_var_still_wins(self):
        os.environ["POLY_ADK_KEY_UK"] = "per-region-env-key"
        os.environ["POLY_ADK_KEY"] = "generic-env-key"

        self.assertEqual(retrieve_api_key("uk-1"), "per-region-env-key")

    def test_generic_env_var_is_the_last_fallback(self):
        os.environ["POLY_ADK_KEY"] = "generic-env-key"

        self.assertEqual(retrieve_api_key("uk-1"), "generic-env-key")

    def test_poly_api_key_is_not_read_as_a_credential(self):
        os.environ["POLY_API_KEY"] = "account-key"

        with self.assertRaises(ValueError):
            retrieve_api_key("uk-1")

    def test_missing_key_is_still_a_value_error(self):
        with self.assertRaises(ValueError):
            retrieve_api_key("uk-1")


class RaiseIfNoCredentialsTest(_CredentialsTestCase):
    """The region-less check used before a region has been chosen."""

    def test_raise_if_no_credentials_says_any_region(self):
        with self.assertRaises(ValueError) as ctx:
            raise_if_no_credentials()

        message = str(ctx.exception)
        self.assertTrue(message.startswith("No ADK key found. ADK commands need an ADK key"))
        self.assertIn("Run `poly login` to sign in.", message)
        self.assertNotIn("--region", message)
        self.assertIn("set POLY_ADK_KEY or POLY_ADK_KEY_<REGION> instead", message)

    def test_raise_if_no_credentials_mentions_poly_api_key_when_set(self):
        os.environ["POLY_API_KEY"] = "account-key"

        with self.assertRaises(ValueError) as ctx:
            raise_if_no_credentials()

        self.assertIn("POLY_API_KEY is set, but that is an account API key", str(ctx.exception))

    def test_raise_if_no_credentials_is_silent_when_any_key_exists(self):
        self.write_credentials({"studio": "stored-key"})
        raise_if_no_credentials()

        self.write_credentials({})
        os.environ["POLY_ADK_KEY_US"] = "per-region-env-key"
        raise_if_no_credentials()

        del os.environ["POLY_ADK_KEY_US"]
        os.environ["POLY_ADK_KEY"] = "generic-env-key"
        raise_if_no_credentials()


if __name__ == "__main__":
    unittest.main()
