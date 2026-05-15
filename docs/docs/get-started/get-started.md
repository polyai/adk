---
title: Getting started with PolyAI
description: Learn how to build your first PolyAI agent in minutes, then connect it to the ADK for local development.
---

# Not sure where to start?

If you do not yet have an agent in Agent Studio, or you want a working starting point before setting up the ADK, you can build a personalized agent from your company website in a few minutes — no configuration required. The agent lives in Agent Studio as a normal project, so you can pull it straight into the ADK and continue development locally as soon as it is ready.

---

## New to PolyAI — build your first agent

If you do not yet have access to Agent Studio or an existing agent, start here.

### Step 1 — Get access to Agent Studio

Go to [studio.poly.ai](https://studio.poly.ai) and sign up. You can sign up with your email or login with SSO.

![Agent Studio sign up for the first time](../assets/agent-studio-login.png)

### Step 2 — Create an agent from your website

![Quick setup button Agent Studio](../assets/quick-agent-setup.png)

Once you are inside Agent Studio:

1. Click the **+ Agent** button in the top-right corner.
2. Select **Quick Agent Setup** from the dropdown.
3. Enter your company website URL and click **Create agent**.

Agent Studio crawls your website and generates a working agent configuration — usually within a few minutes. Before it builds, you can choose the voice your agent will use.

![Agent building step — showing Analyzing website, Retrieving data, and voice selection](../assets/agent-build.png)

!!! tip "What gets generated"

    Agent Studio populates **topics** (knowledge base entries) and basic **agent settings** (personality, role, rules) from your website's public content. This gives you an agent that knows about your company and can answer questions — but it does not generate flows, variants, entities, handoffs, or integrations. Those are for you to build locally with the ADK. Everything that is generated is standard ADK-compatible configuration and fully editable once pulled down.

### Step 3 — Test your agent in Agent Studio

![Completed lite builder](../assets/setup-agent.png)

Once the agent is ready, test it inside Agent Studio to confirm it's filled in with information as expected. This gives you a working baseline before you move to local development.

### Step 4 — Install the ADK and run `poly start`

Once the [ADK is installed](./installation.md), run:

~~~bash
poly start
~~~

[`poly start`](../reference/cli.md#poly-start) is the recommended entry point for new users. It:

1. opens `https://studio.poly.ai` in your browser so you can sign in or create an account
2. sets up a Personal Access Token (API key) and saves it to `~/.poly/credentials.json`
3. optionally creates a first project (or you can skip this and initialize an existing one)

If you already have an API key and just want to link a local folder to an existing project, use `poly init` directly — see [Step 5](#step-5--pull-the-agent-into-the-adk) below.

### Step 5 — Pull the agent into the ADK

Link your local folder to the project you created in Agent Studio:

```bash
poly init
```

[`poly init`](../reference/cli.md#poly-init) walks you through interactive dropdowns to pick a region, account, and project. It creates a subdirectory and pulls the configuration automatically. Change into the project directory before running any further commands. See [First commands](./first-commands.md) for the full walkthrough.

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
3. Run:

    ~~~bash
    poly init
    ~~~

    `poly init` shows interactive dropdowns to pick your project. See [First commands](./first-commands.md) for details.

Your local folder will mirror the project in Agent Studio and you can begin editing immediately.

---

## Next step

Install the ADK and confirm your local tools are in place before running your first commands.

<div class="grid cards" markdown>

-   **Installation**

    ---

    Install the ADK and set up your local environment.
    [Open installation](./installation.md)

-   **What is the ADK?**

    ---

    Understand what the ADK does and how it fits into the Agent Studio workflow.
    [Read the overview](./what-is-the-adk.md)

</div>
