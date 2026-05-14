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

The **PolyAI ADK extension** brings ADK-aware editing into **VS Code** and **Cursor**. It is the recommended path if you prefer an IDE-first workflow.

The extension helps with:

- navigating and editing flows, functions, topics, entities, and agent settings with resource-aware tooling
- catching common mistakes while you edit, before you push
- driving `poly` commands without leaving the editor
- pairing with your IDE's built-in AI features (Cursor's agent, VS Code Copilot, etc.) to generate and update project files

#### Install the extension

The extension is published on **Open VSX**, so it works in both VS Code and Cursor.

1. Open the Extensions view in VS Code or Cursor.
2. Search for `PolyAI ADK` and install it, or install it directly from the [Open VSX listing](https://open-vsx.org/extension/PolyAI/adk-extension){ target="_blank" rel="noopener" }.
3. Open a project that has been pulled down with `poly pull`.

Once installed, the extension auto-detects local ADK projects and exposes resource-aware navigation, validation, and commands.

### Claude Code

**Claude Code** is a good alternative when you want an agentic CLI workflow — useful for generating a project from a brief, applying patterns across many files, or running longer build tasks end-to-end.

The repository includes a `.claude/` directory with project-specific instructions and examples.

Claude Code is particularly useful for:

- generating project resources from structured requirements
- updating flows and functions at scale
- applying patterns reused across previous projects
- speeding up repetitive implementation work

#### Loading ADK rules into Claude Code

Before starting a session with Claude Code or another external coding tool, generate a documentation file and pass it as context:

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

Tooling slots into the standard [CLI workflow](./cli.md#working-pattern): pull or init, edit with your tool of choice, validate, push, and review in Agent Studio.

## Related pages

<div class="grid cards" markdown>

-   **Installation**

    ---

    Set up the ADK locally before using it with development tools.
    [Open installation](../get-started/installation.md)

-   **CLI reference**

    ---

    Review the commands that drive the local workflow.
    [Open CLI reference](./cli.md)

</div>