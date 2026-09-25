"""SIP CLI integration through the project and shared API layers.

Copyright PolyAI Limited
"""

import json
from unittest.mock import call, patch

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
            "--account-id",
            "acct-123",
            "--region",
            "uk-1",
            "--json",
            *extra,
        ]
    )


def test_manage_creates_shared_trunk_and_persists_metadata(tmp_path, capsys):
    config_path = tmp_path / "sip-trunks.yaml"
    config_path.write_text(
        "- name: Shared carrier\n"
        "  sip_cidr: [203.0.113.0/24]\n"
        "  rtp_cidr: [198.51.100.0/24]\n"
        "  extensions:\n"
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
    ):
        SIPTrunksCommand.run(sip_args(tmp_path, "manage", "--yes"))

    assert request.call_args_list == [
        call("uk-1", endpoint),
        call(
            "uk-1",
            endpoint,
            "POST",
            data={
                "name": "Shared carrier",
                "sip_cidr": ["203.0.113.0/24"],
                "rtp_cidr": ["198.51.100.0/24"],
            },
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
    sync_client.assert_not_called()
    saved = YAML(typ="safe").load(config_path)
    assert saved[0]["id"] == "tr-123"
    assert saved[0]["hostname"] == "tr-123.example.com"
    assert [route["agent_id"] for route in saved[0]["extensions"]] == ["project-1", "project-3"]
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is True
    assert result["trunks"][0]["extensions_created"] == 2


def test_list_preserves_routes_to_multiple_projects(tmp_path, capsys):
    with (
        patch.object(
            PlatformAPIHandler,
            "make_request",
            side_effect=[
                {"sip_trunks": [{"id": "tr-123", "name": "Shared carrier"}]},
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
        SIPTrunksCommand.run(sip_args(tmp_path, "list"))

    assert request.call_args_list == [
        call("uk-1", "/v1/accounts/acct-123/telephony/sip-trunks"),
        call("uk-1", "/v1/accounts/acct-123/telephony/sip-trunks/tr-123/extensions"),
    ]
    sync_client.assert_not_called()
    result = json.loads(capsys.readouterr().out)
    assert result["account_id"] == "acct-123"
    assert result["sip_trunks"][0]["extensions"] == [
        {"extension": "1000", "agent_id": "project-1", "client_env": "live"},
        {"extension": "2000", "agent_id": "project-3", "client_env": "sandbox"},
    ]
