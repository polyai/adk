"""Tests for the metric read commands: available, query, score.

Copyright PolyAI Limited
"""

import unittest
from argparse import Namespace
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.metrics import MetricsCommand
from poly.cli_commands.shared import (
    describe_data_api_error,
    parse_datetime_flag,
    parse_filter_flags,
    parse_having_flags,
    parse_sort_flag,
)


def _args(**overrides) -> Namespace:
    """Build a Namespace with every query flag defaulted, overriding as asked."""
    base = {
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
        "agg": None,
    }
    base.update(overrides)
    return Namespace(**base)


def _http_error(status: int, detail: str | None = None) -> requests.HTTPError:
    response = MagicMock()
    response.status_code = status
    response.json.return_value = {"detail": detail} if detail else {}
    response.text = detail or ""
    return requests.HTTPError(response=response)


class ParseDatetimeFlagTest(unittest.TestCase):
    """Tests for parse_datetime_flag."""

    def test_date_only_start(self):
        """A bare date starts at midnight."""
        self.assertEqual(parse_datetime_flag("2026-09-01"), "2026-09-01T00:00:00")

    def test_date_only_exclusive_end_rolls_to_next_day(self):
        """A bare --to date includes the whole day by moving to the next midnight."""
        self.assertEqual(
            parse_datetime_flag("2026-09-30", exclusive_end=True), "2026-10-01T00:00:00"
        )

    def test_datetime_kept_as_given(self):
        """A full datetime is passed through, Z normalised to an offset."""
        self.assertEqual(parse_datetime_flag("2026-09-01T09:30:00Z"), "2026-09-01T09:30:00+00:00")
        self.assertEqual(
            parse_datetime_flag("2026-09-01T09:30", exclusive_end=True), "2026-09-01T09:30:00"
        )

    def test_invalid_raises(self):
        """Garbage is rejected with a helpful message."""
        with self.assertRaises(ValueError) as ctx:
            parse_datetime_flag("yesterday")
        self.assertIn("YYYY-MM-DD", str(ctx.exception))


class ParseFilterFlagsTest(unittest.TestCase):
    """Tests for parse_filter_flags and parse_having_flags."""

    def test_scalar_values_are_coerced(self):
        """Numbers and booleans become JSON types; everything else stays a string."""
        parsed = parse_filter_flags(
            [["poly_score", "gte", "80"], ["handoff", "eq", "true"], ["channel", "eq", "CHAT"]]
        )
        self.assertEqual(parsed[0], {"metric": "poly_score", "op": "gte", "value": 80})
        self.assertEqual(parsed[1], {"metric": "handoff", "op": "eq", "value": True})
        self.assertEqual(parsed[2], {"metric": "channel", "op": "eq", "value": "CHAT"})

    def test_list_operators_split_on_commas(self):
        """in/ex take a comma-separated list."""
        parsed = parse_filter_flags([["channel", "IN", "CHAT, SMS"]])
        self.assertEqual(parsed[0], {"metric": "channel", "op": "in", "value": ["CHAT", "SMS"]})

    def test_unknown_operator_raises(self):
        """An operator the gateway does not know is rejected before the request."""
        with self.assertRaises(ValueError):
            parse_filter_flags([["x", "like", "y"]])

    def test_having_validates_field_op_and_number(self):
        """having needs an aggregation name, a comparison and a numeric value."""
        self.assertEqual(
            parse_having_flags([["avg", "gte", "4"]]), [{"field": "avg", "op": "gte", "value": 4.0}]
        )
        with self.assertRaises(ValueError):
            parse_having_flags([["median", "gte", "4"]])
        with self.assertRaises(ValueError):
            parse_having_flags([["avg", "in", "4"]])
        with self.assertRaises(ValueError):
            parse_having_flags([["avg", "gte", "high"]])

    def test_sort_flag(self):
        """FIELD and FIELD:desc both parse; other orders are rejected."""
        self.assertIsNone(parse_sort_flag(None))
        self.assertEqual(parse_sort_flag("avg"), {"field": "avg", "order": "asc"})
        self.assertEqual(parse_sort_flag("channel:DESC"), {"field": "channel", "order": "desc"})
        with self.assertRaises(ValueError):
            parse_sort_flag("avg:sideways")


class DescribeDataApiErrorTest(unittest.TestCase):
    """Tests for describe_data_api_error."""

    def test_403_names_pii_when_route_requires_it(self):
        """Transcript routes explain the PII permission; others say permission generally."""
        self.assertIn("PII read", describe_data_api_error(_http_error(403), needs_pii=True))
        self.assertNotIn("PII", describe_data_api_error(_http_error(403)))

    def test_429_mentions_the_limit(self):
        """Rate limit errors say what the limit is."""
        self.assertIn("100 requests", describe_data_api_error(_http_error(429)))

    def test_400_carries_the_gateway_detail(self):
        """Validation errors pass the gateway's message through."""
        self.assertIn("bad metric", describe_data_api_error(_http_error(400, "bad metric")))


class MetricsAvailableTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_available."""

    @patch("poly.cli_commands.metrics.print_available_metrics")
    @patch("poly.cli_commands.metrics.load_project")
    def test_table_mode(self, mock_load, mock_print):
        """Fetches the catalog for the project's region and prints it."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.get_available_metrics
        metrics = [{"name": "poly_score", "type": "float"}]
        mock_api.return_value = {"metrics": metrics, "total": 1}

        MetricsCommand.metrics_available("/tmp/p", output_json=False)

        mock_api.assert_called_once_with()
        mock_print.assert_called_once_with(metrics)

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_json_mode(self, mock_load, mock_json):
        """JSON mode emits the raw response."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.get_available_metrics
        mock_api.return_value = {"metrics": [], "total": 0}

        MetricsCommand.metrics_available("/tmp/p", output_json=True)

        mock_json.assert_called_once_with({"metrics": [], "total": 0})

    @patch("poly.cli_commands.metrics.error")
    @patch("poly.cli_commands.metrics.load_project")
    def test_http_error_exits_with_message(self, mock_load, mock_error):
        """A gateway error is explained and the command exits non-zero."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.get_available_metrics
        mock_api.side_effect = _http_error(401)

        with self.assertRaises(SystemExit) as ctx:
            MetricsCommand.metrics_available("/tmp/p", output_json=False)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("poly apikey", mock_error.call_args[0][0])


class MetricsQueryTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_query."""

    @patch("poly.cli_commands.metrics.print_aggregate")
    @patch("poly.cli_commands.metrics.load_project")
    def test_builds_full_body(self, mock_load, mock_print):
        """Every flag lands in the request body under the gateway's field name."""
        mock_load.return_value = MagicMock(region="uk-1", project_id="proj1")
        mock_api = mock_load.return_value.query_metric
        mock_api.return_value = {"columns": ["avg"], "rows": [[4.2]], "limit": 20, "offset": 0}
        args = _args(
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
            filter=[["handoff", "eq", "false"]],
            any=True,
            having=[["avg", "gte", "4"]],
            sort="avg:desc",
            limit=50,
            offset=100,
        )

        MetricsCommand.metrics_query("/tmp/p", "duration", args, output_json=False)

        body = mock_api.call_args.args[0]
        self.assertEqual(body["metric"], "duration")
        self.assertEqual(body["aggs"], ["avg", "p95"])
        self.assertEqual(body["from_datetime"], "2026-09-01T00:00:00")
        self.assertEqual(body["to_datetime"], "2026-10-01T00:00:00")
        self.assertEqual(body["interval"], "daily")
        self.assertEqual(body["timezone"], "Europe/London")
        self.assertEqual(body["group_by"], ["channel"])
        self.assertEqual(body["channel"], ["VOICE-SIP"])
        self.assertEqual(body["client_env"], ["live"])
        self.assertEqual(body["deployment_id"], ["dep1"])
        self.assertEqual(body["variant_id"], ["var1"])
        self.assertEqual(body["filters"], [{"metric": "handoff", "op": "eq", "value": False}])
        self.assertEqual(body["filter_operator"], "or")
        self.assertEqual(body["having"], [{"field": "avg", "op": "gte", "value": 4.0}])
        self.assertEqual(body["sort"], {"field": "avg", "order": "desc"})
        self.assertEqual(body["limit"], 50)
        self.assertEqual(body["offset"], 100)
        mock_print.assert_called_once()

    @patch("poly.cli_commands.metrics.load_project")
    def test_minimal_body_has_defaults_and_no_nulls(self, mock_load):
        """With no flags the body carries the defaults only; nothing is sent as null."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.query_metric
        mock_api.return_value = {"columns": [], "rows": []}

        MetricsCommand.metrics_query("/tmp/p", "poly_score", _args(), output_json=True)

        body = mock_api.call_args.args[0]
        self.assertEqual(
            body,
            {
                "metric": "poly_score",
                "aggs": ["avg", "conversation_count"],
                "limit": 20,
                "offset": 0,
            },
        )

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_bad_filter_fails_before_any_request(self, mock_load, mock_json):
        """A malformed flag is reported without loading the project or calling the API."""
        with self.assertRaises(SystemExit):
            MetricsCommand.metrics_query(
                "/tmp/p", "x", _args(filter=[["a", "like", "b"]]), output_json=True
            )
        mock_load.assert_not_called()
        self.assertFalse(mock_json.call_args[0][0]["success"])


class MetricsScoreTest(unittest.TestCase):
    """Tests for MetricsCommand.metrics_score."""

    @patch("poly.cli_commands.metrics.print_aggregate")
    @patch("poly.cli_commands.metrics.load_project")
    def test_defaults_to_seven_days_daily_with_weighted_headline(
        self, mock_load, mock_print
    ):
        """score queries poly_score avg+count, daily, over the last 7 days, and summarises."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.query_metric
        mock_api.return_value = {
            "columns": ["bucket", "avg", "conversation_count"],
            "rows": [["2026-09-28T00:00:00", 80.0, 10], ["2026-09-29T00:00:00", 90.0, 30]],
            "limit": 20,
            "offset": 0,
        }

        MetricsCommand.metrics_score("/tmp/p", _args(interval="daily"), output_json=False)

        body = mock_api.call_args.args[0]
        self.assertEqual(body["metric"], "poly_score")
        self.assertEqual(body["aggs"], ["avg", "conversation_count"])
        self.assertEqual(body["interval"], "daily")
        self.assertIn("from_datetime", body)
        self.assertIn("to_datetime", body)
        headline = mock_print.call_args.kwargs["headline"]
        # (80*10 + 90*30) / 40 = 87.5
        self.assertIn("87.5 average over 40 conversations", headline)

    @patch("poly.cli_commands.metrics.json_print")
    @patch("poly.cli_commands.metrics.load_project")
    def test_json_includes_summary(self, mock_load, mock_json):
        """JSON output carries the computed summary next to the raw table."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.query_metric
        mock_api.return_value = {"columns": ["avg", "conversation_count"], "rows": []}

        MetricsCommand.metrics_score("/tmp/p", _args(interval="daily"), output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertIsNone(payload["summary"]["average"])
        self.assertEqual(payload["summary"]["conversations"], 0)
        self.assertIn("no scored conversations", payload["summary"]["text"])

    @patch("poly.cli_commands.metrics.load_project")
    def test_explicit_window_is_respected(self, mock_load):
        """When --from is given, no default window is applied."""
        mock_load.return_value = MagicMock(region="us-1", project_id="proj1")
        mock_api = mock_load.return_value.query_metric
        mock_api.return_value = {"columns": [], "rows": []}

        MetricsCommand.metrics_score(
            "/tmp/p", _args(interval="weekly", from_dt="2026-09-01"), output_json=True
        )

        body = mock_api.call_args.args[0]
        self.assertEqual(body["from_datetime"], "2026-09-01T00:00:00")
        self.assertNotIn("to_datetime", body)
        self.assertEqual(body["interval"], "weekly")


if __name__ == "__main__":
    unittest.main()


class ProjectDataReadTest(unittest.TestCase):
    """The project layer scopes every Data API read to the loaded project."""

    def _project(self):
        return MagicMock(region="us-1", project_id="proj1")

    @patch("poly.project.AgentStudioInterface.get_available_metrics")
    def test_available_metrics_is_scoped_to_project(self, mock_api):
        """Catalog lookups pass the project's region and id."""
        from poly.project import AgentStudioProject

        AgentStudioProject.get_available_metrics(self._project())

        mock_api.assert_called_once_with("us-1", project_id="proj1")

    @patch("poly.project.AgentStudioInterface.query_metric")
    def test_query_metric_sets_project_id(self, mock_api):
        """The project id is added to the body without mutating the caller's dict."""
        from poly.project import AgentStudioProject

        body = {"metric": "poly_score", "aggs": ["avg"]}
        AgentStudioProject.query_metric(self._project(), body)

        sent = mock_api.call_args.kwargs["body"]
        self.assertEqual(sent["project_id"], "proj1")
        self.assertEqual(sent["metric"], "poly_score")
        self.assertNotIn("project_id", body)

    @patch("poly.project.AgentStudioInterface.search_conversations")
    def test_search_conversations_sets_project_id(self, mock_api):
        """Conversation search is scoped to the project."""
        from poly.project import AgentStudioProject

        AgentStudioProject.search_conversations(self._project(), {"limit": 5})

        self.assertEqual(mock_api.call_args.kwargs["body"], {"limit": 5, "project_id": "proj1"})

    @patch("poly.project.AgentStudioInterface.search_transcripts")
    def test_search_transcripts_sets_project_id(self, mock_api):
        """Transcript search always sends the project id (PATs require it)."""
        from poly.project import AgentStudioProject

        AgentStudioProject.search_transcripts(self._project(), {"query": "human"})

        self.assertEqual(
            mock_api.call_args.kwargs["params"], {"query": "human", "project_id": "proj1"}
        )

    @patch("poly.project.AgentStudioInterface.get_transcript")
    def test_get_transcript_passes_ids(self, mock_api):
        """Transcript fetches carry the conversation and project ids."""
        from poly.project import AgentStudioProject

        AgentStudioProject.get_transcript(self._project(), "conv-1")

        mock_api.assert_called_once_with("us-1", conversation_id="conv-1", project_id="proj1")
