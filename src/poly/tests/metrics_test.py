"""Tests for the metrics CLI commands.

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

from poly.cli_commands.metrics import VALID_METRIC_TYPES, MetricsCommand, _parse_bool_flag


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
    @patch("poly.cli_commands.metrics.AgentStudioInterface.get_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_list_calls_print_metrics(self, mock_load, mock_get, mock_print):
        """metrics_list fetches metrics and prints them in table mode."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_get.return_value = [{"name": "SCORE", "type": "int"}]

        MetricsCommand.metrics_list("/fake/path", output_json=False)

        mock_get.assert_called_once_with("us", "acc1", "proj1")
        mock_print.assert_called_once_with([{"name": "SCORE", "type": "int"}])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.get_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_list_json_output(self, mock_load, mock_get, mock_json):
        """metrics_list uses json_print when output_json=True."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        metrics = [{"name": "SCORE"}]
        mock_get.return_value = metrics

        MetricsCommand.metrics_list("/fake/path", output_json=True)

        mock_json.assert_called_once_with(metrics)


class MetricsExportTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_export."""

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.export_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_json_output(self, mock_load, mock_export, mock_json):
        """In JSON mode, export passes the dict straight to json_print."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        data = {"SCORE": {"type": "int"}, "STATUS": {"type": "string"}}
        mock_export.return_value = data

        MetricsCommand.metrics_export("/fake/path", output_json=True)

        mock_json.assert_called_once_with(data)

    @patch("poly.cli_commands.metrics.AgentStudioInterface.export_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_to_stdout(self, mock_load, mock_export):
        """Without a file path, YAML is dumped to stdout."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_export.return_value = {"SCORE": {"type": "int"}}

        with patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls:
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/fake/path", file_path=None, output_json=False)

            import sys

            mock_ry.dump.assert_called_once_with({"SCORE": {"type": "int"}}, sys.stdout)

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.export_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_to_file(self, mock_load, mock_export, mock_success):
        """With a file path, YAML is written to file and success message shown."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_export.return_value = {"SCORE": {"type": "int"}}

        with (
            patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls,
            patch("builtins.open", unittest.mock.mock_open()) as mock_file,
        ):
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/fake/path", file_path="out.yaml", output_json=False)

            mock_file.assert_called_once_with("out.yaml", "w")
            mock_ry.dump.assert_called_once()
            mock_success.assert_called_once()
            self.assertIn("out.yaml", mock_success.call_args[0][0])

    @patch("poly.cli_commands.metrics.AgentStudioInterface.export_custom_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_export_empty_metrics(self, mock_load, mock_export):
        """Export with empty dict still dumps without error."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_export.return_value = {}

        with patch("poly.cli_commands.metrics.YAML") as mock_yaml_cls:
            mock_ry = MagicMock()
            mock_yaml_cls.return_value = mock_ry
            MetricsCommand.metrics_export("/fake/path", output_json=False)

            mock_ry.dump.assert_called_once_with({}, unittest.mock.ANY)


class MetricsAddTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_add."""

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.create_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_with_all_args(self, mock_load, mock_create, mock_update, mock_success):
        """Non-interactive add passes all fields to create_custom_metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_create.return_value = {"name": "SCORE", "type": "int"}
        mock_update.return_value = {"name": "SCORE", "type": "int", "api": True}

        MetricsCommand.metrics_add(
            "/fake/path",
            name="SCORE",
            metric_type="int",
            description="CSAT Score",
            api=True,
            expected_values=None,
            output_json=False,
        )

        mock_create.assert_called_once_with(
            "us",
            "acc1",
            "proj1",
            {"name": "SCORE", "type": "int", "description": "CSAT Score", "api": True},
        )
        mock_update.assert_called_once_with("us", "acc1", "proj1", "SCORE", {"api": True})
        mock_success.assert_called_once()

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.create_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_without_api_skips_update(self, mock_load, mock_create, mock_update, mock_json):
        """When api=False, no follow-up update call is made."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_create.return_value = {"name": "SCORE", "type": "int"}

        MetricsCommand.metrics_add(
            "/fake/path",
            name="SCORE",
            metric_type="int",
            api=False,
            output_json=True,
        )

        mock_create.assert_called_once()
        mock_update.assert_not_called()

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.create_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_passes_expected_values(self, mock_load, mock_create, mock_json):
        """Expected values are included in the data dict when provided."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_create.return_value = {}

        MetricsCommand.metrics_add(
            "/fake/path",
            name="STATUS",
            metric_type="string",
            description=None,
            api=False,
            expected_values=["open", "closed"],
            output_json=True,
        )

        data = mock_create.call_args[0][3]
        self.assertEqual(data["expected_values"], ["open", "closed"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_json_error_when_name_missing(self, mock_load, mock_json):
        """In JSON mode, missing --name prints an error and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_add(
                "/fake/path",
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
                "/fake/path",
                name="SCORE",
                metric_type=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        printed = mock_json.call_args[0][0]
        self.assertIn("--type", printed["error"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.create_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_add_json_output_on_success(self, mock_load, mock_create, mock_json):
        """In JSON mode, successful add prints success with the metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        result = {"name": "SCORE", "type": "int"}
        mock_create.return_value = result

        MetricsCommand.metrics_add(
            "/fake/path",
            name="SCORE",
            metric_type="int",
            output_json=True,
        )

        mock_json.assert_called_once_with({"success": True, "metric": result})


class MetricsEditTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_edit."""

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_with_description(self, mock_load, mock_update, mock_success):
        """Editing description passes it through to update_custom_metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_update.return_value = {}

        MetricsCommand.metrics_edit(
            "/fake/path", name="SCORE", description="New desc", output_json=False
        )

        mock_update.assert_called_once_with(
            "us", "acc1", "proj1", "SCORE", {"description": "New desc"}
        )

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_deactivate_metric(self, mock_load, mock_update, mock_success):
        """Setting active=False prints 'Deactivated' message."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_update.return_value = {}

        MetricsCommand.metrics_edit("/fake/path", name="SCORE", active=False, output_json=False)

        mock_update.assert_called_once_with("us", "acc1", "proj1", "SCORE", {"active": False})
        mock_success.assert_called_once()
        self.assertIn("Deactivated", mock_success.call_args[0][0])

    @patch("poly.cli_commands.metrics.success")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_multiple_flags(self, mock_load, mock_update, mock_success):
        """Multiple flags are combined into one update call."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_update.return_value = {}

        MetricsCommand.metrics_edit(
            "/fake/path",
            name="SCORE",
            description="Updated",
            api=True,
            active=True,
            output_json=False,
        )

        data = mock_update.call_args[0][4]
        self.assertEqual(data["description"], "Updated")
        self.assertTrue(data["api"])
        self.assertTrue(data["active"])

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_no_flags_exits(self, mock_load, mock_error):
        """Exits with error when no update flags are provided."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_edit("/fake/path", name="SCORE", output_json=False)

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_no_flags_json_exits(self, mock_load, mock_json):
        """In JSON mode, no flags prints error JSON and exits."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_edit("/fake/path", name="SCORE", output_json=True)

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.update_custom_metric")
    @patch("poly.cli_commands.metrics.load_project")
    def test_edit_json_output(self, mock_load, mock_update, mock_json):
        """In JSON mode, successful edit prints success with the metric."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        result = {"name": "SCORE", "active": True}
        mock_update.return_value = result

        MetricsCommand.metrics_edit("/fake/path", name="SCORE", active=True, output_json=True)

        mock_json.assert_called_once_with({"success": True, "metric": result})


class MetricsImportTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_import."""

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_file_not_found(self, mock_load, mock_error):
        """Exits with error when the import file does not exist."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_import(
                "/fake/path", file_path="/nonexistent/metrics.yaml", output_json=False
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

        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_import(
                "/fake/path", file_path="/nonexistent/metrics.yaml", output_json=True
            )

        printed = mock_json.call_args[0][0]
        self.assertFalse(printed["success"])

    @patch("builtins.open", unittest.mock.mock_open(read_data="{{invalid"))
    @patch("os.path.exists", return_value=True)
    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_invalid_yaml(self, mock_load, mock_error, mock_exists):
        """Exits with error when YAML parsing fails."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_import("/fake/path", file_path="bad.yaml", output_json=False)

        self.assertEqual(ctx.exception.code, 1)

    @patch("builtins.open", unittest.mock.mock_open(read_data="SCORE:\n  type: int\n"))
    @patch("os.path.exists", return_value=True)
    @patch("poly.cli_commands.metrics.AgentStudioInterface.import_custom_metrics")
    @patch("poly.cli_commands.metrics.AgentStudioInterface.preview_metrics_import")
    @patch("poly.cli_commands.metrics.load_project")
    def test_import_success(self, mock_load, mock_preview, mock_import, mock_exists):
        """Successful import calls import_custom_metrics and prints summary."""
        project = MagicMock(region="us", account_id="acc1", project_id="proj1")
        mock_load.return_value = project
        mock_preview.return_value = {"remote_only": []}
        mock_import.return_value = {
            "metadata": {"created": ["SCORE"], "ignored": []},
        }

        with patch("poly.cli_commands.metrics.success"), patch("poly.cli_commands.metrics.plain"):
            MetricsCommand.metrics_import("/fake/path", file_path="metrics.yaml", output_json=False)

        mock_import.assert_called_once()
        # Verify dry_run=False was passed
        self.assertFalse(mock_import.call_args[1]["dry_run"])


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


class ValidMetricTypesTest(unittest.TestCase):
    """Tests for the VALID_METRIC_TYPES constant."""

    def test_contains_expected_types(self):
        """All expected metric types are present."""
        self.assertEqual(VALID_METRIC_TYPES, ["string", "int", "bool", "float"])


if __name__ == "__main__":
    unittest.main()
