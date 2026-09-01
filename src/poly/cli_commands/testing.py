"""Testing command family: run, list, and show test results.

Copyright PolyAI Limited
"""

import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction

from poly.cli_commands.base import PROJECT_SYNC_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.output.json_output import json_print


class TestingCommand(BaseCommand):
    """Manage and run tests for the project."""

    command = "test"

    group = PROJECT_SYNC_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``test`` subcommand tree."""
        test_parser = subparsers.add_parser(
            "test",
            parents=[parents.verbose, parents.debug],
            help="Manage and run tests for the project.",
            description="Manage and run tests for the project.\n\nExamples:\n  poly test\n",
            formatter_class=RawTextHelpFormatter,
        )
        testing_subparsers = test_parser.add_subparsers(dest="test_subcommand", required=True)

        test_run_parser = testing_subparsers.add_parser(
            "run",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="Run tests for the project.",
            description=(
                "Run tests for the project. Runs all tests by default.\n"
                "Use --files or --tag to filter.\n\n"
                "Examples:\n"
                "  poly test run\n"
                "  poly test run --path /path/to/project\n"
                "  poly test run --files test1.yaml test2.yaml\n"
                "  poly test run --tag smoke\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        test_run_parser.add_argument(
            "--files",
            nargs="*",
            help="List of test files to run.",
        )
        test_run_parser.add_argument(
            "--tag",
            type=str,
            nargs="*",
            help="Run tests with the specified tag(s).",
        )
        test_run_parser.add_argument(
            "--dont-poll",
            action="store_true",
            help="Do not poll for test results.",
        )
        test_run_parser.add_argument(
            "--push",
            action="store_true",
            help="Push the project before running tests.",
        )
        test_run_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the tests that would be run without triggering them.",
        )

        test_get_parser = testing_subparsers.add_parser(
            "show",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="View test run results.",
            description=(
                "Get test run results.\n\n"
                "Examples:\n"
                "  poly test show <run_id>\n"
                "  poly test show <run_id> <test_case_id>\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        test_get_parser.add_argument(
            "run_id",
            type=str,
            help="The test run ID.",
        )
        test_get_parser.add_argument(
            "test_case_id",
            type=str,
            nargs="?",
            default=None,
            help="Optional test case ID for detailed view.",
        )

        test_list_parser = testing_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json, parents.verbose, parents.debug],
            help="List test runs.",
            description=(
                "List test runs.\n\n"
                "Examples:\n"
                "  poly test list\n"
                "  poly test list --limit 10 --offset 5\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        test_list_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of test runs to list. Defaults to 10.",
        )
        test_list_parser.add_argument(
            "--offset",
            type=int,
            default=0,
            help="Number of test runs to skip. Defaults to 0.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching test sub-handler."""
        if args.test_subcommand == "run":
            cls.testing_run(
                args.path,
                files=args.files,
                tags=args.tag,
                dont_poll=args.dont_poll,
                push=args.push,
                output_json=args.json,
                dry_run=args.dry_run,
            )
        elif args.test_subcommand == "show":
            cls.testing_show(
                args.path,
                run_id=args.run_id,
                test_case_id=args.test_case_id,
                output_json=args.json,
            )
        elif args.test_subcommand == "list":
            cls.testing_list(
                args.path,
                limit=args.limit,
                offset=args.offset,
                output_json=args.json,
            )

    @classmethod
    def testing_run(
        cls,
        base_path: str,
        files: list[str],
        tags: list[str] = None,
        dont_poll: bool = False,
        push: bool = False,
        output_json: bool = False,
        dry_run: bool = False,
    ) -> None:
        """Run tests for the project."""
        from poly.output.console import error, info, plain, poll_test_run_live, success

        project = load_project(base_path)

        json_output = {}

        if dry_run:
            matched = project.resolve_tests(files=files, tags=tags)
            if output_json:
                json_print(
                    {
                        "success": True,
                        "test_count": len(matched),
                        "tests": [{"resource_id": t.resource_id, "name": t.name} for t in matched],
                    }
                )
            else:
                info(f"Would run {len(matched)} test{'s' if len(matched) != 1 else ''}:")
                for test in matched:
                    plain(f"  - {test.name} ({test.resource_id})")
            return

        if push:
            if not output_json:
                info("Pushing project before running tests...")
            push_success, output, _ = project.push_project(
                force=False,
                skip_validation=False,
                dry_run=False,
                format=False,
            )
            if output == "No changes detected":
                push_success = True

            if push_success:
                if not output_json:
                    success("Project pushed successfully.")
                else:
                    json_output["push"] = {"success": True, "message": output}
            else:
                if output_json:
                    json_output["push"] = {
                        "success": False,
                        "message": "Failed to push project before running tests.",
                        "error": output,
                    }
                    json_print(json_output)
                else:
                    error(
                        f"Failed to push {project.account_id}/{project.project_id} to Agent Studio."
                    )
                    plain(output)
                sys.exit(1)

        matched = project.resolve_tests(files=files, tags=tags)
        test_ids = [t.resource_id for t in matched]

        if not output_json:
            info(f"Running tests for {project.account_id}/{project.project_id}...")

        test_info = project.trigger_tests(test_ids)
        test_run_id = test_info.get("id")

        if output_json:
            json_output["test_run"] = test_info
            json_output["success"] = True
            json_print(json_output)
            return

        test_count = test_info.get("test_case_count", "?")
        success(
            f"Triggered test run [bold]{test_run_id}[/bold] "
            f"({test_count} test{'s' if test_count != 1 else ''})"
        )

        if dont_poll:
            info(
                f"Use [bold]poly test show {test_run_id}[/bold] to check the status of the test run."
            )
            return

        poll_test_run_live(project.get_test_run, test_run_id, matched)

    @classmethod
    def testing_list(
        cls,
        base_path: str,
        limit: int = 10,
        offset: int = 0,
        output_json: bool = False,
    ) -> None:
        """List test runs."""
        from poly.output.console import paged_output, print_test_run_list

        project = load_project(base_path)
        result = project.list_test_runs(limit=limit, offset=offset)

        if output_json:
            json_print({"success": True, "test_runs": result})
            return

        with paged_output():
            print_test_run_list(result)

    @classmethod
    def testing_show(
        cls,
        base_path: str,
        run_id: str,
        test_case_id: str = None,
        output_json: bool = False,
    ) -> None:
        """Show test run results, optionally for a specific test case."""
        from poly.output.console import error, print_test_detail, print_test_run_summary

        project = load_project(base_path)
        result = project.get_test_run(run_id)

        if output_json:
            if test_case_id:
                test_history = result.get("testHistory") or []
                entry = next(
                    (e for e in test_history if e.get("testCaseId") == test_case_id),
                    None,
                )
                if not entry:
                    json_print({"success": False, "error": f"Test case {test_case_id} not found"})
                    sys.exit(1)
                json_print({"success": True, "test": entry})
            else:
                json_print({"success": True, "test_run": result})
            return

        if test_case_id:
            test_history = result.get("testHistory") or []
            entry = next(
                (e for e in test_history if e.get("testCaseId") == test_case_id),
                None,
            )
            if not entry:
                error(f"Test case {test_case_id} not found in run {run_id}")
                sys.exit(1)
            print_test_detail(entry)
        else:
            print_test_run_summary(result)
