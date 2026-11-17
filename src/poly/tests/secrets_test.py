"""Account secrets through the real CLI, project, interface and HTTP layers.

Copyright PolyAI Limited
"""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from poly.cli import AgentStudioCLI
from poly.project import AgentStudioProject
from poly.tests.project_test import PROJECT_DATA
from poly.tests.testing_utils import make_mock_response

SENTINEL = "PRIVATE_VALUE_MUST_NOT_APPEAR"


class TTYInput(io.StringIO):
    def isatty(self):
        return True


class SecretsCommandTest(unittest.TestCase):
    """Model only the remote HTTP boundary; exercise the command's real layers."""

    def setUp(self):
        self.workspace = tempfile.TemporaryDirectory()
        self.addCleanup(self.workspace.cleanup)
        self.project = AgentStudioProject.from_dict(PROJECT_DATA, self.workspace.name)
        self.project.save_config(write_project_yaml=True)
        self.state = {
            "credentials": {
                "display_name": "credentials",
                "description": None,
                "value_type": "key-value",
                "secret_value": {"username": "old", "password": SENTINEL},
                "access_config": [self.project.project_id, "project-b"],
                "created_at": "2026-01-01T00:00:00Z",
                "last_updated": "2026-01-02T00:00:00Z",
            },
            "single": {
                "display_name": "single",
                "description": "Single value",
                "value_type": "single",
                "secret_value": SENTINEL,
                "access_config": [],
            },
        }
        self.calls = []
        request_patch = patch("requests.request", side_effect=self.request)
        self.http = request_patch.start()
        self.addCleanup(request_patch.stop)
        key_patch = patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-key")
        key_patch.start()
        self.addCleanup(key_patch.stop)
        update_patch = patch("poly.cli.display_update_message")
        update_patch.start()
        self.addCleanup(update_patch.stop)

    def request(self, **kwargs):
        self.assertEqual(
            kwargs["url"],
            f"https://api.us.poly.ai/adk/v1/accounts/{self.project.account_id}/secrets",
        )
        self.assertEqual(kwargs["headers"]["X-API-KEY"], "test-key")
        self.assertIsNone(kwargs["params"])
        method = kwargs["method"]
        body = json.loads(kwargs["data"]) if kwargs["data"] else None
        self.calls.append((method, deepcopy(body)))
        if method == "GET":
            # Deliberately echo values and an unknown field to test the client boundary.
            records = [dict(record, server_debug=SENTINEL) for record in self.state.values()]
            return make_mock_response(json_body=deepcopy(records))
        if method == "DELETE":
            for name in body["display_name"]:
                self.state.pop(name, None)
            return make_mock_response(status_code=204)
        name = body["display_name"]
        if method == "POST":
            self.assertNotIn(name, self.state)
            self.state[name] = deepcopy(body)
        else:
            self.assertEqual(method, "PUT")
            self.state[name].update(deepcopy(body))
        return make_mock_response(json_body=dict(self.state[name], server_debug=SENTINEL))

    def run_cli(self, *args, stdin="", tty=False):
        stdout, stderr = io.StringIO(), io.StringIO()
        input_file = TTYInput(stdin) if tty else io.StringIO(stdin)
        code = 0
        with patch("sys.stdin", input_file), redirect_stdout(stdout), redirect_stderr(stderr):
            try:
                AgentStudioCLI().main(["secrets", *args, "--path", self.workspace.name])
            except SystemExit as error:
                code = error.code
        return code, stdout.getvalue(), stderr.getvalue()

    def test_list_returns_metadata_and_filters_current_project(self):
        code, output, _ = self.run_cli("list", "--project", "--json")
        self.assertEqual(code, 0, output)
        records = json.loads(output)["secrets"]
        self.assertEqual([record["display_name"] for record in records], ["credentials"])
        self.assertNotIn(SENTINEL, output)
        self.assertNotIn("secret_value", output)

    def test_human_list_and_debug_logs_never_show_values(self):
        with self.assertLogs("poly.handlers.platform_api", level="DEBUG") as logs:
            code, output, errors = self.run_cli("list")
        self.assertEqual(code, 0, errors)
        self.assertIn("credentials", output)
        self.assertNotIn(SENTINEL, output + errors + "\n".join(logs.output))
        for path in Path(self.workspace.name).rglob("*"):
            if path.is_file():
                self.assertNotIn(SENTINEL.encode(), path.read_bytes())

    def test_create_defaults_to_current_project_and_never_echoes_a_value(self):
        with self.assertLogs("poly.handlers.platform_api", level="DEBUG") as logs:
            code, output, errors = self.run_cli("set", "new-token", "--json", stdin=SENTINEL)
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(self.state["new-token"]["secret_value"], SENTINEL)
        self.assertEqual(self.state["new-token"]["access_config"], [self.project.project_id])
        self.assertEqual(json.loads(output)["secret"]["display_name"], "new-token")
        self.assertNotIn(SENTINEL, output + errors + "\n".join(logs.output))

    def test_metadata_edit_preserves_value_type_and_inaccessible_project_access(self):
        original = deepcopy(self.state["credentials"])
        code, output, _ = self.run_cli(
            "set", "credentials", "--description", "Updated", "--json", tty=True
        )
        self.assertEqual(code, 0, output)
        saved = self.state["credentials"]
        self.assertEqual(saved["secret_value"], original["secret_value"])
        self.assertEqual(saved["access_config"], original["access_config"])
        self.assertEqual(saved["value_type"], "key-value")
        self.assertEqual(saved["description"], "Updated")
        self.assertNotIn(
            "secret_value", [body for method, body in self.calls if method == "PUT"][0]
        )

    def test_grant_and_revoke_preserve_untouched_access_and_value(self):
        code, output, _ = self.run_cli(
            "set",
            "credentials",
            "--grant",
            "project-c",
            "--revoke",
            self.project.project_id,
            "--json",
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["credentials"]["access_config"], ["project-b", "project-c"])
        self.assertEqual(self.state["credentials"]["secret_value"]["password"], SENTINEL)

    def test_replacement_projects_and_no_projects_are_explicit(self):
        code, output, _ = self.run_cli(
            "set", "credentials", "--project", "one", "--project", "two", "--json"
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["credentials"]["access_config"], ["one", "two"])
        code, output, _ = self.run_cli("set", "new", "--no-projects", "--json", stdin="token")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["new"]["access_config"], [])

    def test_key_value_input_is_a_complete_replacement(self):
        code, output, _ = self.run_cli(
            "set", "credentials", "--json", stdin='{"password":"replacement"}'
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["credentials"]["secret_value"], {"password": "replacement"})

    def test_json_value_input_refuses_a_terminal_without_prompting(self):
        with patch("getpass.getpass") as prompt:
            code, output, _ = self.run_cli("set", "new", "--json", tty=True)
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["success"])
        prompt.assert_not_called()
        self.assertNotIn("new", self.state)

    def test_single_value_prompt_is_hidden(self):
        with patch("getpass.getpass", return_value=SENTINEL) as prompt:
            code, output, errors = self.run_cli("set", "new", tty=True)
        self.assertEqual(code, 0, output + errors)
        prompt.assert_called_once()
        self.assertEqual(self.state["new"]["secret_value"], SENTINEL)
        self.assertNotIn(SENTINEL, output + errors)

    def test_key_value_prompt_hides_every_value(self):
        prompts = [Mock(), Mock(), Mock()]
        for prompt, key in zip(prompts, ["username", "password", ""]):
            prompt.ask.return_value = key
        with (
            patch("questionary.text", side_effect=prompts),
            patch("getpass.getpass", side_effect=["user", SENTINEL]) as hidden,
        ):
            code, output, errors = self.run_cli("set", "new", "--key-value", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(hidden.call_count, 2)
        self.assertEqual(
            self.state["new"]["secret_value"], {"username": "user", "password": SENTINEL}
        )
        self.assertNotIn(SENTINEL, output + errors)

    def test_metadata_and_value_can_be_changed_together(self):
        with patch("getpass.getpass", return_value="replacement"):
            code, output, errors = self.run_cli(
                "set", "single", "--description", "Updated", "--replace-value", tty=True
            )
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(self.state["single"]["secret_value"], "replacement")
        self.assertEqual(self.state["single"]["description"], "Updated")

    def test_invalid_input_never_writes_or_exposes_the_supplied_value(self):
        for value in ('{"password":"' + SENTINEL, '{"password": null}', "{}", "null"):
            with self.subTest(value_type=type(value)):
                self.calls.clear()
                code, output, errors = self.run_cli(
                    "set", "new", "--key-value", "--json", stdin=value
                )
                self.assertEqual(code, 1)
                self.assertNotIn(SENTINEL, output + errors)
                self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_http_errors_and_network_exceptions_never_echo_values(self):
        self.http.return_value = make_mock_response(
            400, {"message": SENTINEL}, content=SENTINEL.encode()
        )
        self.http.side_effect = None
        with self.assertLogs("poly.handlers.platform_api", level="DEBUG") as logs:
            code, output, errors = self.run_cli("set", "new", "--json", stdin=SENTINEL)
        self.assertEqual(code, 1)
        self.assertNotIn(SENTINEL, output + errors + "\n".join(logs.output))
        self.http.side_effect = requests.Timeout(SENTINEL)
        code, output, errors = self.run_cli("list", "--json")
        self.assertEqual(code, 1)
        self.assertNotIn(SENTINEL, output + errors)

    def test_bulk_delete_json_skips_confirmation_and_deduplicates(self):
        with patch("questionary.confirm") as confirm:
            code, output, _ = self.run_cli("delete", "single", "credentials", "single", "--json")
        self.assertEqual(code, 0, output)
        confirm.assert_not_called()
        self.assertEqual(json.loads(output)["deleted"], ["single", "credentials"])
        self.assertEqual(self.state, {})

    def test_cancelled_delete_does_not_write(self):
        with patch("questionary.confirm") as confirm:
            confirm.return_value.ask.return_value = False
            code, output, errors = self.run_cli("delete", "single", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertIn("single", self.state)
        self.assertFalse(self.calls)

    def test_programmatic_validation_prevents_invalid_access_and_values(self):
        for kwargs in (
            {"projects": ["a"], "grant": ["b"]},
            {"grant": ["a"], "revoke": ["a"]},
            {"value": {"token": None}},
            {"projects": [""]},
            {"projects": "project-a"},
        ):
            with self.subTest(options=list(kwargs)):
                with self.assertRaises(ValueError):
                    self.project.set_secret("credentials", **kwargs)
        self.assertFalse(any(method != "GET" for method, _ in self.calls))


if __name__ == "__main__":
    unittest.main()
