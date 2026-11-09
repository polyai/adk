"""Checks on function code that need the whole project: imports between functions, and syntax
as the platform's Python sees it. Both come from ty.

Copyright PolyAI Limited
"""

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# The Python version the platform runs function code on.
RUNTIME_PYTHON_VERSION = "3.14"

TY_TIMEOUT_SECONDS = 30

# Function files: global functions and each flow's functions. Function steps are checked for
# syntax only, since how their imports resolve differs.
_FUNCTION_FILE = re.compile(r"^(?:functions|flows/[^/]+/functions)/[^/]+\.py$")
_FUNCTION_OR_STEP_FILE = re.compile(
    r"^(?:functions|flows/[^/]+/(?:functions|function_steps))/[^/]+\.py$"
)
# Imports of the project's own modules. Anything else (_gen, the standard library, packages the
# runtime provides) isn't installed locally, so ty can't resolve it.
_PROJECT_MODULE = re.compile(r"`(?:functions|flows)\.[\w.]+")


@dataclass
class CodeError:
    """One problem ty found in a function file."""

    # Relative to the project root, with forward slashes.
    path: str
    line: int
    message: str


def function_code_errors(root_path: str) -> Optional[list[CodeError]]:
    """Unresolved project imports in function files, and syntax errors in function and step files.

    Every other ty diagnostic is ignored: the type rules fire constantly on valid projects,
    mostly because `conv.state` attributes are typed `Any | None`.

    Args:
        root_path: The project root.

    Returns:
        The errors found, with paths relative to the root, or None if ty couldn't run.
    """
    targets = [d for d in ("functions", "flows") if os.path.isdir(os.path.join(root_path, d))]
    if not targets:
        return []
    try:
        with tempfile.TemporaryDirectory() as config_dir:
            # An empty config in place of any ty settings found above the project, which can
            # switch rules off or widen what ty checks to a whole repository.
            config_file = os.path.join(config_dir, "ty.toml")
            open(config_file, "w").close()
            command = [
                # -I so a ty.py in the project can't shadow the real one.
                *(sys.executable, "-I", "-m", "ty", "check", *targets),
                *("--project", root_path),
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
        logger.warning(f"Couldn't run ty to check function code: {e}")
        return None

    errors = []
    for diagnostic in diagnostics:
        rule = diagnostic.get("check_name")
        path = diagnostic["location"]["path"].replace("\\", "/")
        message = diagnostic["description"].removeprefix(f"{rule}: ")
        if rule == "unresolved-import":
            reported = _FUNCTION_FILE.match(path) and _PROJECT_MODULE.search(message)
        elif rule == "invalid-syntax":
            reported = _FUNCTION_OR_STEP_FILE.match(path)
        else:
            reported = False
        if reported:
            line = diagnostic["location"]["positions"]["begin"]["line"]
            errors.append(CodeError(path=path, line=line, message=message))
    return errors
