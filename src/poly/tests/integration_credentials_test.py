"""API integration credential serialization, storage, and CLI tests.

Copyright PolyAI Limited
"""

import json
import unittest
from argparse import Namespace
from io import StringIO
from unittest.mock import MagicMock, patch

import requests

from poly.cli import AgentStudioCLI
from poly.cli_commands.api_integrations import ApiIntegrationsCommand
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
