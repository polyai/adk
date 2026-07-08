"""Tests for RTC (Real-Time Configuration) functionality.

Copyright PolyAI Limited
"""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from poly.cli_commands.rtc import RTCCommand, RTC_ENV_TO_DIR, RTC_DIR_TO_ENV


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
        mock_load_project.return_value = mock_project

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
    def test_rtc_push_missing_schema_raises(self, mock_load_project):
        """Verify rtc push raises if schema.json is missing."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        # Create only data.json
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
        with open(os.path.join(sandbox_dir, "data.json"), "w") as f:
            json.dump({}, f)

        with self.assertRaises(SystemExit):
            RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_missing_data_raises(self, mock_load_project):
        """Verify rtc push raises if data.json is missing."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        # Create only schema.json
        sandbox_dir = os.path.join(self.temp_dir, "real_time_configuration", "draft_and_sandbox")
        os.makedirs(sandbox_dir)
        with open(os.path.join(sandbox_dir, "schema.json"), "w") as f:
            json.dump({}, f)

        with self.assertRaises(SystemExit):
            RTCCommand.rtc_push(self.temp_dir, env="sandbox", output_json=True)

    @patch("poly.cli_commands.rtc.load_project")
    def test_rtc_push_live_without_force_json_exits(self, mock_load_project):
        """Verify pushing to live in JSON mode without --force is refused."""
        mock_project = MagicMock()
        mock_project.root_path = self.temp_dir
        mock_load_project.return_value = mock_project

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({}, f)

        with self.assertRaises(SystemExit):
            RTCCommand.rtc_push(self.temp_dir, env="live", force=False, output_json=True)

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

        live_dir = os.path.join(self.temp_dir, "real_time_configuration", "live")
        os.makedirs(live_dir)
        with open(os.path.join(live_dir, "schema.json"), "w") as f:
            json.dump({"type": "object"}, f)
        with open(os.path.join(live_dir, "data.json"), "w") as f:
            json.dump({"key": "val"}, f)

        RTCCommand.rtc_push(self.temp_dir, env="live", force=True, output_json=True)

        mock_put_schema.assert_called_once()
        mock_patch_vars.assert_called_once()


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


if __name__ == "__main__":
    unittest.main()
