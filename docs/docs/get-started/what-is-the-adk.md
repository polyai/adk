---
title: What is the PolyAI ADK?
description: Learn what the PolyAI Agent Development Kit is, why it exists, and how it supports local development workflows for Agent Studio.
---

The **PolyAI ADK (Agent Development Kit)** is a **CLI tool and Python package** for managing **Agent Studio** projects on your local machine.

It gives you a Git-like workflow for synchronizing project configuration between your local filesystem and the Agent Studio platform.

## What you can do with the ADK

- Build and edit Agent Studio projects locally using standard tooling
- Synchronize project configuration with Agent Studio using `poly push` and `poly pull`
- Branch, validate, and review changes before deployment
- Use AI coding tools such as **Claude Code** to generate and update project files
- Collaborate across multiple developers on the same project

## Why it exists

The ADK moves development work out of the browser and into your local environment.

Instead of editing everything directly inside Agent Studio, you pull a project locally, make changes using your normal tools, and push those changes back to the platform.

This makes it straightforward to:

- iterate quickly without browser round-trips
- collaborate across a team without overwriting each other's work
- validate and test changes before pushing them live
- automate repetitive build work with coding tools

## Multi-developer workflows

The ADK supports team workflows out of the box.

It preserves the same guardrails as Agent Studio, so developers cannot push changes that are incompatible with the project.

!!! tip "Git-like, but for Agent Studio"

    Think of the ADK as the local development layer for Agent Studio: pull, edit locally, validate, and push.

## Next steps

<div class="grid cards" markdown>

-   **No agent yet? Start with Agent Wizard**

    ---

    Build a working agent from your website in minutes, then pull it into the ADK.
    [Open Agent Wizard guide](./agent-wizard.md)

-   **Install the ADK**

    ---

    Set up the ADK and prepare your environment.
    [Open installation](./installation.md)

-   **Watch the walkthrough**

    ---

    See a practical demonstration of the ADK in use.
    [Open the walkthrough video](./walkthrough-video.md)

</div>