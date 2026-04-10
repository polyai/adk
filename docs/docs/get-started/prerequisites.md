---
title: Prerequisites
description: Understand the access requirements and local tools needed before using the PolyAI ADK.
---

Before using the **PolyAI ADK**, you need the correct **platform access** and the required **local tools**.

## Platform access

To use the ADK, you must have:

- access to a **workspace in PolyAI Agent Studio**
- a valid **API key**

Access and API credentials are provided by your PolyAI contact.

If you need access to the PolyAI platform, contact:

- `developers@poly-ai.com`

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

- [ ] You have access to an **Agent Studio workspace**
- [ ] You have obtained an **API key** from your PolyAI contact
- [ ] `uv` is installed
- [ ] `git` is available locally

## Next step

Once these requirements are in place, continue to installation.

<div class="grid cards" markdown>

-   **Installation**

    ---

    Install the ADK and set up your local environment.
    [Open installation](./installation.md)

</div>
