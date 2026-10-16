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

## "Another poly comes first on your PATH"

If an older `poly` sits earlier on your `PATH` than the one you just installed (a Homebrew or pip install from before, for example), typing `poly` keeps running the old one. When the `poly` that is running notices this, the first command in each terminal session prints:

~~~text
Warning: Another poly comes first on your PATH: /opt/homebrew/bin/poly (0.7.3).
This command ran /Users/you/.local/bin/poly (0.71.0); plain 'poly' runs the first one.
Remove the older install, or put /Users/you/.local/bin earlier on PATH.
~~~

Do one of the two things it suggests, then open a new terminal. The warning shows once per terminal session (a new tab shows it again until the PATH is fixed), never under `--json`, in CI, when output is not a terminal, or with `POLY_NO_UPDATE_CHECK=1`. `poly --version` and `--help` never print it. [`poly apikey`](./apikey.md) and `poly update` also carry the fact in `--json` as `shadowed_by`, so an AI coding assistant can act on it.

The check can only run inside the `poly` that is executing: if the older install is the one plain `poly` runs, it cannot warn. `which -a poly` (or `where poly` on Windows) lists every install in `PATH` order.

## Related pages

- [Tooling](../../tooling/tooling.md) — the coding-agent integrations the skills step installs into
