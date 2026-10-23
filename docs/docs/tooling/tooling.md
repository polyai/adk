---
title: Tooling
description: Development tools and integrations commonly used with the PolyAI ADK.
---

# Tooling

<p class="lead">
The PolyAI ADK fits naturally into a local developer workflow and can be used alongside standard editors, terminals, and AI-assisted coding tools.
</p>

The ADK is especially useful when paired with tools that help developers inspect, edit, generate, and review local project files efficiently.

## Recommended tooling

There are two well-supported paths for working with the ADK. They are not mutually exclusive — many developers use both.

### PolyAI ADK extension for VS Code and Cursor

The **PolyAI ADK extension** brings resource-aware editing, validation and `poly` commands into **VS Code** and **Cursor**. It is the recommended path if you prefer an IDE-first workflow. See [VS Code and Cursor extension](./editor-extension.md) to install it.

### Claude Code

**Claude Code** is a good alternative when you want an agentic CLI workflow — useful for generating a project from a brief, applying patterns across many files, or running longer build tasks end-to-end.

The repository includes a `.claude/` directory with project-specific instructions and examples.

Claude Code is particularly useful for:

- generating project resources from structured requirements
- updating flows and functions at scale
- applying patterns reused across previous projects
- speeding up repetitive implementation work

#### Installing the ADK skills

[`poly setup`](../reference/cli/setup.md) installs the ADK's agent skills into coding agents detected on your machine — Claude Code, Cursor, Codex, and others:

~~~bash
poly setup            # full onboarding
poly setup --skip-auth   # just add the skills on an already-configured machine
~~~

The skills teach the agent the `poly` workflow — project structure, branching, testing, conversation review, and real-time configuration — and load on demand as you work.

For a coding tool without skill support, generate a documentation file and pass it as context instead:

~~~bash
poly docs --all --output rules.md
~~~

Reference `rules.md` in your session prompt. This gives the coding tool accurate knowledge of ADK resource types, constraints, and conventions.

!!! tip "Use both where useful"

    The IDE extension and Claude Code cover different modes of work. You can edit in VS Code or Cursor day-to-day and still reach for Claude Code when you want an agent to generate or refactor a large slice of the project on your behalf.

## Other local tools

The ADK also fits well with standard local development tooling such as:

- a terminal
- Git
- Python
- `uv`
- code editors such as VS Code or IntelliJ-based IDEs

<div class="grid cards" markdown>

-   **AI coding tools**

    ---

    Useful for generating and updating ADK project files from structured inputs.

-   **Editors and IDEs**

    ---

    Helpful for navigating project structure, editing resources, and reviewing changes.

-   **Terminal workflow**

    ---

    The `poly` CLI is the core interface for local project work.

</div>

## How tooling fits into the workflow

Tooling slots into the standard [CLI workflow](../reference/cli.md): pull or init, edit with your tool of choice, validate, push, and review in Agent Studio.

To keep projects in a GitHub repo that tests and deploys every change, see [deploying from GitHub](./deploying-from-github.md).

!!! tip "Tooling should reduce friction, not reduce scrutiny"

    Faster editing and generation are valuable, but project review, validation, and testing still matter.

## Next steps

<div class="grid cards" markdown>

-   **VS Code and Cursor extension**

    ---

    Install the extension and edit projects with resource-aware tooling.
    [Open the extension page](./editor-extension.md)

-   **Deploying from GitHub**

    ---

    Keep projects in a GitHub repo that tests and deploys every change.
    [Open deploying from GitHub](./deploying-from-github.md)

-   **CLI reference**

    ---

    Every `poly` command and its options.
    [Open the CLI reference](../reference/cli.md)

</div>
