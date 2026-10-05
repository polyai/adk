---
title: poly transcripts
description: Reference for the `poly transcripts` command.
---

# `poly transcripts`

Search what was said across the project's conversations, or print one conversation's transcript turn by turn, through the Data API. `poly transcripts` requires a subcommand.

Examples:

~~~bash
poly transcripts search "cancel my booking"
poly transcripts get <conversation_id>
~~~

Transcripts are PII. Both subcommands need an API key with PII read permission on the project; without it the Data API answers `403` and the CLI says which permission is missing. The loaded project's ID is always sent, which Personal Access Tokens require on search.

## `poly transcripts search`

Full-text search over transcript turns. Each match is printed with the turns around it, the phrase highlighted, under the conversation ID (an Agent Studio link) and the time of the first match.

Examples:

~~~bash
poly transcripts search "cancel my booking"
poly transcripts search "refund" --from 2026-09-01 --to 2026-09-30 --context 0
poly transcripts search "speak to a human" --context 2 --limit 5
poly transcripts search "refund" --english --json
~~~

| Argument | Description |
|---|---|
| `query` | **Required.** Phrase to search for, 3 to 300 characters. |

| Flag | Description |
|---|---|
| `--from` | Inclusive window start on conversation start time, `YYYY-MM-DD` or an ISO 8601 datetime. |
| `--to` | Exclusive window end. A bare date includes the whole of that day. |
| `--context` | Turns of context to show on each side of a match, `0` to `3`. Defaults to `1`. |
| `--english` | Show the English translation of non-English turns where the platform has one. |
| `--limit`, `--offset` | Conversations per page (1 to 100, default 20) and conversations to skip (up to 1000). |

`--json` output shape:

~~~json
{
  "results": [
    {
      "conversation_id": "...",
      "project_id": "...",
      "matched_turns": [
        {
          "turn_index": 2,
          "user_input": "...",
          "user_input_datetime": "2026-09-30T10:00:05Z",
          "english_user_input": null,
          "agent_response": "...",
          "agent_response_datetime": "2026-09-30T10:00:07Z",
          "english_agent_response": null,
          "context": { "before": [], "after": [] }
        }
      ]
    }
  ],
  "total": 0,
  "limit": 20,
  "offset": 0
}
~~~

## `poly transcripts get`

Print every turn of one conversation with speaker and timestamp. For call metadata — channel, handoff, tags, summary — use [`poly conversations get`](./conversations.md#poly-conversations-get) instead.

Examples:

~~~bash
poly transcripts get <conversation_id>
poly transcripts get <conversation_id> --english
poly transcripts get <conversation_id> --json
~~~

| Argument | Description |
|---|---|
| `conversation_id` | **Required.** The conversation ID, for example from `poly transcripts search` or `poly conversations search`. |

| Flag | Description |
|---|---|
| `--english` | Show the English translation of non-English turns where the platform has one. |

`--json` output shape:

~~~json
{
  "conversation_id": "...",
  "project_id": "...",
  "turns": [
    {
      "turn_index": 0,
      "user_input": "...",
      "user_input_datetime": "2026-09-30T10:00:00Z",
      "agent_response": "...",
      "agent_response_datetime": "2026-09-30T10:00:02Z"
    }
  ],
  "total_turns": 0
}
~~~

## Related pages

- [Observability](../../development/observability.md) — inspecting real calls as part of the wider instrument-and-review workflow
