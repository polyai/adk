# Outbound Campaigns

## Purpose

An outbound campaign contacts people for you: it imports contacts, then calls and texts them, moving each contact from node to node, and records how each contact ended. The ADK syncs each campaign's **draft**: its settings and nodes. What is live changes only when the campaign is published. Archived campaigns are not pulled.

## Location

```
outbound_campaigns/
  {campaign_name}/
    campaign.yaml        # name, description, settings, nodes
    functions/
      {node_name}.py     # code of that node's function, only when it has code
```

The folder name is the campaign's name, lowercased with punctuation replaced by `_`. A second campaign with the same name gets the end of its id added, as in `reminders-a1b2c3d4`. Renaming a campaign means changing `name` and renaming the folder to match; the campaign keeps its identity.

## campaign.yaml

- **name**: Required, under 256 characters.
- **description**: Optional text, or empty for none.
- **settings**: The whole settings object. Fields left out take their default (`dailyContactLimit: 3`, everything else empty).
  - **startDate**, **endDate**: ISO dates; the end can't be before the start.
  - **fromNumber**, **smsFromNumber**: Numbers calls and texts come from.
  - **defaultVariant**: Name of the variant the campaign's calls use.
  - **country**: ISO 3166-1 alpha-2 code (e.g. `US`). Required to publish.
  - **useCase**: `transactional` or `marketing`. Required to publish.
  - **dailyContactLimit**: Most times a contact is reached per day.
  - **voiceDispatchLimits**, **smsDispatchLimits**: `maxConcurrent`, `perHour`, `perDay`.
  - **defaultTimezone**: IANA time zone, used when a contact has none.
  - **contactWindow**: `daysOfWeek` (at least one of `monday` .. `sunday`), `startTime` and `endTime` as `"HH:mm"` in the contact's time zone, ending after it starts.
- **nodes**: List of nodes, in any order. Each has a **name**, unique in the campaign, a **type**, and that type's fields (below). Nodes refer to each other by name. Positions on the Agent Studio canvas are not in the file: a node keeps its position, and a new node is placed next to the node that routes to it.

A node's name is its identity. Renaming a node deletes it and creates a new one with a new history; rename its `.py` file to match.

### Node types

| type | Fields |
|---|---|
| `trigger` | `function`, `routes` (each `next` and an optional `outcome`), `sourceType` (`csv`, `api`, `webhook`; default `csv`), `ingestInterval` (`hourly`, `daily`, `manual`; default `daily`) |
| `call` | `flowName`, `amdFlowName` (optional), `function`, `greeting`, `voicemailEnabled`, `voicemailScript` and `voicemailWhen` (`detection`, `final_retry`; both required when voicemail is on), `maxAttempts` (1-5), `backoff`, `backoffUnit` (`minutes`, `hours`, `days`), `defaultRoute` |
| `sms` | `function`, `messageTemplate`, `replyFlowName`, `replyTimeoutValue`, `replyTimeoutUnit` (all three optional), `defaultRoute` |
| `conditional` | `function`, `branches` (each `id`, `variable`, `next`), `defaultNext` |
| `wait` | `amount`, `unit`, `next` |
| `writeback` | `target` (`api`, `csv`), `function`, `next` |
| `end` | `exitReason`, `writebackEnabled`, `function` (optional) |

`next`, `defaultNext` and `defaultRoute` name the node a contact moves to. A call or text always moves to its `defaultRoute`; put a `conditional` after it to branch on how it went. Flow fields hold a flow's name. At most one node is a `trigger`.

### Functions

Every node except `wait` has a **function** with a `name` (a Python name) and a `description`; on an `end` node it is optional, and a webhook trigger runs none. Its code goes in `functions/{node_name}.py` (the name lowercased, punctuation replaced by `_`). The `def` line must be whole on one line and take exactly these parameters:

- `trigger` with `sourceType: csv`: `contacts`, `outbound_campaign`
- `trigger` with `sourceType: api`: `outbound_campaign`, `sync`
- `writeback` with `target: csv`: `outbound_contacts`, `outbound_campaign`
- any other node: `outbound_contact`, `outbound_campaign`

## Example

```yaml
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
```

`functions/import_contacts.py`:

```python
def map_contacts(contacts: list[dict], outbound_campaign: OutboundCampaign):
    return {"contacts": [...]}
```

## Running a campaign

Use `poly campaign` (`validate`, `preview`, `test`, `publish`, `pause`, `resume`, `archive`); see `poly campaign --help`. Run `poly campaign validate` after you push to check the whole graph, such as every node being reachable. `publish`, `pause`, `resume` and `archive` act on the live campaign on `main`.
