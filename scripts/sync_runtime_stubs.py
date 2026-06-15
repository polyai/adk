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
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

STUB_DIR = Path(__file__).resolve().parent.parent / "src" / "poly" / "types"

STUB_HEADER = """\
# Copyright PolyAI Limited
"""

# Regex patterns for import rewriting
_FROM_RUNTIME_RE = re.compile(r"^from runtime\.(\S+)", re.MULTILINE)
_IMPORT_RUNTIME_RE = re.compile(r"^import runtime\.(\w+)", re.MULTILINE)
# Imports that should be dropped entirely from stubs
_DROP_IMPORT_RE = re.compile(
    r"^from (?:_typeshed|constants|utils\.api_connector|utils\.secret_vault) .*\n",
    re.MULTILINE,
)
# _typeshed.Incomplete -> Any
_INCOMPLETE_RE = re.compile(r"\bIncomplete\b")
# Types from dropped imports that should become Any
_UNRESOLVABLE_TYPES = re.compile(r"\bHandoffMethod\b|\bApiIntegrations\b")


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


def _load_imports_json(python_root: Path) -> dict[str, list[str]]:
    """Load imports.json and return a mapping of stub rel_path → __all__ names.

    *python_root* is the ``python/`` directory containing both ``runtime/``
    and ``utils/`` alongside ``assets/imports.json``.

    The keys in imports.json use ``runtime/X.py`` or ``utils/X.py`` form;
    we strip the top-level package prefix to get the stub-relative path.
    """
    imports_file = python_root / "assets" / "imports.json"
    if not imports_file.exists():
        return {}
    with open(imports_file, encoding="utf-8") as f:
        raw = json.load(f)
    result: dict[str, list[str]] = {}
    for key, names in raw.items():
        # "runtime/conversation.py" -> "conversation.py"
        # "utils/secret_vault.py"   -> "secret_vault.py"
        rel = key.split("/", 1)[1] if "/" in key else key
        result.setdefault(rel, []).extend(names)
    return result


def _source_files_from_imports_json(python_root: Path) -> list[Path]:
    """Return the list of source files referenced in imports.json."""
    imports_file = python_root / "assets" / "imports.json"
    if not imports_file.exists():
        return []
    with open(imports_file, encoding="utf-8") as f:
        raw = json.load(f)
    files = []
    for key in raw:
        source = python_root / key
        if source.exists():
            files.append(source)
    return files


def _ensure_any_imported(source: str) -> str:
    """Add ``Any`` to the typing import if not already present."""
    if "from typing import" in source:
        return re.sub(
            r"from typing import (.+)",
            lambda m: f"from typing import {m.group(1)}"
            if "Any" in m.group(1)
            else f"from typing import Any, {m.group(1)}",
            source,
            count=1,
        )
    return "from typing import Any\n" + source


def _postprocess(source: str, rel_path: str, all_names: list[str] | None = None) -> str:
    """Apply all post-processing to a stubgen output file."""
    # Drop imports from modules we don't ship
    source = _DROP_IMPORT_RE.sub("", source)
    # Replace unresolvable types and Incomplete with Any
    needs_any = False
    for pattern in (_INCOMPLETE_RE, _UNRESOLVABLE_TYPES):
        if pattern.search(source):
            source = pattern.sub("Any", source)
            needs_any = True
    if needs_any:
        source = _ensure_any_imported(source)
    # Relativize runtime/utils imports
    source = _relativize_imports(source, rel_path)
    # Inject __all__ from imports.json, filtered to names available in the stub
    if all_names:
        tree = ast.parse(source)
        available: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                available.add(node.name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        available.add(target.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                available.add(node.target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    available.add(alias.asname or alias.name)
        filtered = [n for n in all_names if n in available]
        if filtered:
            all_line = "__all__ = " + repr(filtered) + "\n\n"
            source = all_line + source
    # Add header
    source = STUB_HEADER + source
    return source


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync runtime type stubs using stubgen")
    parser.add_argument(
        "--python-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "genai_lambda_runtime" / "python",
        help="Path to the genai_lambda_runtime/python directory",
    )
    args = parser.parse_args()

    python_root: Path = args.python_root
    if not python_root.is_dir():
        print(f"Error: python root not found: {python_root}", file=sys.stderr)
        sys.exit(1)

    # imports.json drives which files to stub and their __all__
    imports_map = _load_imports_json(python_root)
    source_files = _source_files_from_imports_json(python_root)
    if not source_files:
        print("Error: no source files found via imports.json", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(source_files)} source files in imports.json")

    # Run stubgen on all source files at once
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = ["uv", "run", "stubgen", "-o", tmpdir] + [str(f) for f in source_files]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"stubgen failed:\n{result.stderr}", file=sys.stderr)
            sys.exit(1)
        print(result.stdout.strip())

        # stubgen nests output under the source tree structure;
        # find the common root (python/) and process each package separately
        tmpdir_path = Path(tmpdir)
        updated = 0

        # Process each top-level package (runtime/, utils/) that has stubs
        for pkg in ("runtime", "utils"):
            stub_pkg = tmpdir_path / "python" / pkg
            if not stub_pkg.is_dir():
                stub_pkg = tmpdir_path / pkg
            if not stub_pkg.is_dir():
                continue

            for pyi_file in sorted(stub_pkg.rglob("*.pyi")):
                rel = pyi_file.relative_to(stub_pkg)
                # imports_map keys use .py paths
                rel_py = str(rel.with_suffix(".py"))

                source = pyi_file.read_text(encoding="utf-8")
                all_names = imports_map.get(rel_py)
                processed = _postprocess(source, rel_py, all_names)

                dest = STUB_DIR / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(processed, encoding="utf-8")
                print(f"  OK   {rel}")
                updated += 1

    print(f"\nSynced {updated} stub files to {STUB_DIR}")


if __name__ == "__main__":
    main()
