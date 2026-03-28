---
title: Installation
description: Install the PolyAI ADK and prepare your local environment.
---

!!! warning "Early access"

    The PolyAI ADK is currently in Early Access. Availability is limited, and some functionality may change before general release.

    [Join the waitlist](https://fehky.share-eu1.hsforms.com/2oSGLpUctRvyqXcb6K44DAQ){ target="_blank" rel="noopener" }

The **PolyAI ADK** can be installed as a Python package.

## Install the ADK

We recommend installing in a virtual environment rather than installing to the global system Python. Run the following to create one:

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

Once installed, you can use the `poly` command to interact with Agent Studio projects locally.

## Generate API key

Set your API key as an environment variable:

~~~bash
export POLY_ADK_KEY=<your-api-key>
~~~

You can generate an API key from the Agent Studio platform. The `POLY_ADK_KEY` environment variable must be set before running any `poly` commands.

## Verify the installation

Confirm the CLI is available:

~~~bash
poly --help
~~~

You should see the top-level command help if installation succeeded.

## Next step

Once the ADK is installed, continue to the first commands page to explore the CLI.

<div class="grid cards" markdown>

-   **First commands**

    ---

    Learn the core ADK commands and how to inspect the CLI.
    [Open first commands](./first-commands.md)

</div>
