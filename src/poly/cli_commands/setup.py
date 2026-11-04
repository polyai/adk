"""Setup command: one-command onboarding for the ADK.

Runs the full first-run sequence — authentication, shell completion, AI agent
skills, and project setup — skipping any step that is already done, so it is
safe to re-run at any time. Each run reports start, per-step outcome and
completion to PostHog unless the user opted out (see ``poly.setup.telemetry``).

Copyright PolyAI Limited
"""

import logging
import os
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from pathlib import Path

from poly.cli_commands.auth import _authenticate_and_save_key, _select_region, _signin
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.project import InitCommand, ProjectCommand
from poly.cli_commands.shared import REGION_CHOICES, region_type
from poly.cli_commands.skills import install_skills, node_gate_reason
from poly.project import PROJECT_CONFIG_FILE, STATUS_FILE
from poly.setup.telemetry import SetupRun, StepResult, detect_mode
from poly.utils import any_credentials_exist

logger = logging.getLogger(__name__)

# Marks lines 'poly setup' added to a shell rc file, so re-runs can detect them.
COMPLETION_MARKER = "# Added by 'poly setup'"

_SHELL_RC_FILES = {
    "bash": "~/.bashrc",
    "zsh": "~/.zshrc",
}
_FISH_COMPLETION_PATH = "~/.config/fish/completions/poly.fish"


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
        from poly.output.console import info, plain, print_welcome_message, success

        print_welcome_message()
        plain(
            "This will set up authentication, shell completion, AI agent skills,"
            " and a project. Steps that are already done are skipped."
        )
        plain("")

        had_credentials = any_credentials_exist()
        run = SetupRun(region=region, mode=detect_mode())
        run.started(had_credentials=had_credentials)

        # --- 1. Authentication: sign in, then fetch or create the key ---
        if skip_auth or had_credentials:
            if skip_auth:
                info("Authentication: skipped (--skip-auth).")
            else:
                success("Authentication: existing credentials found — skipping.")
            with run.step("signin") as step:
                step.skipped()
            with run.step("credentials") as step:
                step.skipped()
        else:
            with run.step("signin"):
                if region is None:
                    region = _select_region()
                run.region = region
                jwt_access_token = _signin(region)
            with run.step("credentials"):
                accounts = _authenticate_and_save_key(jwt_access_token, region=region)
                # The PAT path does not pick an account; with exactly one there is no
                # ambiguity. Multi-account runs stay anonymous until the credentials
                # step resolves one.
                if len(accounts) == 1:
                    run.identify(next(iter(accounts)))

        # --- 2. Shell completion ---
        with run.step("completion") as step:
            cls._install_completion(step)

        # --- 3. AI agent skills ---
        with run.step("skills") as step:
            cls._install_skills(skip_skills, agents, dev, global_install, step)

        # --- 4. Project setup ---
        with run.step("project") as step:
            cls._setup_project(base_path, region, step)

        run.completed()
        success("Setup complete.")

    @classmethod
    def _install_completion(cls, step: StepResult | None = None) -> None:
        """Install shell completion for the user's shell, if not already installed.

        Never raises — completion is a convenience and must not abort setup.

        Args:
            step: Telemetry record for this step, filled in with the outcome.
        """
        from poly.output.console import info, success, warning

        step = step or StepResult()
        shell = Path(os.environ.get("SHELL", "")).name
        try:
            if shell in _SHELL_RC_FILES:
                rc_path = Path(_SHELL_RC_FILES[shell]).expanduser()
                existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
                if COMPLETION_MARKER in existing or "poly completion" in existing:
                    success(f"Shell completion: already configured in {rc_path} — skipping.")
                    step.skipped()
                    return
                with open(rc_path, "a", encoding="utf-8") as f:
                    f.write(f'\n{COMPLETION_MARKER}\neval "$(poly completion {shell})"\n')
                success(f"Shell completion: added to {rc_path} (takes effect in new shells).")
            elif shell == "fish":
                completion_path = Path(_FISH_COMPLETION_PATH).expanduser()
                if completion_path.exists():
                    success(f"Shell completion: {completion_path} already exists — skipping.")
                    step.skipped()
                    return
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
                step.skipped()
        except Exception as e:
            logger.debug("Completion install failed: %s", e)
            warning(
                "Shell completion: could not install automatically."
                " See 'poly completion --help' to set it up manually."
            )
            step.failed(type(e).__name__)

    @classmethod
    def _install_skills(
        cls,
        skip_skills: bool,
        agents: list[str] | None,
        dev: bool,
        global_install: bool,
        step: StepResult | None = None,
    ) -> None:
        """Install AI agent skills. Non-fatal: failure warns and setup continues.

        Args:
            step: Telemetry record for this step, filled in with the outcome.
        """
        from poly.output.console import info, success, warning

        step = step or StepResult()
        if skip_skills:
            info("AI skills: skipped (--skip-skills).")
            step.skipped()
            return

        gate_reason = node_gate_reason()
        if gate_reason:
            warning(
                f"AI skills: skipped — {gate_reason}."
                " Install Node.js 18+ and re-run 'poly setup' to add them."
            )
            step.skipped()
            return

        info("AI skills: installing into detected coding agents...")
        source = "./skills" if dev else None
        if install_skills(source=source, global_install=global_install, agents=agents):
            success("AI skills: installed.")
        else:
            warning("AI skills: installation failed. Re-run 'poly setup' to retry.")
            step.failed("npx_failed")

    @classmethod
    def _setup_project(
        cls, base_path: str, region: str | None, step: StepResult | None = None
    ) -> None:
        """Create or connect a project, unless already inside one.

        Args:
            step: Telemetry record for this step, filled in with the outcome and
                a ``created`` / ``connected`` / ``declined`` detail.
        """
        import sys

        import questionary

        from poly.output.console import info, success

        step = step or StepResult()
        for marker in (PROJECT_CONFIG_FILE, STATUS_FILE):
            if os.path.exists(os.path.join(base_path, marker)):
                success("Project: already inside an ADK project — skipping.")
                step.skipped()
                return

        if not sys.stdin.isatty():
            info(
                "Project: skipped (not an interactive terminal). Run"
                " 'poly project create' or 'poly init' to set one up."
            )
            step.skipped()
            return

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
            step.done("created")
        elif choice == "init":
            InitCommand.init_project(base_path, region=region)
            step.done("connected")
        else:
            info("Project: skipped. Run 'poly project create' or 'poly init' when you are ready.")
            step.declined("declined")
