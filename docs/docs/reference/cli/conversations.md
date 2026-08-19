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
poly conversations list --json
~~~

The default table view shows conversation ID (rendered as a clickable Agent Studio link), start time, duration, caller number, channel, variant (when present), handoff status, and a short summary heading.

| Flag | Description |
|---|---|
| `--limit` | Max number of conversations to return. Defaults to `50`. |
| `--offset` | Number of conversations to skip. Defaults to `0`. |

`--json` output shape:

~~~json
{
  "conversations": [{ "id": "...", "startedAt": "...", "...": "..." }],
  "count": 0,
  "limit": 50,
  "offset": 0
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
