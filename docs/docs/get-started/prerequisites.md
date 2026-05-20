---
title: Prerequisites
description: Local tools and API key setup for the PolyAI ADK.
---

Before using the **PolyAI ADK**, you need a couple of local tools. If you run into any issues, contact [developers@poly-ai.com](mailto:developers@poly-ai.com).

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

The ADK needs an API key to communicate with Agent Studio. How you obtain it depends on your account type:

- **Self-serve accounts** ([studio.poly.ai](https://studio.poly.ai)) — `poly start` signs you in and saves the key automatically.
- **Enterprise accounts** (regional clusters such as `us-1`, `euw-1`, `uk-1`) — create the key in the Agent Studio UI and export it locally. `poly start` is not yet supported for enterprise clusters.

See [Getting started](./get-started.md#step-2--sign-in-and-set-up-your-api-key) for the full walkthrough.

!!! warning "API keys are workspace-scoped"
    An API key grants access to one specific Agent Studio workspace. When you run `poly init`, it lists all projects visible to that key. If you see projects that don't look like yours, you may be using a key scoped to the wrong workspace. Contact your PolyAI contact to confirm.

## Checklist

Before continuing, confirm:

- `uv` is installed
- You have an API key — saved by `poly start` (self-serve) or exported manually (enterprise)

## Next step

<div class="grid cards" markdown>

-   **Getting started**

    ---

    Install the ADK, sign in, and create your first project.
    [Open getting started](./get-started.md)

</div>
