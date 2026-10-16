---
title: poly wren
description: Reference for the `poly wren` command.
---

# `poly wren`

Work on the project with Wren, Agent Studio's AI builder (also called Studio Assistant). `poly wren` requires a subcommand.

## `poly wren chat`

Chat with Wren about the project. Wren plans and makes changes remotely, on a branch, and the local project follows along: when Wren creates or switches to a branch, the local project tracks it, and when Wren applies changes, they're pulled into your local files.

Examples:

~~~bash
poly wren chat
poly wren chat -m 'Add a transfer flow for billing'
poly wren chat --json -m 'Add an FAQ topic about parking'
poly wren chat --session-id <session_id>
~~~

Without `-m`, `poly wren chat` starts an interactive session. Press Enter to send and Ctrl+J for a new line. Type `/usage` to see what the session has cost so far, and `/exit` to leave. When the session ends, the CLI prints its cost and the `--session-id` to resume it.

Wren works on the project's current branch. It never edits main: if you start on main, it creates a branch for its changes, and the local project switches to it. Wren reads the project's [context documents](../resources/context.md) for background.

When Wren needs a decision, the interactive session asks you:

- **Questions**: pick an option or type an answer.
- **Plans**: approve, give feedback, or cancel.
- **Configuration changes**: review the keys Wren wants to change and approve or reject the write. A change to live, or one that removes existing values, is called out before you answer.
- **Secrets and API credentials**: these can't be set from the CLI, so the request is declined and Wren notes it. Set them up in Agent Studio, then ask Wren to continue.

With `-m`, Wren answers its own questions where it can. If it still needs you, for example to approve a configuration change, run `poly wren chat` without `-m` to answer.

`poly wren chat` won't start while you have local changes, because Wren's changes would overwrite them. Push or revert them first, or pass `--force`.

| Flag | Description |
|---|---|
| `--message`, `-m` | Send one message instead of starting an interactive session. Required with `--json`. |
| `--session-id` | Continue an existing Wren session. |
| `--no-pull` | Don't pull Wren's changes into the local project. Use `poly pull` later to fetch them. |
| `--force` | Start even if there are local changes. Wren's changes overwrite them. |

`--json` output shape:

~~~json
{
  "success": true,
  "sessionId": "8f6c1e2a-...",
  "branch": {"id": "BRANCH-...", "action": "create", "name": "wren/parking-faq"},
  "messages": ["I've added a parking FAQ topic..."],
  "toolCalls": [{"toolName": "apply", "isError": false}],
  "changesApplied": true,
  "changes": {"modified": 0, "added": 1, "deleted": 0},
  "suspended": false,
  "report": {"title": "Parking FAQ added", "text": "## Summary\n..."},
  "pull": {"performed": true, "conflicts": []},
  "usage": {"totalSteps": 6, "costUsd": 0.1842},
  "pendingInput": null,
  "error": null
}
~~~

`branch` is null when Wren stayed on the current branch, and `pull` is null when nothing was pulled. `suspended` is true when Wren is still working remotely after the message returned; run `poly pull` later to fetch the rest. `pendingInput` names a decision Wren is waiting on that a single message can't answer.
