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