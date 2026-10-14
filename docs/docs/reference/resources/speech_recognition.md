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

!!! info "No effect on Raven Omni"
    Keyphrase boosting and transcript corrections only apply to the traditional ASR pipeline. Projects running an end-to-end model such as Raven Omni bypass this pipeline, so they are silently ignored.

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

    Configure turn-taking, filler phrases and background ambience.

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

They match the Turn-taking tab of the Model Configuration page in Agent Studio, and apply to the whole voice channel. Individual flow steps can override barge-in, ASR provider, VAD, and LLM settings for a single turn — see [ASR override](./flows.md#asr-override) and [barge-in](./flows.md#barge-in) in the flows reference.

Every section is optional. A section that is left out uses the platform default, and removing a section resets it on the next push. The exception is `background_ambience`, which Agent Studio can't reset: removing it switches ambience off instead.

### Fields

| Field | Description |
|---|---|
| `speech_end_delay_ms` | How long the caller must be silent, in milliseconds, before the agent treats their turn as finished. |
| `barge_in` | Whether the caller can interrupt the agent: `enabled`, `allow_on_first_turn` and `max_per_call`. |
| `filler_phrases` | Phrases the agent says while the caller waits: `enabled`, `phrases`, `randomize`, `initial_interval_seconds` (before the first phrase) and `interval_seconds` (between phrases). |
| `background_ambience` | Background sound played under the agent: `enabled`, `preset` and `loudness` in dB. |

`background_ambience.preset` is one of `office-ambiance`, `restaurant-ambiance` or `whitenoise-subtle`. `loudness` is stored in dB: Agent Studio shows -70 dB as volume 0 and -20 dB as volume 100.

### Example

~~~yaml
speech_end_delay_ms: 800

barge_in:
  enabled: true
  allow_on_first_turn: false
  max_per_call: 5

filler_phrases:
  enabled: false
  phrases:
    - One moment...
    - Just a second...
    - One second...
  randomize: true
  initial_interval_seconds: 2.5
  interval_seconds: 5

background_ambience:
  enabled: false
  preset: office-ambiance
  loudness: -50
~~~

!!! note "Managed voice configuration"
    When the Model Configuration page in Agent Studio is read-only because PolyAI manages the project's voice configuration, the platform chooses the speech end delay. `speech_end_delay_ms` is still pulled and pushed, but has no effect.

!!! warning "Older `asr_settings.yaml` files"
    Earlier versions of the ADK wrote `barge_in: true` / `false` and `interaction_style`. `barge_in: true` is still read as `barge_in.enabled: true`, with a warning. `interaction_style` is ignored, because `speech_end_delay_ms` now sets end-of-speech timing. Run `poly pull` to rewrite the file in the current shape.

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
- `filler_phrases.initial_interval_seconds` must be at least 0.5, and `interval_seconds` at least 1. An enabled `filler_phrases` needs at least one phrase.
- `background_ambience` needs a `preset`, and `loudness` must be between -70 and -20. A preset Agent Studio doesn't know is a warning, not an error.
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