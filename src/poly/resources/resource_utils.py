"""Util functions for resources in ADK

Copyright PolyAI Limited
"""

import ast
import functools
import hashlib
import inspect
import json
import logging
import os
import re
import subprocess
import sys
from difflib import unified_diff
from enum import Enum
from io import StringIO
from typing import TYPE_CHECKING, Optional

import ruamel.yaml as yaml

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from poly.resources.flows import BaseFlowStep
    from poly.resources.resource import ResourceMapping

# Create YAML instances with block style for multiline strings
_yaml_dumper = yaml.YAML()
_yaml_dumper.default_flow_style = False
_yaml_dumper.preserve_quotes = False
_yaml_dumper.width = 100

_yaml_loader = yaml.YAML(typ="safe")
_yaml_loader.preserve_quotes = False


def resource_to_dict(obj) -> dict:
    """Recursively serialize a resource dataclass to a dict.

    Like dataclasses.asdict() but only includes keys that match
    the class's __init__ parameters, so extra dataclass fields
    (e.g. computed or create-only fields) are excluded.
    """
    from dataclasses import fields

    valid_params = set(inspect.signature(type(obj).__init__).parameters.keys()) - {"self"}
    result = {}
    for f in fields(obj):
        if f.name not in valid_params:
            continue
        result[f.name] = _serialize_value(getattr(obj, f.name))
    return result


def _serialize_value(value):
    """Recursively serialize a value for status dict storage."""
    from dataclasses import is_dataclass
    from enum import Enum

    if is_dataclass(value) and not isinstance(value, type):
        return resource_to_dict(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_serialize_value(item) for item in value)
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value


def _key_needs_quoting(key: str) -> bool:
    """Return True if a YAML key should be quoted to avoid parse errors."""
    # & and * are YAML indicators (anchor, alias) that require quoting
    return "&" in key or "*" in key


def _quote_keys_for_yaml(data):
    """Recursively quote dict keys that contain special YAML characters."""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if isinstance(k, str) and _key_needs_quoting(k):
                new_key = yaml.scalarstring.DoubleQuotedScalarString(k)
            else:
                new_key = k
            result[new_key] = _quote_keys_for_yaml(v)
        return result
    elif isinstance(data, list):
        return [_quote_keys_for_yaml(item) for item in data]
    return data


def set_block_style_for_multiline_strings(data):
    """Recursively set block style for strings containing newlines in ruamel.yaml format.

    Args:
        data: Dictionary, list, or other data structure to process in-place.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and "\n" in value:
                data[key] = yaml.scalarstring.LiteralScalarString(value)
            else:
                set_block_style_for_multiline_strings(value)
    elif isinstance(data, list):
        for item in data:
            set_block_style_for_multiline_strings(item)


def dump_yaml(data, stream=None):
    """Dump data to YAML format with block style for multiline strings.

    Args:
        data: Data structure to dump.
        stream: Optional stream to write to. If None, returns a string.

    Returns:
        str: YAML string if stream is None, otherwise None.
    """
    data = _quote_keys_for_yaml(data)
    set_block_style_for_multiline_strings(data)
    if stream is None:
        stream = StringIO()
        _yaml_dumper.dump(data, stream)
        return stream.getvalue()
    else:
        _yaml_dumper.dump(data, stream)
        return None


def load_yaml(content):
    """Load YAML content.

    Args:
        content: YAML string or file-like object.

    Returns:
        Parsed YAML data.
    """
    return _yaml_loader.load(content)


def get_diff(original: str, updated: str) -> str:
    """Get the diff between original and updated strings."""

    original_lines = original.splitlines()
    updated_lines = updated.splitlines()

    diff = unified_diff(
        original_lines,
        updated_lines,
        lineterm="",
        fromfile="original",
        tofile="updated",
    )
    return "\n".join(diff)


def contains_merge_conflict(string: str) -> bool:
    """Check if the string contains merge conflict markers."""
    has_start = False
    has_middle = False
    has_end = False
    for line in string.splitlines():
        if "<<<<<<<" in line:
            has_start = True
        elif "=======" in line and has_start:
            has_middle = True
        elif ">>>>>>>" in line and has_middle:
            has_end = True
    return has_start and has_middle and has_end


REFERENCES_PREFIX_MAP = {
    "sms": "twilio_sms",
    "handoff": "ho",
    "attributes": "attr",
    "transition_functions": "ft",
    "global_functions": "fn",
    "entities": "entity",
    "variables": "vrbl",
}
REFERENCES_PREFIX_MAP_REGEX = {
    reference: re.compile(rf"{{{{{prefix}:([\w-]+)}}}}")
    for reference, prefix in REFERENCES_PREFIX_MAP.items()
}

PREFIX_TO_REFERENCE = {prefix: reference for reference, prefix in REFERENCES_PREFIX_MAP.items()}

# Regex matching any {{prefix:value}} reference in a single pass
_REFERENCE_PATTERN = re.compile(r"\{\{(\w+):([^}]+)\}\}")

# Regex to find variable names defined in function code via conv.state.<name>
CONV_STATE_DOT_NAME = re.compile(r"(?<![\w.])conv\.state\.([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\()")


def remove_comments_from_code(code: str) -> str:
    """Return code without comments"""
    clean_code = []
    for line in code.splitlines():
        # remove comments from the line
        line = line.split("#")[0].strip()
        if line:
            clean_code.append(line)

    return "\n".join(clean_code)


def extract_variable_names_from_code(code: str) -> set[str]:
    """Extract variable names used in code via conv.state.<name>"""
    if not code:
        return set()

    names = set(CONV_STATE_DOT_NAME.findall(remove_comments_from_code(code)))

    return names


def get_references_from_prompt(
    prompt: str, valid_references: list[str] = None, raise_on_invalid: bool = False
) -> dict[str, dict[str, bool]]:
    """Extract references from a prompt string."""
    references: dict[str, dict[str, bool]] = {}
    for reference, regex in REFERENCES_PREFIX_MAP_REGEX.items():
        if valid_references is not None and reference not in valid_references:
            if not raise_on_invalid:
                continue

        references[reference] = {}
        for match in regex.findall(prompt):
            if raise_on_invalid and reference not in valid_references:
                raise ValueError(
                    f"Invalid reference type: {reference} is not a valid reference type for this resource. Valid references are: {valid_references}"
                )
            references[reference][match] = True

    return references


def validate_references(
    references: dict[str, dict[str, bool]],
    resource_mappings: list["ResourceMapping"],
    flow_name: str = None,
) -> tuple[bool, list[str]]:
    """Validate that all references in the prompt are valid.

    Args:
        references (dict[str, dict[str, bool]]): The references to validate.
        resource_mappings (list["ResourceMapping"]): The resource mappings to use for validation.
        flow_name (str): The flow name to use for validation.

    Returns:
        bool: True if all references are valid, False otherwise.
    """
    looking_for = {
        reference: set(values.keys()) for reference, values in references.items() if values
    }

    if not looking_for:
        return True, []

    # Build set of available (reference_type, resource_id) for O(1) lookups
    available = set()
    for rm in resource_mappings:
        if rm.flow_name not in (None, flow_name):
            continue
        ref_type = PREFIX_TO_REFERENCE.get(rm.resource_prefix)
        if ref_type:
            available.add((ref_type, rm.resource_id))

    invalid_references = []
    for reference, ids in looking_for.items():
        for rid in ids:
            if (reference, rid) not in available:
                invalid_references.append(f"{reference}: {rid}")

    return len(invalid_references) == 0, invalid_references


def replace_resource_ids_with_names(
    prompt: str,
    resource_mappings: list["ResourceMapping"],
    flow_folder_name: str = None,
) -> str:
    """Replace resource IDs with names in the prompt string."""
    # Build dict for O(1) lookups: (prefix, id) -> name
    id_to_name: dict[tuple[str, str], str] = {}
    for rm in resource_mappings:
        if rm.flow_name and clean_name(rm.flow_name) not in (None, flow_folder_name):
            continue
        if rm.resource_prefix:
            id_to_name[(rm.resource_prefix, rm.resource_id)] = rm.resource_name

    def _replacer(match: re.Match) -> str:
        key = (match.group(1), match.group(2))
        if key in id_to_name:
            return f"{{{{{key[0]}:{id_to_name[key]}}}}}"
        return match.group(0)

    return _REFERENCE_PATTERN.sub(_replacer, prompt)


def replace_resource_names_with_ids(
    prompt: str,
    resource_mappings: list["ResourceMapping"],
    flow_folder_name: str = None,
) -> str:
    """Replace resource names with IDs in the prompt string."""
    # Build dict for O(1) lookups: (prefix, name) -> id
    name_to_id: dict[tuple[str, str], str] = {}
    for rm in resource_mappings:
        if rm.flow_name and clean_name(rm.flow_name) not in (None, flow_folder_name):
            continue
        if rm.resource_prefix:
            name_to_id[(rm.resource_prefix, rm.resource_name)] = rm.resource_id

    def _replacer(match: re.Match) -> str:
        key = (match.group(1), match.group(2))
        if key in name_to_id:
            return f"{{{{{key[0]}:{name_to_id[key]}}}}}"
        return match.group(0)

    return _REFERENCE_PATTERN.sub(_replacer, prompt)


def get_flow_id_from_flow_name(
    formatted_flow_name: str, resource_mappings: list["ResourceMapping"]
) -> tuple[Optional[str], Optional[str]]:
    """Get the flow ID corresponding to the given flow name from resource mappings."""
    for res in resource_mappings:
        if (
            res.resource_type.__name__ == "FlowConfig"
            and clean_name(res.flow_name) == formatted_flow_name
        ):
            return res.resource_id, res.resource_name
    return None, None


def get_flow_name_from_path(file_path: str) -> Optional[str]:
    """Extract the flow name from the file path."""
    parts = file_path.split(os.sep)
    if "flows" in parts:
        flow_index = parts.index("flows")
        if flow_index < len(parts) - 1:
            flow_name = parts[flow_index + 1]
            return flow_name
    return None


def compute_hash(content: str) -> str:
    """Compute a hash of the given content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _canonicalize_for_hash(obj) -> str | int | float | bool | list | dict:
    """Convert to JSON-serializable form for deterministic hashing."""
    if isinstance(obj, dict):
        return {k: _canonicalize_for_hash(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_canonicalize_for_hash(item) for item in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return obj.value
    return str(obj)


def compute_hash_from_dict(data: dict) -> str:
    """Compute a hash of a dict without YAML serialization. Faster than compute_hash(dump_yaml(data))."""
    canonical = _canonicalize_for_hash(data)
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _format_def_line(line: str) -> str:
    line = line.strip()

    # remove spaces just inside parentheses
    line = re.sub(r"\(\s+", "(", line)
    line = re.sub(r"\s+\)", ")", line)

    # remove space before colon
    line = re.sub(r"\s+:", ":", line)

    # normalize multiple spaces everywhere else
    line = re.sub(r"\s+", " ", line)

    # remove comma after last parameter
    line = re.sub(r",\):$", "):", line)

    return line + "\n"


def restore_function_def_line(file_content: str, file_name: str) -> str:
    """Restore the main function definition to be formatted on one line.

    In AS, the main function is the same as the file name and is required
    to be formatted on one line. This function restores the main function
    definition to be formatted on one line.

    Args:
        file_content (str): The file content
        file_name (str): The name of the file and main function to be formatted

    Returns:
        str: The formatted file content
    """

    try:
        tree = ast.parse(file_content)
    except SyntaxError:
        return file_content

    fn = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == file_name:
            fn = node
            break

    if fn is None:
        return file_content

    lines = file_content.splitlines(keepends=True)
    i = fn.lineno - 1
    header_lines = []
    end_line = None
    for j in range(i, len(lines)):
        header_lines.append(lines[j])
        if lines[j].rstrip().endswith(":"):
            end_line = j
            break

    if end_line is None:
        return file_content

    one_line_header = " ".join(header_lines)
    formatted_one_line_header = _format_def_line(one_line_header)

    return "".join(lines[:i]) + formatted_one_line_header + "".join(lines[end_line + 1 :])


def format_code_with_ruff(code: str, file_name: str) -> str:
    """Format the given code string using ruff (via current Python; no PATH required).

    Uses the same interpreter as the running process, so ruff must be installed
    in that environment (e.g. as a dependency of this package).

    Args:
        code (str): The code to format.
        file_name (str): The name of the file being formatted.

    Returns:
        str: The formatted code.
    """
    ruff_cmd = [sys.executable, "-m", "ruff"]

    # Run ruff format
    process = subprocess.run(
        ruff_cmd + ["format", "-"],
        input=code.encode(),
        capture_output=True,
    )
    if process.returncode != 0:
        logger.error(f"Ruff formatting failed for {file_name}. " + process.stderr.decode())
        return code  # Return original code if ruff fails

    output = process.stdout.decode()

    # Run ruff check --fix to apply any additional fixes
    process = subprocess.run(
        ruff_cmd + ["check", "--fix", "-"],
        input=output.encode(),
        capture_output=True,
    )

    if process.returncode != 0:
        logger.error(f"Ruff check --fix failed for {file_name}. " + process.stderr.decode())
        return output  # Return code after format if check fails
    output = process.stdout.decode()

    return output


def format_yaml(yaml_content: str, file_name: str) -> str:
    """Format YAML content using ruamel.yaml (no external tools like prettier).

    Args:
        yaml_content (str): The YAML content to format.
        file_name (str): The name of the file (unused; for API compatibility).

    Returns:
        str: The formatted YAML content.
    """
    return format_yaml_python(yaml_content)


def format_yaml_python(yaml_content: str) -> str:
    """Format YAML content using ruamel.yaml (no external tools).

    Args:
        yaml_content: Raw YAML string.

    Returns:
        Formatted YAML string, or original on parse error.
    """
    try:
        data = load_yaml(yaml_content)
        if data is None:
            return yaml_content
        return dump_yaml(data)
    except Exception:
        return yaml_content


def format_json_python(json_content: str) -> str:
    """Format JSON content (no external tools).

    Args:
        json_content: Raw JSON string.

    Returns:
        Formatted JSON string (indent=2), or original on parse error.
    """
    try:
        data = json.loads(json_content)
        return json.dumps(data, indent=2) + "\n"
    except Exception:
        return json_content


SPACES_REGEX = re.compile(r"\s+")
NON_LETTER_REGEX = re.compile(r"[^\w\s]", re.UNICODE)
MULTI_UNDERSCORE_REGEX = re.compile(r"_+")


@functools.cache
def clean_name(name: str, lowercase: bool = True) -> str:
    """Convert a resource name to a folder-friendly format."""
    # Convert to lowercase if requested
    if lowercase:
        name = name.lower()
    # Replace all punctuation with spaces
    name = NON_LETTER_REGEX.sub(" ", name)
    # Replace spaces with underscores
    name = SPACES_REGEX.sub("_", name)
    # Replace multiple underscores with single underscore
    name = MULTI_UNDERSCORE_REGEX.sub("_", name)
    # Trim leading/trailing underscores
    name = name.strip("_")

    return name


def to_camel_case(s: str) -> str:
    """Convert a string to camelCase from snake_case"""
    word = "".join(word.capitalize() for word in s.split("_"))
    return word[0].lower() + word[1:]


def to_snake_case(s: str) -> str:
    """Convert a string to snake_case."""
    return "".join([("_" + c.lower()) if c.isupper() else c for c in s]).lstrip("_")


def convert_keys_to_snake_case(dict_obj: dict) -> dict:
    """Convert config keys to snake_case for consistency."""
    return {to_snake_case(k): v for k, v in dict_obj.items()}


def assign_flow_positions(
    nodes: list["BaseFlowStep"],
    start_node_id: str,
    x_start: float = 0.0,
    y_start: float = 0.0,
    x_gap: float = 600.0,
    y_gap: float = 500.0,
) -> None:
    """Assign positions to flow nodes in a grid layout.

    Args:
        nodes (list[dict]): List of node dictionaries to assign positions to.
        x_start (float): Starting x position.
        y_start (float): Starting y position.
        x_gap (float): Gap between nodes in the x direction.
        y_gap (float): Gap between nodes in the y direction.
    """
    known_positions = [node.position for node in nodes if node.position]

    x_max = x_start
    if known_positions:
        x_max = max(pos["x"] for pos in known_positions)

    # Assign start node position first
    assigning_order: list[BaseFlowStep] = []
    for node in nodes:
        if node.step_id != start_node_id:
            assigning_order.append(node)
        else:
            assigning_order.insert(0, node)

    for node in assigning_order:
        if node.position:
            continue

        if node.step_id == start_node_id and not known_positions:
            node.position = {"x": x_start, "y": y_start}
        else:
            x_max = assign_flow_node_position(
                node,
                nodes,
                visited_node_ids=set(),
                x_start=x_max,
                y_start=y_start,
                x_gap=x_gap,
                y_gap=y_gap,
            )

    # Assign conditions label positions
    for node in nodes:
        if not hasattr(node, "conditions"):
            continue
        for condition in node.conditions:
            if condition.position:
                continue
            # If child_node position condition between parent and child
            if condition.child_step:
                child_node = next((n for n in nodes if n.step_id == condition.child_step), None)
                if child_node and child_node.position and node.position:
                    condition.position = {
                        "x": (node.position["x"] + child_node.position["x"]) / 2,
                        "y": (node.position["y"] + child_node.position["y"]) / 2,
                    }
            elif not condition.exit_flow_position:
                # Collect sibling positions: child nodes and other exit_flow_positions
                sibling_x_positions = []

                # Get positions of child node siblings and other exit_flow_positions
                for other_condition in node.conditions:
                    if other_condition == condition:
                        continue

                    # Check for child node siblings
                    if other_condition.child_step:
                        sibling_node = next(
                            (n for n in nodes if n.step_id == other_condition.child_step),
                            None,
                        )
                        if sibling_node and sibling_node.position:
                            sibling_x_positions.append(sibling_node.position["x"])

                    # Check for other exit_flow_positions
                    if other_condition.exit_flow_position:
                        sibling_x_positions.append(other_condition.exit_flow_position["x"])

                max_x_sibling = (
                    max(sibling_x_positions + [node.position["x"]]) + x_gap
                    if sibling_x_positions
                    else node.position["x"]
                )
                condition.exit_flow_position = {
                    "x": max_x_sibling,
                    "y": node.position["y"] + y_gap,
                }
                condition.position = {
                    "x": (node.position["x"] + condition.exit_flow_position["x"]) / 2,
                    "y": node.position["y"] + y_gap / 2,
                }


def assign_flow_node_position(
    node: "BaseFlowStep",
    nodes: list["BaseFlowStep"],
    visited_node_ids: set[str] = None,
    x_start: float = 0.0,
    y_start: float = 0.0,
    x_gap: float = 600.0,
    y_gap: float = 150.0,
) -> float:
    """Assign positions to flow nodes in a grid layout.

    Args:
        nodes (list[dict]): List of node dictionaries to assign positions to.
        x_start (float): Starting x position.
        y_start (float): Starting y position.
        x_gap (float): Gap between nodes in the x direction.
        y_gap (float): Gap between nodes in the y direction.

    Returns:
        float: The maximum x position assigned.
    """
    if node.position:
        return x_start

    if not visited_node_ids:
        visited_node_ids = set()

    if node.step_id in visited_node_ids:
        # Prevent infinite recursion on cycles
        node.position = {
            "x": x_start + x_gap,
            "y": y_start,
        }
        return node.position["x"]

    # Work out if node has a parent node
    parent_node = None
    max_x_sibling = None
    for potential_parent in nodes:
        if not hasattr(potential_parent, "conditions"):
            continue
        for condition in potential_parent.conditions:
            if condition.child_step == node.step_id:
                parent_node = potential_parent

                if not parent_node.position:
                    # Parent has no position yet, assign it first
                    x_start = assign_flow_node_position(
                        parent_node,
                        nodes,
                        visited_node_ids | {node.step_id},
                        x_start,
                        y_start,
                        x_gap,
                        y_gap,
                    )

                sibling_ids = [
                    c.child_step for c in parent_node.conditions if c.child_step != node.step_id
                ]
                sibling_x_positions = [
                    n.position["x"] for n in nodes if n.step_id in sibling_ids and n.position
                ]
                # Add x positions for end flow conditions
                for c in parent_node.conditions:
                    if c.exit_flow_position and c.child_step not in sibling_ids:
                        sibling_x_positions.append(c.exit_flow_position["x"])

                max_x_sibling = (
                    max(sibling_x_positions + [parent_node.position["x"]]) + x_gap
                    if sibling_x_positions
                    else parent_node.position["x"]
                )
                break

    if parent_node:
        # Position below parent node
        node.position = {
            "x": max_x_sibling,
            "y": parent_node.position["y"] + y_gap,
        }

        return max(x_start, node.position["x"])

    else:
        # Position to the right of the last node
        node.position = {
            "x": x_start + x_gap,
            "y": y_start,
        }
        return node.position["x"]
