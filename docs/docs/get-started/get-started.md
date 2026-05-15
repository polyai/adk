---
title: Getting started with PolyAI
description: Go from zero to a working local agent project in minutes using the ADK CLI.
---

# Getting started

The fastest way to get up and running is entirely from the command line. `poly start` handles account creation, API key setup, and project initialization in a single command — you do not need to visit Agent Studio first.

---

## From zero to a local project

### Step 1 — Install the ADK

Install `uv` (if you don't have it), create a virtual environment, and install the ADK:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # skip if uv is already installed
uv venv --python=3.14 --seed
source .venv/bin/activate
pip install polyai-adk
```

See [Installation](./installation.md) for more detail and platform-specific notes.

### Step 2 — Run `poly start`

```bash
poly start
```

`poly start` walks you through three things:

1. **Sign up or sign in** — opens a browser window for authentication. This can be on any device, not just the machine running the CLI.
2. **API key** — generates a key and saves it to `~/.poly/credentials.json`. Future `poly` commands pick it up automatically — no environment variables to manage.
3. **Create a project** — optionally creates a new Agent Studio project and pulls it down locally so you can start editing immediately.

That's it. You now have a local project directory with your agent's configuration files, ready to edit with any tooling you like.

!!! tip "Already have an account?"
    If `poly start` detects an existing API key (from the credential file or an environment variable), it skips authentication and goes straight to project creation.

### Step 3 — Start building

From inside your project directory, the core workflow is:

```bash
poly status              # see what's changed
poly diff                # inspect changes in detail
poly branch create dev   # work on a branch
poly push                # push changes to Agent Studio
poly chat                # talk to your agent
```

Edit flows, functions, topics, and other resources in your editor of choice — they're just YAML and Python files. Push when you're ready to test in Agent Studio.

<div class="grid cards" markdown>

-   **Build an agent with the ADK**

    ---

    Follow the full step-by-step tutorial for local development.
    [Open the tutorial](../tutorials/build-an-agent.md)

-   **First commands**

    ---

    Explore the full set of CLI commands available to you.
    [Open first commands](./first-commands.md)

</div>

---

## Seed an agent from your website

If you're starting from scratch and want a working baseline, you can generate an agent from your company website inside Agent Studio. This gives you topics and agent settings pre-populated from your site's public content — a useful starting point before building locally.

1. Open [Agent Studio](https://studio.poly.ai) and sign in (your `poly start` account works here).
2. Click **+ Agent** → **Quick Agent Setup**.
3. Enter your website URL and click **Create agent**.

![Quick setup button Agent Studio](../assets/quick-agent-setup.png)

Agent Studio crawls your site and generates a configuration — usually within a few minutes. Once it's ready, pull it into your local project:

```bash
poly pull
```

!!! tip "What gets generated"

    Agent Studio populates **topics** (knowledge base entries) and basic **agent settings** (personality, role, rules) from your website's public content. It does not generate flows, variants, entities, handoffs, or integrations — those are for you to build locally with the ADK.

---

## Already have an agent in Agent Studio?

If you have an existing project — built in the browser, by a PolyAI team, or by any other method — connect it to the ADK in two commands:

```bash
poly start    # sign in and save your API key (skip if already done)
poly init     # interactive prompts to pick region, account, and project
```

`poly init` creates a local directory and pulls the full project configuration. From there the standard `poly status` / `poly push` / `poly pull` workflow applies.

---

## Next step

<div class="grid cards" markdown>

-   **Installation**

    ---

    Detailed install instructions, platform notes, and per-region key setup.
    [Open installation](./installation.md)

-   **What is the ADK?**

    ---

    Understand what the ADK does and how it fits into Agent Studio.
    [Read the overview](./what-is-the-adk.md)

</div>
