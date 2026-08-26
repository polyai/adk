---
title: poly review
description: Reference for the `poly review` command.
---

# `poly review`

Create a GitHub Gist of Agent Studio project changes to share for review. `poly review` requires a subcommand.

Examples:

~~~bash
poly review create
poly review create --before main --after feature-branch
poly review list
poly review delete
~~~

## `poly review create`

Create a review gist comparing project versions. With no arguments, it compares your local project against the remote version (local vs remote). Pass a positional version hash to compare that version against the current remote. Pass `--before` and `--after` to compare two branches or versions directly — the syntax matches the [`poly diff` command](diff.md).

Examples:

~~~bash
poly review create
poly review create version-hash-1
poly review create --before main --after feature-branch
poly review create --before sandbox --after live
poly review create --before version-hash-1 --after version-hash-2
~~~

The gist is created privately on GitHub, with one `.diff` file per changed resource file.

| Argument | Description |
|---|---|
| `hash` | Version hash to compare against the current remote. Omit to use `--before`/`--after` instead. |

| Flag | Description |
|---|---|
| `--before` | Name of the original branch or version to compare from. |
| `--after` | Name of the branch or version to compare to. |
| `--files` | List of specific files to show changes for. If omitted, shows all changed files. |

`--json` output shape:

~~~json
{ "success": true, "link": "https://gist.github.com/..." }
~~~

On failure (no changes to review, or a GitHub API/network error):

~~~json
{ "success": false, "message": "..." }
~~~

## `poly review list`

Interactively select a review gist and open it in the browser.

Examples:

~~~bash
poly review list
~~~

!!! info "`--json` skips the browser prompt"

    With `--json`, the gist list is printed instead of opening the interactive picker.

`--json` output shape is a JSON array (not an object) of gist entries:

~~~json
[
  {
    "id": "...",
    "description": "Poly ADK: account/project: local → remote",
    "created_at": "2024-01-01T00:00:00Z",
    "html_url": "https://gist.github.com/..."
  }
]
~~~

On a GitHub API/network error, it falls back to the standard `{ "success": false, "message": "..." }` object.

## `poly review delete`

Interactively select and delete one or more review gists. Use `--id` to delete a specific gist directly without an interactive prompt.

Examples:

~~~bash
poly review delete
poly review delete --id GIST_ID
poly review delete --json
~~~

| Flag | Description |
|---|---|
| `--id` | Gist ID (or its first 7 characters) to delete directly, skipping the interactive prompt. |

Without `--id`, an interactive checkbox prompt runs to select gists.

!!! info "`--json` requires `--id`"

    When using `--json`, you must supply `--id` explicitly. The interactive checkbox prompt is not available in JSON mode, so omitting `--id` returns a JSON error instead of prompting.

`--json` output shape:

~~~json
{ "success": true }
~~~

On error (for example, when `--id` is omitted with `--json`):

~~~json
{ "success": false, "error": "Please provide a gist ID to delete when using JSON output." }
~~~
