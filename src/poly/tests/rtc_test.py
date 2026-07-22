"""Tests for RTC (Real-Time Configuration) functionality.

Copyright PolyAI Limited
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from poly.cli_commands.rtc import (
    RTCCommand,
    _merge_rtc_file,
)
from poly.project import AgentStudioProject


class TestRTC(unittest.TestCase):
    """Test suite for poly rtc command."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_env_mapping_roundtrip(self):
        """Verify AgentStudioProject.RTC_ENV_TO_DIR and {v: k for k, v in AgentStudioProject.RTC_ENV_TO_DIR.items()} are consistent."""
        for env, dir_name in AgentStudioProject.RTC_ENV_TO_DIR.items():
            self.assertEqual(
                {v: k for k, v in AgentStudioProject.RTC_ENV_TO_DIR.items()}[dir_name], env
            )

    def test_env_mapping_coverage(self):
        """Verify all 3 standard environments are mapped."""
        self.assertEqual(len(AgentStudioProject.RTC_ENV_TO_DIR), 3)
        self.assertIn("sandbox", AgentStudioProject.RTC_ENV_TO_DIR)
        self.assertIn("pre-release", AgentStudioProject.RTC_ENV_TO_DIR)
        self.assertIn("live", AgentStudioProject.RTC_ENV_TO_DIR)

    def test_sandbox_maps_to_draft_and_sandbox(self):
        """Verify sandbox API env maps to draft_and_sandbox directory."""
        self.assertEqual(AgentStudioProject.RTC_ENV_TO_DIR["sandbox"], "draft_and_sandbox")

    def test_pre_release_maps_to_pre_release(self):
        """Verify pre-release API env maps to pre_release directory."""
        self.assertEqual(AgentStudioProject.RTC_ENV_TO_DIR["pre-release"], "pre_release")

    def test_live_maps_to_live(self):
        """Verify live API env maps to live directory."""
        self.assertEqual(AgentStudioProject.RTC_ENV_TO_DIR["live"], "live")

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_pull_all_envs(self, mock_load_project):
        """Verify rtc pull calls rtc_pull_env for all 3 environments."""
        mock_project = MagicMock()
        mock_project.rtc_pull_env.return_value = {
            "environment": "sandbox",
            "schema_file": "schema.json",
            "data_file": "data.json",
        }
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_pull(self.temp_dir, env="all", output_json=True)

        self.assertEqual(mock_project.rtc_pull_env.call_count, 3)
        envs_called = [c[0][0] for c in mock_project.rtc_pull_env.call_args_list]
        self.assertIn("sandbox", envs_called)
        self.assertIn("pre-release", envs_called)
        self.assertIn("live", envs_called)

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_pull_single_env(self, mock_load_project):
        """Verify rtc pull --env sandbox calls rtc_pull_env once."""
        mock_project = MagicMock()
        mock_project.rtc_pull_env.return_value = {
            "environment": "sandbox",
            "schema_file": "schema.json",
            "data_file": "data.json",
        }
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)

        mock_project.rtc_pull_env.assert_called_once_with(
            "sandbox", schema_only=False, data_only=False
        )

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_pull_creates_directories(self, mock_load_project):
        """Verify rtc pull delegates to project.rtc_pull_env."""
        mock_project = MagicMock()
        mock_project.rtc_pull_env.return_value = {
            "environment": "sandbox",
            "schema_file": "schema.json",
            "data_file": "data.json",
        }
        mock_load_project.return_value = mock_project

        result = RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)
        self.assertTrue(result["success"])
        mock_project.rtc_pull_env.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_pull_returns_files_written(self, mock_load_project):
        """Verify rtc pull returns the files_written from rtc_pull_env."""
        mock_project = MagicMock()
        expected = {
            "environment": "sandbox",
            "schema_file": "/path/schema.json",
            "data_file": "/path/data.json",
        }
        mock_project.rtc_pull_env.return_value = expected
        mock_load_project.return_value = mock_project

        result = RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["files_written"], [expected])

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_schema_and_variables(self, mock_load_project):
        """Verify rtc push reads files and calls rtc_push_to_api."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.get_rtc_last_updated.return_value = None
        mock_load_project.return_value = mock_project

        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
        mock_project._rtc_env_dir.return_value = sandbox_dir

        schema_obj = {"type": "object"}
        variables_obj = {"mock_api": False}

        with open(os.path.join(sandbox_dir, "schema.json"), "w") as f:
            json.dump(schema_obj, f)
        with open(os.path.join(sandbox_dir, "data.json"), "w") as f:
            json.dump(variables_obj, f)

        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}

        RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)

        mock_project.rtc_push_to_api.assert_called_once()
        call_kwargs = mock_project.rtc_push_to_api.call_args[1]
        self.assertEqual(call_kwargs["schema"], schema_obj)
        self.assertEqual(call_kwargs["variables"], variables_obj)

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_missing_schema_returns_error(self, mock_load_project):
        """Verify rtc push returns error if schema.json is missing."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
        mock_project._rtc_env_dir.return_value = sandbox_dir
        mock_load_project.return_value = mock_project

        with open(os.path.join(sandbox_dir, "data.json"), "w") as f:
            json.dump({}, f)

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)
        self.assertFalse(result["success"])
        self.assertIn("schema.json not found", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_missing_data_returns_error(self, mock_load_project):
        """Verify rtc push returns error if data.json is missing."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
        mock_project._rtc_env_dir.return_value = sandbox_dir
        mock_load_project.return_value = mock_project

        with open(os.path.join(sandbox_dir, "schema.json"), "w") as f:
            json.dump({}, f)

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)
        self.assertFalse(result["success"])
        self.assertIn("data.json not found", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_live_without_force_json_returns_error(self, mock_load_project):
        """Verify pushing to live in JSON mode without --force returns error."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        mock_project.get_rtc_last_updated.return_value = None
        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        mock_project._rtc_env_dir.return_value = live_dir
        mock_load_project.return_value = mock_project

        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({}, f)

        result = RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=True)
        self.assertFalse(result["success"])
        self.assertIn("--force", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_live_with_force_succeeds(self, mock_load_project):
        """Verify pushing to live with --force bypasses the safety gate."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "live"}
        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        mock_project._rtc_env_dir.return_value = live_dir
        mock_load_project.return_value = mock_project

        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)

        result = RTCCommand.rtc_push(self.temp_dir, env="live", force=True, output_json=True)
        self.assertTrue(result["success"])
        mock_project.rtc_push_to_api.assert_called_once()

    @patch("poly.cli_commands.rtc.questionary")
    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_live_interactive_confirm(self, mock_load_project, mock_questionary):
        """Verify interactive live push proceeds when user confirms."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.get_rtc_last_updated.return_value = None
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "live"}
        mock_questionary.confirm.return_value.ask.return_value = True

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        mock_project._rtc_env_dir.return_value = live_dir
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=False)

        mock_questionary.confirm.assert_called_once()
        mock_project.rtc_push_to_api.assert_called_once()

    @patch("poly.cli_commands.rtc.questionary")
    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_live_interactive_decline(self, mock_load_project, mock_questionary):
        """Verify interactive live push is cancelled when user declines."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.get_rtc_last_updated.return_value = None
        mock_questionary.confirm.return_value.ask.return_value = False

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        mock_project._rtc_env_dir.return_value = live_dir
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=False)

        mock_questionary.confirm.assert_called_once()
        mock_project.rtc_push_to_api.assert_not_called()


class TestRTCDriftProtection(unittest.TestCase):
    """Test suite for RTC drift protection on push."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sandbox_dir = os.path.join(
            self.temp_dir, "real_time_configuration", "draft_and_sandbox"
        )
        os.makedirs(self.sandbox_dir)
        with open(os.path.join(self.sandbox_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(self.sandbox_dir, "data.json"), "w") as f:
            json.dump({"key": "value"}, f)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("poly.cli_commands.rtc.load_project")
    def test_pull_calls_rtc_pull_env(self, mock_load_project):
        """Verify rtc pull calls project.rtc_pull_env for each environment."""
        mock_project = MagicMock()
        mock_project.rtc_pull_env.return_value = {
            "environment": "sandbox",
            "schema_file": "schema.json",
            "data_file": "data.json",
        }
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox")

        mock_project.rtc_pull_env.assert_called_once_with(
            "sandbox", schema_only=False, data_only=False
        )

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_detects_drift(self, mock_get_rtc, mock_load_project):
        """Verify push refuses when remote lastUpdated differs from local."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_project.get_rtc_base.return_value = (None, None)
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {"lastUpdated": "T2"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertFalse(result["success"])
        self.assertIn("no base version", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_allows_when_no_drift(self, mock_get_rtc, mock_load_project):
        """Verify push proceeds when remote lastUpdated matches local."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {"lastUpdated": "T1"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_project.rtc_push_to_api.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    def test_push_force_bypasses_drift_check(self, mock_load_project):
        """Verify --force skips drift check entirely."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}
        mock_load_project.return_value = mock_project

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", force=True)
        self.assertTrue(result["success"])
        mock_project.rtc_push_to_api.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    def test_push_no_metadata_warns_and_proceeds(self, mock_load_project):
        """Verify push proceeds with warning when no metadata exists."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = None
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}
        mock_load_project.return_value = mock_project

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_project.rtc_push_to_api.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_updates_metadata_after_success(self, mock_get_rtc, mock_load_project):
        """Verify push calls rtc_push_to_api which handles metadata update."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {"lastUpdated": "T1"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_project.rtc_push_to_api.assert_called_once()


class TestRTCMerge(unittest.TestCase):
    """Test suite for RTC 3-way merge on push."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sandbox_dir = os.path.join(
            self.temp_dir, "real_time_configuration", "draft_and_sandbox"
        )
        os.makedirs(self.sandbox_dir)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("poly.cli_commands.rtc.load_project")
    def test_pull_stores_base_in_metadata(self, mock_load_project):
        """Verify rtc pull stores base copies in project metadata."""
        mock_project = MagicMock()
        mock_project.rtc_pull_env.return_value = {
            "environment": "sandbox",
            "schema_file": "schema.json",
            "data_file": "data.json",
        }
        mock_load_project.return_value = mock_project

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox")

        mock_project.rtc_pull_env.assert_called_once()
        # set_rtc_base is called inside rtc_pull_env on the real project

    def test_merge_clean_non_overlapping_changes(self):
        """Verify clean merge when local and remote change different fields."""
        base = {"a": 1, "b": 2, "c": 3}
        local = {"a": 10, "b": 2, "c": 3}
        remote = {"a": 1, "b": 20, "c": 3}

        result = _merge_rtc_file("data.json", base, local, remote, output_json=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["a"], 10)
        self.assertEqual(result["b"], 20)
        self.assertEqual(result["c"], 3)

    def test_merge_local_only_changes(self):
        """Verify merge returns local when only local changed."""
        base = {"a": 1, "b": 2}
        local = {"a": 10, "b": 2}
        remote = {"a": 1, "b": 2}

        result = _merge_rtc_file("data.json", base, local, remote)
        self.assertEqual(result, local)

    def test_merge_remote_only_changes(self):
        """Verify merge returns remote when only remote changed."""
        base = {"a": 1, "b": 2}
        local = {"a": 1, "b": 2}
        remote = {"a": 1, "b": 20}

        result = _merge_rtc_file("data.json", base, local, remote)
        self.assertEqual(result, remote)

    def test_merge_identical_changes(self):
        """Verify merge succeeds when both sides made the same change."""
        base = {"a": 1, "b": 2}
        local = {"a": 10, "b": 2}
        remote = {"a": 10, "b": 2}

        result = _merge_rtc_file("data.json", base, local, remote)
        self.assertEqual(result["a"], 10)

    def test_merge_nested_non_overlapping(self):
        """Verify nested dict changes on different keys merge cleanly."""
        base = {"config": {"a": 1, "b": 2}}
        local = {"config": {"a": 10, "b": 2}}
        remote = {"config": {"a": 1, "b": 20}}

        result = _merge_rtc_file("data.json", base, local, remote, output_json=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["config"]["a"], 10)
        self.assertEqual(result["config"]["b"], 20)

    def test_merge_nested_conflict_returns_none_in_json_mode(self):
        """Verify nested dict conflict on same key returns None in JSON mode."""
        base = {"config": {"a": 1}}
        local = {"config": {"a": 10}}
        remote = {"config": {"a": 20}}

        result = _merge_rtc_file("data.json", base, local, remote, output_json=True)
        self.assertIsNone(result)

    def test_merge_conflict_returns_none_in_json_mode(self):
        """Verify conflicting changes return None in JSON mode."""
        base = {"a": 1}
        local = {"a": 10}
        remote = {"a": 20}

        result = _merge_rtc_file("data.json", base, local, remote, output_json=True)
        self.assertIsNone(result)

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_drift_clean_merge_succeeds(self, mock_get_rtc, mock_load_project):
        """Verify push with clean merge auto-resolves and pushes."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_project.get_rtc_base.return_value = ({"type": "object"}, {"a": 1, "b": 2})
        mock_project.rtc_push_to_api.return_value = {"success": True, "environment": "sandbox"}
        mock_load_project.return_value = mock_project

        with open(os.path.join(self.sandbox_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(self.sandbox_dir, "data.json"), "w") as f:
            json.dump({"a": 10, "b": 2}, f)

        mock_get_rtc.return_value = {
            "lastUpdated": "T2",
            "schema": {"type": "object"},
            "variables": {"a": 1, "b": 20},
        }

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])

        call_kwargs = mock_project.rtc_push_to_api.call_args[1]
        self.assertEqual(call_kwargs["variables"]["a"], 10)
        self.assertEqual(call_kwargs["variables"]["b"], 20)

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_drift_no_base_returns_error(self, mock_get_rtc, mock_load_project):
        """Verify push fails gracefully when no base copies exist."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_project.get_rtc_base.return_value = (None, None)
        mock_load_project.return_value = mock_project

        with open(os.path.join(self.sandbox_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(self.sandbox_dir, "data.json"), "w") as f:
            json.dump({"a": 10}, f)

        mock_get_rtc.return_value = {"lastUpdated": "T2", "schema": {}, "variables": {}}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertFalse(result["success"])
        self.assertIn("no base version", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_drift_no_merge_flag_hard_fails(self, mock_get_rtc, mock_load_project):
        """Verify --no-merge disables merge and hard-fails on drift."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_project.get_rtc_last_updated.return_value = "T1"
        mock_load_project.return_value = mock_project

        with open(os.path.join(self.sandbox_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(self.sandbox_dir, "data.json"), "w") as f:
            json.dump({"a": 10}, f)

        mock_get_rtc.return_value = {"lastUpdated": "T2"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", no_merge=True)
        self.assertFalse(result["success"])
        self.assertIn("Run 'poly rtc pull", result["error"])


class TestIncludeRTC(unittest.TestCase):
    """Test suite for --include-rtc on pull/push commands."""

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_pull")
    @patch("poly.cli_commands.sync.load_project")
    def test_pull_include_rtc_calls_rtc_pull(self, mock_load_project, mock_rtc_pull):
        """Verify pull --include-rtc calls rtc_pull after normal pull."""
        from poly.cli_commands.sync import PullCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.pull_project.return_value = ([], {})
        mock_load_project.return_value = mock_project

        PullCommand.pull("/tmp/test", include_rtc=True, output_json=True)

        mock_rtc_pull.assert_called_once_with("/tmp/test", env="all", output_json=True)

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_pull")
    @patch("poly.cli_commands.sync.load_project")
    def test_pull_without_include_rtc_does_not_call_rtc(self, mock_load_project, mock_rtc_pull):
        """Verify pull without --include-rtc does not call rtc_pull."""
        from poly.cli_commands.sync import PullCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.pull_project.return_value = ([], {})
        mock_load_project.return_value = mock_project

        PullCommand.pull("/tmp/test", include_rtc=False, output_json=True)

        mock_rtc_pull.assert_not_called()

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_push")
    @patch("poly.cli_commands.sync.load_project")
    def test_push_include_rtc_calls_rtc_push_sandbox_default(
        self, mock_load_project, mock_rtc_push
    ):
        """Verify push --include-rtc calls rtc_push with sandbox default."""
        from poly.cli_commands.sync import PushCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.push_project.return_value = (True, "ok", [])
        mock_load_project.return_value = mock_project

        PushCommand.push("/tmp/test", include_rtc=True, output_json=True)

        mock_rtc_push.assert_called_once_with(
            "/tmp/test", env="sandbox", force=False, output_json=True
        )

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_push")
    @patch("poly.cli_commands.sync.load_project")
    def test_push_include_rtc_with_custom_env(self, mock_load_project, mock_rtc_push):
        """Verify push --include-rtc --rtc-env live passes the correct env."""
        from poly.cli_commands.sync import PushCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.push_project.return_value = (True, "ok", [])
        mock_load_project.return_value = mock_project

        PushCommand.push(
            "/tmp/test", include_rtc=True, rtc_env="live", force=True, output_json=True
        )

        mock_rtc_push.assert_called_once_with("/tmp/test", env="live", force=True, output_json=True)

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_push")
    @patch("poly.cli_commands.sync.load_project")
    def test_push_without_include_rtc_does_not_call_rtc(self, mock_load_project, mock_rtc_push):
        """Verify push without --include-rtc does not call rtc_push."""
        from poly.cli_commands.sync import PushCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.push_project.return_value = (True, "ok", [])
        mock_load_project.return_value = mock_project

        PushCommand.push("/tmp/test", include_rtc=False, output_json=True)

        mock_rtc_push.assert_not_called()

    @patch("poly.cli_commands.rtc.RTCCommand.rtc_push")
    @patch("poly.cli_commands.sync.load_project")
    def test_push_include_rtc_skipped_on_failed_push(self, mock_load_project, mock_rtc_push):
        """Verify rtc_push is not called when the main push fails."""
        from poly.cli_commands.sync import PushCommand

        mock_project = MagicMock()
        mock_project.branch_id = "branch-1"
        mock_project.account_id = "acc"
        mock_project.project_id = "proj"
        mock_project.push_project.return_value = (False, "error", [])
        mock_load_project.return_value = mock_project

        with self.assertRaises(SystemExit):
            PushCommand.push("/tmp/test", include_rtc=True, output_json=True)

        mock_rtc_push.assert_not_called()


class TestRTCEdit(unittest.TestCase):
    """Test suite for poly rtc edit command."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.sandbox_dir = os.path.join(
            self.temp_dir, "real_time_configuration", "draft_and_sandbox"
        )
        os.makedirs(self.sandbox_dir)

    def tearDown(self):
        """Clean up temporary files."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_happy_path(self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor):
        """Verify edit pulls, opens editor, and pushes data."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project

        config = {
            "schema": {"type": "object"},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_get_rtc.return_value = config
        mock_editor.return_value = '{\n  "flag": true\n}\n'
        mock_patch_vars.return_value = {"lastUpdated": "T2"}

        RTCCommand.rtc_edit(self.temp_dir, env="sandbox")

        mock_patch_vars.assert_called_once()
        pushed = mock_patch_vars.call_args[1]["variables"]
        self.assertEqual(pushed["flag"], True)

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    def test_edit_schema_flag(self, mock_put_schema, mock_get_rtc, mock_load_project, mock_editor):
        """Verify --schema edits and pushes schema instead of data."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project

        config = {
            "schema": {"type": "object"},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_get_rtc.return_value = config
        mock_editor.return_value = '{\n  "type": "object",\n  "title": "Config"\n}\n'
        mock_put_schema.return_value = {"lastUpdated": "T2"}

        RTCCommand.rtc_edit(self.temp_dir, env="sandbox", edit_schema=True)

        mock_put_schema.assert_called_once()
        pushed = mock_put_schema.call_args[1]["schema"]
        self.assertEqual(pushed["title"], "Config")

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_no_changes(self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor):
        """Verify no push when editor reports no changes."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {
            "schema": {},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_editor.side_effect = ValueError("No changes")

        RTCCommand.rtc_edit(self.temp_dir, env="sandbox")

        mock_patch_vars.assert_not_called()

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_invalid_json(self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor):
        """Verify no push when editor returns invalid JSON."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {
            "schema": {},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_editor.return_value = "not valid json {{"

        with self.assertRaises(SystemExit):
            RTCCommand.rtc_edit(self.temp_dir, env="sandbox")

        mock_patch_vars.assert_not_called()

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_race_detected(
        self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor
    ):
        """Verify push aborted when remote changed during editing."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        mock_get_rtc.side_effect = [
            {"schema": {}, "variables": {"flag": False}, "lastUpdated": "T1"},
            {"schema": {}, "variables": {"flag": False}, "lastUpdated": "T2"},
        ]
        mock_editor.return_value = '{"flag": true}'

        with self.assertRaises(SystemExit):
            RTCCommand.rtc_edit(self.temp_dir, env="sandbox")

        mock_patch_vars.assert_not_called()

    @patch("poly.cli_commands.rtc.questionary")
    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_live_declined(
        self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor, mock_questionary
    ):
        """Verify live edit cancelled when user declines confirmation."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project
        mock_questionary.confirm.return_value.ask.return_value = False

        mock_get_rtc.return_value = {
            "schema": {},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_editor.return_value = '{"flag": true}'

        RTCCommand.rtc_edit(self.temp_dir, env="live")

        mock_patch_vars.assert_not_called()

    @patch("poly.cli_commands.rtc.edit_in_editor")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_edit_updates_local_files(
        self, mock_patch_vars, mock_get_rtc, mock_load_project, mock_editor
    ):
        """Verify edit updates local data.json and calls set_rtc_base."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project._rtc_env_dir.return_value = self.sandbox_dir
        mock_load_project.return_value = mock_project

        with open(os.path.join(self.sandbox_dir, "data.json"), "w") as f:
            json.dump({"flag": False}, f)

        mock_get_rtc.return_value = {
            "schema": {},
            "variables": {"flag": False},
            "lastUpdated": "T1",
        }
        mock_editor.return_value = '{\n  "flag": true\n}\n'
        mock_patch_vars.return_value = {"lastUpdated": "T2"}

        RTCCommand.rtc_edit(self.temp_dir, env="sandbox")

        with open(os.path.join(self.sandbox_dir, "data.json"), "r") as f:
            local = json.load(f)
        self.assertTrue(local["flag"])

        mock_project.set_rtc_base.assert_called_once()
        call_kwargs = mock_project.set_rtc_base.call_args[1]
        self.assertTrue(call_kwargs["variables"]["flag"])


if __name__ == "__main__":
    unittest.main()
