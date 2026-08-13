---
title: Branch merging
description: Merge ADK branches into their parent branch from the CLI, including conflict resolution flows.
---

# Branch merging

<p class="lead">
Merge a feature branch back into its parent with <code>poly branch merge</code>, including interactive and pre-defined conflict resolution.
</p>

`poly branch merge` is the CLI-native counterpart to merging in the Agent Studio web UI. It brings everything you've changed on the current branch back onto the parent branch, surfaces any conflicts in a structured table, and lets you resolve them either interactively or from a JSON file.

For the broader branching workflow (creating, switching, listing, deleting branches), see the [`poly branch` section of the CLI reference](./cli.md#poly-branch). For the team-level guardrails around branching and merging, see [Multi-user workflows and guardrails](../concepts/multi-user-and-guardrails.md).

## When to use it

You'll typically reach for `poly branch merge` at the end of a feature loop:

1. Create a branch with `poly branch create my-feature` (see [`poly branch create`](./cli.md#poly-branch-create)).
2. Iterate locally, pushing with `poly push` (see [Working locally](../concepts/working-locally.md)).
3. Test with `poly chat` against the branch's pushed state.
4. Merge back to the parent with `poly branch merge '<message>'` — described on this page.
5. Optionally deploy through Agent Studio.

You can also merge from the Agent Studio web UI by switching to the branch and clicking **Merge**. The CLI command and the UI hit the same platform endpoint, so the result is identical.

## Basic usage

`poly branch merge` merges the **current branch** into its configured parent branch. Switch to the source branch first if you aren't on it.

~~~bash
poly branch switch my-feature
poly branch merge 'Merge my-feature into main'
~~~

A merge message is **required when merging into `main`**. When merging into another branch (branch-to-branch), the message is optional.

If the merge has no conflicts, the branch is merged immediately and the CLI automatically switches your local checkout to the parent branch. Run `poly pull` afterwards if you need to refresh local state.

| Argument | Required | Description |
|---|---|---|
| `message` | Yes (when merging into `main`) | Merge commit message. Quote it if it contains spaces. Optional for branch-to-branch merges. |
| `--interactive`, `-i` | no | Resolve conflicts in an interactive prompt. |
| `--resolutions <source>` | no | Pre-defined resolutions as a JSON file path, inline JSON string, or `-` for stdin. |
| `--force`, `-f` | no | Skip the live-deployment confirmation prompt when merging into `main` under simplified deployments. |
| `--path <dir>` | no | Project base path. Defaults to the current working directory. |
| `--json` | no | Print a single JSON object on stdout (machine-readable). |
| `--verbose` | no | Show full error tracebacks for debugging. |

## Merging into `main` under simplified deployments

For projects using simplified deployments, merging into `main` deploys changes directly to the live environment — there is no sandbox → pre-release → live promotion ladder.

When this applies, `poly branch merge` warns you before proceeding:

~~~
Warning: Merging into 'main' will deploy changes into live environment
Confirm Deployment? [y/N]
~~~

Use `--force` to skip this prompt in scripts or CI pipelines.

After a successful merge into `main` under simplified deployments, the CLI shows:

~~~
Branch 'my-feature' merged into main — your changes are now live.
~~~

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
| `strategy` | One of `"ours"` (keep parent branch), `"theirs"` (keep current branch), or `"base"` (revert to the original). |
| `value` | Optional custom value. Only honored with the `"theirs"` strategy. |

You can capture the structure of a resolution file by running `poly branch merge` once to surface the conflicts, then writing a JSON file that addresses each `path` row.

## After a successful merge

- The CLI switches your local checkout to the parent branch.
- Run [`poly pull`](./cli.md#poly-pull) if you need to refresh local state to match the post-merge parent.
- Run [`poly chat`](./cli.md#poly-chat) to smoke-test the merged result.
- If you're ready to ship and the project uses the traditional deployment model, follow up with [`poly deployments`](./cli.md#poly-deployments) to promote the merged state to a live environment.

## Syncing parent changes into your branch

The reverse operation — pulling the parent branch's latest changes down into your current branch — is `poly branch sync`. It uses the same conflict-resolution flow.

~~~bash
poly branch sync
poly branch sync --interactive
poly branch sync --resolutions resolutions.json
~~~

!!! info "Simplified deployments only"

    `poly branch sync` is only available for projects using simplified deployments.

## Merging through the Agent Studio web UI

You can also merge through the Agent Studio interface:

1. Open the project in Agent Studio.
2. Switch to the branch.
3. Click **Merge**.

The web UI surfaces the same conflicts as the CLI and lets you resolve them in the browser. Use whichever path fits your workflow — they hit the same platform endpoint, so there is no functional difference between them.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Merge message is required when merging into main` | You ran `poly branch merge` with no message argument while merging into `main`. | Pass a quoted message: `poly branch merge 'Describe the merge'`. |
| Conflict table appears and the command exits non-zero | One or more fields conflict between branch and parent. | Re-run with `--interactive` or supply `--resolutions`. |
| `[Errno 22] Invalid argument` during interactive prompt | The shell isn't a TTY (CI, scripts, non-interactive containers). | Run interactively, or use `--resolutions` with a pre-built JSON file. |
| Editor doesn't open in interactive mode | `$EDITOR` and `$VISUAL` are unset. | Export one of them before running the merge. |
| Local changes block the merge | You have unpushed work on the source branch. | Run [`poly push`](./cli.md#poly-push) first, or [`poly revert`](./cli.md#poly-revert) to discard. |
| Live deployment confirmation prompt appears | Merging into `main` on a project using simplified deployments deploys directly to live. | Confirm to proceed, or use `--force` to skip the prompt in scripts. |
| `Command is only available for projects using simplified deployments` | You ran `poly branch sync`, `poly branch tag`, or `poly branch untag` on a project that hasn't enabled simplified deployments. | These commands require the simplified deployment model. Check with your PolyAI contact if you expect this to be enabled. |

## Related references

<div class="grid cards" markdown>

-   **Tests**

    ---

    Validate agent behavior with conversation tests before merging.
    [Open tests reference](./tests.md)

-   **Tooling**

    ---

    IDE extensions and AI coding tools that integrate with the ADK workflow.
    [Open tooling](./tooling.md)

-   **Multi-user workflows and guardrails**

    ---

    How branches, merges, and validation interact across a team.
    [Open multi-user workflows](../concepts/multi-user-and-guardrails.md)

</div>
