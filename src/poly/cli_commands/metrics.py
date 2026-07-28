"""Metrics command family: list, add, edit, and import custom metrics.

Copyright PolyAI Limited
"""

import logging
import os
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction

from ruamel.yaml import YAML, YAMLError

from poly.cli_commands.base import BaseCommand, Parents
from poly.cli_commands.shared import load_project
from poly.handlers.interface import AgentStudioInterface
from poly.output.console import error, plain, print_metrics, success, warning
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

VALID_METRIC_TYPES = ["string", "int", "bool", "float"]


def _parse_bool_flag(value: str) -> bool:
    """Convert a string flag value to a boolean."""
    if value.lower() in ("true", "1", "yes"):
        return True
    if value.lower() in ("false", "0", "no"):
        return False
    raise ValueError(f"Invalid boolean value: {value!r}. Use true/false.")


class MetricsCommand(BaseCommand):
    """Manage custom metrics in the Agent Studio project."""

    command = "metrics"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``metrics`` subcommand tree."""
        metrics_parser = subparsers.add_parser(
            "metrics",
            parents=[parents.verbose],
            help="Manage custom metrics in the Agent Studio project.",
            description=(
                "Manage custom metrics in the Agent Studio project.\n\n"
                "Examples:\n"
                "  poly metrics list\n"
                "  poly metrics add --name SCORE --type int --description 'CSAT Score'\n"
                "  poly metrics edit CSAT_OFFERED --no-active\n"
                "  poly metrics import metrics.yaml"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_subcommand", required=True)

        # ── list ────────────────────────────────────────────────────────
        metrics_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json],
            help="List all custom metrics in the project.",
            description="List all custom metrics for the current project.",
            formatter_class=RawTextHelpFormatter,
        )

        # ── add ─────────────────────────────────────────────────────────
        add_parser = metrics_subparsers.add_parser(
            "add",
            parents=[parents.path, parents.json],
            help="Create a new custom metric.",
            description=(
                "Create a new custom metric. Required fields prompt\n"
                "interactively when omitted.\n\n"
                "Examples:\n"
                "  poly metrics add --name CALL_DURATION --type int"
                " --description 'Duration in seconds'\n"
                "  poly metrics add  # interactive mode\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        add_parser.add_argument(
            "--name",
            type=str,
            help="Metric name (max 50 characters).",
        )
        add_parser.add_argument(
            "--type",
            type=str,
            dest="metric_type",
            choices=VALID_METRIC_TYPES,
            help="Metric value type: string, int, bool, or float.",
        )
        add_parser.add_argument(
            "--description",
            type=str,
            default=None,
            help="Optional description for the metric.",
        )
        add_parser.add_argument(
            "--api",
            action="store_true",
            default=False,
            help="Mark as an API metric.",
        )
        add_parser.add_argument(
            "--expected-values",
            type=str,
            nargs="+",
            default=None,
            help="Expected values (only valid for string type).",
        )

        # ── edit ────────────────────────────────────────────────────────
        edit_parser = metrics_subparsers.add_parser(
            "edit",
            parents=[parents.path, parents.json],
            help="Update an existing custom metric.",
            description=(
                "Update an existing custom metric. At least one flag required.\n\n"
                "Examples:\n"
                "  poly metrics edit CARRIER_ID --description 'Carrier handling the shipment'\n"
                "  poly metrics edit CSAT_OFFERED --active false\n"
                "  poly metrics edit SCORE --api\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        edit_parser.add_argument(
            "name",
            type=str,
            help="Name of the metric to edit.",
        )
        edit_parser.add_argument(
            "--description",
            type=str,
            default=None,
            help="New description for the metric.",
        )
        edit_parser.add_argument(
            "--api",
            type=_parse_bool_flag,
            nargs="?",
            const=True,
            default=None,
            help="Set API flag (true/false). Omit value to set true.",
        )
        edit_parser.add_argument(
            "--active",
            type=_parse_bool_flag,
            nargs="?",
            const=True,
            default=None,
            help="Set active state (true/false). Omit value to set true.",
        )
        edit_parser.add_argument(
            "--expected-values",
            type=str,
            nargs="+",
            default=None,
            help="Expected values (only valid for string type).",
        )

        # ── import ──────────────────────────────────────────────────────
        import_parser = metrics_subparsers.add_parser(
            "import",
            parents=[parents.path, parents.json],
            help="Bulk-import metrics from a YAML file.",
            description=(
                "Bulk-import metrics from a YAML file. Creates metrics that\n"
                "don't already exist and skips those that do. Never deletes.\n\n"
                "Examples:\n"
                "  poly metrics import metrics.yaml\n"
                "  poly metrics import metrics.yaml --dry-run\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        import_parser.add_argument(
            "file",
            type=str,
            help="Path to the YAML file to import.",
        )
        import_parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created/skipped without making changes.",
        )

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Dispatch to the matching metrics sub-handler."""
        if args.metrics_subcommand == "list":
            cls.metrics_list(args.path, output_json=args.json)
        elif args.metrics_subcommand == "add":
            cls.metrics_add(
                args.path,
                name=args.name,
                metric_type=args.metric_type,
                description=args.description,
                api=args.api,
                expected_values=args.expected_values,
                output_json=args.json,
            )
        elif args.metrics_subcommand == "edit":
            cls.metrics_edit(
                args.path,
                name=args.name,
                description=args.description,
                api=args.api,
                active=args.active,
                expected_values=args.expected_values,
                output_json=args.json,
            )
        elif args.metrics_subcommand == "import":
            cls.metrics_import(
                args.path,
                file_path=args.file,
                dry_run=args.dry_run,
                output_json=args.json,
            )

    # ── sub-handlers ────────────────────────────────────────────────

    @classmethod
    def metrics_list(cls, base_path: str, output_json: bool = False) -> None:
        """List all custom metrics for the project."""
        project = load_project(base_path, output_json=output_json)
        metrics = AgentStudioInterface.get_custom_metrics(
            project.region, project.account_id, project.project_id
        )

        if output_json:
            json_print(metrics)
        else:
            print_metrics(metrics)

    @classmethod
    def metrics_add(
        cls,
        base_path: str,
        name: str | None = None,
        metric_type: str | None = None,
        description: str | None = None,
        api: bool = False,
        expected_values: list[str] | None = None,
        output_json: bool = False,
    ) -> None:
        """Create a new custom metric."""
        project = load_project(base_path, output_json=output_json)

        if name is None:
            if output_json:
                json_print({"success": False, "error": "--name is required when using --json."})
                sys.exit(1)
            name = input("Metric name: ").strip()
            if not name:
                error("Metric name is required.")
                sys.exit(1)

        if metric_type is None:
            if output_json:
                json_print({"success": False, "error": "--type is required when using --json."})
                sys.exit(1)
            metric_type = input(f"Type ({'/'.join(VALID_METRIC_TYPES)}): ").strip()
            if metric_type not in VALID_METRIC_TYPES:
                error(
                    f"Invalid type '{metric_type}'. Must be one of: {', '.join(VALID_METRIC_TYPES)}"
                )
                sys.exit(1)

        if description is None and not output_json:
            description = input("Description (optional): ").strip() or None

        if api is False and not output_json:
            api_input = input("API metric? (y/N): ").strip().lower()
            api = api_input in ("y", "yes")

        data: dict = {"name": name, "type": metric_type}
        if description:
            data["description"] = description
        if api:
            data["api"] = True
        if expected_values:
            data["expected_values"] = expected_values

        result = AgentStudioInterface.create_custom_metric(
            project.region, project.account_id, project.project_id, data
        )

        if output_json:
            json_print({"success": True, "metric": result})
        else:
            success(f"Created metric {name} ({metric_type})")

    @classmethod
    def metrics_edit(
        cls,
        base_path: str,
        name: str,
        description: str | None = None,
        api: bool | None = None,
        active: bool | None = None,
        expected_values: list[str] | None = None,
        output_json: bool = False,
    ) -> None:
        """Update an existing custom metric."""
        project = load_project(base_path, output_json=output_json)

        data: dict = {}
        if description is not None:
            data["description"] = description
        if api is not None:
            data["api"] = api
        if active is not None:
            data["active"] = active
        if expected_values is not None:
            data["expected_values"] = expected_values

        if not data:
            msg = "At least one flag is required (--description, --api, --active, etc.)."
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        result = AgentStudioInterface.update_custom_metric(
            project.region, project.account_id, project.project_id, name, data
        )

        if output_json:
            json_print({"success": True, "metric": result})
        else:
            if data.get("active") is False:
                success(f"Deactivated metric {name}")
            else:
                success(f"Updated metric {name}")

    @classmethod
    def metrics_import(
        cls,
        base_path: str,
        file_path: str,
        dry_run: bool = False,
        output_json: bool = False,
    ) -> None:
        """Bulk-import metrics from a YAML file."""
        project = load_project(base_path, output_json=output_json)

        if not os.path.exists(file_path):
            msg = f"File not found: {file_path}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        with open(file_path) as f:
            yaml_content = f.read()

        try:
            ry = YAML()
            local_metrics = ry.load(yaml_content) or {}
        except YAMLError as e:
            msg = f"Invalid YAML: {e}"
            if output_json:
                json_print({"success": False, "error": msg})
            else:
                error(msg)
            sys.exit(1)

        local_names = set(local_metrics.keys())

        # Fetch current remote metrics for the no-delete warning
        remote_metrics = AgentStudioInterface.get_custom_metrics(
            project.region, project.account_id, project.project_id
        )
        remote_names = {m["name"] for m in remote_metrics if "name" in m}
        missing_from_file = remote_names - local_names

        if dry_run:
            cls._print_dry_run(local_names, remote_names, missing_from_file, output_json)
            return

        # Warn about metrics not in the file
        if missing_from_file and not output_json:
            warning(
                f"Metrics on remote but not in file (not deleted):"
                f" {', '.join(sorted(missing_from_file))}"
            )

        import_result = AgentStudioInterface.import_custom_metrics(
            project.region,
            project.account_id,
            project.project_id,
            yaml_content,
            dry_run=False,
        )

        if output_json:
            json_print({"success": True, **import_result})
        else:
            metadata = import_result.get("metadata", {})
            created = metadata.get("created", [])
            ignored = metadata.get("ignored", [])

            if created:
                plain(f"Created: {', '.join(created)}")
            if ignored:
                plain(f"Skipped (already exist): {', '.join(ignored)}")

            created_count = len(created)
            skipped_count = len(ignored)
            success(f"Imported {created_count} metrics ({skipped_count} skipped)")

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _print_dry_run(
        local_names: set[str],
        remote_names: set[str],
        missing_from_file: set[str],
        output_json: bool,
    ) -> None:
        """Display the results of a dry-run import."""
        would_create = local_names - remote_names
        would_skip = local_names & remote_names

        result = {
            "dry_run": True,
            "would_create": sorted(would_create),
            "would_skip": sorted(would_skip),
            "remote_only": sorted(missing_from_file),
        }

        if output_json:
            json_print(result)
        else:
            plain("[dim]Dry run — no changes will be made.[/dim]")
            if would_create:
                plain(f"Would create: {', '.join(sorted(would_create))}")
            if would_skip:
                plain(f"Would skip (already exist): {', '.join(sorted(would_skip))}")
            if missing_from_file:
                warning(
                    f"Metrics on remote but not in file (will NOT be deleted):"
                    f" {', '.join(sorted(missing_from_file))}"
                )
