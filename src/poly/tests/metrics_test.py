"""Tests for the metrics CLI commands.

Copyright PolyAI Limited
"""

import json
import os
import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.metrics import VALID_METRIC_TYPES, MetricsCommand, _parse_bool_flag
from poly.cli_commands.shared import (
    describe_data_api_error,
    filter_flags_to_filters,
    having_flags_to_having,
    sort_flag_to_sort,
)
from poly.output.console import console
from poly.project import AgentStudioProject

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_projects", "test_project")
with open(os.path.join(TEST_DIR, "test_project.json"), encoding="utf-8") as _f:
    PROJECT_DATA = json.load(_f)


def _query_args(**overrides) -> Namespace:
    """A Namespace with every query/score flag at its parser default."""
    base = {
        "agg": None,
        "from_dt": None,
        "to_dt": None,
        "interval": None,
        "timezone": None,
        "by": None,
        "channel": None,
        "env": None,
        "deployment": None,
        "variant": None,
        "filter": None,
        "any": False,
        "having": None,
        "sort": None,
        "limit": 20,
        "offset": 0,
    }
    base.update(overrides)
    return Namespace(**base)


def _http_error(status: int, payload=None, text: str = "") -> requests.HTTPError:
    """An HTTPError whose response has the given status and JSON body."""
    response = MagicMock()
    response.status_code = status
    response.text = text
    if payload is None:
        response.json.side_effect = ValueError("no body")
    else:
        response.json.return_value = payload
    return requests.HTTPError(response=response)


class ParseBoolFlagTest(unittest.TestCase):
    """Tests for _parse_bool_flag helper."""

    def test_true_values(self):
        """Accepts 'true', '1', 'yes' (case-insensitive) as True."""
        for val in ("true", "True", "TRUE", "1", "yes", "Yes", "YES"):
            self.assertTrue(_parse_bool_flag(val), f"Expected True for {val!r}")

    def test_false_values(self):
        """Accepts 'false', '0', 'no' (case-insensitive) as False."""
        for val in ("false", "False", "FALSE", "0", "no", "No", "NO"):
            self.assertFalse(_parse_bool_flag(val), f"Expected False for {val!r}")

    def test_invalid_value_raises(self):
        """Raises ValueError for unrecognized strings."""
        with self.assertRaises(ValueError) as ctx:
            _parse_bool_flag("maybe")
        self.assertIn("maybe", str(ctx.exception))

    def test_empty_string_raises(self):
        """Raises ValueError for an empty string."""
        with self.assertRaises(ValueError):
            _parse_bool_flag("")


class MetricsListTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_list."""

    @patch("poly.cli_commands.metrics.print_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_list_calls_print_metrics(self, mock_load, mock_print):
        """metrics_list fetches metrics and prints them in table mode."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = [{"name": "SCORE", "type": "int"}]
        mock_load.return_value = project

        MetricsCommand.metrics_list("/tmp/test", output_json=False)

        project.get_custom_metrics.assert_called_once_with()
        mock_print.assert_called_once_with([{"name": "SCORE", "type": "int"}])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_list_json_output(self, mock_load, mock_json):
        """metrics_list uses json_print when output_json=True."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        metrics = [{"name": "SCORE"}]
        project.get_custom_metrics.return_value = metrics
        mock_load.return_value = project

        MetricsCommand.metrics_list("/tmp/test", output_json=True)

        mock_json.assert_called_once_with(metrics)


class MetricsExportTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_export."""

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_json_output(self, mock_load, mock_json):
        """In JSON mode, export passes the dict straight to json_print."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        data = {"SCORE": {"type": "int"}, "STATUS": {"type": "string"}}
        project.export_custom_metrics.return_value = data
        mock_load.return_value = project

        MetricsCommand.metrics_export("/tmp/test", output_json=True)

        mock_json.assert_called_once_with(data)

    @patch("poly.cli_commands.metrics.load_project")
    def test_export_to_stdout(self, mock_load):
        """Without a file path, YAML is dumped to stdout."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.export_custom_metrics.return_value = {"SCORE": {"type": "int"}}
        mock_load.return_value = project

        with patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls:
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/tmp/test", file_path=None, output_json=False)

            import sys

            mock_ry.dump.assert_called_once_with({"SCORE": {"type": "int"}}, sys.stdout)

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_to_file(self, mock_load, mock_success):
        """With a file path, YAML is written to file and success message shown."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.export_custom_metrics.return_value = {"SCORE": {"type": "int"}}
        mock_load.return_value = project

        with (
            patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls,
            patch("builtins.open", unittest.mock.mock_open()) as mock_file,
        ):
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/tmp/test", file_path="out.yaml", output_json=False)

            mock_file.assert_called_once_with("out.yaml", "w")
            mock_ry.dump.assert_called_once()
            mock_success.assert_called_once()
            self.assertIn("out.yaml", mock_success.call_args[0][0])

    @patch("poly.cli_commands.metrics.load_project")
    def test_export_empty_metrics(self, mock_load):
        """Export with empty dict still dumps without error."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.export_custom_metrics.return_value = {}
        mock_load.return_value = project

        with patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls:
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/tmp/test", output_json=False)

            mock_ry.dump.assert_called_once_with({}, unittest.mock.ANY)


class MetricsAddTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_add."""

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_with_all_args(self, mock_load, mock_success):
        """Non-interactive add passes all fields to project.create_custom_metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.return_value = {"name": "SCORE", "type": "int", "api": True}

        MetricsCommand.metrics_add(
            "/tmp/test",
            name="SCORE",
            metric_type="int",
            description="CSAT Score",
            api=True,
            expected_values=None,
            output_json=False,
        )

        project.create_custom_metric.assert_called_once_with(
            {"name": "SCORE", "type": "int", "description": "CSAT Score", "api": True},
        )
        mock_success.assert_called_once()

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_without_api(self, mock_load, mock_json):
        """When api=False, create is called without the api flag."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.return_value = {"name": "SCORE", "type": "int"}

        MetricsCommand.metrics_add(
            "/tmp/test",
            name="SCORE",
            metric_type="int",
            api=False,
            output_json=True,
        )

        project.create_custom_metric.assert_called_once()
        data = project.create_custom_metric.call_args[0][0]
        self.assertNotIn("api", data)

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_passes_expected_values(self, mock_load, mock_json):
        """Expected values are included in the data dict when provided."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.return_value = {}

        MetricsCommand.metrics_add(
            "/tmp/test",
            name="STATUS",
            metric_type="string",
            description=None,
            api=False,
            expected_values=["open", "closed"],
            output_json=True,
        )

        data = project.create_custom_metric.call_args[0][0]
        self.assertEqual(data["expected_values"], ["open", "closed"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_json_error_when_name_missing(self, mock_load, mock_json):
        """In JSON mode, missing --name prints an error and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_add(
                "/tmp/test",
                name=None,
                metric_type="int",
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_json.assert_called_once()
        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])
        self.assertIn("--name", printed["error"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_json_error_when_type_missing(self, mock_load, mock_json):
        """In JSON mode, missing --type prints an error and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_add(
                "/tmp/test",
                name="SCORE",
                metric_type=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        printed = mock_json.call_args[0][0]
        self.assertIn("--type", printed["error"])

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_expected_values_rejected_for_non_string(self, mock_load, mock_error):
        """Expected values are rejected for non-string metric types."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.side_effect = ValueError(
            "--expected-values is only valid for string metrics."
        )

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_add(
                "/tmp/test",
                name="SCORE",
                metric_type="int",
                description="desc",
                api=True,
                expected_values=["a", "b"],
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()
        self.assertIn("only valid for string", mock_error.call_args[0][0])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_expected_values_rejected_json(self, mock_load, mock_json):
        """In JSON mode, expected values are rejected for non-string types."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.side_effect = ValueError(
            "--expected-values is only valid for string metrics."
        )

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_add(
                "/tmp/test",
                name="SCORE",
                metric_type="int",
                expected_values=["a", "b"],
                output_json=True,
            )

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])
        self.assertIn("only valid for string", printed["error"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_json_output_on_success(self, mock_load, mock_json):
        """In JSON mode, successful add prints success with the metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        result = {"name": "SCORE", "type": "int"}
        project.create_custom_metric.return_value = result

        MetricsCommand.metrics_add(
            "/tmp/test",
            name="SCORE",
            metric_type="int",
            output_json=True,
        )

        mock_json.assert_called_once_with({"success": True, "metric": result})

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_duplicate_metric_friendly_error(self, mock_load, mock_error):
        """409 from the server shows 'already exists' instead of raw HTTP error."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.side_effect = ValueError("Metric 'SCORE' already exists.")

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_add(
                "/tmp/test",
                name="SCORE",
                metric_type="int",
                description="desc",
                api=True,
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("already exists", mock_error.call_args[0][0])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_duplicate_metric_json(self, mock_load, mock_json):
        """409 in JSON mode prints structured error with 'already exists'."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.create_custom_metric.side_effect = ValueError("Metric 'SCORE' already exists.")

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_add(
                "/tmp/test", name="SCORE", metric_type="int", output_json=True
            )

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])
        self.assertIn("already exists", printed["error"])


class MetricsEditTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_edit."""

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_with_description(self, mock_load, mock_success):
        """Editing description passes it through to project.update_custom_metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.return_value = {}

        MetricsCommand.metrics_edit(
            "/tmp/test", name="SCORE", description="New desc", output_json=False
        )

        project.update_custom_metric.assert_called_once_with("SCORE", {"description": "New desc"})

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_deactivate_metric(self, mock_load, mock_success):
        """Setting active=False prints 'Deactivated' message."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.return_value = {}

        MetricsCommand.metrics_edit("/tmp/test", name="SCORE", active=False, output_json=False)

        project.update_custom_metric.assert_called_once_with("SCORE", {"active": False})
        mock_success.assert_called_once()
        self.assertIn("Deactivated", mock_success.call_args[0][0])

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_multiple_flags(self, mock_load, mock_success):
        """Multiple flags are combined into one update call."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.return_value = {}

        MetricsCommand.metrics_edit(
            "/tmp/test",
            name="SCORE",
            description="Updated",
            api=True,
            active=True,
            output_json=False,
        )

        data = project.update_custom_metric.call_args[0][1]
        self.assertEqual(data["description"], "Updated")
        self.assertTrue(data["api"])
        self.assertTrue(data["active"])

    @patch("poly.cli_commands.metrics.MetricsCommand._interactive_edit")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_no_flags_triggers_interactive(self, mock_load, mock_interactive):
        """Enters interactive mode when no flags are provided and not JSON."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_interactive.return_value = {"description": "New desc"}
        project.update_custom_metric.return_value = {"name": "SCORE", "description": "New desc"}

        MetricsCommand.metrics_edit("/tmp/test", name="SCORE", output_json=False)

        mock_interactive.assert_called_once_with(project, "SCORE")
        project.update_custom_metric.assert_called_once()

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_no_flags_json_exits(self, mock_load, mock_json):
        """In JSON mode, no flags prints error JSON and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_edit("/tmp/test", name="SCORE", output_json=True)

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_not_found_friendly_error(self, mock_load, mock_error):
        """404 from the server shows 'not found' instead of raw HTTP error."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.side_effect = ValueError("Metric 'GHOST' not found.")

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_edit(
                "/tmp/test", name="GHOST", description="x", output_json=False
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("not found", mock_error.call_args[0][0])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_not_found_json(self, mock_load, mock_json):
        """404 in JSON mode prints structured error with 'not found'."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.side_effect = ValueError("Metric 'GHOST' not found.")

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_edit(
                "/tmp/test", name="GHOST", description="x", output_json=True
            )

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])
        self.assertIn("not found", printed["error"])

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_expected_values_rejected_for_non_string(self, mock_load, mock_error):
        """Expected values flag is rejected when the metric type is not string."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.update_custom_metric.side_effect = ValueError(
            "--expected-values is only valid for string metrics."
        )

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_edit(
                "/tmp/test",
                name="SCORE",
                expected_values=["a", "b"],
                output_json=False,
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("only valid for string", mock_error.call_args[0][0])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_json_output(self, mock_load, mock_json):
        """In JSON mode, successful edit prints success with the metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        result = {"name": "SCORE", "active": True}
        project.update_custom_metric.return_value = result

        MetricsCommand.metrics_edit("/tmp/test", name="SCORE", active=True, output_json=True)

        mock_json.assert_called_once_with({"success": True, "metric": result})


class InteractiveEditTest(unittest.TestCase):
    """Tests for MetricsCommand._interactive_edit."""

    SAMPLE_METRICS = [
        {
            "name": "SCORE",
            "type": "int",
            "description": "CSAT score",
            "api": False,
            "active": True,
            "expected_values": [],
        },
        {
            "name": "STATUS",
            "type": "string",
            "description": "Call status",
            "api": False,
            "active": True,
            "expected_values": ["open", "closed"],
        },
    ]

    @patch("poly.cli_commands.metrics.error")
    def test_metric_not_found_exits(self, mock_error):
        """Exits with error when the named metric does not exist."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand._interactive_edit(project, "NONEXISTENT")

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()

    @patch("questionary.checkbox")
    def test_metrics_checkbox_cancel_exits(self, mock_checkbox):
        """Exits when user cancels field selection in metrics."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand._interactive_edit(project, "SCORE")

        self.assertEqual(ctx.exception.code, 1)

    @patch("questionary.checkbox")
    def test_no_fields_selected_exits(self, mock_checkbox):
        """Exits when user selects no fields in metrics."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = []

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand._interactive_edit(project, "SCORE")

        self.assertEqual(ctx.exception.code, 1)

    @patch("questionary.text")
    @patch("questionary.checkbox")
    def test_edit_description(self, mock_checkbox, mock_text):
        """Returns updated description when user edits it."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = ["description"]
        mock_text.return_value.ask.return_value = "New description"

        result = MetricsCommand._interactive_edit(project, "SCORE")

        self.assertEqual(result, {"description": "New description"})

    @patch("questionary.confirm")
    @patch("questionary.checkbox")
    def test_edit_api_and_active(self, mock_checkbox, mock_confirm):
        """Returns updated api and active flags."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = ["api", "active"]
        mock_confirm.return_value.ask.side_effect = [True, False]

        result = MetricsCommand._interactive_edit(project, "SCORE")

        self.assertEqual(result, {"api": True, "active": False})

    @patch("questionary.text")
    @patch("questionary.checkbox")
    def test_edit_expected_values_string_metric(self, mock_checkbox, mock_text):
        """Parses space-separated expected values for string metrics."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = ["expected_values"]
        mock_text.return_value.ask.return_value = "low medium high"

        result = MetricsCommand._interactive_edit(project, "STATUS")

        self.assertEqual(result, {"expected_values": ["low", "medium", "high"]})

    @patch("questionary.checkbox")
    def test_no_expected_values_for_non_string(self, mock_checkbox):
        """expected_values is not offered as a choice for non-string metrics."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        project.get_custom_metrics.return_value = self.SAMPLE_METRICS
        mock_checkbox.return_value.ask.return_value = []

        with self.assertRaises(SystemExit):
            MetricsCommand._interactive_edit(project, "SCORE")

        choices = mock_checkbox.call_args[1]["choices"]
        self.assertNotIn("expected_values", choices)


class MetricsImportTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_import."""

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_file_not_found(self, mock_load, mock_error):
        """Exits with error when the import file does not exist."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.import_metrics_from_file.side_effect = FileNotFoundError(
            "File not found: /nonexistent/metrics.yaml"
        )

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_import(
                "/tmp/test", file_path="/nonexistent/metrics.yaml", output_json=False
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()
        self.assertIn("File not found", mock_error.call_args[0][0])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_file_not_found_json(self, mock_load, mock_json):
        """In JSON mode, missing file prints error JSON and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.import_metrics_from_file.side_effect = FileNotFoundError(
            "File not found: /nonexistent/metrics.yaml"
        )

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_import(
                "/tmp/test", file_path="/nonexistent/metrics.yaml", output_json=True
            )

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_invalid_yaml(self, mock_load, mock_error):
        """Exits with error when YAML parsing fails."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.import_metrics_from_file.side_effect = ValueError("Invalid YAML: ...")

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_import("/tmp/test", file_path="bad.yaml", output_json=False)

        self.assertEqual(ctx.exception.code, 1)

    @patch("poly.cli_commands.metrics.load_project")
    def test_import_success(self, mock_load):
        """Successful import calls project.import_metrics_from_file and prints summary."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.import_metrics_from_file.return_value = {
            "remote_only": [],
            "metadata": {"created": ["SCORE"], "ignored": []},
        }

        with patch("poly.cli_commands.metrics.success"), patch("poly.cli_commands.metrics.plain"):
            MetricsCommand.metrics_import("/tmp/test", file_path="metrics.yaml", output_json=False)

        project.import_metrics_from_file.assert_called_once_with("metrics.yaml", False)

    @patch("poly.cli_commands.metrics.load_project")
    def test_import_handles_dict_response_items(self, mock_load):
        """Import correctly extracts names from dict-format metadata items."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        project.import_metrics_from_file.return_value = {
            "remote_only": [],
            "metadata": {
                "created": [{"name": "SCORE", "message": "created"}],
                "ignored": [{"name": "STATUS", "message": "already exists"}],
            },
        }

        with (
            patch("poly.cli_commands.metrics.success") as mock_success,
            patch("poly.cli_commands.metrics.plain") as mock_plain,
        ):
            MetricsCommand.metrics_import("/tmp/test", file_path="m.yaml", output_json=False)

        plain_calls = [c[0][0] for c in mock_plain.call_args_list]
        self.assertTrue(any("SCORE" in c for c in plain_calls))
        self.assertTrue(any("STATUS" in c for c in plain_calls))
        mock_success.assert_called_once()
        self.assertIn("1 metrics", mock_success.call_args[0][0])


class PrintDryRunTest(unittest.TestCase):
    """Tests for MetricsCommand._print_dry_run static method."""

    @patch("poly.cli_commands.metrics.json_print")
    def test_dry_run_json_output(self, mock_json):
        """JSON dry-run output includes would_create, would_skip, remote_only."""
        preview = {
            "would_create": ["A", "C"],
            "would_skip": ["B"],
            "remote_only": ["D"],
        }

        MetricsCommand._print_dry_run(preview, output_json=True)

        result = mock_json.call_args[0][0]
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["would_create"], ["A", "C"])
        self.assertEqual(result["would_skip"], ["B"])
        self.assertEqual(result["remote_only"], ["D"])

    @patch("poly.cli_commands.metrics.warning")
    @patch("poly.cli_commands.metrics.plain")
    def test_dry_run_text_output(self, mock_plain, mock_warning):
        """Text dry-run shows create, skip, and remote-only warnings."""
        preview = {
            "would_create": ["NEW_METRIC"],
            "would_skip": ["EXISTING"],
            "remote_only": ["REMOTE_ONLY"],
        }

        MetricsCommand._print_dry_run(preview, output_json=False)

        calls = [c[0][0] for c in mock_plain.call_args_list]
        self.assertTrue(any("Would create" in c for c in calls))
        self.assertTrue(any("Would skip" in c for c in calls))
        mock_warning.assert_called_once()

    @patch("poly.cli_commands.metrics.plain")
    def test_dry_run_empty_preview(self, mock_plain):
        """With empty lists, only the dim header is printed."""
        preview = {"would_create": [], "would_skip": [], "remote_only": []}

        MetricsCommand._print_dry_run(preview, output_json=False)

        # Only the dim header should be printed
        self.assertEqual(mock_plain.call_count, 1)


class PrintMetricsTest(unittest.TestCase):
    """Tests for print_metrics console output."""

    @patch("poly.output.console.plain")
    def test_empty_metrics(self, mock_plain):
        """Prints 'No metrics found.' when list is empty."""
        from poly.output.console import print_metrics

        print_metrics([])

        mock_plain.assert_called_once_with("No metrics found.")

    @patch("poly.output.console.console")
    def test_renders_table_with_counts(self, mock_console):
        """Renders a table and prints active/inactive summary."""
        from poly.output.console import print_metrics

        metrics = [
            {"name": "SCORE", "type": "int", "active": True, "api": False},
            {"name": "OLD", "type": "string", "active": False, "api": True, "description": "old"},
        ]

        print_metrics(metrics)

        self.assertEqual(mock_console.print.call_count, 2)
        summary = mock_console.print.call_args_list[1][0][0]
        self.assertIn("1 active", summary)
        self.assertIn("1 inactive", summary)


class ValidMetricTypesTest(unittest.TestCase):
    """Tests for the VALID_METRIC_TYPES constant."""

    def test_contains_expected_types(self):
        """All expected metric types are present."""
        self.assertEqual(VALID_METRIC_TYPES, ["string", "int", "bool", "float"])


if __name__ == "__main__":
    unittest.main()


class MetricsReadCommandTest(unittest.TestCase):
    """Base for the read commands: a real fixture project, the mock at the HTTP boundary."""

    def setUp(self):
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, TEST_DIR)
        patch("poly.cli_commands.metrics.load_project", return_value=self.project).start()
        self.mock_request = patch(
            "poly.handlers.platform_api.PlatformAPIHandler.make_request"
        ).start()
        self.addCleanup(patch.stopall)

    def _render(self, fn, *args, **kwargs) -> str:
        # Wide enough that no column truncates, whatever the platform calls UTC.
        with patch.object(console, "_width", 200), console.capture() as capture:
            fn(*args, **kwargs)
        return capture.get()


class MetricsAvailableTest(MetricsReadCommandTest):
    """Tests for MetricsCommand.metrics_available."""

    def test_table_mode_lists_the_catalog_for_the_project(self):
        """The catalog is fetched for the project's region and id, then printed."""
        self.mock_request.return_value = {
            "metrics": [{"name": "poly_score", "type": "float", "description": "Overall score"}],
            "total": 1,
        }

        output = self._render(MetricsCommand.metrics_available, TEST_DIR, output_json=False)

        self.mock_request.assert_called_once_with(
            "us-1", "/api/v1/metrics", "GET", params={"project_id": "test_project"}
        )
        self.assertIn("poly_score", output)
        self.assertIn("Overall score", output)

    @patch("poly.cli_commands.metrics.json_print")
    def test_json_mode_emits_the_raw_response(self, mock_json):
        """JSON mode passes the Data API response through unchanged."""
        self.mock_request.return_value = {"metrics": [], "total": 0}

        MetricsCommand.metrics_available(TEST_DIR, output_json=True)

        mock_json.assert_called_once_with({"metrics": [], "total": 0})

    @patch("poly.cli_commands.metrics.error")
    def test_http_error_is_explained_and_exits(self, mock_error):
        """A Data API error becomes a plain message and a non-zero exit."""
        self.mock_request.side_effect = _http_error(401)

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_available(TEST_DIR, output_json=False)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("poly apikey", mock_error.call_args[0][0])


class MetricsQueryTest(MetricsReadCommandTest):
    """Tests for MetricsCommand.metrics_query."""

    def test_every_flag_reaches_the_request_body(self):
        """Flags map onto the aggregate body under the Data API's field names."""
        self.mock_request.return_value = {"columns": ["avg"], "rows": [[4.2]], "limit": 50}
        args = _query_args(
            agg=["avg", "p95"],
            from_dt="2026-09-01",
            to_dt="2026-09-30",
            interval="daily",
            timezone="Europe/London",
            by=["channel"],
            channel=["VOICE-SIP"],
            env=["live"],
            deployment=["dep1"],
            variant=["var1"],
            filter=[["handoff", "eq", "false"], ["channel", "in", "CHAT, SMS"]],
            any=True,
            having=[["avg", "gte", "4"]],
            sort="avg:desc",
            limit=50,
            offset=100,
        )

        self._render(MetricsCommand.metrics_query, TEST_DIR, "duration", args, output_json=False)

        region, endpoint, method = self.mock_request.call_args.args
        body = self.mock_request.call_args.kwargs["data"]
        self.assertEqual((region, endpoint, method), ("us-1", "/api/v1/metrics/aggregate", "POST"))
        self.assertEqual(
            body,
            {
                "project_id": "test_project",
                "metric": "duration",
                "aggs": ["avg", "p95"],
                "from_datetime": "2026-09-01T00:00:00",
                "to_datetime": "2026-10-01T00:00:00",
                "interval": "daily",
                "timezone": "Europe/London",
                "group_by": ["channel"],
                "channel": ["VOICE-SIP"],
                "client_env": ["live"],
                "deployment_id": ["dep1"],
                "variant_id": ["var1"],
                "filters": [
                    {"metric": "handoff", "op": "eq", "value": False},
                    {"metric": "channel", "op": "in", "value": ["CHAT", "SMS"]},
                ],
                "filter_operator": "or",
                "having": [{"field": "avg", "op": "gte", "value": 4.0}],
                "sort": {"field": "avg", "order": "desc"},
                "limit": 50,
                "offset": 100,
            },
        )

    @patch("poly.cli_commands.metrics.json_print")
    def test_minimal_body_has_defaults_and_no_nulls(self, mock_json):
        """With no flags the body carries the defaults only; nothing is sent as null."""
        self.mock_request.return_value = {"columns": [], "rows": []}

        MetricsCommand.metrics_query(TEST_DIR, "poly_score", _query_args(), output_json=True)

        self.assertEqual(
            self.mock_request.call_args.kwargs["data"],
            {
                "project_id": "test_project",
                "metric": "poly_score",
                "aggs": ["avg", "conversation_count"],
                "limit": 20,
                "offset": 0,
            },
        )
        mock_json.assert_called_once_with({"columns": [], "rows": []})

    @patch("poly.cli_commands.metrics.json_print")
    def test_invalid_flag_fails_before_any_request(self, mock_json):
        """The project's validation stops a bad flag before the API is called."""
        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_query(
                TEST_DIR, "x", _query_args(filter=[["a", "like", "b"]]), output_json=True
            )

        self.mock_request.assert_not_called()
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("like", payload["error"])

    @patch("poly.cli_commands.metrics.error")
    def test_out_of_range_limit_fails_locally(self, mock_error):
        """--limit outside 1 to 100 is refused without a request."""
        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_query(
                TEST_DIR, "poly_score", _query_args(limit=500), output_json=False
            )

        self.mock_request.assert_not_called()
        self.assertIn("Limit", mock_error.call_args[0][0])

    def test_table_mode_prints_the_rows(self):
        """Rows render with the bucket column and formatted numbers."""
        self.mock_request.return_value = {
            "columns": ["bucket", "channel", "avg", "conversation_count"],
            "rows": [["2026-09-01T00:00:00+00:00", "VOICE-SIP", 4.2134, 1318]],
            "limit": 20,
            "offset": 0,
        }

        output = self._render(
            MetricsCommand.metrics_query, TEST_DIR, "duration", _query_args(), output_json=False
        )

        self.assertIn("VOICE-SIP", output)
        self.assertIn("4.21", output)
        self.assertIn("1,318", output)


class MetricsScoreTest(MetricsReadCommandTest):
    """Tests for MetricsCommand.metrics_score."""

    def _responses(self, overall_rows, table_rows):
        """Answer the overall query first, then the bucketed one."""
        self.mock_request.side_effect = [
            {"columns": ["avg", "conversation_count"], "rows": overall_rows, "limit": 1},
            {
                "columns": ["bucket", "avg", "conversation_count"],
                "rows": table_rows,
                "limit": 20,
                "offset": 0,
            },
        ]

    def test_headline_comes_from_a_separate_unbucketed_query(self):
        """The overall figure is fetched without interval or group-by, so paging can't skew it."""
        self._responses([[87.5, 40]], [["2026-09-28T00:00:00", 80.0, 10]])

        output = self._render(
            MetricsCommand.metrics_score,
            TEST_DIR,
            _query_args(interval="daily", by=["channel"], limit=1),
            output_json=False,
        )

        overall_body = self.mock_request.call_args_list[0].kwargs["data"]
        table_body = self.mock_request.call_args_list[1].kwargs["data"]
        self.assertEqual(overall_body["metric"], "poly_score")
        self.assertEqual(overall_body["aggs"], ["avg", "conversation_count"])
        self.assertEqual(overall_body["limit"], 1)
        self.assertNotIn("interval", overall_body)
        self.assertNotIn("group_by", overall_body)
        self.assertEqual(table_body["interval"], "daily")
        self.assertEqual(table_body["group_by"], ["channel"])
        self.assertEqual(table_body["limit"], 1)
        self.assertIn("from_datetime", overall_body)
        self.assertEqual(overall_body["from_datetime"], table_body["from_datetime"])
        self.assertIn("87.5 average over 40 conversations", output)

    def test_headline_shows_the_window_as_given(self):
        """--to 2026-09-30 reads 'to 2026-09-30' although the request end is the next day."""
        self._responses([[4.0, 3]], [])

        output = self._render(
            MetricsCommand.metrics_score,
            TEST_DIR,
            _query_args(interval="daily", from_dt="2026-09-01", to_dt="2026-09-30"),
            output_json=False,
        )

        self.assertIn("from 2026-09-01 to 2026-09-30", output)
        self.assertEqual(
            self.mock_request.call_args_list[0].kwargs["data"]["to_datetime"],
            "2026-10-01T00:00:00",
        )

    @patch("poly.cli_commands.metrics.json_print")
    def test_json_includes_summary(self, mock_json):
        """JSON output carries the summary next to the table."""
        self._responses([], [])

        MetricsCommand.metrics_score(TEST_DIR, _query_args(interval="daily"), output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertIsNone(payload["summary"]["average"])
        self.assertEqual(payload["summary"]["conversations"], 0)
        self.assertIn("no scored conversations", payload["summary"]["text"])
        self.assertEqual(payload["rows"], [])

    def test_explicit_window_is_respected(self):
        """When --from is given, no default window is applied."""
        self._responses([], [])

        MetricsCommand.metrics_score(
            TEST_DIR, _query_args(interval="weekly", from_dt="2026-09-01"), output_json=True
        )

        body = self.mock_request.call_args_list[1].kwargs["data"]
        self.assertEqual(body["from_datetime"], "2026-09-01T00:00:00")
        self.assertNotIn("to_datetime", body)
        self.assertEqual(body["interval"], "weekly")


class FlagMappingTest(unittest.TestCase):
    """The argv mappers in shared.py shape flags; validation happens on the project."""

    def test_filter_values_are_coerced_and_lists_split(self):
        """Numbers and booleans become JSON types; in/ex take a comma-separated list."""
        parsed = filter_flags_to_filters(
            [["poly_score", "GTE", "80"], ["handoff", "eq", "true"], ["channel", "in", "CHAT, SMS"]]
        )
        self.assertEqual(parsed[0], {"metric": "poly_score", "op": "gte", "value": 80})
        self.assertEqual(parsed[1], {"metric": "handoff", "op": "eq", "value": True})
        self.assertEqual(parsed[2], {"metric": "channel", "op": "in", "value": ["CHAT", "SMS"]})

    def test_having_and_sort_are_passed_through_for_the_project_to_check(self):
        """The mappers keep the raw values; the project rejects bad ones."""
        self.assertEqual(
            having_flags_to_having([["avg", "gte", "4"]]),
            [{"field": "avg", "op": "gte", "value": "4"}],
        )
        self.assertIsNone(sort_flag_to_sort(None))
        self.assertEqual(sort_flag_to_sort("avg"), {"field": "avg", "order": "asc"})
        self.assertEqual(sort_flag_to_sort("channel:DESC"), {"field": "channel", "order": "DESC"})


class DescribeDataApiErrorTest(unittest.TestCase):
    """Tests for describe_data_api_error."""

    def test_statuses_map_to_plain_messages(self):
        """Each status the Data API returns gets a message in the caller's terms."""
        self.assertIn("poly apikey", describe_data_api_error(_http_error(401)))
        self.assertIn("permission", describe_data_api_error(_http_error(403)))
        self.assertIn("100 requests", describe_data_api_error(_http_error(429)))
        self.assertEqual(
            describe_data_api_error(_http_error(400, {"detail": "metric not found"})),
            "The Data API rejected the request: metric not found.",
        )

    def test_validation_detail_list_is_joined(self):
        """A FastAPI-style list of errors is flattened into one line."""
        payload = {"detail": [{"msg": "field required", "loc": ["body", "metric"]}]}
        self.assertIn("field required", describe_data_api_error(_http_error(422, payload)))

    def test_unexpected_body_shapes_do_not_raise(self):
        """A list body, a dict detail or no JSON at all still produce a message."""
        self.assertIn("rejected", describe_data_api_error(_http_error(400, ["oops"])))
        self.assertIn("rejected", describe_data_api_error(_http_error(400, {"detail": {"a": 1}})))
        self.assertIn("rejected", describe_data_api_error(_http_error(400, text="plain text")))
