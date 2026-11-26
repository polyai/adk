"""Checks imports between function files across the whole project, with ty.

Copyright PolyAI Limited
"""

import ast
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.util import find_spec
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

# The Python version the platform runs function code on.
RUNTIME_PYTHON_VERSION = "3.14"

TY_TIMEOUT_SECONDS = 30

# Function files: global functions and each flow's functions. Function steps are left out, since
# how their imports resolve differs.
_FUNCTION_FILE = re.compile(r"^(?:functions|flows/[^/]+/functions)/[^/]+\.py$")
_FLOW_FUNCTION_FILE = re.compile(r"^flows/[^/]+/functions/[^/]+\.py$")
# Imports of the project's own modules, by absolute or relative name. Anything else (_gen, the
# standard library, packages the runtime provides) isn't installed locally, so ty can't resolve it.
_PROJECT_MODULE = re.compile(r"`(?:(?:functions|flows)(?:\.[\w.]+)?|\.[\w.]*)`")
# Exceptions that catch a failed import, so an import inside such a `try` is allowed to fail.
_IMPORT_ERROR_CATCHERS = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


@dataclass
class CodeError:
    """One import in a function file that doesn't resolve."""

    # Relative to the project root, with forward slashes.
    path: str
    line: int
    message: str


def function_code_errors(root_path: str) -> Optional[list[CodeError]]:
    """Imports of the project's own modules, in function files, that don't resolve.

    Every other ty diagnostic is ignored: the type rules fire constantly on valid projects,
    mostly because `conv.state` attributes are typed `Any | None`. Syntax is left to
    `Function.validate`, since pull writes some flow imports in a form that isn't valid Python.

    Args:
        root_path: The project root.

    Returns:
        The errors found, with paths relative to the root, or None if ty couldn't run.
    """
    targets = [d for d in ("functions", "flows") if os.path.isdir(os.path.join(root_path, d))]
    if not targets:
        return []
    # Without ty, `python -m ty` exits 1 with no output, which would read as no errors.
    if find_spec("ty") is None:
        logger.warning("Couldn't run ty to check function imports: it isn't installed")
        return None
    try:
        with tempfile.TemporaryDirectory() as config_dir:
            # An empty config in place of any ty settings found above the project, which can
            # switch rules off or widen what ty checks to a whole repository.
            config_file = os.path.join(config_dir, "ty.toml")
            open(config_file, "w").close()
            command = [
                # -I so a ty.py in the project can't shadow the real one.
                *(sys.executable, "-I", "-m", "ty", "check", *targets),
                *("--project", "."),
                *("--config-file", config_file),
                *("--python-version", RUNTIME_PYTHON_VERSION),
                *("--output-format", "gitlab"),
            ]
            result = subprocess.run(
                command,
                cwd=root_path,
                capture_output=True,
                text=True,
                timeout=TY_TIMEOUT_SECONDS,
                stdin=subprocess.DEVNULL,
            )
        # ty exits 0 with no diagnostics and 1 with some; anything else means it failed.
        if result.returncode not in (0, 1):
            raise OSError(f"ty exited with {result.returncode}: {result.stderr.strip()[:200]}")
        diagnostics = json.loads(result.stdout or "[]")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        logger.warning(f"Couldn't run ty to check function imports: {e}")
        return None

    unchecked_lines: dict[str, set[int]] = {}
    errors = []
    for diagnostic in diagnostics:
        rule = diagnostic.get("check_name")
        if rule != "unresolved-import":
            continue
        path = diagnostic["location"]["path"].replace("\\", "/")
        line = diagnostic["location"]["positions"]["begin"]["line"]
        message = diagnostic["description"].removeprefix(f"{rule}: ")
        if not (_FUNCTION_FILE.match(path) and _PROJECT_MODULE.search(message)):
            continue
        if path not in unchecked_lines:
            unchecked_lines[path] = _unchecked_import_lines(root_path, path)
        if line not in unchecked_lines[path]:
            errors.append(CodeError(path=path, line=line, message=message))
    errors.extend(_global_imports_from_flow_errors(root_path))
    return errors


def _parse(file_path: str) -> Optional[ast.Module]:
    """The file's syntax tree, or None if it can't be read or parsed."""
    try:
        with open(file_path, encoding="utf-8") as f:
            return ast.parse(f.read())
    except (OSError, SyntaxError, ValueError):
        return None


def _flow_function_files(root_path: str) -> list[str]:
    """Paths of every flow's function files, relative to the root, with forward slashes."""
    flows_dir = os.path.join(root_path, "flows")
    if not os.path.isdir(flows_dir):
        return []
    paths = []
    for folder in sorted(os.listdir(flows_dir)):
        functions_dir = os.path.join(flows_dir, folder, "functions")
        if os.path.isdir(functions_dir):
            for name in sorted(os.listdir(functions_dir)):
                if name.endswith(".py"):
                    paths.append(f"flows/{folder}/functions/{name}")
    return paths


def _unchecked_import_lines(root_path: str, path: str) -> set[int]:
    """Lines of imports ty's diagnostics don't apply to.

    Those are guarded imports, and, in a flow's functions, imports from `..`, which are checked
    separately because they resolve differently on the platform.
    """
    tree = _parse(os.path.join(root_path, path))
    if tree is None:
        return set()
    lines = _guarded_import_lines(tree)
    if _FLOW_FUNCTION_FILE.match(path):
        lines |= _lines(_parent_imports(tree))
    return lines


def _guarded_import_lines(tree: ast.Module) -> set[int]:
    """Lines of imports the code expects might fail: inside a `try` that catches `ImportError`,
    or under `if TYPE_CHECKING:`."""
    guarded = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Try, ast.TryStar)) and any(
            _catches_import_error(handler) for handler in node.handlers
        ):
            guarded.extend(node.body)
        elif isinstance(node, ast.If) and _is_type_checking(node.test):
            guarded.extend(node.body)
    return _lines(
        n for g in guarded for n in ast.walk(g) if isinstance(n, (ast.Import, ast.ImportFrom))
    )


def _parent_imports(tree: ast.Module) -> list[ast.ImportFrom]:
    """Every `from ..<module> import ...` in the file."""
    return [n for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 2]


def _lines(nodes: Iterable[ast.stmt]) -> set[int]:
    """Every line the statements span."""
    return {line for n in nodes for line in range(n.lineno, (n.end_lineno or n.lineno) + 1)}


def _catches_import_error(handler: ast.ExceptHandler) -> bool:
    """Whether an `except` clause catches a failed import."""
    if handler.type is None:
        return True
    for node in ast.walk(handler.type):
        name = node.id if isinstance(node, ast.Name) else getattr(node, "attr", None)
        if name in _IMPORT_ERROR_CATCHERS:
            return True
    return False


def _is_type_checking(test: ast.expr) -> bool:
    """Whether an `if` test is `TYPE_CHECKING` or `typing.TYPE_CHECKING`."""
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _global_imports_from_flow_errors(root_path: str) -> list[CodeError]:
    """Imports from `..` in a flow's functions that don't resolve.

    On the platform a flow's functions sit in `functions/<flow id>/`, so `..` is the global
    `functions/` folder. Locally they sit in `flows/<folder>/functions/`, where ty resolves `..`
    to the flow's folder instead.
    """
    errors = []
    for path in _flow_function_files(root_path):
        tree = _parse(os.path.join(root_path, path))
        if tree is None:
            continue
        guarded = _guarded_import_lines(tree)
        for node in _parent_imports(tree):
            if node.lineno in guarded:
                continue
            for message in _global_import_problems(root_path, node):
                errors.append(CodeError(path=path, line=node.lineno, message=message))
    return errors


def _global_import_problems(root_path: str, node: ast.ImportFrom) -> list[str]:
    """What doesn't resolve in a `from ..<module> import <names>` against `functions/`."""
    functions_dir = os.path.join(root_path, "functions")
    shown = f"..{node.module or ''}"
    if node.module:
        target = os.path.join(functions_dir, *node.module.split("."))
        if os.path.isfile(f"{target}.py"):
            names = _top_level_names(f"{target}.py")
        elif os.path.isdir(target):
            names = None
        else:
            return [f"Cannot resolve imported module `{shown}`"]
    else:
        names = _top_level_names(os.path.join(functions_dir, "__init__.py"))
    problems = []
    for alias in node.names:
        if alias.name == "*" or names is None or alias.name in names:
            continue
        if node.module is None and os.path.isfile(os.path.join(functions_dir, f"{alias.name}.py")):
            continue
        problems.append(f"Module `{shown}` has no member `{alias.name}`")
    return problems


def _top_level_names(file_path: str) -> Optional[set[str]]:
    """Names a module defines at top level, or None if that can't be told."""
    if not os.path.isfile(file_path):
        return set()
    tree = _parse(file_path)
    if tree is None:
        return None
    names: set[str] = set()
    pending: list[ast.AST] = list(tree.body)
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    # `from _gen import *` heads every function file and brings in the
                    # runtime's types, which nothing imports from another function.
                    if (
                        isinstance(node, ast.ImportFrom)
                        and node.level == 0
                        and node.module == "_gen"
                    ):
                        continue
                    return None
                names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif not isinstance(node, ast.Lambda):
            pending.extend(ast.iter_child_nodes(node))
    return names
