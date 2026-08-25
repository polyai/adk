---
title: poly rtc
description: Reference for the `poly rtc` command.
---

# `poly rtc`

Manage Real-Time Configuration (RTC) — per-environment configuration that takes effect without a deployment. `poly rtc` requires a subcommand.

Each environment holds a **schema**, which defines the shape of the configuration, and **data**, which holds the values. Locally these live in `real_time_configuration/`, one directory per environment:

| Environment | Directory |
|---|---|
| `sandbox` | `real_time_configuration/draft_and_sandbox/` |
| `pre-release` | `real_time_configuration/pre_release/` |
| `live` | `real_time_configuration/live/` |

Each directory contains `schema.json` and `data.json`.

## `poly rtc pull`

Pull RTC from Agent Studio and write it to local files.

Examples:

~~~bash
poly rtc pull
poly rtc pull --env sandbox
poly rtc pull --env all
poly rtc pull --env sandbox --schema
~~~

| Flag | Description |
|---|---|
| `--env` | Environment to pull. Choices: `sandbox`, `pre-release`, `live`, `all`. Defaults to `all`. |
| `--schema` | Pull the schema only. Mutually exclusive with `--data`. |
| `--data` | Pull the data only. Mutually exclusive with `--schema`. |

`--json` output shape:

~~~json
{
  "success": true,
  "files_written": [
    {
      "environment": "sandbox",
      "schema_file": "real_time_configuration/draft_and_sandbox/schema.json",
      "data_file": "real_time_configuration/draft_and_sandbox/data.json"
    }
  ]
}
~~~

## `poly rtc push`

Push RTC from local files to Agent Studio. `--env` is required — there is no default.

Examples:

~~~bash
poly rtc push --env sandbox
poly rtc push --env sandbox --schema
poly rtc push --env live --force
~~~

| Flag | Description |
|---|---|
| `--env` | **Required.** Environment to push to. Choices: `sandbox`, `pre-release`, `live`. |
| `--force` | Skip the drift check and confirmation prompt, overwriting the remote state. |
| `--no-merge` | Fail with an error on drift instead of merging automatically. |
| `--skip-validation` | Skip schema validation before pushing. |
| `--schema` | Push the schema only. Mutually exclusive with `--data`. |
| `--data` | Push the data only. Mutually exclusive with `--schema`. |

!!! warning "A push to `live` takes effect immediately"

    RTC is not branched and not promoted through the deployment ladder. `poly rtc push --env live` writes straight to production.

### Drift behavior

If the remote has changed since your last pull, the configuration has drifted. By default the ADK performs a three-way merge between the stored base, your local files, and the remote state, **per key** rather than per line. A key changed on only one side applies cleanly; a key changed differently on both sides is a conflict, and conflicts abort the push.

Drift protection depends on base copies stored by `poly rtc pull`. Pushing without ever having pulled skips the check.

`--json` output shape:

~~~json
{
  "success": true,
  "environment": "sandbox",
  "schema_file": "real_time_configuration/draft_and_sandbox/schema.json",
  "data_file": "real_time_configuration/draft_and_sandbox/data.json"
}
~~~

## `poly rtc edit`

Pull the current configuration, open it in your editor, validate it, and push it back in one step. Edits `data.json` unless `--schema` is passed.

Examples:

~~~bash
poly rtc edit --env sandbox
poly rtc edit --env sandbox --schema
~~~

| Flag | Description |
|---|---|
| `--env` | **Required.** Environment to edit. Choices: `sandbox`, `pre-release`, `live`. |
| `--schema` | Edit the schema instead of the data. |
| `--force` | Skip the confirmation prompt when editing `live`. |

The file opens with `$EDITOR` or `$VISUAL`. Closing the editor without changes cancels the operation. Before pushing, the remote state is re-checked, so a change made elsewhere while you were editing is caught rather than overwritten — the push fails rather than merging.

!!! info "No `--json` support"

    `poly rtc edit` is inherently interactive (it opens an editor) and does not accept `--json`.

## `poly rtc diff`

Show differences between local and remote RTC configuration.

Examples:

~~~bash
poly rtc diff
poly rtc diff --env sandbox
~~~

| Flag | Description |
|---|---|
| `--env` | Environment to diff. Choices: `sandbox`, `pre-release`, `live`, `all`. Defaults to `all`. |

`--json` output shape:

~~~json
{
  "success": true,
  "diffs": [
    {
      "environment": "sandbox",
      "schema": [],
      "data": []
    }
  ]
}
~~~

An environment with no local files reports `{"environment": "sandbox", "status": "no_local_files"}` instead.

## `poly rtc validate`

Validate local `data.json` against `schema.json` for each environment. `poly rtc push` runs the same validation unless `--skip-validation` is passed.

Examples:

~~~bash
poly rtc validate
poly rtc validate --env sandbox
~~~

| Flag | Description |
|---|---|
| `--env` | Environment to validate. Choices: `sandbox`, `pre-release`, `live`, `all`. Defaults to `all`. |

`--json` output shape:

~~~json
{
  "success": true,
  "results": [
    {
      "environment": "sandbox",
      "valid": true
    }
  ]
}
~~~

An environment missing local files reports `{"environment": "sandbox", "status": "skipped"}` instead. A failed validation adds `"errors": []` alongside `"valid": false`.

## Related pages

- [Real-time configuration](../../development/real-time-configuration.md) — how RTC fits the development workflow
