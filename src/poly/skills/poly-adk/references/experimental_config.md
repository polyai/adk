# Experimental Config

## Purpose
Optional JSON enabling experimental features (feature flags, ASR tuning, conversation control, debug options).

## Location
`agent_settings/experimental_config.json`

## Structure
Flat or nested JSON. Top-level keys are feature categories; values are feature-specific settings.

```json
{
  "asr": {
    "disable_itn": true,
    "eager_final": true
  },
  "conversation_control": {
    "enhanced_tts_preprocessing_enabled": false,
    "max_silence_count": 1000,
    "min_chunk_size": 1
  }
}
```

## Schema
Available features/types are defined in `src/poly/resources/experimental_config_schema.yaml`. `poly validate`
checks this file against that schema. Invalid config in a deployed agent is not read at runtime.

## When to use
Tuning ASR/TTS beyond standard settings; enabling experimental platform features early; adjusting conversation
control (silence handling, chunk sizes).

## Best practices
Only set values you intend to override — omit defaults; validate locally with `poly validate` before pushing;
remove flags no longer needed.
