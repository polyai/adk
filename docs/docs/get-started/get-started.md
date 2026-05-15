---
title: Getting started with PolyAI
description: Go from zero to a working local agent project in minutes using the ADK CLI.
---

# Getting started

The fastest way to get up and running is entirely from the command line. Two steps — install the ADK, then run `poly start` — take you from an empty machine to a local project you can edit, push, and deploy.

---

## Step 1 — Install the ADK

You need **uv** to manage the Python environment. If you already have it, skip the first line.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # or: brew install uv
```

Then create a virtual environment and install the ADK:

```bash
uv venv --python=3.14 --seed
source .venv/bin/activate
pip install polyai-adk
```

Confirm it worked:

```bash
poly --help
```

!!! info "Suppress SyntaxWarnings from platform-generated code"

    Platform-generated code uses regex patterns (such as `\d`) that trigger `SyntaxWarning` in Python 3.14's stricter string handling. This produces 40+ warning lines on every `poly` command and obscures normal output.

    To suppress them, set this before running any `poly` command:

    ```bash
    export PYTHONWARNINGS=ignore
    ```

!!! tip "Optional — install the VS Code / Cursor extension"

    If you plan to work in **VS Code** or **Cursor**, you can also install the [PolyAI ADK extension](../reference/tooling.md#polyai-adk-extension-for-vs-code-and-cursor) for resource-aware editing on top of the CLI. The extension is additive — the `poly` command remains the source of truth for every workflow.

## Step 2 — Sign in and set up your API key

```bash
poly start
```

`poly start` handles everything you need to authenticate:

1. **Sign up or sign in** — opens a browser window for authentication. This can be on any device, not just the machine running the CLI.
2. **API key** — generates a key and saves it to `~/.poly/credentials.json`. Future `poly` commands pick it up automatically — no environment variables to manage.
3. **Create a project** — optionally creates a new Agent Studio project and pulls it down locally so you can start editing immediately.

!!! tip "Already have an account?"
    If `poly start` detects an existing API key (from the credential file or an environment variable), it skips authentication and goes straight to project creation.

??? note "Manual API key setup"

    If you prefer to manage API keys through the Agent Studio UI:

    1. Log in to [Agent Studio](https://studio.poly.ai) and open your workspace.
    2. In the **API Keys** tab (next to the **Users** tab), click **+ API key**.

    ![Generating an API key in Agent Studio — API Keys tab with the + API key button highlighted](../assets/api-key-data-access.png)

    Then export the key:

    ```bash
    export POLY_ADK_KEY=<your-api-key>
    ```

    To make it permanent, add the export line to your shell profile (`~/.zshrc` or `~/.bashrc`).

!!! info "How the ADK resolves API keys"
    The ADK checks for credentials in the following order:

    1. **Credential file** — `~/.poly/credentials.json` (written by `poly start`)
    2. **Region-specific env var** — e.g. `POLY_ADK_KEY_US`
    3. **General env var** — `POLY_ADK_KEY`

    The first match wins. If nothing is found, the CLI raises an error.

    If you work across multiple regions, you can set region-scoped variables. See [per-region API keys](#per-region-api-keys) below.

## Step 3 — Start building

If `poly start` created a project for you, `cd` into the project directory. Otherwise, connect to an existing project:

```bash
poly init
```

[`poly init`](../reference/cli.md#poly-init) walks you through interactive dropdowns to pick a region, account, and project, then pulls the configuration locally.

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

## Per-region API keys

If you work across multiple regions, you can set region-scoped environment variables. The ADK checks the credential file first, then region-scoped env vars, then `POLY_ADK_KEY`.

| Region | Environment variable |
|---|---|
| `us-1` | `POLY_ADK_KEY_US` |
| `euw-1` | `POLY_ADK_KEY_EUW` |
| `uk-1` | `POLY_ADK_KEY_UK` |
| `studio` | `POLY_ADK_KEY_STUDIO` |
| `staging` | `POLY_ADK_KEY_STAGING` |
| `dev` | `POLY_ADK_KEY_DEV` |

```bash
export POLY_ADK_KEY_US=<your-us-api-key>
export POLY_ADK_KEY=<your-fallback-api-key>   # used for any other region
```

---

## Next step

<div class="grid cards" markdown>

-   **What is the ADK?**

    ---

    Understand what the ADK does and how it fits into Agent Studio.
    [Read the overview](./what-is-the-adk.md)

</div>
