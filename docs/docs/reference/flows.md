---
title: Flows
description: Define multi-step processes that guide the agent through structured tasks in the PolyAI ADK.
---

# Flows

<p class="lead">
Flows choreograph multi-step processes. At any given moment, the model only sees the current step's prompt and tools.
</p>

A good flow keeps each step focused on a single task. Use Python for branching, validation, and routing logic, and use prompts for conversational behavior.

## What flows are for

Flows are best used when the agent needs to move through a structured process such as:

- collecting information in a defined order
- confirming details before taking action
- calling APIs or deterministic logic at specific points
- handling success, failure, and retry paths explicitly

<div class="grid cards" markdown>

-   **Default steps**

    ---

    LLM-driven steps for collecting information and transitioning based on conditions.

-   **Advanced steps**

    ---

    Steps with more control over ASR, DTMF, and callable transition functions.

-   **Function steps**

    ---

    Deterministic Python steps for routing, validation, and API calls.

</div>

## Entering a flow

A flow can be entered in several ways.

### From code

~~~python
conv.goto_flow("Flow Name")
~~~

This enters the flow at its configured start step.

### Via a returned transition

~~~python
return {"transition": {"goto_flow": "Flow Name", "goto_step": "Step Name"}}
~~~

### Within a flow

~~~python
flow.goto_step("Step Name")
~~~

This is only available inside flow functions.

## File structure

Flows live under the `flows/` directory.

~~~text
flows/
└── {flow_name}/
    ├── flow_config.yaml
    ├── steps/
    │   └── {step_name}.yaml
    ├── function_steps/
    │   └── {function_step}.py
    └── functions/
        └── {function_name}.py
~~~

Directory and file names are cleaned to lowercase snake_case.

## Flow configuration

Each flow includes a `flow_config.yaml` file that defines the flow itself.

### Fields

| Field | Required | Description |
|---|---|---|
| `name` | No | Human-readable flow name |
| `description` | Yes | What the flow does |
| `start_step` | Yes | The step to enter when the flow starts |

### Example

~~~yaml
name: Example Flow
description: Handles the booking process
start_step: Collect Details
~~~

## Step types

A step represents the agent's current position in the flow.

There are three step types:

1. default steps
2. advanced steps
3. function steps

## Default steps

Default steps live in `steps/*.yaml`.

These steps use LLM logic to process information and transition based on configured conditions. They cannot call transition functions from their prompt.

ASR biasing is automatically configured based on the entities requested in the step.

### Fields

| Field | Description |
|---|---|
| `step_type` | Must be `default_step` |
| `name` | Human-readable step name |
| `conditions` | Conditions that control transitions |
| `extracted_entities` | Entities to collect in the step |
| `prompt` | Prompt shown to the model |

### Prompt behavior

Default step prompts may use entity references such as:

~~~text
{{entity:entity_name}}
~~~

They should not contain function calls.

### Conditions

Conditions define how the agent transitions out of a default step.

A condition can:

- go to another step
- exit the flow

### Condition fields

| Field | Description |
|---|---|
| `condition_type` | `step_condition` or `exit_flow_condition` |
| `description` | When this condition applies |
| `child_step` | Next step, only for `step_condition` |
| `required_entities` | Entities that must be collected before the condition can trigger |

### `child_step` rules

Use the correct step identifier depending on target type:

- **Default step** or **advanced step**: use the step's `name`
- **Function step**: use the Python filename without `.py`

## Advanced steps

Advanced steps also live in `steps/*.yaml`.

These steps support additional controls such as:

- custom ASR tuning
- DTMF collection rules
- transition function calls from the prompt

### Fields

| Field | Description |
|---|---|
| `step_type` | Must be `advanced_step` |
| `name` | Human-readable step name |
| `asr_biasing` | ASR tuning for the turn |
| `dtmf_config` | DTMF collection settings |
| `prompt` | Prompt shown to the model |

### ASR biasing

Advanced steps can tune ASR toward specific kinds of user input.

Supported ASR biasing fields include:

- `alphanumeric`
- `name_spelling`
- `numeric`
- `party_size`
- `precise_date`
- `relative_date`
- `single_number`
- `time`
- `yes_no`
- `address`
- `custom_keywords`

### DTMF configuration

Advanced steps can also define DTMF behavior, including:

- `inter_digit_timeout`
- `max_digits`
- `end_key`
- `collect_while_agent_speaking`
- `is_pii`

## Step prompt design

Prompts should be used for:

- collecting input
- presenting information
- shaping the conversational turn

Python should be used for:

- comparisons
- conditionals
- routing
- state-driven decisions

!!! warning "Do not put deterministic branching logic into prompts"

    Do not encode logic like “If $x == 0 do A, else do B” in prompts. Put that logic in Python and transition to the correct step explicitly.

### Prompt tips

- use markdown headers to structure instructions
- keep one clear purpose per step
- include validation and edge cases where needed
- use voice-friendly phrasing for spoken interactions
- make transitions explicit

## Function steps

Function steps live in `function_steps/*.py`.

These are deterministic Python steps with no LLM decision-making involved. They are ideal for:

- API calls
- validation
- state updates
- explicit routing

### Signature

~~~python
def function_name(conv: Conversation, flow: Flow):
~~~

### Important rules

Function steps:

- cannot define extra parameters
- cannot use `@func_description`
- must control flow explicitly

A function step must call either:

- `flow.goto_step(...)`
- `conv.exit_flow()`

and may also return a context string for the model.

### Common uses

<div class="grid cards" markdown>

-   **Validation**

    ---

    Check whether collected input is valid before the flow continues.

-   **Routing**

    ---

    Move to the correct step based on deterministic logic.

-   **External calls**

    ---

    Call APIs and store the results in state.

-   **Error handling**

    ---

    Send the flow to an error step with a useful context string.

</div>

## Transition functions

Transition functions live in `functions/*.py` inside a flow.

They can be called from advanced-step prompts and are referenced using:

~~~text
{{ft:flow_function}}
~~~

Unlike function steps, transition functions:

- may define custom parameters
- may have a description shown to the model
- can be called by the model within the same flow

Logic reused across flows is usually better placed in global functions.

## Best practices

- keep one clear purpose per step
- start with a simple linear path, then add branching
- use confirmation steps before function steps that change state
- add explicit error and failure paths
- use meaningful step names
- test the full path from entry to exit

!!! tip "Prefer simple flows first"

    A clean A → B → C path is easier to reason about and test than a highly branched flow built too early.

## Common mistakes

- leaving a flow function without advancing the flow
- encoding branching logic in prompts
- using internal IDs instead of resource names
- putting too much deterministic logic into LLM-driven steps
- mixing `conv.exit_flow()` with additional navigation
- using `end_turn=False` when the user is actually expected to reply

## Design principles

1. start with a single path
2. add branching only where needed
3. use function steps for deterministic logic
4. use prompts for conversational behavior
5. make every transition explicit

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn how global functions, transition functions, and function steps differ.
    [Open functions](./functions.md)

-   **Entities**

    ---

    See how structured data collection fits into flow steps and conditions.
    [Open entities](./entities.md)

</div>