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
| **Python** | 3.14+ | Required to run the ADK |
| **uv** | latest | Recommended for development setup from source |
| **Git** | any | Required to clone the repository or contribute |

### Install Python 3.14+

Python 3.14 is a recent release. Use one of these methods:

- **Homebrew** (macOS): `brew install python@3.14`
- **pyenv**: `pyenv install 3.14` then `pyenv global 3.14`
- **Official installer**: [python.org/downloads](https://www.python.org/downloads/){ target="_blank" rel="noopener" }

### Install uv

The recommended way to install `uv`:

~~~bash
curl -LsSf https://astral.sh/uv/install.sh | sh
~~~

Alternatively, with Homebrew on macOS:

~~~bash
brew install uv
~~~

## Checklist

Before continuing, confirm:

- [ ] You have access to an **Agent Studio workspace**
- [ ] You have obtained an **API key** from your PolyAI contact
- [ ] Python 3.14+ is installed and on your `PATH`
- [ ] `uv` is installed if you plan to use the development setup
- [ ] `git` is available locally

## Next step

Once these requirements are in place, continue to installation.

<div class="grid cards" markdown>

-   **Installation**

    ---

    Install the ADK and set up your local environment.
    [Open installation](./installation.md)

</div>