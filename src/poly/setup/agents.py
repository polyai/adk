"""Which coding agent is running ``poly setup``, and which are installed on the machine.

Both answers feed telemetry now and agent-mode detection and MCP configuration
later, so the agent names used here are the canonical ones: ``claude-code``,
``cursor``, ``codex``, ``claude-desktop``.

Copyright PolyAI Limited
"""

import os
import platform
import re
import shutil
import sys
from pathlib import Path

# Environment variables an agent sets in the processes it spawns, mapped to the
# agent's name. Extend as agents are identified; keep this the only list.
AGENT_ENV_MARKERS: dict[str, str] = {
    "CLAUDECODE": "claude-code",
    "CURSOR_AGENT": "cursor",
    "CODEX_SANDBOX": "codex",
}

NO_AGENT = "none"


def detect_invoking_agent(environ: dict[str, str] | None = None) -> str:
    """Name the coding agent that spawned this process, or ``"none"``.

    Args:
        environ: The environment to inspect; defaults to ``os.environ``.
    """
    env = os.environ if environ is None else environ
    for marker, agent in AGENT_ENV_MARKERS.items():
        if env.get(marker):
            return agent
    return NO_AGENT


def _claude_desktop_config_dir(home: Path) -> Path:
    system = platform.system()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "Claude"
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        return Path(appdata) / "Claude" if appdata else home / "AppData" / "Roaming" / "Claude"
    return home / ".config" / "Claude"


def detect_installed_agents(home: Path | None = None) -> list[str]:
    """List the coding agents installed for this user, by their config directories.

    Args:
        home: The user's home directory; defaults to ``Path.home()``. A parameter so
            tests can point at a fixture tree.

    Returns:
        Agent names in a fixed order, so two runs on one machine compare equal.
    """
    home = Path.home() if home is None else home
    found = []
    if (home / ".claude").is_dir() or shutil.which("claude"):
        found.append("claude-code")
    if (home / ".cursor").is_dir():
        found.append("cursor")
    if (home / ".codex").is_dir():
        found.append("codex")
    if _claude_desktop_config_dir(home).is_dir():
        found.append("claude-desktop")
    return found


def has_node() -> bool:
    """Whether ``node`` and ``npx`` are on PATH. Presence only; the skills step checks the version."""
    return shutil.which("node") is not None and shutil.which("npx") is not None


def detect_entry() -> str:
    """How the CLI was launched: ``"uvx"`` for an ephemeral ``uvx`` environment, else ``"poly"``.

    ``uvx`` runs the package from an environment under uv's cache
    (``.../uv/archive-v0/<hash>``), whereas ``uv tool install`` and ``pip``
    environments live elsewhere, so the interpreter prefix tells them apart.
    """
    # Split on both separators so the check reads the same on Windows and POSIX.
    parts = re.split(r"[\\/]", sys.prefix)
    is_uv_cache = any(part.startswith("archive-v") for part in parts) and "uv" in parts
    return "uvx" if is_uv_cache else "poly"
