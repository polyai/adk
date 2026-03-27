---
title: Installation
description: Install the PolyAI ADK and prepare your local environment.
---

!!! warning "Early access"

    The PolyAI ADK is currently in Early Access. Availability is limited, and some functionality may change before general release.

    [Join the waitlist](https://fehky.share-eu1.hsforms.com/2oSGLpUctRvyqXcb6K44DAQ){ target="_blank" rel="noopener" }

The **PolyAI ADK** can be installed as a Python package.

## Install the ADK

Install the package with pip:

~~~bash
pip install polyai-adk
~~~

Once installed, you can use the `poly` command to interact with Agent Studio projects locally.

## Verify the installation

Confirm the CLI is available:

~~~bash
poly --help
~~~

You should see the top-level command help if installation succeeded.

## Development setup from source

To contribute to the ADK or work directly from the repository:

~~~bash
git clone https://github.com/polyai/adk.git
cd adk
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
~~~

This installs the project in editable mode and registers the development hooks.

## Next step

Once the ADK is installed, continue to the first commands page to explore the CLI.

<div class="grid cards" markdown>

-   **First commands**

    ---

    Learn the core ADK commands and how to inspect the CLI.
    [Open first commands](./first-commands.md)

</div>