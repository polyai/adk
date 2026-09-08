---
title: poly functions
description: Reference for the `poly functions` command.
---

# `poly functions`

Run and validate Functions using the public Functions REST API, scoped to the project's current branch. `poly functions` requires a subcommand.

This isn't where the push/pull Functions mechanism lives (see [Functions](../resources/functions.md)). `poly functions` covers `execute` (run a function by name or ID) and `validate` (check functions for syntax errors and orphaned references).

Examples:

~~~bash
poly functions execute <function_name> --args '{"x": 1}'
poly functions validate
~~~

Every subcommand also accepts `--region`, `--project_id` and `--branch_id` directly, so `poly functions` can run headlessly (CI, scripts, or against a branch you haven't pulled locally) without a local project checkout:

~~~bash
poly functions execute <function_name> --region us-1 --project_id abc123 --branch_id main
~~~

All three must be given together — if any one is set, all three are required. With none set, the current local project's region/project/branch are used, as before.

## `poly functions execute`

Execute a Function and print its return value, logs and runtime.

Examples:

~~~bash
poly functions execute <function_name>
poly functions execute <function_name> --args '{"x": 1}'
~~~

Each run builds a real `conv` object from the branch's config, but it's a fresh one with no live caller and no prior state — not a way to attach to an actual call.

**Does not work this way**

~~~bash
poly functions execute my_function --conv <call_id>
~~~

There's no `--conv` flag. `conv.state` starts empty every run and isn't persisted between runs; calls like `conv.say(...)`, `conv.goto_flow(...)`, or `conv.call_handoff(...)` have no live channel to act on — only the returned `body`, `logs`, and `runtime` reflect what happened.

Covers global functions only, not flow-scoped transition functions or function steps.

| Argument | Description |
|---|---|
| `function` | The function's name or ID. Required. |

| Flag | Description |
|---|---|
| `--args` | JSON object of arguments to pass to the function. Defaults to `{}`. |

!!! info "Unknown function name or ID"

    If no function on the branch matches, the command exits with an error message rather than a traceback.

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
