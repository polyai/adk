#!/usr/bin/env python3
"""Sync type stubs from genai_lambda_runtime into src/poly/types/.

Extracts public API signatures (classes, methods, properties, type aliases,
exceptions) from the runtime source and writes stub-only .py files with
``...`` bodies. Internal helpers (prefixed with ``_``) and implementation
details are stripped.

Usage:
    python scripts/sync_runtime_stubs.py [--runtime-path PATH]

Default runtime path: ../genai_lambda_runtime/python/runtime
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

STUB_HEADER = """\
# Copyright PolyAI Limited
# flake8: noqa
# ruff: noqa
# type: ignore
"""

STUB_DIR = Path(__file__).resolve().parent.parent / "src" / "poly" / "types"

STUB_FILES = [
    "attachment.py",
    "conv_utils.py",
    "conversation.py",
    "external_events.py",
    "flow.py",
    "history.py",
    "log_utils.py",
    "memory.py",
    "sms.py",
    "value_extraction.py",
    "value_extraction_types.py",
    "webchat.py",
    "agentic_dial.py",
    "emails.py",
    "entity_validator.py",
]


def _has_private_name(name: str) -> bool:
    """Return True if name starts with _ (private/internal)."""
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _format_annotation(node: ast.expr | None) -> str | None:
    """Convert an AST annotation node to source text."""
    if node is None:
        return None
    return ast.unparse(node)


def _format_arg(arg: ast.arg) -> str:
    """Format a function argument with optional annotation."""
    ann = _format_annotation(arg.annotation)
    if ann:
        return f"{arg.arg}: {ann}"
    return arg.arg


def _build_signature(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Build a stub-style function signature."""
    args = func.args
    parts: list[str] = []

    for arg in args.posonlyargs:
        parts.append(_format_arg(arg))
    if args.posonlyargs:
        parts.append("/")

    num_defaults = len(args.defaults)
    num_args = len(args.args)
    for i, arg in enumerate(args.args):
        formatted = _format_arg(arg)
        default_idx = i - (num_args - num_defaults)
        if default_idx >= 0:
            formatted += " = ..."
        parts.append(formatted)

    if args.vararg:
        parts.append(f"*{_format_arg(args.vararg)}")
    elif args.kwonlyargs:
        parts.append("*")

    kw_defaults = args.kw_defaults
    for i, arg in enumerate(args.kwonlyargs):
        formatted = _format_arg(arg)
        if kw_defaults[i] is not None:
            formatted += " = ..."
        parts.append(formatted)

    if args.kwarg:
        parts.append(f"**{_format_arg(args.kwarg)}")

    sig = ", ".join(parts)
    ret = _format_annotation(func.returns)
    if ret:
        return f"({sig}) -> {ret}"
    return f"({sig})"


def _get_docstring(node: ast.AST) -> str | None:
    """Extract docstring from a node."""
    if (
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        val = node.body[0].value
        if isinstance(val.value, str):
            return val.value
    return None


def _extract_class_vars(cls_node: ast.ClassDef) -> list[str]:
    """Extract annotated class variables."""
    lines = []
    for stmt in cls_node.body:
        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            name = stmt.target.id
            if _has_private_name(name):
                continue
            ann = _format_annotation(stmt.annotation)
            lines.append(f"    {name}: {ann}")
    return lines


def _extract_method_stub(func: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    """Generate a stub line for a method."""
    name = func.name
    if name.startswith("_") and not (name.startswith("__") and name.endswith("__")):
        return None

    is_property = any(
        (isinstance(d, ast.Name) and d.id == "property")
        or (isinstance(d, ast.Attribute) and d.attr == "property")
        for d in func.decorator_list
    )
    is_staticmethod = any(
        isinstance(d, ast.Name) and d.id == "staticmethod" for d in func.decorator_list
    )
    is_classmethod = any(
        isinstance(d, ast.Name) and d.id == "classmethod" for d in func.decorator_list
    )

    sig = _build_signature(func)
    prefix = "async def" if isinstance(func, ast.AsyncFunctionDef) else "def"

    docstring = _get_docstring(func)

    lines = []
    if is_property:
        lines.append("    @property")
    elif is_staticmethod:
        lines.append("    @staticmethod")
    elif is_classmethod:
        lines.append("    @classmethod")

    if docstring:
        first_line = docstring.strip().split("\n")[0]
        lines.append(f"    {prefix} {name}{sig}:")
        lines.append(f'        """{first_line}"""')
    else:
        lines.append(f"    {prefix} {name}{sig}: ...")

    return "\n".join(lines)


def _is_dataclass(cls_node: ast.ClassDef) -> bool:
    """Check if a class is decorated with @dataclass."""
    for d in cls_node.decorator_list:
        if isinstance(d, ast.Name) and d.id == "dataclass":
            return True
        if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "dataclass":
            return True
    return False


def _synthesize_dataclass_init(cls_node: ast.ClassDef) -> str | None:
    """Build an __init__ stub from dataclass field annotations.

    Fields with a default value or default_factory get ``= ...`` in the
    signature.  Returns None when no annotated fields are found.
    """
    params = ["self"]
    for stmt in cls_node.body:
        if not (isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name)):
            continue
        name = stmt.target.id
        if _has_private_name(name):
            continue
        ann = _format_annotation(stmt.annotation)
        if stmt.value is not None:
            params.append(f"{name}: {ann} = ...")
        else:
            params.append(f"{name}: {ann}")

    if len(params) == 1:
        return None

    sig = ", ".join(params)
    return f"    def __init__({sig}) -> None: ..."


def _extract_class_stub(cls_node: ast.ClassDef) -> str:
    """Generate a full class stub."""
    bases = [ast.unparse(b) for b in cls_node.bases]
    bases_str = f"({', '.join(bases)})" if bases else ""

    docstring = _get_docstring(cls_node)
    doc_section = ""
    if docstring:
        first_line = docstring.strip().split("\n")[0]
        doc_section = f'    """{first_line}"""\n\n'

    class_vars = _extract_class_vars(cls_node)
    cv_section = "\n".join(class_vars) + "\n" if class_vars else ""

    is_dc = _is_dataclass(cls_node)
    has_explicit_init = any(
        isinstance(s, ast.FunctionDef) and s.name == "__init__" for s in cls_node.body
    )

    methods = []
    # Synthesize __init__ for dataclasses that don't define one explicitly
    if is_dc and not has_explicit_init:
        init_stub = _synthesize_dataclass_init(cls_node)
        if init_stub:
            methods.append(init_stub)

    for stmt in cls_node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stub = _extract_method_stub(stmt)
            if stub:
                methods.append(stub)

    methods_section = "\n".join(methods) + "\n" if methods else ""

    body = doc_section + cv_section + methods_section
    if not body.strip():
        body = "    ...\n"

    return f"class {cls_node.name}{bases_str}:\n{body}"


def _extract_top_level_assignments(tree: ast.Module) -> list[str]:
    """Extract public type aliases and constants."""
    lines = []
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and not _has_private_name(target.id):
                    lines.append(ast.unparse(stmt))
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if not _has_private_name(stmt.target.id):
                lines.append(ast.unparse(stmt))
    return lines


def _get_all_list(tree: ast.Module) -> list[str] | None:
    """Extract __all__ if defined."""
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(stmt.value, ast.List):
                        return [
                            elt.value for elt in stmt.value.elts if isinstance(elt, ast.Constant)
                        ]
    return None


def _filter_import_names(names: list[ast.alias]) -> list[ast.alias]:
    """Filter out private names from import lists."""
    return [alias for alias in names if not _has_private_name(alias.name)]


# Modules that only contain internal implementation details — skip entirely.
_INTERNAL_MODULES = frozenset(
    {
        "runtime.state_utils",
        "runtime.llm_client",
        "utils.api_connector",
        "utils.secret_vault",
    }
)

# Stdlib/third-party modules whose types appear in public signatures.
_ALLOWED_STDLIB_MODULES = frozenset(
    {
        "abc",
        "collections.abc",
        "datetime",
        "enum",
        "re",
        "typing",
        "pydantic",
    }
)


def _collect_import_stmts(stmts: list[ast.stmt]) -> list[ast.stmt]:
    """Collect import statements, including those inside TYPE_CHECKING blocks."""
    result = []
    for stmt in stmts:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            result.append(stmt)
        elif (
            isinstance(stmt, ast.If)
            and isinstance(stmt.test, ast.Name)
            and stmt.test.id == "TYPE_CHECKING"
        ):
            result.extend(_collect_import_stmts(stmt.body))
    return result


def _expand_module_import(module: str, alias: str, body_text: str) -> str | None:
    """Convert ``import runtime.X as Y`` to ``from .X import A, B, C``.

    Scans *body_text* for ``Y.name`` references and emits a relative
    ``from`` import for each attribute used.  Also rewrites those
    ``Y.name`` references in body_text to just ``name``.
    Returns (import_line, new_body_text) or None if no attributes are found.
    """
    import re as _re

    pattern = _re.compile(r"(?<![a-zA-Z0-9_.])" + _re.escape(alias) + r"\.(\w+)")
    names = sorted(set(m.group(1) for m in pattern.finditer(body_text)))
    if not names:
        return None, body_text
    # Relativize: runtime.foo -> .foo
    rel_module = "." + module.split(".", 1)[1] if "." in module else module
    import_line = f"from {rel_module} import {', '.join(names)}"
    # Rewrite body: extraction_types.EntityConfig -> EntityConfig
    new_body = pattern.sub(r"\1", body_text)
    return import_line, new_body


def _relativize_module(module: str) -> str:
    """Convert ``runtime.X`` or ``utils.X`` to ``.X`` for relative imports."""
    if module.startswith(("runtime.", "utils.")):
        return "." + module.split(".", 1)[1]
    return module


def _extract_imports(tree: ast.Module, source_path: Path) -> list[str]:
    """Extract imports needed for the stub.

    Includes:
    - typing imports
    - runtime.* imports (relativized to .X)
    - stdlib/pydantic imports used in type annotations
    - imports from ``if TYPE_CHECKING:`` blocks (promoted to unconditional)

    ``import runtime.X as Y`` forms are tagged for deferred expansion
    (needs body_text to resolve which attributes are used).
    """
    imports = []
    for stmt in _collect_import_stmts(tree.body):
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name.startswith("runtime"):
                    imports.append(
                        ("module_alias", alias.name, alias.asname or alias.name.rsplit(".", 1)[-1])
                    )
                elif alias.name in _ALLOWED_STDLIB_MODULES:
                    imports.append(ast.unparse(stmt))
        elif isinstance(stmt, ast.ImportFrom):
            if not stmt.module:
                continue
            if stmt.module in _INTERNAL_MODULES:
                continue

            is_runtime = stmt.module.startswith("runtime.") or stmt.module == "runtime"
            is_typing = stmt.module.startswith("typing")
            is_stdlib = any(
                stmt.module == m or stmt.module.startswith(m + ".") for m in _ALLOWED_STDLIB_MODULES
            )

            if is_runtime or is_typing or is_stdlib:
                public_names = _filter_import_names(stmt.names)
                if not public_names:
                    continue
                rel_module = _relativize_module(stmt.module)
                filtered = ast.ImportFrom(
                    module=rel_module,
                    names=public_names,
                    level=0 if rel_module.startswith(".") else stmt.level,
                )
                imports.append(ast.unparse(filtered))
    return imports


def _name_used_in(name: str, body_text: str) -> bool:
    """Check if an imported name is actually referenced in the body.

    Uses word-boundary matching to avoid false positives like
    ``import re`` matching ``"score"``.
    """
    import re as _re

    return bool(
        _re.search(r"(?<![a-zA-Z0-9_])" + _re.escape(name) + r"(?![a-zA-Z0-9_])", body_text)
    )


def _prune_imports(import_lines: list[str], body_text: str) -> list[str]:
    """Keep only imports whose names actually appear in the stub body."""
    pruned = []
    for line in import_lines:
        # `import foo as bar` or `import foo` — keep if the bound name appears
        if line.startswith("import "):
            # e.g. "import runtime.external_events as external_events"
            parts = line.split()
            bound_name = parts[-1]  # alias or last dotted segment
            if _name_used_in(bound_name, body_text):
                pruned.append(line)
            continue

        # `from X import a, b, c` — keep only names that appear in body
        try:
            node = ast.parse(line).body[0]
        except SyntaxError:
            pruned.append(line)
            continue

        if not isinstance(node, ast.ImportFrom):
            pruned.append(line)
            continue

        used = [
            alias for alias in node.names if _name_used_in(alias.asname or alias.name, body_text)
        ]
        if not used:
            continue
        filtered = ast.ImportFrom(module=node.module, names=used, level=node.level)
        pruned.append(ast.unparse(filtered))

    return pruned


def generate_stub(source_path: Path) -> str:
    """Generate a stub file from a runtime source file."""
    source = source_path.read_text()
    tree = ast.parse(source)

    candidate_imports = _extract_imports(tree, source_path)
    all_list = _get_all_list(tree)

    classes = []
    for stmt in tree.body:
        if isinstance(stmt, ast.ClassDef) and not _has_private_name(stmt.name):
            classes.append(_extract_class_stub(stmt))

    # Collect assignments, separating those that reference class names
    # (type aliases like VoiceType = ...) to place them after class definitions.
    class_names = {stmt.name for stmt in tree.body if isinstance(stmt, ast.ClassDef)}
    assignments_before = []
    assignments_after = []
    for stmt in tree.body:
        line = None
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and not _has_private_name(target.id):
                    line = ast.unparse(stmt)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            if not _has_private_name(stmt.target.id):
                line = ast.unparse(stmt)

        if line is None:
            continue

        unparsed_value = ast.unparse(stmt.value) if hasattr(stmt, "value") and stmt.value else ""
        if any(cn in unparsed_value for cn in class_names):
            assignments_after.append(line)
        else:
            assignments_before.append(line)

    # Derive __all__ from public classes and type aliases if source doesn't define one.
    if all_list is None:
        public_class_names = [
            stmt.name
            for stmt in tree.body
            if isinstance(stmt, ast.ClassDef) and not _has_private_name(stmt.name)
        ]
        public_assignment_names = []
        for stmt in tree.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and not _has_private_name(target.id):
                        public_assignment_names.append(target.id)
        all_list = public_class_names + public_assignment_names

    # Build body text (everything except imports) to prune unused imports.
    body_parts = []
    if assignments_before:
        body_parts.append("\n".join(assignments_before))
    if classes:
        body_parts.append("\n\n".join(classes))
    if assignments_after:
        body_parts.append("\n".join(assignments_after))
    body_text = "\n".join(body_parts)

    # Resolve deferred module-alias imports and rewrite body references.
    resolved_imports = []
    for item in candidate_imports:
        if isinstance(item, tuple) and item[0] == "module_alias":
            _, module, alias = item
            import_line, body_text = _expand_module_import(module, alias, body_text)
            if import_line:
                resolved_imports.append(import_line)
        else:
            resolved_imports.append(item)

    imports = _prune_imports(resolved_imports, body_text)

    # Rebuild body_parts from (possibly rewritten) body_text
    # Split back into sections for assembly
    all_body_lines = body_text.split("\n") if body_text.strip() else []

    # Assemble final stub
    parts = [STUB_HEADER]

    if imports:
        parts.append("\n".join(imports))

    if all_list:
        items = ", ".join(f'"{name}"' for name in all_list)
        parts.append(f"\n__all__ = [{items}]")

    if all_body_lines:
        parts.append("\n".join(all_body_lines))

    return "\n\n".join(parts) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync runtime type stubs")
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

    STUB_DIR.mkdir(parents=True, exist_ok=True)

    updated = 0
    for filename in STUB_FILES:
        source = runtime_path / filename
        if not source.exists():
            print(f"  SKIP {filename} (not found in runtime)")
            continue

        stub_content = generate_stub(source)
        dest = STUB_DIR / filename
        dest.write_text(stub_content)
        print(f"  OK   {filename}")
        updated += 1

    print(f"\nSynced {updated}/{len(STUB_FILES)} stub files to {STUB_DIR}")


if __name__ == "__main__":
    main()
