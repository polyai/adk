"""SIP CLI integration through the project and shared API layers.

Copyright PolyAI Limited
"""

import json
from unittest.mock import call, patch

import pytest
from ruamel.yaml import YAML

from poly.cli import AgentStudioCLI
from poly.cli_commands.sip_trunks import SIPTrunksCommand
from poly.handlers.platform_api import PlatformAPIHandler


def sip_args(path, action, *extra):
    cli = AgentStudioCLI()
    cli.register_commands()
    return cli._create_parser().parse_args(
        [
            "sip-trunks",
            action,
            "--path",
            str(path),
            "--json",
            *extra,
        ]
    )


@pytest.mark.parametrize("disable_default_route", [False, True])
@pytest.mark.parametrize("disable_outbound", [False, True])
def test_manage_creates_shared_trunk_and_persists_metadata(
    tmp_path, capsys, disable_default_route, disable_outbound
):
    project_dir = tmp_path / "current-project"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        "project_id: project-1\naccount_id: acct-123\nregion: uk-1\n"
    )
    sibling_dir = tmp_path / "sibling-project"
    sibling_dir.mkdir()
    (sibling_dir / "project.yaml").write_text(
        "project_id: project-2\naccount_id: acct-123\nregion: us-1\n"
    )
    config_path = tmp_path / "sip-trunks.yaml"
    route_yaml = (
        "  default_route: null\n"
        if disable_default_route
        else "  default_route:\n"
        "    agent_id: project-4\n"
        "    client_env: live\n"
        "    variant_id: variant-1\n"
    )
    outbound_yaml = (
        "  outbound: null\n"
        if disable_outbound
        else "  outbound:\n"
        "    sip_addresses: ['sip:carrier.example.com', 'sip:backup.example.com']\n"
        "    default_caller_id: '+441234567890'\n"
    )
    config_path.write_text(
        "- name: Shared carrier\n"
        "  sip_cidr: [203.0.113.0/24]\n"
        "  rtp_cidr: [198.51.100.0/24]\n" + route_yaml + outbound_yaml + "  extensions:\n"
        "    - extension: '1000'\n"
        "      agent_id: project-1\n"
        "      client_env: live\n"
        "    - extension: '+44/2000'\n"
        "      agent_id: project-3\n"
        "      client_env: sandbox\n"
    )
    endpoint = "/v1/accounts/acct-123/telephony/sip-trunks"
    with (
        patch.object(
            PlatformAPIHandler,
            "make_request",
            side_effect=[
                {"sip_trunks": []},
                {"id": "tr-123", "inbound": {"hostname": "tr-123.example.com"}},
                {},
                {},
            ],
        ) as request,
        patch("poly.handlers.interface.SyncClientHandler") as sync_client,
        patch("questionary.confirm") as confirm,
    ):
        SIPTrunksCommand.run(sip_args(project_dir, "manage"))

    expected_create = {
        "name": "Shared carrier",
        "sip_cidr": ["203.0.113.0/24"],
        "rtp_cidr": ["198.51.100.0/24"],
    }
    expected_default_route = None
    if not disable_default_route:
        expected_default_route = {
            "agent_id": "project-4",
            "client_env": "live",
            "variant_id": "variant-1",
        }
        expected_create["inbound"] = {"default_route": {"agent": expected_default_route}}
    expected_outbound = None
    if not disable_outbound:
        expected_outbound = {
            "sip_addresses": ["sip:carrier.example.com", "sip:backup.example.com"],
            "default_caller_id": "+441234567890",
        }
        expected_create["outbound"] = expected_outbound

    assert request.call_args_list == [
        call("uk-1", endpoint),
        call(
            "uk-1",
            endpoint,
            "POST",
            data=expected_create,
        ),
        call(
            "uk-1",
            f"{endpoint}/tr-123/extensions",
            "POST",
            data={
                "extension": "1000",
                "agent": {"agent_id": "project-1", "client_env": "live"},
            },
        ),
        call(
            "uk-1",
            f"{endpoint}/tr-123/extensions",
            "POST",
            data={
                "extension": "+44/2000",
                "agent": {"agent_id": "project-3", "client_env": "sandbox"},
            },
        ),
    ]
    confirm.assert_not_called()
    sync_client.assert_not_called()
    saved = YAML(typ="safe").load(config_path)
    assert saved[0]["id"] == "tr-123"
    assert saved[0]["hostname"] == "tr-123.example.com"
    assert saved[0]["default_route"] == expected_default_route
    assert saved[0]["outbound"] == expected_outbound
    assert [route["agent_id"] for route in saved[0]["extensions"]] == ["project-1", "project-3"]
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is True
    assert result["account_id"] == "acct-123"
    assert result["region"] == "uk-1"
    assert result["config_file"] == str(config_path)
    assert result["trunks"][0]["extensions_created"] == 2


@pytest.mark.parametrize(
    ("inbound", "expected_default_route"),
    [
        (
            {
                "default_route": {
                    "agent": {
                        "agent_id": "project-4",
                        "client_env": "live",
                        "variant_id": "variant-1",
                    }
                }
            },
            {
                "agent_id": "project-4",
                "client_env": "live",
                "variant_id": "variant-1",
            },
        ),
        ({}, None),
    ],
)
@pytest.mark.parametrize(
    "outbound",
    [
        {
            "sip_addresses": ["sip:carrier.example.com", "sip:backup.example.com"],
            "default_caller_id": "+441234567890",
        },
        None,
    ],
)
def test_list_preserves_routes_to_multiple_projects(
    tmp_path, capsys, inbound, expected_default_route, outbound
):
    remote_trunk = {"id": "tr-123", "name": "Shared carrier", "inbound": inbound}
    if outbound is not None:
        remote_trunk["outbound"] = outbound
    with (
        patch.object(
            PlatformAPIHandler,
            "make_request",
            side_effect=[
                {"sip_trunks": [remote_trunk]},
                {
                    "extensions": [
                        {
                            "extension": "1000",
                            "agent": {"agent_id": "project-1", "client_env": "live"},
                        },
                        {
                            "extension": "2000",
                            "agent": {"agent_id": "project-3", "client_env": "sandbox"},
                        },
                    ]
                },
            ],
        ) as request,
        patch("poly.handlers.interface.SyncClientHandler") as sync_client,
    ):
        SIPTrunksCommand.run(
            sip_args(tmp_path, "list", "--account-id", "acct-123", "--region", "uk-1")
        )

    assert request.call_args_list == [
        call("uk-1", "/v1/accounts/acct-123/telephony/sip-trunks"),
        call("uk-1", "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions"),
    ]
    sync_client.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert result["account_id"] == "acct-123"
    assert result["sip_trunks"][0]["default_route"] == expected_default_route
    assert result["sip_trunks"][0]["outbound"] == outbound
    assert result["sip_trunks"][0]["extensions"] == [
        {"extension": "1000", "agent_id": "project-1", "client_env": "live"},
        {"extension": "2000", "agent_id": "project-3", "client_env": "sandbox"},
    ]
