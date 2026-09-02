"""Auth command family: start and login.

Copyright PolyAI Limited
"""

import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from pathlib import Path

from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import (
    PACKAGE_NAME,
    get_available_versions,
    get_latest_version,
    get_package_version,
    is_newer_version,
)
from poly.constants import POLY_HOME_DIR
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

UPDATE_CHECK_INTERVAL_SECONDS = 12 * 60 * 60
UPDATE_CHECK_STAMP_FILE = Path(POLY_HOME_DIR) / ".update_check"
# Every command pays this, so it must be short enough to go unnoticed on a bad
# connection. The 'poly update' command itself uses the far more generous default.
UPDATE_CHECK_TIMEOUT_SECONDS = 2


class UpdateCommand(BaseCommand):
    """Update the Poly CLI to the latest version."""

    command = "update"

    group = GETTING_STARTED_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``update`` subcommand."""
        update_parser = subparsers.add_parser(
            "update",
            parents=[parents.verbose, parents.debug, parents.json],
            formatter_class=RawTextHelpFormatter,
            help="Update the Poly CLI to the latest version.",
            description=(
                "Update the Poly CLI to the latest version.\n\n"
                "Examples:\n"
                "  poly update\n"
                "  poly update --check\n"
                "  poly update --to 0.52.0\n"
            ),
        )

        update_parser.add_argument(
            "--check",
            action="store_true",
            help="Check for updates without installing them.",
        )

        # Deliberately not --version: the root parser already uses that to print the
        # installed version and exit, so reusing the name here would read as a typo.
        update_parser.add_argument(
            "--to",
            metavar="VERSION",
            help="Install a specific version instead of the latest, e.g. --to 0.52.0.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Run the update command."""
        cls.update(args.check, args.json, args.to)

    @classmethod
    def update(cls, check: bool, output_json: bool, target_version: str | None = None) -> None:
        """Update the Poly CLI to the latest version, or to ``target_version`` if given."""
        from poly.output.console import info, success

        if target_version:
            # An explicit target skips the "is anything newer" gate below, so that
            # reinstalling the current version and downgrading both work.
            if not cls.check_version_exists(target_version, output_json):
                # Asking for a version that does not exist is a usage error, unlike
                # the "nothing to do" paths below, which are advisory and exit 0.
                sys.exit(1)
            target = target_version
        else:
            update_available, target = cls.check_for_updates()
            if not update_available:
                if output_json:
                    json_print({"update_available": False, "latest_version": target})
                else:
                    info("Poly CLI is already up to date, no update needed.")
                    info(f"Current version: {get_package_version()}")
                return

        if check:
            if output_json:
                json_print({"update_available": True, "latest_version": target})
            else:
                info(f"Update available: {get_package_version()} -> {target}")
            return

        if not output_json:
            info(f"Updating Poly CLI to version {target}...")
        if not cls.perform_update(output_json, target_version):
            return
        if output_json:
            json_print({"success": True, "latest_version": target})
        else:
            success(f"Poly CLI updated to version {target}.")

    @staticmethod
    def check_for_updates() -> tuple[bool, str]:
        """Check whether a newer Poly CLI release is available on PyPI.

        Returns:
            Whether an update is available, and the latest version string.
        """
        latest_version = get_latest_version()
        return is_newer_version(latest_version, get_package_version()), latest_version

    @staticmethod
    def check_version_exists(target_version: str, output_json: bool) -> bool:
        """Check that ``target_version`` is a real polyai-adk release on PyPI.

        Args:
            target_version: The version requested via ``--to``.
            output_json: If True, report failure as JSON instead of a message.

        Returns:
            True if the version can be installed.
        """
        from poly.output.console import error

        versions = get_available_versions()
        if not versions:
            # PyPI is unreachable, so there is nothing to validate against. Let the
            # installer resolve the version and report its own error, rather than
            # blocking a version that is very likely valid.
            return True
        if target_version in versions:
            return True

        message = (
            f"Version '{target_version}' not found on PyPI. "
            f"Recent versions: {', '.join(reversed(versions[-5:]))}"
        )
        if output_json:
            json_print({"success": False, "error": message})
        else:
            error(message)
        return False

    @staticmethod
    def _is_editable_install() -> bool:
        """Check whether polyai-adk is installed in editable/dev mode (e.g. ``pip install -e .``).

        Returns:
            True if installed editable, per the PEP 610 ``direct_url.json`` marker.
        """
        from importlib.metadata import distribution

        # Deliberately broad: unreadable or malformed metadata should make this fall
        # back to "not editable" rather than crash the whole command. The guard is a
        # safety check, so failing it must not be worse than not having it.
        try:
            direct_url_text = distribution(PACKAGE_NAME).read_text("direct_url.json")
            if not direct_url_text:
                return False
            direct_url = json.loads(direct_url_text)
        except Exception:
            return False
        return bool(direct_url.get("dir_info", {}).get("editable", False))

    @staticmethod
    def tool_install_method() -> str | None:
        """Detect a standalone tool install (``uv tool`` / ``pipx``) from ``sys.prefix``.

        Deliberately cheap — string comparisons only, no metadata lookups or PATH
        scans — because the startup update check calls this on every command.

        Returns:
            "uv-tool" or "pipx" if the CLI is installed as a standalone tool, else
            None. None covers project installs, where the version is the project's
            business rather than something the user should be nagged about.
        """
        prefix = sys.prefix.replace("\\", "/")
        if "/uv/tools/" in prefix:
            return "uv-tool"
        if "/pipx/venvs/" in prefix:
            return "pipx"
        return None

    @classmethod
    def _detect_install_method(cls) -> str:
        """Detect how the Poly CLI was installed, based on the active interpreter's prefix.

        Returns:
            One of "editable", "ephemeral", "uv-tool", "pipx", "uv-pip", or "pip".
        """
        if cls._is_editable_install():
            return "editable"
        prefix = sys.prefix.replace("\\", "/")
        # uv's throwaway environments (uvx, uv run --with) live in versioned cache
        # directories, e.g. ~/.cache/uv/archive-v0/<hash>. The version suffixes are
        # bumped by uv over time, so match the shape rather than exact names.
        if re.search(r"/(archive|builds|environments)-v\d+/", prefix):
            return "ephemeral"
        tool_method = cls.tool_install_method()
        if tool_method:
            return tool_method
        if shutil.which("uv"):
            return "uv-pip"
        return "pip"

    @staticmethod
    def _upgrade_command(method: str, target_version: str | None) -> list[str]:
        """Build the install command for an upgradable install method.

        Args:
            method: An upgradable method returned by ``_detect_install_method``.
            target_version: An explicit version to install, or None for the latest.

        Returns:
            The command to run.
        """
        if target_version is None:
            return {
                "uv-tool": ["uv", "tool", "upgrade", PACKAGE_NAME],
                "pipx": ["pipx", "upgrade", PACKAGE_NAME],
                "uv-pip": ["uv", "pip", "install", "--upgrade", PACKAGE_NAME],
                "pip": [sys.executable, "-m", "pip", "install", "--upgrade", PACKAGE_NAME],
            }[method]

        # A pinned spec selects the version outright, so "--upgrade" is dropped: it is
        # redundant, and the "upgrade" subcommands will not move backwards, which would
        # rule out downgrades.
        spec = f"{PACKAGE_NAME}=={target_version}"
        return {
            "uv-tool": ["uv", "tool", "install", "--force", spec],
            "pipx": ["pipx", "install", "--force", spec],
            "uv-pip": ["uv", "pip", "install", spec],
            "pip": [sys.executable, "-m", "pip", "install", spec],
        }[method]

    @classmethod
    def perform_update(cls, output_json: bool, target_version: str | None = None) -> bool:
        """Perform the update, to ``target_version`` if given, otherwise to the latest."""
        from poly.output.console import error, warning

        # Installs that 'poly update' must not touch: upgrading in place would either
        # clobber a dev checkout or write to an environment that is about to be discarded.
        not_upgradable = {
            "editable": (
                f"{PACKAGE_NAME} is installed in editable/dev mode; run 'git pull' in "
                "your checkout instead of 'poly update'."
            ),
            "ephemeral": (
                f"{PACKAGE_NAME} is running from a temporary environment (uvx or uv "
                f"run); there is nothing to update. Run 'uvx {PACKAGE_NAME}@latest' to "
                "use the newest version."
            ),
        }

        method = cls._detect_install_method()
        if method in not_upgradable:
            message = not_upgradable[method]
            if output_json:
                json_print({"success": False, "error": message})
            else:
                warning(message)
            return False

        command = cls._upgrade_command(method, target_version)

        try:
            subprocess.run(command, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            message = f"Update failed ({' '.join(command)}): {e}"
            if output_json:
                json_print({"success": False, "error": message})
            else:
                error(message)
            sys.exit(1)
        return True


def _update_check_is_due() -> bool:
    """Check whether enough time has passed since the last startup update check."""
    try:
        last_checked = float(UPDATE_CHECK_STAMP_FILE.read_text().strip())
    except (OSError, ValueError):
        return True
    if not math.isfinite(last_checked):
        # float() accepts "inf" and "nan", either of which would make the comparison
        # below permanently False and silence the check for good. A stamp we cannot
        # trust should mean "check now", the same as a missing or unreadable one.
        return True
    return (time.time() - last_checked) > UPDATE_CHECK_INTERVAL_SECONDS


def _record_update_check() -> None:
    """Stamp the current time so the next check is deferred."""
    try:
        UPDATE_CHECK_STAMP_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATE_CHECK_STAMP_FILE.write_text(str(time.time()))
    except OSError:
        pass


def display_update_message(output_json: bool = False) -> None:
    """Tell the user about a newer release, at most once per check interval.

    Only standalone tool installs are notified. A project install's version is
    pinned by that project's manifest, so telling the user to upgrade it would be
    advice that the next dependency sync silently undoes.

    Never raises: a failure here must not break the command the user actually ran.

    Args:
        output_json: True if the command is producing machine-readable output.
    """
    try:
        # Cheapest checks first, so the common case costs almost nothing: no output
        # to corrupt, then a string comparison, then a small file read, and only
        # then the network.
        if output_json or not sys.stdout.isatty():
            return
        if os.environ.get("POLY_NO_UPDATE_CHECK"):
            return
        method = UpdateCommand.tool_install_method()
        if method is None:
            return
        if not _update_check_is_due():
            return

        latest_version = get_latest_version(timeout=UPDATE_CHECK_TIMEOUT_SECONDS)
        if latest_version == "unknown":
            # PyPI did not answer. Leave the stamp alone so the next run retries,
            # rather than letting a blip buy hours of silence.
            return
        _record_update_check()

        current_version = get_package_version()
        if not is_newer_version(latest_version, current_version):
            return

        from poly.output.console import plain

        plain(f"\n[warning]Update available: {current_version} -> {latest_version}[/warning]")
        plain("[muted]Run 'poly update' to install it.[/muted]\n")
    except Exception as e:
        logger.debug(f"Update check failed: {e}")
