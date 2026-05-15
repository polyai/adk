---
title: Installation
description: Install the PolyAI ADK and prepare your local environment.
---

The **PolyAI ADK** is a Python package. We recommend installing in a virtual environment.

## Install the ADK

If you don't have `uv` installed, see [Prerequisites](./prerequisites.md#install-uv).

```bash
uv venv --python=3.14 --seed
source .venv/bin/activate
pip install polyai-adk
```

!!! info "Suppress SyntaxWarnings from platform-generated code"

    Platform-generated code uses regex patterns (such as `\d`) that trigger `SyntaxWarning` in Python 3.14's stricter string handling. This produces 40+ warning lines on every `poly` command and obscures normal output.

    To suppress them, set this before running any `poly` command:

    ```bash
    export PYTHONWARNINGS=ignore
    ```

Verify the CLI is available:

```bash
poly --help
```

!!! tip "Optional — install the VS Code / Cursor extension"

    If you plan to work in **VS Code** or **Cursor**, you can also install the [PolyAI ADK extension](../reference/tooling.md#polyai-adk-extension-for-vs-code-and-cursor) for resource-aware editing on top of the CLI. The extension is additive — the `poly` command remains the source of truth for every workflow.

## Authenticate

Run `poly start` to sign in (or create an account) and save your API key:

```bash
poly start
```

Your API key is saved to `~/.poly/credentials.json` and used automatically by all `poly` commands. No environment variables needed.

`poly start` can also create your first project and pull it down locally — follow the prompts or see [Getting started](./get-started.md) for the full walkthrough.

??? note "Manual API key setup"

    If you prefer environment variables, generate a key in Agent Studio and export it:

    ```bash
    export POLY_ADK_KEY=<your-api-key>
    ```

    See [Prerequisites — Manual setup](./prerequisites.md#api-key) for step-by-step instructions.

### Per-region API keys

If you work across multiple regions, you can set region-scoped environment variables. The ADK checks for these before falling back to the credential file and `POLY_ADK_KEY`.

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

## Next step

<div class="grid cards" markdown>

-   **First commands**

    ---

    Start with `poly init`, then learn the rest of the core ADK commands.
    [Open first commands](./first-commands.md)

</div>
