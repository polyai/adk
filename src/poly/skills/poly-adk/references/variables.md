# Variables

## Overview
Virtual resources representing state values used in agent code. Unlike other resources, variables have no files
on disk — they're discovered automatically by scanning function code for `conv.state.<name>` usage.

## How they work
Writing `conv.state.customer_name = "Alice"` in any function makes `customer_name` a tracked variable. The ADK
scans all function files (global functions, flow functions, function steps) for state attribute access.

Reference in prompts/templates as `$variable_name` or `{{vrbl:variable_name}}` — interchangeable; prefer
`{{vrbl:...}}` since it's validated by the ADK.

## Setting state in code
```python
conv.state.customer_name = "Alice"
conv.state.account_balance = 150.00
conv.state.is_verified = True
```

## Reading state in code
```python
name = conv.state.customer_name  # None if unset
if conv.state.is_verified:
    ...
```

## Using variables in prompts and templates
```
The customer's name is $customer_name and their balance is $account_balance.
```
```yaml
text: "Hi {{vrbl:customer_name}}, your booking is confirmed for {{vrbl:booking_date}}."
```
Never use `conv.state.variable` syntax in prompts. Never use `$var.attribute` — stringify complex objects in
Python first, then store the string in state.

## Best practices
Auto-discovered, no manual registration; descriptive snake_case names; initialize in `start_function` or early in
the flow to avoid `None` values; keep names consistent across functions and prompts.
