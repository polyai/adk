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

To confirm that the CLI is available, run:

~~~bash
poly --help
~~~

If installation has completed successfully, this will display the top-level command help.

## Development setup from source

If you are contributing to the ADK itself or working directly from the repository, you can set it up locally from source instead.

~~~bash
git clone https://github.com/polyai/adk.git
cd adk
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
~~~

This installs the project in editable mode and enables the repository’s development hooks.

## Running tests

To run the test suite:

~~~bash
pytest
~~~

Test files are located in `src/poly/tests/`.

## Next step

Once the ADK is installed, continue to the first commands page to explore the CLI.

<div class="grid cards" markdown>

-   **First commands**

    ---

    Learn the core ADK commands and how to inspect the CLI.
    [Open first commands](./first-commands.md)

</div>