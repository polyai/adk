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

Activate the virtual environment:

~~~bash
source .venv/bin/activate
~~~

Install the package with pip:

~~~bash
pip install polyai-adk
~~~

## Generate API key

Log in to Agent Studio and open your workspace. In the **Data Access** tab (next to the **Users** tab), click **+ API Key** in the top right to generate a key. Then set it as an environment variable:

~~~bash
export POLY_ADK_KEY=<your-api-key>
~~~

The `POLY_ADK_KEY` environment variable must be set before running any `poly` commands. To make it permanent, add the export line to your shell profile (for example, `~/.zshrc` or `~/.bashrc`).

Once the ADK is installed and your API key is set, you can use the `poly` command to interact with Agent Studio projects locally.

## Verify the installation

Confirm the CLI is available:

~~~bash
poly --help
~~~

You should see the top-level command help if installation succeeded.

## Next step

Continue to the first commands page to explore the CLI.

<div class="grid cards" markdown>

-   **First commands**

    ---

    Learn the core ADK commands and how to inspect the CLI.
    [Open first commands](./first-commands.md)

</div>
