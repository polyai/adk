"""Account secrets through the real CLI, project, interface and HTTP layers.

Copyright PolyAI Limited
"""

import io
import json
import tempfile
import unittest
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
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
        if (
            kwargs["url"]
            == f"https://api.us.poly.ai/adk/v1/accounts/{self.project.account_id}/projects"
        ):
            self.assertEqual(kwargs["method"], "GET")
            self.assertEqual(kwargs["headers"]["X-API-KEY"], "test-key")
            return make_mock_response(
                json_body={
                    "projects": [
                        {
                            "id": project_id,
                            "name": "Bravo" if project_id == "project-b" else project_id,
                        }
                        for project_id in (
                            self.project.project_id,
                            "project-b",
                            "project-c",
                            "one",
                            "two",
                        )
                    ]
                }
            )
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
            for record in records:
                if record["value_type"] == "key-value":
                    record["keys"] = list(record["secret_value"])
            return make_mock_response(json_body=deepcopy(records))
        if method == "DELETE":
            for name in body["display_name"]:
                self.state.pop(name, None)
            return make_mock_response(status_code=204)
        name = body["display_name"]
        if method == "POST":
            self.assertNotIn(name, self.state)
            self.state[name] = deepcopy(body)
        elif method == "PATCH":
            self.assertNotIn("value_type", body)
            values = deepcopy(self.state[name]["secret_value"])
            for key, value in body["secret_value"].items():
                if value is None:
                    values.pop(key, None)
                else:
                    values[key] = value
            if not values:
                return make_mock_response(400, {"message": "Empty key-value map"})
            self.state[name].update({k: v for k, v in body.items() if k != "secret_value"})
            self.state[name]["secret_value"] = values
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

    @contextmanager
    def prompts(self, *steps):
        """Script terminal answers and reject unexpected, repeated, or skipped prompts."""
        pending = iter(steps)
        calls = []

        def answer(kind, message, **kwargs):
            expected, result = next(pending)
            self.assertEqual(expected, (kind, message))
            calls.append((kind, message, kwargs))
            if callable(result):
                result = result(kwargs)
            if result is not None and "validate" in kwargs:
                self.assertIs(kwargs["validate"](result), True)
            return Mock(ask=Mock(return_value=result))

        with ExitStack() as stack:
            for kind in ("select", "checkbox", "text", "password", "confirm"):
                stack.enter_context(
                    patch(
                        f"questionary.{kind}",
                        side_effect=lambda *a, kind=kind, **kw: answer(kind, *a, **kw),
                    )
                )
            yield calls
        self.assertIsNone(next(pending, None))

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
        self.assertIn("Bravo", output)
        self.assertNotIn(SENTINEL, output + errors + "\n".join(logs.output))
        for path in Path(self.workspace.name).rglob("*"):
            if path.is_file():
                self.assertNotIn(SENTINEL.encode(), path.read_bytes())

    def test_project_names_permission_is_optional_for_listing_and_value_updates(self):
        def request(**kwargs):
            if kwargs["url"].endswith("/projects"):
                return make_mock_response(403)
            return self.request(**kwargs)

        self.http.side_effect = request
        with patch.dict("os.environ", COLUMNS="160"):
            code, output, errors = self.run_cli("list")
        self.assertEqual(code, 0, output + errors)
        self.assertIn("project-b", output)
        with self.prompts((("password", "Secret value"), SENTINEL)):
            code, output, errors = self.run_cli(
                "set", "single", "--replace-value", "--yes", tty=True
            )
        self.assertEqual(code, 0, output + errors)
        self.assertNotIn(SENTINEL, output + errors)

    def test_single_stdin_strips_one_line_ending(self):
        for raw, expected in (
            ("token", "token"),
            ("token\n", "token"),
            ("token\r\n", "token"),
            ("token\n\n", "token\n"),
            ("  first\nsecond  \n", "  first\nsecond  "),
        ):
            with self.subTest(raw=raw):
                code, output, errors = self.run_cli("set", "single", "--json", stdin=raw)
                self.assertEqual(code, 0, output + errors)
                self.assertEqual(self.state["single"]["secret_value"], expected)
        self.calls.clear()
        code, _, _ = self.run_cli("set", "single", "--json", stdin="\n")
        self.assertEqual(code, 1)
        self.assertEqual(self.calls, [("GET", None)])

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

    def test_metadata_only_get_and_put_responses_confirm_success(self):
        def metadata_response(**kwargs):
            payload = self.request(**kwargs).json()
            records = payload if isinstance(payload, list) else [payload]
            for record in records:
                record.pop("secret_value", None)
                record.pop("server_debug", None)
            return make_mock_response(json_body=payload)

        self.http.side_effect = metadata_response
        for replace_value in (False, True):
            with self.subTest(replace_value=replace_value):
                args = ["set", "single", "--description", "Updated", "--json"]
                if replace_value:
                    args.append("--replace-value")
                code, output, errors = self.run_cli(
                    *args, stdin="replacement" if replace_value else "", tty=not replace_value
                )

                self.assertEqual(code, 0, output + errors)
                result = json.loads(output)
                self.assertTrue(result["success"])
                self.assertEqual(result["secret"]["display_name"], "single")
                self.assertEqual(result["secret"]["description"], "Updated")
                self.assertNotIn("secret_value", result["secret"])
                self.assertEqual(
                    self.state["single"]["secret_value"],
                    "replacement" if replace_value else SENTINEL,
                )
                self.assertEqual(self.calls[-1][0], "PUT")
                self.assertEqual("secret_value" in self.calls[-1][1], replace_value)

    def test_failed_put_is_not_reported_as_saved(self):
        for status in (400, 500):
            with self.subTest(status=status):

                def reject_put(**kwargs):
                    if kwargs["method"] == "PUT":
                        return make_mock_response(status, {"error_message": "Update failed"})
                    return self.request(**kwargs)

                self.http.side_effect = reject_put
                code, output, errors = self.run_cli("set", "single", "--json", stdin="replacement")

                self.assertEqual(code, 1, output + errors)
                self.assertFalse(json.loads(output)["success"])
                self.assertIn(f"HTTP {status}", output)
                self.assertNotIn("permissions", output)
                self.assertEqual(self.state["single"]["secret_value"], SENTINEL)

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
        self.assertEqual([method for method, _ in self.calls], ["GET", "PUT"])
        self.assertEqual(self.state["credentials"]["access_config"], ["project-b", "project-c"])
        self.assertEqual(self.state["credentials"]["secret_value"]["password"], SENTINEL)

    def test_invalid_set_flags_fail_before_any_edit_prompt(self):
        cases = (
            ("new-name", ["--grant", "project-c"], "require an existing secret"),
            ("new-name", ["--revoke", "project-c"], "require an existing secret"),
            ("new-name", ["--delete-key", "token"], "requires an existing key-value secret"),
            ("new-name", ["--project", "missing"], "not found or not visible"),
            (
                "credentials",
                ["--grant", "project-c", "--revoke", "project-c"],
                "both granted and revoked",
            ),
            ("credentials", ["--type", "single", "--delete-key", "token"], "changing secret type"),
        )
        for name, flags, message in cases:
            with self.subTest(name=name, flags=flags), self.prompts():
                self.calls.clear()
                code, output, errors = self.run_cli("set", name, *flags, tty=True)
                self.assertEqual(code, 1)
                self.assertIn(message, output + errors)
                self.assertEqual(self.calls, [("GET", None)])

    def test_invalid_project_flag_is_rejected_before_reading_stdin(self):
        with patch("poly.cli_commands.secrets.SecretsCommand._read_stdin") as read_value:
            code, output, _ = self.run_cli(
                "set", "new-name", "--project", "missing", "--json", stdin=SENTINEL
            )
        self.assertEqual(code, 1, output)
        self.assertIn("not found or not visible", json.loads(output)["error"])
        read_value.assert_not_called()
        self.assertEqual(self.calls, [("GET", None)])

    def test_rejects_unknown_project_ids_before_writing(self):
        for flag in ("--project", "--grant", "--revoke"):
            with self.subTest(flag=flag):
                self.calls.clear()
                code, output, _ = self.run_cli(
                    "set", "credentials", flag, "PROJECT_NOT_EXIST", "--json"
                )
                self.assertEqual(code, 1, output)
                self.assertIn("Project IDs not found or not visible", json.loads(output)["error"])
                self.assertIn("PROJECT_NOT_EXIST", json.loads(output)["error"])
                self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_revokes_deleted_project_still_on_access_list(self):
        self.state["credentials"]["access_config"].append("deleted-project")
        code, output, _ = self.run_cli(
            "set", "credentials", "--revoke", "deleted-project", "--json"
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(
            self.state["credentials"]["access_config"], [self.project.project_id, "project-b"]
        )

    def test_replacement_projects_and_no_projects_are_explicit(self):
        code, output, _ = self.run_cli(
            "set", "credentials", "--project", "one", "--project", "two", "--json"
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["credentials"]["access_config"], ["one", "two"])
        code, output, _ = self.run_cli("set", "new", "--no-projects", "--json", stdin="token")
        self.assertEqual(code, 0, output)
        self.assertEqual(self.state["new"]["access_config"], [])

    def test_convert_single_to_key_value_interactively_replaces_value_and_preserves_metadata(self):
        self.state["single"]["access_config"] = ["project-b"]
        with self.prompts(
            (("text", "Key (leave empty to finish)"), "first"),
            (("password", "Value for first"), SENTINEL),
            (("text", "Key (leave empty to finish)"), "second"),
            (("password", "Value for second"), "null"),
            (("text", "Key (leave empty to finish)"), ""),
        ):
            code, output, errors = self.run_cli(
                "set", "single", "--type", "key-value", "--yes", tty=True
            )
        self.assertEqual(code, 0, output + errors)
        self.assertNotIn(SENTINEL, output + errors)
        self.assertEqual(
            [call for call in self.calls if call[0] != "GET"],
            [
                (
                    "PUT",
                    {
                        "display_name": "single",
                        "value_type": "key-value",
                        "secret_value": {"first": SENTINEL, "second": "null"},
                        "description": "Single value",
                        "access_config": ["project-b"],
                    },
                )
            ],
        )

    def test_convert_key_value_to_single_with_metadata_changes(self):
        code, output, errors = self.run_cli(
            "set",
            "credentials",
            "--type",
            "single",
            "--description",
            "New description",
            "--grant",
            "project-c",
            "--json",
            stdin=SENTINEL,
        )
        self.assertEqual(code, 0, output + errors)
        self.assertNotIn(SENTINEL, output + errors)
        self.assertEqual(
            self.calls[-1],
            (
                "PUT",
                {
                    "display_name": "credentials",
                    "value_type": "single",
                    "secret_value": SENTINEL,
                    "description": "New description",
                    "access_config": [self.project.project_id, "project-b", "project-c"],
                },
            ),
        )

    def test_type_change_rejects_missing_or_incomplete_values_without_writing(self):
        for name, target, raw in (
            ("single", "key-value", ""),
            ("credentials", "single", ""),
            ("single", "key-value", "{}"),
            ("single", "key-value", '{"keep":"value","remove":null}'),
        ):
            with self.subTest(name=name, raw=raw):
                code, output, _ = self.run_cli(
                    "set", name, "--type", target, "--description", "Changed", "--json", stdin=raw
                )
                self.assertEqual(code, 1, output)
        with self.assertRaisesRegex(ValueError, "complete replacement value"):
            self.project.set_secret("single", value_type="key-value", description="Changed")
        self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_type_change_rejects_key_deletion_before_prompting(self):
        with patch("questionary.password") as hidden, patch("questionary.text") as prompt:
            for name, target in (("single", "key-value"), ("credentials", "single")):
                with self.subTest(name=name):
                    code, output, errors = self.run_cli(
                        "set", name, "--type", target, "--delete-key", "obsolete", tty=True
                    )
                    self.assertEqual(code, 1)
                    self.assertIn("--delete-key", output + errors)
            hidden.assert_not_called()
            prompt.assert_not_called()
        self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_key_value_update_preserves_omitted_keys_and_sends_only_changes(self):
        code, output, _ = self.run_cli(
            "set",
            "credentials",
            "--type",
            "key-value",
            "--json",
            stdin='{"password":"replacement"}',
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(
            self.state["credentials"]["secret_value"],
            {"username": "old", "password": "replacement"},
        )
        self.assertEqual(
            [body for method, body in self.calls if method == "PATCH"],
            [{"display_name": "credentials", "secret_value": {"password": "replacement"}}],
        )
        self.assertNotIn(SENTINEL, output)

    def test_key_value_update_adds_and_deletes_keys_from_stdin(self):
        code, output, errors = self.run_cli(
            "set", "credentials", "--json", stdin='{"username":null,"new":"value"}'
        )
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(
            self.state["credentials"]["secret_value"], {"password": SENTINEL, "new": "value"}
        )
        self.assertNotIn(SENTINEL, output + errors)

    def test_delete_key_skips_value_prompt_and_preserves_other_keys(self):
        with patch("questionary.password") as prompt:
            code, output, errors = self.run_cli(
                "set",
                "credentials",
                "--delete-key",
                "username",
                "--delete-key",
                "missing",
                "--json",
                tty=True,
            )
        self.assertEqual(code, 0, output + errors)
        prompt.assert_not_called()
        self.assertEqual(self.state["credentials"]["secret_value"], {"password": SENTINEL})
        self.assertEqual(
            self.calls[-1],
            (
                "PATCH",
                {
                    "display_name": "credentials",
                    "secret_value": {"username": None, "missing": None},
                },
            ),
        )

    def test_key_updates_can_include_explicit_metadata_and_access_changes(self):
        original = deepcopy(self.state["credentials"]["secret_value"])
        metadata = self.project.set_secret(
            "credentials", {"new": "value"}, description="", no_projects=True
        )
        self.assertEqual(self.state["credentials"]["secret_value"], {**original, "new": "value"})
        self.assertEqual(metadata["description"], "")
        self.assertEqual(metadata["access_config"], [])
        self.assertEqual(
            self.calls[-1],
            (
                "PATCH",
                {
                    "display_name": "credentials",
                    "secret_value": {"new": "value"},
                    "description": "",
                    "access_config": [],
                },
            ),
        )
        self.assertNotIn("secret_value", metadata)

    def test_deleting_all_known_keys_fails_without_writing(self):
        code, output, _ = self.run_cli(
            "set", "credentials", "--json", stdin='{"username":null,"password":null}'
        )
        self.assertEqual(code, 1)
        self.assertIn("retain at least one key", output)
        self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_4xx_shows_structured_error_code_and_message(self):
        detail = {"error_code": "INVALID_ACCESS", "error_message": "Unknown project in access list"}
        for body in (
            {**detail, "debug": SENTINEL},
            {
                "error_code": "BAD_REQUEST",
                "error_message": json.dumps({**detail, "debug": SENTINEL}),
            },
        ):
            with self.subTest(body=body):
                self.http.side_effect = lambda **kw: (
                    self.request(**kw) if kw["method"] == "GET" else make_mock_response(400, body)
                )
                code, output, errors = self.run_cli("set", "single", "--json", stdin=SENTINEL)
                self.assertEqual(code, 1)
                self.assertIn("HTTP 400", output)
                self.assertIn("INVALID_ACCESS: Unknown project in access list", output)
                self.assertNotIn(SENTINEL, output + errors)

    def test_patch_errors_are_redacted_and_are_not_retried_as_put(self):
        def reject_patch(**kwargs):
            if kwargs["method"] == "PATCH":
                return make_mock_response(
                    400, {"error_code": "BAD_REQUEST", "error_message": f"Rejected {SENTINEL}"}
                )
            return self.request(**kwargs)

        self.http.side_effect = reject_patch
        with self.assertLogs("poly.handlers.platform_api", level="DEBUG") as logs:
            code, output, errors = self.run_cli(
                "set", "credentials", "--json", stdin=json.dumps({"password": SENTINEL})
            )
        self.assertEqual(code, 1)
        self.assertNotIn(SENTINEL, output + errors + "\n".join(logs.output))
        self.assertEqual(
            [
                call.kwargs["method"]
                for call in self.http.call_args_list
                if call.kwargs["method"] != "GET"
            ],
            ["PATCH"],
        )

    def test_json_value_input_refuses_a_terminal_without_prompting(self):
        with patch("questionary.password") as prompt:
            code, output, _ = self.run_cli("set", "new", "--json", tty=True)
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(output)["success"])
        prompt.assert_not_called()
        self.assertNotIn("new", self.state)

    def test_new_secret_picker_prompts_only_once_for_name_and_confirms(self):
        def choose_new(kwargs):
            choices = kwargs["choices"]
            self.assertEqual(
                [c.title for c in choices],
                ["New secret…", "credentials (key-value)", "single (single)"],
            )
            return choices[0].value

        def choose_projects(kwargs):
            choices = kwargs["choices"]
            self.assertEqual([c.value for c in choices if c.checked], [self.project.project_id])
            self.assertIn("Bravo (project-b)", [c.title for c in choices])
            return [self.project.project_id, "project-b"]

        with self.prompts(
            (("select", "Secret"), choose_new),
            (("text", "New secret name"), "new"),
            (("select", "Type"), "single"),
            (("text", "Description (optional)"), "Example"),
            (("checkbox", "Projects with access"), choose_projects),
            (("password", "Secret value"), SENTINEL),
            (("confirm", "Save to every environment, including live?"), True),
        ) as calls:
            code, output, errors = self.run_cli("set", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertFalse(calls[-1][2]["default"])
        self.assertEqual([method for method, _ in self.calls], ["GET", "POST"])
        self.assertEqual(self.state["new"]["secret_value"], SENTINEL)
        self.assertEqual(self.state["new"]["access_config"], [self.project.project_id, "project-b"])
        self.assertIn("Bravo", output)
        self.assertNotIn(SENTINEL, output + errors)

    def test_named_create_uses_supplied_fields_and_duplicate_key_can_be_corrected(self):
        def finish(kwargs):
            validate = kwargs["validate"]
            self.assertIsInstance(validate("first"), str)
            return ""

        with self.prompts(
            (("text", "Key (leave empty to finish)"), "first"),
            (("password", "Value for first"), SENTINEL),
            (("text", "Key (leave empty to finish)"), finish),
        ):
            code, output, errors = self.run_cli(
                "set",
                "new",
                "--type",
                "key-value",
                "--description",
                "Example",
                "--no-projects",
                "--yes",
                tty=True,
            )
        self.assertEqual(code, 0, errors + output)
        self.assertEqual(self.state["new"]["secret_value"], {"first": SENTINEL})
        self.assertNotIn(SENTINEL, output + errors)

    def test_edit_keys_from_picker_reviews_and_applies_one_patch(self):
        def edit_username(kwargs):
            self.assertIn("Update password", [choice.title for choice in kwargs["choices"]])
            return next(c.value for c in kwargs["choices"] if c.title == "Update username")

        with self.prompts(
            (("select", "Secret"), "credentials"),
            (("checkbox", "What do you want to change?"), ["value"]),
            (("select", "Keys"), edit_username),
            (("password", "Value for username"), "new-user"),
            (("select", "Keys"), "add"),
            (("text", "Key name"), "extra"),
            (("password", "Value for extra"), "null"),
            (("select", "Keys"), "delete"),
            (("checkbox", "Keys to delete"), ["password"]),
            (("select", "Keys"), "done"),
            (("confirm", "Save to every environment, including live?"), True),
        ):
            code, output, errors = self.run_cli("set", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(
            self.state["credentials"]["secret_value"], {"username": "new-user", "extra": "null"}
        )
        self.assertEqual([method for method, _ in self.calls], ["GET", "PATCH"])
        for line in ("Keys added: extra", "Keys updated: username", "Keys removed: password"):
            self.assertIn(line, output)
        for value in (SENTINEL, "new-user", "null"):
            self.assertNotIn(value, output + errors)

    def test_declining_conversion_does_not_write(self):
        def convert(kwargs):
            choice = kwargs["choices"][1]
            self.assertIn("replaces keys username, password", choice.title)
            return choice.value

        original = deepcopy(self.state)
        with self.prompts(
            (("checkbox", "What do you want to change?"), ["type", "access"]),
            (("select", "Type"), convert),
            (("checkbox", "Projects with access"), []),
            (("password", "Secret value"), SENTINEL),
            (("confirm", "Save to every environment, including live?"), False),
        ):
            code, output, errors = self.run_cli("set", "credentials", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertIn("key-value → single", output)
        self.assertIn("Keys removed: password, username", output)
        self.assertIn("→ None", output)
        self.assertNotIn(SENTINEL, output + errors)
        self.assertEqual(self.state, original)
        self.assertEqual(self.calls, [("GET", None)])

    def test_access_checkbox_retains_stale_grants_and_uses_ids(self):
        self.state["credentials"]["access_config"].append("deleted")
        with self.prompts(
            (("checkbox", "What do you want to change?"), ["access"]),
            (("checkbox", "Projects with access"), ["deleted", "project-c"]),
        ):
            code, output, errors = self.run_cli("set", "credentials", "--yes", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(self.state["credentials"]["access_config"], ["deleted", "project-c"])

    def test_metadata_and_value_can_be_changed_together(self):
        with self.prompts((("password", "Secret value"), "replacement")):
            code, output, errors = self.run_cli(
                "set", "single", "--description", "Updated", "--replace-value", "--yes", tty=True
            )
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(self.state["single"]["secret_value"], "replacement")
        self.assertEqual(self.state["single"]["description"], "Updated")

    def test_empty_edit_and_cancelled_password_do_not_save(self):
        with self.prompts((("checkbox", "What do you want to change?"), [])):
            code, output, errors = self.run_cli("set", "single", tty=True)
        self.assertEqual(code, 0, output + errors)
        with self.prompts(
            (("checkbox", "What do you want to change?"), ["value"]),
            (("password", "Secret value"), None),
        ):
            code, output, errors = self.run_cli("set", "single", tty=True)
        self.assertEqual(code, 1, output + errors)
        self.assertTrue(all(method == "GET" for method, _ in self.calls))

    def test_noninteractive_writes_require_names_and_confirmation(self):
        with self.prompts():
            for args in (
                ["set", "--json"],
                ["delete", "--json"],
                ["set", "single"],
                ["delete", "single"],
            ):
                with self.subTest(args=args):
                    code, _, _ = self.run_cli(*args, stdin=SENTINEL)
                    self.assertNotEqual(code, 0)
            self.assertFalse(self.calls)
            code, output, errors = self.run_cli("set", "new", "--yes", stdin=SENTINEL)
        self.assertEqual(code, 0, output + errors)
        self.assertNotIn(SENTINEL, output + errors)
        self.assertEqual(self.state["new"]["secret_value"], SENTINEL)

    def test_delete_without_names_uses_checkbox_and_confirms(self):
        with self.prompts(
            (("checkbox", "Select secrets to delete"), ["single", "credentials"]),
            (
                (
                    "confirm",
                    "Delete these account secrets for every project with access, including live? single, credentials",
                ),
                True,
            ),
        ):
            code, output, errors = self.run_cli("delete", tty=True)
        self.assertEqual(code, 0, output + errors)
        self.assertEqual(self.state, {})

    def test_invalid_input_never_writes_or_exposes_the_supplied_value(self):
        for value in ('{"password":"' + SENTINEL, '{"password": null}', "{}", "null"):
            with self.subTest(value_type=type(value)):
                self.calls.clear()
                code, output, errors = self.run_cli(
                    "set", "new", "--type", "key-value", "--json", stdin=value
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

    def test_missing_endpoint_is_not_reported_as_a_permission_failure(self):
        self.http.side_effect = None
        self.http.return_value = make_mock_response(
            404, {"error_message": SENTINEL}, content=SENTINEL.encode()
        )

        code, output, errors = self.run_cli("list", "--json")

        self.assertEqual(code, 1, output + errors)
        self.assertFalse(json.loads(output)["success"])
        self.assertIn("HTTP 404", output)
        self.assertIn("not found", output)
        self.assertIn("API", output)
        self.assertNotIn("permissions", output)
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
            {"value_type": "unsupported"},
            {"projects": ["a"], "grant": ["b"]},
            {"grant": ["a"], "revoke": ["a"]},
            {"value": {"token": 123}},
            {"value": {"token": {"nested": SENTINEL}}},
            {"delete_keys": "username"},
            {"delete_keys": [""]},
            {"delete_keys": ["username"], "value": {"username": "replacement"}},
            {"projects": [""]},
            {"projects": "project-a"},
        ):
            with self.subTest(options=list(kwargs)):
                with self.assertRaises(ValueError):
                    self.project.set_secret("credentials", **kwargs)
        self.assertFalse(any(method != "GET" for method, _ in self.calls))

    def test_key_deletion_requires_an_existing_key_value_secret(self):
        for name in ("single", "new"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "existing key-value secret"):
                    self.project.set_secret(name, delete_keys=["username"])
        self.assertFalse(any(method != "GET" for method, _ in self.calls))


if __name__ == "__main__":
    unittest.main()
