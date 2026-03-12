---
title: Agent settings
description: Define the agent’s identity, role, and behavioral rules in the PolyAI ADK.
---

# Agent settings

<p class="lead">
Agent settings define the agent’s identity and behavioral rules.
They live in <code>agent_settings/</code> and are made up of personality, role, and rules resources.
</p>

These settings shape how the agent presents itself and how it should behave across the conversation.

## Location

Agent settings live under:

~~~text
agent_settings/
├── personality.yaml
├── role.yaml
├── rules.txt
└── experimental_config.json
~~~

## What agent settings control

<div class="grid cards" markdown>

-   **Personality**

    ---

    Controls the agent’s tone and conversational style.

-   **Role**

    ---

    Defines what the agent is and what kind of job it performs.

-   **Rules**

    ---

    Provides plain-text instructions the agent should follow on every turn.

-   **Experimental config**

    ---

    Optional advanced feature flags and tuning.

</div>

## Personality

The `personality.yaml` file controls the agent’s conversational tone.

### Fields

| Field | Description |
|---|---|
| `adjectives` | Map of personality traits to booleans |
| `custom` | Free-text personality description |

### Adjectives

Allowed adjective values are:

- `Polite`
- `Calm`
- `Kind`
- `Funny`
- `Energetic`
- `Thoughtful`
- `Other`

If `Other` is set to `true`, no other adjective can be selected.

### `custom`

The `custom` field is a free-text description of the personality.

It supports:

- `{{attr:...}}`
- `{{vrbl:...}}`

### Example

~~~yaml
adjectives:
Polite: true
Calm: true
Kind: true
custom: ""
~~~

## Role

The `role.yaml` file defines what the agent is.

This is usually the agent’s role, title, or function in the business context.

### Fields

| Field | Description |
|---|---|
| `value` | Role name, such as `Customer Service Representative` |
| `additional_info` | Extra context about the role |
| `custom` | Free-text role description used when `value` is `other` |

If `value` is set to `other`, the `custom` field is used instead.

The `custom` field supports:

- `{{attr:...}}`
- `{{vrbl:...}}`

### Example

~~~yaml
value: Customer Service Representative
additional_info: Handles customer inquiries and bookings
custom: ""
~~~

## Rules

The `rules.txt` file contains plain-text behavioral instructions that the agent should follow on every turn.

This is one of the most important files for shaping agent behavior.

### Supported references

The rules file supports the following references:

| Syntax | Meaning |
|---|---|
| `{{fn:function_name}}` | Global function |
| `{{twilio_sms:template_name}}` | SMS template |
| `{{ho:handoff_name}}` | Handoff destination |
| `{{attr:attribute_name}}` | Variant attribute |
| `{{vrbl:variable_name}}` | State variable |

### Example

~~~text
Be helpful and professional at all times.
Use {{fn:validate_email}} when the user provides an email address.
For complex issues, use {{ho:escalation_handoff}} to transfer to a specialist.
Send confirmation via {{twilio_sms:confirmation_template}} after booking.
~~~

## Writing effective rules

Rules are most useful when they are:

- concise
- explicit
- actionable
- stable across turns

Good rules tell the agent what standard it should follow, not how to perform step-by-step branching logic.

!!! tip "Use rules for behavioral guidance"

    Rules are a good place for durable operating principles such as escalation behavior, safety guidance, or how the agent should handle common classes of requests.

## What not to put in rules

Avoid putting deterministic branching logic into `rules.txt`.

### Avoid

- long conditional logic chains
- step-by-step routing logic
- hard-coded values that should come from references

For example, do not write logic such as:

~~~text
If $x == 0 do A, else do B.
~~~

That kind of logic belongs in flows and Python functions.

### Prefer

- references such as `{{fn:...}}`, `{{attr:...}}`, and `{{vrbl:...}}`
- concise instructions that apply broadly
- deterministic logic handled in code or flow transitions

## Best practices

- keep rules concise and actionable
- use references instead of hard-coded values
- use `custom` personality and role text only when you need more than the structured fields provide
- treat rules as a global behavioral layer, not a place for detailed flow logic

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn how referenced global functions are defined and used.
    [Open functions](./functions.md)

-   **Experimental config**

    ---

    Configure optional advanced features and runtime overrides.
    [Open experimental config](./experimental_config.md)

</div>