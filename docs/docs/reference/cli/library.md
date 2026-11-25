---
title: poly library
description: Reference for the `poly library` command.
---

# `poly library`

List the language models, ASR models and TTS voices Agent Studio offers. `poly library` requires a subcommand.

Examples:

~~~bash
poly library llm
poly library asr --region eu
poly library voice list --language en-GB
poly library refresh
~~~

The model lists are the same for every account in a region, so the ADK saves one copy per region on your machine, in `~/.poly/library/`. `poly library llm` and `poly library asr` read that copy, and fetch it first when there's none yet or it's more than a day old. [`poly pull`](./pull.md) and `poly fetch` also refresh it on the same schedule.

Voices differ between accounts, because an account can import its own. The ADK saves them separately for each account, and refreshes them on the same schedule.

In the model lists, PolyAI's own models come first and are tagged `PolyAI`, and the rest follow in name order. `--json` returns the models in the same order.

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

## `poly library voice list`

List the TTS voices the project's account can use: the shared library and the voices the account has imported.

Examples:

~~~bash
poly library voice list
poly library voice list --language fr --gender female
poly library voice list --owner account
poly library voice list --name anne --json
~~~

Voices are in Agent Studio's order: the shared library before imported voices, then featured voices, then the voices the most live projects use. The table pages through `less` when it's taller than the terminal, so `/` searches it and `&` filters it to matching rows.

| Flag | Description |
|---|---|
| `--name` | Only voices whose name contains this text, ignoring case. |
| `--language` | Only voices in this language, e.g. `en` or `en-GB`. |
| `--gender` | Only voices of this gender. One of `male`, `female`, `neutral`. |
| `--poly` | Only PolyAI's own voices. |
| `--owner` | Only voices from the shared library (`global`), or only the account's own (`account`). |
| `--archived` | Include archived voices, and internal ones. |
| `--refresh` | Fetch the voices before listing, even if the saved copy is recent. |

`--json` output shape:

~~~json
{
  "success": true,
  "voices": [
    {
      "id": "VOICE-1a2b3c4d",
      "name": "Anne",
      "provider": "elevenlabs",
      "providerVoiceId": "abc123",
      "config": {},
      "metadata": {"accent": "en-GB", "gender": "female"},
      "isPolyVoice": true,
      "owner": "global"
    }
  ]
}
~~~

`owner` is `global` for the shared library and `account` for the account's own voices.

## `poly library voice show`

Show one voice's details: its provider, language, tags, recording and default settings.

Examples:

~~~bash
poly library voice show Anne
poly library voice show Pierre --language fr-CA
poly library voice show VOICE-1a2b3c4d --json
~~~

A name matches whatever its case and spacing. When more than one language has a voice with that name, pick one with `--language`, or give the voice ID.

| Argument | Description |
|---|---|
| `voice` | The voice's name, or its `VOICE-` ID. |

| Flag | Description |
|---|---|
| `--language` | The voice's language, for a name more than one language uses. |
| `--refresh` | Fetch the voices first, even if the saved copy is recent. |

`--json` output shape, with the voice in the same shape as one entry of [`poly library voice list`](#poly-library-voice-list):

~~~json
{
  "success": true,
  "voice": {
    "id": "VOICE-1a2b3c4d",
    "name": "Anne"
  }
}
~~~

## `poly library voice play`

Play a voice's recording through your speaker. Press Ctrl+C to stop.

Examples:

~~~bash
poly library voice play Anne
poly library voice play Pierre --language fr-CA
poly library voice play VOICE-1a2b3c4d --json
~~~

Playing needs the voice calling dependencies, the same ones as [`poly call`](./call.md). With `--json`, the command doesn't play anything. It returns the recording's URL instead, and exits with an error when the voice has no recording.

| Argument | Description |
|---|---|
| `voice` | The voice's name, or its `VOICE-` ID. |

| Flag | Description |
|---|---|
| `--language` | The voice's language, for a name more than one language uses. |
| `--refresh` | Fetch the voices first, even if the saved copy is recent. |

`--json` output shape:

~~~json
{
  "success": true,
  "voice_id": "VOICE-1a2b3c4d",
  "name": "Anne",
  "sample_voice_url": "https://..."
}
~~~

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
