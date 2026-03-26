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

### Claude Code

PolyAI recommends using **Claude Code** for development with the ADK.

The repository includes a `.claude/` directory with project-specific instructions and examples.

Claude Code is particularly useful for:

- generating project resources from structured requirements
- updating flows and functions
- applying patterns reused across previous projects
- speeding up repetitive implementation work

#### Loading ADK rules into Claude Code

Before starting a session with Claude Code or another coding tool, generate a documentation file and pass it as context:

~~~bash
poly docs --all --output rules.md
~~~

Reference `rules.md` in your session prompt. This gives the coding tool accurate knowledge of ADK resource types, constraints, and conventions.

### VS Code extension

A **PolyAI ADK VS Code extension** is available in the VS Code Marketplace. Search for `PolyAI.adk-extension` or install it directly from the [marketplace listing](https://marketplace.visualstudio.com/items?itemName=PolyAI.adk-extension){ target="_blank" rel="noopener" }.

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

A common pattern looks like this:

1. use the ADK to pull or initialize a project locally
2. open the project in your editor or IDE
3. use an AI coding tool or standard editing workflow to make changes
4. inspect and validate those changes locally
5. push them back to Agent Studio

## Best practices

- use the CLI as the source of truth for project operations
- keep AI-assisted generation grounded in real project requirements
- validate generated output before pushing
- review changes in Agent Studio before merging
- treat tooling as an accelerator, not a substitute for review

!!! tip "Tooling should reduce friction, not reduce scrutiny"

    Faster editing and generation are valuable, but project review, validation, and testing still matter.

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