"""AI agent skill installation via the ``npx skills`` package.

Wraps the Vercel Labs ``skills`` npm CLI, which handles multi-IDE discovery,
symlink management, and updates. The ADK repo hosts the skills as Markdown
files under ``skills/``; this module only shells out to distribute them.

Copyright PolyAI Limited
"""

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)

# Pinned so that a breaking release of the npm package cannot break 'poly setup'
# or 'poly update' for every user at once. Bump deliberately.
SKILLS_NPX_PACKAGE = "skills@1.5.18"

# Where the published skills live. 'poly setup --dev' overrides this with the
# local ./skills directory for skill development.
SKILLS_SOURCE = "https://github.com/polyai/adk"

# npx itself requires a modern Node; the skills package targets 18+.
MIN_NODE_MAJOR = 18

# Generous: the first run downloads the npm package and clones the skills repo.
NPX_TIMEOUT_SECONDS = 600


def node_gate_reason() -> str | None:
    """Return why the ``npx skills`` step cannot run, or ``None`` if it can.

    The skills step must never fail onboarding after auth and project setup
    have succeeded, so callers use this to skip the step with a warning rather
    than attempting a run that cannot work.
    """
    if shutil.which("node") is None or shutil.which("npx") is None:
        return "Node.js (with npx) was not found on your PATH"
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        major = int(result.stdout.strip().lstrip("v").split(".")[0])
    except Exception:
        return "the Node.js version could not be determined"
    if major < MIN_NODE_MAJOR:
        return f"Node.js {major} is too old (Node {MIN_NODE_MAJOR}+ is required)"
    return None


def _run_npx_skills(args: list[str]) -> bool:
    """Run ``npx -y skills@<pin> <args>``, streaming output to the terminal.

    Returns:
        True if the command exited 0. Never raises — failures here must not
        abort the caller's remaining steps.
    """
    command = ["npx", "-y", SKILLS_NPX_PACKAGE, *args]
    logger.debug("Running: %s", " ".join(command))
    try:
        result = subprocess.run(command, timeout=NPX_TIMEOUT_SECONDS)
    except Exception as e:
        logger.debug("npx skills invocation failed: %s", e)
        return False
    return result.returncode == 0


def install_skills(
    source: str | None = None,
    global_install: bool = False,
    agents: list[str] | None = None,
) -> bool:
    """Install the ADK skills into detected coding agents.

    Args:
        source: Skills source — a repo URL or local path. Defaults to the
            published ADK repo.
        global_install: Install user-level rather than into the current project.
        agents: Restrict installation to specific agents (e.g. 'claude-code').

    Returns:
        True on success, False otherwise (never raises).
    """
    args = ["add", source or SKILLS_SOURCE, "-y"]
    if global_install:
        args.append("--global")
    if agents:
        args.extend(["--agent", *agents])
    return _run_npx_skills(args)


def update_skills(global_only: bool = False) -> bool:
    """Update previously installed skills to their latest versions.

    Returns:
        True on success, False otherwise (never raises).
    """
    args = ["update", "-y"]
    if global_only:
        args.append("--global")
    return _run_npx_skills(args)
