---
title: poly sip-trunks
description: Reference for the `poly sip-trunks` command.
---

# `poly sip-trunks`

Manage account-level SIP trunks, default routes, outbound settings, and extension-to-agent routes through the SIP Trunking API. `poly sip-trunks` requires a subcommand.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks manage
poly sip-trunks get <trunk_id>
poly sip-trunks delete <trunk_id>
~~~

Every subcommand requires an ADK project, which supplies the account and canonical API region. ADK finds the project by checking the current working directory, or `--path` when supplied, then its parents. Commands therefore work from project subdirectories. If no project is found, use `--path /path/to/project`.

Project lookup is separate from YAML discovery: after finding the project, `manage` checks only that project's root and its immediate parent for `sip-trunks.yaml`. `--file` explicitly selects the YAML file; it does not select the project.

## `poly sip-trunks list`

List the account's SIP trunks, including their default routes and outbound SIP addresses, in a summary table, or export their configuration to a reusable YAML file.

Examples:

~~~bash
poly sip-trunks list
poly sip-trunks list --output
poly sip-trunks list --output ../sip-trunks.yaml  # shared export, run from project root
poly sip-trunks list --output export.yaml
poly sip-trunks list --output --force
poly sip-trunks list --path /path/to/project --json
~~~

The export includes trunk IDs, hostnames, CIDRs, readable authentication state (including the digest realm), default routes, outbound settings, and all extension bindings. Every exported trunk includes `default_route` and `outbound`, each set to `null` when absent from the API response. Creation and update timestamps are omitted. Export the current configuration, edit the desired settings, then pass the file back to `manage` to apply them. An outbound mapping describes the complete desired outbound configuration. SIP passwords and tokens are never returned by the API and therefore cannot appear in the export.

The export uses a top-level list. A SIP trunk can serve multiple projects in the same account and region, so the export includes all its extension routes, including routes to other projects. `manage` treats an `extensions` list as complete: filtering it to the current project's routes would schedule the other projects' bindings for deletion.

When `--output` is passed without a filename, the export goes to `sip-trunks.yaml` in the project root, even when run from a project subdirectory. An explicit output filename is relative to the current working directory. Overwriting an existing file requires `--force`, including with `--json`.

| Flag | Description |
|---|---|
| `--path PATH` | Starting directory for project lookup. Defaults to the current working directory. |
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
      "default_route": {
        "agent_id": "fallback-agent",
        "client_env": "live",
        "variant_id": ""
      },
      "outbound": {
        "sip_addresses": ["sip:sbc.example.com:5060"],
        "default_caller_id": "+442079460000"
      },
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

Create or update SIP trunks, default routes, outbound settings, and extension bindings from a YAML file for one account and region.

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
  default_route:
    agent_id: fallback-agent
    client_env: live
  outbound:
    sip_addresses:
      - sip:sbc.example.com:5060
    default_caller_id: "+442079460000"
  inbound_auth:
    type: digest
    username: carrier-user
    realm: sbc.sip.uk.poly.ai
  extensions:
    - extension: "1000"
      agent_id: my-project
      client_env: live
~~~

After finding the project, `manage` checks for `sip-trunks.yaml` in that project's root, then its immediate parent, and stops there. This file search is the same when running from a project subdirectory. `--file` selects a YAML file relative to the current working directory; it does not select the project or change its account or region.

Use separate YAML files for different accounts or regions, selecting the appropriate file with `--file` when needed.

Every trunk mapping must explicitly include a top-level `default_route` key. A missing or invalid value is rejected before any API calls. Set it to a mapping with required `agent_id` and `client_env` fields, as above. The environment must be `sandbox`, `pre-release`, or `live`. An optional `variant_id` selects a variant; omitting it uses the agent's default variant.

An extension always takes precedence over the default route. Calls to numbers without an extension go to the default route; without one, those calls are rejected. To disable the route, declare:

~~~yaml
default_route: null
~~~

For a new trunk, `null` creates it without a default route. For an existing trunk, it removes the current default route; if the trunk already has no default route, it makes no change.

Every trunk mapping must also explicitly include a top-level `outbound` key. A missing or invalid value is rejected before any API calls. To enable outbound calling, use a mapping with:

- `sip_addresses`: a required list of 1–4 `sip:` or `sips:` server URIs, each at most 255 characters. A URI may include a port and transport parameter, but must not contain a user part such as `user@`. Address order does not affect the configuration.
- `default_caller_id`: an optional string of at most 128 characters. Omitting it, or setting it to an empty string, clears any existing default caller ID.

The mapping describes the complete desired outbound configuration. To disable outbound calling and clear both the destinations and default caller ID, declare:

~~~yaml
outbound: null
~~~

For a new trunk, `null` creates it without outbound configuration. For an existing trunk, it removes that configuration; if outbound is already absent, it makes no change. An empty mapping or empty `sip_addresses` list is invalid in YAML; use `outbound: null` to disable it.

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
| `--path PATH` | Starting directory for project lookup. Defaults to the current working directory. |
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

Display a detailed trunk table, including its default route, outbound SIP addresses, and default caller ID, followed by its extension bindings.

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
| `--path PATH` | Starting directory for project lookup. Defaults to the current working directory. |

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
    },
    "default_route": {
      "agent": {
        "agent_id": "fallback-agent",
        "client_env": "live",
        "variant_id": ""
      }
    }
  },
  "outbound": {
    "sip_addresses": ["sip:sbc.example.com:5060"],
    "default_caller_id": "+442079460000"
  },
  "created_at": "2026-08-12T12:00:00Z",
  "updated_at": "2026-08-12T12:01:00Z"
}
~~~

JSON mode returns the trunk API response directly. `inbound.default_route` and `outbound` are omitted when their respective settings are absent. The response does not add the separately fetched extension bindings shown in the table output; use `list --json` for configuration that includes extensions and explicit `null` values for disabled default routes and outbound settings.

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
| `--path PATH` | Starting directory for project lookup. Defaults to the current working directory. |
| `-f`, `--force` | Delete without prompting for confirmation. |

`--json` output shape:

~~~json
{
  "success": true,
  "trunk_id": "tr-example"
}
~~~
