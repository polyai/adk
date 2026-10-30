---
title: Outbound campaigns
description: Define the draft settings and nodes of each outbound campaign, with its node functions in Python.
---

# Outbound campaigns

<p class="lead">
An outbound campaign contacts people for you: it imports contacts, then calls and texts them, moving each contact from node to node. The ADK syncs each campaign's draft (its settings and nodes) and the code of its node functions.
</p>

!!! note "Drafts only"

    Your files hold the campaign's draft. What is live changes only when the campaign is published. Archived campaigns are not pulled.

## Location

~~~text
outbound_campaigns/
└── {campaign_name}/
    ├── campaign.yaml          # name, description, settings, nodes
    └── functions/
        └── {node_name}.py     # a node function's code, only when it has code
~~~

Optional. The folder name is the campaign's name, lowercased, with punctuation replaced by `_`. Agent Studio allows two campaigns with the same name, so a second one gets the end of its id added to its folder, as in `reminders-a1b2c3d4`.

To rename a campaign, change `name` and rename the folder to match. The campaign keeps its identity, contacts and history.

## What a campaign contains

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | The campaign's name, under 256 characters. |
| `description` | No | Text under 1024 characters, or empty for none. |
| `settings` | No | The campaign's settings (below). Fields left out take their defaults. |
| `nodes` | Yes | The campaign's nodes (below), in any order you like. |

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

Each node has a `name`, unique in the campaign, and a `type` with that type's fields. Nodes refer to each other by name. A node's function code lives in `functions/{node_name}.py`, with the name lowercased and punctuation replaced by `_`.

| Type | Fields |
|---|---|
| `trigger` | `function`, `routes` (each a `next` and an optional `outcome`), `sourceType` (`csv`, `api` or `webhook`; default `csv`), `ingestInterval` (`hourly`, `daily` or `manual`; default `daily`) |
| `call` | `flowName`, `amdFlowName` (optional), `function`, `greeting`, `voicemailEnabled`, `voicemailScript` and `voicemailWhen` (`detection` or `final_retry`), `maxAttempts` (1 to 5), `backoff`, `backoffUnit` (`minutes`, `hours` or `days`), `defaultRoute` |
| `sms` | `function`, `messageTemplate`, `replyFlowName`, `replyTimeoutValue` and `replyTimeoutUnit` (all optional), `defaultRoute` |
| `conditional` | `function`, `branches` (each an `id`, `variable` and `next`), `defaultNext` |
| `wait` | `amount`, `unit`, `next` |
| `writeback` | `target` (`api` or `csv`), `function`, `next` |
| `end` | `exitReason`, `writebackEnabled`, `function` (optional) |

`next`, `defaultNext` and `defaultRoute` name the node a contact moves to next. A call or text always moves to its `defaultRoute`; put a `conditional` after it to branch on how it went. Flow fields hold a [flow](./flows.md)'s name.

Every node except `wait` has a `function` with a `name` (a valid Python name) and a `description`. Its code goes in the node's `.py` file, whose `def` line takes exactly the parameters the node is called with:

| Node | Parameters |
|---|---|
| `trigger` with `sourceType: csv` | `contacts`, `outbound_campaign` |
| `trigger` with `sourceType: api` | `outbound_campaign`, `sync` |
| `writeback` with `target: csv` | `outbound_contacts`, `outbound_campaign` |
| Any other `call`, `sms`, `conditional`, `writeback` or `end` | `outbound_contact`, `outbound_campaign` |

A webhook trigger runs no function.

Node positions on the Agent Studio canvas are not in the file. A node keeps its position, and a new node is placed next to the node that routes to it.

!!! warning "Renaming a node"

    A node's name is its identity in your files. Renaming one deletes the node and creates a new one, which starts its history again. Rename its `.py` file to match.

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
- name: Import contacts
  type: trigger
  function: {name: map_contacts, description: Maps CSV rows to contacts.}
  routes:
  - next: Reminder call
- name: Reminder call
  type: call
  flowName: Reminder
  function: {name: call_args, description: Passes the appointment to the call.}
  greeting: Hi, this is a reminder about your appointment.
  voicemailEnabled: false
  maxAttempts: 2
  backoff: 1
  backoffUnit: hours
  defaultRoute: Done
- name: Done
  type: end
  exitReason: completed
  writebackEnabled: false
~~~

`functions/import_contacts.py`:

~~~python
def map_contacts(contacts: list[dict], outbound_campaign: OutboundCampaign):
    return {"contacts": [...]}
~~~

## Validation

`poly validate` and `poly push` check:

- `name` is present and under 256 characters, and `description` under 1024.
- The folder name matches the campaign's name.
- Settings have the right types and allowed values:
    - `useCase` is `transactional` or `marketing`, and limits are positive whole numbers.
    - `country` is a real ISO 3166-1 alpha-2 code.
    - `defaultTimezone` is a valid IANA time zone.
    - `endDate` is not before `startDate`.
    - `contactWindow` has at least one day, its times are `HH:mm`, and it ends after it starts.
- `nodes` is a list, every node has a name, and names are unique in the campaign, ignoring case and punctuation.
- There is at most one `trigger` node.
- Each node has a known `type`, its required fields, allowed values, and no fields its type doesn't have.
- `voicemailScript` and `voicemailWhen` are set when `voicemailEnabled` is true.
- Every route names a node in the campaign.
- Function names are valid Python names, and `code` is not in the YAML.
- Each function's `def` line is whole on one line and takes exactly the node's parameters.
- Every file in `functions/` belongs to a node with a function.

## Best practices

- Name nodes after what they do, like `Reminder call`, so routes read clearly.
- Keep node names stable: renaming a node gives it a new identity and history.
- Make a campaign on a branch, merge it, then publish it from `main`.

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    Call and SMS nodes enter a flow by its name.
    [Open flows](./flows.md)

</div>
