---
title: PolyAI ADK Docs
description: Documentation for the PolyAI Agent Development Kit.
---

![PolyAI ADK](assets/poly-ai-adk.png)

Build and edit Agent Studio projects locally with the **PolyAI ADK**, then push them back to Agent Studio to review and deploy.

The ADK gives you a local, Git-like workflow for Agent Studio projects: pull, edit with standard tooling, validate, and push.

## From zero to a local project

A few commands take you from an empty machine to a working local copy of your agent:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # install uv (skip if you have it)
uv venv --python=3.14 --seed
source .venv/bin/activate
pip install polyai-adk
poly start                                          # sign in, get API key, create project
```

See [Getting started](get-started/get-started.md) for the full walkthrough, [Prerequisites](get-started/prerequisites.md) for local tool setup, and [First commands](get-started/first-commands.md) for a guide to `poly init` and the core CLI.

## Start here

<div class="grid cards" markdown>

-   **Not sure where to start?**

    ---

    Build a working voice agent from your website in minutes, then pull it into the ADK.
    [Open getting started guide](get-started/get-started.md)

-   **What is the ADK?**

    ---

    Understand what the ADK does and where it fits in the Agent Studio workflow.
    [Read the overview](get-started/what-is-the-adk.md)

-   **Build an agent**

    ---

    Follow the end-to-end workflow from project setup to deployment.
    [Open the tutorial](tutorials/build-an-agent.md)

-   **CLI reference**

    ---

    See every `poly` command and its flags.
    [Open CLI reference](reference/cli.md)

</div>

## What this site covers

This documentation follows the developer journey:

- understanding what the ADK is and how it fits into Agent Studio
- installing it and running the first commands
- building, reviewing, and deploying agents
- reference for all CLI commands, resource types, and tooling

## Recommended path

If you are new to the ADK, follow this order:

1. follow **Getting started** — install the ADK, run `poly start`, and create your first project
2. read **What is the PolyAI ADK?**
3. use **First commands** — explore the core CLI commands
4. continue to **Build an agent with the ADK**
