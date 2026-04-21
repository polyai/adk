---
title: First commands
description: Learn the core PolyAI ADK commands and how to inspect the CLI.
---

# First commands

Once the ADK is installed, the fastest way to get oriented is to inspect the CLI directly.

## View top-level help

Run `poly --help` to see every available command:

~~~bash
poly --help
~~~

Each command also accepts `--help` for its own flags and options:

~~~bash
poly push --help
~~~

## Core commands

The ADK provides the following core commands:

<div class="grid cards" markdown>

-   **`poly init`**

    ---

    Initialize a new Agent Studio project locally.

-   **`poly pull`**

    ---

    Pull the latest project configuration from Agent Studio.

-   **`poly push`**

    ---

    Push local changes back to Agent Studio.

-   **`poly status`**

    ---

    View changed, new, and deleted files in your project.

-   **`poly diff`**

    ---

    Show differences between the local project and the remote version.

-   **`poly branch`**

    ---

    Manage project branches.

-   **`poly format`**

    ---

    Format project resources.

-   **`poly validate`**

    ---

    Validate project configuration locally.

-   **`poly review`**

    ---

    Create a GitHub gist for reviewing changes.

-   **`poly chat`**

    ---

    Start an interactive chat session with your agent.

-   **`poly revert`**

    ---

    Revert local changes.

</div>

## Explore any command

To learn what a command does and what flags it accepts, run it with `--help`:

~~~bash
poly init --help
poly pull --help
poly push --help
~~~

## Common first-run behavior

### `poly status` shows variables you didn't create

After `poly init` or `poly pull`, `poly status` may report `variables/` entries as new files — for example, `variables/caller_number` or `variables/verified_record`. These are **virtual**: the ADK scans function code for `conv.state.*` assignments and tracks each one as a variable resource. No corresponding files exist on disk. This is expected and does not mean you have changes to push.

### `poly branch switch` reports uncommitted changes

If `poly status` shows phantom `variables/` entries and you try to switch branches, the ADK may block the switch:

~~~text
Cannot switch branches with uncommitted changes. Use --force to switch and discard changes.
~~~

Use `--force` to override:

~~~bash
poly branch switch <branch-name> --force
~~~

This discards no actual work — the variables entries are virtual and will reappear after the next pull.

## Next step

Continue to the command reference for a complete listing, or go straight to the tutorial to see a real workflow.

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    See a more detailed overview of the available commands.
    [Open CLI reference](../reference/cli.md)

-   **Build an agent**

    ---

    Follow the step-by-step workflow for using the ADK in practice.
    [Open the tutorial](../tutorials/build-an-agent.md)

</div>