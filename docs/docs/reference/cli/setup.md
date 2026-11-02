---
title: poly setup
description: Reference for the `poly setup` command.
---

# `poly setup`

Set up everything the ADK needs in one command: one sign-in that gives you both an ADK key and an account API key, `POLY_API_KEY` in your shell profile, shell completion, AI agent skills, and a project. Each step is skipped automatically if it is already done, so `poly setup` is safe to re-run at any time.

Examples:

~~~bash
poly setup
poly setup --region us
poly setup --region studio --account-id acc-123
poly setup --skip-auth --agent claude-code
poly setup --dev -g
~~~

The five steps, in order:

1. **Authentication** — one browser sign-in (on `studio`, the GitHub sign-in that creates your workspace on first login) that saves two credentials to `~/.poly/credentials.json`: the ADK key the CLI uses, as [`poly login`](./login.md) does, and an account API key for the PolyAI APIs and MCPs, as [`poly apikey`](./apikey.md) does. The sign-in is kept in `~/.poly/apikey_session` until it expires, so a machine that already has one key gains the other without a second browser round trip. The account key reuses an existing `cli-generated-key` when there is one, otherwise it is created as `setup-key`. With more than one account, a terminal shows a picker; otherwise pass `--account-id`. Skipped when both credentials exist.
2. **`POLY_API_KEY`** — offers to add one line exporting the account API key to your shell profile (or, on Windows, your user environment). This always asks separately, and is skipped when the profile already holds that value or when there is no terminal to ask; `poly apikey` writes it later in that case.
3. **Shell completion** — installs tab completion for your shell. For bash and zsh this appends an `eval "$(poly completion <shell>)"` line to your rc file; for fish it writes `~/.config/fish/completions/poly.fish`. Skipped if already configured. See [`poly completion`](./completion.md) for the manual route.
4. **AI agent skills** — installs the ADK skills into coding agents detected on your machine (Claude Code, Cursor, Codex, and others) via the `npx skills` package. Skipped with a warning if Node.js 18+ is not available — a missing Node never fails setup.
5. **Project** — offers to create a new Agent Studio project or connect an existing one, as [`poly project create`](./project.md) and [`poly init`](./init.md) do. Skipped if the directory already contains a project.

| Flag | Description |
|---|---|
| `--region` | Region to sign in to. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). If omitted, you will be prompted to select one. |
| `--account-id ID` | Account to scope the account API key to. With more than one account and no `--account-id`, a terminal shows a picker; otherwise setup stops and lists the accounts. |
| `--base-path` | Base path for project setup. Defaults to the current working directory. |
| `--skip-auth` | Skip the authentication step, and with it the `POLY_API_KEY` export. |
| `--skip-skills` | Skip installing AI agent skills. |
| `--agent NAME` | Install skills only into this coding agent (repeatable), e.g. `claude-code`, `cursor`, `codex`. |
| `--dev` | Install skills from the local `./skills` directory instead of the published ADK repo (for skill development). |
| `--global`, `-g` | Install skills user-level (available in every project) instead of into the current project. |

!!! info "The skills step needs Node.js 18+"

    Skill installation shells out to `npx`, which requires Node.js 18 or newer. Without it, the step is skipped with a warning and the rest of setup completes normally — install Node and re-run `poly setup` to add the skills later.

!!! info "Setup reports anonymous usage, and you can turn it off"

    Each run sends three events to PolyAI's PostHog: that setup started (operating system, ADK version, which coding agent ran it, which agents were found, whether credentials already existed), the outcome and duration of each step, and completion. The run is keyed by a random id until sign-in succeeds, then by your account id. No email, key value, file path or command argument is ever sent. Set `POLY_NO_TELEMETRY=1` or `DO_NOT_TRACK=1` to send nothing.

!!! tip "Re-run after anything changes"

    Because every step checks whether it is already done, `poly setup` doubles as a repair command — re-run it after installing Node, switching shells, or clearing credentials, and only the missing pieces are redone.

## Related pages

- [Tooling](../../tooling/tooling.md) — the coding-agent integrations the skills step installs into
