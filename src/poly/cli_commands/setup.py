"""Setup command: one-command onboarding for the ADK.

Runs the full first-run sequence — authentication, shell completion, AI agent
skills, and project setup — skipping any step that is already done, so it is
safe to re-run at any time.

Copyright PolyAI Limited
"""

import logging
import os
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from pathlib import Path

from poly.cli_commands.auth import _authenticate_and_save_key, _select_region, _signin
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.project import InitCommand, ProjectCommand
from poly.cli_commands.skills import install_skills, node_gate_reason
from poly.handlers.interface import REGIONS
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
                "  poly setup --region us-1\n"
                "  poly setup --skip-auth --agent claude-code\n"
                "  poly setup --dev -g\n"
            ),
        )
        setup_parser.add_argument(
            "--region",
            type=str,
            choices=REGIONS,
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

        # --- 1. Authentication ---
        if skip_auth:
            info("Authentication: skipped (--skip-auth).")
        elif any_credentials_exist():
            success("Authentication: existing credentials found — skipping.")
        else:
            if region is None:
                region = _select_region()
            jwt_access_token = _signin(region)
            _authenticate_and_save_key(jwt_access_token, region=region)

        # --- 2. Shell completion ---
        cls._install_completion()

        # --- 3. AI agent skills ---
        cls._install_skills(skip_skills, agents, dev, global_install)

        # --- 4. Project setup ---
        cls._setup_project(base_path, region)

        success("Setup complete.")

    @classmethod
    def _install_completion(cls) -> None:
        """Install shell completion for the user's shell, if not already installed.

        Never raises — completion is a convenience and must not abort setup.
        """
        from poly.output.console import info, success, warning

        shell = Path(os.environ.get("SHELL", "")).name
        try:
            if shell in _SHELL_RC_FILES:
                rc_path = Path(_SHELL_RC_FILES[shell]).expanduser()
                existing = rc_path.read_text(encoding="utf-8") if rc_path.exists() else ""
                if COMPLETION_MARKER in existing or "poly completion" in existing:
                    success(f"Shell completion: already configured in {rc_path} — skipping.")
                    return
                with open(rc_path, "a", encoding="utf-8") as f:
                    f.write(f'\n{COMPLETION_MARKER}\neval "$(poly completion {shell})"\n')
                success(f"Shell completion: added to {rc_path} (takes effect in new shells).")
            elif shell == "fish":
                completion_path = Path(_FISH_COMPLETION_PATH).expanduser()
                if completion_path.exists():
                    success(f"Shell completion: {completion_path} already exists — skipping.")
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
        except Exception as e:
            logger.debug("Completion install failed: %s", e)
            warning(
                "Shell completion: could not install automatically."
                " See 'poly completion --help' to set it up manually."
            )

    @classmethod
    def _install_skills(
        cls,
        skip_skills: bool,
        agents: list[str] | None,
        dev: bool,
        global_install: bool,
    ) -> None:
        """Install AI agent skills. Non-fatal: failure warns and setup continues."""
        from poly.output.console import info, success, warning

        if skip_skills:
            info("AI skills: skipped (--skip-skills).")
            return

        gate_reason = node_gate_reason()
        if gate_reason:
            warning(
                f"AI skills: skipped — {gate_reason}."
                " Install Node.js 18+ and re-run 'poly setup' to add them."
            )
            return

        info("AI skills: installing into detected coding agents...")
        source = "./skills" if dev else None
        if install_skills(source=source, global_install=global_install, agents=agents):
            success("AI skills: installed.")
        else:
            warning("AI skills: installation failed. Re-run 'poly setup' to retry.")

    @classmethod
    def _setup_project(cls, base_path: str, region: str | None) -> None:
        """Create or connect a project, unless already inside one."""
        import sys

        import questionary

        from poly.output.console import info, success

        if os.path.exists(os.path.join(base_path, "project.yaml")):
            success("Project: already inside an ADK project — skipping.")
            return

        if not sys.stdin.isatty():
            info(
                "Project: skipped (not an interactive terminal). Run"
                " 'poly project create' or 'poly init' to set one up."
            )
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
        elif choice == "init":
            InitCommand.init_project(base_path, region=region)
        else:
            info("Project: skipped. Run 'poly project create' or 'poly init' when you are ready.")
