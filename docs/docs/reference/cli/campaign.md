---
title: poly campaign
description: Reference for the `poly campaign` command.
---

# `poly campaign`

Validate, preview, test and run [outbound campaigns](../resources/outbound_campaigns.md). `poly campaign` requires a subcommand.

Examples:

~~~bash
poly campaign validate 'Appointment reminders'
poly campaign preview 'Appointment reminders' --phone +15550100
poly campaign publish 'Appointment reminders'
~~~

Every subcommand takes the campaign's name (or its folder name) and acts on the campaign as pushed, not on your local files: run [`poly push`](./push.md) first. `validate` and `preview` use your current branch. `test`, `publish`, `pause`, `resume` and `archive` act on the live campaign on `main`, whatever branch you are on, so a campaign made on a branch must be merged first.

| Argument | Description |
|---|---|
| `name` | The campaign's name. |

## `poly campaign validate`

Check a campaign's graph with the platform: one trigger, routes to nodes that exist, every node reachable, and each node function's `def` line. [`poly validate`](./validate.md) checks the files' fields locally; this checks the graph.

Examples:

~~~bash
poly campaign validate 'Appointment reminders'
~~~

Exits `1` when the campaign is not valid. Warnings do not fail it.

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "valid": true,
  "errors": [],
  "warnings": [{"node_id": "call-1", "field": "flowName", "message": "...", "is_warning": true}]
}
~~~

## `poly campaign preview`

Walk a made-up contact through the campaign to the next call, condition or end. Nothing is called, texted or stored, and node functions are not run: say what each returns with `--sample-outputs`.

Examples:

~~~bash
poly campaign preview 'Appointment reminders' --phone +15550100 --field first_name=Ada
poly campaign preview 'Appointment reminders' --contact contact.json --sample-outputs outputs.json
poly campaign preview 'Appointment reminders' --phone +15550100 --start-node call-1 --call-result no_answer
~~~

| Flag | Description |
|---|---|
| `--contact` | JSON file with the contact's data, as an import would carry it. |
| `--phone` | The contact's phone number. |
| `--first-name` | The contact's first name. |
| `--field` | Another contact column, as `KEY=VALUE`. Repeatable. |
| `--sample-outputs` | JSON file of what each node's function returns, keyed by node id. |
| `--start-node` | Node id to carry on from. Defaults to the trigger. |
| `--call-result` | How the call being left ended, e.g. `no_answer`. |
| `--tool-called` | A tool the agent called on that call. Repeatable. |
| `--ask-branches` | Stop at a condition with no sample output instead of taking its default branch. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "steps": [],
  "stopped_at": "call-1",
  "stop_reason": "call",
  "error": null,
  "notes": []
}
~~~

## `poly campaign test`

Run one step of a test of the live campaign, and wait for it to finish. It calls and texts the test contact for real. The first step starts at the trigger; to carry on, pass the node it stopped at and the run it printed.

Examples:

~~~bash
poly campaign test 'Appointment reminders' --phone +15550100
poly campaign test 'Appointment reminders' --phone +15550100 --start-node call-1 --run run.json --call-result no_answer
~~~

| Flag | Description |
|---|---|
| `--contact` | JSON file with the test contact: `phone`, `firstName`, `lastName`, `externalId`, `metadata`. |
| `--phone` | Number to call and text. |
| `--first-name`, `--last-name` | The contact's name. |
| `--external-id` | The contact's id in your own system. |
| `--field` | A metadata column, as `KEY=VALUE`. Repeatable. |
| `--start-node` | Node id to carry on from. |
| `--run` | The run the previous step printed, as JSON or a JSON file. |
| `--call-result` | How the call being left ended. |
| `--tool-called` | A tool the agent called on that call. Repeatable. |
| `--timeout` | Seconds to wait for the step. Defaults to `600`. |
| `--force` | Run without confirmation. Implied by `--json`. |

!!! warning "This contacts a real phone"

    `poly campaign test` runs the live campaign and calls or texts the number you give it.

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "step_id": "TSTEP-...",
  "status": "done",
  "run": {"contact_id": "...", "enrolment_id": "...", "graph_hash": "..."},
  "result": {"steps": [], "stopped_at": "call-1", "stop_reason": "call", "resume_node_id": null, "error": null, "notes": []},
  "error": null
}
~~~

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

    `publish`, `pause`, `resume` and `archive` change what the live campaign does straight away. Each asks for confirmation unless you pass `--force` or `--json`.
