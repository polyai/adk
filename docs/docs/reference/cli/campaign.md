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

Outbound campaigns must be turned on for the project; otherwise every subcommand exits `1` and says so.

Two campaigns can share a name. Each then has its own folder, such as `reminders-abcd1234`; name the campaign by its folder.

`--field` and `--state` values are read as JSON when they parse as JSON, so `age=30`, `booked=true` and `note=null` give a number, a boolean and `null`. Any other value, such as `plan=gold`, is kept as a string. `--contact`, `--run`, `--last-send` and `--sample-outputs` take a JSON file or JSON written inline.

| Argument | Description |
|---|---|
| `name` | The campaign's name, or its folder name. |

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
  "result": {
    "valid": true,
    "errors": [],
    "warnings": [{"node_id": "call-1", "field": "flowName", "message": "...", "is_warning": true}]
  }
}
~~~

The `result` is the platform's own, so it refers to nodes by id; the human output shows their names, in its messages too.

## `poly campaign preview`

Walk a made-up contact through the campaign to the next call, condition or end. Nothing is called, texted or stored, and node functions are not run: say what each returns with `--sample-outputs`.

Examples:

~~~bash
poly campaign preview 'Appointment reminders' --phone +15550100 --field first_name=Ada
poly campaign preview 'Appointment reminders' --contact contact.json --sample-outputs outputs.json
poly campaign preview 'Appointment reminders' --phone +15550100 --start-node 'Reminder call' --result no_answer
~~~

A preview keeps nothing between steps. Each step prints the flags to carry on with, including `--last-send` when the step left a call or a text: pass it back, so that the next step's conditions and templates read it as `journey.last_send`.

| Flag | Description |
|---|---|
| `--contact` | JSON file with the contact's data, as an import would carry it. |
| `--phone` | The contact's phone number. |
| `--first-name` | The contact's first name. |
| `--field` | Another contact column, as `KEY=VALUE`. Repeatable. |
| `--sample-outputs` | JSON file of what each node's function returns, keyed by node name. |
| `--start-node` | Name of the node to carry on from. Defaults to the trigger. |
| `--result` | How the call or text at `--start-node` went, e.g. `no_answer` or `replied`. |
| `--state` | A value that call or text reported back, as `KEY=VALUE`. Repeatable. |
| `--last-send` | The `last_send` the previous step printed, as JSON or a JSON file. Only with `--start-node`. |
| `--ask-branches` | Stop at a condition with no sample output instead of taking its default branch. |

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "result": {"steps": [], "stopped_at": "call-1", "stop_reason": "call", "error": null, "notes": [], "last_send": null}
}
~~~

## `poly campaign test`

Run one step of a test of the live campaign, and wait for it to finish. It calls and texts the test contact for real. The first step starts at the trigger. To carry on, pass the `--start-node` and the run it printed. After a call or a text, also say how it went with `--result`; after a wait, carry on from the node it printed.

The run is printed as soon as the step starts, so it is not lost if waiting fails or you stop it; the step carries on regardless. A poll that fails with no response, a stalled connection or a server error is retried three times. Node names are matched as they are on `main`, which the test runs, even from another branch. A step that stops at a failed node exits `1`. If the platform is slow to answer the start, the step may still have started: check the campaign's tests in Agent Studio before you run `test` again.

Examples:

~~~bash
poly campaign test 'Appointment reminders' --phone +15550100
poly campaign test 'Appointment reminders' --phone +15550100 --start-node 'Reminder call' --run run.json --result no_answer
~~~

| Flag | Description |
|---|---|
| `--contact` | JSON file with the test contact: `phone`, `firstName`, `lastName`, `externalId`, `metadata`. |
| `--phone` | Number to call and text. |
| `--first-name`, `--last-name` | The contact's name. |
| `--external-id` | The contact's id in your own system. |
| `--field` | A metadata column, as `KEY=VALUE`. Repeatable. |
| `--start-node` | Name of the node to carry on from. |
| `--run` | The run the previous step printed, as JSON or a JSON file. |
| `--result` | How the call or text at `--start-node` went. |
| `--state` | A value that call or text reported back, as `KEY=VALUE`. Repeatable. |
| `--timeout` | Seconds to wait for the step. Defaults to `600`. |
| `--force` | Run without confirmation. Implied by `--json`. |

The inputs are checked before you are asked to confirm, including that `main` has the campaign. The lifecycle commands make the same check.

!!! warning "This contacts a real phone"

    `poly campaign test` runs the live campaign and calls or texts the number you give it.

`--json` output shape:

~~~json
{
  "success": true,
  "campaign": "Appointment reminders",
  "test_step": {
    "step_id": "TSTEP-...",
    "status": "done",
    "run": {"contact_id": "...", "enrolment_id": "...", "graph_hash": "..."},
    "result": {"steps": [], "stopped_at": "call-1", "stop_reason": "call", "resume_node_id": null, "error": null, "notes": []},
    "error": null
  }
}
~~~

With `--json`, as soon as the step starts, one line goes to stderr with the step and its run, so a caller that is stopped before the step finishes still has them:

~~~json
{"step_id": "TSTEP-...", "run": {"contact_id": "...", "enrolment_id": "...", "graph_hash": "..."}}
~~~

The result goes to stdout once the step stops. `success` is `false` when the step failed, or finished by stopping at a failed node (`result.stop_reason` is `error`). If waiting for the step fails or times out, the error carries the step and its run:

~~~json
{
  "success": false,
  "error": "Test step TSTEP-... of campaign 'Appointment reminders' is still running after 600 seconds.",
  "campaign": "Appointment reminders",
  "step_id": "TSTEP-...",
  "run": {"contact_id": "...", "enrolment_id": "...", "graph_hash": "..."}
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

    `publish`, `pause`, `resume` and `archive` change what the live campaign does straight away. Each asks for confirmation unless you pass `--force` or `--json`. If the platform does not answer in time, or you stop the command while it is sending, the change may still have gone through: check the campaign's status in Agent Studio, or with `poly pull` on main, before sending it again.
