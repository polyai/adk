---
title: What is the PolyAI ADK?
description: Learn what the PolyAI Agent Development Kit is, why it exists, and how it supports local development workflows for Agent Studio.
---

# What is the PolyAI ADK?

The **PolyAI ADK (Agent Development Kit)** is a **CLI tool and Python package** for interacting with **Agent Studio** projects on your local machine.

It provides a Git-like workflow for synchronizing project configurations between your local filesystem and the Agent Studio platform.

The ADK originated as **Local Agent Studio**, an internal Deployment team tool, and was later repackaged for external use with changes such as API key authentication and the removal of internal-only process references.

## What it enables

With the ADK, developers can:

- build and edit Agent Studio projects locally
- synchronize project configuration with Agent Studio
- use Git-based workflows alongside agent development
- work with AI coding tools such as **Cursor** or **Claude Code**
- accelerate onboarding and agent building

## Why it exists

The ADK was designed to move developer workflows out of the browser and into a local development environment.

Instead of editing everything directly inside Agent Studio, developers can pull a project locally, make changes using standard development tooling, and push those changes back to the platform.

This makes it easier to:

- iterate quickly
- collaborate across multiple contributors
- run validation and tests before deployment
- use coding agents to automate work that would otherwise be manual

## Multi-developer workflows

The ADK was designed with **multi-user collaboration** in mind.

It preserves the same guardrails as Agent Studio, so developers should not be able to push changes that are incompatible with the project.

!!! tip "Git-like, but for Agent Studio"

    The ADK is best understood as a developer workflow layer for Agent Studio: pull, edit locally, validate, and push.

## Next steps

<div class="grid cards" markdown>

-   **Install the ADK**

    ---

    Set up the ADK and prepare your environment.
    [Open installation](./installation.md)

-   **Watch the walkthrough**

    ---

    See a practical demonstration of the ADK in use.
    [Open the walkthrough video](./walkthrough-video.md)

</div>