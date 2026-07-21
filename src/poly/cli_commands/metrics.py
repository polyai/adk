"""Metrics command family: create, list, and delete GitHub Gist metricss.

Copyright PolyAI Limited
"""

from argparse import ArgumentParser, Namespace, RawTextHelpFormatter, _SubParsersAction

from poly.cli_commands.base import BaseCommand, Parents


class MetricsCommand(BaseCommand):
    """Manage Metrics in the Agent Studio project"""

    command = "metrics"

    @classmethod
    def add_arguments(cls, subparsers: _SubParsersAction[ArgumentParser], parents: Parents) -> None:
        """Register the ``metrics`` subcommand tree."""
        metrics_parser = subparsers.add_parser(
            "metrics",
            parents=[parents.verbose, parents.json],
            help="Manages Metrics in the Agent Studio project.",
            description=(
                "Manage metrics in the Agent Studio project.\n\n"
                "Examples:\n"
                "  poly metrics list\n"
                "  poly metrics add --name SCORE --type int --description 'CSAT Score' \n"
                "  poly metrics edit CSAT_OFFERED --active true \n"
                "  poly metrics edit CARRIER_ID --description 'Carrier handling the shipment' \n"
                "  poly metrics import metrics.yaml"
            ),
            formatter_class=RawTextHelpFormatter,
        )

        metrics_subparsers = metrics_parser.add_subparsers(dest="metrics_subcommand", required=True)

        metrics_list_parser = metrics_subparsers.add_parser(
            "list",
            parents=[parents.json],
            help="Lists all metrics in the project.",
        )
        metrics_list_parser.set_defaults(metrics_subcommand="list")

        metrics_add_parser = metrics_subparsers.add_parser(
            "add",
            parents=[parents.json],
            help="Add new metric to project.",
        )

        metrics_add_parser.add_argument(
            "--name",
            type=str,
            help="Name of metric to add.",
        )

        metrics_add_parser.add_argument(
            "--type",
            type=str,
            choices=["str", "bool", "int"],
            help="Name of metric to add.",
        )

        metrics_add_parser.add_argument(
            "--description",
            type=str,
            help="Description of metric to add.",
        )

        metrics_add_parser.set_defaults(metrics_subcommand="add")

    @classmethod
    def run(cls, args: Namespace) -> None:
        """Manage Metrics in the Agent Studio project."""
        if args.metrics_subcommand == "list":
            cls.list_gists(output_json=args.json)
        elif args.metrics_subcommand == "create":
            cls.metrics(
                base_path=args.path,
                files=args.files,
                version_hash=args.hash,
                before=args.before,
                after=args.after,
                output_json=args.json,
            )

    @classmethod
    def metrics(
        cls,
    ) -> None:
        """Create a GitHub gist for metricsing changes, similar to a pull request."""

    @classmethod
    def metrics_list():
        pass

    @classmethod
    def metrics_add():
        pass

    @classmethod
    def metrics_edit():
        pass

    @classmethod
    def metrics_import():
        pass
