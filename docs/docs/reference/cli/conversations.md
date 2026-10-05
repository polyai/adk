---
title: poly conversations
description: Reference for the `poly conversations` command.
---

# `poly conversations`

List, search and inspect conversations for the project. `list`, `get` and `get-audio` use the Conversations API; `search` uses the Data API, which filters on metric values. `poly conversations` requires a subcommand:

Examples:

~~~bash
poly conversations list
poly conversations search --filter poly_score lt 3 --env live
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

## `poly conversations search`

Find conversations by metric values, channel, environment and start time. Each row carries the metric fields you ask for with `--field`, so this is also the way to pull Poly Score or a custom metric per conversation.

Examples:

~~~bash
poly conversations search --from 2026-09-01 --to 2026-09-30
poly conversations search --filter poly_score lt 3 --env live
poly conversations search --filter handoff eq true --field handoff_reason
poly conversations search --filter conversation_id in id1,id2 --field call_summary
poly conversations search --sort duration:desc --limit 5 --json
~~~

The table shows conversation ID (as an Agent Studio link), start time, duration, then one column per `--field`. Free-text metric fields such as `call_summary`, `email_subject` and the `poly_score_*_summary` reasoning are PII: without PII read permission on the API key the search still succeeds, but those columns come back empty and the CLI says why.

| Flag | Description |
|---|---|
| `--from` | Inclusive window start on conversation start time, `YYYY-MM-DD` or an ISO 8601 datetime. |
| `--to` | Exclusive window end. A bare date includes the whole of that day. |
| `--filter METRIC OP VALUE` | Only conversations where the condition holds. `METRIC` is a name from [`poly metrics available`](./metrics.md#poly-metrics-available), `conversation_id` (with `eq` or `in`, at most 100 IDs) or `CUSTOM_SCORE_<id>` for an AI Score. `OP` is `eq`, `gt`, `gte`, `lt`, `lte`, `in`, `ex`, `contains`, `not_contains`, `exists`; `in`/`ex` take a comma-separated list. Repeatable. |
| `--any` | Match conversations that satisfy any `--filter` instead of all. |
| `--channel` | Restrict to a channel: `VOICE-SIP`, `CHAT`, `WEBCHAT`, `SMS`, `RCS`. Repeatable. |
| `--env` | Restrict to an environment: `test`, `sandbox`, `pre-release` (Staging), `live`, `scenarios`. Repeatable. |
| `--field` | Metric field to show per conversation. Repeatable. Defaults to `poly_score`, `duration`, `channel`. |
| `--sort FIELD[:asc\|desc]` | Sort by `started_at`, `duration` or `conversation_id`. Defaults to `started_at:desc`. |
| `--limit`, `--offset` | Conversations per page (1 to 100, default 20) and conversations to skip (up to 1000). |

`--json` output shape:

~~~json
{
  "conversations": [
    {
      "conversation_id": "...",
      "project_id": "...",
      "started_at": "2026-09-30T10:00:00Z",
      "duration_seconds": 95,
      "metrics": { "poly_score": 4.5, "channel": "CHAT" }
    }
  ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
~~~

## `poly conversations get`

Get detailed information for a specific conversation, including all turns. For the transcript alone, with a timestamp on every turn, use [`poly transcripts get`](./transcripts.md#poly-transcripts-get).

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
