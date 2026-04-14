---
title: Functions
description: Add deterministic logic to your agent using global functions, transition functions, function steps, and lifecycle hooks.
---

# Functions

<p class="lead">
Functions are Python files that add deterministic logic to your agent.
They can be called by the model, used as flow steps, or run automatically at call start and end.
</p>

Functions are how the ADK handles behavior that should not be left to prompt interpretation alone.

## Where functions live

~~~text
functions/
├── start_function.py
├── end_function.py
└── {function_name}.py

flows/{flow_name}/
├── functions/
│   └── {function_name}.py
└── function_steps/
    └── {function_step}.py
~~~

## Function types

| Type | Location | Signature | Referenced as |
|---|---|---|---|
| Global | `functions/` | `def name(conv: Conversation, ...)` | `{{fn:name}}` |
| Transition | `flows/{flow}/functions/` | `def name(conv: Conversation, flow: Flow, ...)` | `{{ft:name}}` |
| Function step | `flows/{flow}/function_steps/` | `def name(conv: Conversation, flow: Flow)` | Entered by flow conditions |
| Start | `functions/start_function.py` | `def start_function(conv: Conversation)` | Runs automatically |
| End | `functions/end_function.py` | `def end_function(conv: Conversation)` | Runs automatically |

## What functions are for

Functions are useful when you need deterministic behavior such as:

- validating input
- routing based on state
- calling APIs
- writing metrics
- setting variables
- transferring calls
- starting or ending flows explicitly

<div class="grid cards" markdown>

-   **Global functions**

    ---

    Reusable functions that can be called by the model.

-   **Transition functions**

    ---

    Flow-local functions used for step transitions and routing.

-   **Function steps**

    ---

    Deterministic flow steps with no LLM decision-making.

-   **Lifecycle functions**

    ---

    Hooks that run automatically at the start or end of a call.

</div>

## File structure rules

Every `.py` file must define a function with the same name as the file, excluding `.py`.

That function is the entry point when the file is called by the model or runtime.

Every function file must include this import line:

~~~python
from _gen import *  # <AUTO GENERATED>
~~~

Do not modify this line. The ADK matches it exactly when reading function files.

## Decorators

Global and transition functions use decorators to describe themselves to the model.

### Supported decorators

| Decorator | Purpose |
|---|---|
| `@func_description("...")` | Describes when the function should be called |
| `@func_parameter("name", "...")` | Describes a parameter |
| `@func_latency_control(...)` | Configures delay messaging while the function runs |

Function steps do not support `@func_description` or `@func_parameter`.

!!! warning "All parameters must have a type annotation"

    Every parameter decorated with `@func_parameter` must have a Python type annotation (for example, `booking_ref: str`). Parameters without an annotation, or with an unsupported annotation such as `Optional[str]`, will raise a `ValueError` when the function is processed. Only the types listed in the table below are supported.

## Parameter types

Supported parameter types map to schema types as follows:

| Python type | Schema type |
|---|---|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |

## Example

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description("Look up a booking by reference number.")
@func_parameter("booking_ref", "The booking reference provided by the customer")
@func_parameter("include_history", "Whether to include booking history")
def lookup_booking(conv: Conversation, booking_ref: str, include_history: bool):
    result = external_api.get_booking(booking_ref, include_history)
    if not result:
        return "No booking found. Ask the customer to verify the reference number."
    conv.state.booking = str(result)
    return f"Booking found: {result['status']}. Confirm the details with the customer."
~~~

## Naming guidance

Prefer naming functions after the **event that should trigger them**, rather than the internal action they perform.

### Prefer

- `first_name_provided`
- `booking_confirmed`

### Avoid

- `store_first_name`
- `send_confirmation`

This tells the model when to call the function.

## Returns and control flow

Functions can influence the conversation in several ways.

| Return or action | Effect |
|---|---|
| `return "string"` | Injects the string as system context |
| `conv.say("exact phrase")` | Sends or speaks exact text |
| `conv.goto_flow("name")` | Navigates to a flow |
| `flow.goto_step("Step Name", "reason")` | Navigates to a step |
| `conv.exit_flow()` | Exits the current flow |
| `conv.call_handoff(...)` | Transfers the call |
| `return {"hangup": True}` | Ends the call |
| `return {"transition": {...}}` | Navigates via returned transition |
| `return {"utterance": "...", "end_turn": False}` | Speaks and immediately continues |

!!! warning "Use `end_turn=False` carefully"

    Only use `end_turn=False` when the agent must continue immediately in the same turn. Do not use it when the user is expected to answer.

## Calling other functions

You can call functions from within functions.

### Global function call

~~~python
conv.functions.my_global_function(...)
~~~

### Flow function call

~~~python
flow.functions.my_flow_function(...)
~~~

## Start function

`start_function.py` runs once at call start, before the first user input.

### Signature

~~~python
def start_function(conv: Conversation):
~~~

### Typical uses

- initialize state
- read SIP headers
- set language
- write initial metrics
- send the agent into the first flow

## End function

`end_function.py` runs once at call end, after the conversation completes.

### Signature

~~~python
def end_function(conv: Conversation):
~~~

### Typical uses

- aggregate metrics
- write final outcome metrics
- trigger post-call behavior in live environments

## Utility modules

If a function file is not intended to be called by the model, it still needs a main function matching the filename.

Decorate that main function and have it return a utility-module message. Helper functions inside the file should not be decorated.

## State

`conv.state` is preserved between turns.

### In code

Set a state value:

~~~python
conv.state.variable_name = value
~~~

Read a state value:

~~~python
conv.state.variable_name
~~~

### In prompts

Use:

- `$variable`
- `{{vrbl:variable}}`

Do not use:

- `conv.state.variable`
- `$var.attribute`

If you need complex structured data in prompts, stringify it in Python first and store the string in state.

## Counters

State counters are useful for limiting retries and preventing loops.

For example:

- initialize a counter
- increment it after each retry
- hand off or exit after a defined limit

## Metrics and logging

Functions are a natural place to write metrics and logs.

### Metrics

Examples:

~~~python
conv.write_metric("EVENT_NAME")
conv.write_metric("NAME", value)
conv.write_metric("NAME", write_once=True)
~~~

### Logging

Examples:

~~~python
conv.log.info(...)
conv.log.warning(...)
conv.log.error(...)
~~~

### Good practices

- use `SCREAMING_SNAKE_CASE` for metric names
- use grouped naming patterns where helpful
- use `write_once=True` for one-time events
- log important outcomes around external calls and failures

## Quick reference

| Task | Code |
|---|---|
| State in prompt | `$variable` or `{{vrbl:variable}}` |
| State in code | `conv.state.variable` |
| Persist data | `conv.state.variable = value` |
| Track event | `conv.write_metric("NAME", value)` |
| Call global function | `conv.functions.my_function(...)` |
| Call flow function | `flow.functions.my_function(...)` |
| Navigate to flow | `conv.goto_flow("Flow Name")` |
| Navigate to step | `flow.goto_step("Step Name", "reason")` |
| Exit flow | `conv.exit_flow()` |
| Transfer call | `conv.call_handoff(destination="...", reason="...")` |

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    See how function steps and transition functions fit into flow design.
    [Open flows](./flows.md)

-   **Variables**

    ---

    Learn how state variables are discovered and referenced.
    [Open variables](./variables.md)

</div>
