"""Tests for shell/registry environment variable persistence.

Copyright PolyAI Limited
"""

import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import MagicMock, patch

from poly.utils.env_profile import (
    MARKER_COMMENT,
    EnvVarConflict,
    _get_windows_registry_backend,
    detect_profile,
    write_env_var,
)


@contextmanager
def _home_env():
    """Patch HOME/USERPROFILE to a fresh temp dir and force the posix code path.

    Needed so the Unix/fish tests behave identically on the Windows CI
    runner: `os.path.expanduser("~")` reads `USERPROFILE` on Windows and
    ignores `HOME` (Python 3.8+), and `detect_profile()`/`write_env_var()`
    both branch on `os.name`, which is `"nt"` there.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        home = Path(tmp_dir)
        with (
            patch.dict(os.environ, {"HOME": str(home), "USERPROFILE": str(home)}),
            patch("poly.utils.env_profile.os.name", "posix"),
        ):
            yield home


class DetectProfile(unittest.TestCase):
    """Tests for detect_profile's shell -> file mapping."""

    def test_zsh(self):
        """zsh resolves to ~/.zshrc."""
        with _home_env() as home, patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            target = detect_profile()
        self.assertEqual(target.path, home / ".zshrc")
        self.assertEqual(target.shell, "zsh")

    def test_bash_on_macos(self):
        """bash on macOS resolves to ~/.bash_profile."""
        with (
            _home_env() as home,
            patch.dict(os.environ, {"SHELL": "/bin/bash"}),
            patch("poly.utils.env_profile.sys.platform", "darwin"),
        ):
            target = detect_profile()
        self.assertEqual(target.path, home / ".bash_profile")
        self.assertEqual(target.shell, "bash")

    def test_bash_on_linux(self):
        """bash on Linux resolves to ~/.bashrc."""
        with (
            _home_env() as home,
            patch.dict(os.environ, {"SHELL": "/bin/bash"}),
            patch("poly.utils.env_profile.sys.platform", "linux"),
        ):
            target = detect_profile()
        self.assertEqual(target.path, home / ".bashrc")
        self.assertEqual(target.shell, "bash")

    def test_fish(self):
        """fish resolves to ~/.config/fish/config.fish."""
        with _home_env() as home, patch.dict(os.environ, {"SHELL": "/usr/bin/fish"}):
            target = detect_profile()
        self.assertEqual(target.path, home / ".config" / "fish" / "config.fish")
        self.assertEqual(target.shell, "fish")

    def test_unknown_shell_falls_back_to_profile(self):
        """An unrecognized $SHELL falls back to ~/.profile."""
        with _home_env() as home, patch.dict(os.environ, {"SHELL": "/bin/tcsh"}):
            target = detect_profile()
        self.assertEqual(target.path, home / ".profile")
        self.assertEqual(target.shell, "sh")

    def test_unset_shell_falls_back_to_profile(self):
        """A missing $SHELL falls back to ~/.profile."""
        with _home_env() as home:
            os.environ.pop("SHELL", None)
            target = detect_profile()
        self.assertEqual(target.path, home / ".profile")
        self.assertEqual(target.shell, "sh")

    def test_windows_returns_registry_target_regardless_of_shell(self):
        """On Windows, the target is always the registry, $SHELL is not consulted."""
        with patch("poly.utils.env_profile.os.name", "nt"):
            target = detect_profile()
        self.assertEqual(str(target.path), "HKCU\\Environment")
        self.assertEqual(target.shell, "powershell")

    def test_resolves_under_temp_dir_when_posix_is_forced(self):
        """Regression for the Windows CI fix.

        Forcing posix resolution while both HOME and USERPROFILE are set (as
        they would be on the Windows runner) must still resolve under the
        patched home, not the real Windows profile directory.
        """
        with tempfile.TemporaryDirectory() as tmp_dir:
            home = Path(tmp_dir)
            with (
                patch.dict(
                    os.environ, {"HOME": str(home), "USERPROFILE": str(home), "SHELL": "/bin/zsh"}
                ),
                patch("poly.utils.env_profile.os.name", "posix"),
            ):
                target = detect_profile()
        self.assertEqual(target.path, home / ".zshrc")


class WriteEnvVarUnix(unittest.TestCase):
    """Tests for write_env_var against a real temp file on Unix-style profiles."""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp_dir.name)
        self._env_patch = patch.dict(
            os.environ,
            {"HOME": str(self.home), "USERPROFILE": str(self.home), "SHELL": "/bin/zsh"},
        )
        self._env_patch.start()
        self._os_name_patch = patch("poly.utils.env_profile.os.name", "posix")
        self._os_name_patch.start()

    def tearDown(self):
        self._os_name_patch.stop()
        self._env_patch.stop()
        self._tmp_dir.cleanup()

    def test_creates_file_with_marker_and_export_line(self):
        """A missing profile file is created with the marker and export line."""
        target, masked_line = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        content = target.path.read_text(encoding="utf-8")
        self.assertIn(MARKER_COMMENT, content)
        self.assertIn('export POLY_API_KEY="sk-abcdefgh1234"', content)
        self.assertNotIn("sk-abcdefgh1234", masked_line)

    def test_appends_to_existing_file_preserving_content(self):
        """Existing profile content is preserved; the new line is appended."""
        target_path = self.home / ".zshrc"
        target_path.write_text("alias ll='ls -la'\n", encoding="utf-8")

        target, _ = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        content = target.path.read_text(encoding="utf-8")
        self.assertIn("alias ll='ls -la'", content)
        self.assertIn(MARKER_COMMENT, content)
        self.assertIn('export POLY_API_KEY="sk-abcdefgh1234"', content)

    def test_identical_value_is_a_no_op(self):
        """Writing the same value twice does not duplicate the line."""
        write_env_var("POLY_API_KEY", "sk-abcdefgh1234")
        target, message = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        content = target.path.read_text(encoding="utf-8")
        self.assertEqual(content.count("POLY_API_KEY"), 1)
        self.assertIn("already set", message)

    def test_conflicting_value_raises_without_force(self):
        """A differing existing value raises EnvVarConflict when force is False."""
        write_env_var("POLY_API_KEY", "sk-old-value-1")

        with self.assertRaises(EnvVarConflict) as ctx:
            write_env_var("POLY_API_KEY", "sk-new-value-2")

        self.assertNotIn("sk-old-value-1", str(ctx.exception))
        self.assertNotIn("sk-new-value-2", str(ctx.exception))

    def test_force_replaces_in_place_with_single_marker(self):
        """force=True replaces the value in place without duplicating the marker."""
        write_env_var("POLY_API_KEY", "sk-old-value-1")

        target, _ = write_env_var("POLY_API_KEY", "sk-new-value-2", force=True)

        content = target.path.read_text(encoding="utf-8")
        self.assertEqual(content.count(MARKER_COMMENT), 1)
        self.assertIn('export POLY_API_KEY="sk-new-value-2"', content)
        self.assertNotIn("sk-old-value-1", content)

    def test_force_on_foreign_line_inserts_marker(self):
        """force=True replacing a user-authored line inserts the marker above it."""
        target_path = self.home / ".zshrc"
        target_path.write_text('export POLY_API_KEY="user-set-value"\n', encoding="utf-8")

        target, _ = write_env_var("POLY_API_KEY", "sk-new-value-2", force=True)

        content = target.path.read_text(encoding="utf-8")
        self.assertEqual(content.count(MARKER_COMMENT), 1)
        self.assertIn('export POLY_API_KEY="sk-new-value-2"', content)


class WriteEnvVarFish(unittest.TestCase):
    """Tests for the fish shell's `set -gx` syntax."""

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp_dir.name)
        self._env_patch = patch.dict(
            os.environ,
            {"HOME": str(self.home), "USERPROFILE": str(self.home), "SHELL": "/usr/bin/fish"},
        )
        self._env_patch.start()
        self._os_name_patch = patch("poly.utils.env_profile.os.name", "posix")
        self._os_name_patch.start()

    def tearDown(self):
        self._os_name_patch.stop()
        self._env_patch.stop()
        self._tmp_dir.cleanup()

    def test_uses_set_gx_syntax_and_creates_parent_dir(self):
        """fish's config.fish is created (with parent dir) using `set -gx` syntax."""
        target, _ = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        self.assertEqual(target.path, self.home / ".config" / "fish" / "config.fish")
        content = target.path.read_text(encoding="utf-8")
        self.assertIn('set -gx POLY_API_KEY "sk-abcdefgh1234"', content)

    def test_identical_value_is_a_no_op(self):
        """Re-running with the same value in fish syntax is a no-op."""
        write_env_var("POLY_API_KEY", "sk-abcdefgh1234")
        target, message = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        content = target.path.read_text(encoding="utf-8")
        self.assertEqual(content.count("POLY_API_KEY"), 1)
        self.assertIn("already set", message)


class WriteEnvVarWindows(unittest.TestCase):
    """Tests for the Windows registry path, using an injected fake backend."""

    def tearDown(self):
        # write_env_var sets this on the current process so tests don't leak it.
        os.environ.pop("POLY_API_KEY", None)

    def _fake_backend(self, existing=None):
        backend = MagicMock()
        backend.read.return_value = existing
        return backend

    @patch("poly.utils.env_profile.os.name", "nt")
    @patch("poly.utils.env_profile._get_windows_registry_backend")
    def test_writes_new_value_and_broadcasts(self, mock_get_backend):
        """A fresh value is written to the registry and the change is broadcast."""
        backend = self._fake_backend(existing=None)
        mock_get_backend.return_value = backend

        target, masked_line = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        self.assertEqual(str(target.path), "HKCU\\Environment")
        backend.write.assert_called_once_with("POLY_API_KEY", "sk-abcdefgh1234")
        backend.broadcast.assert_called_once()
        self.assertNotIn("sk-abcdefgh1234", masked_line)
        self.assertEqual(os.environ["POLY_API_KEY"], "sk-abcdefgh1234")

    @patch("poly.utils.env_profile.os.name", "nt")
    @patch("poly.utils.env_profile._get_windows_registry_backend")
    def test_identical_value_is_a_no_op(self, mock_get_backend):
        """An identical existing registry value is left untouched."""
        backend = self._fake_backend(existing="sk-abcdefgh1234")
        mock_get_backend.return_value = backend

        _, message = write_env_var("POLY_API_KEY", "sk-abcdefgh1234")

        backend.write.assert_not_called()
        self.assertIn("already set", message)

    @patch("poly.utils.env_profile.os.name", "nt")
    @patch("poly.utils.env_profile._get_windows_registry_backend")
    def test_conflicting_value_raises_without_force(self, mock_get_backend):
        """A differing existing registry value raises EnvVarConflict without --force."""
        backend = self._fake_backend(existing="old-value")
        mock_get_backend.return_value = backend

        with self.assertRaises(EnvVarConflict):
            write_env_var("POLY_API_KEY", "new-value")
        backend.write.assert_not_called()

    @patch("poly.utils.env_profile.os.name", "nt")
    @patch("poly.utils.env_profile._get_windows_registry_backend")
    def test_force_overwrites_conflicting_value(self, mock_get_backend):
        """force=True overwrites a differing existing registry value."""
        backend = self._fake_backend(existing="old-value")
        mock_get_backend.return_value = backend

        write_env_var("POLY_API_KEY", "new-value", force=True)

        backend.write.assert_called_once_with("POLY_API_KEY", "new-value")
        backend.broadcast.assert_called_once()

    def test_default_backend_factory_returns_real_backend_type(self):
        """The default factory returns the real backend (used only on actual Windows)."""
        from poly.utils.env_profile import _WindowsRegistryBackend

        self.assertIsInstance(_get_windows_registry_backend(), _WindowsRegistryBackend)


if __name__ == "__main__":
    unittest.main()
