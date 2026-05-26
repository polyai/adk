"""Flow layout utilities for positioning flow nodes.

Copyright PolyAI Limited
"""

import math
import re
from typing import TYPE_CHECKING

import networkx as nx

from poly.handlers.protobuf.flows_pb2 import (
    FlowPositionDetail,
    FlowStepPositionDetails,
    FunctionStepConditionPositionDetail,
    FunctionStepExitFlowPositionDetail,
    FunctionStepPositionDetail,
    MoveFlowComponents,
    NoCodeStepConditionPositionDetail,
    NoCodeStepExitFlowPositionDetail,
    NoCodeStepPositionDetail,
    StepPosition,
)
from poly.resources.flows import ConditionType, StepType
from poly.resources.resource_utils import extract_go_to_steps, remove_comments_from_code

if TYPE_CHECKING:
    from poly.resources.flows import BaseFlowStep, Condition

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
LABEL_GAP = 10.0
CONDITION_LABEL_OFFSET_Y = 100.0
BACK_EDGE_X_OFFSET = 50.0

_FLOW_FUNC_REF_RE = re.compile(r"\{\{ft:([^}]+)\}\}")

NodeIndexes = tuple[dict[str, "BaseFlowStep"], dict[str, "BaseFlowStep"]]


def _build_node_indexes(nodes: list["BaseFlowStep"]) -> NodeIndexes:
    """Build name->node and id->node lookup dicts."""
    return {n.name: n for n in nodes}, {n.step_id: n for n in nodes}


def _has_conditions(node: "BaseFlowStep") -> bool:
    """Check if a node has conditions."""
    return hasattr(node, "conditions") and bool(node.conditions)


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
    indexes: NodeIndexes,
    flow_functions: list | None = None,
) -> tuple[nx.DiGraph, set[str]]:
    """Build a directed graph from flow nodes."""
    node_by_name, node_by_id = indexes
    func_targets = _build_flow_func_targets(flow_functions or [])

    G = nx.DiGraph()
    exit_node_ids: set[str] = set()

    for n in nodes:
        G.add_node(n.step_id)

    for node in nodes:
        if _has_conditions(node):
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


def _get_node_width(
    nid: str, exit_node_ids: set[str], node_map: dict[str, "BaseFlowStep"]
) -> float:
    """Return the rendered width of a node."""
    if nid in exit_node_ids:
        return EXIT_NODE_WIDTH
    node = node_map.get(nid)
    if node and node.step_type == StepType.FUNCTION_STEP:
        return FUNC_STEP_WIDTH
    return STEP_WIDTH


def _get_node_height(
    nid: str, exit_node_ids: set[str], node_map: dict[str, "BaseFlowStep"]
) -> float:
    """Return the rendered height of a node."""
    if nid in exit_node_ids:
        return EXIT_NODE_HEIGHT
    node = node_map.get(nid)
    return _estimate_step_height(node) if node else STEP_HEIGHT


def _compute_positions(
    G: nx.DiGraph,
    layer_lists: dict[int, list[str]],
    exit_node_ids: set[str],
    node_map: dict[str, "BaseFlowStep"],
) -> dict[str, dict[str, float]]:
    """Assign x,y positions, centering children under their parents."""
    positions: dict[str, dict[str, float]] = {}
    y = 0.0

    for layer in sorted(layer_lists):
        node_ids = layer_lists[layer]
        if not node_ids:
            continue

        max_h = max(_get_node_height(nid, exit_node_ids, node_map) for nid in node_ids)
        widths = {nid: _get_node_width(nid, exit_node_ids, node_map) for nid in node_ids}

        if layer == 0:
            total_width = sum(widths.values()) + NODE_SEP * (len(node_ids) - 1)
            x = -total_width / 2.0
            for nid in node_ids:
                positions[nid] = {"x": round(x, 1), "y": round(y, 1)}
                x += widths[nid] + NODE_SEP
        else:
            for nid in node_ids:
                parent_xs = []
                for pred in G.predecessors(nid):
                    if pred in positions:
                        pw = _get_node_width(pred, exit_node_ids, node_map)
                        parent_xs.append(positions[pred]["x"] + pw / 2)
                if parent_xs:
                    center_x = sum(parent_xs) / len(parent_xs)
                else:
                    center_x = 0.0
                positions[nid] = {
                    "x": round(center_x - widths[nid] / 2, 1),
                    "y": round(y, 1),
                }

            # Resolve overlaps within the layer
            sorted_ids = sorted(node_ids, key=lambda nid: positions[nid]["x"])
            for i in range(1, len(sorted_ids)):
                prev = sorted_ids[i - 1]
                curr = sorted_ids[i]
                min_x = positions[prev]["x"] + widths[prev] + NODE_SEP
                if positions[curr]["x"] < min_x:
                    positions[curr]["x"] = round(min_x, 1)

        y += max_h + RANK_SEP

    return positions


def assign_flow_positions(
    nodes: list["BaseFlowStep"],
    start_node_id: str,
    flow_functions: list | None = None,
    clean: bool = False,
) -> None:
    """Assign positions to flow nodes using hierarchical layout.

    Args:
        nodes: Flow step objects to position (FlowStep and FunctionStep).
        start_node_id: The step_id of the flow's start step.
        flow_functions: Optional list of flow Function objects whose code
            is used to resolve {{ft:func}} prompt references into edges.
        clean: If True, clear all positions and recompute from scratch.
    """
    if not nodes:
        return

    indexes = _build_node_indexes(nodes)

    if clean:
        for node in nodes:
            node.position = {}
            if _has_conditions(node):
                for cond in node.conditions:
                    cond.position = {}
                    cond.exit_flow_position = {}

    unpositioned = [n for n in nodes if not n.position]
    if not unpositioned:
        _assign_condition_positions(nodes, indexes)
        return

    if clean:
        node_map = indexes[1]
        G, exit_node_ids = _build_graph(nodes, indexes, flow_functions)
        layers = _assign_layers(G, start_node_id)
        layer_lists = _order_within_layers(G, layers)
        positions = _compute_positions(G, layer_lists, exit_node_ids, node_map)

        for node in nodes:
            if node.step_id in positions:
                node.position = positions[node.step_id]

        for node in nodes:
            if not _has_conditions(node):
                continue
            for cond in node.conditions:
                exit_id = f"{node.step_id}:exit:{cond.resource_id}"
                if exit_id in positions:
                    cond.exit_flow_position = positions[exit_id]
    else:
        _place_new_nodes(nodes, unpositioned, indexes, flow_functions)

    _assign_condition_positions(nodes, indexes)


def _place_new_nodes(
    all_nodes: list["BaseFlowStep"],
    new_nodes: list["BaseFlowStep"],
    indexes: NodeIndexes,
    flow_functions: list | None = None,
) -> None:
    """Place new nodes relative to their parents' existing positions."""
    G, _ = _build_graph(all_nodes, indexes, flow_functions)
    node_by_id = indexes[1]

    fallback_x = max((n.position["x"] for n in all_nodes if n.position), default=0.0)
    fallback_x += STEP_WIDTH + NODE_SEP
    fallback_y = min((n.position["y"] for n in all_nodes if n.position), default=0.0)

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
            node.position = {"x": round(fallback_x, 1), "y": round(fallback_y, 1)}
            fallback_x += STEP_WIDTH + NODE_SEP


def _estimate_label_width(text: str, has_icon: bool = False) -> float:
    """Estimate the rendered width of a condition label."""
    return len(text) * LABEL_CHAR_WIDTH + LABEL_PADDING + (LABEL_ICON_WIDTH if has_icon else 0)


def _assign_condition_positions(
    nodes: list["BaseFlowStep"],
    indexes: NodeIndexes,
) -> None:
    """Assign label positions for conditions, fanning out horizontally above each child."""
    node_by_name, node_by_id = indexes

    target_groups: dict[str, list[tuple["BaseFlowStep", "Condition"]]] = {}
    target_positions: dict[str, dict[str, float]] = {}
    target_widths: dict[str, float] = {}
    back_edges: list[tuple["BaseFlowStep", "Condition"]] = []

    for node in nodes:
        if not _has_conditions(node) or not node.position:
            continue

        for condition in node.conditions:
            if condition.position:
                continue

            if condition.child_step:
                child = _resolve_node(condition.child_step, node_by_name, node_by_id)
                if not child or not child.position:
                    continue
                if child.position["y"] <= node.position["y"]:
                    back_edges.append((node, condition))
                else:
                    key = child.step_id
                    target_groups.setdefault(key, []).append((node, condition))
                    target_positions[key] = child.position
                    target_widths[key] = _node_width(child)
            elif condition.exit_flow_position:
                key = f"{node.step_id}:exit:{condition.resource_id}"
                target_groups.setdefault(key, []).append((node, condition))
                target_positions[key] = condition.exit_flow_position
                target_widths[key] = EXIT_NODE_WIDTH

    for key, group in target_groups.items():
        target_pos = target_positions[key]
        target_w = target_widths[key]
        center_x = target_pos["x"] + target_w / 2
        label_y = target_pos["y"] - CONDITION_LABEL_OFFSET_Y

        widths = []
        for parent, cond in group:
            has_icon = parent.step_type != StepType.FUNCTION_STEP
            widths.append(_estimate_label_width(cond.name, has_icon))

        total_width = sum(widths) + LABEL_GAP * (len(widths) - 1)
        x = center_x - total_width / 2

        for i, (_, cond) in enumerate(group):
            cond.position = {"x": round(x, 1), "y": round(label_y, 1)}
            x += widths[i] + LABEL_GAP

    for node, condition in back_edges:
        condition.ingress = "bottom"
        condition.position = {
            "x": node.position["x"] + _node_width(node) + BACK_EDGE_X_OFFSET,
            "y": node.position["y"],
        }


def _pos(xy: dict[str, float]) -> StepPosition:
    """Build a StepPosition proto from an {x, y} dict."""
    return StepPosition(x=xy.get("x", 0.0), y=xy.get("y", 0.0))


def _step_position_detail(node: "BaseFlowStep") -> FlowPositionDetail:
    """Build a FlowPositionDetail for a step node."""
    pos = _pos(node.position)
    if node.step_type == StepType.FUNCTION_STEP:
        return FlowPositionDetail(
            function_step=FunctionStepPositionDetail(step_id=node.step_id, new_position=pos)
        )
    if node.step_type == StepType.ADVANCED_STEP:
        return FlowPositionDetail(
            flow_step=FlowStepPositionDetails(step_id=node.step_id, new_position=pos)
        )
    return FlowPositionDetail(
        no_code_step=NoCodeStepPositionDetail(step_id=node.step_id, new_position=pos)
    )


def _condition_position_details(
    node: "BaseFlowStep",
    condition: "Condition",
) -> list[FlowPositionDetail]:
    """Build FlowPositionDetail protos for a condition.

    Returns one detail for the label, plus a second for the exit node if applicable.
    """
    if not condition.position:
        return []
    pos = _pos(condition.position)
    is_no_code = condition.parent_is_no_code_step
    details: list[FlowPositionDetail] = []

    if is_no_code:
        details.append(
            FlowPositionDetail(
                no_code_step_condition=NoCodeStepConditionPositionDetail(
                    step_id=node.step_id, condition_id=condition.resource_id, new_position=pos
                )
            )
        )
    else:
        details.append(
            FlowPositionDetail(
                function_step_condition=FunctionStepConditionPositionDetail(
                    step_id=node.step_id, condition_id=condition.resource_id, new_position=pos
                )
            )
        )

    if condition.condition_type == ConditionType.EXIT_FLOW and condition.exit_flow_position:
        exit_pos = _pos(condition.exit_flow_position)
        if is_no_code:
            details.append(
                FlowPositionDetail(
                    no_code_step_condition_exit_flow=NoCodeStepExitFlowPositionDetail(
                        step_id=node.step_id,
                        condition_id=condition.resource_id,
                        new_position=exit_pos,
                    )
                )
            )
        else:
            details.append(
                FlowPositionDetail(
                    function_step_condition_exit_flow=FunctionStepExitFlowPositionDetail(
                        step_id=node.step_id,
                        condition_id=condition.resource_id,
                        new_position=exit_pos,
                    )
                )
            )

    return details


def build_move_commands(flow_id: str, nodes: list["BaseFlowStep"]) -> MoveFlowComponents:
    """Build a MoveFlowComponents proto for all positioned components in a flow."""
    details: list[FlowPositionDetail] = []

    for node in nodes:
        if node.position:
            details.append(_step_position_detail(node))

        if not _has_conditions(node):
            continue
        for cond in node.conditions:
            details.extend(_condition_position_details(node, cond))

    return MoveFlowComponents(flow_id=flow_id, position_details=details)


def clean_flow_positions(
    flow_id: str,
    start_step_id: str,
    flow_steps: list["BaseFlowStep"],
    flow_functions: list | None = None,
) -> MoveFlowComponents | None:
    """Re-layout a flow from scratch and return a MoveFlowComponents proto."""
    if not flow_steps:
        return None
    assign_flow_positions(flow_steps, start_step_id, flow_functions=flow_functions, clean=True)
    move_proto = build_move_commands(flow_id, flow_steps)
    return move_proto if move_proto.position_details else None
