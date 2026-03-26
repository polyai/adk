---
title: Multi-user workflows and guardrails
description: Learn how the PolyAI ADK supports collaboration, branching, validation, and safe synchronization with Agent Studio.
---

The **PolyAI ADK** was designed with **multi-user collaboration** in mind.

It allows multiple developers to work on the same Agent Studio project while preserving the same platform guardrails that prevent incompatible or invalid changes from being pushed.

## Why this matters

Local workflows are only useful if teams can collaborate safely.

Without guardrails, local editing quickly becomes chaotic:

- one developer overwrites another’s work
- invalid resources are pushed upstream
- branch state becomes unclear
- review becomes difficult

The ADK is designed to reduce those risks by combining local editing with validation, branching, and synchronization back to Agent Studio.

<div class="grid cards" markdown>

-   **Branch-based work**

    ---

    Developers can create and switch branches for isolated work.

-   **Validation before push**

    ---

    Local changes can be checked before they are sent back to Agent Studio.

-   **Review support**

    ---

    Changes can be compared and shared for review before merge.

-   **Platform compatibility**

    ---

    The CLI helps ensure that pushed changes remain valid for the project.

</div>

## Branch workflow

A typical collaborative workflow looks like this:

1. start from the `main` branch
2. create a new branch with `poly branch create {name}`
3. switch branches as needed with `poly branch switch {name}`
4. edit files locally
5. inspect changes with `poly status` and `poly diff`
6. validate the project with `poly validate`
7. push changes with `poly push`
8. review the branch in Agent Studio
9. merge the branch in Agent Studio when ready

You can also use:

- `poly branch list` to view available branches
- `poly branch current` to check the active branch

## Validation as a guardrail

Run `poly validate` before pushing to catch issues locally, before they reach Agent Studio.

Examples of what validation protects against include:

- invalid resource structures
- missing required values
- incompatible references between resources
- malformed configuration files

!!! info "Validate before pushing"

    In collaborative workflows, treat `poly validate` as a standard step in the editing cycle, not an optional one.

## Pulling and merge behavior

If work is done to your branch in Agent Studio and you want to bring those changes into your local copy, you can run:

~~~bash
poly pull
~~~

If the pulled changes conflict with your own local edits, the ADK will merge them and surface merge markers where conflicts occur.

The local workflow is not isolated from Agent Studio UI work — both sides affect branch state. Keep that in mind when collaborating.

## Review workflow

When changes are ready for review, generate a review artifact:

~~~bash
poly review
~~~

Use this to compare:

- local changes against the remote project
- one branch against another
- a feature branch against `main` or `sandbox`

A GitHub environment token is required. The output lets reviewers inspect changes without access to your local filesystem.

## Guardrails inherited from Agent Studio

The ADK is intentionally aligned with the Agent Studio platform.

That means it is not just a free-form local editing tool. It is structured so that developers should not be able to push changes that are incompatible with the project as defined by the platform.

In practice, this means:

- project resources must still conform to Agent Studio expectations
- references between resources must remain valid
- branch merges still happen in Agent Studio
- deployment still happens through Agent Studio

!!! tip "Local flexibility, platform constraints"

    The ADK expands where and how developers can work, but it does not remove the constraints that keep projects valid and deployable.

## Best practices for teams

When multiple developers are working on the same project, a few habits make the workflow much smoother:

- create a branch before making substantial changes
- pull the latest changes before starting work
- validate locally before pushing
- use `poly diff` and `poly status` frequently
- review branch output before merging
- keep resource names stable and descriptive

## Common failure modes

Common collaboration problems usually come from process, not tooling.

Watch out for:

- editing directly on the wrong branch
- forgetting to pull before starting work
- pushing without validation
- mixing large unrelated changes into one branch
- treating Agent Studio UI edits and local edits as if they cannot collide

## Related pages

<div class="grid cards" markdown>

-   **Working locally**

    ---

    Learn how the local project structure maps to Agent Studio.
    [Open working locally](./working-locally.md)

-   **CLI reference**

    ---

    Review the commands used for branching, validation, diffing, and review.
    [Open CLI reference](../reference/cli.md)

</div>