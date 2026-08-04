"""Functions command family: manage Functions via the public Functions REST API.

Scoped to the project's current branch. Distinct from the local-file/decorator
Functions (``poly/resources/function.py``) synced via ``poly push``/``poly pull``.

Copyright PolyAI Limited
"""

import json
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any, Optional

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.handlers.platform_api import FunctionConflictError
from poly.output.json_output import json_print


class FunctionsCommand(BaseCommand):
    """Manage Functions via the public Functions REST API."""

    command = "functions"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``functions`` subcommand tree."""
        functions_parser = subparsers.add_parser(
            "functions",
            parents=[parents.verbose],
            help="Manage Functions via the public Functions REST API.",
            description=(
                "Manage Functions via the public Functions REST API, scoped to the\n"
                "project's current branch.\n\n"
                "Examples:\n"
                "  poly functions list\n"
                "  poly functions get <function_id>\n"
                "  poly functions create --name my_func --description 'desc' --code-file func.py\n"
                "  poly functions execute <function_id> --args '{\"x\": 1}'\n"
                "  poly functions deploy\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        functions_subparsers = functions_parser.add_subparsers(
            dest="functions_subcommand", required=True
        )

        list_parser = functions_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose],
            help="List functions on the current branch.",
            description=(
                "List the Functions defined on the project's current branch.\n\n"
                "Examples:\n"
                "  poly functions list\n"
                "  poly functions list --limit 50 --offset 50\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        list_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Max number of functions to return (1-50). Defaults to 20.",
        )
        list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of functions to skip. Defaults to 0.",
        )

        get_parser = functions_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Get a single function by ID.",
            description=(
                "Show a function's metadata, parameters and code.\n\n"
                "Examples:\n"
                "  poly functions get <function_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        get_parser.add_argument("function_id", type=str, help="The function ID.")

        create_parser = functions_subparsers.add_parser(
            "create",
            parents=[parents.path, parents.json, parents.verbose],
            help="Create a new function.",
            description=(
                "Create a new Function on the current branch from a local code file.\n\n"
                "Examples:\n"
                "  poly functions create --name my_func --description 'desc' \\\n"
                "      --code-file func.py\n"
                "  poly functions create --name my_func --description 'desc' \\\n"
                '      --code-file func.py --parameters \'[{"name": "x", "type": "str", '
                '"description": "an x"}]\'\n'
            ),
            formatter_class=RawTextHelpFormatter,
        )
        create_parser.add_argument("--name", type=str, required=True, help="The function name.")
        create_parser.add_argument(
            "--description", type=str, required=True, help="The function description."
        )
        create_parser.add_argument(
            "--code-file",
            type=str,
            required=True,
            metavar="FILE",
            dest="code_file",
            help="Local path to the function's Python source.",
        )
        create_parser.add_argument(
            "--parameters",
            type=str,
            default=None,
            help=(
                "JSON list of parameter specs, e.g. "
                '\'[{"name": "x", "type": "str", "description": "an x"}]\'.'
            ),
        )

        update_parser = functions_subparsers.add_parser(
            "update",
            parents=[parents.path, parents.json, parents.verbose],
            help="Update an existing function.",
            description=(
                "Update a Function's name, description, code or parameters. At least\n"
                "one field must be supplied.\n\n"
                "Examples:\n"
                "  poly functions update <function_id> --code-file func.py\n"
                "  poly functions update <function_id> --description 'new desc'\n"
                "  poly functions update <function_id> --name renamed --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        update_parser.add_argument("function_id", type=str, help="The function ID.")
        update_parser.add_argument("--name", type=str, default=None, help="New function name.")
        update_parser.add_argument(
            "--description", type=str, default=None, help="New function description."
        )
        update_parser.add_argument(
            "--code-file",
            type=str,
            default=None,
            metavar="FILE",
            dest="code_file",
            help="Local path to the replacement Python source.",
        )
        update_parser.add_argument(
            "--parameters", type=str, default=None, help="JSON list of parameter specs."
        )
        update_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Override an orphaned-reference conflict (leaves flow steps pointing at nothing).",
        )

        delete_parser = functions_subparsers.add_parser(
            "delete",
            parents=[parents.path, parents.json, parents.verbose],
            help="Delete a function.",
            description=(
                "Delete a Function from the current branch.\n\n"
                "Examples:\n"
                "  poly functions delete <function_id>\n"
                "  poly functions delete <function_id> --force\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        delete_parser.add_argument("function_id", type=str, help="The function ID.")
        delete_parser.add_argument(
            "--force",
            "-f",
            action="store_true",
            help="Override an orphaned-reference conflict (leaves flow steps pointing at nothing).",
        )

        execute_parser = functions_subparsers.add_parser(
            "execute",
            parents=[parents.path, parents.json, parents.verbose],
            help="Execute a function with the given arguments.",
            description=(
                "Execute a Function and print its return value, logs and runtime.\n\n"
                "Examples:\n"
                "  poly functions execute <function_id>\n"
                "  poly functions execute <function_id> --args '{\"x\": 1}'\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        execute_parser.add_argument("function_id", type=str, help="The function ID.")
        execute_parser.add_argument(
            "--args",
            type=str,
            default="{}",
            help="JSON object of arguments to pass to the function. Defaults to {}.",
        )

        duplicate_parser = functions_subparsers.add_parser(
            "duplicate",
            parents=[parents.path, parents.json, parents.verbose],
            help="Duplicate a function.",
            description=(
                "Copy a Function on the current branch.\n\n"
                "Examples:\n"
                "  poly functions duplicate <function_id>\n"
                "  poly functions duplicate <function_id> --name my_func_copy\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        duplicate_parser.add_argument("function_id", type=str, help="The function ID to copy.")
        duplicate_parser.add_argument(
            "--name",
            type=str,
            default=None,
            help="Name for the copy. Defaults to a server-generated name.",
        )

        functions_subparsers.add_parser(
            "deploy",
            parents=[parents.path, parents.json, parents.verbose],
            help="Deploy all draft functions on the current branch.",
            description=(
                "Deploy every draft Function on the current branch.\n\n"
                "Examples:\n"
                "  poly functions deploy\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        functions_subparsers.add_parser(
            "validate",
            parents=[parents.path, parents.json, parents.verbose],
            help="Validate all functions on the current branch.",
            description=(
                "Check every Function on the current branch for syntax errors and\n"
                "orphaned flow-step references.\n\n"
                "Examples:\n"
                "  poly functions validate\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        references_parser = functions_subparsers.add_parser(
            "references",
            parents=[parents.path, parents.json, parents.verbose],
            help="Show flow steps that reference a function.",
            description=(
                "List the flow steps that call a Function.\n\n"
                "Examples:\n"
                "  poly functions references <function_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        references_parser.add_argument("function_id", type=str, help="The function ID.")

        type_definitions_parser = functions_subparsers.add_parser(
            "type-definitions",
            parents=[parents.path, parents.json, parents.verbose],
            help="Show Python type stubs for a function, for IDE autocomplete.",
            description=(
                "Print the Conversation/Flow type stubs available to a Function, for\n"
                "IDE autocomplete.\n\n"
                "Examples:\n"
                "  poly functions type-definitions <function_id>\n"
                "  poly functions type-definitions <function_id> > stubs.py\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        type_definitions_parser.add_argument("function_id", type=str, help="The function ID.")

        functions_subparsers.add_parser(
            "deployments",
            parents=[parents.path, parents.json, parents.verbose],
            help="List function deployment history across environments.",
            description=(
                "Show the deployment history for the project's Functions.\n\n"
                "Examples:\n"
                "  poly functions deployments\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        start_parser = functions_subparsers.add_parser(
            "start",
            parents=[parents.verbose],
            help="Manage the branch's start_function.",
            description=(
                "Read or replace the branch's start_function.\n\n"
                "Examples:\n"
                "  poly functions start get\n"
                "  poly functions start update --code-file start.py\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        start_subparsers = start_parser.add_subparsers(
            dest="functions_start_subcommand", required=True
        )
        start_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Get the branch's start_function code.",
        )
        start_update_parser = start_subparsers.add_parser(
            "update",
            parents=[parents.path, parents.json, parents.verbose],
            help="Update the branch's start_function code from a local file.",
        )
        start_update_parser.add_argument(
            "--code-file",
            type=str,
            required=True,
            metavar="FILE",
            dest="code_file",
            help="Local path to the replacement start_function source.",
        )

        end_parser = functions_subparsers.add_parser(
            "end",
            parents=[parents.verbose],
            help="Manage the branch's end_function.",
            description=(
                "Read or replace the branch's end_function.\n\n"
                "Examples:\n"
                "  poly functions end get\n"
                "  poly functions end update --code-file end.py\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        end_subparsers = end_parser.add_subparsers(dest="functions_end_subcommand", required=True)
        end_subparsers.add_parser(
            "get",
            parents=[parents.path, parents.json, parents.verbose],
            help="Get the branch's end_function code.",
        )
        end_update_parser = end_subparsers.add_parser(
            "update",
            parents=[parents.path, parents.json, parents.verbose],
            help="Update the branch's end_function code from a local file.",
        )
        end_update_parser.add_argument(
            "--code-file",
            type=str,
            required=True,
            metavar="FILE",
            dest="code_file",
            help="Local path to the replacement end_function source.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching functions sub-handler."""
        if args.functions_subcommand == "list":
            cls.functions_list(
                args.path,
                limit=args.limit,
                offset=args.offset,
                output_json=args.json,
            )
        elif args.functions_subcommand == "get":
            cls.functions_get(args.path, args.function_id, output_json=args.json)
        elif args.functions_subcommand == "create":
            cls.functions_create(
                args.path,
                args.name,
                args.description,
                args.code_file,
                parameters=args.parameters,
                output_json=args.json,
            )
        elif args.functions_subcommand == "update":
            cls.functions_update(
                args.path,
                args.function_id,
                name=args.name,
                description=args.description,
                code_file=args.code_file,
                parameters=args.parameters,
                force=args.force,
                output_json=args.json,
            )
        elif args.functions_subcommand == "delete":
            cls.functions_delete(
                args.path,
                args.function_id,
                force=args.force,
                output_json=args.json,
            )
        elif args.functions_subcommand == "execute":
            cls.functions_execute(
                args.path,
                args.function_id,
                args.args,
                output_json=args.json,
            )
        elif args.functions_subcommand == "duplicate":
            cls.functions_duplicate(
                args.path,
                args.function_id,
                name=args.name,
                output_json=args.json,
            )
        elif args.functions_subcommand == "deploy":
            cls.functions_deploy(args.path, output_json=args.json)
        elif args.functions_subcommand == "validate":
            cls.functions_validate(args.path, output_json=args.json)
        elif args.functions_subcommand == "references":
            cls.functions_references(args.path, args.function_id, output_json=args.json)
        elif args.functions_subcommand == "type-definitions":
            cls.functions_type_definitions(args.path, args.function_id, output_json=args.json)
        elif args.functions_subcommand == "deployments":
            cls.functions_deployments(args.path, output_json=args.json)
        elif args.functions_subcommand == "start":
            if args.functions_start_subcommand == "get":
                cls.functions_start_get(args.path, output_json=args.json)
            elif args.functions_start_subcommand == "update":
                cls.functions_start_update(args.path, args.code_file, output_json=args.json)
        elif args.functions_subcommand == "end":
            if args.functions_end_subcommand == "get":
                cls.functions_end_get(args.path, output_json=args.json)
            elif args.functions_end_subcommand == "update":
                cls.functions_end_update(args.path, args.code_file, output_json=args.json)

    @staticmethod
    def _handle_conflict(e: FunctionConflictError, output_json: bool) -> None:
        """Report a Functions API 409 conflict and exit non-zero.

        Args:
            e: The conflict raised by the handler layer.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import console, error

        if output_json:
            json_print(
                {
                    "success": False,
                    "error": str(e),
                    "orphaned_references": e.orphaned_references,
                }
            )
        else:
            error(str(e))
            for ref in e.orphaned_references:
                console.print(f"  [error]-[/error] {ref}")
        sys.exit(1)

    @staticmethod
    def _read_code_file(code_file: str, output_json: bool) -> str:
        """Read a local Python source file, exiting with a clear error if unreadable.

        Args:
            code_file: Path to the source file.
            output_json: If True, emit machine-readable JSON.

        Returns:
            The file's contents.
        """
        from poly.output.console import error

        try:
            with open(code_file, "r", encoding="utf-8") as f:
                return f.read()
        except OSError as e:
            msg = f"Could not read code file {code_file}: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

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
    def functions_list(
        cls,
        base_path: str,
        limit: int = 20,
        offset: int = 0,
        output_json: bool = False,
    ) -> None:
        """List functions on the project's current branch.

        Args:
            base_path: Base path for the project.
            limit: Max number of functions to return.
            offset: Number of functions to skip.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, print_functions

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.list_functions(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            limit=limit,
            offset=offset,
        )
        functions = result.get("functions", [])

        if output_json:
            json_print(result)
        else:
            if not functions:
                info("No functions found.")
                return
            print_functions(functions)

    @classmethod
    def functions_get(cls, base_path: str, function_id: str, output_json: bool = False) -> None:
        """Show a single function by ID.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_function_detail

        project = load_project(base_path, output_json=output_json)
        function = AgentStudioInterface.get_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            function_id=function_id,
        )

        if output_json:
            json_print(function)
        else:
            print_function_detail(function)

    @classmethod
    def functions_create(
        cls,
        base_path: str,
        name: str,
        description: str,
        code_file: str,
        parameters: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Create a new function from a local code file.

        Args:
            base_path: Base path for the project.
            name: The function name.
            description: The function description.
            code_file: Local path to the function's Python source.
            parameters: Optional JSON list of parameter specs.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        code = cls._read_code_file(code_file, output_json)
        parsed_parameters = (
            cls._parse_json_arg(parameters, "--parameters", output_json) if parameters else None
        )

        try:
            function = AgentStudioInterface.create_function(
                region=project.region,
                project_id=project.project_id,
                branch_id=project.branch_id,
                name=name,
                description=description,
                code=code,
                parameters=parsed_parameters,
            )
        except FunctionConflictError as e:
            cls._handle_conflict(e, output_json)
            return

        if output_json:
            json_print(function)
        else:
            success(
                f"Created function [bold]{function.get('name')}[/bold] "
                f"({function.get('function_id')})"
            )

    @classmethod
    def functions_update(
        cls,
        base_path: str,
        function_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        code_file: Optional[str] = None,
        parameters: Optional[str] = None,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Update an existing function.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            name: New function name.
            description: New function description.
            code_file: Local path to the replacement Python source.
            parameters: JSON list of parameter specs.
            force: Override an orphaned-reference conflict.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import error, success

        project = load_project(base_path, output_json=output_json)

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if code_file is not None:
            updates["code"] = cls._read_code_file(code_file, output_json)
        if parameters is not None:
            updates["parameters"] = cls._parse_json_arg(parameters, "--parameters", output_json)

        if not updates:
            msg = "No updates provided. Pass at least one of --name, --description, --code-file or --parameters."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        try:
            function = AgentStudioInterface.update_function(
                region=project.region,
                project_id=project.project_id,
                branch_id=project.branch_id,
                function_id=function_id,
                updates=updates,
                force=force,
            )
        except FunctionConflictError as e:
            cls._handle_conflict(e, output_json)
            return

        if output_json:
            json_print(function)
        else:
            success(
                f"Updated function [bold]{function.get('name')}[/bold] "
                f"({function.get('function_id')})"
            )

    @classmethod
    def functions_delete(
        cls,
        base_path: str,
        function_id: str,
        force: bool = False,
        output_json: bool = False,
    ) -> None:
        """Delete a function.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            force: Override an orphaned-reference conflict.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)

        try:
            AgentStudioInterface.delete_function(
                region=project.region,
                project_id=project.project_id,
                branch_id=project.branch_id,
                function_id=function_id,
                force=force,
            )
        except FunctionConflictError as e:
            cls._handle_conflict(e, output_json)
            return

        if output_json:
            json_print({"success": True, "function_id": function_id})
        else:
            success(f"Deleted function {function_id}.")

    @classmethod
    def functions_execute(
        cls,
        base_path: str,
        function_id: str,
        args_json: str = "{}",
        output_json: bool = False,
    ) -> None:
        """Execute a function with the given JSON arguments.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            args_json: JSON object of arguments to pass.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import console

        project = load_project(base_path, output_json=output_json)
        args = cls._parse_json_arg(args_json, "--args", output_json)

        result = AgentStudioInterface.execute_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
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
    def functions_duplicate(
        cls,
        base_path: str,
        function_id: str,
        name: Optional[str] = None,
        output_json: bool = False,
    ) -> None:
        """Duplicate a function, optionally with a new name.

        Args:
            base_path: Base path for the project.
            function_id: The function ID to copy.
            name: Name for the copy.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)

        try:
            function = AgentStudioInterface.duplicate_function(
                region=project.region,
                project_id=project.project_id,
                branch_id=project.branch_id,
                function_id=function_id,
                name=name,
            )
        except FunctionConflictError as e:
            cls._handle_conflict(e, output_json)
            return

        if output_json:
            json_print(function)
        else:
            success(
                f"Duplicated function as [bold]{function.get('name')}[/bold] "
                f"({function.get('function_id')})"
            )

    @classmethod
    def functions_deploy(cls, base_path: str, output_json: bool = False) -> None:
        """Deploy all draft functions on the current branch.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.deploy_functions(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
        )

        if output_json:
            json_print(result)
        else:
            success(f"Deployed functions (version {result.get('deployment_version', 'unknown')}).")

    @classmethod
    def functions_validate(cls, base_path: str, output_json: bool = False) -> None:
        """Validate all functions on the current branch.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_function_validation_issues

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.validate_functions(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
        )

        if output_json:
            json_print(result)
        else:
            print_function_validation_issues(result.get("valid", False), result.get("issues", []))

    @classmethod
    def functions_references(
        cls, base_path: str, function_id: str, output_json: bool = False
    ) -> None:
        """Show the flow steps that reference a function.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_function_references

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.get_function_references(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            function_id=function_id,
        )

        if output_json:
            json_print(result)
        else:
            print_function_references(result.get("references", []))

    @classmethod
    def functions_type_definitions(
        cls, base_path: str, function_id: str, output_json: bool = False
    ) -> None:
        """Show Python type stubs for a function, for IDE autocomplete.

        Args:
            base_path: Base path for the project.
            function_id: The function ID.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_code

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.get_function_type_definitions(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            function_id=function_id,
        )

        if output_json:
            json_print(result)
        else:
            print_code(result.get("code", ""), line_numbers=False)

    @classmethod
    def functions_deployments(cls, base_path: str, output_json: bool = False) -> None:
        """List function deployment history across environments.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import info, print_function_deployments

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.list_function_deployments(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
        )
        deployments = result.get("deployments", [])

        if output_json:
            json_print(result)
        else:
            if not deployments:
                info("No function deployments found.")
                return
            print_function_deployments(deployments)

    @classmethod
    def functions_start_get(cls, base_path: str, output_json: bool = False) -> None:
        """Show the branch's start_function code.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_code

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.get_start_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
        )

        if output_json:
            json_print(result)
        else:
            print_code(result.get("code", ""))

    @classmethod
    def functions_start_update(
        cls, base_path: str, code_file: str, output_json: bool = False
    ) -> None:
        """Update the branch's start_function code from a local file.

        Args:
            base_path: Base path for the project.
            code_file: Local path to the replacement source.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        code = cls._read_code_file(code_file, output_json)

        result = AgentStudioInterface.update_start_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            code=code,
        )

        if output_json:
            json_print(result)
        else:
            success("Updated start_function.")

    @classmethod
    def functions_end_get(cls, base_path: str, output_json: bool = False) -> None:
        """Show the branch's end_function code.

        Args:
            base_path: Base path for the project.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import print_code

        project = load_project(base_path, output_json=output_json)
        result = AgentStudioInterface.get_end_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
        )

        if output_json:
            json_print(result)
        else:
            print_code(result.get("code", ""))

    @classmethod
    def functions_end_update(
        cls, base_path: str, code_file: str, output_json: bool = False
    ) -> None:
        """Update the branch's end_function code from a local file.

        Args:
            base_path: Base path for the project.
            code_file: Local path to the replacement source.
            output_json: If True, emit machine-readable JSON.
        """
        from poly.output.console import success

        project = load_project(base_path, output_json=output_json)
        code = cls._read_code_file(code_file, output_json)

        result = AgentStudioInterface.update_end_function(
            region=project.region,
            project_id=project.project_id,
            branch_id=project.branch_id,
            code=code,
        )

        if output_json:
            json_print(result)
        else:
            success("Updated end_function.")
