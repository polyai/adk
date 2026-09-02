---
title: poly conversations
description: Reference for the `poly conversations` command.
---

# `poly conversations`

List and inspect conversations for the project using the public Conversations API. `poly conversations` requires a subcommand:

Examples:

~~~bash
poly conversations list
poly conversations get <conversation_id>
poly conversations get-audio <conversation_id> -o recording.wav
~~~

## `poly conversations list`

List conversations for the project.

Examples:

~~~bash
poly conversations list
poly conversations list --limit 20 --offset 10
poly conversations list --cursor <cursor>
poly conversations list --channel voice --channel chat
poly conversations list --in-progress
poly conversations list --json
~~~

The default table view shows conversation ID (rendered as a clickable Agent Studio link), start time, duration, caller number, channel, variant (when present), and handoff status.

In `us-1`, `uk-1`, and `euw-1`, this command uses the v3 conversations API, which doesn't return a
summary, tags, PolyScore, note, deployment ID, direction, or language for list results — fetch
those per-conversation with [`poly conversations get`](#poly-conversations-get) instead. Other
regions (`dev`, `staging`, `studio`) still use the deprecated v1 endpoint until it's rolled out
there, so their list output currently retains those fields.

| Flag | Description |
|---|---|
| `--limit` | Max number of conversations to return. Defaults to `50`. |
| `--offset` | Number of conversations to skip. Defaults to `0`. Prefer `--cursor` where available. |
| `--cursor` | Pagination cursor from a previous response's `cursor` field. `us-1`/`uk-1`/`euw-1` only. |
| `--channel` | Filter by channel (e.g. `voice`, `chat`). Repeatable. `us-1`/`uk-1`/`euw-1` only. |
| `--in-progress` / `--no-in-progress` | Filter to only in-progress, or only finished, conversations. `us-1`/`uk-1`/`euw-1` only. |

`--json` passes through the raw API response, so its shape follows the same regional split as the
table above. In `us-1`/`uk-1`/`euw-1` (v3):

~~~json
{
  "conversations": [{ "id": "...", "started_at": "...", "...": "..." }],
  "next_offset": null,
  "cursor": null
}
~~~

In `dev`/`staging`/`studio` (v1, unchanged from before this migration):

~~~json
{
  "conversations": [{ "conversationId": "...", "startedAt": "...", "...": "..." }],
  "next_offset": null
}
~~~

## `poly conversations get`

Get detailed information for a specific conversation, including all turns.

Examples:

~~~bash
poly conversations get <conversation_id>
poly conversations get <conversation_id> --json
~~~

The default output shows conversation metadata (channel, language, duration, timestamps, handoff, tags, PolyScore, summary, note) followed by a turn-by-turn transcript.

| Argument | Description |
|---|---|
| `conversation_id` | The conversation ID to look up. Required. |

`--json` output shape:

~~~json
{
  "id": "...",
  "channel": "...",
  "turns": [],
  "...": "..."
}
~~~

## `poly conversations get-audio`

Download the audio recording for a conversation as a WAV file.

Examples:

~~~bash
poly conversations get-audio <conversation_id>
poly conversations get-audio <conversation_id> --direction user
poly conversations get-audio <conversation_id> --redacted -o redacted.wav
poly conversations get-audio <conversation_id> --json
~~~

| Argument | Description |
|---|---|
| `conversation_id` | The conversation ID. Required. |

| Flag | Description |
|---|---|
| `--direction` | Audio track to download. Choices: `combined`, `user`, `agent`. Defaults to `combined`. |
| `--redacted` | Download the redacted version of the audio. |
| `-o`, `--output` | Output file path. Defaults to `<conversation_id>.wav`. |

`--json` output shape:

~~~json
{
  "success": true,
  "conversation_id": "...",
  "direction": "combined",
  "redacted": false,
  "output_path": "...",
  "size_bytes": 0
}
~~~

## Related pages

- [Observability](../../development/observability.md) — inspecting real calls as part of the wider instrument-and-review workflow
