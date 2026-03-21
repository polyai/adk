#!/usr/bin/env python3
"""Agentic docs updater — called by the auto-update-docs GitHub Actions workflow.

Reads the diff of what just merged to main, reads all current documentation,
asks Claude which pages need updating and what the updates should be, then
writes changes to disk. The workflow then opens a PR if any files changed.

Requires:
    ANTHROPIC_API_KEY environment variable
    anthropic Python package (pip install anthropic)
"""

import subprocess
import sys
from pathlib import Path

import anthropic

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = REPO_ROOT / "docs" / "docs"
SUMMARY_FILE = Path(__file__).resolve().parent / ".pr_summary"

# Swap to claude-opus-4-6 for higher-stakes repos with complex docs.
MODEL = "claude-sonnet-4-6"

# Soft limits to stay well within context. Diffs larger than this are truncated
# with a notice so Claude knows it's seeing a partial picture.
DIFF_CHAR_LIMIT = 30_000
DOCS_CHAR_LIMIT = 60_000


def run(cmd: list[str], cwd: Path = REPO_ROOT) -> str:
    """Run a shell command and return stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.stdout


def get_diff() -> str:
    """Return the unified diff of src/ and pyproject.toml from the last merge."""
    diff = run(["git", "diff", "HEAD~1", "HEAD", "--", "src/", "pyproject.toml"])
    if len(diff) > DIFF_CHAR_LIMIT:
        return diff[:DIFF_CHAR_LIMIT] + "\n\n[diff truncated — showing first 30 000 chars]"
    return diff


def get_commit_info() -> str:
    """Return the commit message and short hash of the merge commit."""
    return run(["git", "log", "-1", "--pretty=format:hash: %h%nauthor: %an%n%ncommit message:%n%B"])


def read_docs() -> dict[str, str]:
    """Read all markdown files from the docs directory."""
    docs: dict[str, str] = {}
    for path in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(path.relative_to(REPO_ROOT))
        docs[rel] = path.read_text()
    return docs


def build_docs_block(docs: dict[str, str]) -> str:
    """Render all docs as a single block, truncated if needed."""
    lines: list[str] = []
    total = 0
    for path, content in docs.items():
        entry = f"### {path}\n{content}\n---\n"
        if total + len(entry) > DOCS_CHAR_LIMIT:
            lines.append("[remaining docs truncated to fit context]")
            break
        lines.append(entry)
        total += len(entry)
    return "\n".join(lines)


def main() -> None:
    diff = get_diff()
    if not diff.strip():
        print("No relevant code changes in src/ or pyproject.toml — skipping.")
        sys.exit(0)

    commit_info = get_commit_info()
    docs = read_docs()
    docs_block = build_docs_block(docs)

    client = anthropic.Anthropic()

    tools = [
        {
            "name": "update_doc_file",
            "description": (
                "Write updated content to a documentation file. "
                "Call once per file that needs changing. "
                "Provide the complete new file content, not just the diff."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": (
                            "Path to the file relative to repo root. "
                            "Must be an existing file from the docs listing, "
                            "e.g. docs/docs/reference/cli.md"
                        ),
                    },
                    "new_content": {
                        "type": "string",
                        "description": "Complete replacement content for the file.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "One sentence explaining what changed and why.",
                    },
                },
                "required": ["file_path", "new_content", "reason"],
            },
        },
        {
            "name": "no_updates_needed",
            "description": "Signal that no documentation changes are required for this merge.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the docs are already accurate.",
                    }
                },
                "required": ["reason"],
            },
        },
    ]

    prompt = f"""You are a technical writer maintaining the PolyAI ADK documentation.

A pull request was just merged to main. Review what changed in the code and update \
the documentation if needed.

## Merged commit
{commit_info}

## Code diff (src/ and pyproject.toml)
```diff
{diff}
```

## Current documentation
{docs_block}

## Instructions

1. Read the diff carefully and identify any user-facing changes:
   - New or removed CLI commands or flags
   - Changed command behaviour or output
   - New or changed resource types, YAML fields, or schemas
   - Version bumps in pyproject.toml
   - New concepts or workflows

2. For each docs page that is now inaccurate or incomplete, call `update_doc_file`
   with the full corrected content.

3. Make minimal, precise edits. Do not rewrite sections that are still accurate.
   Preserve the existing writing style, formatting (MkDocs Material admonitions,
   code fences, grid cards), and tone.

4. Do NOT update docs for:
   - Internal refactors with no user-visible effect
   - Test-only changes
   - CI or tooling changes
   - Changes already clearly reflected in the docs

5. If nothing needs changing, call `no_updates_needed`.
"""

    print(f"Sending diff ({len(diff)} chars) and {len(docs)} doc files to Claude...")

    response = client.messages.create(
        model=MODEL,
        max_tokens=8096,
        tools=tools,
        messages=[{"role": "user", "content": prompt}],
    )

    updated: list[str] = []
    reasons: list[str] = []

    for block in response.content:
        if block.type != "tool_use":
            continue
        if block.name == "no_updates_needed":
            print(f"No updates needed: {block.input['reason']}")
            sys.exit(0)
        if block.name == "update_doc_file":
            rel_path = block.input["file_path"]
            abs_path = REPO_ROOT / rel_path
            if not abs_path.is_relative_to(DOCS_DIR):
                print(f"Skipping {rel_path} — outside docs directory.")
                continue
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text(block.input["new_content"])
            updated.append(rel_path)
            reasons.append(f"- **{rel_path}**: {block.input['reason']}")
            print(f"Updated: {rel_path}")

    if not updated:
        print("Claude returned no file updates.")
        sys.exit(0)

    # Write PR summary for the workflow to use as the PR body.
    merge_hash = run(["git", "rev-parse", "--short", "HEAD"]).strip()
    summary = (
        f"Auto-generated docs update triggered by merge {merge_hash}.\n\n"
        "## Changes\n\n"
        + "\n".join(reasons)
        + "\n\n---\n_Updated by the auto-update-docs workflow using Claude._"
    )
    SUMMARY_FILE.write_text(summary)
    print(f"\nUpdated {len(updated)} file(s). PR summary written to {SUMMARY_FILE}.")


if __name__ == "__main__":
    main()
