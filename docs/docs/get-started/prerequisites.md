---
title: Prerequisites
description: Local tools and API key setup for the PolyAI ADK.
---

Before using the **PolyAI ADK**, you need a couple of local tools and an API key.

## Local requirements

| Tool | Version | Notes |
|---|---|---|
| **uv** | latest | Manages Python and virtual environments |
| **Git** | any | Optional — recommended for version control of your local project files |

### Install uv

`uv` manages Python versions for you, including the version required by the ADK. Install it with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Alternatively, with Homebrew on macOS:

```bash
brew install uv
```

See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/){ target="_blank" rel="noopener" } for more options.

## API key

The ADK needs an API key to communicate with Agent Studio.

### `poly start` (recommended)

Run `poly start` after [installing the ADK](./installation.md). It handles account creation (or sign-in), API key generation, and credential storage in one step. The key is saved to `~/.poly/credentials.json` and picked up automatically by every `poly` command — no environment variables to set.

```bash
poly start
```

See [Getting started](./get-started.md) for the full walkthrough.

??? note "Manual setup — generate a key in Agent Studio"

    If you prefer to manage API keys yourself:

    1. Log in to [Agent Studio](https://studio.poly.ai) and open your workspace.
    2. In the **API Keys** tab (next to the **Users** tab), click **+ API key**.

    ![Generating an API key in Agent Studio — API Keys tab with the + API key button highlighted](../assets/api-key-data-access.png)

    Then export the key:

    ```bash
    export POLY_ADK_KEY=<your-api-key>
    ```

    To make it permanent, add the export line to your shell profile (`~/.zshrc` or `~/.bashrc`). See [per-region keys](./installation.md#per-region-api-keys) if you work across multiple regions.

!!! info "How the ADK resolves API keys"
    The ADK checks for credentials in the following order:

    1. **Credential file** — `~/.poly/credentials.json` (written by `poly start`)
    2. **Region-specific env var** — e.g. `POLY_ADK_KEY_US` (see [per-region keys](./installation.md#per-region-api-keys))
    3. **General env var** — `POLY_ADK_KEY`

    The first match wins. If nothing is found, the CLI raises an error.

!!! warning "API keys are workspace-scoped"
    An API key grants access to one specific Agent Studio workspace. When you run `poly init`, it lists all projects visible to that key. If you see projects that don't look like yours, you may be using a key scoped to the wrong workspace. Contact your PolyAI contact to confirm.

## Checklist

Before continuing, confirm:

- `uv` is installed
- You have an API key — either saved by `poly start` or exported manually

## Next step

<div class="grid cards" markdown>

-   **Installation**

    ---

    Install the ADK and set up your local environment.
    [Open installation](./installation.md)

</div>
