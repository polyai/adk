---
title: Agent settings
description: Define the agent's identity, persona, and behavioral rules in the PolyAI ADK.
---

# Agent settings

<p class="lead">
Agent settings define the agent's identity and behavioral rules.
They live in <code>agent_settings/</code> and are made up of persona and rules resources.
</p>

!!! note "The persona is platform-provisioned — update only"
    The persona resource is created automatically by the platform when a project is created. It always exists on any Agent Studio project and can be updated with `poly push`, but cannot be created from scratch via the ADK. If `persona.txt` appears in a project directory without a matching entry in `.agent_studio_config` — for example, after copying a directory from another project — the push will fail with a "Create operation not supported" error. Always start a new project with [`poly init`](../cli/init.md) and [`poly pull`](../cli/pull.md) rather than copying an existing directory.

!!! warning "Personality and role have been removed"
    The agent's identity used to be split across `personality.yaml` and `role.yaml`. Agent Studio replaced both with a single free-text persona, so the ADK no longer pulls or pushes them. A project last pulled with an older version still has the two files on disk; they are deleted the first time the project is loaded, and the ADK logs a warning telling you to run [`poly pull`](../cli/pull.md) to fetch `persona.txt`.

These settings shape how the agent presents itself and how it should behave across the conversation.

## Location

Agent settings live under:

~~~text
agent_settings/
├── languages.yaml                  # Optional
├── persona.txt
├── rules.txt
├── safety_filters.yaml             # Optional
└── experimental_config.json        # Optional
~~~

## What agent settings control

<div class="grid cards" markdown>

-   **Persona**

    ---

    Describes who the agent is, in free text.

-   **Rules**

    ---

    Provides plain-text instructions the agent should follow on every turn.

-   **Languages**

    ---

    Configures the default language and any additional languages the agent supports.

-   **Safety filters**

    ---

    Project-level content safety filtering across four categories.

-   **Experimental config**

    ---

    Optional advanced feature flags and tuning.

</div>

## Persona

The `persona.txt` file is a free-text description of who the agent is. It is the single field that defines the agent's identity, and it is what the **Role** field in Agent Studio edits.

### Supported references

| Syntax | Meaning |
|---|---|
| `{{attr:attribute_name}}` | [Variant attribute](./variants.md) |
| `{{vrbl:variable_name}}` | [State variable](./variables.md) |

These are the same two the personality and role settings accepted, so the persona can vary per [variant](./variants.md) or per call. Behavioral references such as `{{fn:}}` and `{{ho:}}` belong in `rules.txt`.

!!! warning "Attribute references are not tracked"

    `PersonaReferences` carries a variables map and nothing else, so an `{{attr:}}` reference travels in the persona text but is not recorded as a reference on the resource. The personality and role settings behaved the same way. `poly push` still validates that the attribute exists.

### Example

~~~text
You are a calm and polite concierge for {{vrbl:hotel_name}}. Keep answers short.
~~~

### Derived personas

A project that predates the persona and has never had one authored still pulls a `persona.txt`: the platform derives its content from the project's old personality and role settings, without storing it. Because `poly push` only sends resources whose contents have changed, an untouched file is never pushed back.

Editing `persona.txt` and pushing authors a real persona. From that point the content is fixed and no longer derived.

## Rules

The `rules.txt` file contains plain-text behavioral instructions that the agent should follow on every turn.

This is one of the most important files for shaping agent behavior.

### Supported references

The rules file supports the following references:

| Syntax | Meaning |
|---|---|
| `{{fn:function_name}}` | [Global function](./functions.md) |
| `{{twilio_sms:template_name}}` | [SMS template](./sms.md) |
| `{{ho:handoff_name}}` | [Handoff destination](./handoffs.md) |
| `{{attr:attribute_name}}` | [Variant attribute](./variants.md) |
| `{{vrbl:variable_name}}` or `$variable_name` | [State variable](./variables.md) |
| `{{tn:translation_key}}` | [Translation](./translations.md) |

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

## Languages

The optional `languages.yaml` file configures which languages the agent supports. When present, it defines the default language and any additional languages.

See the [Languages reference](./languages.md) for full field descriptions, validation rules, and examples.

## Safety filters

The `safety_filters.yaml` file configures project-level content safety filtering. It controls whether harmful content is filtered across all channels by default.

See the [Safety filters reference](./safety_filters.md) for field descriptions, schema, and examples.

## Best practices

- keep rules concise and actionable
- use references instead of hard-coded values
- keep the persona focused on who the agent is, and leave what it should do to the rules
- treat rules as a global behavioral layer, not a place for detailed flow logic

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn how referenced global functions are defined and used.
    [Open functions](./functions.md)

-   **Languages**

    ---

    Configure default and additional language settings for the agent.
    [Open languages](./languages.md)

-   **Translations**

    ---

    Define localized text strings per language.
    [Open translations](./translations.md)

-   **Safety filters**

    ---

    Configure content safety filtering at the project and channel level.
    [Open safety filters](./safety_filters.md)

-   **Experimental config**

    ---

    Configure optional advanced features and runtime overrides.
    [Open experimental config](./experimental_config.md)

</div>
