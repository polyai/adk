---
title: poly push
description: Reference for the `poly push` command.
---

# `poly push`

Push local changes to Agent Studio to the current branch. If you are on the main branch, it will automatically create a new branch.

Before pushing, it will pull and merge the remote changes. If any merge conflicts appear it will stop you from pushing.

Examples:

~~~bash
poly push
poly push --dry-run
poly push --skip-validation
poly push --force
poly push --format
poly push --include-rtc --rtc-env live
~~~

| Flag | Description |
|---|---|
| `--force`, `-f` | Force push the project, overwriting remote changes. |
| `--skip-validation` | Skip validation of the project before pushing. |
| `--dry-run` | Perform a dry run of the push without actually sending changes. |
| `--format` | Run [`poly format`](./format.md) over the project before pushing. |
| `--include-rtc` | Also push [Real-Time Configuration](./rtc.md). Defaults to the `sandbox` environment; use `--rtc-env` to override. |
| `--rtc-env` | RTC environment to push to. Requires `--include-rtc`. Choices: `sandbox`, `pre-release`, `live`. Defaults to `sandbox`. |

!!! info "`--rtc-env` without `--include-rtc`"

    Passing `--rtc-env` without `--include-rtc` has no effect — the CLI prints a warning and pushes normally without touching RTC.

`--json` output shape:

~~~json
{
  "success": true,
  "message": "...",
  "dry_run": false
}
~~~

`"switched_to"` and `"new_branch_id"` are added if pushing from `main` created and switched to a new branch. `"rtc"` is added when `--include-rtc` is passed, containing the result of the RTC push.
