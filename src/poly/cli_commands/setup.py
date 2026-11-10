"""Setup command: one-command onboarding for the ADK.

Runs the full first-run sequence — authentication, shell completion, AI agent
skills, and project setup — skipping any step that is already done, so it is
safe to re-run at any time. Each run reports anonymous usage events unless
the user has opted out.

Copyright PolyAI Limited
"""

import logging
import os
import platform
import sys
import time
import uuid
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from collections.abc import Callable
from pathlib import Path

from poly.cli_commands.auth import _authenticate_and_save_key, _select_region, _signin
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.project import InitCommand, ProjectCommand
from poly.cli_commands.shared import REGION_CHOICES, get_package_version, region_type
from poly.cli_commands.skills import install_skills, node_gate_reason
from poly.handlers.posthog import capture_event
from poly.project import PROJECT_CONFIG_FILE, STATUS_FILE
from poly.utils import any_credentials_exist

logger = logging.getLogger(__name__)

# Marks lines 'poly setup' added to a shell rc file, so re-runs can detect them.
COMPLETION_MARKER = "# Added by 'poly setup'"

_SHELL_RC_FILES = {
    "bash": "~/.bashrc",
    "zsh": "~/.zshrc",
}
_FISH_COMPLETION_PATH = "~/.config/fish/completions/poly.fish"

# Environment variables a coding agent sets in the processes it spawns.
_AGENT_ENV_MARKERS = {
    "CLAUDECODE": "claude-code",
    "CURSOR_AGENT": "cursor",
    "CODEX_SANDBOX": "codex",
}


def _invoking_agent() -> str:
    """Name the coding agent that spawned this process, or ``"none"``."""
    return next((a for var, a in _AGENT_ENV_MARKERS.items() if os.environ.get(var)), "none")


class SetupRun:
    """Anonymous usage events for one ``poly setup`` run, keyed by a random run id.

    Sends ``setup_started``, one ``setup_step`` per step and ``setup_completed``.
    If the first event is not sent (opt-out or no network), nothing else is.
    """

    def __init__(self, region: str | None, **started: object) -> None:
        self.region = region
        self.run_id = f"setup:{uuid.uuid4()}"
        self.sending = capture_event(region, "setup_started", started, self.run_id)

    def _send(self, event: str, **properties: object) -> None:
        if self.sending:
            capture_event(self.region, event, properties, self.run_id)

    def step(
        self, name: str, run_step: Callable[..., str | tuple[str, str]], *args: object
    ) -> None:
        """Run a step, then report its outcome (or outcome and reason) and duration."""
        start = time.monotonic()
        result: str | tuple[str, str] = "failed"
        try:
            result = run_step(*args)
        except BaseException as exc:
            result = ("failed", type(exc).__name__)
            raise
        finally:
            outcome, *reason = (result,) if isinstance(result, str) else result
            extra = {"reason": reason[0]} if reason else {}
            duration_ms = int((time.monotonic() - start) * 1000)
            self._send("setup_step", step=name, outcome=outcome, duration_ms=duration_ms, **extra)

    def completed(self) -> None:
        """Report that the run reached the end."""
        self._send("setup_completed")


class SetupCommand(BaseCommand):
    """Set up the ADK: authentication, shell completion, AI skills, and a project."""

    command = "setup"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``setup`` subcommand."""
        setup_parser = subparsers.add_parser(
            "setup",
            parents=[parents.verbose, parents.debug],
            formatter_class=RawTextHelpFormatter,
            help="Set up the ADK: auth, shell completion, AI skills, and a project",
            description=(
                "Set up everything the ADK needs in one command.\n\n"
                "Runs four steps, each skipped automatically if already done:\n"
                "  1. Authentication (browser sign-in, saves an API key)\n"
                "  2. Shell completion for bash/zsh/fish\n"
                "  3. AI agent skills, installed into detected coding agents\n"
                "  4. Project setup (create a new project or connect an existing one)\n\n"
                "Examples:\n"
                "  poly setup\n"
                "  poly setup --region us\n"
                "  poly setup --skip-auth --agent claude-code\n"
                "  poly setup --dev -g\n"
            ),
        )
        setup_parser.add_argument(
            "--region",
            type=region_type,
            choices=REGION_CHOICES,
            default=None,
            help="Region to sign in to. If omitted, you will be prompted to select one.",
        )
        setup_parser.add_argument(
            "--base-path",
            type=str,
            default=os.getcwd(),
            help="Base path for project setup. Defaults to the current working directory.",
        )
        setup_parser.add_argument(
            "--skip-auth",
            action="store_true",
            help="Skip the authentication step.",
        )
        setup_parser.add_argument(
            "--skip-skills",
            action="store_true",
            help="Skip installing AI agent skills.",
        )
        setup_parser.add_argument(
            "--agent",
            action="append",
            dest="agents",
            metavar="NAME",
            help="Install skills only into this coding agent (repeatable), "
            "e.g. claude-code, cursor, codex.",
        )
        setup_parser.add_argument(
            "--dev",
            action="store_true",
            help="Install skills from the local ./skills directory instead of the "
            "published ADK repo (for skill development).",
        )
        setup_parser.add_argument(
            "--global",
            "-g",
            action="store_true",
            dest="global_install",
            help="Install skills user-level (all projects) instead of into the current project.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the setup handler."""
        cls.setup(
            base_path=args.base_path,
            region=args.region,
            skip_auth=args.skip_auth,
            skip_skills=args.skip_skills,
            agents=args.agents,
            dev=args.dev,
            global_install=args.global_install,
        )

    @classmethod
    def setup(
        cls,
        base_path: str,
        region: str | None = None,
        skip_auth: bool = False,
        skip_skills: bool = False,
        agents: list[str] | None = None,
        dev: bool = False,
        global_install: bool = False,
    ) -> None:
        """Run the full setup sequence, skipping steps that are already done."""
        from poly.output.console import plain, print_welcome_message, success

        print_welcome_message()
        plain(
            "This will set up authentication, shell completion, AI agent skills,"
            " and a project. Steps that are already done are skipped."
        )
        plain("")

        had_credentials = any_credentials_exist()
        run = SetupRun(
            region,
            os=platform.system().lower(),
            adk_version=get_package_version(),
            invoking_agent=_invoking_agent(),
            interactive=sys.stdin.isatty(),
            had_credentials=had_credentials,
        )

        # --- 1. Authentication ---
        if not (skip_auth or had_credentials) and region is None:
            region = run.region = _select_region()
        run.step("auth", cls._authenticate, skip_auth, had_credentials, region)

        # --- 2. Shell completion ---
        run.step("completion", cls._install_completion)

        # --- 3. AI agent skills ---
        run.step("skills", cls._install_skills, skip_skills, agents, dev, global_install)

        # --- 4. Project setup ---
        run.step("project", cls._setup_project, base_path, region)

        run.completed()
        success("Setup complete.")

    @classmethod
    def _authenticate(cls, skip_auth: bool, had_credentials: bool, region: str | None) -> str:
        """Sign in and save an API key, unless skipped or already done.

        Returns:
            The step outcome: ``"done"`` or ``"skipped"``.
        """
        from poly.output.console import info, success

        if skip_auth:
            info("Authentication: skipped (--skip-auth).")
            return "skipped"
        if had_credentials:
            success("Authentication: existing credentials found — skipping.")
            return "skipped"
        jwt_access_token = _signin(region)
        _authenticate_and_save_key(jwt_access_token, region=region)
        return "done"

    @classmethod
    def _install_completion(cls) -> str | tuple[str, str]:
        """Install shell completion for the user's shell, if not already installed.

        Never raises — completion is a convenience and must not abort setup.

        Returns:
            The step outcome: ``"done"``, ``"skipped"``, or ``"failed"`` with the
            error's class name.
        """
        from poly.output.console import info, success, warning

        shell = Path(os.environ.get("SHELL", "")).name
        try:
            if shell in _SHELL_RC_FILES:
                rc_path = Path(_SHELL_RC_FILES[shell]).expanduser()
                existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
                if COMPLETION_MARKER in existing or "poly completion" in existing:
                    success(f"Shell completion: already configured in {rc_path} — skipping.")
                    return "skipped"
                with open(rc_path, "a", encoding="utf-8") as f:
                    f.write(f'\n{COMPLETION_MARKER}\neval "$(poly completion {shell})"\n')
                success(f"Shell completion: added to {rc_path} (takes effect in new shells).")
            elif shell == "fish":
                completion_path = Path(_FISH_COMPLETION_PATH).expanduser()
                if completion_path.exists():
                    success(f"Shell completion: {completion_path} already exists — skipping.")
                    return "skipped"
                import argcomplete

                completion_path.parent.mkdir(parents=True, exist_ok=True)
                completion_path.write_text(
                    argcomplete.shellcode(["poly", "adk"], shell="fish"), encoding="utf-8"
                )
                success(f"Shell completion: written to {completion_path}.")
            else:
                info(
                    "Shell completion: unrecognised shell"
                    f" {shell or '(unknown)'} — skipping."
                    " See 'poly completion --help' to set it up manually."
                )
                return "skipped"
        except Exception as e:
            logger.debug("Completion install failed: %s", e)
            warning(
                "Shell completion: could not install automatically."
                " See 'poly completion --help' to set it up manually."
            )
            return "failed", type(e).__name__
        return "done"

    @classmethod
    def _install_skills(
        cls,
        skip_skills: bool,
        agents: list[str] | None,
        dev: bool,
        global_install: bool,
    ) -> str | tuple[str, str]:
        """Install AI agent skills. Non-fatal: failure warns and setup continues.

        Returns:
            The step outcome: ``"done"``, ``"skipped"`` (with the reason when
            Node.js is the cause) or ``"failed"``.
        """
        from poly.output.console import info, success, warning

        if skip_skills:
            info("AI skills: skipped (--skip-skills).")
            return "skipped"

        gate_reason = node_gate_reason()
        if gate_reason:
            warning(
                f"AI skills: skipped — {gate_reason}."
                " Install Node.js 18+ and re-run 'poly setup' to add them."
            )
            return "skipped", gate_reason

        info("AI skills: installing into detected coding agents...")
        source = "./skills" if dev else None
        if install_skills(source=source, global_install=global_install, agents=agents):
            success("AI skills: installed.")
            return "done"
        warning("AI skills: installation failed. Re-run 'poly setup' to retry.")
        return "failed"

    @classmethod
    def _setup_project(cls, base_path: str, region: str | None) -> str:
        """Create or connect a project, unless already inside one.

        Returns:
            The step outcome: ``"created"``, ``"connected"``, ``"declined"`` or
            ``"skipped"``.
        """
        import questionary

        from poly.output.console import info, success

        for marker in (PROJECT_CONFIG_FILE, STATUS_FILE):
            if os.path.exists(os.path.join(base_path, marker)):
                success("Project: already inside an ADK project — skipping.")
                return "skipped"

        if not sys.stdin.isatty():
            info(
                "Project: skipped (not an interactive terminal). Run"
                " 'poly project create' or 'poly init' to set one up."
            )
            return "skipped"

        choice = questionary.select(
            "Set up a project?",
            choices=[
                questionary.Choice("Create a new Agent Studio project", value="create"),
                questionary.Choice("Connect an existing project", value="init"),
                questionary.Choice("Skip for now", value="skip"),
            ],
        ).ask()

        if choice == "create":
            ProjectCommand.create_project(base_path, region=region)
            return "created"
        if choice == "init":
            InitCommand.init_project(base_path, region=region)
            return "connected"
        info("Project: skipped. Run 'poly project create' or 'poly init' when you are ready.")
        return "declined"
