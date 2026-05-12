#!/usr/bin/env python3
"""Visualize a flow's layout as an HTML file with positioned boxes.

Usage:
    python scripts/visualize_flow.py <flow_dir> [output.html]

Example:
    python scripts/visualize_flow.py ~/agent_studio/ruari-ws/poly-hotel/flows/make_a_booking
    open flow_layout.html
"""

import os
import sys
import html
import re
import tempfile
import webbrowser

import ruamel.yaml as ryaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from poly.resources.flows import (
    Condition,
    ConditionType,
    FlowStep,
    FunctionStep,
    StepType,
)
from poly.resources.resource_utils import assign_flow_positions

yaml = ryaml.YAML()


def load_flow(flow_dir: str):
    config_path = os.path.join(flow_dir, "flow_config.yaml")
    with open(config_path) as f:
        config = yaml.load(f)

    flow_id = "flow-viz"
    flow_name = config["name"]
    start_step = config["start_step"]

    nodes = []
    steps_dir = os.path.join(flow_dir, "steps")

    # Load flow functions (not nodes — just used to resolve routing edges)
    flow_func_targets: dict[str, list[str]] = {}
    for dir_name in ("functions",):
        fdir = os.path.join(flow_dir, dir_name)
        if not os.path.isdir(fdir):
            continue
        for fname in sorted(os.listdir(fdir)):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(fdir, fname)) as f:
                code = f.read()
            func_name = fname.removesuffix(".py")
            targets = [
                m.group(1) or m.group(2)
                for m in re.finditer(
                    r'flow\.goto_step\(\s*"([^"]+)"'
                    r"|flow\.goto_step\(\s*'([^']+)'",
                    code,
                )
            ]
            if targets:
                flow_func_targets[func_name] = targets

    # Load steps
    if os.path.isdir(steps_dir):
        for fname in sorted(os.listdir(steps_dir)):
            if not fname.endswith(".yaml"):
                continue
            with open(os.path.join(steps_dir, fname)) as f:
                data = yaml.load(f)

            step_id = f"step-{fname.removesuffix('.yaml')}"
            name = data["name"]
            prompt = data.get("prompt", "")
            conditions = []

            for i, c in enumerate(data.get("conditions") or []):
                ctype = c.get("condition_type", "step_condition")
                if ctype == "exit_flow_condition":
                    ct = ConditionType.EXIT_FLOW
                else:
                    ct = ConditionType.STEP
                conditions.append(
                    Condition(
                        resource_id=f"cond-{step_id}-{i}",
                        name=c["name"],
                        condition_type=ct,
                        step_id=step_id,
                        flow_id=flow_id,
                        child_step=c.get("child_step", ""),
                        description=c.get("description", ""),
                        required_entities=c.get("required_entities", []),
                    )
                )

            # Resolve {{ft:func}} / {{fn:func}} in prompts to direct step conditions
            for match in re.finditer(r"\{\{ft:([^}]+)\}\}", prompt):
                func_name = match.group(1)
                for target_step in flow_func_targets.get(func_name, []):
                    conditions.append(
                        Condition(
                            resource_id=f"cond-{step_id}-ft-{func_name}",
                            name=func_name,
                            condition_type=ConditionType.STEP,
                            step_id=step_id,
                            flow_id=flow_id,
                            child_step=target_step,
                        )
                    )

            nodes.append(
                FlowStep(
                    resource_id=step_id,
                    step_id=step_id,
                    name=name,
                    flow_id=flow_id,
                    flow_name=flow_name,
                    step_type=StepType.DEFAULT_STEP,
                    conditions=conditions,
                    prompt=prompt,
                )
            )

    # Load function steps (these ARE nodes in the graph, unlike flow functions)
    func_steps_dir = os.path.join(flow_dir, "function_steps")
    if os.path.isdir(func_steps_dir):
        for fname in sorted(os.listdir(func_steps_dir)):
            if not fname.endswith(".py"):
                continue
            with open(os.path.join(func_steps_dir, fname)) as f:
                code = f.read()
            name = fname.removesuffix(".py")
            step_id = f"step-{name}"
            nodes.append(
                FunctionStep(
                    resource_id=step_id,
                    step_id=step_id,
                    name=name,
                    flow_id=flow_id,
                    flow_name=flow_name,
                    code=code,
                )
            )

    # Find start node
    start_id = None
    for n in nodes:
        if n.name == start_step:
            start_id = n.step_id
            break
    if not start_id:
        print(f"Start step '{start_step}' not found in nodes: {[n.name for n in nodes]}")
        sys.exit(1)

    return nodes, start_id, flow_name


def generate_html(nodes, flow_name):
    STEP_W, STEP_H = 350, 145
    FUNC_W, FUNC_H = 250, 50
    EXIT_W, EXIT_H = 100, 40

    node_lookup = {n.name: n for n in nodes}
    node_lookup.update({n.step_id: n for n in nodes})

    def _dims(n):
        if isinstance(n, FunctionStep):
            return FUNC_W, FUNC_H
        return STEP_W, STEP_H

    # Collect all positioned items
    items = []
    edges = []

    for node in nodes:
        if not node.position:
            continue
        is_func = isinstance(node, FunctionStep)
        prompt = getattr(node, "prompt", "") or ""
        items.append(
            {
                "id": node.step_id,
                "name": node.name,
                "prompt": prompt,
                "x": node.position["x"],
                "y": node.position["y"],
                "w": FUNC_W if is_func else STEP_W,
                "h": FUNC_H if is_func else STEP_H,
                "type": "function_step" if is_func else "step",
            }
        )

        if hasattr(node, "conditions") and node.conditions:
            for cond in node.conditions:
                if cond.child_step:
                    target = node_lookup.get(cond.child_step)
                    if target and target.position:
                        edges.append(
                            {
                                "from_id": node.step_id,
                                "to_id": target.step_id,
                                "label": cond.name,
                                "back_edge": target.position["y"] <= node.position["y"],
                            }
                        )

                if cond.exit_flow_position:
                    exit_id = f"{node.step_id}:exit:{cond.resource_id}"
                    items.append(
                        {
                            "id": exit_id,
                            "name": f"Exit: {cond.name}",
                            "prompt": "",
                            "x": cond.exit_flow_position["x"],
                            "y": cond.exit_flow_position["y"],
                            "w": EXIT_W,
                            "h": EXIT_H,
                            "type": "exit",
                        }
                    )
                    edges.append(
                        {
                            "from_id": node.step_id,
                            "to_id": exit_id,
                            "label": cond.name,
                            "back_edge": False,
                        }
                    )

        if isinstance(node, FunctionStep) and node.position:
            code = getattr(node, "code", "") or ""
            for match in re.finditer(r'flow\.goto_step\(\s*["\']([^"\']+)["\']', code):
                target_name = match.group(1)
                target = node_lookup.get(target_name)
                if target and target.position:
                    edges.append(
                        {
                            "from_id": node.step_id,
                            "to_id": target.step_id,
                            "label": f"goto: {target_name}",
                            "back_edge": target.position["y"] <= node.position["y"],
                        }
                    )

    # Deduplicate edges
    seen_edges = set()
    unique_edges = []
    for e in edges:
        key = (e["from_id"], e["to_id"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)
    edges = unique_edges

    # Normalize coordinates so nothing is negative
    min_x = min(i["x"] for i in items) if items else 0
    min_y = min(i["y"] for i in items) if items else 0
    pad = 60
    offset_x = -min_x + pad
    offset_y = -min_y + pad

    for i in items:
        i["x"] += offset_x
        i["y"] += offset_y

    boxes_html = []
    for item in items:
        if item["type"] == "exit":
            cls = "exit-node"
        elif item["type"] == "function_step":
            cls = "func-node"
        else:
            cls = "step-node"
        prompt_html = ""
        if item.get("prompt"):
            prompt_html = f'<div class="prompt">{html.escape(item["prompt"])}</div>'
        boxes_html.append(
            f'<div class="node {cls}" data-id="{html.escape(item["id"])}" '
            f'style="left:{item["x"]:.0f}px;top:{item["y"]:.0f}px;'
            f'width:{item["w"]}px;min-height:{item["h"]}px;">'
            f'<div class="node-inner"><div class="node-title">{html.escape(item["name"])}</div>'
            f"{prompt_html}</div></div>"
        )

    import json as _json

    edges_json = _json.dumps(
        [
            {
                "from": e["from_id"],
                "to": e["to_id"],
                "label": e["label"],
                "back": e["back_edge"],
            }
            for e in edges
        ]
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>{html.escape(flow_name)} — Layout Preview</title>
<style>
  body {{ margin:0; background:#f5f5f5; font-family: -apple-system, sans-serif; }}
  h1 {{ padding:16px 24px; margin:0; font-size:18px; background:#fff; border-bottom:1px solid #ddd; }}
  .canvas {{ position:relative; margin:24px; }}
  .node {{ position:absolute; border-radius:8px; padding:12px; box-sizing:border-box;
           font-size:13px; font-weight:500; box-shadow:0 2px 8px rgba(0,0,0,0.1); z-index:1;
           overflow:hidden; }}
  .node-inner {{ width:100%; }}
  .node-title {{ font-weight:600; font-size:14px; margin-bottom:6px; }}
  .prompt {{ font-size:11px; font-weight:400; color:#555; white-space:pre-wrap;
             line-height:1.4; max-height:400px; overflow-y:auto; }}
  .step-node {{ background:#fff; border:2px solid #6366f1; color:#333; }}
  .func-node {{ background:#fef3c7; border:2px solid #d97706; color:#92400e; }}
  .exit-node {{ background:#fce7f3; border:2px solid #db2777; color:#9d174d; font-size:11px; }}
  .edge-label {{ font-size:11px; fill:#666; text-anchor:middle; dominant-baseline:middle;
                 background:#f5f5f5; }}
  svg {{ position:absolute; top:0; left:0; pointer-events:none; z-index:2; }}
</style>
</head><body>
<h1>{html.escape(flow_name)}</h1>
<div class="canvas" id="canvas">
  {"".join(boxes_html)}
</div>
<script>
const edges = {edges_json};
const canvas = document.getElementById('canvas');
const nodeEls = Object.fromEntries(
  [...canvas.querySelectorAll('.node')].map(el => [el.dataset.id, el])
);

// Measure actual rendered sizes
requestAnimationFrame(() => {{
  let maxR = 0, maxB = 0;
  for (const el of Object.values(nodeEls)) {{
    maxR = Math.max(maxR, el.offsetLeft + el.offsetWidth);
    maxB = Math.max(maxB, el.offsetTop + el.offsetHeight);
  }}
  canvas.style.width = (maxR + 60) + 'px';
  canvas.style.height = (maxB + 60) + 'px';

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', maxR + 60);
  svg.setAttribute('height', maxB + 60);
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  defs.innerHTML = '<marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" ' +
    'markerWidth="8" markerHeight="8" orient="auto-start-reverse">' +
    '<path d="M 0 0 L 10 5 L 0 10 z" fill="#555"/></marker>';
  svg.appendChild(defs);

  for (const e of edges) {{
    const fromEl = nodeEls[e.from];
    const toEl = nodeEls[e.to];
    if (!fromEl || !toEl) continue;

    const fx = fromEl.offsetLeft + fromEl.offsetWidth / 2;
    const fy = fromEl.offsetTop + fromEl.offsetHeight;
    const tx = toEl.offsetLeft + toEl.offsetWidth / 2;
    const ty = toEl.offsetTop;

    const color = e.back ? '#999' : '#555';
    const dash = e.back ? '8,4' : 'none';
    const midY = (fy + ty) / 2;

    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${{fx}},${{fy}} C${{fx}},${{midY}} ${{tx}},${{midY}} ${{tx}},${{ty}}`);
    path.setAttribute('stroke', color);
    path.setAttribute('stroke-width', '2');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke-dasharray', dash);
    path.setAttribute('marker-end', 'url(#arrow)');
    svg.appendChild(path);

    const lx = (fx + tx) / 2;
    const ly = (fy + ty) / 2;
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', lx);
    text.setAttribute('y', ly);
    text.setAttribute('class', 'edge-label');
    text.textContent = e.label;
    svg.appendChild(text);
  }}

  canvas.insertBefore(svg, canvas.firstChild);
}});
</script>
</body></html>"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    flow_dir = os.path.expanduser(sys.argv[1])

    nodes, start_id, flow_name = load_flow(flow_dir)
    assign_flow_positions(nodes, start_id)

    print(f"Flow: {flow_name}")
    print(f"Nodes: {len(nodes)}")
    for n in nodes:
        tag = "(func)" if isinstance(n, FunctionStep) else ""
        print(f"  [{n.name}] {tag} x={n.position.get('x', '?')}, y={n.position.get('y', '?')}")
        if hasattr(n, "conditions"):
            for c in n.conditions:
                if c.exit_flow_position:
                    print(
                        f"    exit:{c.name} x={c.exit_flow_position['x']}, y={c.exit_flow_position['y']}"
                    )

    page = generate_html(nodes, flow_name)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as f:
        f.write(page)
        output = f.name
    print(f"\nWritten to {output}")
    webbrowser.open(f"file://{output}")


if __name__ == "__main__":
    main()
