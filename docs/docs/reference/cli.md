---
title: CLI reference
description: Reference for the core commands provided by the PolyAI ADK CLI.
---

<p class="lead">
The PolyAI ADK is accessed through the <code>poly</code> command.
When in doubt about a flag or option, run the command with <code>--help</code> - that output reflects your installed version exactly.
</p>

## Start with help

To see all available commands and options:

~~~bash
poly --help
~~~

Each command also supports its own help output. For example:

~~~bash
poly push --help
~~~

!!! tip "Help output reflects your installed version"

    This reference page covers the standard commands. Run `poly <command> --help` to confirm the exact flags available in your environment.

## Core commands

### `poly init`

Initialize a new Agent Studio project locally.

Examples:

~~~bash
poly init
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format
~~~

### `poly pull`

Pull the latest project configuration from Agent Studio.

Examples:

~~~bash
poly pull
poly pull --force
poly pull --format
~~~

### `poly push`

Push local changes to Agent Studio.

Examples:

~~~bash
poly push
poly push --dry-run
poly push --skip-validation
poly push --force
poly push --format
~~~

### `poly status`

View changed, new, and deleted files in your project.

~~~bash
poly status
~~~

### `poly diff`

Show differences between the local project and the remote version.

Examples:

~~~bash
poly diff
poly diff file1.yaml
~~~

### `poly revert`

Revert local changes.

Examples:

~~~bash
poly revert --all
poly revert file1.yaml file2.yaml
~~~

### `poly branch`

Manage project branches.

Examples:

~~~bash
poly branch list
poly branch current
poly branch create my-feature
poly branch switch my-feature
poly branch switch my-feature --force
~~~

### `poly format`

Format project resources.

Examples:

~~~bash
poly format
poly format file1.py
~~~

### `poly validate`

Validate project configuration locally.

~~~bash
poly validate
~~~

### `poly review`

Create a GitHub gist for reviewing changes.

Examples:

~~~bash
poly review
poly review --before main --after feature-branch
poly review --delete
~~~

### `poly chat`

Start an interactive chat session with your agent.

Examples:

~~~bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --metadata
~~~

### `poly docs`

Output resource documentation.

Examples:

~~~bash
poly docs flows functions topics
poly docs --all
poly docs --all --output rules.md
~~~

Use `--output` to write the documentation to a local file. This is useful when working with AI coding tools - pass the output file as context to give the agent accurate knowledge of ADK resource types and conventions.


## Working pattern

A typical CLI workflow looks like this:

1. initialize or pull a project locally
2. create or switch to a branch
3. edit files
4. inspect changes with `poly status` and `poly diff`
5. validate with `poly validate`
6. push with `poly push`
7. optionally review with `poly review`
8. test or chat with the agent using `poly chat`

!!! info "Run commands from the project folder"

    ADK commands are expected to be run from within your local project directory. If needed, use the <code>--path</code> flag to point to a project explicitly.

## Related pages

<div class="grid cards" markdown>

-   **Build an agent**

    ---

    See how the CLI fits into a real workflow.
    [Open the tutorial](../tutorials/build-an-agent.md)

-   **Testing**

    ---

    Learn how to run tests for the project.
    [Open testing](./testing.md)

</div>
