---
title: Outbound campaigns
description: Define the draft settings and node graph of each outbound campaign, with its node functions in Python.
---

# Outbound campaigns

<p class="lead">
An outbound campaign contacts people for you: it imports contacts, then calls and texts them following a graph of nodes. The ADK syncs each campaign's draft — its settings and node graph — and the code of its node functions.
</p>

!!! note "Drafts only"

    Your files hold the campaign's draft. What is live changes only when you publish with `poly campaign publish`. Archived campaigns are not pulled.

## Location

~~~text
outbound_campaigns/
└── {campaign_name}/
    ├── campaign.yaml        # name, description, settings, nodes
    └── functions/
        └── {node_id}.py     # a node function's code, only when it has code
~~~

The folder name is the campaign's name, lowercased, with punctuation replaced by `_`. To rename a campaign, change `name` and rename the folder to match: the campaign keeps its identity, contacts and history.

## What a campaign contains

`campaign.yaml` has the same shape as the `campaign` block of a campaign exported from Agent Studio, so its keys are camelCase. The one difference is that a node function's code lives in `functions/{node_id}.py` instead of the YAML.

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | The campaign's name, under 256 characters. |
| `description` | No | Text under 1024 characters, or empty for none. |
| `settings` | No | The campaign's settings (below). Left-out fields take their defaults. |
| `nodes` | Yes | The node graph (below). |

### Settings

| Field | Description |
|---|---|
| `startDate`, `endDate` | ISO dates the campaign runs between. |
| `fromNumber`, `smsFromNumber` | Numbers calls and texts come from. |
| `defaultVariant` | Name of the variant the campaign's calls use. |
| `country` | ISO 3166-1 alpha-2 code, e.g. `US`. Required to publish. |
| `useCase` | `transactional` or `marketing`. Required to publish. |
| `dailyContactLimit` | Most times a contact is reached per day. Defaults to `3`. |
| `voiceDispatchLimits`, `smsDispatchLimits` | `maxConcurrent`, `perHour` and `perDay` caps. |
| `defaultTimezone` | IANA time zone, used for a contact with none. |
| `contactWindow` | `daysOfWeek` (`monday` to `sunday`), and `startTime` and `endTime` as `"HH:mm"` in the contact's time zone. |

### Nodes

Each node has an `id` (unique in the campaign; it also names the node's function file), a `position` (`x`, `y` on the Agent Studio canvas), an optional `label`, and `data` holding its `type` and fields:

| Type | Fields |
|---|---|
| `trigger` | `function`, `routes`, `sourceType` (`csv`, `api` or `webhook`; default `csv`), `ingestInterval` (`hourly`, `daily` or `manual`; default `daily`) |
| `call` | `flowName`, `amdFlowName` (optional), `function`, `greeting`, `voicemailEnabled`, `voicemailScript` and `voicemailWhen` (`detection` or `final_retry`), `maxAttempts` (1 to 5), `backoff`, `backoffUnit` (`minutes`, `hours` or `days`), `routes`, `defaultRoute` |
| `sms` | `function`, `messageTemplate`, `replyFlowName`, `replyTimeoutValue` and `replyTimeoutUnit` (all optional), `routes`, `defaultRoute` |
| `conditional` | `function`, `branches` (each an `id`, `variable` and `targetNodeId`), `defaultTargetNodeId` |
| `wait` | `amount`, `unit`, `targetNodeId` |
| `writeback` | `target` (`api` or `csv`), `function`, `targetNodeId` |
| `end` | `exitReason`, `writebackEnabled`, `function` (optional) |

A route is a `targetNodeId` and an optional `outcome`; `defaultRoute` is where outcomes that match no route go. Flow fields hold a [flow](./flows.md)'s name.

Every node except `wait` has a `function` with a `name` (a valid Python name) and a `description`. Its code goes in `functions/{node_id}.py`, whose `def` line must be the one the node expects; Agent Studio shows it in the node's editor.

### Example

~~~yaml
name: Appointment reminders
description: Reminds patients of their appointment.
settings:
  fromNumber: '+15550100'
  country: US
  useCase: transactional
  contactWindow:
    daysOfWeek: [monday, tuesday, wednesday, thursday, friday]
    startTime: '09:00'
    endTime: '17:00'
nodes:
- id: trigger-1
  position: {x: 0.0, y: 0.0}
  data:
    type: trigger
    function: {name: map_contacts, description: Maps CSV rows to contacts.}
    routes:
    - targetNodeId: call-1
- id: call-1
  position: {x: 0.0, y: 200.0}
  label: Reminder call
  data:
    type: call
    flowName: Reminder
    function: {name: call_args, description: Passes the appointment to the call.}
    greeting: Hi, this is a reminder about your appointment.
    voicemailEnabled: false
    maxAttempts: 2
    backoff: 1
    backoffUnit: hours
    defaultRoute: end-1
- id: end-1
  position: {x: 0.0, y: 400.0}
  data: {type: end, exitReason: completed, writebackEnabled: false}
~~~

`functions/trigger-1.py`:

~~~python
def map_contacts(contacts: list[dict], outbound_campaign: OutboundCampaign):
    return {"contacts": [...]}
~~~

## How changes are pushed

[`poly push`](../cli/push.md) sends only what changed, node by node: a moved node sends its new position, an edited node (or its function file) its data, and added or removed nodes are created or deleted. Settings are always sent whole. A new folder creates a draft campaign; removing a folder deletes the campaign, which the platform allows only for a draft that was never published or archived.

## Validation

`poly validate` and `poly push` check:

- `name` is present and under 256 characters; `description` under 1024.
- Settings have the right types and allowed values (`useCase`, `country`, positive limits, valid `daysOfWeek`).
- Node ids are unique, every node has a `position` and a known `type`, and each type has its required fields with allowed values.
- `voicemailScript` and `voicemailWhen` are set when `voicemailEnabled` is true.
- Function names are valid Python names, and `code` is not in the YAML.
- Every file in `functions/` belongs to a node that has a function.
- The folder name matches the campaign's name.

The graph itself — one trigger, routes to nodes that exist, every node reachable, each function's `def` line — is checked by `poly campaign validate` once you have pushed.

## Best practices

- Run `poly campaign validate` and `poly campaign preview` after every push, before you publish.
- Keep node ids stable; they tie a node to its function file and its history.
- Make a campaign on a branch, merge it, then publish it from `main`.

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    Call and SMS nodes enter a flow by its name.
    [Open flows](./flows.md)

</div>
