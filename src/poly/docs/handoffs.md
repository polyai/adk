# Handoffs

## Overview
Handoffs configure SIP call transfers for voice agents. They define how and where to transfer a call (invite, refer, or end).

## Location
`config/handoffs.yaml`. Handoffs are listed under the `handoffs` key.

## Structure

Each handoff has:
- **name** (string): Identifier for the handoff, up to 100 characters, unique within the file. Referenced in rules as `{{ho:handoff_name}}`.
- **description** (string): What this handoff does, up to 300 characters.
- **is_default** (bool): Whether this is the default handoff.
- **sip_config** (object): Transfer method configuration (see below).
- **sip_headers** (list, optional): Custom SIP headers as `key`/`value` pairs, both text (quote numbers and booleans). A `key` is up to 100 characters of letters, digits and `!#$%&'*+-.^_~`. A `value` is up to 1,000 characters of printable ASCII.

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

## Usage
- **In code**: `conv.call_handoff(destination="handoff_name", reason="transfer_reason")`
- **In rules**: Reference as `{{ho:handoff_name}}` with instructions for when to use it.
- **In topics/flows**: Instruct the LLM to call a function that performs the handoff (e.g. `{{fn:transfer_call}}`).

## Best practices
- Use clear, descriptive handoff names.
- Use E.164 format for phone numbers.
- One handoff config per purpose (don't reuse the same config for different transfer destinations).
- Keep `sip_headers` minimal and only add custom headers when the receiving system needs them.
