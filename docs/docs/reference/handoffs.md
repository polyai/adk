---
title: Handoffs
description: Configure SIP call transfers for voice agents using handoff definitions in the PolyAI ADK.
---

# Handoffs

<p class="lead">
Handoffs configure SIP call transfers for voice agents. They define how and where a call should be transferred, or whether it should be ended.
</p>

Handoffs are used when an agent needs to escalate, transfer, or terminate a voice interaction in a controlled way.

## Location

Handoffs are defined in:

~~~text
config/handoffs.yaml
~~~

They are listed under the `handoffs` key.

## What a handoff contains

Each handoff includes the following fields:

| Field | Description |
|---|---|
| `name` | Identifier for the handoff. Referenced in rules as `{{ho:handoff_name}}`. |
| `description` | Explains what the handoff does. |
| `is_default` | Whether this is the default handoff. |
| `sip_config` | Transfer method configuration. |
| `sip_headers` | Optional custom SIP headers as key/value pairs. |

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