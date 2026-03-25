#!/usr/bin/env python3
"""Generate a coverage comparison comment for a GitHub PR.

Usage:
    coverage_comment.py <base.json> <pr.json> [base-ref-name]
"""

import json
import sys
from pathlib import Path


def load_coverage(path: str) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def get_file_coverage(data: dict) -> dict[str, float]:
    """Return {display_name: pct} for non-test files that have at least one statement."""
    results = {}
    for filepath, info in data.get("files", {}).items():
        summary = info["summary"]
        if summary["num_statements"] == 0:
            continue
        display = filepath.removeprefix("src/")
        if display.startswith("poly/tests/"):
            continue
        results[display] = summary["percent_covered"]
    return results


def format_delta(delta: float) -> str:
    if delta > 0:
        return f"+{delta:.1f}% ✅"
    elif delta < 0:
        return f"{delta:.1f}% ⚠️"
    return "±0.0% ➡️"


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: coverage_comment.py <base.json> <pr.json> [base-ref]", file=sys.stderr)
        sys.exit(1)

    base_data = load_coverage(sys.argv[1])
    pr_data = load_coverage(sys.argv[2])
    base_ref = sys.argv[3] if len(sys.argv) > 3 else "base"

    if pr_data is None:
        print("<!-- coverage-report -->\n> Coverage data not available.")
        return

    pr_total = pr_data["totals"]["percent_covered"]

    lines: list[str] = ["<!-- coverage-report -->", "## Coverage Report", ""]

    if base_data is not None:
        base_total = base_data["totals"]["percent_covered"]
        delta = pr_total - base_total
        lines += [
            f"| Base (`{base_ref}`) | PR | Change |",
            "|---|---|---|",
            f"| {base_total:.1f}% | {pr_total:.1f}% | {format_delta(delta)} |",
        ]
    else:
        lines += ["| PR Coverage |", "|---|", f"| {pr_total:.1f}% |"]

    pr_files = get_file_coverage(pr_data)
    base_files = get_file_coverage(base_data) if base_data is not None else {}

    changed = [
        (name, pct, pct - base_files[name])
        for name, pct in pr_files.items()
        if name in base_files and base_files[name] != pct
    ]
    changed_sorted = sorted(changed, key=lambda x: x[1])

    if changed_sorted:
        lines += [
            "",
            "### Changed file coverage",
            "| File | Coverage | Change |",
            "|---|---|---|",
            *[
                f"| `{name}` | {pct:.1f}% | {format_delta(delta)} |"
                for name, pct, delta in changed_sorted
            ],
        ]

    print("\n".join(lines))


if __name__ == "__main__":
    main()
