#!/usr/bin/env python3
"""Verify the built wheel ships everything ``save_imports`` needs.

Dev and CI otherwise run from an editable install, where packaging mistakes
(package discovery, package-data entries) cannot surface. This script builds
the wheel, installs it into a fresh venv, generates a ``_gen`` package with
that installation, and checks the result. Checks are parse-level only:
runtime-only third-party imports in the stubs (e.g. pydantic) are not wheel
dependencies, so ``_gen`` is not imported here.

Usage:
    python scripts/verify_wheel.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Spot-checks covering each packaging mechanism: a root module, a typing-
# closure module, both nested subpackage levels, and the generated decorators.
EXPECTED_FILES = [
    "__init__.py",
    "conversation.py",
    "api_connector.py",
    "connectors/janus_api_connector.py",
    "integrations/available_integrations/opentable.py",
    "decorators.py",
]

_CHECK_SNIPPET = """
import ast, importlib.resources, json, sys
from pathlib import Path

from poly.utils import export_decorators, save_imports

base = sys.argv[1]
export_decorators(["func_parameter", "func_description", "func_latency_control"], base)
save_imports(base)

gen = Path(base) / "_gen"
errors = []
for rel in json.loads(sys.argv[2]):
    if not (gen / rel).is_file():
        errors.append(f"missing from generated _gen: {rel}")

py_files = sorted(gen.rglob("*.py"))
for f in py_files:
    try:
        ast.parse(f.read_text(encoding="utf-8"))
    except SyntaxError as e:
        errors.append(f"{f.relative_to(gen)}: does not parse: {e}")

manifest = json.loads(
    importlib.resources.files("poly.types").joinpath("_manifest.json").read_text(encoding="utf-8")
)
sha = str(manifest["runtime_sha"])[:12]

copied = len(py_files) - 1  # decorators.py is generated, not copied
if copied != manifest["modules"]:
    errors.append(f"copied module count {copied} != manifest count {manifest['modules']}")

if errors:
    print("\\n".join(errors), file=sys.stderr)
    sys.exit(1)
print(f"wheel OK: {len(py_files)} files in _gen, runtime sha {sha}")
"""


def _run(cmd: list[str], **kwargs: object) -> None:
    """Run a command, exiting with its output on failure."""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)  # type: ignore[arg-type]
    if result.returncode != 0:
        print(f"FAILED: {' '.join(cmd)}\n{result.stdout}{result.stderr}", file=sys.stderr)
        sys.exit(1)
    if result.stdout.strip():
        print(result.stdout.strip())


def _stage_clean_source(tmp_path: Path) -> Path:
    """Copy the buildable source into a clean directory.

    Building in the repo would let setuptools reuse a stale ``build/`` tree,
    silently masking packaging-config regressions — the very thing this
    script exists to catch.
    """
    staged = tmp_path / "source"
    staged.mkdir()
    shutil.copy(REPO_ROOT / "pyproject.toml", staged / "pyproject.toml")
    for name in ("README.md", "LICENSE"):
        if (REPO_ROOT / name).is_file():
            shutil.copy(REPO_ROOT / name, staged / name)
    shutil.copytree(
        REPO_ROOT / "src",
        staged / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.egg-info", "tests"),
    )
    return staged


def main() -> None:
    """Build the wheel from a clean source copy, install it fresh, and verify _gen."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        staged = _stage_clean_source(tmp_path)
        dist = tmp_path / "dist"
        _run(["uv", "build", "--wheel", "--out-dir", str(dist)], cwd=str(staged))
        wheels = list(dist.glob("*.whl"))
        if len(wheels) != 1:
            print(f"expected exactly one wheel in {dist}, found {wheels}", file=sys.stderr)
            sys.exit(1)

        venv = tmp_path / "venv"
        _run(["uv", "venv", str(venv)])
        python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        _run(["uv", "pip", "install", "--python", str(python), str(wheels[0])])

        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        _run(
            [str(python), "-c", _CHECK_SNIPPET, str(project_dir), json.dumps(EXPECTED_FILES)],
            cwd=str(tmp_path),
        )


if __name__ == "__main__":
    main()
