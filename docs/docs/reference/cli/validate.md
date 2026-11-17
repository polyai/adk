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

`--json` output shape:

~~~json
{
  "success": true,
  "valid": true,
  "errors": []
}
~~~

When there are validation errors the command exits non-zero, with or without `--json`.
