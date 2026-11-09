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

Function code is checked across the whole project with [ty](https://docs.astral.sh/ty/), which ships with the ADK. Each import of another function file in the project must resolve to a file and a name that exist, and syntax is checked against Python 3.14, the version the platform runs. Imports of packages the platform provides, which aren't installed locally, aren't checked. If ty can't run, each function is compiled with the Python running the ADK instead.

`--json` output shape:

~~~json
{
  "valid": true,
  "errors": []
}
~~~
