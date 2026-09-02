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
3. Fetches or creates an API key for your user and saves it to `~/.poly/credentials.json` under the chosen region.

Run `poly login` once per region you need access to — credentials for multiple regions are stored side by side in the credential file.

Examples:

~~~bash
poly login
poly login --region us-1
poly login --region euw-1
poly login --region uk-1
poly login --region studio
~~~

| Flag | Description |
|---|---|
| `--region` | Region to log in to. Choices: `us-1`, `euw-1`, `uk-1`, `studio`. If omitted, you are prompted to pick one. |
