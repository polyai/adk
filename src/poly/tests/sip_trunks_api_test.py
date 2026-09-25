"""Tests for SIP trunk routing through the shared API layers.

Copyright PolyAI Limited
"""

import json
import os
from unittest.mock import patch

import pytest

from poly.handlers.interface import AgentStudioInterface
from poly.handlers.platform_api import PlatformAPIHandler
from poly.tests.testing_utils import make_mock_response

API_CASES = [
    ("list_sip_trunks", (), "", "GET", None),
    ("create_sip_trunk", (), "", "POST", {"name": "Primary carrier"}),
    ("get_sip_trunk", ("tr-123",), "/tr-123", "GET", None),
    ("update_sip_trunk", ("tr-123",), "/tr-123", "PATCH", {"encrypted": True}),
    ("delete_sip_trunk", ("tr-123",), "/tr-123", "DELETE", None),
    ("list_sip_trunk_extensions", ("tr-123",), "/tr-123/extensions", "GET", None),
    (
        "create_sip_trunk_extension",
        ("tr-123",),
        "/tr-123/extensions",
        "POST",
        {"extension": "1000", "agent": {"agent_id": "agent-1", "client_env": "live"}},
    ),
    (
        "get_sip_trunk_extension",
        ("tr-123", "1000"),
        "/tr-123/extensions/1000",
        "GET",
        None,
    ),
    (
        "update_sip_trunk_extension",
        ("tr-123", "1000"),
        "/tr-123/extensions/1000",
        "PATCH",
        {"agent": {"agent_id": "agent-2", "client_env": "sandbox"}},
    ),
    (
        "delete_sip_trunk_extension",
        ("tr-123", "1000"),
        "/tr-123/extensions/1000",
        "DELETE",
        None,
    ),
]


@pytest.mark.parametrize("method_name,identifiers,suffix,verb,payload", API_CASES)
def test_sip_interface_preserves_request_contract(method_name, identifiers, suffix, verb, payload):
    args = ("uk-1", "acct-123", *identifiers)
    if payload is not None:
        args += (payload,)

    with (
        patch.object(PlatformAPIHandler, "make_request") as make_request,
        patch("poly.handlers.interface.SyncClientHandler") as sync_client,
    ):
        result = getattr(AgentStudioInterface, method_name)(*args)

    expected_args = ("uk-1", f"/v1/accounts/acct-123/telephony/sip-trunks{suffix}")
    if verb != "GET":
        expected_args += (verb,)
    expected_kwargs = {} if payload is None else {"data": payload}
    make_request.assert_called_once_with(*expected_args, **expected_kwargs)
    sync_client.assert_not_called()
    assert result is make_request.return_value
    if payload is not None:
        assert make_request.call_args.kwargs["data"] is payload


@pytest.mark.parametrize(
    "method_name,verb,payload",
    [
        ("get_sip_trunk_extension", "GET", None),
        ("update_sip_trunk_extension", "PATCH", {"agent": {"agent_id": "agent-1"}}),
        ("delete_sip_trunk_extension", "DELETE", None),
    ],
)
def test_sip_path_segments_encode_reserved_characters(method_name, verb, payload):
    args = ("us-1", "acct/one?", "tr#1%", "+44/100?x=1")
    if payload is not None:
        args += (payload,)

    with patch.object(PlatformAPIHandler, "make_request") as make_request:
        getattr(PlatformAPIHandler, method_name)(*args)

    expected_args = (
        "us-1",
        "/v1/accounts/acct%2Fone%3F/telephony/sip-trunks/tr%231%25/extensions/%2B44%2F100%3Fx%3D1",
    )
    if verb != "GET":
        expected_args += (verb,)
    expected_kwargs = {} if payload is None else {"data": payload}
    make_request.assert_called_once_with(*expected_args, **expected_kwargs)


def test_sip_requests_retain_shared_auth_and_user_override_headers():
    payload = {"name": "Primary carrier"}
    response = {"id": "tr-123"}
    with (
        patch("poly.handlers.platform_api.retrieve_api_key", return_value="test-api-key"),
        patch.dict(os.environ, {"ADK_COMMAND_USER_OVERRIDE": "developer@example.com"}),
        patch(
            "poly.handlers.platform_api.requests.request",
            return_value=make_mock_response(status_code=201, json_body=response),
        ) as request,
    ):
        result = AgentStudioInterface.create_sip_trunk("uk-1", "acct-123", payload)

    request.assert_called_once()
    sent = request.call_args.kwargs
    assert sent["method"] == "POST"
    assert sent["url"] == "https://api.uk.poly.ai/v1/accounts/acct-123/telephony/sip-trunks"
    assert sent["headers"]["X-API-KEY"] == "test-api-key"
    assert sent["headers"]["X-Poly-Source"] == "adk"
    assert sent["headers"]["X-PolyAI-Email"] == "developer@example.com"
    assert sent["headers"]["Content-Type"] == "application/json"
    assert sent["headers"]["X-PolyAI-Correlation-Id"].startswith("adk-")
    assert json.loads(sent["data"]) == payload
    assert result == response
