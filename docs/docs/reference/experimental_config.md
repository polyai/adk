---
title: Experimental config
description: Enable experimental features and advanced runtime settings for an agent.
---

# Experimental config

<p class="lead">
The experimental config file is an optional JSON file used to enable experimental features and advanced runtime settings for an agent.
</p>

Use it for:

- feature flags
- ASR tuning
- conversation control
- debug-oriented options

## Location

The file lives at:

~~~text
agent_settings/experimental_config.json
~~~

## What it contains

The file is a JSON object.

It may be:

- flat
- nested
- grouped by feature category

Top-level keys represent feature areas, and values contain the settings for those features.

## Example

~~~json
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
~~~

## Schema and validation

Available features and their types are defined in:

~~~text
src/poly/resources/experimental_config_schema.yaml
~~~

The ADK validates `experimental_config.json` against this schema when you run:

~~~bash
poly validate
~~~

Invalid configuration fails `poly validate` locally. Experimental config that fails validation is not read by the runtime in deployed agents.

!!! info "Validate before pushing"

    Experimental config can affect runtime behavior in subtle ways. Always run `poly validate` locally before pushing changes.

## When to use it

Use experimental config when you need behavior that goes beyond the standard Agent Studio settings.

Common use cases include:

<div class="grid cards" markdown>

-   **ASR and TTS tuning**

    ---

    Adjust speech recognition or speech output behavior beyond the standard channel settings.

-   **Experimental platform features**

    ---

    Enable features before they are generally available.

-   **Conversation control**

    ---

    Tune parameters such as silence handling or chunk size behavior.

</div>

## Feature reference

The following sections describe notable feature areas available in the schema.

### Audio enhancement

Configure audio enhancement processing applied to the incoming audio stream before speech recognition. Three providers are available: `ai-coustics`, `dolby`, and `krisp`.

#### `krisp`

Krisp provides noise cancellation and voice isolation. Settings include:

| Field | Type | Description | Default |
|---|---|---|---|
| `model` | string | Krisp model variant: `"noise-cancellation"`, `"voice-isolation"`, `"telephony"`, `"telephony-lite"`, `"transcription"` | `"telephony-lite"` |
| `noise_suppression_level` | integer | Noise suppression intensity. `0` = off, `100` = max. | `100` |
| `frame_duration_ms` | integer | Audio frame duration in milliseconds. Allowed values: `10`, `15`, `20`, `30`, `32`. | `20` |
| `timeout_ms` | integer | Max milliseconds to wait for enhancement per chunk before falling back to original audio. `0` = no timeout. | `100` |

Example:

~~~json
{
  "audio_enhancement": {
    "krisp": {
      "model": "telephony-lite",
      "noise_suppression_level": 100,
      "frame_duration_ms": 20,
      "timeout_ms": 100
    }
  }
}
~~~

### DTMF

Configure DTMF behavior, including disabling speech recognition for DTMF-only steps.

The `dtmf` object supports a `flow_overrides` map where each key is a flow name. Per-flow settings include:

| Field | Type | Description |
|---|---|---|
| `disable_speech` | boolean | Whether to disable speech recognition when DTMF is enabled for this flow. |
| `steps` | object | Step-specific overrides. Each key is a step name. |

Per-step settings (nested under `steps`) include:

| Field | Type | Description |
|---|---|---|
| `disable_speech` | boolean | Whether to disable speech recognition for this step. Takes precedence over the flow-level setting. |
| `first_digit_timeout` | integer | Timeout in seconds for the first DTMF digit input for this step. Minimum: `1`. |

Example:

~~~json
{
  "dtmf": {
    "flow_overrides": {
      "Payment Flow": {
        "disable_speech": true,
        "steps": {
          "Enter Card Number": {
            "disable_speech": true,
            "first_digit_timeout": 5
          }
        }
      }
    }
  }
}
~~~

### Memory

Configure agent memory features, including repeat-caller identification.

#### `identifier_source`

By default, memory lookups use the caller or callee phone number as the identifier. The `identifier_source` field lets you supply a custom source instead.

| Field | Type | Description |
|---|---|---|
| `identifier_source` | string | Custom source for the memory lookup identifier. Must match the pattern `(sip_headers\|integration_attributes\|state):.+`. |

Example:

~~~json
{
  "memory": {
    "identifier_source": "sip_headers:X-Customer-Id"
  }
}
~~~

### OpenAI Realtime

Configure behavior for the OpenAI Realtime integration, including transcription settings.

#### `set_transcriber_language`

| Field | Type | Description | Default |
|---|---|---|---|
| `set_transcriber_language` | boolean | When `true`, the conversation language code is passed to the transcriber in the session configuration, making the model adhere more strictly to the specified language. Do not use this in multilingual projects with a language detection component. | `false` |

Example:

~~~json
{
  "openai_realtime": {
    "transcription": {
      "set_transcriber_language": true
    }
  }
}
~~~

### `include_kb_functions_in_flows`

Controls whether knowledge base (KB) functions from retrieved RAG topics are shown to the model inside flows.

| Value | Behaviour |
|---|---|
| `true` | KB functions from retrieved RAG topics are shown to the model inside flows, even on steps that have their own `functions_referenced`. |
| `false` (default) | KB functions are hidden inside flows. |

This setting only affects behavior inside flows. Outside flows, KB functions are always shown. It can be overridden per-flow or per-step.

## Best practices

- only set values you actually intend to override
- omit defaults rather than copying them unnecessarily
- validate locally with `poly validate` before pushing
- remove flags that are no longer needed
- treat the file as an advanced override layer, not a dumping ground for ordinary config

## Related pages

<div class="grid cards" markdown>

-   **Agent settings**

    ---

    See where experimental config sits within the broader agent settings area.
    [Open agent settings](./agent_settings.md)

-   **Speech recognition**

    ---

    Compare experimental ASR controls with standard voice speech-recognition settings.
    [Open speech recognition](./speech_recognition.md)

</div>
