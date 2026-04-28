---
title: Branch merging
description: Merge ADK branches into main from the CLI, including conflict resolution flows.
---

# Branch merging

<p class="lead">
Merge a feature branch back into <code>main</code> with <code>poly branch merge</code>, including interactive and pre-defined conflict resolution.
</p>

`poly branch merge` is the CLI-native counterpart to merging in the Agent Studio web UI. It brings everything you've changed on the current branch back onto `main`, surfaces any conflicts in a structured table, and lets you resolve them either interactively or from a JSON file.

For the broader branching workflow (creating, switching, listing, deleting branches), see the [`poly branch` section of the CLI reference](./cli.md#poly-branch). For the team-level guardrails around branching and merging, see [Multi-user workflows and guardrails](../concepts/multi-user-and-guardrails.md).

## When to use it

You'll typically reach for `poly branch merge` at the end of a feature loop:

1. Create a branch with `poly branch create my-feature` (see [`poly branch create`](./cli.md#poly-branch-create)).
2. Iterate locally, pushing with `poly push` (see [Working locally](../concepts/working-locally.md)).
3. Test with `poly chat` against the branch's pushed state.
4. Merge back to `main` with `poly branch merge '<message>'` — described on this page.
5. Optionally deploy through Agent Studio.

You can also merge from the Agent Studio web UI by switching to the branch and clicking **Merge**. The CLI command and the UI hit the same platform endpoint, so the result is identical.

## Basic usage

`poly branch merge` requires a merge message and merges the **current branch** into `main`. Switch to the source branch first if you aren't on it.

~~~bash
poly branch switch my-feature
poly branch merge 'Merge my-feature into main'
~~~

If the merge has no conflicts, the branch is merged immediately and the CLI automatically switches your local checkout to `main`. Run `poly pull` afterwards if you need to refresh local state.

| Argument | Required | Description |
|---|---|---|
| `message` | yes | Merge commit message. Quote it if it contains spaces. |
| `--interactive`, `-i` | no | Resolve conflicts in an interactive prompt. |
| `--resolutions <source>` | no | Pre-defined resolutions as a JSON file path, inline JSON string, or `-` for stdin. |
| `--path <dir>` | no | Project base path. Defaults to the current working directory. |
| `--json` | no | Print a single JSON object on stdout (machine-readable). |
| `--verbose` | no | Show full error tracebacks for debugging. |

## Conflicts

If the merge has conflicts, the command prints a conflict table and exits with a non-zero status code. The table shows, for each conflicting field:

- **Path** — the resource and field that conflicts (for example `topics > Booking > content`)
- **Base / Ours / Theirs** — the original value and the two competing values
- **Auto-merged value** — what the ADK would produce by line-merging the two sides
- **Auto-mergeable** — whether the auto-merged value contains any unresolved markers

If every conflict is auto-mergeable and you want to accept the auto-merge, re-run the command with `--interactive` and accept the suggestions, or pre-populate `--resolutions` with the auto-merge values.

### `--interactive` / `-i`

Interactive mode walks you through each conflict and asks how to resolve it. For every conflict you can:

- accept the auto-merge (when available)
- pick `main` (`ours`)
- pick branch (`theirs`)
- pick `base` (revert to the original value)
- open the value in your `$EDITOR` or `$VISUAL` for free-form editing

After you've answered every conflict the merge is re-attempted automatically.

!!! tip "Set `$EDITOR` or `$VISUAL` before starting an interactive merge"

    Interactive mode shells out to your editor for multiline or long values. If neither variable is set it falls back to `vi`. Setting `EDITOR=code --wait` (or your editor of choice) in your shell profile makes the experience much smoother.

### `--resolutions <source>`

Use `--resolutions` to supply pre-defined resolutions non-interactively. The source can be:

- a path to a JSON file
- a literal JSON string
- `-` to read JSON from stdin

If the resolutions cover every conflict the merge proceeds without prompting. Combine `--resolutions` with `--interactive` to seed an interactive session — pre-defined choices are applied automatically and you'll only be prompted for the conflicts they don't cover.

#### Resolution file format

`--resolutions` expects a JSON array of objects:

~~~json
[
  {
    "path": ["topics", "Booking", "content"],
    "strategy": "theirs"
  },
  {
    "path": ["agent_settings", "rules", "value"],
    "strategy": "theirs",
    "value": "Custom resolved content here"
  },
  {
    "path": ["flows", "main_flow", "steps", "greet", "prompt"],
    "strategy": "ours"
  }
]
~~~

| Field | Description |
|---|---|
| `path` | List of strings identifying the conflicted field. Match the `Path` column from the conflict table. |
| `strategy` | One of `"ours"` (keep `main`), `"theirs"` (keep branch), or `"base"` (revert to the original). |
| `value` | Optional custom value. Only honored with the `"theirs"` strategy. |

You can capture the structure of a resolution file by running `poly branch merge` once to surface the conflicts, then writing a JSON file that addresses each `path` row.

## After a successful merge

- The CLI switches your local checkout to `main`.
- Run [`poly pull`](./cli.md#poly-pull) if you need to refresh local state to match the post-merge `main`.
- Run [`poly chat`](./cli.md#poly-chat) against `main` (which falls back to the sandbox environment) to smoke-test the merged result.
- If you're ready to ship, follow up with [`poly deployments`](./cli.md#poly-deployments) to promote the merged state to a live environment.

## Merging through the Agent Studio web UI

You can also merge through the Agent Studio interface:

1. Open the project in Agent Studio.
2. Switch to the branch.
3. Click **Merge**.

The web UI surfaces the same conflicts as the CLI and lets you resolve them in the browser. Use whichever path fits your workflow — they hit the same platform endpoint, so there is no functional difference between them.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Merge message is required` | You ran `poly branch merge` with no message argument. | Pass a quoted message: `poly branch merge 'Describe the merge'`. |
| Conflict table appears and the command exits non-zero | One or more fields conflict between branch and `main`. | Re-run with `--interactive` or supply `--resolutions`. |
| `[Errno 22] Invalid argument` during interactive prompt | The shell isn't a TTY (CI, scripts, non-interactive containers). | Run interactively, or use `--resolutions` with a pre-built JSON file. |
| Editor doesn't open in interactive mode | `$EDITOR` and `$VISUAL` are unset. | Export one of them before running the merge. |
| Local changes block the merge | You have unpushed work on the source branch. | Run [`poly push`](./cli.md#poly-push) first, or [`poly revert`](./cli.md#poly-revert) to discard. |

## Related references

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    Full surface of every `poly` command, including `poly branch` and its sibling subcommands.
    [Open CLI reference](./cli.md)

-   **Working locally**

    ---

    Where branching fits into the daily edit/push/test loop.
    [Open working locally](../concepts/working-locally.md)

-   **Multi-user workflows and guardrails**

    ---

    How branches, merges, and validation interact across a team.
    [Open multi-user workflows](../concepts/multi-user-and-guardrails.md)

-   **Build an agent tutorial**

    ---

    Walks through a feature-branch workflow end-to-end.
    [Open the tutorial](../tutorials/build-an-agent.md)

</div>
