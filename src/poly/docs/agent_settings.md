# Agent Settings

## Overview

Agent settings define the agent's identity and behavioral rules. They live in `agent_settings/` and consist of two resources: the persona and the rules.

## File structure
```
agent_settings/
├── persona.txt                # The agent's identity
├── rules.txt
└── experimental_config.json   # See experimental_config docs
```

## Persona (`persona.txt`)

Free-text description of who the agent is, and the single field that defines the agent's identity. This is what the **Role** field in Agent Studio edits.

### Supported references
- `{{vrbl:variable_name}}` — variables. No other reference type is allowed.

### Example
```text
You are a calm and polite concierge for {{vrbl:hotel_name}}. Keep answers short.
```

### Notes
- The persona replaced the older personality and role settings, which are no longer surfaced in Agent Studio and are no longer pulled or pushed. Any `personality.yaml` / `role.yaml` left in a project from an earlier version is deleted the next time the project is loaded.
- For projects that predate the persona and have never authored one, the pulled content is **derived** server-side from the old personality and role. Nothing is stored until someone edits it, and `poly push` sends nothing while the file is untouched.
- Editing `persona.txt` and pushing authors a real persona. From that point the content is fixed and no longer derived.

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
