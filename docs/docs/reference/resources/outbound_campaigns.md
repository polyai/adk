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

Optional. The folder name is the campaign's name, lowercased, with punctuation replaced by `_`. Agent Studio allows two campaigns the same name, but each needs its own folder. When two names are the same ignoring case and punctuation, the oldest campaign keeps its name and a pull renames the other `{name} (1)`, numbered on, with a warning. That campaign shows as changed, so a pull followed by a push sends the new name to Agent Studio.

To rename a campaign, change `name` and rename the folder to match. The campaign keeps its identity, contacts and history when its nodes keep their names and types, though the trigger may be renamed too. Otherwise the push deletes the old campaign and creates a new one, with a new id.

When a campaign is renamed in Agent Studio, a pull moves its folder and carries your edits. If a folder already has the new name here, the pull leaves the campaign where it is and reports it as a conflict: move or delete that folder, then pull again. If the folder belongs to a campaign deleted in Agent Studio and is unedited here, this pull removes it and the next pull moves the renamed campaign. Files you added to that folder keep the rename waiting until you move or delete them. Files you added to the renamed campaign's own folder move with it, unless one has the name of a file Agent Studio added to the campaign: then the rename waits until you rename yours.

A campaign that has been published can't be deleted. Pause it, then archive it, with `poly campaign pause` and `poly campaign archive`. It stops being pulled once it's archived.

## What a campaign contains

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | Yes | The campaign's name, under 256 characters. |
| `description` | No | Text under 1024 characters, or empty for none. |
| `settings` | No | The campaign's settings (below). Fields left out take their defaults, and a pull leaves out settings that aren't set. |
| `nodes` | No | The campaign's nodes (below), in any order you like. |

### Settings

| Field | Description |
|---|---|
| `start_date`, `end_date` | ISO dates the campaign runs between. |
| `from_number`, `sms_from_number` | Numbers calls and texts come from. |
| `default_variant` | Name of the variant the campaign's calls use. |
| `country` | ISO 3166-1 alpha-2 code in capitals, e.g. `US`. Required to publish. |
| `use_case` | `transactional` or `marketing`. Required to publish. |
| `daily_contact_limit` | Most times a contact is reached per day. Defaults to `3`. |
| `voice_dispatch_limits`, `sms_dispatch_limits` | `max_concurrent`, `per_hour` and `per_day` caps. |
| `default_timezone` | IANA time zone, used for a contact with none. |
| `contact_window` | `days_of_week` (`monday` to `sunday`), and `start_time` and `end_time` as `"HH:mm"` in the contact's time zone. |

Settings the ADK doesn't know yet are kept as they were pulled, but the ADK can't send them. A settings change replaces every setting, so change the settings of a campaign that has any in Agent Studio, or update the ADK.

### Nodes

Each node has a `name`, unique in the campaign, and a `type` with that type's fields. Nodes refer to each other by name. A node's function code lives in `functions/{node_name}.py`, with the name lowercased and punctuation replaced by `_`. Names are compared ignoring case and punctuation, so when Agent Studio has nodes named `Call` and `call`, a pull numbers the second one, as in `call 2`. A node Agent Studio has with no name, or with a name another node has, is named on pull and shows as changed until your next push sends that name.

| Type | Fields |
|---|---|
| `trigger` | `function`, `routes` (each a `next` and an optional `outcome`), `source_type` (`csv`, `api` or `webhook`; default `csv`), `ingest_interval` (`hourly`, `daily` or `manual`; default `daily`) |
| `call` | `flow_name`, `amd_flow_name` (optional), `function`, `greeting`, `voicemail_enabled`, `voicemail_script` and `voicemail_when` (`detection` or `final_retry`), `max_attempts` (1 to 5), `backoff`, `backoff_unit` (`minutes`, `hours` or `days`), `default_route` |
| `sms` | `function`, `message_template`, `reply_flow_name`, `reply_timeout_value` and `reply_timeout_unit` (all optional), `default_route` |
| `conditional` | `function`, `branches` (each a `variable` and `next`), `default_next` |
| `wait` | `amount`, `unit`, `next` |
| `writeback` | `target` (`api` or `csv`), `function`, `next` |
| `end` | `exit_reason`, `writeback_enabled`, `function` (optional) |

`next`, `default_next` and `default_route` name the node a contact moves to next. Branches have no id in the file: a branch keeps its id in Agent Studio while its `variable` stays the same, and a new branch gets a new one. A call or text always moves to its `default_route`; put a `conditional` after it to branch on how it went. Flow fields hold a [flow](./flows.md)'s name.

Every node except `wait` and `end` has a `function`, and an `end` node may have one. A function has a `name` (a valid Python name) and a `description`. Its code goes in the node's `.py` file, whose `def` line takes exactly the parameters the node is called with:

| Node | Parameters |
|---|---|
| `trigger` with `source_type: csv` | `contacts`, `outbound_campaign` |
| `trigger` with `source_type: api` | `outbound_campaign`, `sync` |
| `writeback` with `target: csv` | `outbound_contacts`, `outbound_campaign` |
| Any other `call`, `sms`, `conditional`, `writeback` or `end` | `outbound_contact`, `outbound_campaign` |

A webhook trigger runs no function.

Node positions on the Agent Studio canvas are not in the file. A node keeps its position, and a new node is placed next to the node that routes to it.

!!! warning "Renaming a node"

    A node's name is its identity in your files. A campaign has one trigger, so renaming or replacing the trigger keeps its id and history. Renaming any other node, or changing its `type`, deletes the node and creates a new one with a new id, which starts its history again. Rename its `.py` file to match.

### Example

~~~yaml
name: Appointment reminders
description: Reminds patients of their appointment.
settings:
  from_number: '+15550100'
  country: US
  use_case: transactional
  contact_window:
    days_of_week: [monday, tuesday, wednesday, thursday, friday]
    start_time: '09:00'
    end_time: '17:00'
nodes:
- name: Import contacts
  type: trigger
  function: {name: map_contacts, description: Maps CSV rows to contacts.}
  routes:
  - next: Reminder call
- name: Reminder call
  type: call
  flow_name: Reminder
  function: {name: call_args, description: Passes the appointment to the call.}
  greeting: Hi, this is a reminder about your appointment.
  voicemail_enabled: false
  max_attempts: 2
  backoff: 1
  backoff_unit: hours
  default_route: Done
- name: Done
  type: end
  exit_reason: completed
  writeback_enabled: false
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
- A campaign deleted in the push has never been published.
- Settings have the right types and allowed values:
    - `use_case` is `transactional` or `marketing`, and limits are positive whole numbers.
    - `country` is a real ISO 3166-1 alpha-2 code, in capitals.
    - `default_timezone` is a valid IANA time zone.
    - `end_date` is not before `start_date`.
    - `contact_window` has at least one day, its times are `HH:mm`, and it ends after it starts.
    - A campaign with settings the ADK doesn't know has no settings changed, and a new campaign has none.
- `nodes` is a list, every node has a name, and names are unique in the campaign, ignoring case and punctuation.
- There is at most one `trigger` node, and a campaign that has a trigger in Agent Studio keeps one: rename or replace its trigger rather than delete it.
- The trigger changes `type` only when another node becomes the trigger in the same push, and a published campaign's trigger keeps its `source_type`.
- Each node has a known `type`, its required fields, allowed values, and no fields its type doesn't have.
- A `conditional` node uses each branch `variable` once.
- `voicemail_script` and `voicemail_when` are set when `voicemail_enabled` is true.
- On a node that is new, changed type or had its routes changed, every route names a node in the campaign. Agent Studio keeps a route to a deleted node until you change it.
- Function names are valid Python names, and `code` is not in the YAML.
- On a node that is new, changed type, or had its code, function name or parameters changed, the function's `def` line is whole on one line and takes exactly the node's parameters.
- Every file in `functions/` belongs to a node with a function, and a node's file is named after it. After renaming a node, rename its file too.

## Best practices

- Name nodes after what they do, like `Reminder call`, so routes read clearly.
- Keep node names stable: renaming a node other than the trigger gives it a new identity and history.
- Make a campaign on a branch, merge it, then publish it from `main`.

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    Call and SMS nodes enter a flow by its name.
    [Open flows](./flows.md)

</div>
