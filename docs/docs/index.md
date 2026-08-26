---
title: PolyAI ADK Docs
description: Documentation for the PolyAI Agent Development Kit.
---

![PolyAI ADK](assets/poly-ai-adk.png)

Build and edit Agent Studio projects locally with the **PolyAI ADK**, then push them back to Agent Studio to review and deploy.

The ADK gives you a local, Git-like workflow for Agent Studio projects: pull, edit with standard tooling, validate, and push.

## Prerequisites

**Required**:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) for package management

## Install

```bash
uv tool install polyai-adk
```

## Authentication

You can login or sign up to a PolyAI Agent Studio account using the `login` command. Select your account's region if you are an enterprise user or "studio" if you have a self-serve account.
```bash
poly login
```

You can also export your API key manually and set it as an environment variable. See [Getting started](get-started/get-started.md#manual-api-key-export).

!!! warning "Creating an account"
    It is only possible to create self-serve accounts. If you require an account and are a PolyAI enterprise customer, please get in touch with your PolyAI contact.

## Start building

Create a new project:
```bash
poly project create
```

Load an existing project:
```bash
poly init
```

Open your project:
```bash
cd <account_id>/<project_id>
```

Begin making changes and use the CLI to sync changes back to Agent Studio
```bash
poly diff # See changes made
poly push # Push changes back to Agent Studio
poly chat # Test changes by chatting against your agent
```

See [Getting started](get-started/get-started.md) for the full walkthrough.

## Next steps

<div class="grid cards" markdown>

-   **What is the ADK?**

    ---

    Understand what the ADK does and where it fits in the Agent Studio workflow.
    [Read the overview](get-started/what-is-the-adk.md)

-   **Getting started**

    ---

    The full walkthrough — both account types, the manual API key fallback, and multi-region setups.
    [Open getting started](get-started/get-started.md)

-   **Build an agent**

    ---

    Follow the end-to-end workflow from project setup to deployment.
    [Open the tutorial](tutorials/build-an-agent.md)


-   **CLI reference**

    ---

    See every `poly` command and its flags.
    [Open CLI reference](reference/cli.md)

-   **Resource reference**

    ---

    See ADK resources and how to use them.
    [Open resource reference](reference/resources.md)

</div>
