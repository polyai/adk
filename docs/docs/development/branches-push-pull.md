---
title: Branches, push, and pull
description: How the PolyAI ADK handles branches, diffs, reviews, and merging when several people work on the same project.
---

# Branches, push, and pull

Several people can work on the same Agent Studio project at once, from their own machines, without overwriting each other. Local edits, edits made by teammates, and edits made directly in the Agent Studio UI all affect the same branch state, so the ADK is built around branching, inspecting, and merging rather than straight overwrites.

## Branches

**You cannot work on `main`.** Every change is made on a branch and merged in. `main` is the state everything branches off from and merges back into, not somewhere you edit.

```bash
poly branch create <branch_name>   # create and switch to a new branch
poly branch switch <branch_name>   # move to an existing branch
poly branch current                # which branch am I on?
poly branch list                   # all branches
```

Branches are created from `main`, and the new branch is created on the platform from `main`'s current state — so you always branch off the latest without needing to pull first.

`poly branch create` leaves your local files alone, so any uncommitted work you had carries over to the new branch. If you started editing on `main` before realizing you needed a branch, creating one is enough — nothing is lost.

`poly branch switch` behaves differently: it refuses to move while you have uncommitted changes, then replaces your local files with the target branch's state. So creating carries your work forward, and switching requires a clean tree.

The ADK reflects the no-`main` rule throughout — `poly branch diff`, `merge`, `sync`, `tag`, and `untag` all refuse to run while you are on `main`. If a command tells you it does not support `main`, the fix is to switch to a branch.

Branches exist on the platform, not just locally — `poly branch create` creates the branch in Agent Studio, so a teammate can switch to it, and you can inspect it in the web UI. This also means the branch you are on determines what `poly push` writes to and what `poly chat` talks to.

!!! warning "Local edits and Agent Studio UI edits can collide"

    The local workflow is not isolated from the web UI. If someone edits the same branch in Agent Studio while you have local changes, both sets of edits are real and the next `poly pull` has to reconcile them. This is the situation the three-way merge below exists to handle.

## Diffs and reviews

There are two levels of inspection, and they answer different questions.

| Command | Shows |
|---|---|
| `poly status`, `poly diff` | Your local edits that have not been pushed yet |
| `poly branch status`, `poly branch diff` | Everything on the branch since it was created, including changes you already pushed |

Use the first while you are working, and the second before you merge.

To share changes with someone else, both review commands publish a GitHub Gist:

```bash
poly branch review           # this branch's changes since it was created
poly review create           # local vs remote
poly review create --before main --after my-feature
```

`poly branch review` is scoped to the branch. `poly review create` is the general form — with no arguments it compares your local project against the remote version, and with `--before`/`--after` it compares any two branches or versions. Both require a GitHub environment token, and both let reviewers read the changes without access to your filesystem.

## How `poly pull` merges

`poly pull` does not overwrite your local files. It performs a **three-way merge**, line by line, between:

| Side | What it is |
|---|---|
| **Base** | The project state as of your last pull or push, tracked in `_gen/.agent_studio_config` |
| **Local** | The file as it currently exists on disk, including your uncommitted edits |
| **Incoming** | The state now on the remote branch |

Comparing against the base is what lets the ADK tell your edits apart from someone else's. A region changed on only one side is applied cleanly. A region changed on both sides, differently, is a conflict.

Before merging, the ADK re-serializes your local file into its canonical form, so differences in formatting, key order, or whitespace do not register as changes. Only real content differences can conflict.

### Resolving conflicts

Conflicts are written into the file with markers. Note that they are unlabelled, unlike Git — your version is always above the divider and the incoming version below:

```text
<<<<<<<
your local version
=======
the incoming remote version
>>>>>>>
```

`poly pull` lists every file it left conflicted. **Until you resolve them, other commands fail** — reading a resource file that still contains markers raises a merge-conflict error, so `poly status`, `poly diff`, `poly validate`, and `poly push` will all refuse to run. Edit each file to the version you want, delete the markers, then carry on.

Two escape hatches:

```bash
poly pull -f          # discard local changes entirely, no merge
poly pull --format    # format all three sides before merging
```

`poly pull -f` overwrites local files with the remote state and deletes local resources that are not on the remote, so use it only when you are willing to lose local work. `--format` can reduce spurious conflicts on files whose formatting has drifted.

!!! info "A deleted local file stays deleted"

    If a file is missing locally but present in the tracked state, `poly pull` treats that as an intentional deletion and does not restore it. Files that are new on the remote are written directly, since there is no local version to merge against.

## Merging changes

Once the branch is reviewed, merge it into its parent:

```bash
poly branch merge '<commit message>'
```

Merging uses the same conflict detection as `poly pull`, so `poly branch status` will tell you in advance whether the branch can merge cleanly. For conflict resolution options — `--interactive` and `--resolutions` — see [`poly branch merge`](../reference/cli/branch.md#conflicts). You can also merge from the Agent Studio web UI by switching to the branch and clicking **Merge**.

Merging into `main` also deploys the result to the `sandbox` environment. See [deploying your changes](./working-locally.md#deploying-your-changes) for promoting from there to `pre-release` and `live`.

## Habits that avoid trouble

Most collaboration problems come from process rather than tooling:

- create a branch before making substantial changes, and check `poly branch current` if you are unsure where you are
- pull before you start work, so your base is recent and conflicts stay small
- run `poly validate` before pushing — it catches invalid resource structures, missing required values, and broken references between resources
- keep branches small and focused; a branch mixing several unrelated changes is much harder to review and to merge
- use `poly branch diff` before merging, not just `poly diff`
- keep resource names stable, since references point at resources by name
