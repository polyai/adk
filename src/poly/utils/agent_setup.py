"""Install coding-agent memory and skill files into a project.

Backs ``poly docs --claude-code``. The assets themselves are shipped as package
data under ``poly/skills`` and copied verbatim into the target project, so
upgrading the CLI and re-running the command refreshes them.

The work is split into a plan and an apply step: ``plan_claude_code_setup``
decides what each file needs (create, overwrite, append or nothing) without
touching disk, and ``apply_claude_code_setup`` writes it. That lets the CLI show
the user exactly what will change and ask before clobbering anything.

Copyright PolyAI Limited
"""

import os
from dataclasses import dataclass, field

SKILL_NAME = "poly-adk"
"""Directory name of the skill inside ``.claude/skills``."""

MEMORY_FILE = "CLAUDE.md"
"""Project memory file Claude Code loads on every session."""

MEMORY_BEGIN = "<!-- BEGIN poly-adk -->"
MEMORY_END = "<!-- END poly-adk -->"

_POLY_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS_PACKAGE_DIR = os.path.join(_POLY_PACKAGE_DIR, "skills")
"""Absolute path to the ``poly/skills`` package data directory."""

# What a planned write does to the file at its path.
CREATE = "create"
OVERWRITE = "overwrite"
APPEND = "append"
UNCHANGED = "unchanged"


@dataclass
class PlannedWrite:
    """A single file the setup wants to write."""

    path: str
    """Absolute path of the file to write."""

    content: str
    """Full content to write to ``path``."""

    action: str
    """One of ``create``, ``overwrite``, ``append`` or ``unchanged``."""

    @property
    def destructive(self) -> bool:
        """Whether applying this write would discard existing content."""
        return self.action == OVERWRITE


@dataclass
class ClaudeCodePlan:
    """Everything ``poly docs --claude-code`` intends to change."""

    target_dir: str
    """Project directory the assets are installed into."""

    writes: list[PlannedWrite] = field(default_factory=list)
    """Planned writes, in the order they should be applied."""

    removals: list[str] = field(default_factory=list)
    """Installed skill files no longer shipped by this CLI version."""

    @property
    def pending(self) -> list[PlannedWrite]:
        """Writes that would actually change something on disk."""
        return [write for write in self.writes if write.action != UNCHANGED]

    @property
    def destructive(self) -> list[PlannedWrite]:
        """Writes that would discard existing content, needing confirmation."""
        return [write for write in self.writes if write.destructive]

    @property
    def needs_confirmation(self) -> bool:
        """Whether applying this plan would destroy anything the user has."""
        return bool(self.destructive or self.removals)

    @property
    def is_noop(self) -> bool:
        """Whether everything is already up to date."""
        return not self.pending and not self.removals


def _read(path: str) -> str | None:
    """Read a UTF-8 file, or return None if it doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def load_memory_block() -> str:
    """Load the packaged memory block written into the project's CLAUDE.md.

    Returns:
        str: The memory block, delimited by the begin and end markers.

    Raises:
        ValueError: If the packaged memory file is missing.
    """
    memory_path = os.path.join(SKILLS_PACKAGE_DIR, "memory.md")
    content = _read(memory_path)
    if content is None:
        raise ValueError(f"Packaged memory file not found: {memory_path}")
    return content.strip() + "\n"


def discover_skill_files() -> list[tuple[str, str]]:
    """Find the packaged skill files to install.

    Returns:
        list[tuple[str, str]]: ``(absolute source path, path relative to the
        skill directory)`` pairs, sorted for stable output.

    Raises:
        ValueError: If the packaged skill directory is missing.
    """
    skill_dir = os.path.join(SKILLS_PACKAGE_DIR, SKILL_NAME)
    if not os.path.isdir(skill_dir):
        raise ValueError(f"Packaged skill not found: {skill_dir}")

    files: list[tuple[str, str]] = []
    for root, _, file_names in os.walk(skill_dir):
        for file_name in file_names:
            if not file_name.endswith(".md"):
                continue
            source = os.path.join(root, file_name)
            files.append((source, os.path.relpath(source, skill_dir)))
    return sorted(files, key=lambda pair: pair[1])


def render_memory(existing: str | None, block: str) -> str:
    """Merge the poly-adk memory block into an existing CLAUDE.md.

    A CLAUDE.md that already carries the block has it replaced in place, so
    anything the user wrote around it survives. A CLAUDE.md without the block
    gets it appended.

    Args:
        existing: Current CLAUDE.md content, or None if the file doesn't exist.
        block: The memory block to install.

    Returns:
        str: The full content the CLAUDE.md should have.

    Raises:
        ValueError: If the existing file opens the block but never closes it.
    """
    if existing is None or not existing.strip():
        return block

    if MEMORY_BEGIN not in existing:
        return existing.rstrip("\n") + "\n\n" + block

    if MEMORY_END not in existing:
        raise ValueError(
            f"{MEMORY_FILE} contains '{MEMORY_BEGIN}' with no matching '{MEMORY_END}'. "
            "Fix or remove the partial block and re-run."
        )

    before = existing.split(MEMORY_BEGIN, 1)[0]
    after = existing.split(MEMORY_END, 1)[1]
    return before + block.rstrip("\n") + after


def _plan_write(path: str, content: str, append: bool = False) -> PlannedWrite:
    """Classify a single write against what is already on disk."""
    current = _read(path)
    if current is None:
        action = CREATE
    elif current == content:
        action = UNCHANGED
    else:
        action = APPEND if append else OVERWRITE
    return PlannedWrite(path=path, content=content, action=action)


def _find_stale_files(skill_dir: str, expected: set[str]) -> list[str]:
    """List files under an installed skill directory that are no longer shipped."""
    if not os.path.isdir(skill_dir):
        return []
    stale = [
        os.path.join(root, file_name)
        for root, _, file_names in os.walk(skill_dir)
        for file_name in file_names
        if os.path.join(root, file_name) not in expected
    ]
    return sorted(stale)


def plan_claude_code_setup(target_dir: str) -> ClaudeCodePlan:
    """Work out what installing the Claude Code assets would change.

    Args:
        target_dir: Project directory to install into.

    Returns:
        ClaudeCodePlan: The planned writes and removals, without touching disk.

    Raises:
        ValueError: If the packaged assets are missing, or an existing
            CLAUDE.md has a malformed poly-adk block.
    """
    target_dir = os.path.abspath(target_dir)
    plan = ClaudeCodePlan(target_dir=target_dir)

    skill_dir = os.path.join(target_dir, ".claude", "skills", SKILL_NAME)
    for source, relative in discover_skill_files():
        content = _read(source) or ""
        plan.writes.append(_plan_write(os.path.join(skill_dir, relative), content))

    memory_path = os.path.join(target_dir, MEMORY_FILE)
    existing_memory = _read(memory_path)
    merged = render_memory(existing_memory, load_memory_block())
    # Appending to a CLAUDE.md the user already had is additive, so it never
    # needs a confirmation prompt; replacing an existing block does.
    is_append = existing_memory is not None and MEMORY_BEGIN not in existing_memory
    plan.writes.append(_plan_write(memory_path, merged, append=is_append))

    # The installed skill mirrors the packaged one exactly, so a reference file
    # dropped or renamed in a later release must not linger and mislead the agent.
    plan.removals = _find_stale_files(skill_dir, {write.path for write in plan.writes})

    return plan


def apply_claude_code_setup(plan: ClaudeCodePlan) -> tuple[list[PlannedWrite], list[str]]:
    """Write every pending file in a plan and delete its stale files.

    Args:
        plan: The plan produced by ``plan_claude_code_setup``.

    Returns:
        tuple[list[PlannedWrite], list[str]]: The writes applied and the paths removed.
    """
    applied = plan.pending
    for write in applied:
        parent = os.path.dirname(write.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(write.path, "w", encoding="utf-8") as f:
            f.write(write.content)

    for path in plan.removals:
        os.remove(path)

    # Drop any directories the removals emptied out.
    skill_dir = os.path.join(plan.target_dir, ".claude", "skills", SKILL_NAME)
    if plan.removals and os.path.isdir(skill_dir):
        for root, dir_names, _ in os.walk(skill_dir, topdown=False):
            for dir_name in dir_names:
                path = os.path.join(root, dir_name)
                if not os.listdir(path):
                    os.rmdir(path)

    return applied, plan.removals
