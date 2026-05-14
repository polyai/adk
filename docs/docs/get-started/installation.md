---
title: Installation
description: Install the PolyAI ADK and prepare your local environment.
---

The **PolyAI ADK** can be installed as a Python package.

## Install the ADK

We recommend installing in a virtual environment rather than installing to the global system Python. If you don't have `uv` installed, see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/){ target="_blank" rel="noopener" }.

Run the following to create a virtual environment:

~~~bash
uv venv --python=3.14 --seed
~~~

!!! info "Suppress SyntaxWarnings from platform-generated code"

    Platform-generated code uses regex patterns (such as `\d`) that trigger `SyntaxWarning` in Python 3.14's stricter string handling. This produces 40+ warning lines on every `poly` command and obscures normal output.

    To suppress them, set this before running any `poly` command:

    ~~~bash
    export PYTHONWARNINGS=ignore
    ~~~

Activate the virtual environment:

~~~bash
source .venv/bin/activate
~~~

Install the package with pip:

~~~bash
pip install polyai-adk
~~~

!!! tip "Optional — install the VS Code / Cursor extension"

    If you plan to work in **VS Code** or **Cursor**, you can also install the [PolyAI ADK extension](../reference/tooling.md#polyai-adk-extension-for-vs-code-and-cursor) for resource-aware editing on top of the CLI. The extension is additive — the `poly` command remains the source of truth for every workflow.

## Set your API key

If you haven't generated an API key yet, follow the steps in [Prerequisites — Generate API key](./prerequisites.md#generate-api-key).

### Per-region API keys

If you need a separate API key for a specific region, you can set a region-scoped variable alongside `POLY_ADK_KEY`. The ADK checks for the region-specific key first and falls back to `POLY_ADK_KEY` if it is not set.

| Region | Environment variable |
|---|---|
| `us-1` | `POLY_ADK_KEY_US` |
| `euw-1` | `POLY_ADK_KEY_EUW` |
| `uk-1` | `POLY_ADK_KEY_UK` |
| `studio` | `POLY_ADK_KEY_STUDIO` |
| `staging` | `POLY_ADK_KEY_STAGING` |
| `dev` | `POLY_ADK_KEY_DEV` |

For example, to use a dedicated key for the US region:

~~~bash
export POLY_ADK_KEY_US=<your-us-api-key>
export POLY_ADK_KEY=<your-fallback-api-key>   # used for any other region
~~~

`POLY_ADK_KEY` is still required as the fallback. If neither the region-specific key nor `POLY_ADK_KEY` is set, the CLI will raise an error.

## Verify the installation

Confirm the CLI is available:

~~~bash
poly --help
~~~

You should see the top-level command help if installation succeeded.

## Next step

With the ADK installed and your API key set, run `poly init` to create your local project and get familiar with the CLI.

<div class="grid cards" markdown>

-   **First commands**

    ---

    Start with `poly init`, then learn the rest of the core ADK commands.
    [Open first commands](./first-commands.md)

</div>
