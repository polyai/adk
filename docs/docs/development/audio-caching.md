---
title: Audio caching
description: How cached TTS audio works in Agent Studio, and how to inspect, retune, and replace what callers actually hear.
---

# Audio caching

When the agent says the same thing twice, the audio is not synthesized twice. Agent Studio caches TTS output, so a phrase like a greeting or a hold message is generated once and replayed after that. This keeps repeated lines fast and identical every time.

The cache is a property of the deployed agent rather than something in your project files, so you work with it through `poly audio-cache` rather than by editing a resource.

Each entry carries its transcript, the provider and voice that produced it, the duration, and a **hit count** — how many times it has been played.

## Start from hit count

Hit count is what makes the cache worth looking at. It tells you which lines callers actually hear, which is rarely the same as which lines you spent the most time writing.

~~~bash
poly audio-cache list --sort hit_count:desc
~~~

A greeting played on every call deserves attention that a rare edge-case line does not. Working down from the top of that list is the difference between improving what callers experience and improving something almost nobody hears.

Download an entry to listen to it:

~~~bash
poly audio-cache get-file <entry_id> -o cached.wav
~~~

## Preview before you commit

`poly audio-cache synthesize` generates a preview using an existing entry's voice and provider configuration **without saving anything to the cache**. It is the safe way to try a different reading or a different tuning setting.

~~~bash
poly audio-cache synthesize <entry_id> --text "Hello there" -o preview.wav
~~~

Iterate here until the audio is right, then write it back. Doing it the other way round means churning live cache entries while you experiment.

## Improve an entry

Two ways to change what an entry plays:

- **`update-file`** replaces just the audio — the route for substituting a recording produced elsewhere, including a human one.
- **`update-details`** replaces the audio together with the transcript and provider-specific voice tuning settings, so the entry and its metadata stay consistent.

Uploaded audio must be WAV and at most 6MB.

Deleting an entry is how you get back to generated audio — the phrase is synthesized again from current settings the next time it is needed.

~~~bash
poly audio-cache delete <entry_id>
poly audio-cache bulk-delete --ids id1,id2,id3
~~~

`bulk-delete` handles up to 20 IDs and is best-effort: it reports which succeeded and which failed rather than failing as a whole.

!!! tip "Delete to pick up new voice settings"

    Changing voice settings does not retroactively rewrite audio that is already cached. If you have retuned a voice and want an existing phrase to reflect it, delete the entry and let it regenerate.

Every flag for these commands is in the [CLI reference](../reference/cli/audio-cache.md).
