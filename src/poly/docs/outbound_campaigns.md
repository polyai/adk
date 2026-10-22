# Outbound Campaigns

## Purpose

An outbound campaign contacts people for you: it imports contacts, then calls and texts them following a graph of nodes, and records how each contact ended. The ADK syncs each campaign's **draft**: its settings and node graph. What is live changes only when you publish.

## Location

```
outbound_campaigns/
  {campaign_name}/
    campaign.yaml        # name, description, settings, nodes
    functions/
      {node_id}.py       # code of that node's function, only when it has code
```

The folder name is the campaign's name, lowercased with punctuation replaced by `_`. Renaming a campaign means changing `name` and renaming the folder to match; the campaign keeps its identity. Archived campaigns are not pulled.

## campaign.yaml

`campaign.yaml` has the same shape as the `campaign` block of a campaign exported from Agent Studio, so keys are camelCase. The one difference: a node function's `code` lives in `functions/{node_id}.py`, not in the YAML.

- **name**: Required, under 256 characters.
- **description**: Optional text, or empty for none.
- **settings**: The whole settings object. Fields left out take their default (`dailyContactLimit: 3`, everything else empty).
  - **startDate**, **endDate**: ISO dates.
  - **fromNumber**, **smsFromNumber**: Numbers calls and texts come from.
  - **defaultVariantId**: Variant the campaign's calls use.
  - **country**: ISO 3166-1 alpha-2 code (e.g. `US`). Required to publish.
  - **useCase**: `transactional` or `marketing`. Required to publish.
  - **dailyContactLimit**: Most times a contact is reached per day.
  - **voiceDispatchLimits**, **smsDispatchLimits**: `maxConcurrent`, `perHour`, `perDay`.
  - **defaultTimezone**: IANA time zone, used when a contact has none.
  - **contactWindow**: `daysOfWeek` (`monday` .. `sunday`), `startTime` and `endTime` as `"HH:mm"` in the contact's time zone.
- **nodes**: List of nodes. Each has:
  - **id**: Unique within the campaign; it names the node's function file. Routes refer to nodes by id.
  - **position**: `x`, `y` on the Agent Studio canvas.
  - **label**: Optional display name.
  - **data**: The node's `type` and its fields (below).

### Node types

Every node except `wait` has a **function** with a `name` (a Python name) and a `description`; on an `end` node it is optional. Its code goes in `functions/{node_id}.py`, and the file's `def` line must be the one the node expects (Agent Studio shows it).

| type | Fields |
|---|---|
| `trigger` | `function`, `routes`, `sourceType` (`csv`, `api`, `webhook`; default `csv`), `ingestInterval` (`hourly`, `daily`, `manual`; default `daily`) |
| `call` | `flowName`, `amdFlowName` (optional), `function`, `greeting`, `voicemailEnabled`, `voicemailScript` and `voicemailWhen` (`detection`, `final_retry`; both required when voicemail is on), `maxAttempts` (1-5), `backoff`, `backoffUnit` (`minutes`, `hours`, `days`), `routes`, `defaultRoute` |
| `sms` | `function`, `messageTemplate`, `replyFlowName`, `replyTimeoutValue`, `replyTimeoutUnit` (all three optional), `routes`, `defaultRoute` |
| `conditional` | `function`, `branches` (each `id`, `variable`, `targetNodeId`), `defaultTargetNodeId` |
| `wait` | `amount`, `unit`, `targetNodeId` |
| `writeback` | `target` (`api`, `csv`), `function`, `targetNodeId` |
| `end` | `exitReason`, `writebackEnabled`, `function` (optional) |

A route is `targetNodeId` plus an optional `outcome`; `defaultRoute` is the node for outcomes no route matches. Flow fields hold a flow's name.

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
```

`functions/trigger-1.py`:

```python
def map_contacts(contacts: list[dict], outbound_campaign: OutboundCampaign):
    return {"contacts": [...]}
```

## Pushing

`poly push` sends only what changed, node by node: a moved node sends its position, an edited node (or its function file) its data, and nodes added or removed are created or deleted. Settings are always sent whole. A new campaign folder creates a draft campaign. Removing a campaign's folder deletes it, which the platform allows only for a draft that was never published.

`poly validate` checks each field. The graph itself (one trigger, routes to nodes that exist, every node reachable) is checked by `poly campaign validate` after you push.

## Running a campaign

Use `poly campaign` (`validate`, `preview`, `test`, `publish`, `pause`, `resume`, `archive`); see `poly campaign --help`. `publish`, `pause`, `resume` and `archive` act on the live campaign on `main`.
