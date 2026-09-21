---
title: poly diff
description: Reference for the `poly diff` command.
---

# `poly diff`

Show the changes made to the project. With no arguments, compares the local project against the last-synced remote version.

Examples:

~~~bash
poly diff
poly diff sandbox
poly diff --before hash1 --after hash2
poly diff --files file1.yaml
~~~

The optional `hash` positional is a shorthand for `--after`: `poly diff sandbox` compares the previous version against the `sandbox` deployment (`pre-release` and `live` are also accepted, as is a specific version hash). Passing only `--before` compares that version against the current local project; passing only `--after` compares it against its immediately preceding version; passing both compares the two named versions or branches directly.

| Argument | Description |
|---|---|
| `hash` | Hash (or deployment name) of the version to compare against. If not specified, it's inferred from `--before`/`--after`. |

| Flag | Description |
|---|---|
| `--files` | List of files to show changes for. If not specified, shows all changed files. |
| `--before` | Name of the original branch or version to compare with. If specified without `--after`, compares against the current local project. |
| `--after` | Name of the branch or version to compare against. If specified without `--before`, compares against its previous version. |

!!! info "`hash` vs. `--before`/`--after`"

    The `hash` positional and `--before`/`--after` are mutually exclusive — passing both errors out.

`--json` output shape:

~~~json
{
  "success": true,
  "diffs": {
    "path/to/file.yaml": "diff text..."
  }
}
~~~

When there are no changes to show, this becomes `{"success": false, "message": "No changes detected"}`.

See also [`poly status`](./status.md) for a summary of what changed, [`poly review`](./review.md) to generate a GitHub Gist of the changes and [`poly revert`](./revert.md) to discard changes.
