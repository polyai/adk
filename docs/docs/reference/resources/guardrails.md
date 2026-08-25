---
title: Guardrails
description: Configure platform and custom guardrails that constrain agent behavior during a conversation.
---

# Guardrails

<p class="lead">
Guardrails are runtime checks that constrain what the agent can say or do, catching problems a prompt or rule alone can't reliably prevent.
</p>

There are two kinds: a fixed catalog of **platform guardrails** you can only toggle on or off, and **custom guardrails** you define yourself with a trigger condition and an action.

## Location

Both kinds of guardrail live in a single optional file:

~~~text
agent_settings/
└── guardrails.yaml       # Optional
~~~

## What guardrails control

<div class="grid cards" markdown>

-   **Platform guardrails**

    ---

    A fixed set of platform-provided checks. Only the `enabled` toggle can be changed.

-   **Custom guardrails**

    ---

    Your own rules: a prompt describing when the guardrail should trigger, and an action describing what happens when it does.

</div>

## Platform guardrails

!!! note "Fixed catalog — enable or disable only"
    The catalog of platform guardrails is fixed by the platform. You can enable or disable each one, but you cannot create a new platform guardrail or delete an existing one via the ADK.

### The catalog

| Name | Description |
|---|---|
| `ai_identity` | Has the agent disclose that it's an AI when asked. |
| `emergency_escalation` | Detects emergencies and escalates instead of continuing the conversation normally. |
| `hallucination_control` | Reduces factually unsupported or made-up responses. |
| `jailbreak_defence` | Detects and blocks attempts to override the agent's instructions or persona. |
| `tool_call_integrity` | Checks that the agent's function/tool calls are well-formed and intended. |

### Fields

| Field | Description |
|---|---|
| `name` | One of the fixed catalog names above. |
| `enabled` | `true` or `false`. Default: `true`. |

### Example

~~~yaml
platform_guardrails:
  - name: jailbreak_defence
    enabled: true
  - name: hallucination_control
    enabled: false
~~~

## Custom guardrails

Custom guardrails live under an optional `custom_guardrails` list in the same file. Unlike platform guardrails, they can be created, updated, and deleted via the ADK.

### Fields

| Field | Description |
|---|---|
| `name` | Display name for the guardrail. |
| `prompt` | Describes the condition that triggers the guardrail. Free text — references are not evaluated here. |
| `action` | Describes what the agent should do when the guardrail triggers, for example `warn`, or an instruction that calls a function, handoff, or SMS template. |
| `enabled` | `true` or `false`. Default: `true`. |

### Supported references in `action`

`action` is the only field scanned for references — a reference written in `prompt` is treated as plain text.

It accepts every prefix in the [resource references table](../../development/resource-architecture.md#resource-references) except two: flow transition functions (`{{ft:...}}`) and entities (`{{entity:...}}`) fail validation in a guardrail action.

### Example

~~~yaml
custom_guardrails:
  - name: No medical advice
    enabled: true
    action: warn
    prompt: Never give medical advice. Offer to transfer the caller to a human instead.
~~~

## Validation

Validation rejects a `guardrails.yaml` that doesn't satisfy these rules:

- Every platform guardrail's `name` must be one of the fixed catalog names; anything else is rejected with the list of valid names.
- Every platform and custom guardrail's `enabled` must be a boolean (`true`/`false`, unquoted).
- A custom guardrail's `name`, `prompt`, and `action` are all required.
- Any `{{prefix:name}}` reference in a custom guardrail's `action` must use one of the supported prefixes above, and must resolve to a resource that actually exists.

## Best practices

- Keep `prompt` focused on the trigger condition and `action` focused on the response; don't fold both into one field.
- Disable a platform or custom guardrail with `enabled: false` instead of deleting it, so it's easy to re-enable later.

## Related pages

<div class="grid cards" markdown>

-   **Safety filters**

    ---

    Content filtering on user input and agent output, configured per channel.
    [Open safety filters](./safety_filters.md)

-   **Agent settings**

    ---

    Personality, role, and rules — the other resources that shape agent behavior.
    [Open agent settings](./agent_settings.md)

-   **Functions**

    ---

    Global functions that a custom guardrail's action can call.
    [Open functions](./functions.md)

</div>
