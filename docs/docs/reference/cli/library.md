---
title: poly library
description: Reference for the `poly library` command.
---

# `poly library`

List the models Agent Studio offers in the project's region. `poly library` requires a subcommand.

The lists are the same for every account in a region. PolyAI's own models come first and are tagged `PolyAI`, and the rest follow in name order. `--json` returns the models in the same order.

## `poly library llm`

List the language models a project can use, with the ID a [flow step's `llm` override](../resources/flows.md#llm) takes and what each model supports.

Examples:

~~~bash
poly library llm
poly library llm --json
~~~

The table shows each model's name and model ID, plus three columns:

- **Speech-native**: the model handles speech itself. On the voice channel, the ASR model then doesn't apply.
- **Web chat**: web chat, SMS and email can use the model.
- **Temperature**: a temperature can be set with the model.

`--json` output shape:

~~~json
[
  {
    "id": "MODEL-1a2b3c4d",
    "name": "PolyAI Raven 3.5",
    "providerModelId": "polywhirl-3-5",
    "endToEnd": false,
    "polyaiModel": true,
    "supportsWebchat": true,
    "supportsTemperature": true
  }
]
~~~

`id` differs between regions. `providerModelId` is the same everywhere, and is the value a step's `llm.provider_model_id` takes.

## `poly library asr`

List the speech recognition models the voice channel can use, with the provider and model a [flow step's `asr` override](../resources/flows.md#asr-override) takes.

Examples:

~~~bash
poly library asr
poly library asr --json
~~~

`--json` output shape:

~~~json
[
  {
    "id": "ASR-1a2b3c4d",
    "name": "Deepgram Nova 3",
    "provider": "deepgram",
    "model": "nova-3"
  }
]
~~~

`id` differs between regions. `provider` and `model` are the values a step's `asr` override takes.
