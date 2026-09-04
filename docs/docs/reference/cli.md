---
title: CLI reference
description: Index of every command provided by the PolyAI ADK CLI, with the flags shared across all of them.
---

# CLI reference

<p class="lead">
The PolyAI ADK is accessed through the <code>poly</code> command.
Use the CLI help output as the first source of truth.
</p>

## Start with help

To see all available commands and options:

~~~bash
poly --help
~~~

Commands are listed under section headers so related ones stay together:

| Section | Commands |
|---|---|
| Getting started | `init`, `start`, `login`, `studio`, `project` |
| Project sync | `pull`, `push`, `status`, `revert`, `format`, `validate`, `diff`, `review`, `branch`, `test`, `rtc`, `chat` |
| Builder API | `deployments`, `conversations`, `audio-cache`, `functions` |
| Other | `template`, `docs`, `completion` |

Each command also supports its own help output. For example:

~~~bash
poly push --help
~~~

!!! tip "Use help output as the source of truth"

    The installed CLI is the fastest way to confirm the commands and flags available in your local environment.

## Commands

### Setting up

| Command | Purpose |
|---|---|
| [`poly login`](./cli/login.md) | Sign in to, or sign up for, an Agent Studio account |
| [`poly start`](./cli/start.md) | Create an account and a project in one step |
| [`poly init`](./cli/init.md) | Connect a local folder to an existing project |
| [`poly project`](./cli/project.md) | Create and manage Agent Studio projects |
| [`poly template`](./cli/template.md) | Browse and load example project templates |
| [`poly completion`](./cli/completion.md) | Output a shell completion script |

### Editing and syncing

| Command | Purpose |
|---|---|
| [`poly pull`](./cli/pull.md) | Pull remote configuration into the local project |
| [`poly push`](./cli/push.md) | Push local changes to Agent Studio |
| [`poly status`](./cli/status.md) | List changed files |
| [`poly diff`](./cli/diff.md) | Show local changes in detail |
| [`poly revert`](./cli/revert.md) | Discard local changes |
| [`poly format`](./cli/format.md) | Format resource files |
| [`poly validate`](./cli/validate.md) | Validate the project locally |

### Branches and review

| Command | Purpose |
|---|---|
| [`poly branch`](./cli/branch.md) | Create, switch, inspect, and merge branches |
| [`poly review`](./cli/review.md) | Publish a diff for review |

### Testing and inspection

| Command | Purpose |
|---|---|
| [`poly chat`](./cli/chat.md) | Talk to the agent interactively |
| [`poly test`](./cli/test.md) | Run and inspect simulated conversation tests |
| [`poly conversations`](./cli/conversations.md) | List and inspect real conversations |
| [`poly docs`](./cli/docs.md) | Output resource documentation |

### Deployment and configuration

| Command | Purpose |
|---|---|
| [`poly deployments`](./cli/deployments.md) | List, promote, and roll back deployments |
| [`poly rtc`](./cli/rtc.md) | Manage per-environment Real-Time Configuration |
| [`poly audio-cache`](./cli/audio-cache.md) | Inspect and replace cached TTS audio |
| [`poly functions`](./cli/functions.md) | Run and validate Functions via the REST API |
| [`poly studio`](./cli/studio.md) | Open the project in the Agent Studio web app |

## Shared flags

Most commands accept the same four flags:

| Flag | Description |
|---|---|
| `--path PATH` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout, for scripting. See below. |
| `--verbose` | Show full error tracebacks. |
| `--debug` | Display debug logs. |

!!! tip "Run commands from the project folder"

    ADK commands are expected to be run from within your local project directory. If needed, use `--path` to point to a project explicitly.

### `poly sip-trunks`

Manage account-level SIP trunks and their extension-to-agent routes through the SIP
Trunking API. By default, the command reads the account and region from the current ADK
project or from project metadata immediately below the account directory. To run it
without project metadata, pass `--account-id` and `--region` (`eu`, `uk`, or `us`).
Authentication uses the same `POLY_ADK_KEY` credentials as other ADK API commands.

The preferred workflow uses an account-level `sip-trunks.yaml`. Given a project at
`pod-point-uk/charging-support`, place the file at `pod-point-uk/sip-trunks.yaml`:

~~~yaml
- id: tr-ev3vx4iqcbhaeilk2jw9qp8n
  name: Primary carrier
  sip_cidr:
    - 203.0.113.0/24
  rtp_cidr:
    - 198.51.100.0/24
  encrypted: true
  hostname: tr-ev3vx4iqcbhaeilk2jw9qp8n.sbc.sip.uk.poly.ai
  inbound_auth:
    type: digest
    username: carrier-user
    realm: sbc.sip.uk.poly.ai
  extensions:
    - extension: "1000"
      agent_id: charging-support
      client_env: live
~~~

From a project directory, `manage` searches parent directories for the nearest
`sip-trunks.yaml`:

~~~bash
poly sip-trunks manage
poly sip-trunks manage --yes
poly sip-trunks manage --file ../sip-trunks.yaml
poly sip-trunks manage --rotate-auth tr-ev3vx4iqcbhaeilk2jw9qp8n
poly sip-trunks manage --json
~~~

`manage` first validates the complete file and calculates a diff without writing or
prompting for credentials. It displays the planned trunk, extension, credential-rotation,
and local metadata changes, then asks whether to continue. After confirmation it creates
missing trunks and extensions and patches changed ones. Use `--yes` to skip confirmation;
machine-readable `--json` runs require `--yes` when changes exist. It reports only created
or updated trunks, including their generated IDs and hostnames. If the YAML already
matches the backend, it prints `Nothing changed.` After reconciling a trunk, `manage` writes
the returned `id`, `hostname`, and digest `realm` back into the YAML using an atomic,
formatting-preserving update. These generated fields are informational and are not sent in
create or update requests. Creation and update timestamps are intentionally omitted. The
older mapping format with a `sip_trunks:` wrapper remains readable for migration, but new
exports use the top-level list.
Removing a trunk entry from YAML does **not** delete the live trunk; trunk deletion remains
an explicit command. An `extensions` list is authoritative, however: removing an extension
entry schedules its live binding for deletion, which is shown in the `manage` diff and only
applied after confirmation. Use `extensions: []` to remove every extension from a trunk.
Omit the `extensions` key entirely to leave its extension bindings unmanaged.

Export all existing configuration before making changes:

~~~bash
poly sip-trunks list                         # summary table
poly sip-trunks list --output                # account-level sip-trunks.yaml
poly sip-trunks list --output export.yaml
poly sip-trunks list --output --force        # explicitly replace an existing file
~~~

The export includes trunk IDs, hostnames, CIDRs, readable authentication state (including
the digest realm), and all extension bindings. Creation and update timestamps are omitted.
The file can be passed directly back to `manage`. SIP passwords and tokens are never
returned by the API and therefore cannot appear in the export.

The export does not store a region. All projects in an account belong to the same region,
so ADK infers it from their `project.yaml` metadata. If projects for the account disagree,
the command stops with an error. Use `--region` when no project metadata is available.

Without `--output`, `list` displays a summary table. `get` displays a detailed trunk table
followed by its extension bindings. Pass `--json` to either command for machine-readable
output.

SIP passwords and tokens must not be stored in YAML. `manage` prompts securely when a
secret is required: when creating authenticated trunks, changing authentication type or
digest username, and explicitly rotating credentials. An ordinary update to a trunk whose
authentication is unchanged never prompts for or resends its credential.

Digest authentication declares only its non-secret state:

~~~yaml
inbound_auth:
  type: digest
  username: carrier-user
~~~

Only one inbound authentication mode can be configured:

~~~yaml
# SIP token authentication
inbound_auth:
  type: token
~~~

Use `type: none` to explicitly disable the trunk's current inbound authentication.
Rotate an existing credential only through an explicit action:

~~~bash
poly sip-trunks manage --rotate-auth <trunk_id>
~~~

~~~bash
poly sip-trunks get <trunk_id>
poly sip-trunks delete <trunk_id>
poly sip-trunks delete <trunk_id> --yes
~~~

`delete` asks for confirmation and prints a human-readable success message by default.
Use `--yes` to skip confirmation. Machine-readable deletion with `--json` requires
`--yes`.

All leaf commands support `--json`, `--path`, `--account-id`, and `--region`.

## Machine-readable JSON output

All core subcommands accept a `--json` flag that switches stdout to a single JSON object. This is designed for scripting, CI pipelines, and any integration that needs stable, parseable output rather than human-readable console text.

~~~bash
poly status --json
poly push --json
poly pull --json
poly validate --json
poly diff --json
poly revert --json
poly branch list --json
poly branch create my-feature --json
poly branch switch my-feature --json
poly branch current --json
poly branch delete --json
poly branch delete my-feature --json
poly branch merge 'Merge message' --json
poly format --json
poly init --region us-1 --account_id 123 --project_id my_project --json
poly project create --region us-1 --account_id my-account --name my-project --json
poly chat --json -m 'Hello'
poly chat --json --input-file ./script.txt
poly deployments show abc123def --json
poly deployments list --json
poly deployments promote --from <id> --to pre-release --force --json
poly deployments rollback --to <id> --force --json
poly conversations list --json
poly conversations get <conversation_id> --json
poly conversations get-audio <conversation_id> --json
poly audio-cache list --json
poly audio-cache get-file <entry_id> --json
poly audio-cache update-file <entry_id> --file replacement.wav --json
poly audio-cache delete <entry_id> --json
poly audio-cache bulk-delete --ids id1,id2 --json
poly audio-cache synthesize <entry_id> --text "Hello" --json
poly functions execute <function_name> --args '{"x": 1}' --json
poly functions validate --json
~~~

### `--json` contract

When `--json` is used:

- stdout contains exactly one JSON object
- the process exits with code `0` on success and non-zero on failure
- human-readable console messages are suppressed
- error responses always include `{ "success": false, "error": "...", "traceback": "..." }`

The exact top-level keys vary by command — each command's page documents its own output shape.

!!! info "`--interactive` and `--json` cannot be used together"

    `poly branch merge --interactive` requires a terminal for its conflict-resolution prompts and is incompatible with `--json`.

!!! info "`--json` implies `--force` for deployments commands"

    When `--json` is used with `poly deployments promote` or `poly deployments rollback`, the confirmation prompt is automatically skipped (equivalent to passing `--force`).

### Advanced JSON-driven workflows

A few commands support extra flags for piping JSON between invocations instead of hitting the API each time:

| Flag | Commands | Description |
|---|---|---|
| `--from-projection <source>` | `pull`, `push`, `init`, `branch switch` | Supply a projection JSON directly (file path, inline string, or `-` for stdin) instead of fetching it from the API. Useful for offline workflows and integration testing. |
| `--output-json-projection` | `pull`, `init`, `branch switch` | Include the projection in the `--json` output, so it can be captured and fed into another command's `--from-projection`. |
| `--output-json-commands` | `push` | Add a `commands` array to the `--json` output, containing the serialized Agent Studio commands that were staged. Useful for dry-run review and integration testing. |

~~~bash
poly pull --from-projection - < projection.json
poly push --from-projection '{"topics": [...], ...}'
poly pull --json --output-json-projection | jq .projection > proj.json
poly push --json --dry-run --output-json-commands
~~~

## Related pages

- [Working locally](../development/working-locally.md) — the edit, push, and test loop these commands fit into
- [Resource reference](./resources.md) — the resources these commands operate on
