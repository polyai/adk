# Safety Filters

## Overview

Safety filters automatically block harmful content and prevent unsafe agent responses in real-time to protect both callers and your brand.
They run on both user input and AI output to block risky content before it affects the conversation.

In Agent Studio, content filtering can be set across four categories (violence, hate, sexual, self-harm) at both the project level and per-channel (voice/chat). Each category can be independently enabled and tuned to a sensitivity level.

## File structure
```
agent_settings/
└── safety_filters.yaml       # Project-level (general) safety filters
voice/
└── safety_filters.yaml       # Voice channel overrides
chat/
└── safety_filters.yaml       # Chat channel overrides
```

All three files share the same schema. Channel-level files override the project-level defaults for that channel.

## Fields

- **enabled**: `true` or `false` — whether safety filtering is active.
- **categories**: A map of the four content filter categories. Each category has:
  - **enabled**: `true` or `false` — whether this category is active.
  - **level**: Sensitivity level. One of `lenient`, `medium`, `strict`.

### Categories

| Category | Description |
|----------|-------------|
| `violence` | Filters violent or graphic content |
| `hate` | Filters hateful or discriminatory content |
| `sexual` | Filters sexually explicit content |
| `self_harm` | Filters self-harm related content |

## Example

General Settings are globally enabled with individual toggles per category

```yaml
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
```

Per-Channel Settings include a global enabled toggle:

```yaml
enabled: true
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
```

## Validation rules

- All four categories (`violence`, `hate`, `sexual`, `self_harm`) must be present.
- Each category must have both `enabled` and `level` set.
- `level` must be one of: `lenient`, `medium`, `strict`.

## Best practices

If setting safety filters across multiple channels, make the settings consistent for each - or vary depending on unique use cases/ risk profile for each.

