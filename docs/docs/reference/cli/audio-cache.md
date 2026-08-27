---
title: poly audio-cache
description: Reference for the `poly audio-cache` command.
---

# `poly audio-cache`

Manage an agent's cached TTS audio entries using the public Audio Cache API. `poly audio-cache` requires a subcommand:

Examples:

~~~bash
poly audio-cache list
poly audio-cache get-file <entry_id> -o cached.wav
poly audio-cache update-file <entry_id> --file replacement.wav
poly audio-cache synthesize <entry_id> --text "Hello there" -o preview.wav
poly audio-cache delete <entry_id>
poly audio-cache bulk-delete --ids id1,id2,id3
~~~

## `poly audio-cache list`

List cached TTS audio entries with metadata (transcript, provider, voice, duration, hit count).

Examples:

~~~bash
poly audio-cache list
poly audio-cache list --limit 20 --offset 10
poly audio-cache list --sort hit_count:desc
~~~

| Flag | Description |
|---|---|
| `--limit` | Max number of entries to return (1-200). Defaults to `50`. |
| `--offset` | Number of entries to skip. Defaults to `0`. |
| `--sort` | Sort expression, e.g. `hit_count:desc` or `duration:asc`. |

`--json` output shape:

~~~json
{
  "entries": [],
  "total_count": 0
}
~~~

## `poly audio-cache get-file`

Download the cached WAV audio file for a cache entry.

Examples:

~~~bash
poly audio-cache get-file <entry_id>
poly audio-cache get-file <entry_id> -o cached.wav
~~~

| Argument | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |

| Flag | Description |
|---|---|
| `-o`, `--output` | Output file path. Defaults to `<entry_id>.wav`. |

`--json` output shape:

~~~json
{
  "success": true,
  "entry_id": "...",
  "output_path": "...",
  "size_bytes": 0
}
~~~

## `poly audio-cache update-file`

Replace the audio file for an existing cache entry. Maximum file size is 6MB.

Examples:

~~~bash
poly audio-cache update-file <entry_id> --file replacement.wav
poly audio-cache update-file <entry_id> --file replacement.wav --filename clip.wav
~~~

| Argument | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |

| Flag | Description |
|---|---|
| `--file` | Path to the local replacement WAV file. Required. |
| `--filename` | Filename to record for the uploaded audio. Defaults to the local file's basename. |

`--json` output shape:

~~~json
{
  "success": true,
  "entry_id": "...",
  "size_bytes": 0
}
~~~

## `poly audio-cache update-details`

Replace both the audio file and voice tuning settings for a cache entry in one call. Maximum file size is 6MB.

Examples:

~~~bash
poly audio-cache update-details <entry_id> --file replacement.wav --text "Hi there"
poly audio-cache update-details <entry_id> --file replacement.wav --text "Hi" --config '{"stability": 0.5}'
~~~

| Argument | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |

| Flag | Description |
|---|---|
| `--file` | Path to the local replacement WAV file. Required. |
| `--text` | Transcript text associated with the audio. Required. |
| `--config` | JSON object of provider-specific voice tuning settings (e.g. `stability`, `speed`, `model_id`). Defaults to `{}`. |

`--json` output shape:

~~~json
{
  "success": true,
  "entry_id": "...",
  "size_bytes": 0
}
~~~

## `poly audio-cache delete`

Permanently delete a cached audio entry and its audio file.

Examples:

~~~bash
poly audio-cache delete <entry_id>
~~~

| Argument | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |

`--json` output shape:

~~~json
{
  "success": true
}
~~~

## `poly audio-cache bulk-delete`

Delete multiple audio cache entries in a single request. Best-effort — reports which IDs succeeded and which failed, so partial failures can be retried. Maximum 20 IDs per request.

Examples:

~~~bash
poly audio-cache bulk-delete --ids id1,id2,id3
~~~

| Flag | Description |
|---|---|
| `--ids` | Comma-separated list of audio cache entry IDs to delete (max 20). Required. |

`--json` output shape:

~~~json
{
  "deleted": [],
  "failed": []
}
~~~

## `poly audio-cache synthesize`

Generate a TTS audio preview using an existing cache entry's voice and provider configuration, without saving it to the cache.

Examples:

~~~bash
poly audio-cache synthesize <entry_id> --text "Hello there"
poly audio-cache synthesize <entry_id> --text "Hi" --language en-US -o out.wav
~~~

| Argument | Description |
|---|---|
| `entry_id` | The audio cache entry ID whose voice/provider config to preview with. Required. |

| Flag | Description |
|---|---|
| `--text` | Text to synthesize. Required. |
| `--config` | JSON object of provider-specific voice tuning settings. Defaults to `{}`. |
| `--language` | BCP-47 language tag, e.g. `en-US`. |
| `-o`, `--output` | Output file path. Defaults to `<entry_id>-preview.wav`. |

`--json` output shape:

~~~json
{
  "success": true,
  "entry_id": "...",
  "output_path": "...",
  "size_bytes": 0
}
~~~

## Related pages

- [Audio caching](../../development/audio-caching.md) — the hit-count-driven workflow this command group supports
