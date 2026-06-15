#!/usr/bin/env python3
"""Sync type stubs from genai_lambda_runtime into src/poly/types/.

Uses mypy's ``stubgen`` to generate .pyi stubs, then post-processes them:
- Renames .pyi → .py
- Rewrites ``runtime.`` / ``utils.`` imports to relative
- Adds copyright header and noqa directives
- Removes internal-only modules

Usage:
    python scripts/sync_runtime_stubs.py [--runtime-path PATH]

Default runtime path: ../genai_lambda_runtime/python/runtime
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

STUB_DIR = Path(__file__).resolve().parent.parent / "src" / "poly" / "types"

STUB_HEADER = """\
# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
"""

# Files to exclude from the output — internal implementation details
# that aren't part of the user-facing API.
_EXCLUDE_FILES = frozenset(
    {
        "llm_client.pyi",
        "state_utils.pyi",
        "analytics.pyi",
        "integration_utils.pyi",
    }
)

# Regex patterns for import rewriting
_FROM_RUNTIME_RE = re.compile(r"^from runtime\.(\S+)", re.MULTILINE)
_IMPORT_RUNTIME_RE = re.compile(r"^import runtime\.(\w+)", re.MULTILINE)
# Imports that should be dropped entirely from stubs
_DROP_IMPORT_RE = re.compile(
    r"^(?:from (?:_typeshed|constants|utils\.api_connector|utils\.secret_vault)"
    r"|from dataclasses import).*\n",
    re.MULTILINE,
)
# _typeshed.Incomplete -> Any
_INCOMPLETE_RE = re.compile(r"\bIncomplete\b")


def _relativize_imports(source: str, rel_path: str) -> str:
    """Rewrite absolute runtime/utils imports to relative ones.

    *rel_path* is the file path relative to the runtime root
    (e.g. "conversation.py" or "integrations/integrations.py").
    """
    source_pkg_parts = list(Path(rel_path).parent.parts)
    depth = len(source_pkg_parts)

    def _rewrite_from(m: re.Match) -> str:
        """Rewrite ``from runtime.X.Y import`` to relative form."""
        mod_tail = m.group(1)  # e.g. "integrations.integration"
        mod_parts = mod_tail.split(".")

        # Find shared prefix with source package
        common = 0
        for a, b in zip(source_pkg_parts, mod_parts):
            if a == b:
                common += 1
            else:
                break

        ups = len(source_pkg_parts) - common
        dots = "." * (ups + 1)
        remainder = ".".join(mod_parts[common:])
        rel = f"{dots}{remainder}" if remainder else dots
        return f"from {rel}"

    def _rewrite_import(m: re.Match) -> str:
        """Rewrite ``import runtime.X`` to ``from . import X``."""
        mod_name = m.group(1)
        if depth == 0:
            return f"from . import {mod_name}"
        dots = "." * (depth + 1)
        return f"from {dots} import {mod_name}"

    source = _FROM_RUNTIME_RE.sub(_rewrite_from, source)
    source = _IMPORT_RUNTIME_RE.sub(_rewrite_import, source)
    # Also handle from utils.X imports
    source = re.sub(
        r"^from utils\.(\S+)",
        lambda m: _rewrite_from(
            type(m)(m.re, f"runtime.{m.group(1)}", m.string, m.start(), m.end())
        )
        if False
        else f"from {'.' * (depth + 1)}{m.group(1)}",
        source,
        flags=re.MULTILINE,
    )
    return source


def _postprocess(source: str, rel_path: str) -> str:
    """Apply all post-processing to a stubgen output file."""
    # Drop imports we don't want
    source = _DROP_IMPORT_RE.sub("", source)
    # Replace Incomplete with Any
    if _INCOMPLETE_RE.search(source):
        source = _INCOMPLETE_RE.sub("Any", source)
        if "from typing import" in source:
            source = re.sub(
                r"from typing import (.+)",
                lambda m: f"from typing import {m.group(1)}"
                if "Any" in m.group(1)
                else f"from typing import Any, {m.group(1)}",
                source,
                count=1,
            )
        else:
            source = "from typing import Any\n" + source
    # Relativize imports
    source = _relativize_imports(source, rel_path)
    # Add header
    source = STUB_HEADER + source
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync runtime type stubs using stubgen")
    parser.add_argument(
        "--runtime-path",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent
        / "genai_lambda_runtime"
        / "python"
        / "runtime",
        help="Path to the genai_lambda_runtime/python/runtime directory",
    )
    args = parser.parse_args()

    runtime_path: Path = args.runtime_path
    if not runtime_path.is_dir():
        print(f"Error: runtime path not found: {runtime_path}", file=sys.stderr)
        sys.exit(1)

    # Run stubgen into a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["uv", "run", "stubgen", str(runtime_path), "-o", tmpdir],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"stubgen failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(result.stdout.strip())

        # Find the generated stubs (stubgen nests under the source structure)
        stub_root = Path(tmpdir) / "python" / "runtime"
        if not stub_root.is_dir():
            # Try without python/ prefix
            stub_root = Path(tmpdir) / "runtime"
        if not stub_root.is_dir():
            print(f"Error: no stubs found under {tmpdir}", file=sys.stderr)
            sys.exit(1)

        # Copy and post-process each stub
        updated = 0
        for pyi_file in sorted(stub_root.rglob("*.pyi")):
            rel = pyi_file.relative_to(stub_root)

            if rel.name in _EXCLUDE_FILES:
                print(f"  SKIP {rel} (internal)")
                continue

            source = pyi_file.read_text(encoding="utf-8")
            # rel_path as string with .py extension for import relativizing
            rel_str = str(rel.with_suffix(".py"))
            processed = _postprocess(source, rel_str)

            dest = STUB_DIR / rel.with_suffix(".py")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(processed, encoding="utf-8")
            print(f"  OK   {rel.with_suffix('.py')}")
            updated += 1

    print(f"\nSynced {updated} stub files to {STUB_DIR}")


if __name__ == "__main__":
    main()
