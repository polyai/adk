# Agent Settings

## Overview

Agent settings define the agent's identity and behavioral rules. They live in `agent_settings/` and consist of three resources: personality, role, and rules.

## File structure
```
agent_settings/
├── personality.yaml
├── role.yaml
├── rules.txt
└── experimental_config.json   # See experimental_config docs
```

## Personality (`personality.yaml`)

Controls the agent's conversational tone.

### Fields
- **adjectives**: Map of personality traits to booleans. Allowed values: `Polite`, `Calm`, `Kind`, `Funny`, `Energetic`, `Thoughtful`, `Other`. If `Other` is `true`, no other adjective can be selected.
- **custom**: Free-text personality description. Supports `{{attr:...}}` and `{{vrbl:...}}` references.

### Example
```yaml
adjectives:
  Polite: true
  Calm: true
  Kind: true
custom: ""
```

## Role (`role.yaml`)

Defines what the agent is (its job title / purpose).

### Fields
- **value**: Role name (e.g. `Customer Service Representative`). If set to `other`, the `custom` field is used.
- **additional_info**: Extra context about the role.
- **custom**: Free-text role description, only valid when `value` is `other`. Supports `{{attr:...}}` and `{{vrbl:...}}` references.

### Example
```yaml
value: Customer Service Representative
additional_info: Handles customer inquiries and bookings
custom: ""
```

## Rules (`rules.txt`)

Plain-text behavioral instructions the agent follows on every turn. This is a key file for shaping agent behavior.

### Supported references
- `{{fn:function_name}}` — global functions
- `{{twilio_sms:template_name}}` — SMS templates
- `{{ho:handoff_name}}` — handoffs
- `{{attr:attribute_name}}` — variant attributes
- `{{vrbl:variable_name}}` — variables

### Example
```text
Be helpful and professional at all times.
Use {{fn:validate_email}} when the user provides an email address.
For complex issues, use {{ho:escalation_handoff}} to transfer to a specialist.
Send confirmation via {{twilio_sms:confirmation_template}} after booking.
```

### Best practices
- Keep rules concise and actionable.
- Use references (`{{fn:...}}`, `{{attr:...}}`) instead of hard-coding values.
- Avoid encoding branching logic here; use flows/functions for conditional behavior.
