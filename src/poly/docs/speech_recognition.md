# Speech Recognition

## Overview

Speech recognition resources control how the agent processes user speech input on the voice channel. They live under `voice/speech_recognition/`.

```
voice/speech_recognition/
├── asr_settings.yaml               # ASR model, turn-taking, filler phrases, ambience
├── keyphrase_boosting.yaml         # Optional - bias ASR toward specific words
└── transcript_corrections.yaml     # Optional - regex corrections on ASR output
```

## ASR Settings (`asr_settings.yaml`)

The voice channel's model configuration: the Speech Recognition and Turn-taking tabs of the
Model Configuration page in Agent Studio. Update only: the file can't be created or deleted.

Every section is optional. A section that is left out uses the platform default, and removing
a section resets it on the next push. `background_ambience` can't be reset, so removing it
switches ambience off instead.

### Fields
- **asr_model**: Speech recognition model.
  - **provider** (string, required), **model** (string, required), **language** (string, optional).
  - Leave it out, or set `asr_model: auto`, to let the platform pick.
  - Has no effect on end-to-end models such as Raven Omni.
- **speech_end_delay_ms** (int): Silence, in milliseconds, before the caller's turn is treated as finished. 200–1500.
- **barge_in**: Whether the caller can interrupt the agent.
  - **enabled** (bool), **allow_on_first_turn** (bool), **max_per_call** (int, 0 or more).
- **filler_phrases**: Phrases the agent says while the caller waits.
  - **enabled** (bool), **phrases** (list of strings, at least one when enabled), **randomize** (bool).
  - **initial_interval_seconds** (float, at least 0.5): wait before the first phrase.
  - **interval_seconds** (float, at least 1): wait between phrases.
- **background_ambience**: Background sound under the agent's speech.
  - **enabled** (bool), **preset** (`office-ambiance`, `restaurant-ambiance` or `whitenoise-subtle`), **loudness** (dB, -70 to -20; Agent Studio shows -70 as volume 0 and -20 as volume 100).

Keys inside a section are checked, so a misspelt key is an error.

If the Model Configuration page is read-only because PolyAI manages the project's voice
configuration, `asr_model` and `speech_end_delay_ms` have no effect.

### Example
```yaml
asr_model:
  provider: openai
  model: gpt-4o-transcribe
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
  randomize: true
  initial_interval_seconds: 2.5
  interval_seconds: 5
background_ambience:
  enabled: false
  preset: office-ambiance
  loudness: -50
```

These apply to the whole voice channel. Individual flow steps can override barge-in, ASR
provider, VAD and LLM settings for a single turn — see [step settings](flows.md#step-settings).

Older files with `barge_in: true` / `false` or `interaction_style` still load, with a warning:
`barge_in: true` is read as `barge_in.enabled: true`, and `interaction_style` is ignored. Run
`poly pull` to rewrite the file.

## Keyphrase Boosting (`keyphrase_boosting.yaml`)

Bias the speech recognizer toward specific words or phrases (brand names, product names, jargon). Improves recognition accuracy for domain-specific terms.

### Structure
A `keyphrases` list where each entry has:
- **keyphrase** (required): The word or phrase to boost.
- **level**: Boost strength - `default`, `boosted`, or `maximum`. Default: `default`.

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
