"""Tests for the A/B test CLI commands (poly deployments ab-test ...).

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.cli import AgentStudioCLI
from poly.tests.project_test import TEST_DIR


def _make_http_error(status_code: int, body: dict | None = None) -> requests.HTTPError:
    """Build a requests.HTTPError with a mock response carrying JSON body."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = body or {}
    err = requests.HTTPError(f"{status_code} Error", response=response)
    err.response = response
    return err


SAMPLE_AB_TEST = {
    "id": "ab-001",
    "name": "v2 test",
    "control_deployment_id": "dep-live",
    "variant_deployment_id": "dep-variant",
    "traffic_percentage": 50,
    "status": "active",
}


class ABTestStartTest(unittest.TestCase):
    """Tests for AgentStudioCLI.ab_test_start."""

    def setUp(self):
        patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.create_ab_test.return_value = dict(SAMPLE_AB_TEST)
        self.proj.get_deployments.return_value = (
            [
                {
                    "id": "dep-v",
                    "version_hash": "variant111",
                    "deployment_metadata": {"deployment_message": "v2"},
                }
            ],
            {"live": "live000000"},
        )
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Happy path --

    @patch("poly.cli.success")
    @patch("poly.cli.print_ab_test_detail")
    def test_start__success_rich_output(self, mock_detail, mock_success):
        """Successful start prints success and detail in rich mode."""
        AgentStudioCLI.ab_test_start(
            TEST_DIR, name="v2 test", variant_version="variant111", traffic_percentage=50
        )

        self.proj.create_ab_test.assert_called_once_with("v2 test", "dep-v", 50)
        mock_success.assert_called_once()
        mock_detail.assert_called_once()

    @patch("poly.cli.json_print")
    def test_start__success_json_output(self, mock_json):
        """Successful start emits JSON with success=True and the ab_test payload."""
        AgentStudioCLI.ab_test_start(
            TEST_DIR,
            name="v2 test",
            variant_version="variant111",
            traffic_percentage=50,
            output_json=True,
        )

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["ab_test"]["id"], "ab-001")

    @patch("poly.cli.json_print")
    def test_start__name_is_stripped(self, mock_json):
        """Leading/trailing whitespace in name is stripped before calling the API."""
        AgentStudioCLI.ab_test_start(
            TEST_DIR,
            name="  v2 test  ",
            variant_version="variant111",
            traffic_percentage=50,
            output_json=True,
        )

        self.proj.create_ab_test.assert_called_once_with("v2 test", "dep-v", 50)

    # -- Interactive prompts --

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    @patch("poly.cli.print_ab_test_detail")
    def test_start__interactive_name_and_traffic(self, mock_detail, mock_success, mock_q):
        """When name and traffic are None, prompts interactively with defaults."""
        mock_q.text.return_value.ask.side_effect = ["my test", "50"]

        AgentStudioCLI.ab_test_start(
            TEST_DIR, name=None, variant_version="variant111", traffic_percentage=None
        )

        self.assertEqual(mock_q.text.call_count, 2)
        name_call = mock_q.text.call_args_list[0]
        self.assertIn("name", name_call[0][0].lower())
        traffic_call = mock_q.text.call_args_list[1]
        self.assertEqual(traffic_call[1]["default"], "50")
        self.proj.create_ab_test.assert_called_once_with("my test", "dep-v", 50)

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    @patch("poly.cli.print_ab_test_detail")
    def test_start__interactive_variant_picker(self, mock_detail, mock_success, mock_q):
        """When variant is None, fetches pre-release deployments and prompts."""
        self.proj.get_deployments.return_value = (
            [
                {
                    "id": "dep-pr-1",
                    "version_hash": "abc123456",
                    "deployment_metadata": {"deployment_message": "v2 candidate"},
                }
            ],
            {"live": "live000000"},
        )
        mock_q.text.return_value.ask.return_value = "50"
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)
        mock_q.select.return_value.ask.return_value = "dep-pr-1"

        AgentStudioCLI.ab_test_start(
            TEST_DIR, name="test", variant_version=None, traffic_percentage=None
        )

        self.proj.get_deployments.assert_any_call(client_env="pre-release")
        mock_q.select.assert_called_once()
        self.proj.create_ab_test.assert_called_once_with("test", "dep-pr-1", 50)

    # -- Version validation --

    @patch("poly.cli.error")
    def test_start__variant_same_version_as_live_exits(self, mock_error):
        """Explicit variant with same version_hash as live exits with error."""
        self.proj.get_deployments.return_value = (
            [{"id": "dep-v", "version_hash": "same_hash"}],
            {"live": "same_hash"},
        )

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="test", variant_version="same_hash", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("same version", mock_error.call_args[0][0])
        self.proj.create_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_start__variant_same_version_as_live_json(self, mock_json):
        """Explicit variant with same version as live exits with error JSON."""
        self.proj.get_deployments.return_value = (
            [{"id": "dep-v", "version_hash": "same_hash"}],
            {"live": "same_hash"},
        )

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="test",
                variant_version="same_hash",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("same version", payload["error"])

    @patch("poly.cli.error")
    def test_start__interactive_filters_same_version_deployments(self, mock_error):
        """Interactive picker excludes pre-release deployments matching live version."""
        self.proj.get_deployments.return_value = (
            [{"id": "dep-1", "version_hash": "live_hash"}],
            {"live": "live_hash"},
        )

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="test", variant_version=None, traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("match the current live version", mock_error.call_args[0][0])

    @patch("poly.cli.json_print")
    def test_start__json_mode_requires_name(self, mock_json):
        """JSON mode with name=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name=None,
                variant_version="variant111",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("--name", payload["error"])

    @patch("poly.cli.json_print")
    def test_start__json_mode_requires_variant_version(self, mock_json):
        """JSON mode with variant_version=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="test",
                variant_version=None,
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("--variant-version", payload["error"])

    @patch("poly.cli.json_print")
    def test_start__json_mode_requires_traffic(self, mock_json):
        """JSON mode with traffic=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="test",
                variant_version="variant111",
                traffic_percentage=None,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("--traffic", payload["error"])

    @patch("poly.cli.questionary")
    @patch("poly.cli.error")
    def test_start__interactive_traffic_not_a_number(self, mock_error, mock_q):
        """Non-numeric interactive traffic input exits with error."""
        mock_q.text.return_value.ask.side_effect = ["my test", "abc"]

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name=None, variant_version="variant111", traffic_percentage=None
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("integer", mock_error.call_args[0][0])

    # -- Validation: name --

    @patch("poly.cli.error")
    def test_start__empty_name_exits_with_error(self, mock_error):
        """Empty string name triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="", variant_version="variant111", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()
        self.assertIn("required", mock_error.call_args[0][0])
        self.proj.create_ab_test.assert_not_called()

    @patch("poly.cli.error")
    def test_start__whitespace_only_name_exits_with_error(self, mock_error):
        """Whitespace-only name triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="   ", variant_version="variant111", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.create_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_start__empty_name_json_mode_exits_with_error(self, mock_json):
        """Empty name in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="",
                variant_version="variant111",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("required", payload["error"])

    # -- Validation: traffic_percentage --

    @patch("poly.cli.error")
    def test_start__negative_traffic_exits_with_error(self, mock_error):
        """Negative traffic percentage triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="test", variant_version="variant111", traffic_percentage=-1
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("0 and 100", mock_error.call_args[0][0])
        self.proj.create_ab_test.assert_not_called()

    @patch("poly.cli.error")
    def test_start__traffic_above_100_exits_with_error(self, mock_error):
        """Traffic percentage > 100 triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR, name="test", variant_version="variant111", traffic_percentage=101
            )

        self.assertEqual(ctx.exception.code, 1)
        self.proj.create_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_start__traffic_above_100_json_mode(self, mock_json):
        """Traffic > 100 in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="test",
                variant_version="variant111",
                traffic_percentage=101,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])

    # -- Boundary: traffic at 0 and 100 --

    @patch("poly.cli.json_print")
    def test_start__traffic_zero_is_valid(self, mock_json):
        """Traffic percentage of 0 is accepted."""
        AgentStudioCLI.ab_test_start(
            TEST_DIR,
            name="test",
            variant_version="variant111",
            traffic_percentage=0,
            output_json=True,
        )

        self.proj.create_ab_test.assert_called_once_with("test", "dep-v", 0)

    @patch("poly.cli.json_print")
    def test_start__traffic_100_is_valid(self, mock_json):
        """Traffic percentage of 100 is accepted."""
        AgentStudioCLI.ab_test_start(
            TEST_DIR,
            name="test",
            variant_version="variant111",
            traffic_percentage=100,
            output_json=True,
        )

        self.proj.create_ab_test.assert_called_once_with("test", "dep-v", 100)

    # -- HTTP errors (propagated to top-level handler) --

    def test_start__http_error_propagates(self):
        """HTTPError from create_ab_test propagates to the top-level handler."""
        self.proj.create_ab_test.side_effect = _make_http_error(
            409, {"error": "An A/B test is already active."}
        )

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_start(
                TEST_DIR,
                name="test",
                variant_version="variant111",
                traffic_percentage=50,
            )


class ABTestListTest(unittest.TestCase):
    """Tests for AgentStudioCLI.ab_test_list."""

    def setUp(self):
        patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    @patch("poly.cli.AgentStudioCLI._fetch_deployment_map")
    @patch("poly.cli.print_ab_tests")
    def test_list__success_rich_output(self, mock_print, mock_dep_map):
        """Successful list calls print_ab_tests with results and deployment map."""
        self.proj.list_ab_tests.return_value = [SAMPLE_AB_TEST]
        mock_dep_map.return_value = {"dep-live": {"id": "dep-live"}}

        AgentStudioCLI.ab_test_list(TEST_DIR, limit=10)

        self.proj.list_ab_tests.assert_called_once_with(limit=10)
        mock_print.assert_called_once_with(
            [SAMPLE_AB_TEST], deployments={"dep-live": {"id": "dep-live"}}
        )

    @patch("poly.cli.json_print")
    def test_list__success_json_output(self, mock_json):
        """Successful list emits JSON with success=True and the ab_tests array."""
        self.proj.list_ab_tests.return_value = [SAMPLE_AB_TEST]

        AgentStudioCLI.ab_test_list(TEST_DIR, limit=5, output_json=True)

        self.proj.list_ab_tests.assert_called_once_with(limit=5)
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(len(payload["ab_tests"]), 1)

    @patch("poly.cli.print_ab_tests")
    def test_list__empty_results(self, mock_print):
        """Empty list result still calls print_ab_tests with empty list."""
        self.proj.list_ab_tests.return_value = []

        AgentStudioCLI.ab_test_list(TEST_DIR)

        mock_print.assert_called_once_with([], deployments={})

    @patch("poly.cli.json_print")
    def test_list__limit_parameter_forwarded(self, mock_json):
        """Custom limit is forwarded to project.list_ab_tests."""
        self.proj.list_ab_tests.return_value = []

        AgentStudioCLI.ab_test_list(TEST_DIR, limit=25, output_json=True)

        self.proj.list_ab_tests.assert_called_once_with(limit=25)

    def test_list__http_error_propagates(self):
        """HTTPError from list_ab_tests propagates to the top-level handler."""
        self.proj.list_ab_tests.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_list(TEST_DIR)


class ABTestActiveTest(unittest.TestCase):
    """Tests for AgentStudioCLI.ab_test_active."""

    def setUp(self):
        patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    @patch("poly.cli.print_ab_test_detail")
    def test_active__found_rich_output(self, mock_detail):
        """Active test found prints detail in rich mode."""
        self.proj.get_active_ab_test.return_value = SAMPLE_AB_TEST

        AgentStudioCLI.ab_test_active(TEST_DIR)

        mock_detail.assert_called_once()
        self.assertEqual(mock_detail.call_args[0][0], SAMPLE_AB_TEST)

    @patch("poly.cli.json_print")
    def test_active__found_json_output(self, mock_json):
        """Active test found emits JSON with the ab_test."""
        self.proj.get_active_ab_test.return_value = SAMPLE_AB_TEST

        AgentStudioCLI.ab_test_active(TEST_DIR, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["ab_test"]["id"], "ab-001")

    @patch("poly.cli.print_ab_test_detail")
    def test_active__none_returned_rich(self, mock_detail):
        """No active test passes None to print_ab_test_detail."""
        self.proj.get_active_ab_test.return_value = None

        AgentStudioCLI.ab_test_active(TEST_DIR)

        mock_detail.assert_called_once()
        self.assertIsNone(mock_detail.call_args[0][0])

    @patch("poly.cli.json_print")
    def test_active__none_returned_json(self, mock_json):
        """No active test emits JSON with ab_test: None."""
        self.proj.get_active_ab_test.return_value = None

        AgentStudioCLI.ab_test_active(TEST_DIR, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertIsNone(payload["ab_test"])

    def test_active__http_error_propagates(self):
        """HTTPError from get_active_ab_test propagates to the top-level handler."""
        self.proj.get_active_ab_test.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_active(TEST_DIR)


class ABTestUpdateTest(unittest.TestCase):
    """Tests for AgentStudioCLI.ab_test_update."""

    def setUp(self):
        patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        updated = dict(SAMPLE_AB_TEST, traffic_percentage=30)
        self.proj.update_ab_test.return_value = updated
        self.proj.get_active_ab_test.return_value = dict(SAMPLE_AB_TEST)
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Happy path --

    @patch("poly.cli.success")
    @patch("poly.cli.print_ab_test_detail")
    def test_update__success_rich_output(self, mock_detail, mock_success):
        """Successful update prints success message with new percentage."""
        AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=30)

        self.proj.update_ab_test.assert_called_once_with("ab-001", 30)
        mock_success.assert_called_once()
        self.assertIn("30%", mock_success.call_args[0][0])
        mock_detail.assert_called_once()

    @patch("poly.cli.json_print")
    def test_update__success_json_output(self, mock_json):
        """Successful update emits JSON with updated ab_test."""
        AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=30, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["ab_test"]["traffic_percentage"], 30)

    # -- No active test --

    @patch("poly.cli.error")
    def test_update__no_active_test_exits(self, mock_error):
        """No active test exits with error."""
        self.proj.get_active_ab_test.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=30)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_error.call_args[0][0])
        self.proj.update_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_update__no_active_test_json_exits(self, mock_json):
        """No active test in JSON mode exits with error JSON."""
        self.proj.get_active_ab_test.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=30, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("No active", payload["error"])

    # -- Validation: traffic_percentage --

    @patch("poly.cli.error")
    def test_update__negative_traffic_exits_with_error(self, mock_error):
        """Negative traffic percentage triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=-5)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("0 and 100", mock_error.call_args[0][0])
        self.proj.update_ab_test.assert_not_called()

    @patch("poly.cli.error")
    def test_update__traffic_above_100_exits_with_error(self, mock_error):
        """Traffic > 100 triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=150)

        self.assertEqual(ctx.exception.code, 1)
        mock_error.assert_called_once()
        self.proj.update_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_update__traffic_above_100_json_mode(self, mock_json):
        """Traffic > 100 in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=200, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])

    # -- HTTP errors --

    def test_update__http_error_propagates(self):
        """HTTPError from update_ab_test propagates to the top-level handler."""
        self.proj.update_ab_test.side_effect = _make_http_error(
            400, {"error": "Traffic percentage must be between 0 and 100"}
        )

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_update(TEST_DIR, traffic_percentage=30)


class ABTestEndTest(unittest.TestCase):
    """Tests for AgentStudioCLI.ab_test_end."""

    def setUp(self):
        patcher = patch("poly.cli.AgentStudioCLI._load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.end_ab_test.return_value = dict(SAMPLE_AB_TEST, status="ended")
        self.proj.get_active_ab_test.return_value = dict(SAMPLE_AB_TEST)
        self.proj.get_deployments.return_value = (
            [
                {
                    "id": "dep-live",
                    "version_hash": "live00000",
                    "deployment_metadata": {"deployment_message": "v1 stable"},
                },
                {
                    "id": "dep-variant",
                    "version_hash": "variant111",
                    "deployment_metadata": {"deployment_message": "v2 candidate"},
                },
            ],
            {},
        )
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Happy path: control wins (no promotion) --

    @patch("poly.cli.success")
    @patch("poly.cli.info")
    def test_end__explicit_winner_rich_output(self, mock_info, mock_success):
        """Ending with control as winner prints success, no promotion."""
        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="live00000")

        self.proj.end_ab_test.assert_called_once_with("ab-001", "dep-live")
        mock_success.assert_called_once()
        self.proj.promote_deployment.assert_not_called()

    @patch("poly.cli.json_print")
    def test_end__explicit_winner_json_output(self, mock_json):
        """Ending with control as winner emits JSON with promoted=False."""
        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="live00000", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertFalse(payload["promoted"])

    # -- Happy path: variant wins (triggers promotion) --

    @patch("poly.cli.success")
    @patch("poly.cli.info")
    def test_end__variant_wins_promotes_to_live(self, mock_info, mock_success):
        """Choosing the variant promotes it to live."""
        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="variant111")

        self.proj.end_ab_test.assert_called_once_with("ab-001", "dep-variant")
        self.proj.promote_deployment.assert_called_once_with(
            "dep-variant", "live", message="v2 candidate"
        )
        self.assertEqual(mock_success.call_count, 2)

    @patch("poly.cli.json_print")
    def test_end__variant_wins_json_includes_promoted(self, mock_json):
        """Variant win in JSON mode includes promoted=True."""
        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="variant111", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertTrue(payload["promoted"])

    @patch("poly.cli.warning")
    @patch("poly.cli.success")
    @patch("poly.cli.info")
    def test_end__variant_wins_promote_fails_warns(self, mock_info, mock_success, mock_warning):
        """If promotion fails after ending, warns but doesn't exit with error."""
        self.proj.promote_deployment.side_effect = Exception("promote failed")

        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="variant111")

        self.proj.end_ab_test.assert_called_once()
        mock_warning.assert_called_once()
        self.assertIn("failed to promote", mock_warning.call_args[0][0])

    # -- JSON mode without chosen_version --

    @patch("poly.cli.json_print")
    def test_end__json_mode_without_chosen_version_exits_with_error(self, mock_json):
        """JSON mode requires --chosen-version; omitting it exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version=None, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("--chosen-version", payload["error"])
        self.proj.end_ab_test.assert_not_called()

    # -- Interactive prompt flow --

    @patch("poly.cli.questionary")
    @patch("poly.cli.success")
    @patch("poly.cli.info")
    def test_end__interactive_prompt_selects_winner(self, mock_info, mock_success, mock_q):
        """Interactive mode fetches active test, prompts, ends test and promotes variant."""
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)
        mock_q.select.return_value.ask.return_value = "dep-variant"

        AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version=None)

        self.proj.get_active_ab_test.assert_called_once()
        mock_q.select.assert_called_once()
        self.proj.end_ab_test.assert_called_once_with("ab-001", "dep-variant")
        self.proj.promote_deployment.assert_called_once()
        self.assertEqual(mock_success.call_count, 2)

    @patch("poly.cli.questionary")
    @patch("poly.cli.warning")
    @patch("poly.cli.info")
    def test_end__interactive_user_aborts(self, mock_info, mock_warning, mock_q):
        """User aborting the interactive prompt exits with 0."""
        mock_q.Choice = MagicMock(side_effect=lambda **kw: kw)
        mock_q.select.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version=None)

        self.assertEqual(ctx.exception.code, 0)
        mock_warning.assert_called_once()
        self.proj.end_ab_test.assert_not_called()

    # -- No active test --

    @patch("poly.cli.error")
    def test_end__no_active_test_exits(self, mock_error):
        """If no active test exists, exits with error."""
        self.proj.get_active_ab_test.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version=None)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_error.call_args[0][0])
        self.proj.end_ab_test.assert_not_called()

    @patch("poly.cli.json_print")
    def test_end__no_active_test_json_exits(self, mock_json):
        """If no active test exists in JSON mode, exits with error JSON."""
        self.proj.get_active_ab_test.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            AgentStudioCLI.ab_test_end(
                TEST_DIR, chosen_version="live00000", output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertIn("No active", payload["error"])

    # -- HTTP errors (propagated to top-level handler) --

    def test_end__http_error_fetching_active_propagates(self):
        """HTTPError when fetching active test propagates to the top-level handler."""
        self.proj.get_active_ab_test.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version=None)

    def test_end__http_error_ending_test_propagates(self):
        """HTTPError from end_ab_test propagates to the top-level handler."""
        self.proj.end_ab_test.side_effect = _make_http_error(
            409, {"error": "A/B test already ended."}
        )

        with self.assertRaises(requests.HTTPError):
            AgentStudioCLI.ab_test_end(TEST_DIR, chosen_version="live00000")


if __name__ == "__main__":
    unittest.main()
