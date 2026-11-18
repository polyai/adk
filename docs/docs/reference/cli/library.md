---
title: poly library
description: Reference for the `poly library` command.
---

# `poly library`

List the language models and ASR models Agent Studio offers in a region. `poly library` requires a subcommand.

Examples:

~~~bash
poly library llm
poly library asr --region eu
poly library refresh
~~~

The lists are the same for every account in a region, so the ADK saves one copy per region on your machine, in `~/.poly/library/`. `poly library llm` and `poly library asr` read that copy, and fetch it first when there's none yet or it's more than a day old. [`poly pull`](./pull.md) and `poly fetch` also refresh it on the same schedule.

In both lists, PolyAI's own models come first and are tagged `PolyAI`, and the rest follow in name order. `--json` returns the models in the same order.

## `poly library llm`

List the language models a project can use, with the name a [flow step's `llm` override](../resources/flows.md#llm) takes and what each model supports.

Examples:

~~~bash
poly library llm
poly library llm --region us
poly library llm --refresh --json
~~~

The table shows each model's name, its model ID (the ID a channel stores, which differs between regions) and its provider model ID (the ID a step override stores), plus two columns:

- **Speech-native**: the model handles speech itself. On the voice channel, the ASR model then doesn't apply.
- **Web chat**: web chat, SMS and email can use the model.

| Flag | Description |
|---|---|
| `--region` | Region to list models for. Defaults to the current project's region. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). |
| `--refresh` | Fetch the lists before listing, even if the saved copy is recent. |

`--json` output shape:

~~~json
{
  "success": true,
  "llm_models": [
    {
      "id": "MODEL-1a2b3c4d",
      "name": "PolyAI Raven 3.5",
      "polyaiModel": true,
      "providerModelId": "polywhirl-3-5",
      "endToEnd": false,
      "supportsWebchat": true,
      "supportsTemperature": true
    }
  ]
}
~~~

`id` differs between regions. A step's `llm` override takes the `name`.

## `poly library asr`

List the speech recognition models the voice channel can use, with the name a [flow step's `asr` override](../resources/flows.md#asr-override) takes.

Examples:

~~~bash
poly library asr
poly library asr --region uk
poly library asr --refresh --json
~~~

| Flag | Description |
|---|---|
| `--region` | Region to list models for. Defaults to the current project's region. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). |
| `--refresh` | Fetch the lists before listing, even if the saved copy is recent. |

`--json` output shape:

~~~json
{
  "success": true,
  "asr_models": [
    {
      "id": "ASR-1a2b3c4d",
      "name": "Deepgram Nova 3",
      "provider": "deepgram",
      "model": "nova-3"
    }
  ]
}
~~~

`id` differs between regions. A step's `asr` override takes the `name`.

## `poly library refresh`

Fetch the language model and ASR model lists now and save them, replacing the saved copy for the region.

Examples:

~~~bash
poly library refresh
poly library refresh --region eu --json
~~~

| Flag | Description |
|---|---|
| `--region` | Region to refresh. Defaults to the current project's region. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). |

`--json` output shape:

~~~json
{
  "success": true,
  "number_of_asr_models": 8,
  "number_of_llm_models": 26
}
~~~
