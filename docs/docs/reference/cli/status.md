---
title: poly status
description: Reference for the `poly status` command.
---

# `poly status`

Check the changed files of the project, comparing the local working tree against the last-synced remote version.

Examples:

~~~bash
poly status
poly status --path /path/to/project
~~~

Prints the account/project panel followed by any of: files with merge conflicts, new files, modified files, and deleted files. If none of these are present, it reports that no changes were detected.

`--json` output shape:

~~~json
{
  "account_name": "...",
  "project_name": "...",
  "files_with_conflicts": [],
  "modified_files": [],
  "new_files": [],
  "deleted_files": []
}
~~~

See also [`poly diff`](./diff.md) to inspect the actual content changes, and [`poly revert`](./revert.md) to discard them.
