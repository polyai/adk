---
title: poly sip-trunks
description: Reference for the `poly sip-trunks` command.
---

# `poly sip-trunks`

Manage SIP trunks and call routing for your project's account and region. `poly sip-trunks` requires a subcommand.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks manage
poly sip-trunks get <trunk_id>
poly sip-trunks delete <trunk_id>
~~~

Run these commands from an ADK project. The account and region come from its project configuration. To select a project with `--path`, see [Shared flags](../cli.md#shared-flags).

## `poly sip-trunks list`

List the account's SIP trunks, or export their current configuration to YAML for editing with `manage`.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks list --output ../sip-trunks.yaml
poly sip-trunks list --output --force
poly sip-trunks list --json
~~~

The table shows each trunk's ID, hostname, encryption, authentication, default route, outbound addresses, and extension count.

An export includes every trunk in the project's account and region, with all extension bindings. It uses the same YAML format as `manage`. Disabled default routes and outbound settings are exported as `null`; passwords, tokens, and timestamps are excluded.

| Flag | Description |
|---|---|
| `-o`, `--output [FILE]` | Write YAML to `FILE`, relative to the working directory. Without a filename, write `sip-trunks.yaml` in the project root. |
| `--force` | Allow an existing output file to be overwritten. Required for overwrites even with `--json`. |

`--json` output shape:

~~~json
{
  "account_id": "my-account",
  "sip_trunks": [
    {
      "id": "tr-example",
      "name": "Primary carrier",
      "sip_cidr": ["203.0.113.0/24"],
      "rtp_cidr": ["198.51.100.0/24"],
      "encrypted": true,
      "hostname": "tr-example.sbc.sip.uk.poly.ai",
      "default_route": null,
      "outbound": null,
      "inbound_auth": {"type": "none"},
      "extensions": [
        {
          "extension": "1000",
          "agent_id": "my-project",
          "client_env": "live"
        }
      ]
    }
  ]
}
~~~

With `--output`, the JSON response describes the written file:

~~~json
{
  "success": true,
  "output_path": "/path/to/my-project/sip-trunks.yaml",
  "trunk_count": 1
}
~~~

## `poly sip-trunks manage`

Create or update trunks from `sip-trunks.yaml`.

Examples:

~~~bash
poly sip-trunks manage
poly sip-trunks manage --file ../shared-sip-trunks.yaml
poly sip-trunks manage --force
poly sip-trunks manage --rotate-auth <trunk_id>
poly sip-trunks manage --json
~~~

Save `sip-trunks.yaml` in the project root. Projects in the same account and region can share a file in their immediate parent directory; a file in the project root takes precedence. Use separate files for different accounts or regions.

`manage` validates the configuration, displays the proposed changes, and asks for confirmation before applying them. It prompts for any required credentials, then creates or updates the trunks and extension bindings. When no changes are needed, it prints `Nothing changed.`

### Configuration file

The file is a list of trunks. To create a trunk with one inbound extension:

~~~yaml
- name: Primary carrier
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  encrypted: true
  default_route: null
  outbound: null
  inbound_auth:
    type: digest
    username: carrier-user
  extensions:
    - extension: "1000"
      agent_id: my-project
      client_env: live
~~~

| Field | Description |
|---|---|
| `id` | Identifies an existing trunk. Omit for a new trunk. Without an ID, `manage` matches by name or creates the trunk if no match exists. Names must be unambiguous. |
| `name` | Display name to apply. Keep this field when editing an existing trunk. |
| `sip_cidr` | SIP server CIDR blocks. Required when creating a trunk. |
| `rtp_cidr` | RTP/media server CIDR blocks. Required when creating a trunk. |
| `encrypted` | Enable encrypted signaling and media. Defaults to `true` for a new trunk. |
| `default_route` | **Required.** An agent target, or `null` to disable the default route. |
| `outbound` | **Required.** Outbound destinations and optional caller ID, or `null` to disable outbound calling. |
| `inbound_auth` | Authentication mode: `digest`, `token`, or `none`. Omit to leave existing authentication unchanged. |
| `extensions` | The complete list of extension bindings to keep on this trunk. Omit to leave existing bindings unchanged. |

After applying changes, `manage` saves the trunk's `id`, `hostname`, and digest `realm` into the file, preserving comments and formatting. Keep the ID to identify the trunk on later runs. The hostname and realm are informational fields supplied by the API.

### Default route

The default route handles inbound calls that do not match an extension:

~~~yaml
default_route:
  agent_id: my-project
  client_env: live
  variant_id: my-variant
~~~

`agent_id` and `client_env` are required. The environment is `sandbox`, `pre-release`, or `live`. Omit `variant_id`, or set it to an empty string, to use the agent's default variant.

Set `default_route: null` to remove the current default route or create a trunk without one. Calls that match an extension still use that extension's route; unmatched calls are rejected when there is no default route.

### Extension bindings

Each extension specifies an `extension`, `agent_id`, and `client_env`, as shown in the configuration example. Quote extension values to preserve leading zeros and `+` prefixes. Use the same environment names as the default route. Set `variant_id` to route to a named variant, or to an empty string to select the default variant.

A trunk can route calls to several projects. When managing its `extensions` list, include every binding that should remain on the trunk, including bindings for other projects:

| YAML | Effect |
|---|---|
| `extensions: [...]` | Create or update the listed bindings and delete existing bindings absent from the list. |
| `extensions: []` | Delete all extension bindings on the trunk. |
| `extensions` omitted or `null` | Leave existing extension bindings unchanged. |

Removing an entire trunk from the file leaves the live trunk unchanged. Use `poly sip-trunks delete <trunk_id>` to delete it.

### Outbound calling

Configure the SIP servers that receive outbound calls from PolyAI:

~~~yaml
outbound:
  sip_addresses:
    - sip:sbc.example.com:5060;transport=tcp
  default_caller_id: "+442079460000"
~~~

| Field | Description |
|---|---|
| `sip_addresses` | **Required.** 1–4 `sip:` or `sips:` server URIs, each at most 255 characters. A URI may include a port and transport parameter, but no user part such as `user@`. Address order has no effect. |
| `default_caller_id` | Optional string of at most 128 characters. Omitting it, or setting it to an empty string, clears any existing default caller ID. |

Set `outbound: null` to clear the outbound destinations and default caller ID, or create a trunk without outbound settings. An empty mapping or empty address list is not accepted in YAML.

### Authentication

Choose an inbound authentication mode:

| Configuration | Effect |
|---|---|
| `inbound_auth: {type: digest, username: carrier-user}` | Enable SIP digest authentication with the specified username. |
| `inbound_auth: {type: token}` | Enable SIP token authentication. |
| `inbound_auth: {type: none}` | Disable inbound authentication. |
| `inbound_auth` omitted or `null` | Leave existing authentication unchanged. |

Passwords and tokens are entered through secure prompts. Do not put credentials or environment-variable references to credentials in the YAML. Prompts appear when enabling digest or token authentication, switching between them, changing the digest username, or rotating credentials with `--rotate-auth`. Routine updates do not prompt for or resend credentials.

### Options

| Flag | Description |
|---|---|
| `--file FILE` | Read the specified YAML file instead of the default `sip-trunks.yaml`. Relative paths use the working directory. |
| `--rotate-auth TRUNK_ID` | Prompt for a new credential for a trunk declared in the file with digest or token authentication. |
| `-f`, `--force` | Apply changes without confirmation. |

!!! info "JSON mode skips confirmation"

    `manage --json` applies changes without asking for confirmation. Required credential prompts still appear.

`--json` output shape after applying changes:

~~~json
{
  "success": true,
  "config_file": "/path/to/my-project/sip-trunks.yaml",
  "account_id": "my-account",
  "region": "uk-1",
  "trunks": [
    {
      "key": "tr-example",
      "id": "tr-example",
      "name": "Primary carrier",
      "status": "updated",
      "hostname": "tr-example.sbc.sip.uk.poly.ai",
      "extensions_total": 1,
      "extensions_created": 0,
      "extensions_updated": 1,
      "extensions_deleted": 0
    }
  ]
}
~~~

When there are no changes:

~~~json
{"success": true, "changed": false, "trunks": []}
~~~

## `poly sip-trunks get`

Show a trunk's configuration and extension bindings, including its default route, outbound destinations, and default caller ID.

Examples:

~~~bash
poly sip-trunks get <trunk_id>
poly sip-trunks get <trunk_id> --json
~~~

| Argument | Description |
|---|---|
| `trunk_id` | SIP trunk ID. Required. |

`--json` returns the trunk API response. It omits separately fetched extension bindings; use `list --json` for an export that includes them. Optional API settings such as `inbound.default_route` and `outbound` are absent when unconfigured.

`--json` output shape:

~~~json
{
  "id": "tr-example",
  "account_id": "my-account",
  "name": "Primary carrier",
  "sip_cidr": ["203.0.113.0/24"],
  "rtp_cidr": ["198.51.100.0/24"],
  "encrypted": true,
  "inbound": {
    "hostname": "tr-example.sbc.sip.uk.poly.ai",
    "sip_auth": {"enabled": false},
    "sip_token_auth": {"enabled": false}
  },
  "created_at": "2026-08-12T12:00:00Z",
  "updated_at": "2026-08-12T12:01:00Z"
}
~~~

## `poly sip-trunks delete`

Delete a live SIP trunk by ID. The command asks for confirmation before deleting it.

Examples:

~~~bash
poly sip-trunks delete <trunk_id>
poly sip-trunks delete <trunk_id> --force
poly sip-trunks delete <trunk_id> --json
~~~

| Argument | Description |
|---|---|
| `trunk_id` | SIP trunk ID. Required. |

| Flag | Description |
|---|---|
| `-f`, `--force` | Delete without confirmation. |

!!! info "JSON mode skips confirmation"

    `delete --json` deletes the trunk without asking for confirmation.

`--json` output shape:

~~~json
{"success": true, "trunk_id": "tr-example"}
~~~
