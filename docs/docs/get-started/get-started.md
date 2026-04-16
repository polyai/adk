---
title: Getting started with PolyAI
description: Learn how to build your first PolyAI agent in minutes, then connect it to the ADK for local development.
---

# Not sure where to start?

If you do not yet have an agent in Agent Studio, or if you are feeling stuck before diving into local development, you can build a personalised agent from your company website in a few minutes — no configuration required. The agent lives in Agent Studio as a normal project, which means you can pull it straight into the ADK and continue development locally the moment it is ready.

---

## New to PolyAI — build your first agent

If you do not yet have access to Agent Studio or an existing agent, start here.

### Step 1 — Get access to Agent Studio

Go to [poly.ai/waitlist](https://poly.ai/waitlist) and sign up using a work email address for instant access. If your organisation already has a PolyAI workspace, ask your PolyAI contact to add you directly. See [Access and waitlist](./access-and-waitlist.md) for details on the Early Access Program and what you need to get started.

### Step 2 — Create an agent from your website

Once you are inside Agent Studio:

1. Click the **+ Agent** button in the top-right corner.
2. Select **Agent wizard** from the dropdown.
3. Enter your company website URL and click **Create agent**.

Agent Studio crawls your website and generates a working agent configuration — usually within a few minutes. While it builds, you can choose the voice your agent will use.

![Agent building step — showing Analyzing website, Retrieving data, and voice selection](../assets/agent-wizard-build.png)

!!! tip "What gets generated"

    Agent Studio creates flows, topics, and agent settings based on your website's public content. Everything it produces is standard ADK-compatible configuration — you can pull it down and edit every file locally.

### Step 3 — Test your agent in Agent Studio

Once the agent is ready, test it inside Agent Studio to confirm it responds as expected. This gives you a working baseline before you move to local development.

### Step 4 — Find your account and project IDs

To pull the agent into the ADK, you need two identifiers from Agent Studio. You can find them in the URL when your project is open:

```
https://studio.poly.ai/<account_id>/<project_id>/...
```

Copy both values — you will need them in the next step.

### Step 5 — Pull the agent into the ADK

Once the [ADK is installed](./installation.md), link your local folder to the project and pull its configuration down:

```bash
poly init --account_id <account_id> --project_id <project_id>
poly pull
```

[`poly init`](../reference/cli.md#poly-init) connects your local folder to the Agent Studio project. [`poly pull`](../reference/cli.md#poly-pull) downloads all the configuration — flows, topics, agent settings, and more — as local YAML and Python files.

You now have a fully editable local copy of your agent.

### Step 6 — Continue with the ADK

From here, the standard ADK workflow applies. You can:

- edit resources locally with any tooling
- create branches with `poly branch create`
- track changes with `poly status` and `poly diff`
- validate and push changes back with `poly push`

<div class="grid cards" markdown>

-   **Build an agent with the ADK**

    ---

    Follow the full step-by-step workflow for local development.
    [Open the tutorial](../tutorials/build-an-agent.md)

</div>

---

## Already have an agent in Agent Studio?

If you already have an agent in Agent Studio — built in the browser editor, by a PolyAI team, or using any other method — you can connect it directly to the ADK. The ADK connects to any existing Agent Studio project using the same `poly init` + `poly pull` workflow described above.

1. Complete [Prerequisites](./prerequisites.md) to generate your API key and install local tools.
2. Follow [Installation](./installation.md) to install the ADK.
3. Find your `account_id` and `project_id` in the Agent Studio URL.
4. Run:

    ```bash
    poly init --account_id <account_id> --project_id <project_id>
    poly pull
    ```

Your local folder will mirror the project in Agent Studio and you can begin editing immediately.

---

## Next step

Once you have an agent in Agent Studio, continue to the prerequisites page to set up your API key and local tools.

<div class="grid cards" markdown>

-   **Prerequisites**

    ---

    Confirm the access and local tools needed before installation.
    [Open prerequisites](./prerequisites.md)

-   **What is the ADK?**

    ---

    Understand what the ADK does and how it fits into the Agent Studio workflow.
    [Read the overview](./what-is-the-adk.md)

</div>
