---
title: Resource reference
description: Index of every resource type the PolyAI ADK manages, with the file it lives in and what it configures.
---

# Resource reference

An ADK project is a set of **resources** — the YAML, text, and Python files that define what an agent knows and how it behaves. Each page below documents one resource type: its fields, its valid values, and worked examples.

For how the resource types relate to each other and which one to reach for, see [resource architecture](../development/resource-architecture.md). For the `{{prefix:name}}` syntax used to reference one resource from another, see [resource references](../development/resource-architecture.md#resource-references).

Every resource here follows the same sync process, including [permission-gated visibility](../development/resource-architecture.md#syncing-and-permissions) — a resource you can't view in Agent Studio won't appear in your local project.

## Agent behavior

| Resource | Configures | File |
|---|---|---|
| [Agent settings](./resources/agent_settings.md) | Persona and global rules | `agent_settings/` |
| [Guardrails](./resources/guardrails.md) | Platform and custom checks that constrain agent behavior | `agent_settings/guardrails.yaml` |
| [Languages](./resources/languages.md) | Supported languages for a multilingual agent | `agent_settings/languages.yaml` |
| [Experimental config](./resources/experimental_config.md) | Opt-in experimental platform features | `agent_settings/experimental_config.json` |

## Knowledge and conversation

| Resource | Configures | File |
|---|---|---|
| [Topics](./resources/topics.md) | Knowledge base entries — facts and per-subject actions | `topics/` |
| [Flows](./resources/flows.md) | Multi-step guided conversations, steps, and transitions | `flows/` |
| [API integrations](./resources/api_integrations.md) | External HTTP APIs callable from functions and flows | `config/api_integrations.yaml` |
| [Entities](./resources/entities.md) | Structured values collected from the caller | `config/entities.yaml` |
| [Functions](./resources/functions.md) | Python for deterministic logic and lifecycle hooks | `functions/` |

## Named values and destinations

| Resource | Configures | File |
|---|---|---|
| [Handoffs](./resources/handoffs.md) | Escalation destinations | `config/handoffs.yaml` |
| [SMS templates](./resources/sms.md) | Reusable outbound message content | `config/sms_templates.yaml` |
| [Variants](./resources/variants.md) | Per-site or per-location attribute values | `config/variant_attributes.yaml` |
| [Variables](./resources/variables.md) | Conversation state set in code and read in prompts | Set via `conv.state` |
| [Translations](./resources/translations.md) | Localized strings | `config/translations.yaml` |

## Channel and voice

| Resource | Configures | File |
|---|---|---|
| [Voice settings](./resources/voice_settings.md) | Greeting, style prompt, and disclaimers for voice | `voice/configuration.yaml` |
| [Chat settings](./resources/chat_settings.md) | Greeting and style prompt for webchat | `chat/configuration.yaml` |
| [Speech recognition](./resources/speech_recognition.md) | ASR behavior, keyphrase boosting, transcript corrections | `voice/speech_recognition/` |
| [Response control](./resources/response_control.md) | Pronunciations and phrase filtering | `voice/response_control/` |
| [Safety filters](./resources/safety_filters.md) | Content filtering, per project and per channel | `safety_filters.yaml` |

## Non-runtime resources

These are synced like any other resource but never affect what the agent does on a call.

| Resource | Purpose | File |
|---|---|---|
| [Tests](./resources/tests.md) | Simulated conversation tests | `test_suite/` |
| [Context documents](./resources/context.md) | Background knowledge for Studio Assistant | `context/` |

## Related references

- [CLI reference](./cli.md) — every `poly` command and its flags
- [`poly branch merge`](./cli/branch.md#poly-branch-merge) — conflict resolution for merging a branch
