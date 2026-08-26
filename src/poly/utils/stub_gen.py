"""Generation of the local ``_gen`` package of importable type stubs.

Copyright PolyAI Limited
"""

import ast
import importlib.resources
import os
import re

_TYPES_PACKAGE = "poly.types"

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


def _copy_types_tree(pkg: importlib.resources.abc.Traversable, dest_dir: str) -> None:
    """Recursively copy .py stub files from a package into *dest_dir*.

    Creates subdirectories as needed and rewrites ``runtime.``/``utils.``
    imports to relative form.
    """
    os.makedirs(dest_dir, exist_ok=True)
    for resource in sorted(pkg.iterdir(), key=lambda r: r.name):
        name = resource.name
        if name == "__pycache__":
            continue
        if resource.is_dir():
            _copy_types_tree(resource, os.path.join(dest_dir, name))
            continue
        if not name.endswith(".py") or (name.startswith("_") and name != "__init__.py"):
            continue
        source = _relativize_stub_imports(resource.read_text(encoding="utf-8"))
        with open(os.path.join(dest_dir, name), "w", encoding="utf-8") as f:
            f.write(source)


def save_imports(base_path: str) -> None:
    """Save the _gen package: __init__.py and importable stub .py files."""
    gen_dir = os.path.join(base_path, "_gen")
    os.makedirs(gen_dir, exist_ok=True)

    # Remove stale .pyi files if any exist from a previous generation
    for fname in os.listdir(gen_dir):
        if fname.endswith(".pyi"):
            os.remove(os.path.join(gen_dir, fname))

    # Copy type files (including subdirectories) into _gen/
    pkg = importlib.resources.files(_TYPES_PACKAGE)
    _copy_types_tree(pkg, gen_dir)

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
