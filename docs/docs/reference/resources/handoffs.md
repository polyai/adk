---
title: Handoffs
description: Configure SIP call transfers, handoff reasons and the default transfer message for voice agents in the PolyAI ADK.
---

# Handoffs

<p class="lead">
Handoffs configure SIP call transfers for voice agents. They define how and where a call should be transferred, or whether it should be ended.
</p>

!!! note "Enterprise feature"

    Handoffs require an enterprise Agent Studio account.

Handoffs are used when an agent needs to escalate, transfer, or terminate a voice interaction in a controlled way.

## Location

Handoffs are defined in:

~~~text
config/handoffs.yaml
~~~

The file has three top-level keys:

| Key | Contains |
|---|---|
| `handoffs` | Destinations: where and how a call is transferred. |
| `reasons` | Why the agent hands off, and what happens for each reason on calls and on chat. Optional. |
| `transfer_message` | What the agent says before a call transfer when the reason has no wording of its own. Optional. |

## What a handoff contains

Each handoff (destination) includes the following fields:

| Field | Description |
|---|---|
| `name` | Identifier for the handoff, up to 100 characters. Referenced in rules as `{{ho:handoff_name}}`. |
| `description` | Explains what the handoff does, up to 300 characters. |
| `is_default` | Whether this is the default handoff. |
| `sip_config` | Transfer method configuration. |
| `sip_headers` | Optional custom SIP headers as key/value pairs. |
| `transfer_test_calls` | Optional. Whether test calls transfer to this destination. Defaults to `true`; set `false` to stop test calls transferring here. A pull only writes it when it is `false`. |

## SIP config types

A handoff uses one of three SIP methods:

| Method | Use | Fields |
|---|---|---|
| `invite` | Start an outbound new call | `phone_number`, `outbound_endpoint`, `outbound_encryption` |
| `refer` | Transfer an existing call | `phone_number` |
| `bye` | End the call | No extra fields |

### Notes

- `phone_number` should use **E.164 format**
- `outbound_encryption` can be `TLS/SRTP` or `UDP/RTP`

## What a reason contains

A reason tells the agent when to hand off, and what to do on each channel. When a project has reasons, the agent hands off by reason, and the reason's outcome for the conversation's channel decides what happens. A project without reasons keeps handing off to destinations as before.

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Up to 100 characters, unique within the file. |
| `key` | No | The analytics key recorded when the agent hands off for this reason. Capital letters, digits and underscores, starting with a letter, up to 64 characters. Leave it out on a new reason and the platform derives one. |
| `description` | Yes | When the agent should use this reason, up to 500 characters. |
| `call` | Yes | What happens on a call: a transfer, a message, or `not_offered`. |
| `chat` | No | What happens on chat: a message or `not_offered`. Chat can't transfer. |

Each outcome takes one of these shapes:

| Outcome | Shape | Meaning |
|---|---|---|
| Transfer | `{transfer_to: <destination name>, wording: <text>}` | Transfer to a destination in `handoffs`. `wording` is optional and is said before the transfer; without it, the agent says the default transfer message. Calls only. |
| Message | `{message: <text>}` | No transfer. The message is guidance the agent puts in its own words, not a script read out verbatim. |
| Not offered | `not_offered` | The reason isn't offered on this channel. |

Wording and messages may reference a state variable as `{{vrbl:variable_name}}`, as prompts do. `poly validate` checks that each variable exists.

!!! info "The key is fixed once a reason exists"

    Changing the key of an existing reason has no effect, and the next pull restores it. Renaming a reason replaces it with a new reason of the new name; keep its `key` line and the new reason takes the same key, so analytics carry on.

As with other resources, the file is the whole list: a push deletes reasons that aren't in `reasons`, and a file without `reasons` has none.

## Default transfer message

`transfer_message` takes a single `call` field:

- `call: <text>`: said before a call transfer when the reason has no `wording`. It may reference `{{vrbl:variable_name}}`.
- `call: ""`: transfer without a line.

Without a `transfer_message` section (or with an empty one) the project has no default transfer message, and a push removes it. Chat has no default transfer message, so a `chat` key is refused.

## Validation

- `name` is required and at most 100 characters. `description` is at most 300 characters.
- `sip_config.method` must be one of `invite`, `refer`, or `bye`.
- For `invite`, `outbound_encryption` must be `TLS/SRTP` or `UDP/RTP`.
- `phone_number` (for `invite` and `refer`) and `outbound_endpoint` (for `invite`) are at most 100 characters each.
- Each `sip_headers` entry needs a text `key` and `value`.
- A SIP header `key` is at most 100 letters, digits or `!#$%&'*+-.^_~`.
- A SIP header `value` is at most 1,000 printable ASCII characters.
- Across all handoffs in `config/handoffs.yaml`, exactly one must have `is_default: true` — zero or more than one default handoff fails validation.
- Each handoff `name` must be unique.
- `transfer_test_calls`, when present, is `true` or `false`.
- A reason needs a `name` (at most 100 characters), a `description` (at most 500 characters) and a `call` outcome.
- A reason `key` is capital letters, digits and underscores, starts with a letter, and is at most 64 characters.
- Reason names and keys are unique.
- An outcome is `not_offered`, `{transfer_to, wording?}` or `{message}`; any other shape or key is refused.
- `transfer_to` must name a destination in `handoffs`, including one added in the same push. To delete a destination that a reason transfers to, point the reason at another destination in the same push. A destination deleted in Agent Studio moves its reasons to the default destination, and the next pull shows that. If no destination is left, the reason keeps the deleted destination's id, and `poly validate` reports it until you add one.
- A `chat` outcome can't be a transfer.
- Messages are not empty. Messages and wording are at most 300 characters.
- Wording, messages and `transfer_message.call` only take `{{vrbl:}}` references, to variables the project has.
- `transfer_message` only takes `call`, at most 300 characters.

## Example

~~~yaml
handoffs:
  - name: escalation_handoff
    description: Transfer to a live agent for complex issues
    is_default: false
    sip_config:
      method: refer
      phone_number: "+15551234567"
    sip_headers:
      - key: X-Reason
        value: escalation

  - name: end_call
    description: End the call gracefully
    is_default: false
    sip_config:
      method: bye
~~~

With reasons and a default transfer message:

~~~yaml
handoffs:
  - name: Front desk
    description: Reception
    is_default: true
    sip_config:
      method: refer
      phone_number: "+15551234567"
  - name: Billing
    description: Billing team
    is_default: false
    sip_config:
      method: refer
      phone_number: "+15551234568"
    transfer_test_calls: false

reasons:
  - name: Billing dispute
    key: BILLING_DISPUTE
    description: The caller disputes a charge on their bill.
    call:
      transfer_to: Billing
      wording: I'll put you through to our billing team, {{vrbl:caller_name}}.
    chat:
      message: Explain that billing disputes are handled by phone and give the billing number.
  - name: Opening hours
    description: The caller asks when the office is open.
    call:
      message: Tell them we're open 9 to 5, Monday to Friday.
    chat: not_offered

transfer_message:
  call: Let me put you through to someone who can help.
~~~

## How handoffs are used

<div class="grid cards" markdown>

-   **In code**

    ---

    Call a handoff directly with `conv.call_handoff(...)`.

-   **In rules**

    ---

    Refer to a handoff using `{{ho:handoff_name}}`.

-   **In topics and flows**

    ---

    Instruct the model to call a function that performs the handoff.

</div>

## In code

You can trigger a handoff directly in code:

~~~python
conv.call_handoff(destination="handoff_name", reason="transfer_reason")
~~~

## In rules

A handoff can be referenced in `rules.txt` using:

~~~text
{{ho:handoff_name}}
~~~

This is useful when rules need to explain when escalation or transfer should happen.

## In topics and flows

Topics and flows should generally not perform raw transfer logic directly in prompt text. Instead, they should guide the model toward calling a function that performs the handoff.

For example:

~~~text
Use {{fn:transfer_call}} when the user needs to be transferred to a specialist.
~~~

## Best practices

- use clear, descriptive handoff names
- use E.164 format for phone numbers
- create one handoff definition per transfer purpose
- keep `sip_headers` minimal
- only add custom SIP headers when the receiving system actually requires them
- write a reason's `description` as the situation the agent should recognise, not as an instruction to transfer

!!! tip "One purpose per handoff"

    Avoid reusing a single handoff for multiple destinations or business cases. Clear handoff names make rules and code easier to understand.

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    See how handoffs are typically triggered from deterministic logic.
    [Open functions](./functions.md)

-   **Agent settings**

    ---

    Learn how handoffs are referenced in rules.
    [Open agent settings](./agent_settings.md)

-   **Conversation object reference (platform)**

    ---

    Full reference for `conv.call_handoff` — destination, reason, utterance, and SIP header overrides.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }

</div>