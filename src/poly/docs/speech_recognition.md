# Speech Recognition

## Overview

Speech recognition resources control how the agent processes user speech input on the voice channel. They live under `voice/speech_recognition/`.

```
voice/speech_recognition/
├── asr_settings.yaml               # Barge-in, interaction style
├── keyphrase_boosting.yaml         # Optional — bias ASR toward specific words
└── transcript_corrections.yaml     # Optional — regex corrections on ASR output
```

## ASR Settings (`asr_settings.yaml`)

Global speech recognition settings for the voice channel.

### Fields
- **barge_in** (bool): Allow the user to interrupt the agent while it's speaking. Default: `false`.
- **interaction_style** (string): Controls ASR latency/accuracy trade-off. One of: `balanced`, `precise`, `swift`, `sonic`, `turbo`. Default: `balanced`.

### Example
```yaml
barge_in: false
interaction_style: balanced
```

| Style | Behavior |
|-------|----------|
| `precise` | Higher accuracy, higher latency |
| `balanced` | Default balance of speed and accuracy |
| `swift` | Faster responses, slightly less accurate |
| `sonic` / `turbo` | Lowest latency |

## Keyphrase Boosting (`keyphrase_boosting.yaml`)

Bias the speech recognizer toward specific words or phrases (brand names, product names, jargon). Improves recognition accuracy for domain-specific terms.

### Structure
A `keyphrases` list where each entry has:
- **keyphrase** (required): The word or phrase to boost.
- **level**: Boost strength — `default`, `boosted`, or `maximum`. Default: `default`.

### Example
```yaml
keyphrases:
  - keyphrase: PolyAI
    level: maximum
  - keyphrase: reservation
    level: boosted
  - keyphrase: check-in
    level: default
```

## Transcript Corrections (`transcript_corrections.yaml`)

Post-process ASR output with regex rules to fix common misrecognitions. Useful for email domains, spelled-out values, and domain-specific terms.

### Structure
A `corrections` list where each entry has:
- **name** (required): Identifier for the correction group.
- **description**: What this correction fixes.
- **regular_expressions**: List of regex rules, each with:
  - **regular_expression** (required): Regex pattern to match.
  - **replacement** (required): Replacement string (supports capture groups like `\1`).
  - **replacement_type**: `full` (replace entire match, default) or `partial`/`substring` (replace within context).

### Example
```yaml
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
```
