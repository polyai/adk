"""Tests for RTC (Real-Time Configuration) functionality.

Copyright PolyAI Limited
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from poly.cli_commands.rtc import (
    RTC_BASE_DATA_FILE,
    RTC_BASE_SCHEMA_FILE,
    RTC_DIR_TO_ENV,
    RTC_ENV_TO_DIR,
    RTCCommand,
    _load_rtc_base,
    _merge_rtc_file,
)
from poly.utils import write_json_file


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
        """Verify RTC_ENV_TO_DIR and RTC_DIR_TO_ENV are consistent."""
        for env, dir_name in RTC_ENV_TO_DIR.items():
            self.assertEqual(RTC_DIR_TO_ENV[dir_name], env)

    def test_env_mapping_coverage(self):
        """Verify all 3 standard environments are mapped."""
        self.assertEqual(len(RTC_ENV_TO_DIR), 3)
        self.assertIn("sandbox", RTC_ENV_TO_DIR)
        self.assertIn("pre-release", RTC_ENV_TO_DIR)
        self.assertIn("live", RTC_ENV_TO_DIR)

    def test_sandbox_maps_to_draft_and_sandbox(self):
        """Verify sandbox API env maps to draft_and_sandbox directory."""
        self.assertEqual(RTC_ENV_TO_DIR["sandbox"], "draft_and_sandbox")

    def test_pre_release_maps_to_pre_release(self):
        """Verify pre-release API env maps to pre_release directory."""
        self.assertEqual(RTC_ENV_TO_DIR["pre-release"], "pre_release")

    def test_live_maps_to_live(self):
        """Verify live API env maps to live directory."""
        self.assertEqual(RTC_ENV_TO_DIR["live"], "live")

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_rtc_pull_all_envs(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull writes all 3 environments."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        # Mock API responses
        rtc_response = {
            "clientEnv": "sandbox",
            "schema": {"type": "object", "properties": {}},
            "variables": {"mock_api": False},
            "lastUpdated": "2024-01-01T00:00:00Z",
        }
        mock_get_rtc.return_value = rtc_response

        RTCCommand.rtc_pull(self.temp_dir, env="all", output_json=True)

        # Verify API was called for each environment
        self.assertEqual(mock_get_rtc.call_count, 3)
        call_args_list = [call[1] for call in mock_get_rtc.call_args_list]
        envs_called = [call["client_env"] for call in call_args_list]
        self.assertIn("sandbox", envs_called)
        self.assertIn("pre-release", envs_called)
        self.assertIn("live", envs_called)

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_rtc_pull_single_env(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull --env sandbox only calls API once."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        rtc_response = {
            "clientEnv": "sandbox",
            "schema": {"type": "object"},
            "variables": {"mock_api": False},
        }
        mock_get_rtc.return_value = rtc_response

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)

        # Verify API was called once
        mock_get_rtc.assert_called_once()
        self.assertEqual(mock_get_rtc.call_args[1]["client_env"], "sandbox")

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_rtc_pull_creates_directories(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull creates necessary directories."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        rtc_response = {
            "clientEnv": "sandbox",
            "schema": {"type": "object"},
            "variables": {"key": "value"},
        }
        mock_get_rtc.return_value = rtc_response

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)

        # Verify directories were created
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        self.assertTrue(os.path.isdir(sandbox_dir))

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_rtc_pull_writes_json_files(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull writes valid JSON files."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        schema_obj = {"type": "object", "properties": {"flag": {"type": "boolean"}}}
        variables_obj = {"flag": True, "nested": {"key": "value"}}

        rtc_response = {
            "clientEnv": "sandbox",
            "schema": schema_obj,
            "variables": variables_obj,
        }
        mock_get_rtc.return_value = rtc_response

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox", output_json=True)

        # Verify files exist and contain correct content
        schema_path = os.path.join(
            self.temp_dir, "real_time_configuration", "draft_and_sandbox", "schema.json"
        )
        data_path = os.path.join(
            self.temp_dir, "real_time_configuration", "draft_and_sandbox", "data.json"
        )

        self.assertTrue(os.path.exists(schema_path))
        self.assertTrue(os.path.exists(data_path))

        with open(schema_path, "r") as f:
            loaded_schema = json.load(f)
        self.assertEqual(loaded_schema, schema_obj)

        with open(data_path, "r") as f:
            loaded_variables = json.load(f)
        self.assertEqual(loaded_variables, variables_obj)

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_rtc_push_schema_and_variables(
        self, mock_patch_vars, mock_put_schema, mock_load_project
    ):
        """Verify rtc push calls both schema and variables APIs."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T1"}

        # Create test files
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)

        schema_obj = {"type": "object"}
        variables_obj = {"mock_api": False}

        with open(os.path.join(sandbox_dir, "schema.json"), "w") as f:
            json.dump(schema_obj, f)

        with open(os.path.join(sandbox_dir, "data.json"), "w") as f:
            json.dump(variables_obj, f)

        RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)

        # Verify both APIs were called
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

        # Verify arguments
        schema_call = mock_put_schema.call_args[1]
        self.assertEqual(schema_call["client_env"], "sandbox")
        self.assertEqual(schema_call["schema"], schema_obj)

        vars_call = mock_patch_vars.call_args[1]
        self.assertEqual(vars_call["client_env"], "sandbox")
        self.assertEqual(vars_call["variables"], variables_obj)

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_missing_schema_returns_error(self, mock_load_project):
        """Verify rtc push returns error if schema.json is missing."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
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
        mock_load_project.return_value = mock_project

        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
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
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({}, f)

        result = RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=True)
        self.assertFalse(result["success"])
        self.assertIn("--force", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_rtc_push_live_with_force_succeeds(
        self, mock_patch_vars, mock_put_schema, mock_load_project
    ):
        """Verify pushing to live with --force bypasses the safety gate."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T1"}

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)

        RTCCommand.rtc_push(self.temp_dir, env="live", force=True, output_json=True)

        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

    @patch("poly.cli_commands.rtc.questionary")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_rtc_push_live_interactive_confirm(
        self, mock_patch_vars, mock_put_schema, mock_load_project, mock_questionary
    ):
        """Verify interactive live push proceeds when user confirms."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T1"}
        mock_questionary.confirm.return_value.ask.return_value = True

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)

        RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=False)

        mock_questionary.confirm.assert_called_once()
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

    @patch("poly.cli_commands.rtc.questionary")
    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_rtc_push_live_interactive_decline(
        self, mock_patch_vars, mock_put_schema, mock_load_project, mock_questionary
    ):
        """Verify interactive live push is cancelled when user declines."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project
        mock_questionary.confirm.return_value.ask.return_value = False

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)

        RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=False)

        mock_questionary.confirm.assert_called_once()
        mock_put_schema.assert_not_called()
        mock_patch_vars.assert_not_called()


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
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_pull_stores_metadata_in_project(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull stores lastUpdated in project.rtc_metadata."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {
            "schema": {"type": "object"},
            "variables": {"key": "value"},
            "lastUpdated": "2024-06-01T12:00:00Z",
        }

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox")

        self.assertEqual(
            mock_project.rtc_metadata["sandbox"]["last_updated"], "2024-06-01T12:00:00Z"
        )
        mock_project.save_config.assert_called()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_detects_drift(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify push refuses when remote lastUpdated differs from local."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {"lastUpdated": "T2"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertFalse(result["success"])
        self.assertIn("changed since your last pull", result["error"])
        mock_put_schema.assert_not_called()
        mock_patch_vars.assert_not_called()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_allows_when_no_drift(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify push proceeds when remote lastUpdated matches local."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T1"}

        mock_get_rtc.return_value = {"lastUpdated": "T1"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_force_bypasses_drift_check(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify --force skips drift check entirely."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T3"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", force=True)
        self.assertTrue(result["success"])
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()
        mock_get_rtc.assert_not_called()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_no_metadata_warns_and_proceeds(
        self, mock_patch_vars, mock_put_schema, mock_load_project
    ):
        """Verify push proceeds with warning when no metadata exists."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T1"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_updates_metadata_after_success(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify push updates rtc_metadata with new lastUpdated."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project

        mock_get_rtc.return_value = {"lastUpdated": "T1"}
        mock_patch_vars.return_value = {"lastUpdated": "T2"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])

        self.assertEqual(mock_project.rtc_metadata["sandbox"]["last_updated"], "T2")
        mock_project.save_config.assert_called()


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
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_pull_writes_base_files(self, mock_get_rtc, mock_load_project):
        """Verify rtc pull writes .rtc_base_schema.json and .rtc_base_data.json."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        schema = {"type": "object", "properties": {"flag": {"type": "boolean"}}}
        variables = {"flag": True}
        mock_get_rtc.return_value = {
            "schema": schema,
            "variables": variables,
            "lastUpdated": "T1",
        }

        RTCCommand.rtc_pull(self.temp_dir, env="sandbox")

        base_schema, base_variables = _load_rtc_base(self.sandbox_dir)
        self.assertEqual(base_schema, schema)
        self.assertEqual(base_variables, variables)

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
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_drift_clean_merge_succeeds(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify push with clean merge auto-resolves and pushes."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T3"}

        base_schema = {"type": "object"}
        base_variables = {"a": 1, "b": 2}

        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_SCHEMA_FILE), base_schema)
        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_DATA_FILE), base_variables)

        write_json_file(os.path.join(self.sandbox_dir, "schema.json"), base_schema)
        write_json_file(os.path.join(self.sandbox_dir, "data.json"), {"a": 10, "b": 2})

        mock_get_rtc.return_value = {
            "lastUpdated": "T2",
            "schema": base_schema,
            "variables": {"a": 1, "b": 20},
        }

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])
        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()

        pushed_vars = mock_patch_vars.call_args[1]["variables"]
        self.assertEqual(pushed_vars["a"], 10)
        self.assertEqual(pushed_vars["b"], 20)

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    def test_push_drift_no_base_files_returns_error(self, mock_get_rtc, mock_load_project):
        """Verify push fails gracefully when base files don't exist."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project

        write_json_file(os.path.join(self.sandbox_dir, "schema.json"), {"type": "object"})
        write_json_file(os.path.join(self.sandbox_dir, "data.json"), {"a": 10})

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
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project

        write_json_file(os.path.join(self.sandbox_dir, "schema.json"), {"type": "object"})
        write_json_file(os.path.join(self.sandbox_dir, "data.json"), {"a": 10})

        mock_get_rtc.return_value = {"lastUpdated": "T2"}

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox", no_merge=True)
        self.assertFalse(result["success"])
        self.assertIn("Run 'poly rtc pull", result["error"])

    @patch("poly.cli_commands.rtc.load_project")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.get_rtc_config")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.put_rtc_schema")
    @patch("poly.cli_commands.rtc.AgentStudioInterface.patch_rtc_variables")
    def test_push_updates_base_and_local_files_after_merge(
        self, mock_patch_vars, mock_put_schema, mock_get_rtc, mock_load_project
    ):
        """Verify base and local files are updated after a successful merge+push."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = {"sandbox": {"last_updated": "T1"}}
        mock_load_project.return_value = mock_project
        mock_patch_vars.return_value = {"lastUpdated": "T3"}

        base_vars = {"a": 1, "b": 2}
        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_SCHEMA_FILE), {"type": "object"})
        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_DATA_FILE), base_vars)
        write_json_file(os.path.join(self.sandbox_dir, "schema.json"), {"type": "object"})
        write_json_file(os.path.join(self.sandbox_dir, "data.json"), {"a": 10, "b": 2})

        mock_get_rtc.return_value = {
            "lastUpdated": "T2",
            "schema": {"type": "object"},
            "variables": {"a": 1, "b": 20},
        }

        result = RTCCommand.rtc_push(self.temp_dir, env="sandbox")
        self.assertTrue(result["success"])

        # Base files should reflect merged content
        base_schema, base_variables = _load_rtc_base(self.sandbox_dir)
        self.assertEqual(base_variables["a"], 10)
        self.assertEqual(base_variables["b"], 20)

        # Local files should also reflect merged content
        with open(os.path.join(self.sandbox_dir, "data.json"), "r") as f:
            local_vars = json.load(f)
        self.assertEqual(local_vars["a"], 10)
        self.assertEqual(local_vars["b"], 20)


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
        """Verify edit updates local data.json and base file when env dir exists."""
        mock_project = MagicMock()
        mock_project.region = "studio"
        mock_project.project_id = "test-project"
        mock_project.root_path = self.temp_dir
        mock_project.rtc_metadata = None
        mock_load_project.return_value = mock_project

        write_json_file(os.path.join(self.sandbox_dir, "data.json"), {"flag": False})
        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_DATA_FILE), {"flag": False})
        write_json_file(os.path.join(self.sandbox_dir, RTC_BASE_SCHEMA_FILE), {})

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

        _, base_vars = _load_rtc_base(self.sandbox_dir)
        self.assertTrue(base_vars["flag"])


if __name__ == "__main__":
    unittest.main()
