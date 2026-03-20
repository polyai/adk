---
title: First commands
description: Learn the core PolyAI ADK commands and how to inspect the CLI.
---

# First commands

Once the ADK is installed, the fastest way to get oriented is to inspect the CLI directly.

## View top-level help

To see all available commands and options, run:

~~~bash
poly --help
~~~

Each command also supports its own help output. For example:

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

## Recommended starting point

A good way to explore the CLI is:

1. run `poly --help`
2. identify the command you need
3. run that command with `--help`

For example:

~~~bash
poly init --help
poly pull --help
poly push --help
~~~

## Next step

Once you understand the CLI shape, continue to the command reference or the tutorial.

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