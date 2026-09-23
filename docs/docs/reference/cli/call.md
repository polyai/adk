---
title: poly call
description: Reference for the `poly call` command.
noindex: true
---

# `poly call`

Start an interactive voice call with your agent using your microphone and speaker — the spoken sibling of [`poly chat`](./chat.md). Only draft/branch calls are supported: switch to a non-main branch, push your changes, then call the draft build.

Examples:

~~~bash
poly call
poly call --push
poly call --variant my-variant
poly call --no-echo-cancellation
~~~

The call connects your local audio to the agent over WebRTC. Speak to talk to the agent; press `Ctrl+C` to hang up. When the call ends, the command prints a link to the conversation in Agent Studio so you can review the transcript, function calls, and audio.

Calling is only available against the current branch's **draft** build, so you must be on a non-main branch. On `main` (or with no branch) the command exits with an error.

#### Pushing before calling

Use `--push` to push the local project to Agent Studio before the call, so the draft build reflects your latest local changes without a separate `poly push` step:

~~~bash
poly call --push
~~~

If the push fails, the command exits without starting the call.

#### Echo cancellation

On a laptop **speaker**, the agent's own speech can be picked up by your microphone and sent back, making the agent hear itself and interrupt its own turn. Echo cancellation (WebRTC AEC3, the same canceller browsers use) is **on by default** to prevent this. Disable it with `--no-echo-cancellation`:

~~~bash
poly call --no-echo-cancellation
~~~

If the echo-cancellation library can't be loaded, the call continues without it and prints a warning rather than failing.

!!! tip "Headphones are the zero-echo fallback"
    Software echo cancellation is strong but not perfect under heavy mic/speaker drift. Headphones remove the echo path entirely — use them if you still hear the agent interrupting itself.

#### `poly call` flags summary

| Flag | Description |
|---|---|
| `--environment`, `-e` | Environment to call. Only `draft` (the current branch) is currently supported. |
| `--variant` | Name of the variant to use for the call. |
| `--push` | Push the project before starting the call. |
| `--echo-cancellation` / `--no-echo-cancellation` | Toggle acoustic echo cancellation. On by default; use `--no-echo-cancellation` to disable. |
