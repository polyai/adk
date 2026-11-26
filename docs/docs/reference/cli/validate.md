---
title: poly validate
description: Reference for the `poly validate` command.
---

# `poly validate`

Validate the project's configuration locally.

Examples:

~~~bash
poly validate
poly validate --path /path/to/project
~~~

Returns a list of validation errors for the whole project. These indicate project misconfiguration that will either be rejected on [`poly push`](./push.md) or break the project's runtime behavior.

Imports between function files are checked across the whole project with [ty](https://docs.astral.sh/ty/), which ships with the ADK. Each import of another function file in the project must resolve to a file and a name that exist. In a flow's functions, `from ..helper import x` resolves to the global `functions/helper.py`, as it does on the platform. Imports of packages the platform provides aren't checked, since they aren't installed locally, and neither are imports inside a `try` that catches `ImportError` or under `if TYPE_CHECKING:`.

`--json` output shape:

~~~json
{
  "success": true,
  "valid": true,
  "errors": []
}
~~~

When there are validation errors the command exits non-zero, with or without `--json`.
