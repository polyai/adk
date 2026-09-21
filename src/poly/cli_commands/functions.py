"""Functions command family: manage Functions via the public Functions REST API.

Scoped to the project's current branch. Distinct from the local-file/decorator
Functions (``poly/resources/function.py``) synced via ``poly push``/``poly pull``.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Optional

from poly.cli_commands.base import (
    BUILDER_API_GROUP,
    BaseCommand,
    GroupedRawTextHelpFormatter,
    Parents,
    add_grouped_subparsers,
    group_subcommands,
)
from poly.cli_commands.shared import resolve_project_scope
from poly.handlers.interface import AgentStudioInterface
from poly.output.json_output import json_print

# Section header for `poly functions --help`. CRUD, duplication and the
# start/end lifecycle hooks live in the local-file/decorator Functions
# mechanism (synced via push/pull); this command family only covers what
# that mechanism can't do: running and inspecting functions via the REST API.
FUNCTIONS_RUN_GROUP = "Run and inspect"

FUNCTIONS_SUBCOMMAND_GROUP_ORDER = [
    FUNCTIONS_RUN_GROUP,
]

FUNCTIONS_SUBCOMMAND_GROUPS = {
    "execute": FUNCTIONS_RUN_GROUP,
    "validate": FUNCTIONS_RUN_GROUP,
}


class FunctionsCommand(BaseCommand):
    """Manage Functions via the public Functions REST API."""

    command = "functions"

    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``functions`` subcommand tree."""
        functions_parser = subparsers.add_parser(
            "functions",
            parents=[parents.verbose],
            help="Manage Functions via the public Functions REST API.",
            description=(
                "Manage Functions via the public Functions REST API, scoped to the\n"
                "project's current branch. Creating, editing and deleting functions is\n"
                "still done via the local-file/decorator workflow (poly push/poly pull);\n"
                "this covers what that workflow can't: running and validating\n"
                "functions.\n\n"
                "Examples:\n"
                "  poly functions execute <function_name> --args '{\"x\": 1}'\n"
                "  poly functions validate\n"
            ),
            formatter_class=GroupedRawTextHelpFormatter,
        )

        functions_subparsers = add_grouped_subparsers(
            functions_parser, dest="functions_subcommand", metavar="<subcommand>"
        )

        execute_parser = functions_subparsers.add_parser(
            "execute",
            parents=[parents.path, parents.scope, parents.json, parents.verbose],
            help="Execute a function with the given arguments.",
            description=(
                "Execute a Function and print its return value, logs and runtime.\n\n"
                "Examples:\n"
                "  poly functions execute <function_name>\n"
                "  poly functions execute <function_name> --args '{\"x\": 1}'\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        execute_parser.add_argument("function", type=str, help="The function name or ID.")
        execute_parser.add_argument(
            "--args",
            type=str,
            default="{}",
            help="JSON object of arguments to pass to the function. Defaults to {}.",
        )

        functions_subparsers.add_parser(
            "validate",
            parents=[parents.path, parents.scope, parents.json, parents.verbose],
            help="Validate all functions on the current branch.",
            description=(
                "Check every Function on the current branch for syntax errors and\n"
                "orphaned flow-step references.\n\n"
                "Examples:\n"
                "  poly functions validate\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        group_subcommands(
            functions_subparsers, FUNCTIONS_SUBCOMMAND_GROUPS, FUNCTIONS_SUBCOMMAND_GROUP_ORDER
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching functions sub-handler."""
        scope = dict(region=args.region, project_id=args.project_id, branch_id=args.branch_id)
        if args.functions_subcommand == "execute":
            cls.functions_execute(
                args.path,
                args.function,
                args.args,
                output_json=args.json,
                **scope,
            )
        elif args.functions_subcommand == "validate":
            cls.functions_validate(args.path, output_json=args.json, **scope)

    @staticmethod
    def _parse_json_arg(value: str, flag: str, output_json: bool) -> Any:
        """Parse a JSON-valued CLI flag, exiting with a clear error if invalid.

        Args:
            value: The raw flag value.
            flag: The flag name, for the error message.
            output_json: If True, emit machine-readable JSON.

        Returns:
            The parsed JSON value.
        """
        from poly.output.console import error

        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON in {flag}: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

    @classmethod
    def _resolve_function_id(
        cls,
        region: str,
        project_id: str,
        branch_id: str,
        function: str,
        output_json: bool,
    ) -> str:
        """Resolve a function name or ID, as given on the command line, to its ID.

        Function IDs aren't surfaced anywhere a user would copy them from, so
        subcommands that take a function accept its name instead (or its ID,
        for scripts that already have one).

        Args:
            region: The region name.
            project_id: The project ID (agent ID).
            branch_id: The branch ID.
            function: The function name or ID.
            output_json: If True, emit machine-readable JSON on error.

        Returns:
            The resolved function ID.
        """
        from poly.output.console import error

        functions = AgentStudioInterface.list_functions(
            region=region, project_id=project_id, branch_id=branch_id
        )
        for candidate in functions:
            if function in (candidate.get("id"), candidate.get("name")):
                return candidate["id"]

        msg = f"No function named or with ID '{function}' found on this branch."
        if output_json:
            json_print({"success": False, "error": msg})
        else:
            error(msg)
        sys.exit(1)

    @classmethod
    def functions_execute(
        cls,
        base_path: str,
        function: str,
        args_json: str = "{}",
        output_json: bool = False,
        region: Optional[str] = None,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> None:
        """Execute a function with the given JSON arguments.

        Args:
            base_path: Base path for the project.
            function: The function name or ID.
            args_json: JSON object of arguments to pass.
            output_json: If True, emit machine-readable JSON.
            region: Explicit region, bypassing the local project.
            project_id: Explicit project ID, bypassing the local project.
            branch_id: Explicit branch ID, bypassing the local project.
        """
        from poly.output.console import console

        region, project_id, branch_id = resolve_project_scope(
            base_path, region, project_id, branch_id, output_json=output_json
        )
        args = cls._parse_json_arg(args_json, "--args", output_json)
        function_id = cls._resolve_function_id(region, project_id, branch_id, function, output_json)

        result = AgentStudioInterface.execute_function(
            region=region,
            project_id=project_id,
            branch_id=branch_id,
            function_id=function_id,
            args=args,
        )

        if output_json:
            json_print(result)
        else:
            console.print(f"Runtime: {result.get('runtime', 0)}ms")
            for log_line in result.get("logs", []):
                console.print(f"[muted]{log_line}[/muted]")
            console.print(json.dumps(result.get("body", {}), indent=2))

    @classmethod
    def functions_validate(
        cls,
        base_path: str,
        output_json: bool = False,
        region: Optional[str] = None,
        project_id: Optional[str] = None,
        branch_id: Optional[str] = None,
    ) -> None:
        """Validate all functions on the current branch.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
            region: Explicit region, bypassing the local project.
            project_id: Explicit project ID, bypassing the local project.
            branch_id: Explicit branch ID, bypassing the local project.
        """
        from poly.output.console import print_function_validation_issues

        region, project_id, branch_id = resolve_project_scope(
            base_path, region, project_id, branch_id, output_json=output_json
        )
        result = AgentStudioInterface.validate_functions(
            region=region,
            project_id=project_id,
            branch_id=branch_id,
        )

        if output_json:
            json_print(result)
        else:
            print_function_validation_issues(result.get("valid", False), result.get("issues", []))
