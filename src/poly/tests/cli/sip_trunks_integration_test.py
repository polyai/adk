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


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize(
    ("auth_type", "change"),
    [
        ("digest", "create"), ("token", "create"),
        ("digest", "enable"), ("token", "enable"),
        ("digest", "switch"), ("token", "switch"),
        ("digest", "rotate"), ("token", "rotate"),
        ("digest", "username"),
    ],
)
def test_manage_json_rejects_credentials_before_any_changes(tmp_path, capsys, auth_type, change, force):
    (tmp_path / "project.yaml").write_text(
        "project_id: project-1\naccount_id: acct-123\nregion: uk-1\n", encoding="utf-8"
    )
    auth_config = {"type": auth_type}
    if auth_type == "digest":
        auth_config["username"] = "bob" if change == "username" else "alice"
    credential_trunk = {
        "name": "Credential carrier", "default_route": None, "outbound": None,
        "sip_cidr": ["203.0.113.0/24"], "rtp_cidr": ["198.51.100.0/24"],
        "inbound_auth": auth_config,
    }
    remote_trunks = [{"id": "tr-safe", "name": "Old carrier", "inbound": {}}]
    if change != "create":
        credential_trunk["id"] = "tr-secret"
        current_type = (
            ("token" if auth_type == "digest" else "digest") if change == "switch" else auth_type
        )
        inbound = {}
        if change != "enable":
            inbound = (
                {"sip_auth": {"enabled": True, "username": "alice"}}
                if current_type == "digest" else {"sip_token_auth": {"enabled": True}}
            )
        remote_trunks.append({"id": "tr-secret", "name": "Credential carrier", "inbound": inbound})
    config_path = tmp_path / "sip-trunks.yaml"
    with config_path.open("w", encoding="utf-8") as config_file:
        YAML().dump([
            {"id": "tr-safe", "name": "Updated carrier", "default_route": None, "outbound": None},
            credential_trunk,
        ], config_file)
    source = config_path.read_text(encoding="utf-8")
    extra = ["--rotate-auth", "tr-secret"] if change == "rotate" else []
    if force:
        extra.append("--force")
    with (
        patch.object(
            PlatformAPIHandler, "make_request", return_value={"sip_trunks": remote_trunks}
        ) as request,
        patch("getpass.getpass") as secret,
        patch("questionary.confirm") as confirm,
        patch("poly.cli.display_update_message"),
    ):
        with pytest.raises(SystemExit) as exit_info:
            AgentStudioCLI().main([
                "sip-trunks", "manage", "--path", str(tmp_path), "--json", *extra,
            ])

    assert exit_info.value.code == 1
    result = json.loads(capsys.readouterr().out)
    assert result["success"] is False
    assert "--json" in result["error"]
    assert "credentials" in result["error"]
    assert "Run without --json" in result["error"]
    request.assert_called_once_with("uk-1", "/v1/accounts/acct-123/telephony/sip-trunks")
    secret.assert_not_called()
    confirm.assert_not_called()
    assert config_path.read_text(encoding="utf-8") == source


@pytest.mark.parametrize("auth_type", ["digest", "token"])
@pytest.mark.parametrize("change", ["update", "unchanged", "disable"])
def test_manage_json_keeps_changes_without_new_credentials_noninteractive(
    tmp_path, capsys, auth_type, change
):
    (tmp_path / "project.yaml").write_text(
        "project_id: project-1\naccount_id: acct-123\nregion: uk-1\n", encoding="utf-8"
    )
    auth_field = "sip_auth" if auth_type == "digest" else "sip_token_auth"
    remote_auth = {"enabled": True}
    auth_config = {"type": auth_type}
    if auth_type == "digest":
        remote_auth.update(username="alice", realm="example.com")
        auth_config.update(username="alice", realm="example.com")
    remote = {
        "id": "tr-123", "name": "Example carrier",
        "inbound": {"hostname": "tr-123.example.com", auth_field: remote_auth},
    }
    name = "Updated carrier" if change == "update" else remote["name"]
    config_path = tmp_path / "sip-trunks.yaml"
    with config_path.open("w", encoding="utf-8") as config_file:
        YAML().dump([{
            "id": "tr-123", "name": name, "hostname": "tr-123.example.com",
            "default_route": None, "outbound": None,
            "inbound_auth": {"type": "none"} if change == "disable" else auth_config,
        }], config_file)
    updated = {**remote, "name": name}
    if change == "disable":
        updated["inbound"] = {**remote["inbound"], auth_field: {"enabled": False}}
    endpoint = "/v1/accounts/acct-123/telephony/sip-trunks"
    with (
        patch.object(
            PlatformAPIHandler, "make_request",
            side_effect=[{"sip_trunks": [remote]}, updated],
        ) as request,
        patch("getpass.getpass") as secret,
        patch("questionary.confirm") as confirm,
    ):
        SIPTrunksCommand.run(sip_args(tmp_path, "manage"))

    result = json.loads(capsys.readouterr().out)
    assert result["success"] is True
    if change == "unchanged":
        assert result["changed"] is False
        assert request.call_args_list == [call("uk-1", endpoint)]
    else:
        expected_patch = (
            {"name": name} if change == "update" else {"inbound": {auth_field: {"disable": True}}}
        )
        assert request.call_args_list == [
            call("uk-1", endpoint),
            call("uk-1", f"{endpoint}/tr-123", "PATCH", data=expected_patch),
        ]
        assert result["trunks"][0]["status"] == "updated"
    secret.assert_not_called()
    confirm.assert_not_called()


@pytest.mark.parametrize("extension", ["1000", "+441234567890", "1.5"])
def test_manage_rejects_numeric_extensions_before_remote_calls(tmp_path, extension):
    (tmp_path / "project.yaml").write_text(
        "project_id: agent-1\naccount_id: acct-123\nregion: uk-1\n", encoding="utf-8"
    )
    config_path = tmp_path / "sip-trunks.yaml"
    source = (
        "- name: Example carrier\n"
        "  default_route: null\n"
        "  outbound: null\n"
        "  sip_cidr: [203.0.113.0/24]\n"
        "  rtp_cidr: [198.51.100.0/24]\n"
        "  extensions:\n"
        f"    - extension: {extension}\n"
        "      agent_id: agent-1\n"
        "      client_env: live\n"
    )
    config_path.write_text(source, encoding="utf-8")
    with (
        patch.object(PlatformAPIHandler, "make_request") as request,
        patch("getpass.getpass") as secret,
        patch("questionary.confirm") as confirm,
    ):
        with pytest.raises(ValueError, match="non-empty 'extension' string"):
            SIPTrunksCommand.run(sip_args(tmp_path, "manage"))

    request.assert_not_called()
    secret.assert_not_called()
    confirm.assert_not_called()
    assert config_path.read_text(encoding="utf-8") == source


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
    project_dir = tmp_path / "current-project"
    project_dir.mkdir()
    (project_dir / "project.yaml").write_text(
        "project_id: project-1\naccount_id: acct-123\nregion: uk-1\n"
    )
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
        SIPTrunksCommand.run(sip_args(project_dir, "list"))

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


@pytest.mark.parametrize(
    "extensions",
    [
        [],
        [
            {
                "extension": "+441234567890",
                "agent": {
                    "agent_id": "project-1",
                    "client_env": "live",
                    "variant_id": "variant-1",
                },
            }
        ],
    ],
)
def test_get_json_includes_trunk_details_and_extension_bindings(tmp_path, capsys, extensions):
    (tmp_path / "project.yaml").write_text(
        "project_id: project-1\naccount_id: acct-123\nregion: uk-1\n"
    )
    trunk = {
        "id": "tr-123",
        "name": "Example carrier",
        "inbound": {"hostname": "tr-123.example.com"},
    }
    with patch.object(
        PlatformAPIHandler,
        "make_request",
        side_effect=[trunk, {"extensions": extensions}],
    ):
        SIPTrunksCommand.run(sip_args(tmp_path, "get", "tr-123"))

    result = json.loads(capsys.readouterr().out)
    assert result == {**trunk, "extensions": extensions}
