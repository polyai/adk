---
name: poly-adk-branching
description: >
  This skill should be used when the user wants to "resolve merge conflicts", "merge a branch",
  "fix conflict markers", "create a hotfix branch", "share changes for review", or manage
  branches in a PolyAI ADK project — or when poly pull or poly branch merge reports conflicts.
  Covers branch management, the three-way merge model, non-interactive conflict resolution,
  and review gists. Part of the PolyAI ADK skills suite. Do NOT use for the everyday
  edit-push loop (use poly-adk-workflow).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.53.1
  requires:
    bins:
      - poly
    install: "uv tool install polyai-adk"
---

# Branching, Merging, and Conflicts

Load `poly-adk-workflow` first for where branching sits in the build loop. The one rule that shapes everything: **you cannot work on `main`** — `branch diff`, `merge`, `sync`, `tag`, and `untag` all refuse to run there.

## Branch management

```bash
poly branch list                   # all branches (--archived for soft-deleted ones)
poly branch current                # current branch + its parent
poly branch create <name>          # create + switch; branches from main's latest state
poly branch switch <name>          # requires a clean tree (--force discards local changes)
poly branch rename <new-name>
poly branch delete [<name>]        # main cannot be deleted
poly branch restore <branch_id>    # un-archive; IDs from poly branch list --archived
poly branch history                # branches merged into the current branch
```

Semantics that matter:

- **`create` carries uncommitted local work onto the new branch; `switch` refuses to move with uncommitted changes** and replaces local files with the target branch's state. Started editing on `main` by accident? `branch create` alone recovers it — nothing is lost.
- Branches exist **on the platform**, not just locally — teammates can switch to yours, and the web UI can edit it while you work.
- `poly status`/`poly diff` show unpushed local edits; `poly branch status`/`poly branch diff` show everything since the branch was created. Use the branch-level pair before merging. `poly branch status` also says whether the branch has diverged — i.e. whether it will merge cleanly.

### Hotfix branches from a deployed environment

`poly branch create my-hotfix --env live` snapshots the deployed environment into a fresh branch (also `sandbox`, `pre-release`). **Use with caution**: it overwrites your local project with the deployed state, and merging that branch back to main can roll back changes made after the snapshot. It fails on uncommitted local changes unless `--force`.

## How pull merges

`poly pull` never blind-overwrites. It three-way merges, line by line, between **base** (state at your last pull/push, tracked in `_gen/.agent_studio_config`), **local** (your disk, including uncommitted edits), and **incoming** (the remote branch). Files are re-serialized to canonical form first, so formatting and key-order differences never conflict — only real content changes do. A file deleted locally stays deleted.

Conflicts are written into files with **unlabelled** markers — unlike Git, there are no branch names:

```text
<<<<<<<
your local version
=======
the incoming remote version
>>>>>>>
```

**While any marker remains, `status`, `diff`, `validate`, and `push` all refuse to run.** `poly pull` lists every conflicted file; edit each to the content you want, delete the markers, then continue. Escape hatches: `poly pull -f` discards all local work and takes the remote (confirm with the user first — it also deletes local resources missing from the remote); `poly pull --format` formats all three sides first to reduce spurious conflicts.

## Merging a branch

```bash
poly branch merge 'Merge message'       # message required when merging into main
```

A clean merge completes immediately and switches your checkout to the parent branch. Merging into `main` deploys to `sandbox` automatically. The web UI's **Merge** button hits the same endpoint — identical result.

### Resolving merge conflicts

On conflict the command exits non-zero and prints a table per conflicting field: **Path** (e.g. `topics > Booking > content`), **Base / Ours / Theirs** values, the **auto-merged value**, and whether it's auto-mergeable. Two resolution routes:

- `--interactive` / `-i` — walks each conflict: accept the auto-merge, pick ours (parent) / theirs (branch) / base, or edit in `$EDITOR`. Terminal-only; incompatible with `--json`.
- `--resolutions <source>` — **the non-interactive route, so the one to use as an agent.** A JSON array (file path, inline string, or `-` for stdin):

```json
[
  { "path": ["topics", "Booking", "content"], "strategy": "theirs" },
  { "path": ["agent_settings", "rules", "value"], "strategy": "theirs", "value": "Custom resolved content" },
  { "path": ["flows", "main_flow", "steps", "greet", "prompt"], "strategy": "ours" }
]
```

`path` matches the conflict table's Path column; `strategy` is `"ours"`, `"theirs"`, or `"base"`; a custom `value` is only honored with `"theirs"`. Workflow: run `poly branch merge --json` once to surface the conflicts, build a resolutions file covering each path, re-run with `--resolutions`. Confirm resolution choices with the user when the right answer isn't obvious — both sides are real work.

## Sharing changes for review

Both review commands publish a private GitHub Gist (one `.diff` file per changed resource) so reviewers don't need filesystem access. Requires a GitHub token in the environment.

```bash
poly branch review                                  # this branch since creation
poly review create                                  # local vs remote
poly review create --before main --after my-feature # any two branches/versions
poly review list                                    # open past gists
poly review delete --id <gist_id>
```

## Habits that avoid trouble

- Pull before starting work so your base is recent and conflicts stay small.
- Keep branches small and single-purpose — easier to review and merge.
- Keep resource names stable; references point at resources by name.
- Check `poly branch status` before merging to know in advance whether it's clean.
