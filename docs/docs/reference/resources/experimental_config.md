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

Available features and their types are defined in a bundled schema file:

~~~text
src/poly/resources/experimental_config_schema.yaml
~~~

The ADK validates `experimental_config.json` against this schema when you run:

~~~bash
poly validate
~~~

Invalid configuration fails `poly validate` locally. Experimental config that fails validation is not read by the runtime in deployed agents.

### Custom schema path

If the bundled schema does not match the schema expected by your Agent Studio environment, you can point validation at a custom schema file by setting the `ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH` environment variable:

~~~bash
export ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH=/path/to/your/experimental_config_schema.yaml
poly validate
~~~

When `ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH` is set, the ADK uses that file instead of the bundled schema. When the variable is unset or empty, validation falls back to the bundled schema.

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

Configure audio enhancement processing applied to the incoming audio stream before speech recognition. Two providers are available: `ai-coustics` and `krisp`.

#### `ai-coustics`

| Field | Type | Description | Default | Range |
|---|---|---|---|---|
| `enabled` | boolean | Enable or disable AI-Coustics audio enhancement. | `true` | |
| `model` | string | Model/quality tier: `voicefocus_small`, `voicefocus`, `fast`. `standard` and `high` are deprecated aliases that remap to `voicefocus_small` and `voicefocus`. | `"voicefocus_small"` | |
| `noise_reduction` | number | Background noise removal strength. `0.0` = off, `1.0` = max. | `0.7` | 0.0 – 1.0 |
| `voice_gain` | number | Output volume adjustment multiplier (`1.0` = no change), compensates for volume reduction after noise removal. | `1.0` | 0.1 – 4.0 |
| `noise_gate` | boolean | Enable silence gating for cleaner output, useful for ASR systems to avoid false triggers. | `false` | |
| `timeout_ms` | integer | Max time in milliseconds to wait for enhancement per chunk before falling back to original audio. `0` = no timeout. | `100` | 0 – 1000 |

##### `ai-coustics` VAD

The `ai-coustics` enhancer also supports a `vad` (voice activity detection) sub-object for tuning how speech is detected in the audio stream.

| Field | Type | Description | Default | Range |
|---|---|---|---|---|
| `sensitivity` | number | Energy threshold for speech detection. Energy threshold = 10^(-sensitivity). Higher values detect quieter speech. | `6.0` | 1.0 – 15.0 |
| `speech_hold_duration` | number | How long the VAD continues to report speech after the audio signal no longer contains speech (in seconds). Useful for bridging short pauses. | `0.03` | ≥ 0.0 |
| `minimum_speech_duration` | number | How long speech must be present before the VAD considers it speech (in seconds). Helps filter out short non-speech sounds like clicks or coughs. | `0.0` | 0.0 – 1.0 |

Example:

~~~json
{
  "audio_enhancement": {
    "ai-coustics": {
      "enabled": true,
      "noise_reduction": 0.7,
      "vad": {
        "sensitivity": 6.0,
        "speech_hold_duration": 0.03,
        "minimum_speech_duration": 0.0
      }
    }
  }
}
~~~

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

### Background track

The `background_track` object (`name`, `loudness`) plays a looped recording behind the agent's voice for the duration of the call. See `background_track` in the schema for exact fields and ranges.

!!! info "No effect on Raven Omni, and telephony only"
    `background_track` only applies to the Raven 3.5 voice stack — it has no effect under Raven Omni. It also only plays on real telephony calls, not in the Agent Studio web call testing UI, so it won't be audible when testing there.

### Barge-in

The fields below sit under `barge_in.experimental_config` and control how interrupted speech is handled and displayed.

#### Interruption granularity

`interruption_granularity` controls where the split happens in agent speech when the user barges in.

| Value | Behavior |
|---|---|
| `"word"` | Audio-timing split at the word boundary. |
| `"sentence"` | Drop the interrupted sentence. |
| `"sentence_keep"` | Keep the interrupted sentence. |
| `"chunk"` | Drop the entire TTS chunk. |

#### Interruption display

`interruption_display` controls how interrupted text appears in Agent Studio `msg.Text` (and in LLM context if `interruption_display_llm` is not set).

| Value | Behavior |
|---|---|
| `"ellipsis"` | Append `"..."` to the said portion. |
| `"tags"` | Wrap the unsaid portion in `<interrupted>` XML tags. |
| `"strip"` | Drop unsaid text silently. |
| `"none"` | Keep the full text unchanged. |
| `"barge"` | Append a `"[BARGE IN]"` marker. |

#### `interruption_display_llm`

An optional LLM-specific override for interrupted text display. Accepts the same values as `interruption_display`. When absent, inherits from `interruption_display`.

#### `truncate_interrupted_utterances`

| Field | Type | Default | Description |
|---|---|---|---|
| `truncate_interrupted_utterances` | boolean | `false` | When `true`, function-output utterances on interrupted turns are truncated to only the said (heard) portion, dropping unsaid text. Useful when TTS utterances are attached to function outputs and should reflect what the caller actually heard. |

#### `annotate_interrupted_function_calls`

| Field | Type | Description |
|---|---|---|
| `annotate_interrupted_function_calls` | boolean | When `true`, function call results on interrupted turns are annotated with said/unsaid context so the LLM can judge whether the initiating question was fully communicated. Defaults to `false`. |

Example:

~~~json
{
  "barge_in": {
    "experimental_config": {
      "interruption_granularity": "sentence",
      "interruption_display": "ellipsis",
      "interruption_display_llm": "tags",
      "truncate_interrupted_utterances": true,
      "annotate_interrupted_function_calls": false
    }
  }
}
~~~

### DTMF

Configure DTMF behavior, including disabling speech recognition for DTMF-only steps.

#### Global DTMF config

The `dtmf.global` object applies to every turn. Step-level DTMF settings take precedence when enabled.

| Field | Type | Description |
|---|---|---|
| `is_enabled` | boolean | Whether global DTMF collection is enabled. |
| `max_digits` | integer | Maximum number of DTMF digits to collect. Minimum: `0`. |
| `end_key` | string | Key that signals the end of DTMF input (e.g. `"#"`). |
| `collect_while_agent_speaking` | boolean | Whether to collect DTMF digits while the agent is speaking. |

#### Flow and step overrides

The `dtmf` object also supports a `flow_overrides` map where each key is a flow name. Per-flow settings include:

| Field | Type | Description |
|---|---|---|
| `disable_speech` | boolean | Whether to disable speech recognition when DTMF is enabled for this flow. |
| `steps` | object | Step-specific overrides. Each key is a step name. |

Per-step settings (nested under `steps`) include:

| Field | Type | Description |
|---|---|---|
| `disable_speech` | boolean | Whether to disable speech recognition for this step. Takes precedence over the flow-level setting. |
| `first_digit_timeout` | integer | Timeout in seconds for the first DTMF digit input for this step. Minimum: `1`. |

!!! warning "Override keys must match `name:` exactly, or they silently do nothing"
    `flow_overrides` and `flow_overrides.<flow>.steps` keys are matched against the flow's and step's `name:` field (not the directory slug), including case and whitespace. A key that doesn't match passes `poly validate` — the schema has no way to check it — but the override is never applied at runtime, with no error surfaced beyond a Datadog warning. When a flow or step is renamed, update the override key too. This applies to every `flow_overrides` map in this file, including [`llm.flow_overrides`](#include_kb_functions_in_flows).

Example:

~~~json
{
  "dtmf": {
    "global": {
      "is_enabled": true,
      "max_digits": 16,
      "end_key": "#",
      "collect_while_agent_speaking": false
    },
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

### Language switching

Configure automatic language switching behavior.

| Field | Type | Default | Description |
|---|---|---|---|
| `explicit_only` | boolean | `false` | When `true`, the agent only switches language when the user explicitly asks. When `false` (default), the agent may also switch spontaneously based on detected language in the transcription. |

Example:

~~~json
{
  "language_switching": {
    "explicit_only": true
  }
}
~~~

### Memory

Configures agent memory features. `memory.identifier_source` overrides the default caller/callee-phone-number lookup identifier with a custom source (`sip_headers:...`, `integration_attributes:...`, or `state:...`). `memory.repeat_caller` controls repeat-caller analytics and which state keys are exposed and persisted to Agent Memory (`state_keys`) — only listed keys are ever persisted. See `memory` in the schema for exact fields.

### Realtime (OpenAI)

Configures the OpenAI realtime speech-to-speech integration, nested under `realtime.openai_config`. The one notable field is `set_transcriber_language` — when `true`, it pins the transcriber to the conversation's language code; avoid it in multilingual projects that rely on language detection. See `realtime` in the schema for exact fields.

### Prompts

The `prompts` section supports channel-specific and language-related decorator overrides.

| Field | Type | Description |
|---|---|---|
| `webchat_decorator` | string | Optional webchat-specific decorator for the `webchat.polyai` channel. |
| `sms_decorator` | string | Optional SMS-specific decorator for the `sms.polyai` channel. |
| `voice_decorator` | string | Optional voice-specific decorator for `chat.polyai` or `sip.polyai` channels. |
| `language_switching_instructions` | string | Optional instructions for language switching behaviour. Must contain a `{available_languages}` placeholder. |

Example:

~~~json
{
  "prompts": {
    "sms_decorator": "Keep responses brief and suitable for SMS.",
    "language_switching_instructions": "You may switch to any of the following languages if the user requests it: {available_languages}."
  }
}
~~~

### Webhooks

Fires HTTP callbacks on `on_draft_published` (sandbox draft publish) or `on_deployment.<sandbox|pre-release|live>` (deployment) events. Each entry needs a `url`, and can optionally set `auth` (a header or query-param name plus a `secret_name`) and a `payload_template` to replace the default deployment payload.

`payload_template` string values may contain `{{field}}` placeholders (`deployment_id`, `account_id`, `project_id`, `client_env`, `artifact_version`, `deployment_type`, `timestamp`, `user`), plus a special `{{payload}}` token that injects the entire deployment payload at a specific position — useful for receivers like GitHub's `repository_dispatch` that require nesting under a key such as `client_payload`. Without `{{payload}}` in the template, the deployment fields are merged at the top level instead. See `webhooks` in the schema for exact fields.

### `include_kb_functions_in_flows`

Controls whether knowledge base (KB) functions from retrieved RAG topics are shown to the model inside flows. This field lives under the top-level `llm` key, as `llm.include_kb_functions_in_flows`.

| Value | Behavior |
|---|---|
| `true` | KB functions from retrieved RAG topics are shown to the model inside flows, even on steps that have their own `functions_referenced`. |
| `false` (default) | KB functions are hidden inside flows. |

This setting only affects behavior inside flows. Outside flows, KB functions are always shown. It can be overridden per-flow (`llm.flow_overrides.<flow_name>.include_kb_functions_in_flows`) or per-step (`llm.flow_overrides.<flow_name>.steps.<step_name>.include_kb_functions_in_flows`).

Example:

~~~json
{
  "llm": {
    "include_kb_functions_in_flows": true,
    "flow_overrides": {
      "Payment Flow": {
        "include_kb_functions_in_flows": false
      }
    }
  }
}
~~~

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
