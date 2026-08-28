---
title: poly functions
description: Reference for the `poly functions` command.
---

# `poly functions`

Run, validate, and inspect Functions using the public Functions REST API, scoped to the project's current branch. `poly functions` requires a subcommand.

!!! note "Local files remain the source of truth"

    Creating, editing and deleting Functions is done via the local `functions/*.py` files synced by `poly pull`/`poly push` (see [Functions](../resources/functions.md)) — that mechanism already covers CRUD, including flow-scoped transition functions, function steps and latency control, and keeps changes reviewable in a branch diff before they're pushed. `poly functions` is additive: it covers what push/pull can't — running a function, validating it, and inspecting its references — via direct REST calls that don't touch local files.

Examples:

~~~bash
poly functions execute <function_id> --args '{"x": 1}'
poly functions validate
poly functions references <function_id>
~~~

Every subcommand also accepts `--region`, `--project_id` and `--branch_id` directly, so `poly functions` can run headlessly (CI, scripts, or against a branch you haven't pulled locally) without a local project checkout:

~~~bash
poly functions execute <function_id> --region us-1 --project_id abc123 --branch_id main
~~~

All three must be given together — if any one is set, all three are required. With none set, the current local project's region/project/branch are used, as before.

## `poly functions execute`

Execute a Function and print its return value, logs and runtime.

Examples:

~~~bash
poly functions execute <function_id>
poly functions execute <function_id> --args '{"x": 1}'
~~~

| Argument | Description |
|---|---|
| `function_id` | The function ID. Required. |

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

## `poly functions references`

List the flow steps that call a Function.

!!! tip "Useful for a branch you haven't pulled"

    Because `--branch_id` can point at any branch, this is the easiest way to check a function's usage on a teammate's in-progress branch or staging — without switching to it or pulling it locally. If you're already on the branch in question, `find flows -name '<function_name>.py'` (function steps) or grepping for `{{fn:<function_name>}}` (global/transition functions) answers the same question against local files.

Examples:

~~~bash
poly functions references <function_id>
~~~

| Argument | Description |
|---|---|
| `function_id` | The function ID. Required. |

`--json` output shape:

~~~json
{
  "references": []
}
~~~

## `poly functions type-definitions`

Print the `Conversation`/`Flow` type stubs available to a Function, for IDE autocomplete.

Examples:

~~~bash
poly functions type-definitions <function_id>
poly functions type-definitions <function_id> > stubs.py
~~~

| Argument | Description |
|---|---|
| `function_id` | The function ID. Required. |

`--json` output shape:

~~~json
{
  "code": ""
}
~~~
