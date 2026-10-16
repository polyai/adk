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
3. Fetches or creates an ADK key for your user and saves it to `~/.poly/credentials.json` under the chosen region. This is the key every ADK command uses; the account API key from `POLY_API_KEY` (made by [`poly apikey`](./apikey.md) or the developer home) is for the PolyAI APIs and the ADK does not read it.

Run `poly login` once per region you need access to — credentials for multiple regions are stored side by side in the credential file.

Examples:

~~~bash
poly login
poly login --region us-1
poly login --region euw-1
poly login --region uk-1
poly login --region uk
poly login --region studio
~~~

| Flag | Description |
|---|---|
| `--region` | Region to log in to. Choices: `us-1`, `euw-1`, `uk-1`, `studio`. Aliases: `uk` → `uk-1`, `us` → `us-1`, `eu` → `euw-1`. If omitted, you are prompted to pick one. |
