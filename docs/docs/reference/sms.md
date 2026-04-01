---
title: SMS templates
description: Define reusable SMS messages that the agent can send during a conversation.
---

# SMS templates

<p class="lead">
SMS templates define reusable text messages that the agent can send during a conversation, such as confirmations, links, or verification codes.
</p>

Templates support dynamic content through variables stored in conversation state.

## Location

SMS templates are defined in:

~~~text
config/sms_templates.yaml
~~~

Templates are listed under the `sms_templates` key.

## What an SMS template contains

Each template can include the following fields:

| Field | Description |
|---|---|
| `name` | Identifier for the template. Referenced in prompts as `{{twilio_sms:template_name}}`. |
| `text` | Message body. Supports `{{vrbl:variable_name}}` placeholders from `conv.state`. |
| `env_phone_numbers` | Optional sender phone numbers for different environments. |

## Environment-specific sender numbers

If needed, you can define different sender numbers for different environments:

| Environment | Description |
|---|---|
| `sandbox` | Sender number for sandbox use |
| `pre_release` | Sender number for pre-release use |
| `live` | Sender number for production use |

## Example

~~~yaml
sms_templates:
  - name: booking_confirmation
    text: "Hi {{vrbl:customer_name}}, your booking for {{vrbl:booking_date}} is confirmed. Reference: {{vrbl:booking_ref}}"
    env_phone_numbers:
      sandbox: "+15551234567"
      live: "+15559876543"

  - name: verification_code
    text: "Your verification code is {{vrbl:verification_code}}. It expires in 10 minutes."
~~~

## How SMS templates are used

<div class="grid cards" markdown>

-   **In rules, topics, and flows**

    ---

    Use `{{twilio_sms:template_name}}` to tell the agent which SMS should be sent.

-   **In code**

    ---

    Call a function that triggers the SMS through `conv` or the platform API.

-   **With variables**

    ---

    Use `{{vrbl:...}}` placeholders to insert values from conversation state.

</div>

## In prompts and instructions

SMS templates can be referenced in rules, topics, and related instructions using:

~~~text
{{twilio_sms:template_name}}
~~~

This lets you reference the correct template by name without embedding the full message body in prompt text.

## Using variables

Template text can include placeholders drawn from `conv.state`, for example:

~~~text
{{vrbl:customer_name}}
~~~

Before the SMS is sent, the corresponding state variables should already be set in code.

For example:

~~~python
conv.state.customer_name = "Alice"
conv.state.booking_date = "12 March"
conv.state.booking_ref = "ABC123"
~~~

## Best practices

- set required state variables before the SMS is triggered
- use separate templates for different purposes such as confirmation, verification, and follow-up
- keep templates short and clear
- configure `env_phone_numbers` when sender numbers differ between environments
- prefer template references over hard-coded SMS text in prompts

!!! tip "Treat templates as reusable resources"

    SMS templates are easier to manage when each template has one clear purpose and a stable name.

## Related pages

<div class="grid cards" markdown>

-   **Variables**

    ---

    Learn how values are stored in `conv.state` and referenced with `{{vrbl:...}}`.
    [Open variables](./variables.md)

-   **Functions**

    ---

    See how deterministic code can set variables and trigger SMS sending.
    [Open functions](./functions.md)

</div>