"""Tests for the PATH shadow check: which poly is running, and which one comes first.

Copyright PolyAI Limited
"""

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from poly.utils import installs
from poly.utils.installs import (
    OtherInstall,
    already_warned,
    is_self,
    mark_warned,
    other_version,
    path_candidates,
    running_binary,
    shadow_json_field,
    shadowing_install,
)


def _executable(directory: Path, name: str = "poly", body: str = "#!/bin/sh\necho 0.7.3\n") -> str:
    """Write an executable file and return its path."""
    path = directory / name
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return str(path)


class InstallsTestCase(unittest.TestCase):
    """Two throwaway bin directories, a running binary in one, and a controlled PATH."""

    def setUp(self):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        self.root = Path(temp_dir.name).resolve()
        self.ours_dir = self.root / "ours"
        self.theirs_dir = self.root / "theirs"
        self.prefix = self.root / "prefix"
        for directory in (self.ours_dir, self.theirs_dir, self.prefix / "bin"):
            directory.mkdir(parents=True)
        self.ours = _executable(self.ours_dir, body="#!/bin/sh\necho 0.71.0\n")
        self.theirs = _executable(self.theirs_dir)
        self._patch("sys.argv", [self.ours])
        self._patch("sys.prefix", str(self.prefix))
        # Never run a real binary: tests of other_version patch subprocess.run explicitly.
        self.run = self._patch(
            "poly.utils.installs.subprocess.run", side_effect=AssertionError("no subprocess")
        )
        self.cache_file = self.root / ".other_poly"
        self.stamp_file = self.root / ".shadow_seen"
        self._patch("poly.utils.installs.OTHER_POLY_CACHE_FILE", self.cache_file)
        self._patch("poly.utils.installs.SHADOW_SEEN_FILE", self.stamp_file)
        self._patch("poly.utils.installs._shadow_field", None)
        self._patch("poly.utils.installs.running_version", return_value="0.71.0")
        # The fixtures are POSIX-shaped (no PATHEXT); the Windows tests flip this themselves.
        self._patch("poly.utils.installs._is_windows", return_value=False)

    def _patch(self, target: str, *args, **kwargs) -> MagicMock:
        patcher = patch(target, *args, **kwargs)
        mock = patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def _symlink(self, link: Path, target: str) -> None:
        """Create a symlink, or skip where the runner cannot (Windows without the privilege)."""
        try:
            link.symlink_to(target)
        except OSError as e:
            self.skipTest(f"symlinks unavailable here: {e}")

    def _set_path(self, *directories: Path | str) -> None:
        patcher = patch.dict(os.environ, {"PATH": os.pathsep.join(str(d) for d in directories)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def _completed(self, stdout: str, returncode: int = 0) -> MagicMock:
        return MagicMock(stdout=stdout, returncode=returncode)


class RunningBinaryTest(InstallsTestCase):
    def test_display_path_is_argv0_absolute(self):
        self.assertEqual(running_binary().display_path, os.path.abspath(self.ours))

    def test_compare_path_is_realpath(self):
        link = self.root / "link"
        self._symlink(link, self.ours)
        with patch("sys.argv", [str(link)]):
            self.assertEqual(running_binary().compare_path, os.path.realpath(self.ours))


class ShadowingInstallTest(InstallsTestCase):
    def test_no_shadow_when_first_on_path_is_us(self):
        self._set_path(self.ours_dir, self.theirs_dir)
        self.assertIsNone(shadowing_install())
        self.run.assert_not_called()

    def test_no_shadow_when_first_is_symlink_to_us(self):
        link_dir = self.root / "links"
        link_dir.mkdir()
        self._symlink(link_dir / "poly", self.ours)
        self._set_path(link_dir, self.theirs_dir)
        self.assertIsNone(shadowing_install())

    def test_no_shadow_when_candidate_is_under_sys_prefix(self):
        """python -m poly and editable installs: argv[0] is on no PATH entry, the venv's poly is."""
        venv_poly = _executable(self.prefix / "bin")
        self._set_path(self.prefix / "bin", self.theirs_dir)
        with patch("sys.argv", [str(self.root / "somewhere" / "__main__.py")]):
            self.assertIsNone(shadowing_install())
        self.assertTrue(os.path.exists(venv_poly))

    def test_shadow_when_different_binary_first(self):
        self.run.side_effect = None
        self.run.return_value = self._completed("0.7.3\n")
        self._set_path(self.theirs_dir, self.ours_dir)
        self.assertEqual(shadowing_install(), OtherInstall(path=self.theirs, version="0.7.3"))

    def test_shadow_when_running_binary_not_on_path(self):
        """uvx or an explicit path: we are on no PATH entry and a different poly is first."""
        self.run.side_effect = None
        self.run.return_value = self._completed("0.7.3\n")
        self._set_path(self.theirs_dir)
        self.assertEqual(shadowing_install(), OtherInstall(path=self.theirs, version="0.7.3"))

    def test_no_candidates_is_not_a_shadow(self):
        self._set_path(self.root / "empty")
        self.assertIsNone(shadowing_install())

    def test_second_entry_is_irrelevant(self):
        """Only the first poly runs when you type poly; an older one behind us is not a shadow."""
        self._set_path(self.ours_dir, self.theirs_dir)
        self.assertIsNone(shadowing_install())

    def test_never_raises(self):
        with patch("poly.utils.installs.path_candidates", side_effect=RuntimeError("boom")):
            self.assertIsNone(shadowing_install())


class PathCandidatesTest(InstallsTestCase):
    def test_candidates_skip_non_executable_and_missing(self):
        plain_dir = self.root / "plain"
        plain_dir.mkdir()
        (plain_dir / "poly").write_text("not executable")
        self._set_path(plain_dir, self.root / "missing", self.theirs_dir, self.ours_dir)
        self.assertEqual(path_candidates(), [self.theirs, self.ours])

    def test_empty_path_entries_are_skipped(self):
        with patch.dict(os.environ, {"PATH": os.pathsep + str(self.theirs_dir) + os.pathsep}):
            self.assertEqual(path_candidates(), [self.theirs])

    def test_windows_pathext_walk(self):
        """On Windows the shell tries each PATHEXT extension per directory, in order."""
        exe = _executable(self.theirs_dir, "poly.exe")
        cmd = _executable(self.theirs_dir, "poly.cmd")
        _executable(self.ours_dir, "poly")  # no extension: not runnable by name on Windows
        self._set_path(self.ours_dir, self.theirs_dir)
        with (
            patch("poly.utils.installs._is_windows", return_value=True),
            patch.dict(os.environ, {"PATHEXT": ".COM;.EXE;.BAT;.CMD"}),
        ):
            self.assertEqual(path_candidates(), [exe, cmd])

    def test_windows_running_binary_without_extension_matches_its_exe(self):
        """uv's trampoline strips .exe from argv[0]; the PATH entry still has it."""
        exe = _executable(self.ours_dir, "poly.exe")
        with (
            patch("poly.utils.installs._is_windows", return_value=True),
            patch.dict(os.environ, {"PATHEXT": ".COM;.EXE"}),
            patch("sys.argv", [str(self.ours_dir / "poly")]),
        ):
            self.assertTrue(is_self(exe))
            self.assertFalse(is_self(_executable(self.theirs_dir, "poly.exe")))


class IsSelfTest(InstallsTestCase):
    def test_same_file(self):
        self.assertTrue(is_self(self.ours))

    def test_different_file(self):
        self.assertFalse(is_self(self.theirs))

    def test_under_sys_prefix(self):
        self.assertTrue(is_self(_executable(self.prefix / "bin")))

    def test_sibling_of_sys_prefix_is_not_under_it(self):
        sibling = self.root / "prefix2" / "bin"
        sibling.mkdir(parents=True)
        self.assertFalse(is_self(_executable(sibling)))

    def test_failure_counts_as_self(self):
        """Better to miss a warning than to warn about our own install."""
        with patch("poly.utils.installs.running_binary", side_effect=RuntimeError("boom")):
            self.assertTrue(is_self(self.theirs))


class OtherVersionTest(InstallsTestCase):
    def setUp(self):
        super().setUp()
        self.run.side_effect = None
        self.run.return_value = self._completed("0.7.3\n")

    def test_other_version_reads_stdout(self):
        self.assertEqual(other_version(self.theirs), "0.7.3")
        args, kwargs = self.run.call_args
        self.assertEqual(args[0], [self.theirs, "--version"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["timeout"], 3.0)
        self.assertEqual(kwargs["env"]["POLY_NO_UPDATE_CHECK"], "1")

    def test_other_version_keeps_first_line_printable_and_capped(self):
        self.run.return_value = self._completed("\x1b[1m" + "9" * 60 + "\nsecond line\n")
        version = other_version(self.theirs)
        self.assertNotIn("\x1b", version)
        self.assertNotIn("second", version)
        self.assertLessEqual(len(version), 40)

    def test_other_version_timeout_is_unknown(self):
        self.run.side_effect = subprocess.TimeoutExpired(cmd="poly", timeout=3)
        self.assertEqual(other_version(self.theirs), "unknown")

    def test_other_version_nonzero_is_unknown(self):
        self.run.return_value = self._completed("Traceback", returncode=1)
        self.assertEqual(other_version(self.theirs), "unknown")

    def test_other_version_empty_output_is_unknown(self):
        self.run.return_value = self._completed("")
        self.assertEqual(other_version(self.theirs), "unknown")

    def test_other_version_missing_file_is_unknown_without_subprocess(self):
        self.assertEqual(other_version(str(self.root / "nope")), "unknown")
        self.run.assert_not_called()

    def test_other_version_cache_hit_skips_subprocess(self):
        self.assertEqual(other_version(self.theirs), "0.7.3")
        self.assertEqual(other_version(self.theirs), "0.7.3")
        self.assertEqual(self.run.call_count, 1)
        self.assertEqual(json.loads(self.cache_file.read_text())[self.theirs]["version"], "0.7.3")

    def test_other_version_cache_invalidated_by_mtime(self):
        other_version(self.theirs)
        os.utime(self.theirs, (1, 1))
        self.run.return_value = self._completed("0.8.0\n")
        self.assertEqual(other_version(self.theirs), "0.8.0")
        self.assertEqual(self.run.call_count, 2)

    def test_other_version_cache_invalidated_by_size(self):
        other_version(self.theirs)
        Path(self.theirs).write_text("#!/bin/sh\necho 0.8.0 # longer\n")
        self.run.return_value = self._completed("0.8.0\n")
        self.assertEqual(other_version(self.theirs), "0.8.0")

    def test_corrupt_cache_is_ignored(self):
        self.cache_file.write_text("{not json")
        self.assertEqual(other_version(self.theirs), "0.7.3")

    def test_unwritable_cache_does_not_raise(self):
        with (
            patch(
                "poly.utils.installs.OTHER_POLY_CACHE_FILE",
                self.root / "missing" / "x" / ".other_poly",
            ),
            patch("poly.utils.installs.Path.mkdir", side_effect=OSError("read-only")),
        ):
            self.assertEqual(other_version(self.theirs), "0.7.3")


class SessionStampTest(InstallsTestCase):
    def setUp(self):
        super().setUp()
        self.other = OtherInstall(path=self.theirs, version="0.7.3")
        self.session = self._patch(
            "poly.utils.installs.session_key", return_value="100:/dev/ttys001"
        )

    def test_first_time_is_not_warned(self):
        self.assertFalse(already_warned(self.other))

    def test_same_session_and_pair_is_warned(self):
        mark_warned(self.other)
        self.assertTrue(already_warned(self.other))

    def test_new_session_warns_again(self):
        mark_warned(self.other)
        self.session.return_value = "200:/dev/ttys002"
        self.assertFalse(already_warned(self.other))

    def test_changed_pair_warns_again(self):
        mark_warned(self.other)
        self.assertFalse(already_warned(OtherInstall(path=self.theirs, version="0.7.4")))

    def test_stamp_is_one_json_line(self):
        mark_warned(self.other)
        lines = self.stamp_file.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        stamp = json.loads(lines[0])
        self.assertEqual(stamp["session"], "100:/dev/ttys001")
        self.assertEqual(
            stamp["pair"], [self.theirs, "0.7.3", os.path.abspath(self.ours), "0.71.0"]
        )

    def test_corrupt_stamp_is_not_warned_and_does_not_raise(self):
        self.stamp_file.write_text("{nope")
        self.assertFalse(already_warned(self.other))

    def test_unwritable_stamp_does_not_raise(self):
        with (
            patch("poly.utils.installs.SHADOW_SEEN_FILE", self.root / "ro" / "x" / ".shadow_seen"),
            patch("poly.utils.installs.Path.mkdir", side_effect=OSError("read-only")),
        ):
            mark_warned(self.other)
        self.assertFalse(already_warned(self.other))


class SessionKeyTest(InstallsTestCase):
    def test_session_key_posix_uses_sid_and_tty(self):
        with (
            patch("poly.utils.installs._is_windows", return_value=False),
            patch("poly.utils.installs.os.getsid", return_value=42, create=True),
            patch("poly.utils.installs.os.ttyname", return_value="/dev/ttys009", create=True),
        ):
            self.assertEqual(installs.session_key(), "42:/dev/ttys009")

    def test_session_key_falls_back_to_parent_pid(self):
        with (
            patch("poly.utils.installs.os.ttyname", side_effect=OSError("not a tty"), create=True),
            patch("poly.utils.installs.os.getppid", return_value=7),
        ):
            self.assertEqual(installs.session_key(), "ppid:7")

    def test_session_key_windows_uses_parent_pid(self):
        with (
            patch("poly.utils.installs._is_windows", return_value=True),
            patch("poly.utils.installs.os.getppid", return_value=7),
        ):
            self.assertEqual(installs.session_key(), "ppid:7")


class ShadowJsonFieldTest(InstallsTestCase):
    def test_absent_when_not_shadowed(self):
        self._set_path(self.ours_dir, self.theirs_dir)
        self.assertEqual(shadow_json_field(), {})

    def test_present_when_shadowed_and_computed_once(self):
        self.run.side_effect = None
        self.run.return_value = self._completed("0.7.3\n")
        self._set_path(self.theirs_dir, self.ours_dir)
        expected = {"shadowed_by": {"path": self.theirs, "version": "0.7.3"}}
        self.assertEqual(shadow_json_field(), expected)
        with patch("poly.utils.installs.shadowing_install", side_effect=AssertionError("cached")):
            self.assertEqual(shadow_json_field(), expected)

    def test_present_regardless_of_the_session_stamp(self):
        """An agent has no memory of the last run: the field is never throttled."""
        self.run.side_effect = None
        self.run.return_value = self._completed("0.7.3\n")
        self._set_path(self.theirs_dir, self.ours_dir)
        mark_warned(OtherInstall(path=self.theirs, version="0.7.3"))
        self.assertIn("shadowed_by", shadow_json_field())

    def test_returns_a_copy(self):
        self._set_path(self.ours_dir)
        shadow_json_field()["shadowed_by"] = "mutated"
        self.assertEqual(shadow_json_field(), {})


if __name__ == "__main__":
    unittest.main()
