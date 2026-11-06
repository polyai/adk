---
title: poly pull
description: Reference for the `poly pull` command.
---

# `poly pull`

Pull the latest project configuration from Agent Studio.

Examples:

~~~bash
poly pull
poly pull --force
poly pull --format
poly pull --include-rtc
~~~

If the branch you are currently on no longer exists in Agent Studio, `poly pull` automatically switches to the `main` branch and displays a warning message with the new branch name.

| Flag | Description |
|---|---|
| `--force`, `-f` | Force pull the project, overwriting all local changes. |
| `--format` | Format resources after pulling. |
| `--include-rtc` | Also pull [Real-Time Configuration](./rtc.md) for all environments. |

`--json` output shape:

~~~json
{
  "success": true,
  "files_with_conflicts": []
}
~~~

`"new_branch_name"` and `"new_branch_id"` are added if the current branch no longer existed and the CLI switched to `main`. `"rtc"` is added when `--include-rtc` is passed, containing the result of the RTC pull.
