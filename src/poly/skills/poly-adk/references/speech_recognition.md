# Speech Recognition

## Overview
Controls how the agent processes voice input, under `voice/speech_recognition/`:
```
voice/speech_recognition/
├── asr_settings.yaml               # Barge-in, interaction style
├── keyphrase_boosting.yaml         # Optional - bias ASR toward specific words
└── transcript_corrections.yaml     # Optional - regex corrections on ASR output
```

## ASR settings (`asr_settings.yaml`)
| Field | Notes |
|---|---|
| `barge_in` (bool) | Allow the user to interrupt the agent while speaking. Default `false`. |
| `interaction_style` (string) | `balanced` (default), `precise`, `swift`, `sonic`, `turbo` |

```yaml
barge_in: false
interaction_style: balanced
```
| Style | Behavior |
|---|---|
| `precise` | Higher accuracy, higher latency |
| `balanced` | Default balance |
| `swift` | Faster, slightly less accurate |
| `sonic` / `turbo` | Lowest latency |

## Keyphrase boosting (`keyphrase_boosting.yaml`)
Biases the recognizer toward brand names, product names, jargon.
| Field | Notes |
|---|---|
| `keyphrase` (required) | Word/phrase to boost |
| `level` | `default` (default), `boosted`, `maximum` |

```yaml
keyphrases:
  - keyphrase: PolyAI
    level: maximum
  - keyphrase: reservation
    level: boosted
  - keyphrase: check-in
    level: default
```

## Transcript corrections (`transcript_corrections.yaml`)
Post-process ASR output with regex to fix common misrecognitions (email domains, spelled-out values, jargon).
| Field | Notes |
|---|---|
| `name` (required) | Correction group identifier |
| `description` | What it fixes |
| `regular_expressions` | List of `{regular_expression, replacement, replacement_type}` |
| `replacement_type` | `full` (default, replaces entire match) or `partial`/`substring` |

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
