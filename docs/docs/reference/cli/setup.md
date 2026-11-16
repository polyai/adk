---
title: poly setup
description: Reference for the `poly setup` command.
---

# `poly setup`

Set up everything the ADK needs in one command: authentication, an optional account API key, shell completion, AI agent skills, and a project. Each step is skipped automatically if it is already done, so `poly setup` is safe to re-run at any time.

Examples:

~~~bash
poly setup
poly setup --region us
poly setup --skip-auth --agent claude-code
poly setup --dev -g
~~~

The five steps, in order:

1. **Authentication** — runs the browser sign-in flow and saves an ADK key, as [`poly login`](./login.md) does. Skipped if credentials already exist.
2. **Account API key (optional)** — asks whether to set up an account API key for the PolyAI APIs, and if you say yes runs [`poly apikey`](./apikey.md), which creates the key and exports `POLY_API_KEY` to your shell profile. It reuses the sign-in from step 1, so there is no second browser trip. The ADK itself does not need this key. Skipped when `POLY_API_KEY` is already in your profile, with `--skip-auth`, or when there is no terminal to ask; run `poly apikey` yourself in that case.
3. **Shell completion** — installs tab completion for your shell. For bash and zsh this appends an `eval "$(poly completion <shell>)"` line to your rc file; for fish it writes `~/.config/fish/completions/poly.fish`. Skipped if already configured. See [`poly completion`](./completion.md) for the manual route.
4. **AI agent skills** — installs the ADK skills into coding agents detected on your machine (Claude Code, Cursor, Codex, and others) via the `npx skills` package. Skipped with a warning if Node.js 18+ is not available — a missing Node never fails setup.
5. **Project** — offers to create a new Agent Studio project or connect an existing one, as [`poly project create`](./project.md) and [`poly init`](./init.md) do. Skipped if the directory already contains a project.

| Flag | Description |
|---|---|
| `--region` | Region to sign in to. One of `us`, `eu`, `uk`, `studio` — see [Regions](../cli.md#regions). If omitted, you will be prompted to select one. |
| `--base-path` | Base path for project setup. Defaults to the current working directory. |
| `--skip-auth` | Skip the authentication step and the account API key step. |
| `--skip-skills` | Skip installing AI agent skills. |
| `--agent NAME` | Install skills only into this coding agent (repeatable), e.g. `claude-code`, `cursor`, `codex`. |
| `--dev` | Install skills from the local `./skills` directory instead of the published ADK repo (for skill development). |
| `--global`, `-g` | Install skills user-level (available in every project) instead of into the current project. |

!!! info "The skills step needs Node.js 18+"

    Skill installation shells out to `npx`, which requires Node.js 18 or newer. Without it, the step is skipped with a warning and the rest of setup completes normally — install Node and re-run `poly setup` to add the skills later.

!!! info "Anonymous usage telemetry"

    `poly setup` sends anonymous usage telemetry. Set `POLY_NO_TELEMETRY=1` or `DO_NOT_TRACK=1` to turn it off.

!!! tip "Re-run after anything changes"

    Because every step checks whether it is already done, `poly setup` doubles as a repair command — re-run it after installing Node, switching shells, or clearing credentials, and only the missing pieces are redone.

## Related pages

- [Tooling](../../tooling/tooling.md) — the coding-agent integrations the skills step installs into
