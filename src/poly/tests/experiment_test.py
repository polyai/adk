"""Tests for the experiment CLI commands (poly deployments experiment ...).

Copyright PolyAI Limited
"""

import unittest
from unittest.mock import MagicMock, patch

import requests

from poly.cli_commands.deployments import DeploymentsCommand
from poly.tests.project_test import TEST_DIR


def _make_http_error(status_code: int, body: dict | None = None) -> requests.HTTPError:
    """Build a requests.HTTPError with a mock response carrying JSON body."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = body or {}
    err = requests.HTTPError(f"{status_code} Error", response=response)
    err.response = response
    return err


# Shape returned by AgentStudioProject.get_branches(): (current_branch, {name: meta}).
SAMPLE_BRANCHES = {
    "main": {"branchId": "br-main"},
    "v2-branch": {"branchId": "br-v2"},
}

# Branch map as built by DeploymentsCommand._fetch_branch_map from SAMPLE_BRANCHES.
SAMPLE_BRANCH_MAP = {
    "br-main": {"name": "main", "branchId": "br-main"},
    "br-v2": {"name": "v2-branch", "branchId": "br-v2"},
}

SAMPLE_EXPERIMENT = {
    "id": "exp-001",
    "name": "v2 test",
    "traffic_percentage": 50,
    "versions": [
        {"branch_id": "br-main", "kind": "control", "traffic_percentage": 50},
        {"branch_id": "br-v2", "kind": "release", "traffic_percentage": 50},
    ],
    "ended_at": None,
}

GATE_MESSAGE = "simplified deployments with top-level branches"

# A legacy A/B test surfaced through get_active_experiment (shared backing table).
LEGACY_AB_TEST_EXPERIMENT = {
    "id": "exp-legacy",
    "name": "old ab test",
    "versions": [],
    "control_deployment_id": "dep-live",
    "variant_deployment_id": "dep-variant",
    "traffic_percentage": 50,
    "ended_at": None,
}


class ExperimentStartTest(unittest.TestCase):
    """Tests for DeploymentsCommand.experiment_start."""

    def setUp(self):
        patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.experiments_enabled = True
        # The create response omits per-version detail (a platform API gap), so
        # experiment_start re-fetches by ID via get_experiment for display.
        self.proj.create_experiment.return_value = {"id": "exp-001", "name": "v2 test"}
        self.proj.get_experiment.return_value = dict(SAMPLE_EXPERIMENT)
        self.proj.get_branches.return_value = ("main", dict(SAMPLE_BRANCHES))
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Gate: require_experiments_enabled --

    @patch("poly.output.console.error")
    def test_start__experiments_disabled_exits_with_error(self, mock_error):
        """An ineligible project is refused before anything is created."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="v2 test", branch="v2-branch", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_start__experiments_disabled_json_exits_with_error(self, mock_json):
        """An ineligible project in JSON mode emits an error payload and exits."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR,
                name="v2 test",
                branch="v2-branch",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn(GATE_MESSAGE, payload["error"])
        self.proj.create_experiment.assert_not_called()

    # -- Happy path --

    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__success_rich_output(self, mock_detail, mock_success):
        """Successful start resolves the branch name to its ID and prints the detail."""
        DeploymentsCommand.experiment_start(
            TEST_DIR, name="v2 test", branch="v2-branch", traffic_percentage=50
        )

        self.proj.create_experiment.assert_called_once_with("v2 test", "br-v2", 50)
        mock_success.assert_called_once()
        mock_detail.assert_called_once_with(SAMPLE_EXPERIMENT, branches=SAMPLE_BRANCH_MAP)

    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__falls_back_to_create_response_if_no_id(self, mock_detail, mock_success):
        """If the create response has no id to re-fetch with, fall back to it as-is."""
        self.proj.create_experiment.return_value = {"name": "v2 test"}

        DeploymentsCommand.experiment_start(
            TEST_DIR, name="v2 test", branch="v2-branch", traffic_percentage=50
        )

        self.proj.get_experiment.assert_not_called()
        mock_detail.assert_called_once_with(
            self.proj.create_experiment.return_value, branches=SAMPLE_BRANCH_MAP
        )

    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__refetches_experiment_by_id(self, mock_detail, mock_success):
        """The re-fetch targets the experiment directly by ID rather than scanning the list."""
        DeploymentsCommand.experiment_start(
            TEST_DIR, name="v2 test", branch="v2-branch", traffic_percentage=50
        )

        self.proj.get_experiment.assert_called_once_with("exp-001")

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__success_json_output(self, mock_json):
        """Successful start emits JSON with success=True and the experiment payload."""
        DeploymentsCommand.experiment_start(
            TEST_DIR,
            name="v2 test",
            branch="v2-branch",
            traffic_percentage=50,
            output_json=True,
        )

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["experiment"]["id"], "exp-001")

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__name_is_stripped(self, mock_json):
        """Leading/trailing whitespace in name is stripped before calling the API."""
        DeploymentsCommand.experiment_start(
            TEST_DIR,
            name="  v2 test  ",
            branch="v2-branch",
            traffic_percentage=50,
            output_json=True,
        )

        self.proj.create_experiment.assert_called_once_with("v2 test", "br-v2", 50)

    # -- Interactive prompts --

    @patch("questionary.text")
    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__interactive_name_and_traffic(self, mock_detail, mock_success, mock_text):
        """When name and traffic are None, prompts interactively with defaults."""
        mock_text.return_value.ask.side_effect = ["my experiment", "30"]

        DeploymentsCommand.experiment_start(
            TEST_DIR, name=None, branch="v2-branch", traffic_percentage=None
        )

        self.assertEqual(mock_text.call_count, 2)
        name_call = mock_text.call_args_list[0]
        self.assertIn("name", name_call[0][0].lower())
        self.assertIn("Experiment", name_call[1]["default"])
        traffic_call = mock_text.call_args_list[1]
        self.assertIn("1-99", traffic_call[0][0])
        self.assertEqual(traffic_call[1]["default"], "50")
        self.proj.create_experiment.assert_called_once_with("my experiment", "br-v2", 30)

    @patch("questionary.text")
    @patch("poly.output.console.warning")
    def test_start__interactive_name_aborted_exits_zero(self, mock_warning, mock_text):
        """Cancelling the name prompt aborts cleanly with exit code 0."""
        mock_text.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name=None, branch="v2-branch", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 0)
        mock_warning.assert_called_once()
        self.proj.create_experiment.assert_not_called()

    @patch("questionary.select")
    @patch("questionary.Choice")
    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__interactive_branch_picker_excludes_main(
        self, mock_detail, mock_success, mock_choice, mock_select
    ):
        """When branch is None, prompts with every branch except 'main'."""
        self.proj.get_branches.return_value = (
            "main",
            {
                "main": {"branchId": "br-main"},
                "v2-branch": {"branchId": "br-v2"},
                "v3-branch": {"branchId": "br-v3"},
            },
        )
        mock_choice.side_effect = lambda **kw: kw
        mock_select.return_value.ask.return_value = "v3-branch"

        DeploymentsCommand.experiment_start(
            TEST_DIR, name="test", branch=None, traffic_percentage=50
        )

        choice_titles = [c["title"] for c in mock_select.call_args[1]["choices"]]
        self.assertEqual(choice_titles, ["v2-branch", "v3-branch"])
        self.proj.create_experiment.assert_called_once_with("test", "br-v3", 50)

    @patch("questionary.select")
    @patch("questionary.Choice")
    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_start__interactive_branch_picker_excludes_child_branches(
        self, mock_detail, mock_success, mock_choice, mock_select
    ):
        """A branch whose parent isn't main is excluded — the server rejects it as a variant."""
        self.proj.get_branches.return_value = (
            "main",
            {
                "main": {"branchId": "br-main"},
                "v2-branch": {"branchId": "br-v2", "parentBranchId": "main"},
                "child-of-v2": {"branchId": "br-v2-child", "parentBranchId": "br-v2"},
            },
        )
        mock_choice.side_effect = lambda **kw: kw
        mock_select.return_value.ask.return_value = "v2-branch"

        DeploymentsCommand.experiment_start(
            TEST_DIR, name="test", branch=None, traffic_percentage=50
        )

        choice_titles = [c["title"] for c in mock_select.call_args[1]["choices"]]
        self.assertEqual(choice_titles, ["v2-branch"])

    @patch("questionary.select")
    @patch("questionary.Choice")
    @patch("poly.output.console.warning")
    def test_start__interactive_branch_picker_aborted_exits_zero(
        self, mock_warning, mock_choice, mock_select
    ):
        """Cancelling the branch picker aborts cleanly with exit code 0."""
        mock_choice.side_effect = lambda **kw: kw
        mock_select.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch=None, traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 0)
        self.proj.create_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_start__interactive_no_eligible_branches_exits(self, mock_error):
        """If 'main' is the only branch, there is nothing to pick as a variant."""
        self.proj.get_branches.return_value = ("main", {"main": {"branchId": "br-main"}})

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch=None, traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No eligible branches", mock_error.call_args[0][0])

    @patch("questionary.text")
    @patch("poly.output.console.error")
    def test_start__interactive_traffic_not_a_number(self, mock_error, mock_text):
        """Non-numeric interactive traffic input exits with error."""
        mock_text.return_value.ask.side_effect = ["my experiment", "abc"]

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name=None, branch="v2-branch", traffic_percentage=None
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("integer", mock_error.call_args[0][0])

    # -- Branch validation --

    @patch("poly.output.console.error")
    def test_start__unknown_branch_exits_with_error(self, mock_error):
        """An explicit branch name that doesn't exist exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="no-such-branch", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No branch found named 'no-such-branch'", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__unknown_branch_json(self, mock_json):
        """An unknown branch name in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR,
                name="test",
                branch="no-such-branch",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("No branch found", payload["error"])

    @patch("poly.output.console.error")
    def test_start__explicit_child_branch_rejected(self, mock_error):
        """A branch whose parent isn't main is rejected — the server only tests top-level branches."""
        self.proj.get_branches.return_value = (
            "main",
            {
                "main": {"branchId": "br-main"},
                "v2-branch": {"branchId": "br-v2", "parentBranchId": "main"},
                "child-of-v2": {"branchId": "br-v2-child", "parentBranchId": "br-v2"},
            },
        )

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="child-of-v2", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("is not a top-level branch", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__explicit_child_branch_rejected_json(self, mock_json):
        """A child branch in JSON mode emits error JSON and exits."""
        self.proj.get_branches.return_value = (
            "main",
            {
                "main": {"branchId": "br-main"},
                "v2-branch": {"branchId": "br-v2", "parentBranchId": "main"},
                "child-of-v2": {"branchId": "br-v2-child", "parentBranchId": "br-v2"},
            },
        )

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR,
                name="test",
                branch="child-of-v2",
                traffic_percentage=50,
                output_json=True,
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("is not a top-level branch", payload["error"])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_start__main_branch_rejected(self, mock_error):
        """'main' is the implicit control, so it can't also be the variant."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="main", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Cannot test 'main' against itself", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__main_branch_rejected_json(self, mock_json):
        """'--branch main' in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="main", traffic_percentage=50, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("Cannot test 'main' against itself", payload["error"])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_start__branch_fetch_failure_exits(self, mock_error):
        """A failure fetching branches is reported and exits with error."""
        self.proj.get_branches.side_effect = Exception("boom")

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Failed to fetch branches", mock_error.call_args[0][0])

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__branch_fetch_failure_json(self, mock_json):
        """A failure fetching branches in JSON mode emits error JSON and exits."""
        self.proj.get_branches.side_effect = Exception("boom")

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=50, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Failed to fetch branches", mock_json.call_args[0][0]["error"])

    @patch("questionary.text")
    @patch("poly.output.console.warning")
    def test_start__interactive_traffic_aborted_exits_zero(self, mock_warning, mock_text):
        """Cancelling the traffic prompt aborts cleanly with exit code 0."""
        mock_text.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=None
            )

        self.assertEqual(ctx.exception.code, 0)
        self.proj.create_experiment.assert_not_called()

    # -- JSON mode requires flags --

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__json_mode_requires_name(self, mock_json):
        """JSON mode with name=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name=None, branch="v2-branch", traffic_percentage=50, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("--name", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__json_mode_requires_branch(self, mock_json):
        """JSON mode with branch=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch=None, traffic_percentage=50, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("--branch", mock_json.call_args[0][0]["error"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__json_mode_requires_traffic(self, mock_json):
        """JSON mode with traffic=None exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=None, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("--traffic", mock_json.call_args[0][0]["error"])

    # -- Validation: name --

    @patch("poly.output.console.error")
    def test_start__whitespace_only_name_exits_with_error(self, mock_error):
        """Whitespace-only name triggers error and sys.exit(1)."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="   ", branch="v2-branch", traffic_percentage=50
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("required", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__empty_name_json_mode_exits_with_error(self, mock_json):
        """Empty name in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="", branch="v2-branch", traffic_percentage=50, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("required", payload["error"])

    # -- Validation: traffic_percentage (1-99, unlike ab-test's 0-100) --

    @patch("poly.output.console.error")
    def test_start__traffic_zero_is_rejected(self, mock_error):
        """0% would route nothing to the variant, so it's rejected."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=0
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("1 and 99", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_start__traffic_100_is_rejected(self, mock_error):
        """100% would route nothing to the control, so it's rejected."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=100
            )

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("1 and 99", mock_error.call_args[0][0])
        self.proj.create_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__traffic_out_of_range_json_mode(self, mock_json):
        """Out-of-range traffic in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=100, output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("1 and 99", payload["error"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__traffic_1_is_valid(self, mock_json):
        """Traffic percentage of 1 is the lowest accepted value."""
        DeploymentsCommand.experiment_start(
            TEST_DIR, name="test", branch="v2-branch", traffic_percentage=1, output_json=True
        )

        self.proj.create_experiment.assert_called_once_with("test", "br-v2", 1)

    @patch("poly.cli_commands.deployments.json_print")
    def test_start__traffic_99_is_valid(self, mock_json):
        """Traffic percentage of 99 is the highest accepted value."""
        DeploymentsCommand.experiment_start(
            TEST_DIR, name="test", branch="v2-branch", traffic_percentage=99, output_json=True
        )

        self.proj.create_experiment.assert_called_once_with("test", "br-v2", 99)

    # -- HTTP errors (propagated to top-level handler) --

    def test_start__http_error_propagates(self):
        """HTTPError from create_experiment propagates to the top-level handler."""
        self.proj.create_experiment.side_effect = _make_http_error(
            409, {"error": "An experiment is already active."}
        )

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_start(
                TEST_DIR, name="test", branch="v2-branch", traffic_percentage=50
            )


class ExperimentListTest(unittest.TestCase):
    """Tests for DeploymentsCommand.experiment_list."""

    def setUp(self):
        patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.experiments_enabled = True
        self.proj.get_branches.return_value = ("main", dict(SAMPLE_BRANCHES))
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    @patch("poly.output.console.error")
    def test_list__experiments_disabled_exits_with_error(self, mock_error):
        """An ineligible project is refused before listing."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_list(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_error.call_args[0][0])
        self.proj.list_experiments.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_list__experiments_disabled_json_exits_with_error(self, mock_json):
        """An ineligible project in JSON mode emits an error payload and exits."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_list(TEST_DIR, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_json.call_args[0][0]["error"])

    @patch("poly.output.console.print_experiments")
    def test_list__success_rich_output(self, mock_print):
        """Successful list calls print_experiments with results and the branch map."""
        self.proj.list_experiments.return_value = [SAMPLE_EXPERIMENT]

        DeploymentsCommand.experiment_list(TEST_DIR, limit=10)

        self.proj.list_experiments.assert_called_once_with(limit=10, offset=None)
        mock_print.assert_called_once_with([SAMPLE_EXPERIMENT], branches=SAMPLE_BRANCH_MAP)

    @patch("poly.cli_commands.deployments.json_print")
    def test_list__success_json_output(self, mock_json):
        """Successful list emits JSON with success=True and the experiments array."""
        self.proj.list_experiments.return_value = [SAMPLE_EXPERIMENT]

        DeploymentsCommand.experiment_list(TEST_DIR, limit=5, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["experiments"], [SAMPLE_EXPERIMENT])

    @patch("poly.output.console.print_experiments")
    def test_list__empty_results_skip_branch_lookup(self, mock_print):
        """Empty results print an empty list without fetching branches."""
        self.proj.list_experiments.return_value = []

        DeploymentsCommand.experiment_list(TEST_DIR)

        mock_print.assert_called_once_with([], branches={})
        self.proj.get_branches.assert_not_called()

    @patch("poly.output.console.print_experiments")
    def test_list__branch_lookup_failure_falls_back_to_empty_map(self, mock_print):
        """If branches can't be fetched, the list still prints with raw branch IDs."""
        self.proj.list_experiments.return_value = [SAMPLE_EXPERIMENT]
        self.proj.get_branches.side_effect = Exception("boom")

        DeploymentsCommand.experiment_list(TEST_DIR)

        mock_print.assert_called_once_with([SAMPLE_EXPERIMENT], branches={})

    @patch("poly.cli_commands.deployments.json_print")
    def test_list__limit_and_offset_forwarded(self, mock_json):
        """Custom limit and offset are forwarded to project.list_experiments."""
        self.proj.list_experiments.return_value = []

        DeploymentsCommand.experiment_list(TEST_DIR, limit=25, offset=50, output_json=True)

        self.proj.list_experiments.assert_called_once_with(limit=25, offset=50)

    def test_list__http_error_propagates(self):
        """HTTPError from list_experiments propagates to the top-level handler."""
        self.proj.list_experiments.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_list(TEST_DIR)


class ExperimentActiveTest(unittest.TestCase):
    """Tests for DeploymentsCommand.experiment_active."""

    def setUp(self):
        patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.experiments_enabled = True
        self.proj.get_branches.return_value = ("main", dict(SAMPLE_BRANCHES))
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    @patch("poly.output.console.error")
    def test_active__experiments_disabled_exits_with_error(self, mock_error):
        """An ineligible project is refused before looking up the active experiment."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_active(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_error.call_args[0][0])
        self.proj.get_active_experiment.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_active__experiments_disabled_json_exits_with_error(self, mock_json):
        """An ineligible project in JSON mode emits an error payload and exits."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_active(TEST_DIR, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_json.call_args[0][0]["error"])

    @patch("poly.output.console.print_experiment_detail")
    def test_active__found_rich_output(self, mock_detail):
        """Active experiment found prints detail with the branch map."""
        self.proj.get_active_experiment.return_value = SAMPLE_EXPERIMENT

        DeploymentsCommand.experiment_active(TEST_DIR)

        mock_detail.assert_called_once_with(SAMPLE_EXPERIMENT, branches=SAMPLE_BRANCH_MAP)

    @patch("poly.cli_commands.deployments.json_print")
    def test_active__found_json_output(self, mock_json):
        """Active experiment found emits JSON with the experiment."""
        self.proj.get_active_experiment.return_value = SAMPLE_EXPERIMENT

        DeploymentsCommand.experiment_active(TEST_DIR, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["experiment"]["id"], "exp-001")

    @patch("poly.output.console.print_experiment_detail")
    def test_active__none_found_rich(self, mock_detail):
        """No active experiment passes the empty record through with no branch lookup."""
        self.proj.get_active_experiment.return_value = {}

        DeploymentsCommand.experiment_active(TEST_DIR)

        mock_detail.assert_called_once_with({}, branches={})
        self.proj.get_branches.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_active__none_found_json_is_null(self, mock_json):
        """No active experiment emits JSON with experiment: None (not an empty dict)."""
        self.proj.get_active_experiment.return_value = {}

        DeploymentsCommand.experiment_active(TEST_DIR, output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertIsNone(payload["experiment"])

    def test_active__http_error_propagates(self):
        """HTTPError from get_active_experiment propagates to the top-level handler."""
        self.proj.get_active_experiment.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_active(TEST_DIR)


class ExperimentUpdateTest(unittest.TestCase):
    """Tests for DeploymentsCommand.experiment_update."""

    def setUp(self):
        patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.experiments_enabled = True
        self.proj.get_branches.return_value = ("main", dict(SAMPLE_BRANCHES))
        self.proj.get_active_experiment.return_value = dict(SAMPLE_EXPERIMENT)
        self.proj.update_experiment.return_value = dict(SAMPLE_EXPERIMENT, traffic_percentage=30)
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Gate: require_experiments_enabled --

    @patch("poly.output.console.error")
    def test_update__experiments_disabled_exits_with_error(self, mock_error):
        """An ineligible project is refused before anything is updated."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_error.call_args[0][0])
        self.proj.update_experiment.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_update__experiments_disabled_json_exits_with_error(self, mock_json):
        """An ineligible project in JSON mode emits an error payload and exits."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_json.call_args[0][0]["error"])

    # -- Happy path --

    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_update__traffic_only(self, mock_detail, mock_success):
        """Updating traffic alone leaves the name untouched."""
        DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30)

        self.proj.update_experiment.assert_called_once_with(
            "exp-001", name=None, branch_id="br-v2", traffic_percentage=30
        )
        mock_success.assert_called_once()
        mock_detail.assert_called_once()

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__name_only(self, mock_json):
        """Updating the name alone leaves the traffic split untouched."""
        DeploymentsCommand.experiment_update(TEST_DIR, name="renamed", output_json=True)

        self.proj.update_experiment.assert_called_once_with(
            "exp-001", name="renamed", branch_id="br-v2", traffic_percentage=None
        )

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__name_and_traffic(self, mock_json):
        """Name and traffic can be updated together in one call."""
        DeploymentsCommand.experiment_update(
            TEST_DIR, name="renamed", traffic_percentage=30, output_json=True
        )

        self.proj.update_experiment.assert_called_once_with(
            "exp-001", name="renamed", branch_id="br-v2", traffic_percentage=30
        )
        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["experiment"]["traffic_percentage"], 30)

    # -- Neither name nor traffic given --

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__json_mode_requires_name_or_traffic(self, mock_json):
        """JSON mode with neither --name nor --traffic exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("--name or --traffic", payload["error"])
        self.proj.update_experiment.assert_not_called()

    @patch("questionary.text")
    @patch("poly.output.console.success")
    @patch("poly.output.console.print_experiment_detail")
    def test_update__interactive_prompts_for_traffic(self, mock_detail, mock_success, mock_text):
        """With neither flag in rich mode, prompts for traffic defaulting to the current value."""
        experiment = dict(SAMPLE_EXPERIMENT)
        experiment["versions"] = [
            {"branch_id": "br-main", "kind": "control", "traffic_percentage": 60},
            {"branch_id": "br-v2", "kind": "release", "traffic_percentage": 40},
        ]
        self.proj.get_active_experiment.return_value = experiment
        mock_text.return_value.ask.return_value = "30"

        DeploymentsCommand.experiment_update(TEST_DIR)

        self.assertEqual(mock_text.call_args[1]["default"], "40")
        self.proj.update_experiment.assert_called_once_with(
            "exp-001", name=None, branch_id="br-v2", traffic_percentage=30
        )

    @patch("questionary.text")
    @patch("poly.output.console.warning")
    def test_update__interactive_aborted_exits_zero(self, mock_warning, mock_text):
        """Cancelling the traffic prompt aborts cleanly with exit code 0."""
        mock_text.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR)

        self.assertEqual(ctx.exception.code, 0)
        self.proj.update_experiment.assert_not_called()

    @patch("questionary.text")
    @patch("poly.output.console.error")
    def test_update__interactive_traffic_not_a_number(self, mock_error, mock_text):
        """Non-numeric interactive traffic input exits with error."""
        mock_text.return_value.ask.return_value = "abc"

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("integer", mock_error.call_args[0][0])

    # -- No active experiment --

    @patch("poly.output.console.error")
    def test_update__no_active_experiment_exits(self, mock_error):
        """No active experiment exits with error."""
        self.proj.get_active_experiment.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_error.call_args[0][0])
        self.proj.update_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__no_active_experiment_json_exits(self, mock_json):
        """No active experiment in JSON mode exits with error JSON."""
        self.proj.get_active_experiment.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_json.call_args[0][0]["error"])

    # -- Validation: traffic_percentage (1-99) --

    @patch("poly.output.console.error")
    def test_update__traffic_zero_is_rejected(self, mock_error):
        """0% traffic is rejected."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=0)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("1 and 99", mock_error.call_args[0][0])
        self.proj.update_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_update__traffic_100_is_rejected(self, mock_error):
        """100% traffic is rejected."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=100)

        self.assertEqual(ctx.exception.code, 1)
        self.proj.update_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__traffic_out_of_range_json_mode(self, mock_json):
        """Out-of-range traffic in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=0, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("1 and 99", payload["error"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__traffic_1_and_99_are_valid(self, mock_json):
        """The 1 and 99 boundaries are both accepted."""
        DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=1, output_json=True)
        DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=99, output_json=True)

        traffic_sent = [
            c.kwargs["traffic_percentage"] for c in self.proj.update_experiment.call_args_list
        ]
        self.assertEqual(traffic_sent, [1, 99])

    # -- HTTP errors --

    def test_update__http_error_propagates(self):
        """HTTPError from update_experiment propagates to the top-level handler."""
        self.proj.update_experiment.side_effect = _make_http_error(400)

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30)

    # -- Legacy A/B test record (versions: []) --

    @patch("poly.output.console.error")
    def test_update__legacy_record_exits_with_error(self, mock_error):
        """A record with no branch-based versions exits cleanly, pointing to ab-test end."""
        self.proj.get_active_experiment.return_value = dict(LEGACY_AB_TEST_EXPERIMENT)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("ab-test end", mock_error.call_args[0][0])
        self.proj.update_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_update__legacy_record_exits_with_error_json(self, mock_json):
        """A legacy record in JSON mode emits error JSON pointing to ab-test end."""
        self.proj.get_active_experiment.return_value = dict(LEGACY_AB_TEST_EXPERIMENT)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_update(TEST_DIR, traffic_percentage=30, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("ab-test end", payload["error"])
        self.proj.update_experiment.assert_not_called()


class ExperimentEndTest(unittest.TestCase):
    """Tests for DeploymentsCommand.experiment_end.

    Unlike ab_test_end, ending an experiment never calls promote_deployment: the
    platform's /end endpoint redeploys the winning branch itself.
    """

    def setUp(self):
        patcher = patch("poly.cli_commands.deployments.load_project")
        self.mock_load = patcher.start()
        self.proj = MagicMock()
        self.proj.experiments_enabled = True
        self.proj.get_branches.return_value = ("main", dict(SAMPLE_BRANCHES))
        self.proj.get_active_experiment.return_value = dict(SAMPLE_EXPERIMENT)
        self.proj.end_experiment.return_value = dict(
            SAMPLE_EXPERIMENT, ended_at="2026-01-01T00:00:00Z"
        )
        self.mock_load.return_value = self.proj
        self.addCleanup(patch.stopall)

    # -- Gate: require_experiments_enabled --

    @patch("poly.output.console.error")
    def test_end__experiments_disabled_exits_with_error(self, mock_error):
        """An ineligible project is refused before anything is ended."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_error.call_args[0][0])
        self.proj.end_experiment.assert_not_called()

    @patch("poly.cli_commands.shared.json_print")
    def test_end__experiments_disabled_json_exits_with_error(self, mock_json):
        """An ineligible project in JSON mode emits an error payload and exits."""
        self.proj.experiments_enabled = False

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn(GATE_MESSAGE, mock_json.call_args[0][0]["error"])

    # -- Happy path: control wins --

    @patch("poly.output.console.success")
    @patch("poly.output.console.info")
    def test_end__control_wins_rich_output(self, mock_info, mock_success):
        """Choosing the control ends the experiment without a redeploy message."""
        DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main")

        self.proj.end_experiment.assert_called_once_with("exp-001", "br-main")
        self.assertIn("Winner: main", mock_success.call_args[0][0])
        info_messages = [c[0][0] for c in mock_info.call_args_list]
        self.assertFalse(any("redeployed" in m for m in info_messages))
        self.proj.promote_deployment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__control_wins_json_output(self, mock_json):
        """Ending in JSON mode emits the ended experiment record."""
        DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main", output_json=True)

        payload = mock_json.call_args[0][0]
        self.assertTrue(payload["success"])
        self.assertEqual(payload["experiment"]["id"], "exp-001")
        self.assertNotIn("promoted", payload)
        self.proj.promote_deployment.assert_not_called()

    # -- Happy path: variant wins --

    @patch("poly.output.console.success")
    @patch("poly.output.console.info")
    def test_end__variant_wins_does_not_promote(self, mock_info, mock_success):
        """Choosing the variant reports the redeploy but never calls promote_deployment."""
        DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="v2-branch")

        self.proj.end_experiment.assert_called_once_with("exp-001", "br-v2")
        self.proj.promote_deployment.assert_not_called()
        mock_success.assert_called_once()
        self.assertIn("Winner: v2-branch", mock_success.call_args[0][0])
        self.assertIn("redeployed to live", mock_info.call_args[0][0])

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__variant_wins_json_does_not_promote(self, mock_json):
        """Variant win in JSON mode also never calls promote_deployment."""
        DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="v2-branch", output_json=True)

        self.proj.end_experiment.assert_called_once_with("exp-001", "br-v2")
        self.proj.promote_deployment.assert_not_called()
        self.assertTrue(mock_json.call_args[0][0]["success"])

    # -- Interactive prompt flow --

    @patch("questionary.select")
    @patch("questionary.Choice")
    @patch("poly.output.console.success")
    @patch("poly.output.console.info")
    def test_end__interactive_prompt_selects_winner(
        self, mock_info, mock_success, mock_choice, mock_select
    ):
        """Interactive mode offers control and variant by branch name, then ends."""
        mock_choice.side_effect = lambda **kw: kw
        mock_select.return_value.ask.return_value = "br-v2"

        DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

        choices = mock_select.call_args[1]["choices"]
        self.assertEqual(
            choices,
            [
                {"title": "Control — main", "value": "br-main"},
                {"title": "Variant — v2-branch", "value": "br-v2"},
            ],
        )
        self.proj.end_experiment.assert_called_once_with("exp-001", "br-v2")
        self.proj.promote_deployment.assert_not_called()

    @patch("questionary.select")
    @patch("questionary.Choice")
    @patch("poly.output.console.warning")
    @patch("poly.output.console.info")
    def test_end__interactive_user_aborts(self, mock_info, mock_warning, mock_choice, mock_select):
        """User aborting the interactive prompt exits with 0."""
        mock_choice.side_effect = lambda **kw: kw
        mock_select.return_value.ask.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

        self.assertEqual(ctx.exception.code, 0)
        mock_warning.assert_called_once()
        self.proj.end_experiment.assert_not_called()

    # -- Validation --

    @patch("poly.output.console.error")
    @patch("poly.output.console.info")
    def test_end__unknown_branch_exits_with_error(self, mock_info, mock_error):
        """A --chosen-branch name that doesn't exist exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="no-such-branch")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No branch found named 'no-such-branch'", mock_error.call_args[0][0])
        self.proj.end_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__unknown_branch_json(self, mock_json):
        """An unknown --chosen-branch in JSON mode emits error JSON and exits."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(
                TEST_DIR, chosen_branch="no-such-branch", output_json=True
            )

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("No branch found", payload["error"])

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__json_mode_without_chosen_branch_exits_with_error(self, mock_json):
        """JSON mode requires --chosen-branch; omitting it exits with error."""
        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None, output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("--chosen-branch", payload["error"])
        self.proj.end_experiment.assert_not_called()

    # -- Branch fetch failures surface instead of being swallowed --

    @patch("poly.output.console.error")
    def test_end__branch_fetch_failure_surfaces_not_swallowed(self, mock_error):
        """A failure fetching branches is reported as-is, not masked as 'branch not found'."""
        self.proj.get_branches.side_effect = _make_http_error(500)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main")

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Failed to fetch branches", mock_error.call_args[0][0])
        self.proj.end_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__branch_fetch_failure_json_surfaces_not_swallowed(self, mock_json):
        """A branch fetch failure in JSON mode is reported as-is in the error payload."""
        self.proj.get_branches.side_effect = _make_http_error(500)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("Failed to fetch branches", payload["error"])
        self.proj.end_experiment.assert_not_called()

    # -- No active experiment --

    @patch("poly.output.console.error")
    def test_end__no_active_experiment_exits(self, mock_error):
        """If no active experiment exists, exits with error."""
        self.proj.get_active_experiment.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_error.call_args[0][0])
        self.proj.end_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__no_active_experiment_json_exits(self, mock_json):
        """If no active experiment exists in JSON mode, exits with error JSON."""
        self.proj.get_active_experiment.return_value = {}

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("No active", mock_json.call_args[0][0]["error"])

    # -- HTTP errors (propagated to top-level handler) --

    def test_end__http_error_fetching_active_propagates(self):
        """HTTPError when fetching the active experiment propagates to the top-level handler."""
        self.proj.get_active_experiment.side_effect = _make_http_error(500)

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

    @patch("poly.output.console.info")
    def test_end__http_error_ending_experiment_propagates(self, mock_info):
        """HTTPError from end_experiment propagates to the top-level handler."""
        self.proj.end_experiment.side_effect = _make_http_error(
            409, {"error": "Experiment already ended."}
        )

        with self.assertRaises(requests.HTTPError):
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main")

    # -- Legacy A/B test record (versions: []) --

    @patch("poly.output.console.error")
    def test_end__legacy_record_exits_with_error(self, mock_error):
        """A record with no branch-based versions exits cleanly, pointing to ab-test end."""
        self.proj.get_active_experiment.return_value = dict(LEGACY_AB_TEST_EXPERIMENT)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("ab-test end", mock_error.call_args[0][0])
        self.proj.get_branches.assert_not_called()
        self.proj.end_experiment.assert_not_called()

    @patch("poly.cli_commands.deployments.json_print")
    def test_end__legacy_record_exits_with_error_json(self, mock_json):
        """A legacy record in JSON mode emits error JSON pointing to ab-test end."""
        self.proj.get_active_experiment.return_value = dict(LEGACY_AB_TEST_EXPERIMENT)

        with self.assertRaises(SystemExit) as ctx:
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch="main", output_json=True)

        self.assertEqual(ctx.exception.code, 1)
        payload = mock_json.call_args[0][0]
        self.assertFalse(payload["success"])
        self.assertIn("ab-test end", payload["error"])
        self.proj.get_branches.assert_not_called()
        self.proj.end_experiment.assert_not_called()

    @patch("poly.output.console.error")
    def test_end__legacy_record_exits_before_building_interactive_prompt(self, mock_error):
        """The guard fires before the interactive prompt, avoiding a title-as-id Choice."""
        self.proj.get_active_experiment.return_value = dict(LEGACY_AB_TEST_EXPERIMENT)

        with self.assertRaises(SystemExit):
            DeploymentsCommand.experiment_end(TEST_DIR, chosen_branch=None)

        self.proj.end_experiment.assert_not_called()


if __name__ == "__main__":
    unittest.main()
