"""API integration credential serialization, storage, and CLI tests.

Copyright PolyAI Limited
"""

import json
import unittest
from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock, call, patch

import requests

from poly.cli import AgentStudioCLI
from poly.cli_commands.api_integrations import (
    ApiIntegrationsCommand,
    _prompt_credentials,
    _studio_token,
)
from poly.handlers.integration_credentials import IntegrationCredentialsHandler
from poly.handlers.sdk import SourcererAPIError
from poly.project import AgentStudioProject
from poly.resources.api_integration import ApiIntegration

build_credentials = AgentStudioProject.build_api_integration_credentials


class CredentialSerializationTest(unittest.TestCase):
    def test_supported_auth_types_match_studio_shapes(self):
        cases = [
            ("basic", {"username": "user", "password": "secret"}, "basic"),
            ("apiKey", {"key": "X-Key", "value": "secret"}, "api_key"),
            ("oauth2", {"client_id": "client", "client_secret": "secret",
                         "access_token_url": "https://example.com/token"}, "oauth2"),
            ("jwt_client_assertion", {"client_id": "client", "private_key": "private",
                                      "token_url": "https://example.com/token", "key_id": "key"},
             "jwt_client_assertion"),
            ("oauth2_client_credentials", {"client_id": "client", "client_secret": "secret",
                                          "token_url": "https://example.com/token"},
             "oauth2_client_credentials"),
        ]
        for auth, values, stored_type in cases:
            with self.subTest(auth=auth):
                result = build_credentials(auth, values, "https://example.com")
                if auth in {"jwt_client_assertion", "oauth2_client_credentials"}:
                    self.assertEqual(result["base_url"], "https://example.com")
                    self.assertEqual(result["auth"]["type"], stored_type)
                    self.assertEqual(result["auth"]["config"]["client_id"], "client")
                else:
                    self.assertEqual(result["type"], stored_type)
                if auth == "oauth2":
                    self.assertEqual(result["clientSecret"], "secret")
                    self.assertEqual(result["scope"], "")
                    self.assertEqual(result["grant_type"], "client_credentials")

    def test_invalid_values_never_appear_in_errors(self):
        for values in [[], {"username": "user"},
                       {"username": "user", "password": "secret", "secret-extra": "secret"}]:
            with self.subTest(values_type=type(values)):
                with self.assertRaises(ValueError) as caught:
                    build_credentials("basic", values, "https://example.com")
                self.assertNotIn("secret", str(caught.exception))

    def test_invalid_location_is_rejected(self):
        with self.assertRaises(ValueError):
            build_credentials("apiKey", {"key": "X-Key", "value": "secret", "location": "invalid"}, "")


class CredentialStorageTest(unittest.TestCase):
    def set_credentials(self, environment="sandbox"):
        IntegrationCredentialsHandler.set_credentials(
            "euw-1", "token", "account", "project", "integration", environment,
            {"type": "basic", "username": "user", "password": "new-secret"},
        )

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_read_defaults_uses_selected_environment_and_legacy_spelling(self, request):
        for key in ["pre_release", "pre-release"]:
            request.return_value = [{
                "display_name": "api-integration-project-integration", "value_type": "key-value",
                "secret_value": {key: json.dumps({"type": "oauth2", "client_secret": "saved"}),
                                 "live": json.dumps({"client_secret": "other-env"})},
            }]
            values = IntegrationCredentialsHandler.get_credentials(
                "euw-1", "token", "account", "project", "integration", "pre-release")
            self.assertEqual(values, {"type": "oauth2", "client_secret": "saved"})

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_malformed_saved_json_is_redacted(self, request):
        request.return_value = [{
            "display_name": "api-integration-project-integration", "value_type": "key-value",
            "secret_value": {"sandbox": "saved-secret-not-json"},
        }]
        with self.assertRaises(ValueError) as caught:
            IntegrationCredentialsHandler.get_credentials(
                "euw-1", "token", "account", "project", "integration", "sandbox")
        self.assertNotIn("saved-secret", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_create_does_not_return_plaintext(self, request):
        request.side_effect = [[], {"secret_value": "new-secret"}]
        self.assertIsNone(self.set_credentials())
        payload = request.call_args.kwargs["json"]
        self.assertEqual(request.call_args.args[3], "POST")
        self.assertEqual(payload["access_config"], ["project"])
        self.assertEqual(json.loads(payload["secret_value"]["sandbox"])["password"], "new-secret")

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_updates_only_selected_environment_and_preserves_metadata(self, request):
        request.return_value = [{
            "display_name": "api-integration-project-integration", "value_type": "key-value",
            "description": "existing description", "access_config": ["project", "other"],
            "secret_value": {"sandbox": "sandbox-secret", "live": "live-secret",
                             "pre-release": "legacy", "pre_release": "old-secret"},
        }]
        self.set_credentials("pre-release")
        payload = request.call_args.kwargs["json"]
        self.assertEqual(request.call_args.args[3], "PUT")
        self.assertEqual(payload["secret_value"]["live"], "live-secret")
        self.assertEqual(payload["secret_value"]["sandbox"], "sandbox-secret")
        self.assertNotIn("pre-release", payload["secret_value"])
        self.assertEqual(payload["description"], "existing description")
        self.assertEqual(payload["access_config"], ["project", "other"])

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_redacted_response_is_not_overwritten(self, request):
        request.return_value = [{"display_name": "api-integration-project-integration",
                                 "value_type": "key-value"}]
        with self.assertRaises(ValueError):
            self.set_credentials()
        self.assertEqual(request.call_count, 1)

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_invalid_environment_does_not_make_requests(self, request):
        with self.assertRaises(ValueError):
            self.set_credentials("all")
        request.assert_not_called()

    @patch.object(IntegrationCredentialsHandler, "_request")
    def test_malformed_or_ambiguous_response_never_causes_a_write(self, request):
        for response in [{}, [None], [{}], ["secret"], [{}, {}]]:
            with self.subTest(response=response):
                request.reset_mock()
                request.return_value = response
                with self.assertRaises(ValueError):
                    self.set_credentials()
                self.assertEqual(request.call_count, 1)

    @patch("poly.handlers.platform_api.requests.request")
    def test_invalid_json_response_is_redacted(self, request):
        request.return_value.status_code = 200
        request.return_value.json.side_effect = ValueError("new-secret")
        with self.assertRaises(ValueError) as caught:
            self.set_credentials()
        self.assertNotIn("new-secret", str(caught.exception))
        self.assertEqual(request.call_count, 1)

    @patch("poly.handlers.platform_api.requests.request")
    def test_failed_write_is_reported_without_exposing_values(self, request):
        read = MagicMock(status_code=200)
        read.json.return_value = []
        write = MagicMock(status_code=403, text="new-secret")
        request.side_effect = [read, write]
        with self.assertRaisesRegex(SourcererAPIError, "HTTP 403") as caught:
            self.set_credentials()
        self.assertNotIn("new-secret", str(caught.exception))
        write.json.assert_not_called()

    @patch("poly.handlers.platform_api.requests.request")
    def test_http_failure_and_network_failure_are_redacted(self, request):
        request.return_value = MagicMock(status_code=403, text="new-secret")
        with self.assertRaises(SourcererAPIError) as caught:
            self.set_credentials()
        self.assertNotIn("new-secret", str(caught.exception))
        self.assertFalse(request.return_value.json.called)
        request.side_effect = requests.ConnectionError("new-secret")
        with self.assertRaises(SourcererAPIError) as caught:
            self.set_credentials()
        self.assertNotIn("new-secret", str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    @patch("poly.handlers.platform_api.requests.request")
    def test_transport_uses_studio_auth_without_logging_values(self, request):
        response = request.return_value
        response.status_code = 200
        response.json.return_value = []
        with self.assertLogs("poly.handlers.platform_api", level="DEBUG") as logs:
            self.set_credentials()
        self.assertNotIn("new-secret", "\n".join(logs.output))
        self.assertEqual(request.call_count, 2)
        kwargs = request.call_args.kwargs
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer token")
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["timeout"], 30)
        self.assertEqual(response.json.call_count, 1)


class ApiIntegrationsCommandTest(unittest.TestCase):
    def setUp(self):
        self.args = Namespace(path="/project", integration="crm", env="sandbox", stdin=True,
                              json=True, private_key_file=None, token_env="TEST_STUDIO_TOKEN")
        self.project = AgentStudioProject(region="euw-1", account_id="account", project_id="project",
                                          root_path="/project", resources={}, last_updated=None,
                                          branch_id="main", _api_handler=MagicMock())
        self.project._api_handler.branch_id = None
        self.projection = {"apiIntegrations": {"apiIntegrations": {"entities": {
            "integration": {"name": "crm", "environments": {
                "sandbox": {"authType": "basic", "baseUrl": "https://example.com"}}}}}}}

    def test_parser_registers_command(self):
        cli = AgentStudioCLI()
        cli.register_commands()
        args = cli._create_parser().parse_args(
            ["api-integrations", "configure", "crm", "--env", "sandbox", "--stdin"])
        self.assertEqual(args.command, "api-integrations")
        self.assertEqual(args.api_integrations_subcommand, "configure")
        self.assertEqual(args.integration, "crm")
        self.assertEqual(args.env, "sandbox")

    @patch("questionary.select")
    @patch("builtins.input", side_effect=["", "", "", ""])
    def test_prompt_reuses_masked_defaults_and_picks_location(self, read, select):
        select.return_value.ask.return_value = "body"
        saved = {"client_id": "saved-client-ABC", "client_secret": "saved-secret-DEF",
                 "access_token_url": "https://example.com/token", "scope": "old-scope",
                 "credentials_location": "header"}
        result = _prompt_credentials("oauth2", saved, None)
        self.assertEqual(result["client_id"], saved["client_id"])
        self.assertEqual(result["client_secret"], saved["client_secret"])
        self.assertEqual(result["access_token_url"], saved["access_token_url"])
        self.assertEqual(result["scope"], "")
        self.assertEqual(result["credentials_location"], "body")
        self.assertEqual(read.call_args_list[0].args[0], "Client ID [******ABC]: ")
        self.assertEqual(read.call_args_list[1].args[0], "Client Secret [******DEF]: ")
        self.assertEqual(read.call_args_list[2].args[0], "Token URL [https://example.com/token]: ")
        select.assert_called_once_with("Credentials location:", choices=["header", "body"],
                                       default="header")

    @patch("poly.output.console.warning")
    @patch("questionary.select")
    @patch("builtins.input", side_effect=["", "abc", "", "secret", "", "https://example.com/token", ""])
    def test_prompt_retries_required_fields_without_saved_values(self, read, select, warn):
        select.return_value.ask.return_value = "header"
        result = _prompt_credentials("oauth2", {}, None)
        self.assertEqual(result["client_id"], "abc")
        self.assertEqual(result["client_secret"], "secret")
        self.assertEqual(warn.call_count, 3)
        self.assertEqual(read.call_count, 7)

    @patch("builtins.input", return_value="")
    def test_short_saved_values_stay_fully_masked(self, read):
        result = _prompt_credentials("basic", {"username": "abc", "password": "xyz"}, None)
        self.assertEqual(result["password"], "xyz")
        read.assert_has_calls([call("Username [******]: "), call("Password [******]: ")])

    @patch("questionary.select")
    @patch("builtins.input", return_value="")
    def test_cancelled_picker_aborts_configuration(self, read, select):
        select.return_value.ask.return_value = None
        with self.assertRaises(KeyboardInterrupt):
            _prompt_credentials("oauth2", {"client_id": "abc", "client_secret": "saved",
                                           "access_token_url": "https://example.com/token"}, None)

    @patch.dict("os.environ", {"TEST_STUDIO_TOKEN": "explicit-token"})
    @patch("poly.cli_commands.api_integrations.apikey_session.load")
    def test_explicit_token_overrides_cached_session(self, load):
        self.assertEqual(_studio_token("euw-1", "TEST_STUDIO_TOKEN", False), "explicit-token")
        load.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    @patch("poly.cli_commands.api_integrations._signin")
    @patch("poly.cli_commands.api_integrations.apikey_session.load")
    def test_unexpired_studio_session_does_not_prompt_for_login(self, load, signin):
        load.return_value.token = "cached-token"
        self.assertEqual(_studio_token("euw-1", "TEST_STUDIO_TOKEN", True), "cached-token")
        load.assert_called_once_with("studio:euw-1")
        signin.assert_not_called()

    @patch.dict("os.environ", {}, clear=True)
    @patch("poly.cli_commands.api_integrations.apikey_session.save")
    @patch("poly.cli_commands.api_integrations.apikey_session.load", return_value=None)
    @patch("poly.cli_commands.api_integrations._signin", return_value="new-token")
    def test_missing_or_expired_session_signs_in_and_saves(self, signin, load, save):
        self.assertEqual(_studio_token("euw-1", "TEST_STUDIO_TOKEN", True), "new-token")
        signin.assert_called_once_with("euw-1")
        save.assert_called_once_with("studio:euw-1", "new-token")

    @patch.dict("os.environ", {}, clear=True)
    @patch("poly.cli_commands.api_integrations._signin")
    @patch("poly.cli_commands.api_integrations.apikey_session.load", return_value=None)
    def test_noninteractive_run_does_not_start_browser_login(self, load, signin):
        with self.assertRaisesRegex(ValueError, "TEST_STUDIO_TOKEN"):
            _studio_token("us-1", "TEST_STUDIO_TOKEN", False)
        load.assert_called_once_with("studio:us-1")
        signin.assert_not_called()

    def test_project_reads_legacy_and_nested_oauth_defaults(self):
        for auth_type, saved in [
            ("oauth2", {"type": "oauth2", "clientId": "abc", "clientSecret": "saved",
                        "accessTokenUrl": "https://example.com/token"}),
            ("oauth2_client_credentials", {"auth": {"type": "oauth2_client_credentials",
                                          "config": {"client_id": "abc", "client_secret": "saved"}}}),
        ]:
            self.projection["apiIntegrations"]["apiIntegrations"]["entities"]["integration"]["environments"]["sandbox"]["authType"] = auth_type
            self.project._api_handler.get_api_integrations.return_value = ApiIntegration.from_projection(self.projection)
            self.project._api_handler.get_api_integration_credentials.return_value = saved
            values = self.project.get_api_integration_credential_defaults("crm", "sandbox", "token")
            self.assertEqual(values["client_id"], "abc")
            self.assertEqual(values["client_secret"], "saved")

    def test_changed_auth_type_does_not_reuse_incompatible_defaults(self):
        self.project._api_handler.get_api_integrations.return_value = ApiIntegration.from_projection(self.projection)
        self.project._api_handler.get_api_integration_credentials.return_value = {
            "type": "oauth2", "password": "do-not-reuse"}
        self.assertEqual(self.project.get_api_integration_credential_defaults("crm", "sandbox", "token"), {})

    def test_invalid_environment_does_not_fetch_or_write(self):
        with self.assertRaises(ValueError):
            self.project.configure_api_integration("crm", "all", {}, "token")
        self.project._api_handler.get_api_integrations.assert_not_called()
        self.project._api_handler.set_api_integration_credentials.assert_not_called()

    def test_invalid_credentials_do_not_write(self):
        self.project._api_handler.get_api_integrations.return_value = ApiIntegration.from_projection(self.projection)
        with self.assertRaises(ValueError):
            self.project.configure_api_integration("crm", "sandbox", {"username": "user"}, "token")
        self.project._api_handler.set_api_integration_credentials.assert_not_called()

    @patch("poly.cli_commands.api_integrations._signin")
    @patch("poly.cli_commands.api_integrations.load_project")
    def test_stdin_sets_credentials_without_exposing_values(self, load, signin):
        load.return_value = self.project
        self.project._api_handler.get_api_integrations.return_value = ApiIntegration.from_projection(self.projection)
        setter = self.project._api_handler.set_api_integration_credentials
        stdin = StringIO('{"username":"user","password":"secret"}')
        stdout = StringIO()
        with patch.dict("os.environ", {"TEST_STUDIO_TOKEN": "token"}), \
                patch("sys.stdin", stdin), patch("sys.stdout", stdout):
            ApiIntegrationsCommand.run(self.args)
        signin.assert_not_called()
        self.assertEqual(setter.call_args.args[1:3], ("integration", "sandbox"))
        self.assertEqual(setter.call_args.args[3]["password"], "secret")
        self.assertTrue(json.loads(stdout.getvalue())["success"])
        self.assertNotIn("secret", stdout.getvalue())
