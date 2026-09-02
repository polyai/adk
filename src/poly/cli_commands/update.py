"""Auth command family: start and login.

Copyright PolyAI Limited
"""

import json
import re
import shutil
import subprocess
import sys
from argparse import ArgumentParser, Namespace, _SubParsersAction

from poly.cli_commands.base import GETTING_STARTED_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import get_latest_version, get_package_version
from poly.output.json_output import json_print


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
            help="Update the Poly CLI to the latest version.",
            description=(
                "Update the Poly CLI to the latest version.\n\nExamples:\n  poly update\n"
            ),
        )

        update_parser.add_argument(
            "--check",
            action="store_true",
            help="Check for updates without installing them.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Run the update command."""
        cls.update(args.check, args.json)

    @classmethod
    def update(cls, check: bool, output_json: bool) -> None:
        """Update the Poly CLI to the latest version."""
        from poly.output.console import info, success

        update_available, latest_version = cls.check_for_updates(output_json)
        if check:
            if output_json:
                json_print({"update_available": update_available, "latest_version": latest_version})
            else:
                info(f"Update available: {'Yes' if update_available else 'No'}")
                info(f"Latest version: {latest_version}")
        if not update_available:
            if not output_json:
                info("Poly CLI is already up to date, no update needed.")
                info(f"Current version: {get_package_version()}")
            else:
                json_print({"success": True, "latest_version": latest_version})
            return

        if not output_json:
            info(f"Updating Poly CLI to version {latest_version}...")
        updated = cls.perform_update(output_json)
        if not updated:
            return
        if not output_json:
            success(f"Poly CLI updated to version {latest_version}.")
        else:
            json_print({"success": True, "latest_version": latest_version})

    @staticmethod
    def check_for_updates(output_json: bool) -> tuple[bool, str]:
        """Check if an update is available for the Poly CLI."""
        current_version = get_package_version()
        latest_version = get_latest_version()
        update_available = latest_version != "unknown" and latest_version != current_version

        return update_available, latest_version

    @staticmethod
    def _is_editable_install() -> bool:
        """Check whether polyai-adk is installed in editable/dev mode (e.g. ``pip install -e .``).

        Returns:
            True if installed editable, per the PEP 610 ``direct_url.json`` marker.
        """
        from importlib.metadata import PackageNotFoundError, distribution

        try:
            direct_url_text = distribution("polyai-adk").read_text("direct_url.json")
        except PackageNotFoundError:
            return False
        if not direct_url_text:
            return False
        direct_url = json.loads(direct_url_text)
        return bool(direct_url.get("dir_info", {}).get("editable", False))

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
        if "/uv/tools/" in prefix:
            return "uv-tool"
        if "/pipx/venvs/" in prefix:
            return "pipx"
        if shutil.which("uv"):
            return "uv-pip"
        return "pip"

    @classmethod
    def perform_update(cls, output_json: bool) -> bool:
        """Perform the update to the latest version."""
        from poly.output.console import error, warning

        # Installs that 'poly update' must not touch: upgrading in place would either
        # clobber a dev checkout or write to an environment that is about to be discarded.
        not_upgradable = {
            "editable": (
                "polyai-adk is installed in editable/dev mode; run 'git pull' in your "
                "checkout instead of 'poly update'."
            ),
            "ephemeral": (
                "polyai-adk is running from a temporary environment (uvx or uv run); "
                "there is nothing to update. Run 'uvx polyai-adk@latest' to use the "
                "newest version."
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

        commands = {
            "uv-tool": ["uv", "tool", "upgrade", "polyai-adk"],
            "pipx": ["pipx", "upgrade", "polyai-adk"],
            "uv-pip": ["uv", "pip", "install", "--upgrade", "polyai-adk"],
            "pip": [sys.executable, "-m", "pip", "install", "--upgrade", "polyai-adk"],
        }
        command = commands[method]

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
