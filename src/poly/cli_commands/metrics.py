"""Metrics command family: list, add, edit, and import custom metrics.

Copyright PolyAI Limited
"""

import logging
import sys
from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction
from typing import Any

import requests
from ruamel.yaml import YAML

from poly.cli_commands.base import BUILDER_API_GROUP, BaseCommand, Parents
from poly.cli_commands.shared import (
    DATA_AGGS,
    DATA_GROUP_BY,
    DATA_INTERVALS,
    add_cohort_arguments,
    add_window_arguments,
    default_window,
    describe_data_api_error,
    load_project,
    parse_datetime_flag,
    parse_filter_flags,
    parse_having_flags,
    parse_sort_flag,
)
from poly.output.console import (
    error,
    plain,
    print_aggregate,
    print_available_metrics,
    print_metrics,
    success,
    warning,
)
from poly.output.json_output import json_print

logger = logging.getLogger(__name__)

VALID_METRIC_TYPES = ["string", "int", "bool", "float"]
SCORE_METRIC = "poly_score"
SCORE_DEFAULT_DAYS = 7


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
    group = BUILDER_API_GROUP

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``metrics`` subcommand tree."""
        metrics_parser = subparsers.add_parser(
            "metrics",
            parents=[parents.verbose],
            help="Manage custom metrics in the Agent Studio project.",
            description=(
                "Manage custom metrics in the Agent Studio project.\n\n"
                "Define custom metrics (list, add, edit, import, export) and read\n"
                "metric values (available, query, score).\n\n"
                "Examples:\n"
                "  poly metrics list\n"
                "  poly metrics add --name SCORE --type int --description 'CSAT Score'\n"
                "  poly metrics edit CSAT_OFFERED --active false\n"
                "  poly metrics import metrics.yaml\n"
                "  poly metrics available\n"
                "  poly metrics score --interval weekly\n"
                "  poly metrics query duration --agg avg --agg p95 --by channel"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_subcommand", required=True)

        metrics_subparsers.add_parser(
            "list",
            parents=[parents.path, parents.json],
            help="List the custom metrics defined in the project.",
            description=(
                "List the custom metrics defined in the current project.\n\n"
                "For every metric you can query, built-in ones such as poly_score\n"
                "included, use `poly metrics available`."
            ),
            formatter_class=RawTextHelpFormatter,
        )

        metrics_subparsers.add_parser(
            "available",
            parents=[parents.path, parents.json],
            help="Show the metrics you can query, including built-in ones such as poly_score.",
            description=(
                "Show every metric you can query for the current project: built-in\n"
                "metrics such as poly_score and duration, plus the custom metrics\n"
                "defined in the project. These are the names `poly metrics query`\n"
                "and the conversation search filters accept.\n\n"
                "Examples:\n"
                "  poly metrics available\n"
                "  poly metrics available --json"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        query_parser = metrics_subparsers.add_parser(
            "query",
            parents=[parents.path, parents.json],
            help="Aggregate a metric's values over a time window (experimental API).",
            description=(
                "Aggregate one metric over a time window, optionally bucketed by\n"
                "interval and grouped by channel, environment, deployment or variant.\n"
                "Metric names come from `poly metrics available`. Backed by the\n"
                "experimental metrics aggregate endpoint of the Data API.\n\n"
                "Examples:\n"
                "  poly metrics query poly_score --agg avg --from 2026-09-01 --to 2026-09-30\n"
                "  poly metrics query duration --agg avg --agg p95 --interval daily --by channel\n"
                "  poly metrics query CSAT --agg avg --filter channel eq VOICE-SIP"
                " --having avg gte 4\n"
                "  poly metrics query poly_score --agg conversation_count --by value_string\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        query_parser.add_argument("metric", type=str, help="Metric name (case-insensitive).")
        query_parser.add_argument(
            "--agg",
            action="append",
            choices=DATA_AGGS,
            default=None,
            help="Aggregation to compute. Repeatable. Defaults to avg and conversation_count.",
        )
        cls._add_query_arguments(query_parser)

        score_parser = metrics_subparsers.add_parser(
            "score",
            parents=[parents.path, parents.json],
            help="Poly Score for the project over a window (default: last 7 days, daily).",
            description=(
                "Average Poly Score and conversation count for the current project.\n"
                "Shortcut for `poly metrics query poly_score --agg avg --agg\n"
                "conversation_count`. Defaults to the last 7 days bucketed daily.\n\n"
                "Examples:\n"
                "  poly metrics score\n"
                "  poly metrics score --interval weekly --from 2026-09-01\n"
                "  poly metrics score --by channel --env live\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        cls._add_query_arguments(score_parser, score=True)

        export_parser = metrics_subparsers.add_parser(
            "export",
            parents=[parents.path, parents.json],
            help="Export all custom metrics as YAML.",
            description=(
                "Export all custom metrics as YAML.\n\n"
                "Examples:\n"
                "  poly metrics export\n"
                "  poly metrics export metrics.yaml\n"
            ),
            formatter_class=RawTextHelpFormatter,
        )
        export_parser.add_argument(
            "file",
            nargs="?",
            default=None,
            type=str,
            help="Output file path. Prints to stdout when omitted.",
        )

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
            help="Metric name.",
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
        elif args.metrics_subcommand == "available":
            cls.metrics_available(args.path, output_json=args.json)
        elif args.metrics_subcommand == "query":
            cls.metrics_query(args.path, args.metric, args, output_json=args.json)
        elif args.metrics_subcommand == "score":
            cls.metrics_score(args.path, args, output_json=args.json)
        elif args.metrics_subcommand == "export":
            cls.metrics_export(args.path, file_path=args.file, output_json=args.json)
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

    @staticmethod
    def _add_query_arguments(parser: ArgumentParser, score: bool = False) -> None:
        """Register the window, grouping, filter and paging flags shared by query and score."""
        add_window_arguments(
            parser,
            default_help=(
                f"Defaults to {SCORE_DEFAULT_DAYS} days ago."
                if score
                else "Defaults to no lower bound."
            ),
        )
        parser.add_argument(
            "--interval",
            choices=DATA_INTERVALS,
            default="daily" if score else None,
            help=(
                "Time bucket. Defaults to daily." if score else "Time bucket. Omit for one total."
            ),
        )
        parser.add_argument(
            "--timezone",
            type=str,
            default=None,
            metavar="IANA",
            help="Timezone for hourly and daily buckets, e.g. Europe/London.",
        )
        parser.add_argument(
            "--by",
            action="append",
            choices=DATA_GROUP_BY,
            default=None,
            help="Group results by a dimension. Repeatable.",
        )
        add_cohort_arguments(parser, deployments=not score)
        if not score:
            parser.add_argument(
                "--filter",
                action="append",
                nargs=3,
                metavar=("METRIC", "OP", "VALUE"),
                default=None,
                help=(
                    "Only count conversations where METRIC OP VALUE. OP is one of eq, gt, gte,\n"
                    "lt, lte, in, ex, exists (in/ex take a comma-separated list). Repeatable."
                ),
            )
            parser.add_argument(
                "--any",
                action="store_true",
                default=False,
                help="Match conversations that satisfy any filter instead of all.",
            )
            parser.add_argument(
                "--having",
                action="append",
                nargs=3,
                metavar=("AGG", "OP", "VALUE"),
                default=None,
                help="Keep only buckets where AGG OP VALUE, e.g. --having avg gte 4. Repeatable.",
            )
            parser.add_argument(
                "--sort",
                type=str,
                default=None,
                metavar="FIELD[:asc|desc]",
                help="Secondary sort on a --by dimension or an aggregation.",
            )
        parser.add_argument("--limit", type=int, default=20, help="Rows per page, 1 to 100.")
        parser.add_argument("--offset", type=int, default=0, help="Rows to skip, up to 1000.")

    @classmethod
    def metrics_available(cls, base_path: str, output_json: bool = False) -> None:
        """Show the metrics the project can query, built-in metrics included."""
        from poly.output.console import paged_output

        project = load_project(base_path, output_json=output_json)
        try:
            result = project.get_available_metrics()
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e), output_json)

        if output_json:
            json_print(result)
        else:
            with paged_output():
                print_available_metrics(result.get("metrics", []))

    @classmethod
    def metrics_query(
        cls, base_path: str, metric: str, args: Namespace, output_json: bool = False
    ) -> None:
        """Aggregate one metric over a window and print the table."""
        try:
            body = cls._build_query_body(args, metric=metric, aggs=args.agg)
        except ValueError as e:
            cls._fail(str(e), output_json)

        project = load_project(base_path, output_json=output_json)
        try:
            result = project.query_metric(body)
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e), output_json)

        if output_json:
            json_print(result)
        else:
            print_aggregate(result)

    @classmethod
    def metrics_score(cls, base_path: str, args: Namespace, output_json: bool = False) -> None:
        """Poly Score over a window: a headline plus the bucketed table."""
        try:
            body = cls._build_query_body(
                args,
                metric=SCORE_METRIC,
                aggs=["avg", "conversation_count"],
                default_days=SCORE_DEFAULT_DAYS,
            )
        except ValueError as e:
            cls._fail(str(e), output_json)

        project = load_project(base_path, output_json=output_json)
        try:
            result = project.query_metric(body)
        except requests.HTTPError as e:
            cls._fail(describe_data_api_error(e), output_json)

        headline = cls._score_headline(result, body)
        if output_json:
            json_print({**result, "summary": headline})
        else:
            print_aggregate(result, headline=headline["text"])

    @classmethod
    def _build_query_body(
        cls,
        args: Namespace,
        metric: str,
        aggs: list[str] | None,
        default_days: int | None = None,
    ) -> dict[str, Any]:
        """Translate parsed flags into a Data API aggregate request body.

        Raises:
            ValueError: On a malformed date, filter, having or sort flag.
        """
        from_dt = parse_datetime_flag(args.from_dt) if args.from_dt else None
        to_dt = parse_datetime_flag(args.to_dt, exclusive_end=True) if args.to_dt else None
        if default_days is not None and from_dt is None and to_dt is None:
            from_dt, to_dt = default_window(default_days)

        body: dict[str, Any] = {
            "metric": metric,
            "aggs": aggs or ["avg", "conversation_count"],
            "limit": args.limit,
            "offset": args.offset,
        }
        optional = {
            "from_datetime": from_dt,
            "to_datetime": to_dt,
            "interval": getattr(args, "interval", None),
            "timezone": getattr(args, "timezone", None),
            "group_by": getattr(args, "by", None),
            "channel": getattr(args, "channel", None),
            "client_env": getattr(args, "env", None),
            "deployment_id": getattr(args, "deployment", None),
            "variant_id": getattr(args, "variant", None),
            "filters": parse_filter_flags(getattr(args, "filter", None)) or None,
            "having": parse_having_flags(getattr(args, "having", None)) or None,
            "sort": parse_sort_flag(getattr(args, "sort", None)),
        }
        if getattr(args, "any", False):
            optional["filter_operator"] = "or"
        body.update({k: v for k, v in optional.items() if v is not None})
        return body

    @staticmethod
    def _score_headline(result: dict[str, Any], body: dict[str, Any]) -> dict[str, Any]:
        """Summarise a Poly Score result: conversation-weighted average and total count.

        The gateway returns one row per bucket (and group), so the overall
        figure is recomputed here from the rows rather than fetched again.
        """
        columns = result.get("columns") or []
        rows = result.get("rows") or []
        avg_i = columns.index("avg") if "avg" in columns else None
        cnt_i = columns.index("conversation_count") if "conversation_count" in columns else None

        total = 0
        weighted = 0.0
        for row in rows:
            count = row[cnt_i] if cnt_i is not None and row[cnt_i] is not None else 0
            avg = row[avg_i] if avg_i is not None else None
            if avg is not None and count:
                weighted += float(avg) * count
                total += count
        overall = round(weighted / total, 2) if total else None

        window = ""
        if body.get("from_datetime") or body.get("to_datetime"):
            window = f" from {body.get('from_datetime', '…')[:10]} to {body.get('to_datetime', 'now')[:10]}"
        if overall is None:
            text = f"Poly Score{window}: no scored conversations."
        else:
            text = f"Poly Score{window}: {overall} average over {total:,} conversations."
        return {"average": overall, "conversations": total, "text": text}

    @staticmethod
    def _fail(message: str, output_json: bool) -> None:
        """Report an error in the requested format and exit."""
        if output_json:
            json_print({"success": False, "error": message})
        else:
            error(message)
        sys.exit(1)

    @classmethod
    def metrics_list(cls, base_path: str, output_json: bool = False) -> None:
        """List all custom metrics for the project."""
        from poly.output.console import paged_output

        project = load_project(base_path, output_json=output_json)
        metrics = project.get_custom_metrics()

        if output_json:
            json_print(metrics)
        else:
            with paged_output():
                print_metrics(metrics)

    @classmethod
    def metrics_export(
        cls,
        base_path: str,
        file_path: str | None = None,
        output_json: bool = False,
    ) -> None:
        """Export all custom metrics as YAML."""
        project = load_project(base_path, output_json=output_json)
        metrics = project.export_custom_metrics()

        if output_json:
            json_print(metrics)
            return

        ry = YAML()
        if file_path:
            with open(file_path, "w") as f:
                ry.dump(metrics, f)
            success(f"Exported metrics to {file_path}")
        else:
            ry.dump(metrics, sys.stdout)

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
            import questionary

            name = questionary.text("Metric name:").ask()
            if name is None:
                sys.exit(1)
            name = name.strip()
            if not name:
                error("Metric name is required.")
                sys.exit(1)

        if metric_type is None:
            if output_json:
                json_print({"success": False, "error": "--type is required when using --json."})
                sys.exit(1)
            import questionary

            metric_type = questionary.select("Metric type:", choices=VALID_METRIC_TYPES).ask()
            if metric_type is None:
                sys.exit(1)

        if description is None and not output_json:
            import questionary

            desc = questionary.text("Description (optional):").ask()
            if desc is None:
                sys.exit(1)
            description = desc.strip() or None

        if api is False and not output_json:
            import questionary

            api_result = questionary.confirm("API metric?", default=False).ask()
            if api_result is None:
                sys.exit(1)
            api = api_result

        data: dict = {"name": name, "type": metric_type}
        if description:
            data["description"] = description
        if api:
            data["api"] = True
        if expected_values:
            data["expected_values"] = expected_values

        try:
            result = project.create_custom_metric(data)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

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

        if not data and not output_json:
            data = cls._interactive_edit(project, name)
        elif not data:
            msg = "At least one flag is required (--description, --api, --active, etc.)."
            json_print({"success": False, "error": msg})
            sys.exit(1)

        try:
            result = project.update_custom_metric(name, data)
        except ValueError as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if output_json:
            json_print({"success": True, "metric": result})
        else:
            if data.get("active") is False:
                success(f"Deactivated metric {name}")
            else:
                success(f"Updated metric {name}")

    @classmethod
    def _interactive_edit(cls, project: object, name: str) -> dict:
        """Prompt the user to select and edit metric fields interactively.

        Args:
            project: The loaded AgentStudioProject.
            name: Name of the metric to edit.

        Returns:
            A dict of fields to update.
        """
        import questionary

        metrics = project.get_custom_metrics()

        metric = next((m for m in metrics if m.get("name") == name), None)
        if metric is None:
            error(f"Metric {name!r} not found.")
            sys.exit(1)

        is_string = metric.get("type") == "string"

        # Display current values
        plain(f"\n[bold]Current values for {name}:[/bold]")
        plain(f"  name:            {metric.get('name', '—')}")
        plain(f"  type:            {metric.get('type', '—')}")
        plain(f"  description:     {metric.get('description') or '—'}")
        plain(f"  api:             {metric.get('api', False)}")
        plain(f"  active:          {metric.get('active', True)}")
        if is_string:
            ev = metric.get("expected_values") or []
            plain(f"  expected_values: {' '.join(ev) if ev else '—'}")
        plain("")

        choices = ["description", "api", "active"]
        if is_string:
            choices.append("expected_values")

        fields = questionary.checkbox(
            "Which fields do you want to edit?",
            choices=choices,
        ).ask()
        if fields is None:
            sys.exit(1)
        if not fields:
            error("No fields selected.")
            sys.exit(1)

        data: dict = {}

        if "description" in fields:
            val = questionary.text(
                "description:",
                default=metric.get("description") or "",
            ).ask()
            if val is None:
                sys.exit(1)
            data["description"] = val

        if "api" in fields:
            val = questionary.confirm(
                "api:",
                default=metric.get("api", False),
            ).ask()
            if val is None:
                sys.exit(1)
            data["api"] = val

        if "active" in fields:
            val = questionary.confirm(
                "active:",
                default=metric.get("active", True),
            ).ask()
            if val is None:
                sys.exit(1)
            data["active"] = val

        if "expected_values" in fields:
            current = metric.get("expected_values") or []
            val = questionary.text(
                "expected_values (space-separated):",
                default=" ".join(current),
            ).ask()
            if val is None:
                sys.exit(1)
            data["expected_values"] = val.split() if val.strip() else []

        return data

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

        try:
            result = project.import_metrics_from_file(file_path, dry_run)
        except (FileNotFoundError, ValueError) as e:
            if output_json:
                json_print({"success": False, "error": str(e)})
            else:
                error(str(e))
            sys.exit(1)

        if dry_run:
            cls._print_dry_run(result, output_json)
            return

        remote_only = result.get("remote_only", [])
        if remote_only and not output_json:
            warning(f"Metrics on remote but not in file (not deleted): {', '.join(remote_only)}")

        if output_json:
            json_print({"success": True, **result})
        else:
            metadata = result.get("metadata", {})
            created = metadata.get("created", [])
            ignored = metadata.get("ignored", [])

            def _item_name(item: dict[str, str] | str) -> str:
                """Extract name from a metadata item (dict or plain string)."""
                return item["name"] if isinstance(item, dict) else item

            if created:
                plain(f"Created: {', '.join(_item_name(i) for i in created)}")
            if ignored:
                plain(f"Skipped (already exist): {', '.join(_item_name(i) for i in ignored)}")

            created_count = len(created)
            skipped_count = len(ignored)
            success(f"Imported {created_count} metrics ({skipped_count} skipped)")

    # Helper function

    @staticmethod
    def _print_dry_run(
        preview: dict[str, list[str]],
        output_json: bool,
    ) -> None:
        """Display the results of a dry-run import."""
        if output_json:
            json_print({"dry_run": True, **preview})
        else:
            plain("[dim]Dry run — no changes will be made.[/dim]")
            if preview["would_create"]:
                plain(f"Would create: {', '.join(preview['would_create'])}")
            if preview["would_skip"]:
                plain(f"Would skip (already exist): {', '.join(preview['would_skip'])}")
            if preview["remote_only"]:
                warning(
                    f"Metrics on remote but not in file (will NOT be deleted):"
                    f" {', '.join(preview['remote_only'])}"
                )
