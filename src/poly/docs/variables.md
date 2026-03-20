# Variables

## Overview

Variables are virtual resources that represent state values used in the agent's code. Unlike other resources, variables do not have files on disk — they are automatically discovered by scanning function code for `conv.state.<name>` usage.

## How variables work

When you write `conv.state.customer_name = "Alice"` in a function, `customer_name` becomes a tracked variable. The ADK discovers these by scanning all function files (global functions, flow functions, and function steps) for state attribute access patterns.

Variables can be referenced in prompts and templates using `$variable_name` or `{{vrbl:variable_name}}` — these are interchangeable. Prefer `{{vrbl:variable_name}}` as it is validated by the ADK.

## Setting state in code
```python
conv.state.customer_name = "Alice"
conv.state.account_balance = 150.00
conv.state.is_verified = True
```

## Reading state in code
```python
name = conv.state.customer_name  # returns None if not set
if conv.state.is_verified:
    ...
```

## Using variables in prompts and templates

In flow step prompts, topic actions, SMS templates, and other text fields, use either syntax — they are interchangeable:

- `{{vrbl:variable_name}}` (preferred — validated by the ADK)
- `$variable_name`

```
The customer's name is $customer_name and their balance is $account_balance.
```

```yaml
text: "Hi {{vrbl:customer_name}}, your booking is confirmed for {{vrbl:booking_date}}."
```

Do not use `conv.state.variable` syntax in prompts — use `$variable` or `{{vrbl:variable}}` only.

Do not use `$var.attribute` — stringify complex objects in Python first, then store the string in state.

## Best practices
- Variables are discovered automatically — no manual registration needed.
- Use descriptive snake_case names.
- Initialize state variables in `start_function` or early in the flow to avoid `None` values.
- Keep variable names consistent across functions and prompts.
