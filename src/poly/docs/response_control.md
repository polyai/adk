# Response Control

## Overview

Response control resources manage what the agent says before it reaches the user. They handle TTS pronunciation fixes and phrase filtering (blocking or intercepting output). They live under `voice/response_control/`.

```
voice/response_control/
├── pronunciations.yaml             # Optional - TTS pronunciation rules
└── phrase_filtering.yaml           # Optional - block/intercept phrases before TTS
```

## Pronunciations (`pronunciations.yaml`)

TTS pronunciation rules that fix how the agent says specific words or abbreviations. Rules are regex-based and applied before speech synthesis.

### Structure
A `pronunciations` list where each entry has:
- **regex** (required): Regex pattern to match in the agent's output text.
- **replacement** (required): What to replace it with for TTS (can be empty string `""`).
- **case_sensitive** (bool): Whether the regex is case-sensitive. Default: `false`.
- **language_code** (string, optional): Restrict the rule to a specific language.
- **description** (string, optional): What this rule does.

Rules are ordered; position in the list matters.

### Example
```yaml
pronunciations:
  - regex: "\\bDr\\."
    replacement: Doctor
    case_sensitive: true
  - regex: "\\bMr\\."
    replacement: Mister
    case_sensitive: true
```

## Phrase Filters (`phrase_filtering.yaml`)

Intercept or block phrases in the agent's output before they are spoken. Can optionally trigger a function when a phrase is matched.

### Structure
A `phrase_filtering` list where each entry has:
- **name** (required): Identifier for this filter.
- **description**: What this filter does.
- **regular_expressions** (required): List of regex patterns to match.
- **say_phrase** (bool): If `true`, still speak the matched phrase. If `false`, suppress it. Default: `false`.
- **language_code** (string, optional): Restrict to a specific language.
- **function** (string, optional): Name of a global function to call when a match occurs.

### Example
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

### Best practices
- Use phrase filters for safety (profanity, PII leakage) and brand protection.
- The `function` field must reference a valid global function (not a flow function).
- Keep regex patterns specific to avoid false positives.
