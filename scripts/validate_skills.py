#!/usr/bin/env python3
"""Validate skills/*/SKILL.md frontmatter and version lockstep with the CLI.

Checks that every SKILL.md has well-formed YAML frontmatter containing the
required fields (name, description, metadata.author, metadata.license,
metadata.version, metadata.requires.bins) and that each skill's
metadata.version matches project.version in pyproject.toml.

Usage:
    python scripts/validate_skills.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"

REQUIRED_FIELDS = [
    "name",
    "description",
    "metadata.author",
    "metadata.license",
    "metadata.version",
    "metadata.requires.bins",
]


def _read_cli_version() -> str:
    """Read project.version from pyproject.toml."""
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        return tomllib.load(f)["project"]["version"]


def _extract_frontmatter(text: str) -> str | None:
    """Return the YAML between the leading '---' delimiters, or None."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:i])
    return None


def _lookup(data: dict[str, Any], dotted_path: str) -> Any:
    """Resolve a dotted path (e.g. 'metadata.requires.bins') in nested dicts."""
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _validate_skill(skill_md: Path, cli_version: str) -> list[str]:
    """Return a list of validation errors for one SKILL.md (empty if valid)."""
    frontmatter = _extract_frontmatter(skill_md.read_text(encoding="utf-8"))
    if frontmatter is None:
        return ["missing YAML frontmatter (expected a leading '---' delimited block)"]

    try:
        data = YAML(typ="safe").load(frontmatter)
    except YAMLError as exc:
        return [f"invalid YAML frontmatter: {exc}"]
    if not isinstance(data, dict):
        return ["frontmatter is not a YAML mapping"]

    errors = []
    for field in REQUIRED_FIELDS:
        value = _lookup(data, field)
        if value is None or value == "" or value == []:
            errors.append(f"missing or empty required field: {field}")

    version = _lookup(data, "metadata.version")
    if version is not None and str(version) != cli_version:
        errors.append(
            f"metadata.version is {version} but pyproject.toml project.version"
            f" is {cli_version} — skill versions must stay in lockstep with the CLI"
        )
    return errors


def main() -> None:
    """Validate all skills and exit non-zero if any check fails."""
    cli_version = _read_cli_version()
    skill_files = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    if not skill_files:
        print(f"Error: no SKILL.md files found under {SKILLS_DIR}", file=sys.stderr)
        sys.exit(1)

    failed = False
    for skill_md in skill_files:
        rel = skill_md.relative_to(REPO_ROOT)
        errors = _validate_skill(skill_md, cli_version)
        if errors:
            failed = True
            for error in errors:
                print(f"  FAIL {rel}: {error}")
        else:
            print(f"  OK   {rel}")

    if failed:
        sys.exit(1)
    print(f"\nValidated {len(skill_files)} skills against CLI version {cli_version}")


if __name__ == "__main__":
    main()
