"""Auto-generate CLI options reference from poly --help output.

Runs at mkdocs build time via mkdocs-gen-files. Requires the poly CLI to be
installed in the build environment (pip install -e ..).
"""

import subprocess

import mkdocs_gen_files

COMMANDS = [
    "init",
    "pull",
    "push",
    "status",
    "diff",
    "revert",
    "branch",
    "format",
    "validate",
    "review",
    "chat",
    "docs",
]


def get_help(*args: str) -> str:
    """Return help text for a poly command, or a placeholder if poly is not installed."""
    try:
        result = subprocess.run(
            ["poly", *args, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return (result.stdout or result.stderr).strip()
    except FileNotFoundError:
        cmd = "poly " + " ".join(args) if args else "poly"
        return f"(poly not installed — run `{cmd} --help` locally to see output)"
    except subprocess.TimeoutExpired:
        return "(timed out fetching help output)"


with mkdocs_gen_files.open("reference/cli-options.md", "w") as f:
    f.write(
        """\
---
title: CLI options
description: Full help output for all poly commands. Auto-generated from the installed CLI.
---

# CLI options

Full `--help` output for every `poly` command. This page is auto-generated at build
time from the installed CLI, so it always reflects the current version.

"""
    )

    f.write(f"## `poly`\n\n```\n{get_help()}\n```\n\n")

    for cmd in COMMANDS:
        f.write(f"## `poly {cmd}`\n\n```\n{get_help(cmd)}\n```\n\n")
