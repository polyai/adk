"""Which ``poly`` is running, and whether a different one comes first on PATH.

``uv tool install polyai-adk`` puts ``poly`` in ``~/.local/bin``. When an older
``poly`` sits earlier on PATH (a brew or pip install from before), typing ``poly``
keeps running the old one and nothing says so. These helpers let the binary that
*is* running notice that it is not the one plain ``poly`` would run, so a command
can say so at a terminal and in ``--json``.

A check can only run inside the binary that is executing: when the old ``poly`` is
first on PATH and the user types ``poly``, the old code runs and nothing here can
speak. The helpers pay off when the new binary is invoked by path, via ``uvx``, or
right after ``uv tool install`` while an older copy is still ahead.

Nothing in this module raises out to the caller: every public function returns a
safe default on any failure, because none of this may break the command the user
actually ran.

Copyright PolyAI Limited
"""

import json
import logging
import os
import string
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from poly.constants import POLY_HOME_DIR

logger = logging.getLogger(__name__)

PACKAGE_NAME = "polyai-adk"
COMMAND_NAME = "poly"
UNKNOWN_VERSION = "unknown"

# Cache of other binaries' ``--version`` answers, keyed by path and invalidated by
# mtime and size, so a shadowed machine runs the foreign binary once, not once per
# command.
OTHER_POLY_CACHE_FILE = Path(POLY_HOME_DIR) / ".other_poly"
# The "already warned" stamp: one JSON line with the terminal session key and the
# (other path, other version, running path, running version) pair it was shown for.
SHADOW_SEEN_FILE = Path(POLY_HOME_DIR) / ".shadow_seen"

OTHER_VERSION_TIMEOUT_SECONDS = 3.0
OTHER_VERSION_MAX_CHARS = 40
# Set in the child so an old ADK does not pay for its own PyPI check while we are
# only asking it for a version string.
UPDATE_CHECK_OPT_OUT_ENV_VAR = "POLY_NO_UPDATE_CHECK"
DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD"


@dataclass(frozen=True)
class OtherInstall:
    """A ``poly`` on PATH that is not the running install."""

    path: str
    version: str  # UNKNOWN_VERSION when it cannot be read


@dataclass(frozen=True)
class RunningBinary:
    """The binary that is executing, in the two forms the code needs."""

    display_path: str  # abspath(sys.argv[0]); matches ``which -a``; for messages and JSON
    compare_path: str  # realpath of the same; for identity


def _is_windows() -> bool:
    return os.name == "nt"


def _pathext() -> list[str]:
    """Return the executable extensions Windows applies when resolving a command."""
    raw = os.environ.get("PATHEXT") or DEFAULT_PATHEXT
    # PATHEXT is a Windows variable and is always ";"-separated.
    return [ext.lower() for ext in raw.split(";") if ext]


def _identity(path: str) -> str:
    """Normalise a path for an equality check.

    On Windows uv's ``.exe`` trampoline runs ``python.exe <the .exe>`` and the embedded
    script strips the ``.exe`` from ``sys.argv[0]``, so the running binary reports
    itself without an extension while the PATH entry has one. Comparing with any
    PATHEXT extension stripped makes the two agree.
    """
    resolved = os.path.realpath(path)
    if _is_windows():
        root, ext = os.path.splitext(resolved)
        if ext.lower() in _pathext():
            resolved = root
        return os.path.normcase(resolved)
    return resolved


def running_binary() -> RunningBinary:
    """Return the path of the binary that is executing, for display and for identity."""
    display_path = os.path.abspath(sys.argv[0]) if sys.argv and sys.argv[0] else sys.executable
    return RunningBinary(display_path=display_path, compare_path=_identity(display_path))


def running_version() -> str:
    """Return the installed package version, or ``"unknown"``."""
    from importlib.metadata import version

    try:
        return version(PACKAGE_NAME)
    except Exception:
        return UNKNOWN_VERSION


def is_self(candidate: str) -> bool:
    """Check whether a PATH candidate is the running install.

    Two rules, because one alone warns about its own install in some layout: the
    candidate resolves to the same file as ``sys.argv[0]`` (uv shim scripts, symlinks
    into a Cellar), or it lives under ``sys.prefix`` (``python -m poly`` and editable
    installs, whose ``argv[0]`` is on no PATH entry at all).
    """
    try:
        resolved = _identity(candidate)
        if resolved == running_binary().compare_path:
            return True
        prefix = _identity(sys.prefix)
        return resolved == prefix or resolved.startswith(prefix.rstrip(os.sep) + os.sep)
    except Exception as e:
        logger.debug(f"Could not compare {candidate!r} with the running binary: {e}")
        # Better to miss a warning than to warn about ourselves.
        return True


def path_candidates(name: str = COMMAND_NAME) -> list[str]:
    """Return every ``name`` on PATH, in PATH order, unresolved.

    Mirrors what the shell does: each directory in turn, and on Windows each PATHEXT
    extension in turn within a directory. Only existing, executable regular files
    count.
    """
    candidates: list[str] = []
    names = [name]
    if _is_windows():
        has_ext = os.path.splitext(name)[1].lower() in _pathext()
        names = [name] if has_ext else [name + ext for ext in _pathext()]
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        for candidate_name in names:
            candidate = os.path.join(directory, candidate_name)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                candidates.append(candidate)
    return candidates


def shadowing_install() -> OtherInstall | None:
    """Return the ``poly`` that plain ``poly`` would run, if it is not this one.

    Only the first PATH entry matters: entries after it are not what ``poly`` runs.
    Also covers the running binary not being on PATH at all (``uvx``, an explicit
    path), in which case the first entry is a different install by definition.
    """
    try:
        candidates = path_candidates()
        if not candidates or is_self(candidates[0]):
            return None
        first = candidates[0]
        return OtherInstall(path=first, version=other_version(first))
    except Exception as e:
        logger.debug(f"PATH shadow check failed: {e}")
        return None


def _sanitise_version(stdout: str) -> str:
    """Keep the first stdout line, printable characters only, capped in length."""
    first_line = stdout.splitlines()[0] if stdout.splitlines() else ""
    printable = "".join(
        ch for ch in first_line if ch in string.printable and ch not in "\t\n\r\x0b\x0c"
    )
    cleaned = printable.strip()[:OTHER_VERSION_MAX_CHARS].strip()
    return cleaned or UNKNOWN_VERSION


def _read_version_cache() -> dict:
    try:
        data = json.loads(OTHER_POLY_CACHE_FILE.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_version_cache(cache: dict) -> None:
    try:
        OTHER_POLY_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        OTHER_POLY_CACHE_FILE.write_text(json.dumps(cache))
    except (OSError, TypeError, ValueError):
        pass


def other_version(path: str, timeout: float = OTHER_VERSION_TIMEOUT_SECONDS) -> str:
    """Return what ``<path> --version`` prints, or ``"unknown"``.

    This runs a program we did not install, so it is bounded: ``--version`` is the
    only argument, stdin is closed, output is captured, the child skips its own
    update check, the call times out, and the output is reduced to a short printable
    string. The answer is cached per ``(path, mtime, size)`` so the subprocess runs
    once per foreign binary, not once per command.
    """
    try:
        stat = os.stat(path)
        key = {"mtime": stat.st_mtime, "size": stat.st_size}
    except OSError:
        return UNKNOWN_VERSION

    cache = _read_version_cache()
    entry = cache.get(path)
    if (
        isinstance(entry, dict)
        and entry.get("mtime") == key["mtime"]
        and entry.get("size") == key["size"]
    ):
        cached = entry.get("version")
        if isinstance(cached, str) and cached:
            return cached

    try:
        env = {**os.environ, UPDATE_CHECK_OPT_OUT_ENV_VAR: "1"}
        completed = subprocess.run(
            [path, "--version"],
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=timeout,
            env=env,
            text=True,
            errors="replace",
        )
        version = (
            _sanitise_version(completed.stdout) if completed.returncode == 0 else UNKNOWN_VERSION
        )
    except Exception as e:
        logger.debug(f"Could not read the version of {path!r}: {e}")
        version = UNKNOWN_VERSION

    cache[path] = {**key, "version": version}
    _write_version_cache(cache)
    return version


# -- Once per terminal session -------------------------------------------------


def session_key() -> str:
    """Identify the terminal session, so the warning shows once per tab.

    POSIX: the session id plus the controlling terminal. The session leader is the
    shell that owns the tab, and it survives the uv/uvx wrappers between the shell
    and us. Windows, or anything without a tty: the parent PID.
    """
    if not _is_windows() and hasattr(os, "getsid"):
        try:
            return f"{os.getsid(0)}:{os.ttyname(0)}"
        except OSError:
            pass
    return f"ppid:{os.getppid()}"


def _pair(other: OtherInstall) -> list[str]:
    return [other.path, other.version, running_binary().display_path, running_version()]


def already_warned(other: OtherInstall) -> bool:
    """Check whether this session has already been told about ``other``."""
    try:
        stamp = json.loads(SHADOW_SEEN_FILE.read_text())
        return (
            isinstance(stamp, dict)
            and stamp.get("session") == session_key()
            and stamp.get("pair") == _pair(other)
        )
    except Exception:
        return False


def mark_warned(other: OtherInstall) -> None:
    """Record that this session has been told about ``other``. Best effort."""
    try:
        SHADOW_SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        SHADOW_SEEN_FILE.write_text(
            json.dumps({"session": session_key(), "pair": _pair(other)}) + "\n"
        )
    except Exception as e:
        logger.debug(f"Could not write the shadow stamp: {e}")


# -- --json field ----------------------------------------------------------------

_shadow_field: dict | None = None


def shadow_json_field() -> dict:
    """Return ``{"shadowed_by": {"path", "version"}}`` while shadowed, else ``{}``.

    Computed once per process. Never throttled: an agent has no memory of the last
    run, so every ``--json`` object while shadowed carries it.
    """
    global _shadow_field
    if _shadow_field is None:
        other = shadowing_install()
        _shadow_field = (
            {"shadowed_by": {"path": other.path, "version": other.version}} if other else {}
        )
    return dict(_shadow_field)
