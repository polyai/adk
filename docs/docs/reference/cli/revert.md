---
title: poly revert
description: Reference for the `poly revert` command.
---

# `poly revert`

Revert local changes back to the last known remote state.

Examples:

~~~bash
poly revert
poly revert file1.yaml file2.yaml
~~~

With no arguments, reverts every local change in the working tree; pass file paths to revert only those files.

| Argument | Description |
|---|---|
| `files` | List of files to revert. If not specified, reverts all changes. |

!!! warning "Reverting cannot be undone"

    Reverting discards local edits with no way to recover them — run [`poly diff`](./diff.md) or [`poly status`](./status.md) first if you're unsure what will be lost.

`--json` output shape:

~~~json
{
  "success": true,
  "files_reverted": []
}
~~~
