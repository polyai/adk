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
