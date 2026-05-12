"""Flow layout utilities for positioning flow nodes.

Copyright PolyAI Limited
"""

import re
from typing import TYPE_CHECKING

from poly.resources.resource_utils import remove_comments_from_code

if TYPE_CHECKING:
    from poly.resources.flows import BaseFlowStep

STEP_WIDTH = 500.0
STEP_HEIGHT = 145.0
FUNC_STEP_WIDTH = 300.0
EXIT_NODE_WIDTH = 100.0
EXIT_NODE_HEIGHT = 40.0
RANK_SEP = 100.0
NODE_SEP = 200.0
LINE_HEIGHT = 20.0
CHARS_PER_LINE = 45.0
STEP_PADDING = 80.0

_GOTO_STEP_RE = re.compile(
    r'flow\.goto_step\(\s*"((?:[^"\\]|\\.)*)"'
    r"|flow\.goto_step\(\s*'((?:[^'\\]|\\.)*)'",
)

_FLOW_FUNC_REF_RE = re.compile(r"\{\{ft:([^}]+)\}\}")


def _extract_goto_targets(node: "BaseFlowStep") -> list[str]:
    """Extract step names from flow.goto_step() calls in a FunctionStep's code."""
    code = getattr(node, "code", None)
    if not code:
        return []
    clean = remove_comments_from_code(code)
    return [m.group(1) or m.group(2) for m in _GOTO_STEP_RE.finditer(clean)]


def _build_flow_func_targets(flow_functions: list) -> dict[str, list[str]]:
    """Map flow function name/ID -> list of step names from goto_step calls."""
    targets: dict[str, list[str]] = {}
    for func in flow_functions:
        code = getattr(func, "code", None)
        if not code:
            continue
        clean = remove_comments_from_code(code)
        step_names = [m.group(1) or m.group(2) for m in _GOTO_STEP_RE.finditer(clean)]
        if step_names:
            targets[func.name] = step_names
            resource_id = getattr(func, "resource_id", None)
            if resource_id:
                targets[resource_id] = step_names
    return targets


def _build_adjacency(
    nodes: list["BaseFlowStep"],
    flow_functions: list | None = None,
) -> tuple[dict[str, list[str]], set[str]]:
    """Build adjacency list and collect exit-flow condition IDs."""
    node_by_name: dict[str, "BaseFlowStep"] = {}
    node_by_id: dict[str, "BaseFlowStep"] = {}
    for n in nodes:
        node_by_name[n.name] = n
        node_by_id[n.step_id] = n

    func_targets = _build_flow_func_targets(flow_functions or [])

    adj: dict[str, list[str]] = {n.step_id: [] for n in nodes}
    exit_node_ids: set[str] = set()

    for node in nodes:
        if hasattr(node, "conditions") and node.conditions:
            for cond in node.conditions:
                if cond.child_step:
                    target = node_by_name.get(cond.child_step) or node_by_id.get(cond.child_step)
                    if target:
                        adj[node.step_id].append(target.step_id)
                elif cond.condition_type.value == "exit_flow_condition":
                    exit_id = f"{node.step_id}:exit:{cond.resource_id}"
                    adj.setdefault(node.step_id, []).append(exit_id)
                    adj[exit_id] = []
                    exit_node_ids.add(exit_id)

        for target_name in _extract_goto_targets(node):
            target = node_by_name.get(target_name) or node_by_id.get(target_name)
            if target and target.step_id not in adj.get(node.step_id, []):
                adj[node.step_id].append(target.step_id)

        prompt = getattr(node, "prompt", None)
        if prompt and func_targets:
            for match in _FLOW_FUNC_REF_RE.finditer(prompt):
                for target_name in func_targets.get(match.group(1), []):
                    target = node_by_name.get(target_name) or node_by_id.get(target_name)
                    if target and target.step_id not in adj.get(node.step_id, []):
                        adj[node.step_id].append(target.step_id)

    return adj, exit_node_ids


def _assign_layers(adj: dict[str, list[str]], start_node_id: str) -> dict[str, int]:
    """BFS layer assignment from start node. Back-edges are skipped."""
    layers: dict[str, int] = {start_node_id: 0}
    queue = [start_node_id]
    while queue:
        current = queue.pop(0)
        for child in adj.get(current, []):
            if child not in layers:
                layers[child] = layers[current] + 1
                queue.append(child)

    all_ids = set(adj.keys())
    if len(layers) < len(all_ids):
        max_layer = max(layers.values()) + 1
        for nid in all_ids:
            if nid not in layers:
                layers[nid] = max_layer
    return layers


def _order_within_layers(
    layers: dict[str, int],
    adj: dict[str, list[str]],
) -> dict[int, list[str]]:
    """Order nodes within each layer using barycenter heuristic."""
    layer_lists: dict[int, list[str]] = {}
    for nid, layer in layers.items():
        layer_lists.setdefault(layer, []).append(nid)

    parents: dict[str, list[str]] = {nid: [] for nid in layers}
    for src, targets in adj.items():
        for tgt in targets:
            if tgt in parents and layers.get(src, -1) < layers.get(tgt, -1):
                parents[tgt].append(src)

    for layer in sorted(layer_lists):
        if layer == 0:
            continue
        prev_order = {nid: idx for idx, nid in enumerate(layer_lists[layer - 1])}

        def barycenter(nid: str) -> float:
            p = [prev_order[pid] for pid in parents.get(nid, []) if pid in prev_order]
            return sum(p) / len(p) if p else float("inf")

        layer_lists[layer].sort(key=barycenter)

    return layer_lists


def _estimate_step_height(node: "BaseFlowStep") -> float:
    """Estimate rendered card height from prompt length."""
    prompt = getattr(node, "prompt", None)
    if not prompt:
        return STEP_HEIGHT
    line_count = 0
    for line in prompt.splitlines():
        line_count += max(1, len(line) / CHARS_PER_LINE)
    return max(STEP_HEIGHT, line_count * LINE_HEIGHT + STEP_PADDING)


def _compute_positions(
    layer_lists: dict[int, list[str]],
    exit_node_ids: set[str],
    node_map: dict[str, "BaseFlowStep"] | None = None,
) -> dict[str, dict[str, float]]:
    """Assign x,y coordinates based on layer and position within layer."""
    positions: dict[str, dict[str, float]] = {}
    y = 0.0

    for layer in sorted(layer_lists):
        node_ids = layer_lists[layer]
        n = len(node_ids)
        if n == 0:
            continue

        max_h = 0.0
        widths = []
        for nid in node_ids:
            if nid in exit_node_ids:
                widths.append(EXIT_NODE_WIDTH)
                max_h = max(max_h, EXIT_NODE_HEIGHT)
            else:
                widths.append(STEP_WIDTH)
                node = node_map.get(nid) if node_map else None
                h = _estimate_step_height(node) if node else STEP_HEIGHT
                max_h = max(max_h, h)

        total_width = sum(widths) + NODE_SEP * (n - 1)
        x = -total_width / 2.0

        for i, nid in enumerate(node_ids):
            w = widths[i]
            positions[nid] = {"x": round(x, 1), "y": round(y, 1)}
            x += w + NODE_SEP

        y += max_h + RANK_SEP

    if node_map:
        func_offset = (STEP_WIDTH - FUNC_STEP_WIDTH) / 2
        exit_offset = (STEP_WIDTH - EXIT_NODE_WIDTH) / 2
        for nid, pos in positions.items():
            if nid in exit_node_ids:
                pos["x"] = round(pos["x"] + exit_offset, 1)
            elif node_map.get(nid) and not hasattr(node_map[nid], "prompt"):
                pos["x"] = round(pos["x"] + func_offset, 1)

    return positions


def assign_flow_positions(
    nodes: list["BaseFlowStep"],
    start_node_id: str,
    x_start: float = 0.0,
    y_start: float = 0.0,
    x_gap: float = 600.0,
    y_gap: float = 500.0,
    flow_functions: list | None = None,
    clean: bool = False,
) -> None:
    """Assign positions to flow nodes using hierarchical layout.

    Uses a simplified Sugiyama algorithm (BFS layers, barycenter ordering)
    matching GLOT's dagre-based layout.  Exit-flow conditions are laid out
    as separate small nodes one layer below their parent step.

    Args:
        nodes: Flow step objects to position (FlowStep and FunctionStep).
        start_node_id: The step_id of the flow's start step.
        x_start: Unused, kept for backwards compatibility.
        y_start: Unused, kept for backwards compatibility.
        x_gap: Unused, kept for backwards compatibility.
        y_gap: Unused, kept for backwards compatibility.
        flow_functions: Optional list of flow Function objects whose code
            is used to resolve {{ft:func}} prompt references into edges.
        clean: If True, clear all positions and recompute from scratch.
            Used for new flows. If False, only position unpositioned nodes
            relative to their parents' existing positions.
    """
    if not nodes:
        return

    if clean:
        for node in nodes:
            node.position = {}
            if hasattr(node, "conditions") and node.conditions:
                for cond in node.conditions:
                    cond.position = {}
                    cond.exit_flow_position = {}

    unpositioned = [n for n in nodes if not n.position]
    if not unpositioned:
        _assign_condition_positions(nodes)
        return

    if clean:
        node_map = {n.step_id: n for n in nodes}
        adj, exit_node_ids = _build_adjacency(nodes, flow_functions)
        layers = _assign_layers(adj, start_node_id)
        layer_lists = _order_within_layers(layers, adj)
        positions = _compute_positions(layer_lists, exit_node_ids, node_map)

        for node in nodes:
            if node.step_id in positions:
                node.position = positions[node.step_id]

        for node in nodes:
            if not hasattr(node, "conditions") or not node.conditions:
                continue
            for cond in node.conditions:
                exit_id = f"{node.step_id}:exit:{cond.resource_id}"
                if exit_id in positions:
                    cond.exit_flow_position = positions[exit_id]
    else:
        _place_new_nodes(nodes, unpositioned, flow_functions)

    _assign_condition_positions(nodes)


def _place_new_nodes(
    all_nodes: list["BaseFlowStep"],
    new_nodes: list["BaseFlowStep"],
    flow_functions: list | None = None,
) -> None:
    """Place new nodes relative to their parents' existing positions."""
    adj, exit_node_ids = _build_adjacency(all_nodes, flow_functions)

    node_by_id = {n.step_id: n for n in all_nodes}
    parents: dict[str, list[str]] = {n.step_id: [] for n in all_nodes}
    for src, targets in adj.items():
        for tgt in targets:
            if tgt in parents:
                parents[tgt].append(src)

    for node in new_nodes:
        parent_ids = parents.get(node.step_id, [])
        positioned_parents = [
            node_by_id[pid] for pid in parent_ids if pid in node_by_id and node_by_id[pid].position
        ]

        if positioned_parents:
            avg_x = sum(p.position["x"] for p in positioned_parents) / len(positioned_parents)
            max_y = max(p.position["y"] for p in positioned_parents)
            parent_h = max(
                _estimate_step_height(p) if hasattr(p, "prompt") else STEP_HEIGHT
                for p in positioned_parents
            )

            sibling_xs = []
            for pid in parent_ids:
                for child_id in adj.get(pid, []):
                    child = node_by_id.get(child_id)
                    if child and child.position and child.step_id != node.step_id:
                        sibling_xs.append(child.position["x"])

            x = avg_x
            if sibling_xs:
                x = max(sibling_xs) + STEP_WIDTH + NODE_SEP

            node.position = {
                "x": round(x, 1),
                "y": round(max_y + parent_h + RANK_SEP, 1),
            }
        else:
            all_x = [n.position["x"] for n in all_nodes if n.position]
            x = max(all_x) + STEP_WIDTH + NODE_SEP if all_x else 0.0
            all_y = [n.position["y"] for n in all_nodes if n.position]
            y = min(all_y) if all_y else 0.0
            node.position = {"x": round(x, 1), "y": round(y, 1)}


def _assign_condition_positions(nodes: list["BaseFlowStep"]) -> None:
    """Assign label positions for conditions (midpoint between parent and target)."""
    node_by_name: dict[str, "BaseFlowStep"] = {n.name: n for n in nodes}
    node_by_id: dict[str, "BaseFlowStep"] = {n.step_id: n for n in nodes}

    for node in nodes:
        if not hasattr(node, "conditions") or not node.conditions:
            continue
        if not node.position:
            continue

        for condition in node.conditions:
            if condition.position:
                continue

            if condition.child_step:
                child = node_by_name.get(condition.child_step) or node_by_id.get(
                    condition.child_step
                )
                if child and child.position:
                    condition.position = {
                        "x": (node.position["x"] + child.position["x"]) / 2,
                        "y": (node.position["y"] + child.position["y"]) / 2,
                    }
            elif condition.exit_flow_position:
                condition.position = {
                    "x": (node.position["x"] + condition.exit_flow_position["x"]) / 2,
                    "y": (node.position["y"] + condition.exit_flow_position["y"]) / 2,
                }
