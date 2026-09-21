---
title: poly branch
description: Reference for the `poly branch` command.
---

# `poly branch`

Manage project branches. `poly branch` requires a subcommand:

Examples:

~~~bash
poly branch list
poly branch create my-feature
poly branch switch my-feature
poly branch current
poly branch merge 'Merge feature branch'
poly branch delete
~~~

## `poly branch list`

List all branches in the project.

Examples:

~~~bash
poly branch list
poly branch list --archived
~~~

| Flag | Description |
|---|---|
| `--archived` | Show soft-deleted (archived) branches instead of active ones. |

`--json` output shape:

~~~json
{
  "current_branch": "my-feature",
  "branches": {
    "main": { "branchId": "..." },
    "my-feature": { "branchId": "...", "parentBranchId": "..." }
  }
}
~~~

With `--archived`, the shape is `{ "archived_branches": [...] }` instead.

## `poly branch current`

Show the current branch, and its parent branch if it isn't `main`.

Examples:

~~~bash
poly branch current
~~~

`--json` output shape:

~~~json
{ "current_branch": "my-feature", "parent_branch": "main" }
~~~

If your local checkout doesn't match a branch that still exists in Agent Studio (it may have been deleted or merged), both fields are `null`.

## `poly branch create`

Create a new branch, sourced from your current branch by default. In the standard deployment mode, a new branch can only be sourced from `main` — if you aren't currently on `main`, switch there first or pass `--from main` explicitly.

Examples:

~~~bash
poly branch create my-feature
poly branch create my-hotfix --env live
poly branch create my-hotfix --env live --force
poly branch create my-feature --from other-branch
~~~

| Argument | Description |
|---|---|
| `branch_name` | Name of the branch to create. Prompted for if omitted — required when `--json` is used. |

| Flag | Description |
|---|---|
| `--env`, `--environment` | Source the new branch from a deployed environment snapshot instead of `main`. Choices: `sandbox`, `pre-release`, `live`. |
| `--from BRANCH` | Source the new branch from a different existing branch instead of your current one. In the standard deployment mode, `main` is the only valid value. |
| `--force`, `-f` | Create the branch even if there are uncommitted local changes on `main`. |

When `--env live` or `--env pre-release` is specified:

- the version of the deployed environment is pulled into your local workspace
- the new branch is created
- that version is immediately pushed to the new branch, leaving a clean slate for hotfix changes
- if there are local changes, the command fails unless `--force` is also passed

!!! warning "Use `--env live` with caution"

    Branching from a live deployment snapshot overwrites your local project with the live state. Merging this branch back to main may roll back changes introduced after the snapshot was taken.


`--json` output shape:

~~~json
{
  "success": true,
  "base_branch_id": "...",
  "base_branch_name": "main",
  "new_branch_id": "...",
  "branch_name": "my-feature"
}
~~~

## `poly branch switch`

Switch to a different branch. Omit `branch_name` for an interactive picker.

Examples:

~~~bash
poly branch switch my-feature
poly branch switch my-feature --force
poly branch switch my-feature --format
~~~

| Argument | Description |
|---|---|
| `branch_name` | Name of the branch to switch to. Shown as an interactive picker if omitted — required when `--json` is used. |

| Flag | Description |
|---|---|
| `--force`, `-f` | Switch even if there are uncommitted local changes, discarding them. |
| `--format` | Format the project after switching. |
| `--output-json-projection` | Include the full post-switch projection in the `--json` output. |

`--json` output shape:

~~~json
{ "success": true, "branch_name": "my-feature" }
~~~

With `--output-json-projection`, a `"projection"` key containing the full project projection is added.

## `poly branch rename`

Rename the current branch. `main` cannot be renamed.

Examples:

~~~bash
poly branch rename new-name
~~~

| Argument | Description |
|---|---|
| `new_branch_name` | New name for the current branch. Prompted for if omitted — required when `--json` is used. |

`--json` output shape:

~~~json
{ "success": true, "old_branch_name": "my-feature", "new_branch_name": "renamed-feature" }
~~~

## `poly branch delete`

Interactively select and delete one or more branches. `main` cannot be deleted.

- Run without arguments to open an interactive checkbox prompt for selecting branches to delete.
- Pass a branch name directly to skip the interactive prompt and delete that branch after confirmation.

Examples:

~~~bash
poly branch delete
poly branch delete my-feature
~~~

| Argument | Description |
|---|---|
| `branch_name` | Name of the branch to delete directly, skipping the interactive picker. Deleting still asks for confirmation unless `--json` is used. |

`--json` output shape — single branch:

~~~json
{ "success": true, "switched_to": "main" }
~~~

`"switched_to"` is only present when the deleted branch was your current branch. Multi-select delete (no `branch_name`) reports a count instead:

~~~json
{ "success": true, "deleted": 2, "switched_to": "main" }
~~~

## `poly branch restore`

Restore a soft-deleted branch from the archive. Archived branch names aren't unique, so restoring by ID is required in non-interactive use — find IDs with [`poly branch list --archived`](#poly-branch-list).

Examples:

~~~bash
poly branch restore
poly branch restore <branch_id>
~~~

| Argument | Description |
|---|---|
| `branch_id` | ID of the archived branch to restore. Shown as an interactive picker if omitted — required when `--json` is used. |

`--json` output shape:

~~~json
{ "success": true, "branch_id": "..." }
~~~

## `poly branch merge`

Merge the current branch into its parent (`main`, unless you branched from another branch). A message is required when merging into `main`.

Examples:

~~~bash
poly branch merge 'Merge message'
poly branch merge 'Merge message' --interactive
poly branch merge 'Merge message' --resolutions resolutions.json
~~~

If the merge has no conflicts, it completes immediately and the CLI switches your local checkout to the parent branch.

| Argument | Description |
|---|---|
| `message` | Merge commit message. Required when merging into `main`; quote it if it contains spaces. |

| Flag | Description |
|---|---|
| `--interactive`, `-i` | Resolve conflicts in an interactive prompt. Set `$EDITOR` or `$VISUAL` for free-form edits during resolution. Cannot be combined with `--json`. |
| `--resolutions <source>` | Pre-defined resolutions as a JSON file path, inline JSON string, or `-` for stdin. |
| `--force`, `-f` | Skip the confirmation prompt shown when merging to `main` would deploy directly to a live environment. |

`--json` output shape:

~~~json
{ "success": true }
~~~

On conflict or error, `"conflicts"` and/or `"errors"` arrays are added and the process exits non-zero.

### Conflicts

If the merge has conflicts, the command prints a conflict table and exits non-zero. The table shows, per conflicting field:

- **Path** — the resource and field that conflicts (for example `topics > Booking > content`)
- **Base / Ours / Theirs** — the original value and the two competing values
- **Auto-merged value** — what the ADK would produce by line-merging both sides
- **Auto-mergeable** — whether the auto-merged value contains any unresolved markers

If every conflict is auto-mergeable and you want to accept it, re-run with `--interactive` and accept the suggestions, or pre-populate `--resolutions` with the auto-merge values.

#### `--interactive` / `-i`

Interactive mode walks through each conflict and asks how to resolve it. For every conflict you can:

- accept the auto-merge (when available)
- pick `main` (`ours`)
- pick the branch (`theirs`)
- pick `base` (revert to the original value)
- open the value in `$EDITOR`/`$VISUAL` for free-form editing

After every conflict is answered, the merge is re-attempted automatically.

!!! tip "Set `$EDITOR` or `$VISUAL` before starting an interactive merge"

    Interactive mode shells out to your editor for multiline or long values, falling back to `vi` if neither variable is set. `EDITOR="code --wait"` (or your editor of choice) makes this much smoother.

#### `--resolutions <source>`

Supply pre-defined resolutions non-interactively. The source can be a JSON file path, a literal JSON string, or `-` to read from stdin. Combine with `--interactive` to seed a session — pre-defined choices apply automatically and you're only prompted for the conflicts they don't cover.

Resolution file format — a JSON array of objects:

~~~json
[
  { "path": ["topics", "Booking", "content"], "strategy": "theirs" },
  { "path": ["agent_settings", "rules", "value"], "strategy": "theirs", "value": "Custom resolved content here" },
  { "path": ["flows", "main_flow", "steps", "greet", "prompt"], "strategy": "ours" }
]
~~~

| Field | Description |
|---|---|
| `path` | List of strings identifying the conflicted field. Match the `Path` column from the conflict table. |
| `strategy` | One of `"ours"` (keep parent), `"theirs"` (keep the branch), or `"base"` (revert to the original). |
| `value` | Optional custom value. Only honored with the `"theirs"` strategy. |

Run `poly branch merge` once to surface conflicts, then write a resolutions file addressing each `path` row.

### Merging through the Agent Studio web UI

Switching to the branch and clicking **Merge** in the Agent Studio UI hits the same platform endpoint as `poly branch merge` — the result is identical either way.

## `poly branch diff`

Show changes made on a branch since it was created — its own local-vs-remote analogue is [`poly diff`](./diff.md).

Examples:

~~~bash
poly branch diff
poly branch diff my-feature
poly branch diff --files topics/booking.yaml
~~~

| Argument | Description |
|---|---|
| `branch_name` | Branch to diff. Defaults to the current branch. |

| Flag | Description |
|---|---|
| `--files [FILES ...]` | Only show changes for these files. |

`--json` output shape:

~~~json
{ "success": true, "diffs": { "topics/booking.yaml": "..." } }
~~~

## `poly branch review`

Create a GitHub Gist of the changes on a branch since it was created — the branch-scoped analogue of [`poly review create`](./review.md).

Examples:

~~~bash
poly branch review
poly branch review my-feature
poly branch review --files topics/booking.yaml
~~~

| Argument | Description |
|---|---|
| `branch_name` | Branch to review. Defaults to the current branch. |

| Flag | Description |
|---|---|
| `--files [FILES ...]` | Only include changes for these files. |

`--json` output shape:

~~~json
{ "success": true, "link": "https://gist.github.com/..." }
~~~

## `poly branch status`

Show a branch's status relative to its fork point — parent branch, who created it, whether it's diverged, and its changed files. The branch-scoped analogue of [`poly status`](./status.md).

Examples:

~~~bash
poly branch status
poly branch status my-feature
~~~

| Argument | Description |
|---|---|
| `branch_name` | Branch to check. Defaults to the current branch. |

`--json` output shape:

~~~json
{
  "branch": "my-feature",
  "parent_branch": "main",
  "created_by": "user@example.com",
  "is_diverged": false,
  "new_files": [],
  "modified_files": ["topics/booking.yaml"],
  "deleted_files": []
}
~~~

## `poly branch history`

Show the branches that has been merged into the current branch. Long listings are automatically paged through the system pager when stdout is a TTY; output piped to a file or another command is never paged.

Examples:

~~~bash
poly branch history
poly branch history --branch-name my-feature
poly branch history --limit 20
~~~

| Flag | Description |
|---|---|
| `--branch-name`, `-b` | Branch to show history for. Defaults to the current branch. |
| `--limit` | Maximum number of history entries to show. Shows all by default. |

`--json` output shape:

~~~json
{ "branch_name": "my-feature", "branch_id": "...", "history": [] }
~~~

## Related pages

- [Working locally](../../development/working-locally.md) — where branching fits in the edit → push → merge loop
- [Branches, push, and pull](../../development/branches-push-pull.md) — the merge conflict model and team habits around branching
