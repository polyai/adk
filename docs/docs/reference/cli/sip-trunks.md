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

By default, the command reads the account and canonical API region from the current ADK project. It finds the project by walking up from the current working directory, or from `--path` when supplied, so commands also work from project subdirectories. Defaults come only from that project, never from sibling projects or directory names.

`--account-id` (or `--account_id`) and `--region` (`euw-1`, `uk-1`, or `us-1`) each override the corresponding project value. Supplying both lets you run without a project. Standalone `manage` also requires `--file`, and standalone export requires an explicit output filename.

## `poly sip-trunks list`

List the account's SIP trunks in a summary table, or export their configuration to a reusable YAML file.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks list --output ../sip-trunks.yaml  # shared export, run from project root
poly sip-trunks list --output export.yaml
poly sip-trunks list --output --force
poly sip-trunks list --account-id my-account --region uk-1 --json
~~~

The export includes trunk IDs, hostnames, CIDRs, readable authentication state (including the digest realm), and all extension bindings. Creation and update timestamps are omitted. The file can be passed directly back to `manage`. SIP passwords and tokens are never returned by the API and therefore cannot appear in the export.

The export uses a top-level list without account or region fields. Each file describes trunks for one account and region, including all their extension bindings; the current project does not filter routes by agent.

When `--output` is passed without a filename, the export goes to `sip-trunks.yaml` in the project root, even when run from a project subdirectory. An explicit output filename is relative to the current working directory and works with or without a project. Exporting without a project requires both context flags and an explicit output filename. Overwriting an existing file requires `--force`, including with `--json`.

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account. |
| `--region` | Account region: `euw-1`, `uk-1`, or `us-1`. Defaults to project metadata. |
| `-o`, `--output [FILE]` | Write reusable YAML to `FILE`. Without `FILE`, write `sip-trunks.yaml` in the project root. Explicit paths are relative to the current working directory. |
| `--force` | Overwrite an existing output file. |

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
      "inbound_auth": {
        "type": "digest",
        "username": "carrier-user",
        "realm": "sbc.sip.uk.poly.ai"
      },
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
  "output_path": "/path/to/projects/my-project/sip-trunks.yaml",
  "trunk_count": 1
}
~~~

## `poly sip-trunks manage`

Create or update SIP trunks and reconcile extension bindings from a YAML file for one account and region.

Examples:

~~~bash
poly sip-trunks manage
poly sip-trunks manage --force
poly sip-trunks manage --file ../sip-trunks.yaml
poly sip-trunks manage --rotate-auth <trunk_id>
poly sip-trunks manage --json
~~~

Place `sip-trunks.yaml` in the project root or its immediate parent. The parent is a convenient shared location for projects using the same account and region. The file uses a top-level list:

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
      agent_id: my-project
      client_env: live
~~~

`manage` searches the project root for `sip-trunks.yaml`, then its immediate parent, and stops there. This search is the same when running from a project subdirectory. `--file` selects a file relative to the current working directory; it does not change the account or region. Without a project, supply `--account-id`, `--region`, and `--file`.

The YAML contains neither account nor region fields. All entries use the selected account and region, and extension routes are not filtered by the current project's agent.

`manage` first validates the complete file and calculates a diff without writing or prompting for credentials. By default, it displays the planned trunk, extension, credential-rotation, and local metadata changes, then asks whether to continue. After confirmation it creates missing trunks and extensions and patches changed ones. Use `--force` to skip confirmation. With `--json`, it automatically skips confirmation, applies the planned changes, and prints the result as JSON.

The human-readable output reports changed trunks, including their generated IDs and hostnames. If the YAML already matches the backend, it prints `Nothing changed.` After reconciling a trunk, `manage` writes the returned `id`, `hostname`, and digest `realm` back into the YAML using an atomic, formatting-preserving update. These generated fields are not sent in create or update request bodies. Creation and update timestamps are intentionally omitted. Both `manage` and YAML exports use the top-level list format shown above.

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
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account. |
| `--region` | Account region: `euw-1`, `uk-1`, or `us-1`. Defaults to project metadata. |
| `--file` | Configuration file, relative to the current working directory. Defaults to `sip-trunks.yaml` in the project root, then its immediate parent. |
| `--rotate-auth TRUNK_ID` | Prompt for and rotate credentials for this YAML-declared trunk. |
| `-f`, `--force` | Apply the planned changes without prompting for confirmation. |

!!! info "JSON mode skips confirmation"

    `poly sip-trunks manage --json` applies changes without asking for confirmation; `--force` is not required. Required credential prompts still apply.

`--json` output shape after applying changes:

~~~json
{
  "success": true,
  "config_file": "/path/to/projects/sip-trunks.yaml",
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
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account. |
| `--region` | Account region: `euw-1`, `uk-1`, or `us-1`. Defaults to project metadata. |

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
poly sip-trunks delete <trunk_id> --force
poly sip-trunks delete <trunk_id> --json
~~~

`delete` asks for confirmation and prints a human-readable success message by default. Use `--force` to skip confirmation. With `--json`, it automatically skips confirmation, deletes the trunk, and prints the result as JSON.

| Argument | Description |
|---|---|
| `trunk_id` | SIP trunk ID. Required. |

| Flag | Description |
|---|---|
| `--account-id`, `--account_id` | PolyAI account ID. Defaults to the current project's account. |
| `--region` | Account region: `euw-1`, `uk-1`, or `us-1`. Defaults to project metadata. |
| `-f`, `--force` | Delete without prompting for confirmation. |

`--json` output shape:

~~~json
{
  "success": true,
  "trunk_id": "tr-example"
}
~~~
