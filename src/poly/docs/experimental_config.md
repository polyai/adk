# Experimental Config

## Purpose
Optional JSON file that enables experimental features and their settings for an agent (feature flags, ASR tuning, conversation control, debug options).

## Location
`agent_settings/experimental_config.json`

## Structure
A flat or nested JSON object. Top-level keys are feature categories; values are feature-specific settings.

## Example
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
Available features and their types are defined in `src/poly/resources/experimental_config_schema.yaml`. The `poly validate` command checks the file against this schema. Invalid config in deployed agents will not be read by the runtime.

## When to use
- Tuning ASR/TTS behavior beyond standard Agent Studio settings.
- Enabling experimental platform features before they are generally available.
- Adjusting conversation control parameters (silence handling, chunk sizes).

## Best practices
- Only set values you intend to override; omit defaults.
- Validate locally with `poly validate` before pushing.
- Remove flags that are no longer needed.
