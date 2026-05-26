"""Flow layout utilities for positioning flow nodes.

Copyright PolyAI Limited
"""

import math
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
FUNC_STEP_HEIGHT = 60.0
EXIT_NODE_WIDTH = 140.0
EXIT_NODE_HEIGHT = 48.0
RANK_SEP = 200.0
NODE_SEP = 200.0
LINE_HEIGHT = 21.0
CHARS_PER_LINE = 66.0
CARD_PADDING = 32.0
ENTITY_CHIP_HEIGHT = 24.0
ENTITY_CHIP_MIN_WIDTH = 80.0
ENTITY_CHIP_GAP = 8.0
ENTITY_SECTION_HEADER = 40.0
LABEL_CHAR_WIDTH = 7.0
LABEL_PADDING = 20.0
LABEL_ICON_WIDTH = 25.0
CONDITION_LABEL_OFFSET_Y = 100.0

_FLOW_FUNC_REF_RE = re.compile(r"\{\{ft:([^}]+)\}\}")


def _node_width(node: "BaseFlowStep") -> float:
    """Return the rendered width for a node based on its step type."""
    return FUNC_STEP_WIDTH if node.step_type == StepType.FUNCTION_STEP else STEP_WIDTH


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


def _resolve_node(
    name_or_id: str,
    by_name: dict[str, "BaseFlowStep"],
    by_id: dict[str, "BaseFlowStep"],
) -> "BaseFlowStep | None":
    """Look up a node by name first, then by ID."""
    return by_name.get(name_or_id) or by_id.get(name_or_id)


def _build_graph(
    nodes: list["BaseFlowStep"],
    flow_functions: list | None = None,
) -> tuple[nx.DiGraph, set[str]]:
    """Build a directed graph from flow nodes."""
    node_by_name = {n.name: n for n in nodes}
    node_by_id = {n.step_id: n for n in nodes}
    func_targets = _build_flow_func_targets(flow_functions or [])

    G = nx.DiGraph()
    exit_node_ids: set[str] = set()

    for n in nodes:
        G.add_node(n.step_id)

    for node in nodes:
        if hasattr(node, "conditions") and node.conditions:
            for cond in node.conditions:
                if cond.child_step:
                    target = _resolve_node(cond.child_step, node_by_name, node_by_id)
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
                    target = _resolve_node(target_name, node_by_name, node_by_id)
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
        return FUNC_STEP_HEIGHT

    line_count = 0
    for line in prompt.splitlines():
        line_count += max(1, math.ceil(len(line) / CHARS_PER_LINE))
    height = STEP_HEIGHT + line_count * LINE_HEIGHT

    if node.step_type == StepType.DEFAULT_STEP:
        entity_count = len(node.extracted_entities)
        if entity_count > 0:
            chips_per_row = max(
                1, int((STEP_WIDTH - CARD_PADDING) / (ENTITY_CHIP_MIN_WIDTH + ENTITY_CHIP_GAP))
            )
            entity_rows = math.ceil(entity_count / chips_per_row)
            height += ENTITY_SECTION_HEADER + entity_rows * (ENTITY_CHIP_HEIGHT + ENTITY_CHIP_GAP)

    return height


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
        if not node_ids:
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

        total_width = sum(widths) + NODE_SEP * (len(node_ids) - 1)
        x = -total_width / 2.0

        for i, nid in enumerate(node_ids):
            positions[nid] = {"x": round(x, 1), "y": round(y, 1)}
            x += widths[i] + NODE_SEP

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
    flow_functions: list | None = None,
    clean: bool = False,
    **_kwargs: object,
) -> None:
    """Assign positions to flow nodes using hierarchical layout.

    Uses networkx for graph structure and BFS layer assignment, with
    barycenter heuristic for node ordering within layers.

    Args:
        nodes: Flow step objects to position (FlowStep and FunctionStep).
        start_node_id: The step_id of the flow's start step.
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
    G, _ = _build_graph(all_nodes, flow_functions)
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


def _estimate_label_width(text: str, has_icon: bool = False) -> float:
    """Estimate the rendered width of a condition label."""
    return len(text) * LABEL_CHAR_WIDTH + LABEL_PADDING + (LABEL_ICON_WIDTH if has_icon else 0)


def _assign_condition_positions(nodes: list["BaseFlowStep"]) -> None:
    """Assign label positions for conditions."""
    node_by_name = {n.name: n for n in nodes}
    node_by_id = {n.step_id: n for n in nodes}

    for node in nodes:
        if not hasattr(node, "conditions") or not node.conditions:
            continue
        if not node.position:
            continue

        for condition in node.conditions:
            if condition.position:
                continue

            if condition.child_step:
                child = _resolve_node(condition.child_step, node_by_name, node_by_id)
                if not child or not child.position:
                    continue

                has_icon = node.step_type != StepType.FUNCTION_STEP
                label_offset = _estimate_label_width(condition.name, has_icon) / 2
                is_back_edge = child.position["y"] <= node.position["y"]

                if is_back_edge:
                    condition.ingress = "bottom"
                    condition.position = {
                        "x": node.position["x"] + _node_width(node) + 50,
                        "y": node.position["y"],
                    }
                else:
                    child_w = _node_width(child)
                    condition.position = {
                        "x": child.position["x"] + child_w / 2 - label_offset,
                        "y": child.position["y"] - CONDITION_LABEL_OFFSET_Y,
                    }

            elif condition.exit_flow_position:
                label_offset = _estimate_label_width(condition.name) / 2
                condition.position = {
                    "x": (node.position["x"] + condition.exit_flow_position["x"]) / 2
                    - label_offset,
                    "y": (node.position["y"] + condition.exit_flow_position["y"]) / 2,
                }
