# Agent Settings

## Overview
Define the agent's identity and behavioral rules, in `agent_settings/`: personality, role, and rules.

## File structure
```
agent_settings/
├── personality.yaml
├── role.yaml
├── rules.txt
└── experimental_config.json   # see references/experimental_config.md
```

## Personality (`personality.yaml`)
Controls conversational tone.
| Field | Notes |
|---|---|
| `adjectives` | Map of trait → boolean. Allowed: `Polite`, `Calm`, `Kind`, `Funny`, `Energetic`, `Thoughtful`, `Other`. If `Other: true`, no other adjective can be selected. |
| `custom` | Free-text description; supports `{{attr:...}}` and `{{vrbl:...}}` |

```yaml
adjectives:
  Polite: true
  Calm: true
  Kind: true
custom: ""
```

## Role (`role.yaml`)
Defines what the agent is (job title / purpose).
| Field | Notes |
|---|---|
| `value` | Role name, e.g. `Customer Service Representative`. If `other`, `custom` is used. |
| `additional_info` | Extra context about the role |
| `custom` | Free-text role, only valid when `value: other`; supports `{{attr:...}}` and `{{vrbl:...}}` |

```yaml
value: Customer Service Representative
additional_info: Handles customer inquiries and bookings
custom: ""
```

## Rules (`rules.txt`)
Plain-text behavioral instructions followed every turn — a key file for shaping behavior.

**Supported references**: `{{fn:function_name}}`, `{{twilio_sms:template_name}}`, `{{ho:handoff_name}}`,
`{{attr:attribute_name}}`, `{{vrbl:variable_name}}`.

```text
Be helpful and professional at all times.
Use {{fn:validate_email}} when the user provides an email address.
For complex issues, use {{ho:escalation_handoff}} to transfer to a specialist.
Send confirmation via {{twilio_sms:confirmation_template}} after booking.
```

**Best practices**: keep rules concise/actionable; use references instead of hardcoded values; avoid encoding
branching logic here — use flows/functions instead.
