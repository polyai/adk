"""Detects the user's shell profile and persists an environment variable into it.

On Windows, "the profile" is the user's registry environment block
(``HKCU\\Environment``) rather than a file, since that is what actually makes
a variable visible to new processes system-wide.

Copyright PolyAI Limited
"""

import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Marker written immediately above a line this module added, so a later run
# can tell "we wrote this" apart from a line the user added by hand, and so
# replacing a value in place never leaves a duplicate marker behind.
MARKER_COMMENT = "# Added by poly onboard"

# HWND_BROADCAST / WM_SETTINGCHANGE / SMTO_ABORTIFHUNG, used to notify running
# processes (Explorer, the Start menu, already-open terminals) that the user
# environment block changed, without requiring a reboot or logoff.
_HWND_BROADCAST = 0xFFFF
_WM_SETTINGCHANGE = 0x1A
_SMTO_ABORTIFHUNG = 0x0002

_WINDOWS_ENVIRONMENT_DISPLAY_PATH = "HKCU\\Environment"


def _is_windows() -> bool:
    """Whether to use the Windows registry environment instead of a profile file."""
    return os.name == "nt"


def _is_macos() -> bool:
    """Whether bash should be pointed at ~/.bash_profile (macOS) rather than ~/.bashrc."""
    return sys.platform == "darwin"


@dataclass
class ProfileTarget:
    """Where an environment variable gets persisted, and in what dialect."""

    path: Path
    shell: str  # "zsh" | "bash" | "fish" | "sh" | "powershell"


class EnvVarConflict(Exception):
    """Raised when an environment variable is already set to a different value.

    Attributes:
        existing_masked: The current value, masked for safe display.
        new_masked: The value that was about to be written, masked for safe display.
        path: Where the conflicting value lives.
    """

    def __init__(self, existing_masked: str, new_masked: str, path: Path):
        self.existing_masked = existing_masked
        self.new_masked = new_masked
        self.path = path
        super().__init__(
            f"{path} already sets this variable to a different value "
            f"({existing_masked} vs {new_masked})."
        )


def detect_profile() -> ProfileTarget:
    """Detect where an environment variable should be persisted for this user.

    Returns:
        ProfileTarget: The file (or, on Windows, the registry location) and
            dialect to write to.
    """
    if _is_windows():
        return ProfileTarget(path=Path(_WINDOWS_ENVIRONMENT_DISPLAY_PATH), shell="powershell")

    home = Path(os.path.expanduser("~"))
    shell = os.path.basename(os.environ.get("SHELL", ""))

    if shell == "zsh":
        return ProfileTarget(path=home / ".zshrc", shell="zsh")
    if shell == "bash":
        if _is_macos():
            return ProfileTarget(path=home / ".bash_profile", shell="bash")
        return ProfileTarget(path=home / ".bashrc", shell="bash")
    if shell == "fish":
        return ProfileTarget(path=home / ".config" / "fish" / "config.fish", shell="fish")
    return ProfileTarget(path=home / ".profile", shell="sh")


def write_env_var(name: str, value: str, *, force: bool = False) -> tuple[ProfileTarget, str]:
    """Persist an environment variable so it is visible in new shells/processes.

    Args:
        name: The environment variable name.
        value: The value to persist. Never logged.
        force: Replace a differing existing value instead of raising.

    Returns:
        tuple[ProfileTarget, str]: The target written to, and a masked line
            describing what was written (safe to print).

    Raises:
        EnvVarConflict: `name` is already set to a different value and `force`
            is false.
    """
    if _is_windows():
        return _write_env_var_windows(name, value, force=force)
    return _write_env_var_unix(name, value, force=force)


def _format_line(shell: str, name: str, value: str) -> str:
    """Render the export line for the given shell dialect."""
    if shell == "fish":
        return f'set -gx {name} "{value}"'
    return f'export {name}="{value}"'


def _existing_line_pattern(shell: str, name: str) -> re.Pattern:
    """A regex matching a line that already sets `name`, capturing its raw value."""
    escaped_name = re.escape(name)
    if shell == "fish":
        return re.compile(rf"^\s*set\s+(?:-gx|-x)\s+{escaped_name}\s+(.*)$")
    return re.compile(rf"^\s*(?:export\s+)?{escaped_name}=(.*)$")


def _strip_quotes(raw: str) -> str:
    """Strip a single layer of matching quotes from a captured shell value."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        return raw[1:-1]
    return raw


def _write_env_var_unix(name: str, value: str, *, force: bool) -> tuple[ProfileTarget, str]:
    """Persist an environment variable into the detected shell profile file."""
    from poly.output.console import mask_secret

    target = detect_profile()
    target.path.parent.mkdir(parents=True, exist_ok=True)

    content = target.path.read_text(encoding="utf-8") if target.path.exists() else ""
    lines = content.splitlines()

    pattern = _existing_line_pattern(target.shell, name)
    existing_index: Optional[int] = None
    existing_value: Optional[str] = None
    for i, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            existing_index = i
            existing_value = _strip_quotes(match.group(1))

    masked_line = _format_line(target.shell, name, mask_secret(value))

    if existing_index is not None:
        if existing_value == value:
            return target, f"{name} already set in {target.path} (unchanged)."

        if not force:
            raise EnvVarConflict(mask_secret(existing_value), mask_secret(value), target.path)

        new_line = _format_line(target.shell, name, value)
        has_marker_above = existing_index > 0 and lines[existing_index - 1].strip() == (
            MARKER_COMMENT
        )
        lines[existing_index] = new_line
        if not has_marker_above:
            lines.insert(existing_index, MARKER_COMMENT)

        target.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return target, masked_line

    new_line = _format_line(target.shell, name, value)
    separator = "\n" if content and not content.endswith("\n") else ""
    addition = f"{MARKER_COMMENT}\n{new_line}\n"
    target.path.write_text(f"{content}{separator}{addition}", encoding="utf-8")
    return target, masked_line


def _write_env_var_windows(name: str, value: str, *, force: bool) -> tuple[ProfileTarget, str]:
    """Persist an environment variable into the user's registry environment block."""
    from poly.output.console import mask_secret

    target = ProfileTarget(path=Path(_WINDOWS_ENVIRONMENT_DISPLAY_PATH), shell="powershell")
    backend = _get_windows_registry_backend()

    existing = backend.read(name)
    if existing is not None:
        if existing == value:
            os.environ[name] = value
            return target, f"{name} already set in {target.path} (unchanged)."
        if not force:
            raise EnvVarConflict(mask_secret(existing), mask_secret(value), target.path)

    backend.write(name, value)
    backend.broadcast()
    os.environ[name] = value

    masked_line = f"{name}={mask_secret(value)}"
    return target, masked_line


class _WindowsRegistryBackend:
    """Real HKCU\\Environment access. Only ever instantiated on Windows.

    Split out from `_write_env_var_windows` so tests can substitute a fake via
    `_get_windows_registry_backend`, without importing `winreg`/`ctypes` (both
    Windows-only) at module import time - this module must still import
    cleanly on macOS/Linux CI.
    """

    def read(self, name: str) -> Optional[str]:
        """Read `name` from HKCU\\Environment, or None if it is not set."""
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, "Environment", access=winreg.KEY_READ
            ) as key:
                value, _ = winreg.QueryValueEx(key, name)
                return value
        except FileNotFoundError:
            return None

    def write(self, name: str, value: str) -> None:
        """Write `name` into HKCU\\Environment."""
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, "Environment", access=winreg.KEY_READ | winreg.KEY_WRITE
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    def broadcast(self) -> None:
        """Notify running processes that the environment block changed.

        A failure here is a warning, not an error: the registry write above
        already persisted, so a new terminal will pick up the value regardless.
        """
        try:
            import ctypes

            result = ctypes.c_ulong()
            ctypes.windll.user32.SendMessageTimeoutW(
                _HWND_BROADCAST,
                _WM_SETTINGCHANGE,
                0,
                "Environment",
                _SMTO_ABORTIFHUNG,
                5000,
                ctypes.byref(result),
            )
        except Exception:
            logger.warning("Failed to broadcast environment variable change", exc_info=True)


def _get_windows_registry_backend() -> _WindowsRegistryBackend:
    """Factory for the registry backend, patched by tests on non-Windows CI.

    Alongside `_is_windows()` and `_is_macos()`, this is one of three test
    seams in this module - patching them lets a test force a code path
    without mutating the real `os.name`/`sys.platform`, which would break
    `pathlib` and other stdlib code on the actual host platform.
    """
    return _WindowsRegistryBackend()
