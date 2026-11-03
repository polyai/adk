"""Setup command: one-command onboarding for the ADK.

Runs the full first-run sequence — one sign-in that mints both the ADK key and
the account API key, the ``POLY_API_KEY`` export, shell completion, AI agent
skills, and project setup — skipping any step that is already done, so it is
safe to re-run at any time. Each run reports start, per-step outcome and
completion to PostHog unless the user opted out (see ``poly.setup.telemetry``).

Copyright PolyAI Limited
"""

import logging
import os
import sys
import time
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from pathlib import Path

import requests

from poly.auth.account_key import (
    DEFAULT_KEY_NAME,
    SETUP_KEY_NAME,
    key_name_for_region,
    mint_account_key,
    resolve_account_id,
    wait_for_key_active,
)
from poly.cli_commands.auth import (
    _authenticate_and_save_key,
    _select_region,
    _signin,
    authorise_or_explain,
)
from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.project import InitCommand, ProjectCommand
from poly.cli_commands.shared import REGION_CHOICES, pick_account, region_type
from poly.cli_commands.skills import install_skills, node_gate_reason
from poly.handlers.auth0_handler import APIKEY_AUTH_DETAILS
from poly.handlers.interface import AgentStudioInterface
from poly.project import PROJECT_CONFIG_FILE, STATUS_FILE
from poly.setup.telemetry import SetupRun, StepResult, detect_mode
from poly.utils import apikey_session
from poly.utils.credentials import (
    CREDENTIALS_FILE_PATH,
    any_credentials_exist,
    load_account_key_credential,
    regions_with_stored_keys,
    retrieve_api_key,
    save_account_key_credential,
)
from poly.utils.env_profile import EnvVarConflict, detect_profile, read_env_var, write_env_var

logger = logging.getLogger(__name__)

# Value for the X-Poly-Source header on the account-key calls setup makes.
SETUP_SOURCE = "setup"
# A freshly minted account key can take a few seconds to become valid at the public
# gateway, so a 401 right after minting is retried for this long before it counts.
VERIFY_RETRY_SECONDS = 20
VERIFY_RETRY_INTERVAL_SECONDS = 2
ACCOUNT_KEY_ENV_VAR = "POLY_API_KEY"

# Marks lines 'poly setup' added to a shell rc file, so re-runs can detect them.
COMPLETION_MARKER = "# Added by 'poly setup'"

_SHELL_RC_FILES = {
    "bash": "~/.bashrc",
    "zsh": "~/.zshrc",
}
_FISH_COMPLETION_PATH = "~/.config/fish/completions/poly.fish"


def _is_not_yet_valid(exc: Exception) -> bool:
    """Whether `exc` is the gateway refusing a key that may simply not be active yet."""
    response = getattr(exc, "response", None)
    return isinstance(exc, requests.HTTPError) and getattr(response, "status_code", None) in (
        401,
        403,
    )


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
                "Runs six steps, each skipped automatically if already done:\n"
                "  1. Authentication: one browser sign-in that saves an ADK key for the CLI\n"
                "     and an account API key for the PolyAI APIs and MCPs\n"
                "  2. Verify: one timed call to the PolyAI API with the account key\n"
                "  3. POLY_API_KEY exported to your shell profile (asks first)\n"
                "  4. Shell completion for bash/zsh/fish\n"
                "  5. AI agent skills, installed into detected coding agents\n"
                "  6. Project setup (create a new project or connect an existing one)\n\n"
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
            "--account-id",
            type=str,
            default=None,
            help=(
                "Account to scope the account API key to. With more than one account and"
                " no --account-id, a terminal shows a picker; otherwise setup stops and"
                " lists the accounts so you can re-run with one of them."
            ),
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
            "--skip-verify",
            action="store_true",
            help="Skip the verification call made with the account API key.",
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
            account_id=args.account_id,
            skip_auth=args.skip_auth,
            skip_verify=args.skip_verify,
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
        account_id: str | None = None,
        skip_auth: bool = False,
        skip_verify: bool = False,
        skip_skills: bool = False,
        agents: list[str] | None = None,
        dev: bool = False,
        global_install: bool = False,
    ) -> None:
        """Run the full setup sequence, skipping steps that are already done."""
        from poly.output.console import info, plain, print_welcome_message, success

        print_welcome_message()
        plain(
            "This will set up authentication, POLY_API_KEY, shell completion, AI agent"
            " skills, and a project. Steps that are already done are skipped."
        )
        plain("")

        run = SetupRun(region=region, mode=detect_mode())
        run.started(had_credentials=any_credentials_exist())

        # --- 1. Authentication: one sign-in, both credentials ---
        if skip_auth:
            info("Authentication: skipped (--skip-auth).")
            with run.step("signin") as step:
                step.skipped()
            with run.step("credentials") as step:
                step.skipped()
            account_key, fresh_key = None, False
        else:
            region, account_id, account_key, fresh_key = cls._authenticate(region, account_id, run)

        # --- 2. Verify: prove the account key before anything persistent uses it ---
        with run.step("verify") as step:
            run.verify_ok = cls._verify(
                account_key, region, account_id, skip_verify, step, fresh=fresh_key
            )

        # --- 3. POLY_API_KEY in the shell profile ---
        with run.step("environment") as step:
            cls._export_account_key(account_key, region, step)

        # --- 4. Shell completion ---
        with run.step("completion") as step:
            cls._install_completion(step)

        # --- 5. AI agent skills ---
        with run.step("skills") as step:
            cls._install_skills(skip_skills, agents, dev, global_install, step)

        # --- 6. Project setup ---
        with run.step("project") as step:
            cls._setup_project(base_path, region, step, account_id=account_id)

        run.completed()
        success("Setup complete.")

    @classmethod
    def _authenticate(
        cls, region: str | None, account_id: str | None, run: SetupRun
    ) -> tuple[str, str | None, str | None, bool]:
        """Make sure `region` holds both an ADK key and an account API key.

        Signs in at most once, reusing the sign-in ``poly apikey`` keeps when it is
        still valid, and mints only what is missing: a developer who already has an
        ADK key from ``poly login`` gains the account key without a second browser
        round trip. On studio the sign-in uses the GitHub-only client, the
        self-serve door; other regions keep their standard client.

        Args:
            region: The region to set up, or None to infer it from the stored ADK
                key when there is exactly one, else to ask.
            account_id: The account to scope the account key to, or None to resolve
                it (polling, or a picker at a terminal).
            run: The telemetry run; records the ``signin`` and ``credentials`` steps
                and switches identity to the account id once known.

        Returns:
            The region used, the account id and the account API key.
        """
        from poly.output.console import console, error, info, mask_api_key, success, warning

        if region is None:
            stored = regions_with_stored_keys()
            region = stored[0] if len(stored) == 1 else _select_region()
        run.region = region

        try:
            retrieve_api_key(region)
            has_adk_key = True
        except ValueError:
            has_adk_key = False
        stored_account = load_account_key_credential(region)

        if has_adk_key and stored_account:
            success(f"Authentication: ADK key and account API key found for {region} — skipping.")
            with run.step("signin") as step:
                step.skipped()
            with run.step("credentials") as step:
                step.skipped()
            run.identify(stored_account["account_id"])
            return region, stored_account["account_id"], stored_account["key"], False

        with run.step("signin"):
            jwt_token, sign_in_reused = cls._sign_in_or_reuse(region)

        with run.step("credentials"):
            api = AgentStudioInterface()
            while True:
                try:
                    if has_adk_key:
                        success(f"ADK key: existing credential for {region} kept.")
                        authorise_or_explain(
                            api,
                            region,
                            jwt_token,
                            self_serve_hint="run `poly setup --region studio`",
                        )
                    else:
                        _authenticate_and_save_key(jwt_token, region=region)
                    break
                except requests.HTTPError as e:
                    # A kept sign-in can be revoked before it expires: drop it and sign
                    # in once more. A fresh sign-in that is refused is a real error.
                    unauthorised = e.response is not None and e.response.status_code == 401
                    if not (sign_in_reused and unauthorised):
                        raise
                    apikey_session.clear(region)
                    info("Your kept sign-in was refused; signing in again.")
                    jwt_token, sign_in_reused = cls._sign_in_or_reuse(region, reuse=False)
                except ValueError as e:
                    error(str(e))
                    sys.exit(1)

            if stored_account:
                success(
                    f"Account API key: existing '{stored_account['name'] or 'stored'}' key kept."
                )
                run.identify(stored_account["account_id"])
                return region, stored_account["account_id"], stored_account["key"], False

            try:
                account_id = resolve_account_id(
                    api,
                    region,
                    jwt_token,
                    account_id,
                    source=SETUP_SOURCE,
                    pick=pick_account if sys.stdin.isatty() else None,
                )
                api_key, reused, key_name = mint_account_key(
                    api,
                    region,
                    jwt_token,
                    account_id,
                    key_name_for_region(SETUP_KEY_NAME, region),
                    source=SETUP_SOURCE,
                    also_reuse=[key_name_for_region(DEFAULT_KEY_NAME, region)],
                )
            except ValueError as e:
                error(str(e))
                sys.exit(1)
            save_account_key_credential(region, api_key, account_id, key_name)
            success(
                f"Account API key: {'reusing' if reused else 'created'} '{key_name}'"
                f" ({mask_api_key(api_key)}), saved to {CREDENTIALS_FILE_PATH}."
            )
            with console.status("[info]Verifying the account API key is active...[/info]"):
                if not wait_for_key_active(api, region, api_key):
                    warning(
                        "The account API key was saved but is not active yet."
                        " If your next call fails, wait a moment and retry."
                    )
            run.identify(account_id)
        return region, account_id, api_key, not reused

    @classmethod
    def _verify(
        cls,
        api_key: str | None,
        region: str | None,
        account_id: str | None,
        skip_verify: bool,
        step: StepResult | None = None,
        *,
        fresh: bool = False,
    ) -> bool | None:
        """Make one timed call to the public API with the account key and report it.

        Proves the key before the shell profile or any agent config is written
        with it. A refused call ends the run, because every later step would
        persist a key that does not work.

        Args:
            api_key: The account API key, or None when the auth step was skipped.
            region: The region the key belongs to.
            account_id: The account the key is scoped to.
            skip_verify: ``--skip-verify``.
            step: Telemetry record for this step, filled in with the outcome.
            fresh: Whether the key was minted this run. Only then is a refusal
                retried, because the gateway can lag a few seconds behind the
                platform; a stored key that is refused has been revoked.

        Returns:
            True when the call succeeded, None when it was skipped. Never False:
            a failed call exits.
        """
        from poly.output.console import error, info, success

        step = step or StepResult()
        if skip_verify:
            info("Verify: skipped (--skip-verify).")
            step.skipped()
            return None
        if api_key is None or account_id is None:
            info("Verify: skipped (no account API key this run).")
            step.skipped()
            return None

        api = AgentStudioInterface()
        started = time.monotonic()
        deadline = started + VERIFY_RETRY_SECONDS
        retrying = False
        while True:
            try:
                projects = api.get_projects_with_key(region, api_key, account_id)
                break
            except Exception as e:
                if fresh and _is_not_yet_valid(e) and time.monotonic() < deadline:
                    if not retrying:
                        info(
                            "Verify: the API does not know the new key yet, retrying for a moment."
                        )
                        retrying = True
                    time.sleep(VERIFY_RETRY_INTERVAL_SECONDS)
                    continue
                if fresh:
                    error(
                        f"Verify: the new account API key was refused by the {region} API"
                        f" ({e}). Nothing else has been written with it. Wait a moment and"
                        " re-run 'poly setup'; if it keeps failing, run 'poly apikey"
                        f" --region {region}' to mint a new key."
                    )
                else:
                    error(
                        f"Verify: the stored account API key was refused by the {region} API"
                        f" ({e}). It may have been revoked. Nothing else has been written"
                        f" with it. Run 'poly apikey --region {region}' to mint a new key,"
                        " then re-run 'poly setup'."
                    )
                step.failed(type(e).__name__)
                sys.exit(1)
        elapsed_ms = int((time.monotonic() - started) * 1000)
        success(
            f"Verify: connected to account {account_id}, {len(projects)} agent"
            f"{'' if len(projects) == 1 else 's'}, {elapsed_ms} ms."
        )
        return True

    @classmethod
    def _sign_in_or_reuse(cls, region: str, reuse: bool = True) -> tuple[str, bool]:
        """A JWT for `region`: the kept sign-in if still valid, else a fresh device flow.

        A fresh sign-in is kept for later runs, like ``poly apikey`` does.

        Args:
            region: The region to sign in to.
            reuse: Whether a kept sign-in may be used; False after one was refused.

        Returns:
            The token, and whether it was reused rather than freshly obtained.
        """
        from poly.output.console import info

        session = apikey_session.load(region) if reuse else None
        if session is not None:
            minutes_ago = max(0, int(time.time() - session.saved_at) // 60)
            info(f"Reusing your sign-in from {minutes_ago} minutes ago.")
            return session.token, True
        if region == "studio":
            info("Sign in with GitHub to create or open your Studio account.")
        token = _signin(region, auth_details=APIKEY_AUTH_DETAILS if region == "studio" else None)
        apikey_session.save(region, token)
        return token, False

    @classmethod
    def _export_account_key(
        cls, api_key: str | None, region: str | None, step: StepResult | None = None
    ) -> None:
        """Write ``POLY_API_KEY`` to the shell profile, after its own confirmation.

        Never folded into another confirmation: the profile is the developer's file.
        Skips when the value is already there, when there is no key to write, or
        when nobody can answer the prompt.

        Args:
            api_key: The account API key, or None when the auth step was skipped.
            region: The region the key belongs to, for the hint on how to retry.
            step: Telemetry record for this step, filled in with the outcome.
        """
        import questionary

        from poly.output.console import info, success, warning

        step = step or StepResult()
        if api_key is None:
            info(f"{ACCOUNT_KEY_ENV_VAR}: skipped (no account API key this run).")
            step.skipped()
            return

        target = detect_profile()
        if read_env_var(ACCOUNT_KEY_ENV_VAR) == api_key:
            success(f"{ACCOUNT_KEY_ENV_VAR}: already set in {target.path} — skipping.")
            step.skipped()
            return

        retry_hint = f"Run 'poly apikey --region {region}' later to export it."
        if not sys.stdin.isatty():
            info(f"{ACCOUNT_KEY_ENV_VAR}: not exported (not an interactive terminal). {retry_hint}")
            step.skipped()
            return

        confirmed = questionary.confirm(
            f"Add one line to {target.path} exporting {ACCOUNT_KEY_ENV_VAR}?", default=True
        ).ask()
        if not confirmed:
            info(f"{ACCOUNT_KEY_ENV_VAR}: not exported. {retry_hint}")
            step.declined()
            return

        try:
            target, masked_line = write_env_var(ACCOUNT_KEY_ENV_VAR, api_key)
        except EnvVarConflict as e:
            warning(
                f"{ACCOUNT_KEY_ENV_VAR}: {e} Run 'poly apikey --region {region} --force'"
                " to replace it."
            )
            step.failed("EnvVarConflict")
            return
        success(f"{ACCOUNT_KEY_ENV_VAR}: wrote to {target.path}: {masked_line}")
        if target.shell == "powershell":
            info(f"Open a new terminal to pick up {ACCOUNT_KEY_ENV_VAR}.")
        else:
            info(f"Open a new terminal, or run `source {target.path}`, to pick it up.")

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
        cls,
        base_path: str,
        region: str | None,
        step: StepResult | None = None,
        *,
        account_id: str | None = None,
    ) -> None:
        """Create or connect a project, unless already inside one.

        Args:
            step: Telemetry record for this step, filled in with the outcome and
                a ``created`` / ``connected`` / ``declined`` detail.
            account_id: The account the auth step resolved, so a developer with more
                than one account is not asked to pick it a second time. None when
                authentication was skipped; the project commands then ask.
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
            ProjectCommand.create_project(base_path, region=region, account_id=account_id)
            step.done("created")
        elif choice == "init":
            InitCommand.init_project(base_path, region=region, account_id=account_id)
            step.done("connected")
        else:
            info("Project: skipped. Run 'poly project create' or 'poly init' when you are ready.")
            step.declined("declined")
