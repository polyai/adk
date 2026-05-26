"""Flow layout utilities for positioning flow nodes.

Copyright PolyAI Limited
"""

import re
from typing import TYPE_CHECKING

import networkx as nx

from poly.resources.flows import StepType
from poly.resources.resource_utils import extract_go_to_steps, remove_comments_from_code

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
CHARS_PER_LINE = 65.0
STEP_PADDING = 80.0
LABEL_CHAR_WIDTH = 7.0
LABEL_PADDING = 20.0

_FLOW_FUNC_REF_RE = re.compile(r"\{\{ft:([^}]+)\}\}")


def _build_flow_func_targets(flow_functions: list) -> dict[str, list[str]]:
    """Map flow function name/ID -> list of step names from goto_step calls."""
    targets: dict[str, list[str]] = {}
    for func in flow_functions:
        code = getattr(func, "code", None)
        if not code:
            continue
        clean = remove_comments_from_code(code)
        step_names = [step for step, _ in extract_go_to_steps(clean)]
        if step_names:
            targets[func.name] = step_names
            resource_id = getattr(func, "resource_id", None)
            if resource_id:
                targets[resource_id] = step_names
    return targets


def _build_graph(
    nodes: list["BaseFlowStep"],
    flow_functions: list | None = None,
) -> tuple[nx.DiGraph, set[str]]:
    """Build a directed graph from flow nodes."""
    node_by_name: dict[str, "BaseFlowStep"] = {}
    node_by_id: dict[str, "BaseFlowStep"] = {}
    for n in nodes:
        node_by_name[n.name] = n
        node_by_id[n.step_id] = n

    func_targets = _build_flow_func_targets(flow_functions or [])

    G = nx.DiGraph()
    exit_node_ids: set[str] = set()

    for n in nodes:
        G.add_node(n.step_id)

    for node in nodes:
        if hasattr(node, "conditions") and node.conditions:
            for cond in node.conditions:
                if cond.child_step:
                    target = node_by_name.get(cond.child_step) or node_by_id.get(cond.child_step)
                    if target:
                        G.add_edge(node.step_id, target.step_id)
                elif cond.condition_type.value == "exit_flow_condition":
                    exit_id = f"{node.step_id}:exit:{cond.resource_id}"
                    G.add_node(exit_id)
                    G.add_edge(node.step_id, exit_id)
                    exit_node_ids.add(exit_id)

        prompt = getattr(node, "prompt", None)
        if prompt and func_targets:
            for match in _FLOW_FUNC_REF_RE.finditer(prompt):
                for target_name in func_targets.get(match.group(1), []):
                    target = node_by_name.get(target_name) or node_by_id.get(target_name)
                    if target and not G.has_edge(node.step_id, target.step_id):
                        G.add_edge(node.step_id, target.step_id)

    return G, exit_node_ids


def _assign_layers(G: nx.DiGraph, start_node_id: str) -> dict[str, int]:
    """BFS layer assignment using networkx."""
    layers: dict[str, int] = {}
    for depth, layer_nodes in enumerate(nx.bfs_layers(G, start_node_id)):
        for nid in layer_nodes:
            layers[nid] = depth

    if len(layers) < len(G):
        max_layer = max(layers.values(), default=-1) + 1
        for nid in G.nodes:
            if nid not in layers:
                layers[nid] = max_layer
    return layers


def _order_within_layers(
    G: nx.DiGraph,
    layers: dict[str, int],
) -> dict[int, list[str]]:
    """Order nodes within each layer using barycenter heuristic."""
    layer_lists: dict[int, list[str]] = {}
    for nid, layer in layers.items():
        layer_lists.setdefault(layer, []).append(nid)

    for layer in sorted(layer_lists):
        if layer == 0:
            continue
        prev_order = {nid: idx for idx, nid in enumerate(layer_lists[layer - 1])}

        def barycenter(nid: str) -> float:
            preds = [p for p in G.predecessors(nid) if layers.get(p, -1) < layers.get(nid, -1)]
            p = [prev_order[pid] for pid in preds if pid in prev_order]
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
    if node.step_type == StepType.DEFAULT_STEP:
        # If extracted entities exist, add extra line for
        line_count += 1 + len(node.extracted_entities) // 5
    return line_count * LINE_HEIGHT + STEP_PADDING + STEP_HEIGHT


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
            elif node_map.get(nid) and node_map[nid].step_type == StepType.FUNCTION_STEP:
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

    Uses networkx for graph structure and BFS layer assignment, with
    barycenter heuristic for node ordering within layers.

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
        G, exit_node_ids = _build_graph(nodes, flow_functions)
        layers = _assign_layers(G, start_node_id)
        layer_lists = _order_within_layers(G, layers)
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
    G, exit_node_ids = _build_graph(all_nodes, flow_functions)

    node_by_id = {n.step_id: n for n in all_nodes}

    for node in new_nodes:
        positioned_parents = [
            node_by_id[pid]
            for pid in G.predecessors(node.step_id)
            if pid in node_by_id and node_by_id[pid].position
        ]

        if positioned_parents:
            avg_x = sum(p.position["x"] for p in positioned_parents) / len(positioned_parents)
            max_y = max(p.position["y"] for p in positioned_parents)
            parent_h = max(
                _estimate_step_height(p) if hasattr(p, "prompt") else STEP_HEIGHT
                for p in positioned_parents
            )

            sibling_xs = []
            for parent in positioned_parents:
                for child_id in G.successors(parent.step_id):
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


LABEL_ICON_WIDTH = 25.0


def _estimate_label_width(text: str, has_icon: bool = False) -> float:
    """Estimate the rendered width of a condition label."""
    return len(text) * LABEL_CHAR_WIDTH + LABEL_PADDING + (LABEL_ICON_WIDTH if has_icon else 0)


def _assign_condition_positions(nodes: list["BaseFlowStep"]) -> None:
    """Assign label positions for conditions, avoiding overlap with nodes."""
    node_by_name: dict[str, "BaseFlowStep"] = {n.name: n for n in nodes}
    node_by_id: dict[str, "BaseFlowStep"] = {n.step_id: n for n in nodes}

    node_boxes = []
    for n in nodes:
        if n.position:
            h = _estimate_step_height(n) if hasattr(n, "prompt") else STEP_HEIGHT
            node_boxes.append((n.position["x"], n.position["y"], STEP_WIDTH, h))

    def _overlaps_node(x: float, y: float) -> bool:
        pad = 20.0
        for bx, by, bw, bh in node_boxes:
            if bx - pad <= x <= bx + bw + pad and by - pad <= y <= by + bh + pad:
                return True
        return False

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
                    has_icon = node.step_type != StepType.FUNCTION_STEP
                    label_offset = _estimate_label_width(condition.name, has_icon) / 2
                    is_back_edge = child.position["y"] <= node.position["y"]
                    if is_back_edge:
                        parent_w = (
                            FUNC_STEP_WIDTH
                            if node.step_type == StepType.FUNCTION_STEP
                            else STEP_WIDTH
                        )
                        condition.ingress = "bottom"
                        condition.position = {
                            "x": node.position["x"] + parent_w + 50,
                            "y": node.position["y"],
                        }
                    else:
                        parent_w = (
                            FUNC_STEP_WIDTH
                            if node.step_type == StepType.FUNCTION_STEP
                            else STEP_WIDTH
                        )
                        mid_x = node.position["x"] + parent_w / 2 - label_offset
                        mid_y = (node.position["y"] + child.position["y"]) / 2
                        if _overlaps_node(node.position["x"] + parent_w / 2, mid_y):
                            parent_h = (
                                _estimate_step_height(node)
                                if hasattr(node, "prompt")
                                else STEP_HEIGHT
                            )
                            mid_y = node.position["y"] + parent_h + 20
                        condition.position = {"x": mid_x, "y": mid_y}
            elif condition.exit_flow_position:
                label_offset = _estimate_label_width(condition.name) / 2
                condition.position = {
                    "x": (node.position["x"] + condition.exit_flow_position["x"]) / 2
                    - label_offset,
                    "y": (node.position["y"] + condition.exit_flow_position["y"]) / 2,
                }
