#!/usr/bin/env python3
"""Verify that a real ``poly update`` leaves a working CLI, for one install method.

The test suite runs from an editable install, which ``poly update`` refuses, so
it never replaces a real install. This script builds the wheel, installs it the
way a user would, runs ``poly update --cli-only --to TARGET_VERSION`` with the
installed ``poly`` executable, and then checks from a new process that ``poly``
still starts and reports the target version.

The target is an older release, so the update is a downgrade performed by this
checkout's update code against a real PyPI release.

Usage:
    python scripts/verify_update.py {pip,uv-pip,uv-tool,pipx}
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from verify_wheel import _run, _stage_clean_source

TARGET_VERSION = "0.77.0"
METHODS = ("pip", "uv-pip", "uv-tool", "pipx")
BIN_DIR = "Scripts" if sys.platform == "win32" else "bin"
EXE_SUFFIX = ".exe" if sys.platform == "win32" else ""


def _path_without_uv(path: str) -> str:
    """Drop every PATH entry that holds uv, so the CLI detects a plain pip install."""
    entries = path.split(os.pathsep)
    return os.pathsep.join(e for e in entries if not (Path(e) / f"uv{EXE_SUFFIX}").exists())


def _install(method: str, wheel: Path, root: Path, env: dict[str, str]) -> Path:
    """Install the wheel with ``method`` under ``root``.

    Tool directories are named so that their paths match the shapes the CLI
    uses to detect uv tool and pipx installs.

    Returns:
        The installed ``poly`` executable.
    """
    if method in ("pip", "uv-pip"):
        venv = root / "venv"
        python = venv / BIN_DIR / f"python{EXE_SUFFIX}"
        if method == "pip":
            _run([sys.executable, "-m", "venv", str(venv)])
            _run([str(python), "-m", "pip", "install", str(wheel)])
        else:
            _run(["uv", "venv", str(venv)])
            _run(["uv", "pip", "install", "--python", str(python), str(wheel)])
            # 'uv pip install' targets the active venv, as it would for a user who
            # activated theirs.
            env["VIRTUAL_ENV"] = str(venv)
        return venv / BIN_DIR / f"poly{EXE_SUFFIX}"

    bin_dir = root / "bin"
    if method == "uv-tool":
        env["UV_TOOL_DIR"] = str(root / "uv" / "tools")
        env["UV_TOOL_BIN_DIR"] = str(bin_dir)
        _run(["uv", "tool", "install", str(wheel)], env=env)
    else:
        env["PIPX_HOME"] = str(root / "pipx")
        env["PIPX_BIN_DIR"] = str(bin_dir)
        _run(["pipx", "install", str(wheel)], env=env)
    return bin_dir / f"poly{EXE_SUFFIX}"


def _report_leftovers(root: Path) -> None:
    """List folders pip renamed aside (``~oly`` and similar) and never restored."""
    for path in sorted(root.rglob("~*")):
        print(f"Left behind: {path}")


def main() -> None:
    """Install, update and check the CLI with the requested install method."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("method", choices=METHODS)
    method = parser.parse_args().method
    if shutil.which("uv") is None:
        sys.exit("uv is required to build the wheel")

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        root = Path(tmp)
        staged = _stage_clean_source(root)
        dist = root / "dist"
        _run(["uv", "build", "--wheel", "--out-dir", str(dist)], cwd=str(staged))
        wheel = next(dist.glob("*.whl"))

        env = {**os.environ, "POLY_NO_UPDATE_CHECK": "1"}
        poly = _install(method, wheel, root / "install", env)
        if method == "pip":
            env["PATH"] = _path_without_uv(env["PATH"])

        # A neutral working directory, so no project or .venv nearby is picked up.
        workdir = root / "work"
        workdir.mkdir()

        update = subprocess.run(
            [str(poly), "update", "--cli-only", "--to", TARGET_VERSION],
            cwd=workdir,
            env=env,
            capture_output=True,
            text=True,
        )
        print(f"poly update exited {update.returncode}\n{update.stdout}{update.stderr}")

        version = subprocess.run(
            [str(poly), "--version"], cwd=workdir, env=env, capture_output=True, text=True
        )
        print(f"poly --version exited {version.returncode}\n{version.stdout}{version.stderr}")
        _report_leftovers(root / "install")

        if update.returncode != 0 or version.returncode != 0:
            sys.exit(f"FAILED ({method}): poly update did not leave a working CLI")
        if TARGET_VERSION not in version.stdout:
            sys.exit(f"FAILED ({method}): expected {TARGET_VERSION}, got {version.stdout!r}")
        print(f"OK ({method}): poly update installed {TARGET_VERSION} and poly still starts")


if __name__ == "__main__":
    main()
