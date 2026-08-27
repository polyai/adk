---
title: poly chat
description: Reference for the `poly chat` command.
---

# `poly chat`

Start an interactive chat session with your agent, or run scripted/automated conversations.

Examples:

~~~bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --sip-header X-Customer-ID=12345
poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB
poly chat --metadata
poly chat --lang fr-FR
poly chat --input-lang en-US --output-lang fr-FR
~~~

#### Non-interactive (scripted) mode

Supply messages directly on the command line or from a file to run `poly chat` without a human at the terminal. This is useful for automated testing pipelines and CI scripts.

**Inline messages** — use `-m`/`--message` (repeatable):

~~~bash
poly chat -m 'Hello' -m 'What can you help with?'
~~~

**File-based input** — use `--input-file`:

~~~bash
poly chat --input-file ./script.txt
echo -e 'Hello\nGoodbye' | poly chat --input-file -
~~~

Each line of the file is sent as a separate message. Use `-` to read from stdin.

If the file path does not exist, `poly chat` exits with an error.

#### Resuming an existing conversation

Use `--conversation-id` (or `--conv-id`) to resume an existing conversation by its ID instead of creating a new session:

~~~bash
poly chat --conv-id <conversation_id>
poly chat --conv-id <conversation_id> -m 'Follow-up message'
~~~

#### Pushing before chatting

Use `--push` to push the local project to Agent Studio before starting the chat session. This ensures local changes are live before testing without requiring a separate `poly push` step:

~~~bash
poly chat --push
poly chat --push -m 'Hello'
~~~

If the push fails, the command exits without starting the chat session.

#### Language flags

Use language flags to specify the expected input and output language when chatting against multilingual agents. If not specified, the project default is used.

| Flag | Description |
|---|---|
| `--lang` | Sets both input and output language (e.g. `en-US`, `fr-FR`). |
| `--input-lang` | Sets the input language (ASR) only. Overrides `--lang` for input. |
| `--output-lang` | Sets the output language (TTS) only. Overrides `--lang` for output. |

`--input-lang` and `--output-lang` take precedence over `--lang` when both are supplied.

#### Simulating SIP headers

Use `--sip-header NAME=VALUE` to simulate a SIP header when starting a conversation.

Single header:

~~~bash
poly chat --sip-header X-Customer-ID=12345
~~~

Multiple headers are supported by repeating the flag:

~~~bash
poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB
~~~

The values are exposed to project functions through `conv.sip_headers`. This is for
testing agent behaviour only; it does not create a SIP call or reproduce carrier-level
SIP behaviour. SIP headers cannot be changed when resuming an existing conversation.

#### `poly chat` flags summary

| Flag | Description |
|---|---|
| `--push` | Push the project before starting the chat session. |
| `-m`, `--message MSG` | Send a message non-interactively (repeatable). |
| `--input-file FILE` | Read messages line-by-line from a file (`-` for stdin). |
| `--conversation-id`, `--conv-id` | Resume an existing conversation by ID. |
| `--environment`, `-e` | Target environment. Choices: `branch`, `sandbox`, `pre-release`, `live`. Defaults to `branch`. `branch` chats against the last **pushed** state of your current branch (not local uncommitted changes); on main it falls back to `sandbox`. Use `--push` to push local changes before chatting. |
| `--channel` | Channel to chat against. Choices: `voice`, `webchat`. Defaults to `voice`. |
| `--sip-header NAME=VALUE` | Simulate a SIP header at conversation start (repeatable). |
| `--lang` | Set both input and output language. |
| `--input-lang` | Set input language only. Overrides `--lang` for input. |
| `--output-lang` | Set output language only. Overrides `--lang` for output. |
| `--variant` | Name of the variant to use for the chat session. |
| `--functions` | Show function/tool calls made each turn. |
| `--flows` | Show the active flow and step each turn. |
| `--state` | Show per-turn state variable changes. |
| `--metadata` | Show all metadata (equivalent to `--functions --flows --state`). |

`--json` output shape — a `conversations` array, one entry per session (more than one if `/restart` was used in scripted input); each `turns` entry mirrors the enabled `--functions`/`--flows`/`--state` flags:

~~~json
{
  "conversations": [
    {
      "conversation_id": "...",
      "url": "https://...",
      "turns": [
        {
          "input": null,
          "response": "Hi, how can I help?",
          "conversation_ended": false
        },
        {
          "input": "Hello",
          "response": "...",
          "conversation_ended": false,
          "function_events": [{ "name": "...", "arguments": {} }],
          "flow": { "in_flow": "...", "in_step": "..." },
          "state_changes": [{ "added": {}, "updated": {}, "removed": [] }]
        }
      ]
    }
  ]
}
~~~

`function_events`, `flow`, and `state_changes` are only present on turns where `--functions`, `--flows`, or `--state` (or `--metadata`) produced data. If `--push` is used, a `push` key (`{ "success": true, "message": "..." }`) is added alongside `conversations`. On failure (e.g. session creation error, missing input file), the shape is `{ "success": false, "error": "..." }` instead.
