---
title: poly campaign
description: Reference for the `poly campaign` command.
---

# `poly campaign`

Validate and run [outbound campaigns](../resources/outbound_campaigns.md). `poly campaign` requires a subcommand.

Examples:

~~~bash
poly campaign validate 'Appointment reminders'
poly campaign publish 'Appointment reminders'
~~~

Every subcommand takes the campaign's name (or its folder name) and acts on the campaign as pushed, not on your local files: run [`poly push`](./push.md) first. `validate` uses your current branch; if it no longer exists, it uses `main`, says so, and adds `"branch": "main"` to the `--json` output. `publish`, `pause`, `resume` and `archive` act on the live campaign on `main`, whatever branch you are on, and take its name as `main` has it, so a campaign made on a branch must be merged first.

Outbound campaigns must be turned on for the project; otherwise every subcommand exits `1` and says so.

With `--json`, every `"success": false` result carries a short `error`. Once the project is loaded, it also carries `campaign`.

Agent Studio lets two campaigns share a name, and a pull renames the newer one `{name} (1)` until a push sends that name. Until then, the shared name matches both: name the campaign by its new name or its folder.

| Argument | Description |
|---|---|
| `name` | The campaign's name or folder. |

## `poly campaign validate`

Check a campaign's graph with the platform: one trigger, routes to nodes that exist, every node reachable, and each node function's `def` line. [`poly validate`](./validate.md) checks the files' fields locally; this checks the graph.

Examples:

~~~bash
poly campaign validate 'Appointment reminders'
~~~

Exits `1` when the campaign is not valid, with an `error` beside the `result` in `--json`. Warnings do not fail it.

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "result": {
    "valid": true,
    "errors": [],
    "warnings": [{"node_id": "call-1", "field": "flowName", "message": "...", "is_warning": true}]
  }
}
~~~

The `result` is the platform's own, so it refers to nodes by id; the human output shows their names, in its messages too.

## `poly campaign publish`

Publish the campaign's draft to live and start it. A paused campaign stays paused.

Examples:

~~~bash
poly campaign publish 'Appointment reminders'
~~~

| Flag | Description |
|---|---|
| `--force` | Publish without confirmation. Implied by `--json`. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "action": "publish"
}
~~~

## `poly campaign pause`

Pause the live campaign.

Examples:

~~~bash
poly campaign pause 'Appointment reminders'
~~~

| Flag | Description |
|---|---|
| `--force` | Pause without confirmation. Implied by `--json`. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "action": "pause"
}
~~~

## `poly campaign resume`

Resume the paused campaign.

Examples:

~~~bash
poly campaign resume 'Appointment reminders'
~~~

| Flag | Description |
|---|---|
| `--force` | Resume without confirmation. Implied by `--json`. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "action": "resume"
}
~~~

!!! info "Set up campaigns once in Agent Studio"

    Publishing or resuming needs the project's campaigns to have been set up, which only Agent Studio can do. If the platform says the project is not set up yet, publish or resume a campaign once in Agent Studio, then try again.

## `poly campaign archive`

Archive a draft or paused campaign. Archiving cannot be undone, and an archived campaign is no longer pulled.

Examples:

~~~bash
poly campaign archive 'Appointment reminders'
~~~

| Flag | Description |
|---|---|
| `--force` | Archive without confirmation. Implied by `--json`. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "action": "archive"
}
~~~

!!! warning "These commands act on live"

    `publish`, `pause`, `resume` and `archive` change what the live campaign does straight away. Each asks for confirmation unless you pass `--force` or `--json`. If the platform does not confirm the change, for example because the connection dropped or you stopped the command, it may still have gone through, even if Agent Studio still shows the old status: the error says so, and `--json` adds `"unconfirmed": true`. To settle it:

    - `publish` and `pause`: send the same command again. That is safe, since a campaign already in the state asked for counts as done.
    - `resume`: run it again. If it says the campaign is active, the first resume went through.
    - `archive`: run it again. If it says the campaign is not on main or is already archived, the first archive went through.

    If you didn't want the change, send the opposite command instead, such as `pause` after an unconfirmed `resume`. Archiving can't be undone.
