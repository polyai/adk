---
title: Prerequisites
description: Understand the access requirements and local tools needed before using the PolyAI ADK.
---

Before using the **PolyAI ADK**, you need the correct **platform access** and the required **local tools**.

Access is provided by your PolyAI contact:

- `developers@poly-ai.com`

## Generate API key

Log in to Agent Studio and open your workspace. In the **Data Access** tab (next to the **Users** tab), click **+ API Key** in the top right to generate a key.

![Generating an API key in Agent Studio — Data Access tab with the + API Key button highlighted](../assets/api-key-data-access.png)

Then set it as an environment variable:

~~~bash
export POLY_ADK_KEY=<your-api-key>
~~~

The `POLY_ADK_KEY` environment variable must be set before running any `poly` commands. To make it permanent, add the export line to your shell profile (for example, `~/.zshrc` or `~/.bashrc`).

Once the ADK is installed and your API key is set, you can use the `poly` command to interact with Agent Studio projects locally.

## Local requirements

Install the following tools before continuing:
Before continuing, confirm:

- You have access to an **Agent Studio workspace**
- You have obtained an **API key** 
- `uv` is installed
- `git` is available locally
  
## Local requirements

Install the following tools before continuing:

| Tool | Version | Notes |
|---|---|---|
| **uv** | latest | Manages Python and virtual environments |
| **Git** | any | Required to clone the repository or contribute |

### Install uv

`uv` manages Python versions for you, including the version required by the ADK. Install it with:

~~~bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~~~

Alternatively, with Homebrew on macOS:

~~~bash
brew install uv
~~~

See the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/){ target="_blank" rel="noopener" } for more options.

## Checklist

Before continuing, confirm:

- You have access to an **Agent Studio workspace**
- You have generated an **API key** in Agent Studio
- `uv` is installed
- `git` is available locally

## Next step

Once these requirements are in place, continue to installation.

<div class="grid cards" markdown>

-   **Installation**

    ---

    Install the ADK and set up your local environment.
    [Open installation](./installation.md)

</div>
