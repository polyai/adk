# Response Control

## Overview
Manages what the agent says before it reaches the user — TTS pronunciation fixes and phrase filtering — under
`voice/response_control/`:
```
voice/response_control/
├── pronunciations.yaml             # Optional - TTS pronunciation rules
└── phrase_filtering.yaml           # Optional - block/intercept phrases before TTS
```

## Pronunciations (`pronunciations.yaml`)
Regex-based TTS rules applied before speech synthesis. Order matters.
| Field | Notes |
|---|---|
| `regex` (required) | Pattern to match in the agent's output text |
| `replacement` (required) | What to replace with for TTS (can be `""`) |
| `case_sensitive` (bool) | Default `false` |
| `language_code` (optional) | Restrict to one language |
| `description` (optional) | What this rule does |

```yaml
pronunciations:
  - regex: "\\bDr\\."
    replacement: Doctor
    case_sensitive: true
  - regex: "\\bMr\\."
    replacement: Mister
    case_sensitive: true
```

## Phrase filters (`phrase_filtering.yaml`)
Intercept/block phrases in the agent's output before they're spoken; can trigger a function on match.
| Field | Notes |
|---|---|
| `name` (required) | Filter identifier |
| `description` | What it does |
| `regular_expressions` (required) | List of patterns |
| `say_phrase` (bool) | `true` = still speak the match; `false` (default) = suppress |
| `language_code` (optional) | Restrict to one language |
| `function` (optional) | Global function to call on match — not a flow function |

```yaml
phrase_filtering:
  - name: Block Profanity
    description: Blocks profane words from being spoken
    regular_expressions:
      - "\\bbadword\\b"
    say_phrase: false
  - name: Competitor Mention Handler
    description: Intercept competitor names and redirect
    regular_expressions:
      - "\\bcompetitor_name\\b"
    say_phrase: true
    function: handle_competitor_mention
```

**Best practices**: use for safety (profanity, PII leakage) and brand protection; keep regex specific to avoid
false positives.
