"""Usage telemetry for the PolyAI ADK.

Copyright PolyAI Limited

Fires a single background HTTP POST for each CLI command so the product team
can understand how developers use the ADK (command frequency, push volume,
active users, etc.)

Identity
--------
We collect the developer's real name and email address (from git config) plus
their OS username and machine hostname.  This lets the team track usage at the
individual contributor level.

Opt-out
-------
Set ``POLY_TELEMETRY_DISABLED=1`` (or any truthy value) to suppress all
telemetry.  Useful for CI/CD pipelines or local overrides.

The call runs in a daemon thread with a hard 2-second timeout and is silently
swallowed on any error — it *never* blocks or breaks the CLI.
"""

import os
import platform
import socket
import subprocess
import threading
from importlib.metadata import version as _pkg_version
from typing import Any, Dict, Optional

_ENDPOINT = "https://analytics.us-1.platform.polyai.app/ingest/v1/adk"
_TIMEOUT_SECS = 2
_DISABLED_ENVVAR = "POLY_TELEMETRY_DISABLED"


def _is_disabled() -> bool:
    val = os.environ.get(_DISABLED_ENVVAR, "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def _git_config(key: str) -> Optional[str]:
    """Read a git config value; returns None on any failure."""
    try:
        result = subprocess.run(
            ["git", "config", "--global", key],
            capture_output=True,
            text=True,
            timeout=1,
        )
        value = result.stdout.strip()
        return value if value else None
    except Exception:
        return None


def _identity() -> Dict[str, Optional[str]]:
    """Collect real developer identity from git config and OS."""
    return {
        "user_email": _git_config("user.email"),
        "user_name": _git_config("user.name"),
        "os_username": os.getlogin() if hasattr(os, "getlogin") else None,
        "hostname": socket.gethostname(),
    }


def _adk_version() -> str:
    try:
        return _pkg_version("polyai-adk")
    except Exception:
        return "unknown"


def _post(payload: Dict[str, Any]) -> None:
    """Fire-and-forget POST; swallows all exceptions."""
    try:
        import json as _json
        import urllib.request

        data = _json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _ENDPOINT,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECS):
            pass
    except Exception:
        pass


def track(
    command: str,
    *,
    subcommand: Optional[str] = None,
    account_id: Optional[str] = None,
    project_id: Optional[str] = None,
    dry_run: bool = False,
    region: Optional[str] = None,
) -> None:
    """Track a CLI command invocation in the background.

    Parameters
    ----------
    command:
        Top-level command name, e.g. ``"push"``, ``"pull"``, ``"init"``.
    subcommand:
        Optional sub-action, e.g. ``"list"`` for ``poly branch list``.
    account_id:
        Agent Studio account ID (read from project.yaml when available).
    project_id:
        Agent Studio project ID (read from project.yaml when available).
    dry_run:
        Whether the command was invoked with ``--dry-run``.
    region:
        Agent Studio region, e.g. ``"eu-west-1"``.
    """
    if _is_disabled():
        return

    payload: Dict[str, Any] = {
        "source": "adk",
        "command": command,
        "adk_version": _adk_version(),
        "python_version": platform.python_version(),
        "os": platform.system().lower(),
        **_identity(),
    }
    if subcommand:
        payload["subcommand"] = subcommand
    if account_id:
        payload["account_id"] = account_id
    if project_id:
        payload["project_id"] = project_id
    if dry_run:
        payload["dry_run"] = True
    if region:
        payload["region"] = region

    t = threading.Thread(target=_post, args=(payload,), daemon=True)
    t.start()
