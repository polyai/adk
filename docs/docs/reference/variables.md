---
title: Variables
description: Understand how state variables are discovered, stored, and referenced in the PolyAI ADK.
---

# Variables

<p class="lead">
Variables are virtual resources that represent state values used in the agent's code.
</p>

Unlike most resources, variables do not have files on disk. They are discovered automatically by scanning function code for `conv.state.<name>` usage.

## How variables work

When you assign a value to `conv.state.customer_name` in code, `customer_name` becomes a tracked variable.

For example:

~~~python
conv.state.customer_name = "Alice"
~~~

The ADK discovers variables by scanning:

- global functions
- flow functions
- function steps

This means variables are not manually declared in a separate configuration file. They emerge from the code that uses them.

## Why variables matter

Variables allow you to carry state across turns and reuse values in prompts, topics, and templates.

<div class="grid cards" markdown>

-   **Persist state**

    ---

    Store values that should survive across turns.

-   **Drive prompts**

    ---

    Reference saved values in prompts and instructions.

-   **Populate templates**

    ---

    Reuse state in SMS templates and other generated text.

-   **Support logic**

    ---

    Let functions and flows branch based on previously stored values.

</div>

## Setting state in code

Set variables by writing to `conv.state`:

~~~python
conv.state.customer_name = "Alice"
conv.state.account_balance = 150.00
conv.state.is_verified = True
~~~

## Reading state in code

Read variables from `conv.state`:

~~~python
name = conv.state.customer_name  # returns None if not set
if conv.state.is_verified:
    ...
~~~

If a variable has not been set, reading it returns `None`.

## Using variables in prompts and templates

Variables can be referenced in prompts, topic actions, SMS templates, and related text fields using either of these forms:

- `{{vrbl:variable_name}}`
- `$variable_name`

Both forms are supported, but `{{vrbl:variable_name}}` is preferred because it is validated by the ADK.

### Example in prompt text

~~~text
The customer's name is $customer_name and their balance is $account_balance.
~~~

### Example in a template

~~~yaml
text: "Hi {{vrbl:customer_name}}, your booking is confirmed for {{vrbl:booking_date}}."
~~~

## Important rules

### In prompts

Use:

- `$variable`
- `{{vrbl:variable}}`

Do not use:

- `conv.state.variable`

### For structured values

Do not use:

- `$var.attribute`

If you need to expose a structured value in prompts, convert it to a string in Python first and store that string in state.

!!! warning "Prompt syntax is not Python syntax"

    In prompts and templates, use `$variable` or `{{vrbl:variable}}`, not `conv.state.variable`.

## Best practices

- variables are discovered automatically, so no manual registration is needed
- use descriptive snake_case names
- initialize variables early, such as in `start_function` or near the beginning of a flow
- keep variable names consistent across functions and prompts
- prefer `{{vrbl:...}}` in user-facing text fields for better validation

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn where variables are typically created, updated, and read.
    [Open functions](./functions.md)

-   **SMS templates**

    ---

    See how state variables are used in reusable text messages.
    [Open SMS templates](./sms.md)

</div>