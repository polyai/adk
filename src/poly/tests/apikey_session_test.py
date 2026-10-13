"""Tests for the `poly apikey` sign-in cache.

Copyright PolyAI Limited
"""

import base64
import json
import os
import stat
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from poly.utils import apikey_session


def _fake_jwt(payload: dict) -> str:
    """Build an unsigned JWT-shaped string carrying `payload`."""

    def seg(obj: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'none'})}.{seg(payload)}.sig"


class SessionFileTestCase(unittest.TestCase):
    """Points the session file at a temp dir so the real ~/.poly is never touched."""

    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.path = os.path.join(tmp_dir.name, "poly", "apikey_session.json")
        patcher = patch.object(apikey_session, "SESSION_FILE_PATH", self.path)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _write_raw(self, content: str) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(content)


class SaveAndLoad(SessionFileTestCase):
    """Round-trips through save/load."""

    def test_save_then_load_returns_the_token(self):
        """A saved, unexpired token is returned for its region."""
        token = _fake_jwt({"exp": int(time.time()) + 3600})

        saved = apikey_session.save("studio", token)
        loaded = apikey_session.load("studio")

        self.assertEqual(loaded, saved)
        self.assertEqual(loaded.token, token)

    def test_exp_is_read_from_the_token(self):
        """The cache entry expires when the token does."""
        exp = int(time.time()) + 1234
        saved = apikey_session.save("studio", _fake_jwt({"exp": exp}))

        self.assertEqual(saved.exp, exp)

    def test_token_without_exp_gets_default_lifetime(self):
        """A token with no readable exp is kept for an hour."""
        before = int(time.time())
        saved = apikey_session.save("studio", "not-a-jwt")

        self.assertGreaterEqual(saved.exp, before + apikey_session.DEFAULT_LIFETIME_SECONDS)
        self.assertLessEqual(saved.exp, int(time.time()) + apikey_session.DEFAULT_LIFETIME_SECONDS)

    def test_regions_are_kept_separately(self):
        """Saving one region does not replace another."""
        exp = int(time.time()) + 3600
        apikey_session.save("studio", _fake_jwt({"exp": exp, "r": "studio"}))
        apikey_session.save("us-1", _fake_jwt({"exp": exp, "r": "us-1"}))

        self.assertNotEqual(
            apikey_session.load("studio").token, apikey_session.load("us-1").token
        )

    def test_missing_region_is_none(self):
        """No entry for the region means nothing to reuse."""
        apikey_session.save("studio", _fake_jwt({"exp": int(time.time()) + 3600}))

        self.assertIsNone(apikey_session.load("us-1"))

    def test_missing_file_is_none(self):
        """No file at all means nothing to reuse."""
        self.assertIsNone(apikey_session.load("studio"))

    @unittest.skipIf(sys.platform == "win32", "POSIX file modes only")
    def test_file_is_user_only(self):
        """The cache file is mode 600, like the credentials file."""
        apikey_session.save("studio", _fake_jwt({"exp": int(time.time()) + 3600}))

        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)


class Expiry(SessionFileTestCase):
    """Expired or nearly expired tokens are not reused."""

    def test_expired_token_is_none(self):
        """A token past its exp is ignored."""
        apikey_session.save("studio", _fake_jwt({"exp": int(time.time()) - 10}))

        self.assertIsNone(apikey_session.load("studio"))

    def test_token_inside_the_margin_is_none(self):
        """A token about to expire is treated as expired."""
        exp = int(time.time()) + apikey_session.EXPIRY_MARGIN_SECONDS - 5
        apikey_session.save("studio", _fake_jwt({"exp": exp}))

        self.assertIsNone(apikey_session.load("studio"))


class BadFile(SessionFileTestCase):
    """A damaged cache file never breaks the command."""

    def test_bad_json_is_none(self):
        """Unparseable JSON is ignored on load."""
        self._write_raw("{not json")

        self.assertIsNone(apikey_session.load("studio"))

    def test_non_dict_json_is_none(self):
        """A JSON list (or any non-object) is ignored."""
        self._write_raw("[1, 2]")

        self.assertIsNone(apikey_session.load("studio"))

    def test_malformed_entry_is_none(self):
        """An entry missing its token or exp is ignored."""
        self._write_raw(json.dumps({"studio": {"exp": "soon"}}))

        self.assertIsNone(apikey_session.load("studio"))

    def test_save_over_bad_json_replaces_it(self):
        """Saving over a damaged file writes a clean one."""
        self._write_raw("{not json")

        apikey_session.save("studio", _fake_jwt({"exp": int(time.time()) + 3600}))

        self.assertIsNotNone(apikey_session.load("studio"))


class Clear(SessionFileTestCase):
    """clear() drops one region only."""

    def test_clear_removes_only_that_region(self):
        """Clearing studio keeps us-1."""
        exp = int(time.time()) + 3600
        apikey_session.save("studio", _fake_jwt({"exp": exp}))
        apikey_session.save("us-1", _fake_jwt({"exp": exp}))

        apikey_session.clear("studio")

        self.assertIsNone(apikey_session.load("studio"))
        self.assertIsNotNone(apikey_session.load("us-1"))

    def test_clear_without_file_is_a_no_op(self):
        """Clearing when nothing is cached does not create a file."""
        apikey_session.clear("studio")

        self.assertFalse(os.path.exists(self.path))


if __name__ == "__main__":
    unittest.main()
