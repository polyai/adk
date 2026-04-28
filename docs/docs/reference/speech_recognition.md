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
    `asr_settings.yaml` is created automatically by the platform when a project is created. It always exists on any Agent Studio project and can be updated with `poly push`, but cannot be created from scratch via the ADK. If this file appears in a project directory without a matching entry in `.agent_studio_config` — for example, after copying a directory from another project — the push will fail with a "Create operation not supported" error. Always start a new project with [`poly init`](./cli.md#poly-init) and [`poly pull`](./cli.md#poly-pull) rather than copying an existing directory.

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

    Configure global speech-recognition behavior such as barge-in and latency/accuracy style.

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

These settings control global speech-recognition behavior for the voice channel.

### Fields

| Field | Type | Description |
|---|---|---|
| `barge_in` | `bool` | Whether the user can interrupt the agent while it is speaking. Default: `false`. |
| `interaction_style` | `string` | Controls the latency/accuracy trade-off. Default: `balanced`. |

### Example

~~~yaml
barge_in: false
interaction_style: balanced
~~~

### Interaction styles

| Style | Behavior |
|---|---|
| `precise` | Higher accuracy, higher latency |
| `balanced` | Default balance of speed and accuracy |
| `swift` | Faster responses, slightly lower accuracy |
| `sonic` / `turbo` | Lowest latency |

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
| `level` | No | Boost strength: `default`, `boosted`, or `maximum` |

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
| `replacement` | Yes | Replacement text |
| `replacement_type` | No | `full` or `partial` / `substring` |

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

## Best practices

- use `keyphrase_boosting` for terms the recognizer is likely to miss
- keep boosted keyphrases focused and specific
- use transcript corrections for common, repeated recognition errors
- avoid overly broad regex rules that may alter normal input unexpectedly
- choose the ASR interaction style deliberately based on latency and accuracy needs

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