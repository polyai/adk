#!/usr/bin/env python3
"""Benchmark pull, status and push on a large multi-resource project, entirely offline.

Builds a synthetic projection shaped like a large production project (many variants, each with a
few typed attributes, plus thousands of pronunciation rules) and times each sync phase against a
temporary project directory using the real ADK code paths. No network access or API key is needed.

With --digest-out, a sha256 of every project file is recorded after each phase. Diffing the digest
files from two runs shows whether a change altered anything written to disk.

Usage:
    uv run python scripts/bench_large_project.py
    uv run python scripts/bench_large_project.py --digest-out before.json
    uv run python scripts/bench_large_project.py --variants 200 --profile push
"""

from __future__ import annotations

import argparse
import copy
import cProfile
import hashlib
import json
import os
import pstats
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from ruamel.yaml.main import CParser

from poly.project import AgentStudioProject

PHASES = ("init", "force-pull", "pull", "status", "push")
EXCLUDED_FROM_DIGEST = {os.path.join("_gen", ".agent_studio_config")}
ENUM_VALUES = ["basic", "standard", "premium"]
VARIANT_ATTRIBUTES_FILE = os.path.join("config", "variant_attributes.yaml")
PRONUNCIATIONS_FILE = os.path.join("voice", "response_control", "pronunciations.yaml")


def _attribute_value(kind: int, variant: int, attribute: int) -> Any:
    """Return a deterministic value of the given proto attribute kind."""
    if kind == 1:
        return (variant * 7 + attribute) % 500
    if kind == 2:
        return (variant + attribute) % 2 == 0
    if kind == 3:
        return ENUM_VALUES[(variant + attribute) % len(ENUM_VALUES)]
    return f"Site {variant:05d} attribute {attribute:03d}: representative configuration text"


def build_projection(n_variants: int, n_attributes: int, n_pronunciations: int) -> dict:
    """Build a projection with variants, typed variant attributes and pronunciations."""
    variant_ids = [f"VARIANT-{i:05d}" for i in range(n_variants)]
    attributes = {}
    for j in range(n_attributes):
        kind = j % 7 if j % 7 < 4 else 0
        attribute_type: dict[str, Any] = {"kind": kind}
        if kind == 3:
            attribute_type["config"] = {"$case": "enumConfig", "value": {"values": ENUM_VALUES}}
        attributes[f"ATTR-{j:03d}"] = {
            "id": f"ATTR-{j:03d}",
            "name": f"attribute_{j:03d}",
            "archived": False,
            "type": attribute_type,
        }

    variant_values = {}
    for i, variant_id in enumerate(variant_ids):
        values, typed_values = {}, {}
        for j, (attribute_id, attribute) in enumerate(attributes.items()):
            kind = attribute["type"]["kind"]
            target = values if kind == 0 else typed_values
            target[attribute_id] = _attribute_value(kind, i, j)
        variant_values[variant_id] = {
            "id": variant_id,
            "values": values,
            "typedValues": typed_values,
        }

    pronunciations = {
        f"PRON-{k:05d}": {
            "id": f"PRON-{k:05d}",
            "regex": rf"\bterm{k:05d}\b",
            "replacement": f"replacement for term {k:05d}",
            "caseSensitive": k % 7 == 0,
            "languageCode": "en-US",
            "description": f"Rule {k:05d}" if k % 3 == 0 else "",
        }
        for k in range(n_pronunciations)
    }

    return {
        "variantManagement": {
            "variants": {
                "entities": {
                    variant_id: {"id": variant_id, "name": f"site_{i:05d}", "isDefault": i == 0}
                    for i, variant_id in enumerate(variant_ids)
                }
            },
            "attributes": {"entities": attributes},
            "variantAttributeValues": {"entities": variant_values},
        },
        "pronunciations": {"pronunciations": {"entities": pronunciations}},
    }


def with_remote_edit(projection: dict) -> dict:
    """Return a copy of the projection with one string attribute value changed remotely."""
    edited = copy.deepcopy(projection)
    entities = edited["variantManagement"]["variantAttributeValues"]["entities"]
    variant_id = sorted(entities)[len(entities) // 2]
    entities[variant_id]["values"]["ATTR-000"] = "Edited remotely"
    return edited


def apply_local_edit(base_path: str) -> None:
    """Change one attribute value of the first variant directly in the working tree."""
    path = os.path.join(base_path, VARIANT_ATTRIBUTES_FILE)
    with open(path, encoding="utf-8") as f:
        content = f.read()
    old = _attribute_value(0, 0, 0)
    if old not in content:
        raise RuntimeError(f"Expected value {old!r} not found in {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.replace(old, "Edited locally", 1))


def digest_tree(base_path: str) -> dict[str, str]:
    """Return {relative path: sha256} for every file under base_path."""
    digests = {}
    for root, _, files in os.walk(base_path):
        for name in files:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, base_path)
            if rel in EXCLUDED_FROM_DIGEST:
                continue
            with open(full, "rb") as f:
                digests[rel] = hashlib.sha256(f.read()).hexdigest()
    return dict(sorted(digests.items()))


def run_phase(name: str, fn: Callable[[], Any], profile: str | None) -> float:
    """Run one phase, optionally under cProfile, and return its wall time in seconds."""
    profiler = cProfile.Profile() if profile == name else None
    start = time.perf_counter()
    if profiler:
        profiler.enable()
    fn()
    if profiler:
        profiler.disable()
    elapsed = time.perf_counter() - start
    if profiler:
        stats = pstats.Stats(profiler, stream=sys.stderr)
        stats.sort_stats("cumulative").print_stats(25)
    return elapsed


def run(args: argparse.Namespace, base_path: str) -> tuple[dict[str, float], dict[str, dict], str]:
    """Run every phase under base_path and return timings, digests and the project root."""
    projection = build_projection(args.variants, args.attributes, args.pronunciations)
    edited = with_remote_edit(projection)
    timings: dict[str, float] = {}
    digests: dict[str, dict] = {}
    state: dict[str, AgentStudioProject] = {}

    def init() -> None:
        state["project"], _ = AgentStudioProject.init_project(
            base_path, "us-1", "bench-account", "bench-project", projection_json=projection
        )

    def status() -> None:
        apply_local_edit(state["project"].root_path)
        state["project"].project_status()

    phases: dict[str, Callable[[], Any]] = {
        "init": init,
        "force-pull": lambda: state["project"].pull_project(force=True, projection_json=projection),
        "pull": lambda: state["project"].pull_project(projection_json=edited),
        "status": status,
        "push": lambda: state["project"].push_project(
            dry_run=True, projection_json=edited, parent_projection_json={}
        ),
    }
    for name in PHASES:
        timings[name] = run_phase(name, phases[name], args.profile)
        digests[name] = digest_tree(state["project"].root_path)
    return timings, digests, state["project"].root_path


def main() -> None:
    """Parse arguments, run the benchmark and print a timing table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--variants", type=int, default=1238)
    parser.add_argument("--attributes", type=int, default=21)
    parser.add_argument("--pronunciations", type=int, default=3317)
    parser.add_argument("--digest-out", type=Path, help="write per-phase file digests as JSON")
    parser.add_argument("--profile", choices=PHASES, help="print a cProfile report for a phase")
    parser.add_argument("--workdir", type=Path, help="run in this directory and keep it")
    args = parser.parse_args()

    if args.workdir:
        args.workdir.mkdir(parents=True, exist_ok=True)
        timings, digests, root = run(args, str(args.workdir))
    else:
        tmp = tempfile.TemporaryDirectory(prefix="adk-bench-")
        timings, digests, root = run(args, tmp.name)

    sizes = {
        rel: os.path.getsize(os.path.join(root, rel)) / 1e6
        for rel in (VARIANT_ATTRIBUTES_FILE, PRONUNCIATIONS_FILE)
    }
    print(
        f"{args.variants} variants x {args.attributes} attributes, "
        f"{args.pronunciations} pronunciations "
        f"({', '.join(f'{rel} {mb:.2f} MB' for rel, mb in sizes.items())})"
    )
    print(f"libyaml parser: {'yes' if CParser is not None else 'no'}")
    for name in PHASES:
        print(f"  {name:<11} {timings[name]:7.2f} s")
    print(f"  {'total':<11} {sum(timings.values()):7.2f} s")

    if args.digest_out:
        args.digest_out.write_text(json.dumps(digests, indent=2) + "\n", encoding="utf-8")
        print(f"digests written to {args.digest_out}")


if __name__ == "__main__":
    main()
