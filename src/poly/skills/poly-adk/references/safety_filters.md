# Safety Filters

## Overview
Automatically blocks harmful content and unsafe responses in real time, on both user input and AI output, across
four categories (violence, hate, sexual, self-harm) — settable at project level and per channel.

## File structure
```
agent_settings/
└── safety_filters.yaml       # Project-level (general) defaults
voice/
└── safety_filters.yaml       # Voice channel overrides
chat/
└── safety_filters.yaml       # Chat channel overrides
```
All three share the same schema; channel-level files override project-level defaults for that channel.

## Fields
| Field | Notes |
|---|---|
| `enabled` | `true`/`false` — whether filtering is active |
| `categories` | Map of the four categories, each with `enabled` (bool) and `level` (`lenient`/`medium`/`strict`) |

### Categories
| Category | Description |
|---|---|
| `violence` | Violent or graphic content |
| `hate` | Hateful or discriminatory content |
| `sexual` | Sexually explicit content |
| `self_harm` | Self-harm related content |

## Example — project-level (general)
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

## Example — per-channel (includes global toggle)
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

## Validation
- All four categories must be present, each with both `enabled` and `level` set.
- `level` must be `lenient`, `medium`, or `strict`.

## Best practices
Keep settings consistent across channels unless a channel's risk profile genuinely differs.
