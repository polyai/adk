# CLI reference page structure

Every page in this directory documents one `poly` command. Follow this shape exactly so pages stay interchangeable and can be regenerated or extended without re-deriving the format each time.

## Page skeleton

```
---
title: poly <command>
description: Reference for the `poly <command>` command.
---

# `poly <command>`

<One or two sentences: what the command does. If it has subcommands, say so but do not enumerate them — "`poly x` requires a subcommand." The `##` sections and Examples block already show what they are.>

Examples:

~~~bash
poly <command>
poly <command> --some-flag value
~~~

<Any implementation detail beyond the one-liner — drift behavior, prompts,
what gets written where — goes here as prose, before the tables.>

| Argument | Description |
|---|---|
| `arg_name` | ... (omit this table if there are no positional arguments) |

| Flag | Description |
|---|---|
| `--flag` | ... (command-specific flags only, see below) |

`--json` output shape:

~~~json
{
  "success": true
}
~~~
```

Include the `--json` output shape whenever the command supports `--json` (see [`cli.md`](../cli.md#-json-contract) for the general contract — single object, exit codes, error shape) — show the actual top-level keys for *this* command, not a generic example. Omit it for commands that don't support `--json` at all.

## Subcommands

If a command has subcommands (e.g. `poly project list/create/delete`), give each one its own `##` heading — following the same skeleton (description → Examples → Argument table → Flag table → JSON output shape). `##` keeps subcommands visible in the page's table of contents.

The `Examples:` label is not optional at the top level only — it applies to every command **and** every subcommand section, with no exceptions. Every bash block on the page sits directly under an `Examples:` line.

## What belongs in the flags table — and what doesn't

Only list flags specific to this command/subcommand. Never repeat `--path`, `--json`, `--verbose`, or `--debug` — these are documented once in the "Shared flags" table on [`cli.md`](../cli.md) and apply to every command. The `--json` flag itself is never a table row; its output shape gets the dedicated block above instead.

Exception: if a flag has command-specific behavior (e.g. `--json` requiring extra explicit flags because interactive prompts aren't available), call that out in a `!!! info` admonition rather than adding a table row.

## What doesn't belong on these pages

- **No "Error handling" sections.** Don't enumerate error messages/situations per command — this is implementation detail, not something a user reaches for.
- **No restating global behavior** (retries, auth, base path resolution) — that lives once on `cli.md`.

## Cross-links

Link to sibling command pages with relative paths (`./push.md`, `../resources/tests.md`) inline, wherever they're relevant to the sentence.

Links to a `development/` concept page are different — never inline. Collect them in a `## Related pages` section at the bottom of the page instead, e.g.:

~~~markdown
## Related pages

- [Real-time configuration](../../development/real-time-configuration.md) — how RTC fits the development workflow
~~~

Check both directions: if a `development/` page links to this command page, this command page should link back to it. A one-way link from the concept page is a sign this page is missing its `## Related pages` section.

## Admonitions

Use `!!! warning` for destructive or hard-to-reverse behavior (e.g. `poly rtc push --env live` writing straight to production), `!!! tip` for workflow advice, `!!! info` for flag-interaction edge cases. Place them after the flags table.

Every admonition gets a quoted title — `!!! warning "Reverting cannot be undone"`, never a bare `!!! warning` with nothing after it. A bare admonition renders with the generic "Warning"/"Info" label instead of something scannable.
