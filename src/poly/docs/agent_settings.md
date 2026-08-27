# Agent Settings

## Overview

Agent settings define the agent's identity and behavioral rules. They live in `agent_settings/` and consist of the persona and rules, plus the superseded personality and role settings.

## File structure
```
agent_settings/
├── persona.txt                # The agent's identity
├── personality.yaml           # Superseded by persona.txt
├── role.yaml                  # Superseded by persona.txt
├── rules.txt
└── experimental_config.json   # See experimental_config docs
```

## Persona (`persona.txt`)

Free-text description of who the agent is, and the single field that defines the agent's identity. This is what the **Role** field in Agent Studio edits — it replaces `personality.yaml` and `role.yaml`, which are no longer surfaced to builders.

### Supported references
- `{{vrbl:variable_name}}` — variables. No other reference type is allowed.

### Example
```text
You are a calm and polite concierge for {{vrbl:hotel_name}}. Keep answers short.
```

### Notes
- For projects that predate the persona and have never authored one, the pulled content is **derived** from `personality.yaml` and `role.yaml`. Nothing is stored server-side until someone edits it, and `poly push` sends nothing while the file is untouched.
- Editing `persona.txt` and pushing authors a real persona. From that point the content is fixed and no longer tracks `personality.yaml` / `role.yaml`.

## Personality (`personality.yaml`)

**Superseded by `persona.txt`.** Kept for projects that predate the persona; it still pulls and pushes, but no longer affects the agent's identity. `poly push` warns when you change it on a project that has a persona.

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

**Superseded by `persona.txt`.** Kept for projects that predate the persona; it still pulls and pushes, but no longer affects the agent's identity. `poly push` warns when you change it on a project that has a persona.

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
- `{{fn:function_name}}` - global functions
- `{{twilio_sms:template_name}}` - SMS templates
- `{{ho:handoff_name}}` - handoffs
- `{{attr:attribute_name}}` - variant attributes
- `{{vrbl:variable_name}}` - variables

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
