"""Unit tests for ADK Console

Copyright PolyAI Limited
"""

import unittest
from collections import namedtuple
from unittest import mock

import requests

from poly.output import console

# Minimal stand-in for the TestCase objects `poll_test_run_live` expects:
# it only reads `.resource_id` and `.name`.
FakeTest = namedtuple("FakeTest", ["resource_id", "name"])


def _completed_run(test_id: str) -> dict:
    """A fully-completed test run response for a single passing test."""
    return {
        "status": "completed",
        "testHistory": [{"testCaseId": test_id, "status": "passed"}],
        "passedCount": 1,
        "failedCount": 0,
        "errorCount": 0,
        "testCaseCount": 1,
    }


class PollTestRunLiveTests(unittest.TestCase):
    """Tests for poll_test_run_live error resilience."""

    def setUp(self):
        # All tests pass poll_interval=0 so the loop's time.sleep is a no-op
        # and tests run instantly.
        self.matched_tests = [FakeTest(resource_id="tc-1", name="My Test")]

    def test_transient_errors_then_success_returns_completed_run(self):
        """Recovers from a few consecutive transient errors and returns the run."""
        completed = _completed_run("tc-1")
        # First 2 polls fail transiently, the 3rd succeeds with a completed run.
        get_test_run = mock.Mock(
            side_effect=[
                requests.exceptions.HTTPError("500 Server Error"),
                requests.exceptions.ConnectionError("connection reset"),
                completed,
            ]
        )

        result = console.poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=5,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 3)

    def test_error_counter_resets_after_successful_poll(self):
        """A successful poll resets the counter so later errors are tolerated again."""
        completed = _completed_run("tc-1")
        # Pattern: fail, fail, succeed(pending), fail, fail, succeed(done).
        # With max_consecutive_errors=3 this only completes if the counter
        # resets after the pending success in the middle.
        pending = {"status": "running", "testHistory": []}
        get_test_run = mock.Mock(
            side_effect=[
                requests.exceptions.HTTPError("boom"),
                requests.exceptions.HTTPError("boom"),
                pending,
                requests.exceptions.HTTPError("boom"),
                requests.exceptions.HTTPError("boom"),
                completed,
            ]
        )

        result = console.poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=3,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 6)

    def test_persistent_errors_give_up_and_return_empty_dict(self):
        """After max_consecutive_errors failures it gives up without raising."""
        get_test_run = mock.Mock(side_effect=requests.exceptions.ConnectionError("platform down"))

        result = console.poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
            max_consecutive_errors=2,
        )

        # No successful poll ever happened, so the abandoned run returns {}.
        self.assertEqual(result, {})
        self.assertEqual(get_test_run.call_count, 2)

    def test_happy_path_no_errors_returns_completed_run(self):
        """A clean run with no errors returns the completed response on first poll."""
        completed = _completed_run("tc-1")
        get_test_run = mock.Mock(return_value=completed)

        result = console.poll_test_run_live(
            get_test_run,
            test_run_id="run-123",
            matched_tests=self.matched_tests,
            poll_interval=0,
        )

        self.assertEqual(result, completed)
        self.assertEqual(get_test_run.call_count, 1)


if __name__ == "__main__":
    unittest.main()
