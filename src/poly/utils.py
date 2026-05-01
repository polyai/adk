"""Utility functions for Agent Development Kit

Copyright PolyAI Limited
"""

import ast
import difflib
import importlib.resources
import inspect
import logging
import os
import re
from typing import Callable, Optional

from poly.resources import Resource, ResourceMapping, Function, FunctionStep

logger = logging.getLogger(__name__)

_TYPES_PACKAGE = "poly.types"

_API_KEY_ENV_VAR = "POLY_ADK_KEY"


def retrieve_api_key(region: Optional[str] = None) -> str:
    """Return an API key, preferring a per-region key when available.

    Resolution order:
      1. ``POLY_ADK_KEY_{REGION}`` (if *region* is provided, e.g. ``POLY_ADK_KEY_US``)
      2. ``POLY_ADK_KEY``

    Raises ``ValueError`` with a helpful message when no key is found.
    """
    if region:
        suffix = re.sub(r"-\d+$", "", region).upper()
        per_region_key = os.getenv(f"{_API_KEY_ENV_VAR}_{suffix}")
        if per_region_key:
            return per_region_key

    api_key = os.getenv(_API_KEY_ENV_VAR)
    if not api_key:
        raise ValueError(
            f"{_API_KEY_ENV_VAR} environment variable is not set. "
            f"Export your API key with: export {_API_KEY_ENV_VAR}=<your-api-key>"
        )
    return api_key


# Matches cross-package imports e.g. "from runtime.foo import" or "from utils.foo import"
_STUB_IMPORT_RE = re.compile(r"^from (?:runtime|utils)\.(\w+) import", re.MULTILINE)


def _relativize_stub_imports(source: str) -> str:
    """Rewrite absolute stub cross-references to relative imports.

    e.g. ``from runtime.attachment import Attachment``
         -> ``from .attachment import Attachment``
    """
    return _STUB_IMPORT_RE.sub(r"from .\1 import", source)


def _read_all_from_stub(source: str) -> list[str] | None:
    """Return the names listed in __all__ of a type source string, or None."""
    tree = ast.parse(source)
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, (ast.List, ast.Tuple)):
                        return [
                            elt.value
                            for elt in node.value.elts
                            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                        ]
    return None


def _load_file_class_maps() -> dict[str, list[str]]:
    """Discover exported names by reading __all__ from each type file.

    Returns:
        A dictionary mapping filenames (e.g. "conversation.py") to the list of
        names declared in that module's __all__.
    """
    result: dict[str, list[str]] = {}
    pkg = importlib.resources.files(_TYPES_PACKAGE)
    for resource in sorted(pkg.iterdir(), key=lambda r: r.name):
        name = resource.name
        if not name.endswith(".py") or name.startswith("_"):
            continue
        names = _read_all_from_stub(resource.read_text(encoding="utf-8"))
        if names:
            result[name] = names
    return result


def _gen_import_statements() -> str:
    """Import statements for _gen/__init__.py using _gen.<module> absolute form."""
    imports = []
    for file_path, names in _load_file_class_maps().items():
        module_name = os.path.basename(file_path).replace(".py", "")
        imports.append(
            f"""from _gen.{module_name} import (
    {", ".join(names)}
)"""
        )
    return "\n".join(imports) + "\n\n"


def create_import_file_contents() -> str:
    """Return the contents that would be written to _gen/__init__.py."""
    header = "# flake8: noqa\n# <AUTO GENERATED>\n"
    all_names = [n for names in _load_file_class_maps().values() for n in names]
    all_line = "__all__ = [\n    " + ",\n    ".join(f'"{n}"' for n in all_names) + "\n]\n\n"
    return header + all_line + _gen_import_statements()


def save_imports(base_path: str) -> None:
    """Save the _gen package: __init__.py and importable stub .py files."""
    gen_dir = os.path.join(base_path, "_gen")
    os.makedirs(gen_dir, exist_ok=True)

    # Remove stale .pyi files if any exist from a previous generation
    for fname in os.listdir(gen_dir):
        if fname.endswith(".pyi"):
            os.remove(os.path.join(gen_dir, fname))

    # Copy type files into _gen/ with relativized cross-package references
    pkg = importlib.resources.files(_TYPES_PACKAGE)
    for resource in sorted(pkg.iterdir(), key=lambda r: r.name):
        name = resource.name
        if not name.endswith(".py") or name.startswith("_"):
            continue
        source = _relativize_stub_imports(resource.read_text(encoding="utf-8"))
        with open(os.path.join(gen_dir, name), "w", encoding="utf-8") as f:
            f.write(source)

    # Collect all type names for __all__
    all_names = [n for names in _load_file_class_maps().values() for n in names]

    # Read decorator names from _gen/decorators.py if it was already generated
    decorator_import = ""
    decorators_path = os.path.join(gen_dir, "decorators.py")
    if os.path.isfile(decorators_path):
        with open(decorators_path, encoding="utf-8") as f:
            dec_names = _read_all_from_stub(f.read()) or []
        all_names.extend(dec_names)
        decorator_import = (
            f"from _gen.decorators import {', '.join(dec_names)}\n"
            if dec_names
            else "from _gen.decorators import *\n"
        )

    header = "# flake8: noqa\n# <AUTO GENERATED>\n"
    all_line = "__all__ = [\n    " + ",\n    ".join(f'"{n}"' for n in all_names) + "\n]\n\n"

    with open(os.path.join(gen_dir, "__init__.py"), "w", encoding="utf-8") as f:
        f.write(header + all_line + _gen_import_statements() + decorator_import)


def merge_strings(original: str, updated: str, incoming: str) -> str:
    """Merge updated and incoming strings with original as base.

    Performs a 3-way merge using difflib. Changes made only in `updated` or
    only in `incoming` are applied cleanly. Conflicting changes (both sides
    modified the same region differently) produce conflict markers.
    """
    base = original.splitlines(keepends=True)
    a = updated.splitlines(keepends=True)
    b = incoming.splitlines(keepends=True)

    result: list[str] = []
    for region in _merge_regions(base, a, b):
        tag = region[0]
        if tag == "unchanged":
            result.extend(base[region[1] : region[2]])
        elif tag in ("a", "same"):
            result.extend(a[region[1] : region[2]])
        elif tag == "b":
            result.extend(b[region[1] : region[2]])
        elif tag == "conflict":
            _, _, _, a_start, a_end, b_start, b_end = region
            result.append("<<<<<<<\n")
            result.extend(a[a_start:a_end])
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            result.append("=======\n")
            result.extend(b[b_start:b_end])
            if result and not result[-1].endswith("\n"):
                result[-1] += "\n"
            result.append(">>>>>>>\n")
    return "".join(result)


def _find_sync_regions(
    matches_a: list[difflib.Match],
    matches_b: list[difflib.Match],
) -> list[tuple[int, int, int, int, int, int]]:
    """Find regions in base that are matched by both a and b.

    Returns (base_start, base_end, a_start, a_end, b_start, b_end) tuples
    representing synchronisation points where all three texts agree.
    """
    regions: list[tuple[int, int, int, int, int, int]] = []
    ia = ib = 0

    while ia < len(matches_a) and ib < len(matches_b):
        base_a_start, a_start, na = matches_a[ia]
        base_b_start, b_start, nb = matches_b[ib]

        base_a_end = base_a_start + na
        base_b_end = base_b_start + nb

        # Intersect the two matching ranges on the base axis
        inter_start = max(base_a_start, base_b_start)
        inter_end = min(base_a_end, base_b_end)

        if inter_start < inter_end:
            a_inter_start = a_start + (inter_start - base_a_start)
            b_inter_start = b_start + (inter_start - base_b_start)
            length = inter_end - inter_start
            regions.append(
                (
                    inter_start,
                    inter_end,
                    a_inter_start,
                    a_inter_start + length,
                    b_inter_start,
                    b_inter_start + length,
                )
            )

        # Advance whichever matching block ends first
        if base_a_end <= base_b_end:
            ia += 1
        if base_b_end <= base_a_end:
            ib += 1

    return regions


def _classify_gap(
    base: list[str],
    base_start: int,
    base_end: int,
    a: list[str],
    a_start: int,
    a_end: int,
    b: list[str],
    b_start: int,
    b_end: int,
):
    """Classify a gap between sync regions as unchanged, one-sided, same, or conflict."""
    base_chunk = base[base_start:base_end]
    a_chunk = a[a_start:a_end]
    b_chunk = b[b_start:b_end]

    if not base_chunk and not a_chunk and not b_chunk:
        return

    if a_chunk == b_chunk:
        # Both sides agree (either both unchanged or both made the same edit)
        if a_chunk == base_chunk:
            yield ("unchanged", base_start, base_end)
        else:
            yield ("same", a_start, a_end)
    elif a_chunk == base_chunk:
        # Only b changed
        yield ("b", b_start, b_end)
    elif b_chunk == base_chunk:
        # Only a changed
        yield ("a", a_start, a_end)
    else:
        # Both changed differently — conflict
        yield ("conflict", base_start, base_end, a_start, a_end, b_start, b_end)


def _merge_regions(base: list[str], a: list[str], b: list[str]):
    """Compute merge regions for a 3-way merge."""
    sync_regions = _find_sync_regions(
        difflib.SequenceMatcher(None, base, a).get_matching_blocks(),
        difflib.SequenceMatcher(None, base, b).get_matching_blocks(),
    )

    base_pos = a_pos = b_pos = 0

    for base_start, base_end, a_start, a_end, b_start, b_end in sync_regions:
        yield from _classify_gap(
            base,
            base_pos,
            base_start,
            a,
            a_pos,
            a_start,
            b,
            b_pos,
            b_start,
        )

        if base_start < base_end:
            yield ("unchanged", base_start, base_end)

        base_pos = base_end
        a_pos = a_end
        b_pos = b_end

    # Trailing content after the last sync region
    yield from _classify_gap(
        base,
        base_pos,
        len(base),
        a,
        a_pos,
        len(a),
        b,
        b_pos,
        len(b),
    )


def func_latency_control(
    delay_before_responses_start: int = 0,
    silence_after_each_response: int = 0,
    delay_responses: Optional[list[tuple[str, int]]] = None,
) -> Callable:
    """Configure latency control for a function.

    Args:
        delay_before_responses_start: Seconds to wait before the first delay
            response is played. Must be between 0 and 10.
        silence_after_each_response: Seconds of silence to insert after each
            delay response. Must be between 0 and 10.
        delay_responses: A list of (message, duration_ms) tuples that are
            played while the function is executing.
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def func_parameter(
    name: str,
    description: str,
) -> Callable:
    """Configure function parameter.

    Args:
        name: Name of the given parameter.
        description: Description of the given parameter (provided to the LLM).
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def func_description(
    description: str,
) -> Callable:
    """Set the description for the target function.

    Args:
        description: Description of the target function (provided to the LLM).
    """

    def decorator(func: Callable) -> Callable:
        return func

    return decorator


def export_decorators(decorators: list[str], base_path: str, filepath: str = "_gen/decorators.py"):
    """Export the decorator functions."""
    filepath = os.path.join(base_path, filepath)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            "# flake8: noqa\n# <AUTO GENERATED>\n" + "from typing import Callable, Optional\n\n"
        )
        f.write(f"__all__ = {decorators!r}\n\n")

        for decorator in decorators:
            f.write(inspect.getsource(globals()[decorator]))
            f.write("\n\n")


# Maps function_type value -> VariableReferences proto field name
FUNCTION_TYPE_TO_VAR_REF_FIELD: dict[str, str] = {
    "global": "functions",
    "start": "start_functions",
    "end": "end_functions",
    "transition": "flow_functions",
    "function_step": "flow_steps",
}


def _iter_functions_with_var_refs(
    resources: dict[type[Resource], dict[str, Resource]],
    resource_mappings: list[ResourceMapping],
):
    """Yield (function, field_name) for every Function/FunctionStep with variable_references."""
    for fn_type in (Function, FunctionStep):
        for fn in resources.get(fn_type, {}).values():
            variable_references = (
                fn.variable_references
                if fn.variable_references is not None
                else fn._extract_variable_references(fn.code, resource_mappings)
            )
            if not variable_references:
                continue
            ft = fn.function_type
            field_name = FUNCTION_TYPE_TO_VAR_REF_FIELD.get(
                ft.value if hasattr(ft, "value") else str(ft), ""
            )
            yield fn.resource_id, field_name, variable_references


def compute_variable_references(
    resources: dict[type[Resource], dict[str, Resource]],
    resource_mappings: list[ResourceMapping],
) -> dict[str, dict[str, dict[str, bool]]]:
    """Return {var_id: {field_name: {fn_id: True}}} built from all functions in resources.

    The result is suitable for populating VariableReferences on Variable objects.
    New functions are included - the backend accepts references to IDs not yet created.
    """
    var_refs: dict[str, dict[str, dict[str, bool]]] = {}
    for fn_id, field_name, variable_references in _iter_functions_with_var_refs(
        resources, resource_mappings
    ):
        for var_id in variable_references:
            var_refs.setdefault(var_id, {}).setdefault(field_name, {})[fn_id] = True
    return var_refs
