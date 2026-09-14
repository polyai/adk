"""Tests for the call command.

These mock the voice stack (``poly.call.client``) so they run without importing the
native WebRTC/audio dependencies.

Copyright PolyAI Limited
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from poly.call.session import CallSession
from poly.cli_commands.call import CallCommand


def make_project(branch: str = "feature-x") -> MagicMock:
    """A mock AgentStudioProject on the given branch."""
    project = MagicMock()
    project.branch_id = branch
    project.get_current_branch.return_value = branch
    project.account_id = "acc-1"
    project.project_id = "proj-1"
    project.create_call_session.return_value = CallSession(
        account_id="acc-1",
        project_id="proj-1",
        variant_id="",
        artifact_version="a",
        lambda_deployment_version="l",
        auth_token="t",
        gateway_ws_url="wss://gw",
        mode="end-to-end",
    )
    return project


def fake_client_module(recorder: list) -> types.ModuleType:
    """A stand-in for poly.call.client that records run_call invocations."""
    module = types.ModuleType("poly.call.client")

    class CallError(Exception):
        pass

    async def run_call(session, caller, *, aec=False):
        recorder.append((session, caller, aec))

    module.CallError = CallError
    module.run_call = run_call
    return module


class CallCommandTest(unittest.TestCase):
    """Tests for CallCommand.call."""

    @patch("poly.cli_commands.call.load_project")
    def test_main_branch_is_rejected(self, mock_load):
        project = make_project(branch="main")
        mock_load.return_value = project

        with self.assertRaises(SystemExit):
            CallCommand.call("/path")

        project.create_call_session.assert_not_called()

    @patch("poly.cli_commands.call.load_project")
    def test_draft_call_invokes_run_call(self, mock_load):
        project = make_project(branch="feature-x")
        mock_load.return_value = project
        recorder: list = []

        with patch.dict(sys.modules, {"poly.call.client": fake_client_module(recorder)}):
            CallCommand.call("/path", variant="v1", mode="echo", aec=False)

        project.create_call_session.assert_called_once_with("draft", variant="v1", mode="echo")
        self.assertEqual(len(recorder), 1)
        session, _caller, aec = recorder[0]
        self.assertEqual(session.project_id, "proj-1")
        self.assertFalse(aec)

    @patch("poly.cli_commands.call.load_project")
    def test_aec_on_by_default(self, mock_load):
        mock_load.return_value = make_project(branch="feature-x")
        recorder: list = []

        with patch.dict(
            sys.modules,
            {
                "poly.call.client": fake_client_module(recorder),
                "pywebrtc_audio": types.ModuleType("pywebrtc_audio"),  # dep present
            },
        ):
            CallCommand.call("/path")  # no aec arg -> defaults on

        self.assertEqual(len(recorder), 1)
        self.assertTrue(recorder[0][2])  # aec == True

    @patch("poly.cli_commands.call.load_project")
    def test_aec_missing_dep_degrades_gracefully(self, mock_load):
        project = make_project(branch="feature-x")
        mock_load.return_value = project
        recorder: list = []

        # Voice stack present, AEC lib absent: the call should proceed without AEC,
        # not abort.
        with patch.dict(
            sys.modules,
            {"poly.call.client": fake_client_module(recorder), "pywebrtc_audio": None},
        ):
            CallCommand.call("/path")  # default aec on

        project.create_call_session.assert_called_once()
        self.assertEqual(len(recorder), 1)
        self.assertFalse(recorder[0][2])  # degraded to aec == False

    @patch("poly.cli_commands.call.load_project")
    def test_broken_voice_deps_exit_with_hint(self, mock_load):
        mock_load.return_value = make_project(branch="feature-x")

        # A None entry in sys.modules makes the import raise ImportError (broken install).
        with patch.dict(sys.modules, {"poly.call.client": None}):
            with self.assertRaises(SystemExit):
                CallCommand.call("/path", aec=False)

    @patch("poly.cli_commands.call.load_project")
    def test_push_failure_aborts_before_calling(self, mock_load):
        project = make_project(branch="feature-x")
        project.push_project.return_value = (False, "boom", None)
        mock_load.return_value = project

        with self.assertRaises(SystemExit):
            CallCommand.call("/path", push_before_call=True)

        project.create_call_session.assert_not_called()


if __name__ == "__main__":
    unittest.main()
