---
title: poly format
description: Reference for the `poly format` command.
---

# `poly format`

Run ruff (lint + format) on Python resources and formatting on YAML/JSON resources.

Examples:

~~~bash
poly format
poly format --path /path/to/project
poly format --check
~~~

By default, applies fixes: `ruff check --fix` and `ruff format` for Python, and in-process `ruamel.yaml`/stdlib formatting for YAML/JSON. Use `--check` to only verify without writing changes. Use `--ty` to also run type checking (via `ty`) after formatting.

| Flag | Description |
|---|---|
| `--files` | Specific files/dirs to format. If not specified, runs on the whole `--path` tree. |
| `--check` | Only check; do not write. Reports Python/YAML/JSON files that would be reformatted and exits non-zero if any are found. |
| `--ty` | Also run type checking (`ty`). Off by default because it can hang on some systems; times out after 15 seconds. |

`--json` output shape:

~~~json
{
  "success": true,
  "check_only": false,
  "format_errors": [],
  "affected": [],
  "ty_ran": false,
  "ty_returncode": null,
  "ty_timed_out": false
}
~~~

See also [`poly push --format`](./push.md) to run formatting automatically as part of a push, and [`poly validate`](./validate.md) to check project configuration.
