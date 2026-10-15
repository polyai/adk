# Voice Settings

## Overview

Voice settings configure the agent's behavior on the voice (phone call) channel. They are defined in `voice/configuration.yaml`.

## Location
`voice/configuration.yaml`

## Greeting

The first message the agent speaks when a call starts.

### Fields
- **welcome_message** (required): Text of the greeting. Supports `{{attr:...}}` and `{{vrbl:...}}` references.
- **language_code** (required): BCP-47 language code (e.g. `en-GB`, `en-US`).

### Example
```yaml
greeting:
  welcome_message: Hello! Welcome to our service. How can I assist you today?
  language_code: en-GB
```

## Style Prompt

Channel-specific instructions that shape how the agent speaks. Separate from personality - use this for voice-specific guidance (e.g. phrasing, verbosity, tone of speech).

### Fields
- **prompt**: Free-text style instructions. No resource references allowed.

### Example
```yaml
style_prompt:
  prompt: You are a helpful and professional customer service assistant. Use natural, conversational phrasing.
```

## Disclaimer Message

An optional disclaimer played at the start of a voice call before the greeting (e.g. "This call may be recorded").

### Fields
- **message**: Disclaimer text. Supports `{{attr:...}}` and `{{vrbl:...}}` references.
- **enabled**: Boolean to toggle the disclaimer on/off.
- **language_code**: BCP-47 language code.

### Example
```yaml
disclaimer_messages:
  message: This conversation may be recorded for quality assurance.
  enabled: true
  language_code: en-GB
```

## Filler Phrases

Phrases the agent says while the caller waits on a slow turn. Optional: removing the section
resets filler phrases on the next push.

### Fields
- **enabled** (bool)
- **phrases** (list of strings): at least one when enabled.
- **randomize** (bool): pick phrases in random order.
- **initial_interval_seconds** (float, at least 0.5): wait before the first phrase.
- **interval_seconds** (float, at least 1): wait between phrases.

### Example
```yaml
filler_phrases:
  enabled: true
  phrases:
    - One moment...
    - Just a second...
  randomize: true
  initial_interval_seconds: 2.5
  interval_seconds: 5
```

## Background Ambience

Background sound played under the agent's speech. Plays while the section is in the file;
removing it turns ambience off.

### Fields
- **preset**: `office-ambiance`, `restaurant-ambiance` or `whitenoise-subtle`. An unknown preset
  is a warning, not an error.
- **loudness** (dB, -70 to -20): Agent Studio shows -70 as volume 0 and -20 as volume 100.

### Example
```yaml
background_ambience:
  preset: office-ambiance
  loudness: -50
```

Keys inside `filler_phrases` and `background_ambience` are checked, so a misspelt key is an
error.

## Full `voice/configuration.yaml` example
```yaml
greeting:
  welcome_message: Hello! Welcome to our service. Your account shows {{attr:member_status}}. How can I assist you today?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional customer service assistant.
disclaimer_messages:
  message: This conversation may be recorded for quality assurance.
  enabled: true
  language_code: en-GB
filler_phrases:
  enabled: true
  phrases:
    - One moment...
    - Just a second...
  randomize: true
  initial_interval_seconds: 2.5
  interval_seconds: 5
background_ambience:
  preset: office-ambiance
  loudness: -50
```

## Related voice resources
- [Speech Recognition](speech_recognition.md) - turn-taking (speech end delay, barge-in), keyphrase boosting, transcript corrections
- [Response Control](response_control.md) - pronunciations, phrase filters
