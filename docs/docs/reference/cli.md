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
