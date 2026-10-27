---
title: Speech recognition
description: Configure how the agent processes spoken input on the voice channel.
---

# Speech recognition

<p class="lead">
Speech recognition resources control how the agent processes user speech input on the voice channel.
</p>

These resources live under `voice/speech_recognition/` and are used to tune how the agent listens, recognizes, and post-processes spoken input.

!!! note "ASR settings are platform-provisioned — update only"
    `asr_settings.yaml` is pulled for every project with a voice channel. It can be updated with `poly push` but not created or deleted. See the [equivalent note on agent settings](./agent_settings.md) for details.

!!! info "Modular mode only"
    Keyphrase boosting and transcript corrections only apply in modular mode, where separate components handle speech recognition and language processing. Projects in speech-native mode, such as Dialog-RSN-1, don't use them.

## Location

~~~text
voice/speech_recognition/
├── asr_settings.yaml
├── keyphrase_boosting.yaml
└── transcript_corrections.yaml
~~~

All three files are voice-specific. Only `asr_settings.yaml` is the core settings file; the others are optional.

## What speech recognition controls

<div class="grid cards" markdown>

-   **ASR settings**

    ---

    Configure turn-taking: speech end delay and barge-in.

-   **Keyphrase boosting**

    ---

    Bias recognition toward specific words or phrases.

-   **Transcript corrections**

    ---

    Apply regex-based corrections after speech recognition.

</div>

## ASR settings

ASR settings are defined in:

~~~text
voice/speech_recognition/asr_settings.yaml
~~~

They hold the voice channel's turn-taking settings, and apply to the whole voice channel. Individual flow steps can override barge-in, ASR provider, VAD, and LLM settings for a single turn — see [ASR override](./flows.md#asr-override) and [barge-in](./flows.md#barge-in) in the flows reference.

Every section is optional. A section that is left out uses the platform default, and removing a section resets it on the next push.

### Fields

| Field | Description |
|---|---|
| `speech_end_delay_ms` | How long the caller must be silent, in milliseconds, before the agent treats their turn as finished. |
| `barge_in` | Whether the caller can interrupt the agent: `enabled`, `allow_on_first_turn` and `max_per_call`. |

### Example

~~~yaml
speech_end_delay_ms: 800

barge_in:
  enabled: true
  allow_on_first_turn: false
  max_per_call: 5
~~~

!!! note "Projects with a managed voice configuration"
    If PolyAI manages your project's voice configuration, `speech_end_delay_ms` is overwritten at runtime. It's still pulled and pushed, but has no effect. You can check on your project's **Voice › Model** page in Agent Studio, which shows a **Best defaults** tag when the configuration is managed.

## Keyphrase boosting

Keyphrase boosting is defined in:

~~~text
voice/speech_recognition/keyphrase_boosting.yaml
~~~

It biases the recognizer toward specific words or phrases, which is useful for:

- brand names
- product names
- specialist terminology
- domain-specific jargon

### Structure

A `keyphrases` list where each entry includes:

| Field | Required | Description |
|---|---|---|
| `keyphrase` | Yes | The word or phrase to boost |
| `level` | No | Boost strength: `default`, `boosted`, or `maximum`. Default: `default`. |

### Example

~~~yaml
keyphrases:
  - keyphrase: PolyAI
    level: maximum
  - keyphrase: reservation
    level: boosted
  - keyphrase: check-in
    level: default
~~~

## Transcript corrections

Transcript corrections are defined in:

~~~text
voice/speech_recognition/transcript_corrections.yaml
~~~

These rules post-process ASR output to fix common misrecognitions.

They are especially useful for:

- email domains
- repeated digits
- domain-specific phrases
- spoken forms that should be normalized into machine-friendly text

### Structure

A `corrections` list where each entry includes:

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Identifier for the correction group |
| `description` | No | Explains what the correction fixes |
| `regular_expressions` | Yes | Regex rules used for correction |

Each regex rule can include:

| Field | Required | Description |
|---|---|---|
| `regular_expression` | Yes | Pattern to match |
| `replacement` | Yes | Replacement text (supports capture groups like `\1`) |
| `replacement_type` | No | `full` or `partial` / `substring`. Default: `full`. |

### Example

~~~yaml
corrections:
  - name: Email domain fix
    description: Correct common email domain misrecognitions
    regular_expressions:
      - regular_expression: at gmail dot com
        replacement: "@gmail.com"
        replacement_type: full
      - regular_expression: at hotmail dot com
        replacement: "@hotmail.com"
        replacement_type: full

  - name: Number normalization
    description: Normalize spoken numbers to digits
    regular_expressions:
      - regular_expression: \bdouble (\d)\b
        replacement: \1\1
        replacement_type: partial
~~~

## Validation

- `speech_end_delay_ms` must be a whole number between 200 and 1500.
- `barge_in.max_per_call` can't be negative.
- Keys inside a section must be ones listed above, so a misspelt key is an error rather than being ignored.
- Each keyphrase must be non-empty, with a `level` of `default`, `boosted`, or `maximum`.
- Keyphrases must be unique once trimmed and lowercased — Agent Studio treats `Infusion Sets` and `infusion sets` as the same phrase, and rejects a project that keeps both.
- Each transcript correction needs a unique `name` and at least one regex rule, and every rule needs a `regular_expression`.
- `replacement_type` must be one of `full`, `partial`, or `substring`.

## Best practices

- use `keyphrase_boosting` for terms the recognizer is likely to miss
- keep boosted keyphrases focused and specific
- keep each keyphrase unique after trimming and lowercasing
- use transcript corrections for common, repeated recognition errors
- avoid overly broad regex rules that may alter normal input unexpectedly
- change `speech_end_delay_ms` in small steps: lower values respond faster but cut off callers who pause mid-sentence
- leave a section out unless you need a value other than the platform default

!!! tip "Use the lightest possible intervention"

    Start with the default settings, then add boosting or transcript corrections only where recognition problems are actually recurring.

## Related pages

<div class="grid cards" markdown>

-   **Voice settings**

    ---

    See how speech recognition fits into the wider voice-channel configuration.
    [Open voice settings](./voice_settings.md)

-   **Response control**

    ---

    Configure what happens to output before it is spoken.
    [Open response control](./response_control.md)

</div>