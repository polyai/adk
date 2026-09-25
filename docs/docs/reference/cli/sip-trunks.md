---
title: poly sip-trunks
description: Reference for the `poly sip-trunks` command.
---

# `poly sip-trunks`

Manage account-level SIP trunks and their extension-to-agent routes through the SIP Trunking API. `poly sip-trunks` requires a subcommand.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks manage
poly sip-trunks get <trunk_id>
poly sip-trunks delete <trunk_id>
~~~

By default, the command reads the account and region from the current ADK project or from project metadata immediately below the account directory. To run it without project metadata, pass `--account-id` and `--region` (`eu`, `uk`, or `us`).

## `poly sip-trunks list`

List the account's SIP trunks in a summary table, or export their configuration to a reusable YAML file.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks list --output export.yaml
poly sip-trunks list --output --force
poly sip-trunks list --account-id example-account --region uk --json
~~~

The export includes trunk IDs, hostnames, CIDRs, readable authentication state (including the digest realm), and all extension bindings. Creation and update timestamps are omitted. The file can be passed directly back to `manage`. SIP passwords and tokens are never returned by the API and therefore cannot appear in the export.

The export uses a top-level list and does not store a region. ADK infers the region from the account's `project.yaml` metadata. If projects for the account disagree, the command stops with an error. Use `--region` when no project metadata is available.

When `--output` is passed without a filename, the export goes to the account-level `sip-trunks.yaml`. For a project at `example-account/support-agent`, this is `example-account/sip-trunks.yaml`. An explicit output filename selects a custom location.

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account or account-directory metadata. |
| `--region` | Account region: `eu`, `uk`, or `us`; `euw-1`, `uk-1`, and `us-1` are also accepted. Defaults to project metadata. |
| `-o`, `--output [FILE]` | Write reusable YAML to `FILE`. Without `FILE`, write `sip-trunks.yaml` in the account directory. |
| `--force` | Overwrite an existing output file. |

`--json` output shape:

~~~json
{
  "account_id": "example-account",
  "sip_trunks": [
    {
      "id": "tr-example",
      "name": "Primary carrier",
      "sip_cidr": ["203.0.113.0/24"],
      "rtp_cidr": ["198.51.100.0/24"],
      "encrypted": true,
      "hostname": "tr-example.sbc.sip.uk.poly.ai",
      "inbound_auth": {
        "type": "digest",
        "username": "carrier-user",
        "realm": "sbc.sip.uk.poly.ai"
      },
      "extensions": [
        {
          "extension": "1000",
          "agent_id": "support-agent",
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
  "output_path": "/workspace/example-account/sip-trunks.yaml",
  "trunk_count": 1
}
~~~

## `poly sip-trunks manage`

Create or update SIP trunks and reconcile extension bindings from an account-level YAML file.

Examples:

~~~bash
poly sip-trunks manage
poly sip-trunks manage --yes
poly sip-trunks manage --file ../sip-trunks.yaml
poly sip-trunks manage --rotate-auth <trunk_id>
poly sip-trunks manage --yes --json
~~~

The preferred workflow uses an account-level `sip-trunks.yaml`. Given a project at `example-account/support-agent`, place the file at `example-account/sip-trunks.yaml`:

~~~yaml
- id: tr-example
  name: Primary carrier
  sip_cidr:
    - 203.0.113.0/24
  rtp_cidr:
    - 198.51.100.0/24
  encrypted: true
  hostname: tr-example.sbc.sip.uk.poly.ai
  inbound_auth:
    type: digest
    username: carrier-user
    realm: sbc.sip.uk.poly.ai
  extensions:
    - extension: "1000"
      agent_id: support-agent
      client_env: live
~~~

From a project directory, `manage` searches parent directories for the nearest `sip-trunks.yaml`. Use `--file` to select a file explicitly.

`manage` first validates the complete file and calculates a diff without writing or prompting for credentials. It displays the planned trunk, extension, credential-rotation, and local metadata changes, then asks whether to continue. After confirmation it creates missing trunks and extensions and patches changed ones. Use `--yes` to skip confirmation.

The human-readable output reports changed trunks, including their generated IDs and hostnames. If the YAML already matches the backend, it prints `Nothing changed.` After reconciling a trunk, `manage` writes the returned `id`, `hostname`, and digest `realm` back into the YAML using an atomic, formatting-preserving update. These generated fields are not sent in create or update request bodies. Creation and update timestamps are intentionally omitted. The older mapping format with a `sip_trunks:` wrapper remains readable for migration, but new exports use the top-level list.

Removing a trunk entry from YAML does **not** delete the live trunk; trunk deletion remains an explicit command. An `extensions` list is authoritative: removing an extension entry schedules its live binding for deletion, which is shown in the `manage` diff. Use `extensions: []` to remove every extension from a trunk. Omit the `extensions` key entirely to leave its extension bindings unmanaged.

SIP passwords and tokens must not be stored in YAML. `manage` prompts securely when a secret is required: when creating authenticated trunks, changing authentication type or digest username, and explicitly rotating credentials. An ordinary update to a trunk whose authentication is unchanged never prompts for or resends its credential.

Digest authentication declares only its non-secret state:

~~~yaml
inbound_auth:
  type: digest
  username: carrier-user
~~~

Only one inbound authentication mode can be configured. For SIP token authentication:

~~~yaml
inbound_auth:
  type: token
~~~

Use `type: none` to explicitly disable the trunk's current inbound authentication. Use `--rotate-auth` to explicitly rotate an existing credential.

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account or account-directory metadata. |
| `--region` | Account region: `eu`, `uk`, or `us`; `euw-1`, `uk-1`, and `us-1` are also accepted. Defaults to project metadata. |
| `-f`, `--file` | Configuration file. Defaults to the nearest `sip-trunks.yaml` found from the base path towards the filesystem root. |
| `--rotate-auth TRUNK_ID` | Prompt for and rotate credentials for this YAML-declared trunk. |
| `-y`, `--yes` | Apply the planned changes without prompting for confirmation. |

!!! info "JSON changes require confirmation to be skipped"

    `poly sip-trunks manage --json` requires `--yes` when changes exist. Required credential prompts still apply.

`--json` output shape after applying changes:

~~~json
{
  "success": true,
  "config_file": "/workspace/example-account/sip-trunks.yaml",
  "account_id": "example-account",
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
{
  "success": true,
  "changed": false,
  "trunks": []
}
~~~

## `poly sip-trunks get`

Display a detailed trunk table followed by its extension bindings.

Examples:

~~~bash
poly sip-trunks get <trunk_id>
poly sip-trunks get <trunk_id> --json
~~~

| Argument | Description |
|---|---|
| `trunk_id` | SIP trunk ID. Required. |

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account or account-directory metadata. |
| `--region` | Account region: `eu`, `uk`, or `us`; `euw-1`, `uk-1`, and `us-1` are also accepted. Defaults to project metadata. |

`--json` output shape:

~~~json
{
  "id": "tr-example",
  "name": "Primary carrier",
  "sip_cidr": ["203.0.113.0/24"],
  "rtp_cidr": ["198.51.100.0/24"],
  "encrypted": true,
  "inbound": {
    "hostname": "tr-example.sbc.sip.uk.poly.ai",
    "sip_auth": {
      "enabled": true,
      "username": "carrier-user",
      "realm": "sbc.sip.uk.poly.ai"
    },
    "sip_token_auth": {
      "enabled": false
    }
  },
  "created_at": "2026-08-12T12:00:00Z",
  "updated_at": "2026-08-12T12:01:00Z"
}
~~~

JSON mode returns the trunk API response directly. It does not add the separately fetched extension bindings shown in the table output; use `list --json` for configuration that includes extensions.

## `poly sip-trunks delete`

Delete a live SIP trunk by ID.

Examples:

~~~bash
poly sip-trunks delete <trunk_id>
poly sip-trunks delete <trunk_id> --yes
poly sip-trunks delete <trunk_id> --yes --json
~~~

`delete` asks for confirmation and prints a human-readable success message by default. Use `--yes` to skip confirmation.

| Argument | Description |
|---|---|
| `trunk_id` | SIP trunk ID. Required. |

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account or account-directory metadata. |
| `--region` | Account region: `eu`, `uk`, or `us`; `euw-1`, `uk-1`, and `us-1` are also accepted. Defaults to project metadata. |
| `-y`, `--yes` | Delete without prompting for confirmation. |

!!! info "JSON deletion requires confirmation to be skipped"

    `poly sip-trunks delete --json` requires `--yes`.

`--json` output shape:

~~~json
{
  "success": true,
  "trunk_id": "tr-example"
}
~~~
