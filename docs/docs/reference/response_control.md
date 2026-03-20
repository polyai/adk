---
title: Response control
description: Control how voice-agent output is filtered and pronounced before it is spoken to the user.
---

# Response control

<p class="lead">
Response control resources manage what the agent says before it reaches the user.
</p>

They are used to adjust spoken output by:

- fixing pronunciation
- intercepting or blocking phrases before speech synthesis

These resources are voice-channel specific and live under `voice/response_control/`.

## Location

~~~text
voice/response_control/
├── pronunciations.yaml
└── phrase_filtering.yaml
~~~

Both files are optional.

## What response control does

<div class="grid cards" markdown>

-   **Pronunciations**

    ---

    Fix how words, abbreviations, or phrases are spoken by TTS.

-   **Phrase filtering**

    ---

    Block or intercept phrases before they are spoken.

</div>

## Pronunciations

Pronunciation rules live in:

~~~text
voice/response_control/pronunciations.yaml
~~~

These rules are applied before speech synthesis and are useful when the agent says something incorrectly.

### What a pronunciation rule contains

Each item in the `pronunciations` list can include:

| Field | Required | Description |
|---|---|---|
| `regex` | Yes | Regex pattern to match in the output text |
| `replacement` | Yes | Replacement text for speech synthesis |
| `case_sensitive` | No | Whether matching is case-sensitive |
| `language_code` | No | Restrict the rule to a specific language |
| `description` | No | Notes about the rule |

Rules are ordered, so list position matters.

### Example

~~~yaml
pronunciations:
  - regex: "\\bDr\\."
    replacement: Doctor
    case_sensitive: true

  - regex: "\\bMr\\."
    replacement: Mister
    case_sensitive: true
~~~

## Phrase filtering

Phrase-filtering rules live in:

~~~text
voice/response_control/phrase_filtering.yaml
~~~

These rules can block or intercept phrases before they are spoken. A matched phrase can also trigger a function.

### What a phrase filter contains

Each item in the `phrase_filtering` list can include:

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Identifier for the filter |
| `description` | No | Explains what the filter does |
| `regular_expressions` | Yes | Regex patterns to match |
| `say_phrase` | No | Whether to still speak the matched phrase |
| `language_code` | No | Restrict the filter to a specific language |
| `function` | No | Global function to call when a match occurs |

### Example

~~~yaml
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
~~~

## When to use response control

Use response control when standard prompting is not enough and you need a more deterministic layer before output is spoken.

Typical cases include:

- fixing abbreviations or domain-specific terms in TTS
- preventing profanity from being spoken
- reducing the risk of unsafe or brand-damaging output
- intercepting special phrases and triggering code

## Best practices

### For pronunciations

- keep regex patterns targeted and readable
- use language-specific rules when pronunciation should vary by locale
- rely on rule ordering deliberately where multiple patterns could overlap

### For phrase filters

- use phrase filters for safety and brand protection
- keep regex patterns specific to avoid false positives
- only attach a `function` when you need a real side effect
- ensure the `function` value refers to a valid **global function**, not a flow function

!!! warning "Phrase filters are powerful"

    An over-broad regex can suppress or intercept normal output unexpectedly. Keep filters as specific as possible.

## Related pages

<div class="grid cards" markdown>

-   **Voice settings**

    ---

    See where response control fits within the broader voice-channel configuration.
    [Open voice settings](./voice_settings.md)

-   **Functions**

    ---

    Learn how global functions can be triggered from phrase filters.
    [Open functions](./functions.md)

</div>