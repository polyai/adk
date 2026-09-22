#!/usr/bin/env python3
"""Sync type stubs from genai_lambda_runtime into src/poly/types/.

Uses mypy's ``stubgen`` to generate stubs, then post-processes them into
runtime-safe ``.py`` modules — the committed files are byte-identical to what
``save_imports`` later copies into a user project's ``_gen/`` package, so
review and CI validate exactly what ships:
- Rewrites ``runtime.`` / ``utils.`` imports to relative
- Injects ``__all__`` from imports.json
- Drops imports of internal-only modules, erasing their names to ``Any``
- Binds module-level annotation-only declarations (``X: T`` → ``X: T = ...``)
  and adds ``from __future__ import annotations`` so the stubs import cleanly
  at runtime (user files execute ``from _gen import *``)
- Prepends the copyright + linter-suppression header
- Writes ``_manifest.json`` recording the runtime commit the stubs came from
- Validates the output by importing every generated module in a subprocess,
  then runs targeted ruff checks and ``ruff format``

Two lists control what ships beyond ``imports.json``:
- ``imports.json`` (in the runtime repo) is the public surface — it decides
  which ``utils/`` modules are stubbed AND exported via ``__all__``.
- ``CLOSURE_SOURCES`` below are stubbed for typing closure only (base classes
  and annotation types referenced by public classes); they get no ``__all__``
  entry, so nothing advertises them to users.

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
from datetime import datetime, timezone
from pathlib import Path

STUB_DIR = Path(__file__).resolve().parent.parent / "src" / "poly" / "types"

# Stub conventions (forward references, ellipsis bodies) are not lint-clean as
# plain .py, and these files ship verbatim into user projects — suppress
# linters in the files themselves; the sync validates with --ignore-noqa.
# (Escaped \n form so ruff does not read the directives as this file's own.)
STUB_HEADER = "# Copyright PolyAI Limited\n# flake8: noqa\n# ruff: noqa\n# type: ignore\n"

FUTURE_IMPORT = "from __future__ import annotations\n\n"

# Third-party modules imported by stubs that are not polyai-adk dependencies;
# faked during import validation (and by the _gen test harness).
FAKE_IMPORT_MODULES = {"pydantic": {"BaseModel": "object"}}

# Matches module-level annotation-only declarations e.g. "SupportedLanguageCodes: Any"
_MODULE_ANNOTATION_RE = re.compile(r"^([A-Za-z_]\w*: [^=\n]+?)\s*$", re.MULTILINE)

# Regex patterns for import rewriting
_FROM_RUNTIME_RE = re.compile(r"^from runtime\.(\S+)", re.MULTILINE)
_IMPORT_RUNTIME_RE = re.compile(r"^import runtime\.(\w+)", re.MULTILINE)
# Imports that should be dropped entirely from stubs
_DROP_IMPORT_RE = re.compile(
    r"^from (?:_typeshed|constants|utils\.deferred_logger|utils\.secret_vault) .*\n",
    re.MULTILINE,
)
# _typeshed.Incomplete -> Any
_INCOMPLETE_RE = re.compile(r"\bIncomplete\b")
# Types from dropped imports that should become Any
_UNRESOLVABLE_TYPES = re.compile(r"\bHandoffMethod\b|\bDeferredLogger\b")

# Stubbed for typing closure (base classes and annotation types referenced by
# public classes), but deliberately absent from imports.json: no __all__ entry,
# nothing advertises them to users.
CLOSURE_SOURCES = ["utils/api_connector.py"]


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


def _drop_private_reexports(source: str) -> str:
    """Drop re-exports of private names (``from .x import _y as z``).

    stubgen omits private module-level variables, so such aliases can never
    resolve within the stub tree; drop the alias and its ``__all__`` entry.
    """
    dropped: list[str] = []

    def _clean_import(m: re.Match) -> str:
        prefix, names = m.group(1), m.group(2)
        kept = []
        for part in names.split(","):
            part = part.strip()
            alias_match = re.fullmatch(r"_\w+ as (\w+)", part)
            if alias_match:
                dropped.append(alias_match.group(1))
            elif part:
                kept.append(part)
        return f"{prefix}{', '.join(kept)}\n" if kept else ""

    source = re.sub(r"^(from \S+ import )(?!\()(.+)\n", _clean_import, source, flags=re.MULTILINE)
    for name in dropped:
        source = re.sub(rf"['\"]{name}['\"],?\s*", "", source)
    return source


def _guard_relative_imports(source: str) -> str:
    """Move a stub's relative imports into an ``if TYPE_CHECKING:`` block.

    Applied to closure stubs only: a public stub may import them back, and
    stubgen promotes TYPE_CHECKING imports to unconditional ones, so leaving
    the back-edge unguarded makes the generated ``_gen`` package circular and
    unimportable at runtime. Safe because closure stubs use these names only
    in annotations, which PEP 649 never evaluates.
    """
    lines = source.splitlines(keepends=True)
    kept: list[str] = []
    guarded: list[str] = []
    last_import = -1
    for line in lines:
        if line.startswith("from ."):
            guarded.append("    " + line)
        else:
            if line.startswith(("from ", "import ")):
                last_import = len(kept)
            kept.append(line)
    if not guarded:
        return source
    block = ["from typing import TYPE_CHECKING\n", "\n", "if TYPE_CHECKING:\n", *guarded, "\n"]
    kept[last_import + 1 : last_import + 1] = block
    return "".join(kept)


def _postprocess(
    source: str, rel_path: str, all_names: list[str] | None = None, is_closure: bool = False
) -> str:
    """Apply all post-processing to a stubgen output file."""
    # Drop imports from modules we don't ship
    source = _DROP_IMPORT_RE.sub("", source)
    source = _drop_private_reexports(source)
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
    if is_closure:
        source = _guard_relative_imports(source)
    # In a stub "X: int" is complete, but these modules are imported at
    # runtime (via _gen), where an unassigned annotation binds nothing and
    # breaks "from _gen.x import X" — give module-level declarations a value.
    source = _MODULE_ANNOTATION_RE.sub(r"\1 = ...", source)
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
    # __future__ must precede everything but comments/docstrings (incl. __all__)
    source = STUB_HEADER + FUTURE_IMPORT + source
    return source


def _git(repo: Path, *args: str) -> str:
    """Run a git command in *repo* and return stdout, exiting on failure."""
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"Error: git {' '.join(args)} failed in {repo}:\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout.strip()


def _check_runtime_up_to_date(python_root: Path) -> None:
    """Verify the runtime checkout is clean and matches origin/main.

    Stubs are committed to this repo, so generating them from a stale or
    dirty runtime checkout would silently bake in wrong types.
    """
    _git(python_root, "fetch", "--quiet", "origin", "main")
    head = _git(python_root, "rev-parse", "HEAD")
    origin_main = _git(python_root, "rev-parse", "origin/main")
    if head != origin_main:
        print(
            f"Error: runtime checkout is not on origin/main "
            f"(HEAD {head[:12]} != origin/main {origin_main[:12]}).\n"
            f"Run `git -C {python_root} checkout main && git -C {python_root} pull` "
            f"or pass --skip-git-check to sync anyway.",
            file=sys.stderr,
        )
        sys.exit(1)
    dirty = _git(python_root, "status", "--porcelain")
    if dirty:
        print(
            f"Error: runtime checkout has uncommitted changes:\n{dirty}\n"
            f"Commit or stash them, or pass --skip-git-check to sync anyway.",
            file=sys.stderr,
        )
        sys.exit(1)


_VALIDATE_SNIPPET = """
import importlib, json, pkgutil, sys, types

for name, attrs in json.loads(sys.argv[1]).items():
    try:
        importlib.import_module(name)
    except ModuleNotFoundError:
        fake = types.ModuleType(name)
        for attr, value in attrs.items():
            setattr(fake, attr, eval(value))
        sys.modules[name] = fake

import poly.types

errors = []
names = [poly.types.__name__] + [
    m.name for m in pkgutil.walk_packages(poly.types.__path__, "poly.types.")
]
for module_name in names:
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        errors.append(f"{module_name}: import failed: {e!r}")
        continue
    for export in getattr(module, "__all__", []):
        if not hasattr(module, export):
            errors.append(f"{module_name}: __all__ name {export!r} is unbound")
if errors:
    print("\\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"  validated {len(names)} modules importable, all __all__ names bound")
"""


def _validate_generated_stubs() -> None:
    """Import every generated module in a subprocess; fail on any error.

    This is the invariant that matters: user projects execute these files
    (via ``from _gen import *``), so "valid stub" means "importable module".
    Catches unresolved imports, cycles, and unbound ``__all__`` names.
    """
    result = subprocess.run(
        ["uv", "run", "python", "-c", _VALIDATE_SNIPPET, json.dumps(FAKE_IMPORT_MODULES)],
        capture_output=True,
        text=True,
        cwd=str(STUB_DIR.parent.parent.parent),
    )
    if result.returncode != 0:
        print(
            "Generated stubs failed import validation — add the module to CLOSURE_SOURCES, "
            "erase the names via the drop/Any rules, or fake the third-party import in "
            f"FAKE_IMPORT_MODULES:\n{result.stdout}{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    print(result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync runtime type stubs using stubgen")
    parser.add_argument(
        "--python-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent.parent / "genai_lambda_runtime" / "python",
        help="Path to the genai_lambda_runtime/python directory",
    )
    parser.add_argument(
        "--skip-git-check",
        action="store_true",
        help="Skip verifying the runtime checkout is clean and up to date with origin/main",
    )
    args = parser.parse_args()

    python_root: Path = args.python_root
    if not python_root.is_dir():
        print(f"Error: python root not found: {python_root}", file=sys.stderr)
        sys.exit(1)

    if not args.skip_git_check:
        _check_runtime_up_to_date(python_root)

    # imports.json drives __all__ generation (not which files to stub)
    imports_map = _load_imports_json(python_root)

    # Stub all of runtime/ plus individual utils files from imports.json
    runtime_dir = python_root / "runtime"
    if not runtime_dir.is_dir():
        print(f"Error: runtime directory not found: {runtime_dir}", file=sys.stderr)
        sys.exit(1)

    sources: list[str] = [str(runtime_dir)]
    # Add individual utils/ files referenced in imports.json
    utils_keys: list[str] = []
    imports_file = python_root / "assets" / "imports.json"
    if imports_file.exists():
        with open(imports_file, encoding="utf-8") as f:
            utils_keys = [key for key in json.load(f) if key.startswith("utils/")]
    for key in utils_keys + [k for k in CLOSURE_SOURCES if k not in utils_keys]:
        source_file = python_root / key
        if source_file.exists():
            sources.append(str(source_file))
        else:
            print(f"Error: source not found: {source_file}", file=sys.stderr)
            sys.exit(1)

    # Run stubgen
    with tempfile.TemporaryDirectory() as tmpdir:
        cmd = ["uv", "run", "--extra", "dev", "stubgen", "-o", tmpdir] + sources
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
                is_closure = f"{pkg}/{rel_py}" in CLOSURE_SOURCES
                processed = _postprocess(source, rel_py, all_names, is_closure=is_closure)

                dest = STUB_DIR / rel.with_suffix(".py")
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(processed, encoding="utf-8")
                print(f"  OK   {rel_py}")
                updated += 1

    # One format: any leftover .pyi is from a previous generation scheme
    stale = list(STUB_DIR.rglob("*.pyi"))
    for stale_file in stale:
        stale_file.unlink()
    if stale:
        print(f"  removed {len(stale)} stale .pyi files")

    manifest = {
        "runtime_sha": _git(python_root, "rev-parse", "HEAD"),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modules": updated,
    }
    (STUB_DIR / "_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    _validate_generated_stubs()

    # The baked-in "# ruff: noqa" would hide real problems from plain ruff, so
    # check with --ignore-noqa for the classes of error a stub must not have
    # (undefined names / unbound __all__ entries), then normalize formatting.
    for cmd in (
        ["uv", "run", "ruff", "check", "--ignore-noqa", "--select", "F821,F822", str(STUB_DIR)],
        ["uv", "run", "ruff", "format", str(STUB_DIR)],
    ):
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(
                f"{' '.join(cmd[2:])} failed on generated stubs:\n{result.stdout}{result.stderr}",
                file=sys.stderr,
            )
            sys.exit(1)

    print(f"\nSynced {updated} stub files to {STUB_DIR}")


if __name__ == "__main__":
    main()
