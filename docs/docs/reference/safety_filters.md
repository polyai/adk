---
title: Safety filters
description: Configure project-level and per-channel content safety filtering for PolyAI agents.
---

# Safety filters

<p class="lead">
Safety filters block harmful content from entering or leaving the conversation in real time.
</p>

They run on user input and on agent output, scoring each turn against four content categories and blocking it before it affects the conversation.

Filters can be configured at the project level and overridden per channel (voice and chat). Each category is enabled independently and tuned to a sensitivity level.

## Location

Safety filters are defined in up to three optional files:

~~~text
agent_settings/
└── safety_filters.yaml       # Project-level (general) defaults
voice/
└── safety_filters.yaml       # Voice channel override
chat/
└── safety_filters.yaml       # Chat channel override
~~~

A channel-level file will override the project-level defaults for that channel. If no channel file exists, the channel inherits the project-level configuration.

## What safety filters control

<div class="grid cards" markdown>

-   **Project-level filters**

    ---

    Defaults applied to every channel when no channel-specific override is set.

-   **Channel-level overrides**

    ---

    Per-channel tuning for voice or chat, including a global enable toggle.

-   **Categories**

    ---

    Violence, hate, sexual, and self-harm content.

-   **Sensitivity levels**

    ---

    Choose how aggressively each category filters: `lenient`, `medium`, or `strict`.

</div>

## Categories

All four categories must be configured. Each category has its own `enabled` flag and `level`.

| Category | Description |
|---|---|
| `violence` | Filters violent or graphic content |
| `hate` | Filters hateful or discriminatory content |
| `sexual` | Filters sexually explicit content |
| `self_harm` | Filters self-harm related content |

## Fields

| Field | Where | Description |
|---|---|---|
| `enabled` | Channel files only | `true` or `false` — global toggle for the channel. Omit at project level; the project filter is active whenever any category is enabled. |
| `categories` | All files | Map of the four categories. Required. |
| `categories.<name>.enabled` | All files | `true` or `false` — whether this category is active. |
| `categories.<name>.level` | All files | Sensitivity level. One of `lenient`, `medium`, `strict`. |

### Sensitivity levels

| Level | Behavior |
|---|---|
| `lenient` | Blocks only the most severe content. |
| `medium` | Balanced filtering. |
| `strict` | Blocks borderline content. |

## Project-level example

Project-level filters omit the global `enabled` key — the filter is active whenever at least one category is enabled.

~~~yaml
categories:
  violence:
    enabled: true
    level: medium
  hate:
    enabled: true
    level: medium
  sexual:
    enabled: true
    level: medium
  self_harm:
    enabled: true
    level: medium
~~~

## Channel-level example

Channel files include a top-level `enabled` flag that turns filtering on or off for the entire channel.

~~~yaml
enabled: true
categories:
  violence:
    enabled: true
    level: strict
  hate:
    enabled: true
    level: medium
  sexual:
    enabled: true
    level: medium
  self_harm:
    enabled: true
    level: strict
~~~

## Validation rules

`poly push` rejects safety filter files that don't satisfy these rules:

- All four categories (`violence`, `hate`, `sexual`, `self_harm`) must be present.
- Each category must set both `enabled` (boolean) and `level`.
- `level` must be one of `lenient`, `medium`, or `strict`.
- Channel files must include the top-level `enabled` flag as a boolean.
- Unrecognized category keys cause a validation error rather than being silently ignored.

## Best practices

- Keep settings consistent across channels unless a channel has a distinct risk profile (for example, a voice line that handles vulnerable callers may warrant `strict` on `self_harm`).
- Start at `medium` and adjust based on observed false positives and missed content.
- Review filter outcomes periodically — the right level depends on caller demographics and use case, not just the deployment.
- Treat the channel files as overrides, not duplicates: only commit a channel file when it actually differs from the project default.

## On the Agent Studio platform

The same settings can be configured in the Agent Studio UI. The platform docs cover the UI workflow and category descriptions in more depth:

<div class="grid cards" markdown>

-   **Project-level (General)**

    ---

    Defaults applied across every channel.
    [Open General settings on docs.poly.ai](https://docs.poly.ai/settings/introduction){ target="_blank" rel="noopener" }

-   **Voice channel**

    ---

    Per-channel overrides for voice.
    [Open Voice configuration on docs.poly.ai](https://docs.poly.ai/voice/voice-configuration#safety-filters){ target="_blank" rel="noopener" }

-   **Chat channel**

    ---

    Per-channel overrides for chat.
    [Open Chat configuration on docs.poly.ai](https://docs.poly.ai/webchat/chat-configuration#safety-filters){ target="_blank" rel="noopener" }

</div>

## Related references

<div class="grid cards" markdown>

-   **Agent settings**

    ---

    Configure personality, role, and rules alongside project-level safety filters.
    [Open agent settings](./agent_settings.md)

-   **Voice settings**

    ---

    Configure voice-channel greetings, disclaimers, and safety filter overrides.
    [Open voice settings](./voice_settings.md)

-   **Chat settings**

    ---

    Configure chat-channel greetings, style, and safety filter overrides.
    [Open chat settings](./chat_settings.md)

</div>
