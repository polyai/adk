---
title: poly docs
description: Reference for the `poly docs` command.
---

# `poly docs`

Output resource documentation for one or more topics, or write it to a file.

Examples:

~~~bash
poly docs flows functions topics
poly docs context
poly docs --all
poly docs --all --output rules.md
~~~

With no arguments, `poly docs` outputs the general project overview. Use `--output` to write the documentation to a local file instead of stdout — this is useful when working with AI coding tools, since you can pass the output file as context to give the agent accurate knowledge of ADK resource types and conventions.

| Argument | Description |
|---|---|
| `documents` | Zero or more resource names to output documentation for (see table below). |

| Flag | Description |
|---|---|
| `--all` | Output documentation for the project overview and all resource types. |
| `-o`, `--output`, `--write` | Write output to a file instead of stdout. |

Available resource names:

| Name | Description |
|---|---|
| `agent_settings` | Personality, role, rules |
| `api_integrations` | External HTTP API definitions |
| `chat_settings` | Chat greeting, style prompt |
| `context` | Context files for agent knowledge |
| `entities` | Structured data collection |
| `experimental_config` | Feature flags |
| `flows` | Multistep processes with steps, functions, conditions |
| `handoffs` | SIP call transfers |
| `functions` | Global and flow functions, decorators, state, metrics |
| `languages` | Default and additional language configuration |
| `tests` | Simulated conversation test cases |
| `safety_filters` | Content moderation settings |
| `sms` | Text message templates |
| `speech_recognition` | ASR settings, keyphrase boosting, transcript corrections |
| `response_control` | Pronunciations, phrase filters |
| `topics` | Knowledge base for RAG |
| `translations` | Localized text strings per language |
| `variants` | Per-variant configuration |
| `voice_settings` | Voice greeting, disclaimer, style prompt |
| `variables` | State variables referenced in code |
