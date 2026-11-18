---
title: poly campaign
description: Reference for the `poly campaign` command.
---

# `poly campaign`

Validate [outbound campaigns](../resources/outbound_campaigns.md). `poly campaign` requires a subcommand.

Examples:

~~~bash
poly campaign validate 'Appointment reminders'
~~~

Every subcommand takes the campaign's name (or its folder name) and acts on the campaign as pushed, not on your local files: run [`poly push`](./push.md) first. `validate` uses your current branch; if it no longer exists, it uses `main`, says so, and adds `"branch": "main"` to the `--json` output.

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
