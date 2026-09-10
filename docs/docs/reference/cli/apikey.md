---
title: poly apikey
description: Reference for the `poly apikey` command.
---

# `poly apikey`

One-shot setup for an AI coding assistant: GitHub sign-in, an account-scoped API key, and `POLY_API_KEY` exported into your shell profile. Never prompts — use [`poly login`](./login.md) for the interactive, human-driven flow.

Examples:

~~~bash
poly apikey
poly apikey --account-id acc-123
poly apikey --key-name my-key --force
~~~

`poly apikey`:

1. Signs in via the Auth0 device authorization flow, against a dedicated client whose login page shows only "Continue with GitHub".
2. Calls the authorise endpoint, which creates your account if it doesn't already exist.
3. Resolves your account id — by default, polls for up to 20 seconds for the newly created account to appear; pass `--account-id` to skip this.
4. Reuses an active, unexpired API key named `cli-generated-key` if one already exists for the account, otherwise creates one. Unlike [`poly login`](./login.md)'s Personal Access Token, this key is **account-scoped**.
5. Saves the key to `~/.poly/credentials.json` under the `studio` region — but only if no `studio` entry already exists there. An existing ADK credential is never overwritten.
6. Writes `export POLY_API_KEY="..."` (or, on Windows, sets the variable in your user environment) into your detected shell profile, so new shells and processes pick it up automatically. The ADK itself reads `~/.poly/credentials.json` and doesn't need this variable; it's exported for the PolyAI SDKs and other tools that read `POLY_API_KEY` directly.
7. Prints a summary with the key masked. The key and your sign-in token are never printed or logged.

Exit codes: `0` on success, `1` on a sign-in, account, or API failure, `2` when `POLY_API_KEY` is already set in your profile to a different value and `--force` was not passed.

### Windows

Install [uv](https://docs.astral.sh/uv/) with `winget install astral-sh.uv`. If `poly` is not found after installing, run `uv tool update-shell` and open a new terminal. `POLY_API_KEY` is written to your user environment (`HKCU\Environment`) rather than a shell profile file — it is visible in new terminals and under System Properties → Environment Variables → User variables.

| Flag | Description |
|---|---|
| `--key-name NAME` | Name for the account-scoped API key. Defaults to `cli-generated-key`. |
| `--account-id ID` | Account ID to scope the key to. Skips polling for a newly created account. |
| `--force`, `-f` | Overwrite an existing `POLY_API_KEY` in your profile if it holds a different value. |

`--json` output shape:

~~~json
{
  "success": true,
  "account_id": "acc-123",
  "key_name": "cli-generated-key",
  "key_reused": false,
  "api_key_masked": "sk-n****7890",
  "credentials_file": "/home/user/.poly/credentials.json (studio)",
  "profile_path": "/home/user/.zshrc",
  "profile_shell": "zsh"
}
~~~

With `--json`, the sign-in URL and code are printed to stderr instead of being suppressed, since the JSON contract only constrains stdout and an agent that can't open a browser still needs them to complete sign-in.

## Telemetry

`poly apikey` sends anonymous usage events (`apikey_started`, `apikey_authenticated`, `apikey_account_resolved`, `apikey_key_reused`/`apikey_key_created`, `apikey_env_written`, `apikey_completed`, `apikey_failed`) to help improve the flow; the API key and sign-in token are never included. Set `DO_NOT_TRACK=1` or `POLY_NO_TELEMETRY=1` to opt out.

!!! info "Designed for AI coding assistants"
    `poly apikey` never prompts, so it can be run unattended by an agent. It is not a replacement for [`poly login`](./login.md) — that remains the interactive path for a human at the keyboard.
