---
title: VS Code and Cursor extension
description: Resource-aware editing, validation and poly commands for ADK projects in VS Code and Cursor.
---

# VS Code and Cursor extension

<p class="lead">
The PolyAI ADK extension brings ADK-aware editing into VS Code and Cursor. It is the recommended path if you prefer an IDE-first workflow.
</p>

The extension helps with:

- navigating and editing flows, functions, topics, entities, and agent settings with resource-aware tooling
- catching common mistakes while you edit, before you push
- driving `poly` commands without leaving the editor
- pairing with your IDE's built-in AI features (Cursor's agent, VS Code Copilot, etc.) to generate and update project files

## Install the extension

The extension is published on **Open VSX**, so it works in both VS Code and Cursor.

1. Open the Extensions view in VS Code or Cursor.
2. Search for `PolyAI ADK` and install it, or install it directly from the [Open VSX listing](https://open-vsx.org/extension/PolyAI/adk-extension){ target="_blank" rel="noopener" }.
3. Open a project that has been pulled down with `poly pull`.

Once installed, the extension auto-detects local ADK projects and exposes resource-aware navigation, validation, and commands.

!!! tip "The CLI stays the source of truth"

    The extension is additive: every workflow still runs through the `poly` command, so anything you do in the editor you can also do in a terminal.

## Next steps

<div class="grid cards" markdown>

-   **Tooling overview**

    ---

    Other tools that pair well with the ADK, including AI coding agents.
    [Open the tooling overview](./tooling.md)

-   **Working locally**

    ---

    The local development loop the extension builds on.
    [Open working locally](../development/working-locally.md)

</div>
