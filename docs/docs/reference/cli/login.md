---
title: poly login
description: Reference for the `poly login` command.
---

# `poly login`

Sign in to an existing Agent Studio account and save API key credentials for the CLI. Works against any region.

For first-time onboarding, [`poly setup`](./setup.md) runs this same sign-in flow plus shell completion, AI agent skills, and project setup in one command.

`poly login`:

1. Prompts for a region if `--region` is not supplied.
2. Opens a browser window for sign-in via the Auth0 device authorization flow.
3. Fetches or creates an ADK key for your user and saves it to `~/.poly/credentials.json` under the chosen region.

On an enterprise region (`us-1`, `uk-1`, `euw-1`) your account must already be provisioned by PolyAI. If it isn't, the command stops with a message saying so; `studio` is the self-serve region, where signing in creates your workspace.

Run `poly login` once per region you need access to — credentials for multiple regions are stored side by side in the credential file.

Examples:

~~~bash
poly login
poly login --region us
poly login --region eu
poly login --region uk
poly login --region studio
~~~

| Flag | Description |
|---|---|
| `--region` | Region to log in to. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). If omitted, you are prompted to pick one. |

## ADK key vs account API key

ADK commands authenticate with the ADK key that `poly login` saves to `~/.poly/credentials.json` for each region. CI or scripts can set `POLY_ADK_KEY`, or `POLY_ADK_KEY_<REGION>` (`POLY_ADK_KEY_US`, `POLY_ADK_KEY_EUW`, `POLY_ADK_KEY_UK`, `POLY_ADK_KEY_STUDIO`) instead.

The account API key in `POLY_API_KEY`, made by [`poly apikey`](./apikey.md) or the developer home, is for the PolyAI APIs. The ADK does not read it, so exporting it does not log the CLI in. When no ADK key is found for a region, the command says so, names any other regions you already hold a key for, and points out when `POLY_API_KEY` is the only key set.
