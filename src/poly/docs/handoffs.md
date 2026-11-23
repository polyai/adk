# Handoffs

## Overview
Handoffs configure SIP call transfers for voice agents. `config/handoffs.yaml` holds three things:

- **Destinations** (`handoffs`): how and where to transfer a call (invite, refer, or end).
- **Reasons** (`reasons`): why the agent hands off, and what happens for each reason on calls and on chat.
- **The default transfer message** (`transfer_message`): what the agent says before a call transfer when the reason has no wording of its own.

## Location
`config/handoffs.yaml`, under the `handoffs`, `reasons` and `transfer_message` keys.

## Structure

Each handoff has:
- **name** (string): Identifier for the handoff, up to 100 characters, unique within the file. Referenced in rules as `{{ho:handoff_name}}`.
- **description** (string): What this handoff does, up to 300 characters.
- **is_default** (bool): Whether this is the default handoff.
- **sip_config** (object): Transfer method configuration (see below).
- **sip_headers** (list, optional): Custom SIP headers as `key`/`value` pairs, both text. A `key` is at most 100 letters, digits or `!#$%&'*+-.^_~`; a `value` is at most 1,000 printable ASCII characters.
- **transfer_test_calls** (bool, optional): Whether test calls (from Agent Studio and the ADK) really transfer to this destination. Defaults to `true`; set `false` to stop test calls transferring here. A pull only writes it when it is `false`.

## SIP config types

| Method | Use | Fields |
|--------|-----|--------|
| **invite** | Outbound new call | `phone_number` (E.164, up to 100 characters), `outbound_endpoint` (up to 100 characters), `outbound_encryption` (`TLS/SRTP` or `UDP/RTP`) |
| **refer** | Transfer existing call | `phone_number` (E.164, up to 100 characters) |
| **bye** | End call | No extra fields |

## Example
```yaml
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
```

## Reasons

A reason tells the agent when to hand off and what to do on each channel. When a project has reasons, the agent hands off by reason, and the reason's outcome for the conversation's channel decides what happens. A project without reasons keeps handing off to destinations as before.

Each reason has:
- **name** (string): Up to 100 characters, unique within the file.
- **key** (string, optional): The analytics key recorded when the agent hands off for this reason. Capital letters, digits and underscores, starting with a letter, up to 64 characters, unique. Leave it out on a new reason and the platform derives one. It is fixed once the reason exists: changing it has no effect (the next pull restores it). Renaming a reason replaces it with a new one; keep its `key` line and the new reason takes the same key.
- **description** (string): When the agent should use this reason, up to 500 characters.
- **call** (required): What happens on a call. One of:
  - `{transfer_to: <destination name>, wording: <text>}`: transfer to a destination in `handoffs`. `wording` is optional and is said before the transfer; without it, the agent says the default transfer message.
  - `{message: <text>}`: no transfer. The message is guidance the agent puts in its own words, not a script read out verbatim.
  - `not_offered`: the reason isn't offered on calls.
- **chat** (optional): What happens on chat: `{message: <text>}` or `not_offered`. Chat can't transfer.

Wording and messages are up to 300 characters and may reference a state variable as `{{vrbl:variable_name}}`. `poly validate` checks each variable exists; no other reference type is allowed.

A reason is always available to the agent. There is no setting for this yet.

The file is the whole list: a push deletes reasons that aren't in `reasons`, and a file without `reasons` has none.

If a destination is deleted while a reason still transfers to it, a pull keeps the destination id the platform has and `poly validate` reports it until you pick another destination.

## Default transfer message

```yaml
transfer_message:
  call: Let me put you through to someone who can help.
```

- `call` is said before a call transfer when the reason has no `wording`, and may reference `{{vrbl:variable_name}}`. `call: ""` transfers without a line.
- Without a `transfer_message` section (or with an empty one) there is no default transfer message, and a push removes it.
- Chat has no default transfer message; a `chat` key is refused.

## Example with reasons
```yaml
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
      wording: I'll put you through to our billing team.
    chat:
      message: Explain that billing disputes are handled by phone and give the billing number.
  - name: Opening hours
    description: The caller asks when the office is open.
    call:
      message: Tell them we're open 9 to 5, Monday to Friday.
    chat: not_offered
transfer_message:
  call: Let me put you through to someone who can help.
```

## Usage
- **In code**: `conv.call_handoff(destination="handoff_name", reason="transfer_reason")`
- **In rules**: Reference as `{{ho:handoff_name}}` with instructions for when to use it.
- **In topics/flows**: Instruct the LLM to call a function that performs the handoff (e.g. `{{fn:transfer_call}}`).

## Best practices
- Use clear, descriptive handoff names.
- Use E.164 format for phone numbers.
- One handoff config per purpose (don't reuse the same config for different transfer destinations).
- Write a reason's `description` as the situation the agent should recognise, not as an instruction to transfer.
- Keep reason names stable once analytics depend on their keys; renaming is fine, the key stays.
- Keep `sip_headers` minimal and only add custom headers when the receiving system needs them.
