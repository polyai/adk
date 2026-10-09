---
title: poly apikey
description: Reference for the `poly apikey` command.
---

# `poly apikey`

`poly apikey` is the narrower cousin of [`poly login`](./login.md): it gets you an account-scoped API key for the PolyAI APIs and Dialog RSN, not an ADK setup. It signs you in, creates (or reuses) that key, and exports it as `POLY_API_KEY` into your shell profile. Never prompts, so an AI coding assistant can run it for you. To set up the ADK itself, use [`poly setup`](./setup.md) or [`poly login`](./login.md) instead — the ADK reads its credentials from `~/.poly/credentials.json` and does not need `POLY_API_KEY`.

Examples:

~~~bash
poly apikey --region studio
poly apikey --region studio --account-id acc-123
poly apikey --region studio --key-name my-key --force
poly apikey --region us-1
~~~

`poly apikey`:

1. Signs in via the Auth0 device authorization flow. For `--region studio`, this is a dedicated client whose login page shows only "Continue with GitHub". For any other `--region`, it's the same standard sign-in page (email/SSO) that [`poly login`](./login.md) uses.
2. Calls the authorise endpoint. On `studio`, this creates your workspace if you don't already have one. On an enterprise region (`us-1`, `uk-1`, `euw-1`), your account must already be provisioned by PolyAI — the command stops with a clear message if it isn't.
3. Resolves your account id — by default, polls for up to 20 seconds for the newly created account to appear; pass `--account-id` to skip this. More than one account without `--account-id` is an error rather than a guess: the command lists the accounts found and asks you to pick one.
4. Reuses an active, unexpired API key with the default name if one already exists for the account, otherwise creates one. Unlike [`poly login`](./login.md)'s Personal Access Token, this key is **account-scoped**.
5. Saves the key to `~/.poly/credentials.json` under `--region` — but only if no entry for that region already exists there. An existing ADK credential is never overwritten, and credentials for different regions coexist independently.
6. Writes `export POLY_API_KEY="..."` (or, on Windows, sets the variable in your user environment) into your detected shell profile, so new shells and processes pick it up automatically. The ADK itself reads `~/.poly/credentials.json` and doesn't need this variable; it's exported for the PolyAI SDKs and other tools that read `POLY_API_KEY` directly.
7. Prints a summary with the key masked. The key and your sign-in token are never printed or logged.

Exit codes: `0` on success, `1` on a sign-in, account, or API failure, `2` when `POLY_API_KEY` is already set in your profile to a different value and `--force` was not passed.

!!! info "Which region should I pick?"
    `--region` is required. `studio` is the self-serve cluster individual developers sign up on via GitHub. Pick a production region (`us-1`, `uk-1`, `euw-1`) only if you already have an enterprise account provisioned there; those regions require signing in through the standard email/SSO login page rather than GitHub, since the GitHub-only client only exists for `studio`.

### Windows

Install [uv](https://docs.astral.sh/uv/) with `winget install astral-sh.uv`. If `poly` is not found after installing, run `uv tool update-shell` and open a new terminal. `POLY_API_KEY` is written to your user environment (`HKCU\Environment`) rather than a shell profile file — it is visible in new terminals and under System Properties → Environment Variables → User variables.

| Flag | Description |
|---|---|
| `--region REGION` | Region/cluster to create the key for. Required. Choices match the standard region list. |
| `--key-name NAME` | Name for the account-scoped API key. Defaults to `cli-generated-key` for `studio`, or `cli-generated-key-<region>` for any other region. |
| `--account-id ID` | Account ID to scope the key to. Skips polling for a newly created account. Required when your account has more than one - the command refuses to guess which one you mean. |
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
  "profile_shell": "zsh",
  "key_active": true
}
~~~

With `--json`, the sign-in URL and code are printed to stderr instead of being suppressed, since the JSON contract only constrains stdout and an agent that can't open a browser still needs them to complete sign-in. `key_active` is `false` if the key never finished activating within the poll window — the human-readable warning that would normally say so is suppressed in `--json` mode, so this is how an agent detects it.

!!! info "Designed for AI coding assistants"
    `poly apikey` never prompts, so it can be run unattended by an agent. It gets you an API key for the PolyAI APIs and Dialog RSN, not an ADK setup — for that, use [`poly setup`](./setup.md) or [`poly login`](./login.md), which remain the interactive path for a human at the keyboard.
