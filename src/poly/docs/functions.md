# Functions

## Overview

Functions are Python files that add deterministic logic to your agent. They can be called by the LLM during conversation, used as flow steps, or run automatically at call start/end.

## Location
```
functions/                          # Global functions
├── start_function.py               # Optional — runs once at call start
├── end_function.py                 # Optional — runs once at call end
└── {function_name}.py              # Called by LLM via {{fn:function_name}}
flows/{flow_name}/
├── functions/
│   └── {function_name}.py          # Flow transition functions, called via {{ft:function_name}}
└── function_steps/
    └── {function_step}.py          # Deterministic flow steps (no LLM)
```

## Function types

| Type | Location | Signature | Referenced as |
|------|----------|-----------|---------------|
| **Global** | `functions/` | `def name(conv: Conversation, ...)` | `{{fn:name}}` |
| **Transition** | `flows/{flow}/functions/` | `def name(conv: Conversation, flow: Flow, ...)` | `{{ft:name}}` (same flow only) |
| **Function step** | `flows/{flow}/function_steps/` | `def name(conv: Conversation, flow: Flow)` | Stepped into by conditions |
| **Start** | `functions/start_function.py` | `def start_function(conv: Conversation)` | Runs automatically |
| **End** | `functions/end_function.py` | `def end_function(conv: Conversation)` | Runs automatically |

## File structure rules

- Every `.py` file must define a function with the **same name as the file** (without `.py`).
  This function is the entry point for the file when called by the LLM.
- Only the main function requires `@func_` decorators to define how it's run and shown to the LLM
- Use `from _gen import *  # <AUTO GENERATED>` in your function to match the imports used when function is run by the agent.
  This line is not pushed to Agent Studio, and must match this exact pattern.

## Decorators

- **`@func_description('...')`** (required for global and transition functions): Description shown to the LLM to decide when to call the function.
- **`@func_parameter('param_name', '...')`** (required for each parameter except `conv` and `flow`): Description of the parameter shown to the LLM.
- **`@func_latency_control(...)`** (optional): Configure delay messages while the function runs.

Function steps do not support `@func_parameter` or `@func_description`.

### Parameter types

Parameters support these Python types, mapped to schema types:

| Python type | Schema type |
|-------------|-------------|
| `str` | `string` |
| `int` | `integer` |
| `float` | `number` |
| `bool` | `boolean` |

### Example
```python
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
```

## Naming

Prefer naming after the **event that should trigger the call** (e.g. `first_name_provided`, `booking_confirmed`), not the action (`store_first_name`, `send_confirmation`). This helps the LLM understand when to call it.

## Returns and control flow

| Return type | Effect |
|------------|--------|
| `return "string"` | String is injected as system context to the LLM |
| `conv.say("exact phrase")` | Speak/send exact text (first sentence should be static for cached audio) |
| `conv.goto_flow("name")` | Navigate to a flow |
| `flow.goto_step("Step Name", "reason")` | Navigate to a step (flow functions only) |
| `conv.exit_flow()` | Exit the current flow |
| `conv.call_handoff(destination="...", reason="...")` | Transfer the call |
| `return {"hangup": True}` | End the call |
| `return {"transition": {"goto_flow": "...", "goto_step": "..."}}` | Navigate via dict |
| `return {"utterance": "...", "end_turn": False}` | Speak and immediately continue (no user reply) |

### Calling other functions
- Global: `conv.functions.my_global_function(...)`
- Flow: `flow.functions.my_flow_function(...)`

## Special functions

### Start function (`start_function.py`)
- Runs **once at call start**, before the first user input.
- Signature: `def start_function(conv: Conversation):` — no `flow`, no `@func_parameter`.
- Typical use: initialize state, read SIP headers, set language, write initial metrics, then `conv.goto_flow("...")`.

### End function (`end_function.py`)
- Runs **once at call end**, after the conversation completes.
- Signature: `def end_function(conv: Conversation):`
- Typical use: aggregate `conv.metric_events`, write summary metrics (e.g. `CALL_OUTCOME`), optionally trigger post-call webhooks when `conv.env == "live"`.

## Utility modules
If a function file isn't intended to be called by the LLM, it still needs a main function matching the filename. Decorate it and have it return a "utility module" message. Do not decorate helper functions.

## State
`conv.state` is preserved between turns. Use it to set variables for future logic or to be used in prompts
- **Set**: `conv.state.variable_name = value`
- **Read**: `conv.state.variable_name` (returns `None` if not set)
- **In prompts**: `$variable` or `{{vrbl:variable}}` (not `conv.state.variable`). No `$var.attribute` — stringify in Python first.

### Counters
Use `conv.state.counter` (initialize and increment) to avoid infinite retries. After a limit (e.g. 3), hand off or exit.

## Metrics

- **Write**: `conv.write_metric("EVENT_NAME")`, `conv.write_metric("NAME", value)`, `conv.write_metric("NAME", write_once=True)`
- **Naming**: `SCREAMING_SNAKE_CASE`; group with prefixes (e.g. `SMS_OFFERED`, `SMS_ACCEPTED`, `SMS_SENT`)
- Use metrics for events you wish to filter calls with or use for analysis such as flow entry, decisions, and key moments.
- Use `write_once=True` when a metric should be recorded once (e.g. flow entered); avoid writing the same metric repeatedly in a loop.
- Log important outcomes (`conv.log.info` / `conv.log.error`) around external calls and failures; don't fail silently.

## Quick reference

| Task | Code |
|------|------|
| State in prompt | `$variable` or `{{vrbl:variable}}`|
| State in code | `conv.state.variable` |
| Persist data | `conv.state.variable = value` |
| Track event | `conv.write_metric("NAME", value)` |
| Call global function | `conv.functions.my_function(...)` |
| Call flow function | `flow.functions.my_function(...)` |
| Navigate to flow | `conv.goto_flow("Flow Name")` |
| Navigate to step | `flow.goto_step("Step Name", "reason")` |
| Exit flow | `conv.exit_flow()` |
| Transfer call | `conv.call_handoff(destination="...", reason="...")` |
