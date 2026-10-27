"""Tests for the call command.

These mock the voice stack (``poly.call.client``) so they run without importing the
native WebRTC/audio dependencies.

Copyright PolyAI Limited
"""

import sys
import types
import unittest
from io import StringIO
from unittest.mock import MagicMock, patch

from rich.console import Console

from poly.call.session import CallSession
from poly.cli_commands.call import _CALL_EXTRA_INSTALL_COMMANDS, CallCommand, voice_deps_hint
from poly.cli_commands.update import UpdateCommand


def make_project(branch: str = "feature-x") -> MagicMock:
    """A mock AgentStudioProject on the given branch."""
    project = MagicMock()
    project.branch_id = branch
    project.get_current_branch.return_value = branch
    project.account_id = "acc-1"
    project.project_id = "proj-1"
    project.get_conversation_url.side_effect = (
        lambda cid: f"https://studio.poly.ai/acc-1/proj-1/conversations/{cid}"
    )
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

    async def run_call(session, caller, *, aec=False, call_sid=None):
        recorder.append((session, caller, aec, call_sid))

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
            CallCommand.call("/path", variant="v1", aec=False)

        project.create_call_session.assert_called_once_with("draft", variant="v1")
        self.assertEqual(len(recorder), 1)
        session, _caller, aec, call_sid = recorder[0]
        self.assertEqual(session.project_id, "proj-1")
        self.assertFalse(aec)
        self.assertTrue(call_sid.startswith("ADK-"))

    @patch("poly.call.aec.EchoCanceller")
    @patch("poly.cli_commands.call.load_project")
    def test_aec_on_by_default(self, mock_load, mock_canceller):
        mock_load.return_value = make_project(branch="feature-x")
        recorder: list = []

        # Canceller constructs cleanly (dep present and working) -> AEC stays on.
        with patch.dict(sys.modules, {"poly.call.client": fake_client_module(recorder)}):
            CallCommand.call("/path")  # no aec arg -> defaults on

        mock_canceller.assert_called_once()  # the probe ran
        self.assertEqual(len(recorder), 1)
        self.assertTrue(recorder[0][2])  # aec == True

    @patch("poly.call.aec.EchoCanceller", side_effect=RuntimeError("APM unavailable"))
    @patch("poly.cli_commands.call.load_project")
    def test_aec_missing_dep_degrades_gracefully(self, mock_load, _mock_canceller):
        project = make_project(branch="feature-x")
        mock_load.return_value = project
        recorder: list = []

        # AEC lib absent: the wrapper raises at construction; the call proceeds without
        # AEC rather than aborting.
        with patch.dict(sys.modules, {"poly.call.client": fake_client_module(recorder)}):
            CallCommand.call("/path")  # default aec on

        project.create_call_session.assert_called_once()
        self.assertEqual(len(recorder), 1)
        self.assertFalse(recorder[0][2])  # degraded to aec == False

    @patch("poly.call.aec.EchoCanceller", side_effect=Exception("native init failed"))
    @patch("poly.cli_commands.call.load_project")
    def test_aec_construction_failure_degrades_gracefully(self, mock_load, _mock_canceller):
        project = make_project(branch="feature-x")
        mock_load.return_value = project
        recorder: list = []

        # Dep present but the APM throws at construction: still degrade, don't crash.
        with patch.dict(sys.modules, {"poly.call.client": fake_client_module(recorder)}):
            CallCommand.call("/path")

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
    def test_missing_voice_deps_fail_before_loading_project(self, mock_load):
        """Without the call extra, the command exits before touching the project."""
        with patch.dict(sys.modules, {"poly.call.client": None}):
            with self.assertRaises(SystemExit):
                CallCommand.call("/path")

        mock_load.assert_not_called()

    @patch("poly.cli_commands.call.load_project")
    def test_missing_voice_deps_skip_push_before_call(self, mock_load):
        """'--push' is not honoured when the call could never start, so nothing is pushed."""
        project = make_project(branch="feature-x")
        mock_load.return_value = project

        with patch.dict(sys.modules, {"poly.call.client": None}):
            with self.assertRaises(SystemExit):
                CallCommand.call("/path", push_before_call=True)

        project.push_project.assert_not_called()

    @patch.object(UpdateCommand, "_detect_install_method", return_value="pip")
    def test_missing_voice_deps_hint_shows_call_extra_literally(self, _mock_method):
        """'[call]' in the install hint is printed as text, not swallowed as Rich markup."""
        stderr = StringIO()
        test_console = Console(file=stderr, width=200)

        with (
            patch("poly.output.console.err_console", test_console),
            patch.dict(sys.modules, {"poly.call.client": None}),
        ):
            with self.assertRaises(SystemExit):
                CallCommand.call("/path")

        self.assertIn('pip install "polyai-adk[call]"', stderr.getvalue())

    @patch("poly.cli_commands.call.load_project")
    def test_push_failure_aborts_before_calling(self, mock_load):
        project = make_project(branch="feature-x")
        project.push_project.return_value = (False, "boom", None)
        mock_load.return_value = project

        with self.assertRaises(SystemExit):
            CallCommand.call("/path", push_before_call=True)

        project.create_call_session.assert_not_called()


class VoiceDepsHintTest(unittest.TestCase):
    """Tests for voice_deps_hint, which says how to add the call extra to this install."""

    def _hint_for(self, method: str) -> str:
        """Build the hint as it would appear for the given install method."""
        with patch.object(UpdateCommand, "_detect_install_method", return_value=method):
            return voice_deps_hint()

    def test_every_install_method_has_a_command(self):
        """Each method _detect_install_method can return has an install command."""
        detectable_methods = {"editable", "ephemeral", "uv-tool", "pipx", "uv-pip", "pip"}

        self.assertEqual(set(_CALL_EXTRA_INSTALL_COMMANDS), detectable_methods)

    def test_editable_checkout_installs_extra_from_source(self):
        """A dev checkout adds the extra to its own editable install."""
        self.assertIn('uv pip install -e ".[call]"', self._hint_for("editable"))

    def test_ephemeral_environment_reruns_with_extra(self):
        """A uvx run has nothing to install into, so the hint reruns with the extra."""
        self.assertIn('uvx --from "polyai-adk[call]" poly call', self._hint_for("ephemeral"))

    def test_uv_tool_reinstalls_with_extra(self):
        """A uv tool install is reinstalled with the extra requested."""
        self.assertIn('uv tool install "polyai-adk[call]"', self._hint_for("uv-tool"))

    def test_pipx_force_reinstalls_with_extra(self):
        """pipx refuses to reinstall an existing tool without --force."""
        self.assertIn('pipx install --force "polyai-adk[call]"', self._hint_for("pipx"))

    def test_uv_pip_installs_extra_into_venv(self):
        """A uv-managed venv installs the extra with uv pip."""
        self.assertIn('uv pip install "polyai-adk[call]"', self._hint_for("uv-pip"))

    def test_pip_installs_extra_into_venv(self):
        """A plain venv installs the extra with pip."""
        self.assertIn('pip install "polyai-adk[call]"', self._hint_for("pip"))

    def test_hint_explains_why_the_extra_is_needed(self):
        """The hint names the call extra so the user knows what is missing."""
        self.assertIn("`call` extra", self._hint_for("pip"))


if __name__ == "__main__":
    unittest.main()
