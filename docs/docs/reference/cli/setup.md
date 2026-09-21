---
title: poly setup
description: Reference for the `poly setup` command.
---

# `poly setup`

Set up everything the ADK needs in one command: authentication, shell completion, AI agent skills, and a project. Each step is skipped automatically if it is already done, so `poly setup` is safe to re-run at any time.

Examples:

~~~bash
poly setup
poly setup --region us-1
poly setup --skip-auth --agent claude-code
poly setup --dev -g
~~~

The four steps, in order:

1. **Authentication** — runs the browser sign-in flow and saves an API key, exactly like [`poly login`](./login.md). Skipped if credentials already exist.
2. **Shell completion** — installs tab completion for your shell. For bash and zsh this appends an `eval "$(poly completion <shell>)"` line to your rc file; for fish it writes `~/.config/fish/completions/poly.fish`. Skipped if already configured. See [`poly completion`](./completion.md) for the manual route.
3. **AI agent skills** — installs the ADK skills into coding agents detected on your machine (Claude Code, Cursor, Codex, and others) via the `npx skills` package. Skipped with a warning if Node.js 18+ is not available — a missing Node never fails setup.
4. **Project** — offers to create a new Agent Studio project or connect an existing one, as [`poly project create`](./project.md) and [`poly init`](./init.md) do. Skipped if the directory already contains a project.

| Flag | Description |
|---|---|
| `--region` | Region to sign in to. If omitted, you will be prompted to select one. |
| `--base-path` | Base path for project setup. Defaults to the current working directory. |
| `--skip-auth` | Skip the authentication step. |
| `--skip-skills` | Skip installing AI agent skills. |
| `--agent NAME` | Install skills only into this coding agent (repeatable), e.g. `claude-code`, `cursor`, `codex`. |
| `--dev` | Install skills from the local `./skills` directory instead of the published ADK repo (for skill development). |
| `--global`, `-g` | Install skills user-level (available in every project) instead of into the current project. |

!!! info "The skills step needs Node.js 18+"

    Skill installation shells out to `npx`, which requires Node.js 18 or newer. Without it, the step is skipped with a warning and the rest of setup completes normally — install Node and re-run `poly setup` to add the skills later.

!!! tip "Re-run after anything changes"

    Because every step checks whether it is already done, `poly setup` doubles as a repair command — re-run it after installing Node, switching shells, or clearing credentials, and only the missing pieces are redone.

## Related pages

- [Tooling](../../tooling/tooling.md) — the coding-agent integrations the skills step installs into
