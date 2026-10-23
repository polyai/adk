---
title: Tooling
description: Development tools and integrations commonly used with the PolyAI ADK.
---

# Tooling

<p class="lead">
The PolyAI ADK fits naturally into a local developer workflow and can be used alongside standard editors, terminals, and AI-assisted coding tools.
</p>

The ADK is especially useful when paired with tools that help developers inspect, edit, generate, and review local project files efficiently.

## Integrating with your workflow

The ADK works alongside the editors, coding agents and version control you already use. Use whichever fit how you work; they combine freely.

### VS Code and Cursor extension

The **PolyAI ADK extension** brings resource-aware editing, validation and `poly` commands into **VS Code** and **Cursor**. See [VS Code and Cursor extension](./editor-extension.md) to install it.

### Coding agents

The ADK ships **agent skills** that teach a coding agent the `poly` workflow: project structure, branching, testing, conversation review and real-time configuration. They work with many agents, including **Claude Code**, **Cursor**, **Codex** and others, and load on demand as you work. The skills live in the ADK repo's [`skills/`](https://github.com/polyai/adk/tree/main/skills){ target="_blank" rel="noopener" } folder.

[`poly setup`](../reference/cli/setup.md) installs them into the coding agents it finds on your machine:

~~~bash
poly setup               # full onboarding
poly setup --skip-auth   # just add the skills on an already-configured machine
~~~

Coding agents are particularly useful for:

- generating project resources from structured requirements
- updating flows and functions at scale
- applying patterns reused across previous projects
- speeding up repetitive implementation work

For a coding tool without skill support, generate a documentation file and pass it as context instead:

~~~bash
poly docs --all --output rules.md
~~~

Reference `rules.md` in your session prompt. This gives the coding tool accurate knowledge of ADK resource types, constraints, and conventions.

### Integrating Git with the ADK

Keep your projects in a git repository, where every pull request is tested and pushed to an Agent Studio branch, merging deploys it to Agent Studio, and changes made in Agent Studio come back into git. The ADK repo template sets this up on GitHub; see [Deploying from GitHub](./deploying-from-github.md).

!!! tip "Combine them"

    Edit in VS Code or Cursor day to day, hand larger changes to a coding agent, and let the git workflow test and deploy both.

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
