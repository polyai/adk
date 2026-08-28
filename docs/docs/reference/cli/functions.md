---
title: poly functions
description: Reference for the `poly functions` command.
---

# `poly functions`

Run and validate Functions using the public Functions REST API, scoped to the project's current branch. `poly functions` requires a subcommand.

!!! note "Local files remain the source of truth"

    Creating, editing and deleting Functions is done via the local `functions/*.py` files synced by `poly pull`/`poly push` (see [Functions](../resources/functions.md)) — that mechanism already covers CRUD, including flow-scoped transition functions, function steps and latency control, and keeps changes reviewable in a branch diff before they're pushed. `poly functions` is additive: it covers what push/pull can't — running a function and validating it — via direct REST calls that don't touch local files.

Examples:

~~~bash
poly functions execute <function_name_or_id> --args '{"x": 1}'
poly functions validate
~~~

Every subcommand also accepts `--region`, `--project_id` and `--branch_id` directly, so `poly functions` can run headlessly (CI, scripts, or against a branch you haven't pulled locally) without a local project checkout:

~~~bash
poly functions execute <function_name_or_id> --region us-1 --project_id abc123 --branch_id main
~~~

All three must be given together — if any one is set, all three are required. With none set, the current local project's region/project/branch are used, as before.

## `poly functions execute`

Execute a Function and print its return value, logs and runtime.

Examples:

~~~bash
poly functions execute <function_name_or_id>
poly functions execute <function_name_or_id> --args '{"x": 1}'
~~~

| Argument | Description |
|---|---|
| `function` | The function's name or ID. Required. |

| Flag | Description |
|---|---|
| `--args` | JSON object of arguments to pass to the function. Defaults to `{}`. |

`--json` output shape:

~~~json
{
  "body": {},
  "logs": [],
  "runtime": 0
}
~~~

## `poly functions validate`

Check every Function on the current branch for syntax errors and orphaned flow-step references.

Examples:

~~~bash
poly functions validate
~~~

`--json` output shape:

~~~json
{
  "valid": true,
  "issues": []
}
~~~
