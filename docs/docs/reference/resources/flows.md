---
title: Flows
description: Define multi-step processes that guide the agent through structured tasks in the PolyAI ADK.
---

# Flows

<p class="lead">
Flows choreograph multi-step processes. At any given moment, the model only sees the current step's prompt and tools.
</p>

A good flow keeps each step focused on a single task. Use Python for branching, validation, and routing logic, and use prompts for conversational behavior.

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

The flow directory name is derived from the flow's `name` field, converted to lowercase snake_case. A flow named `Booking Flow` must live in `flows/booking_flow/`. If the directory name does not match, the ADK will not recognize the flow.

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

    Steps that call transition functions from the prompt instead of relying on built-in conditions.

-   **Function steps**

    ---

    Deterministic Python steps for routing, validation, and API calls.

</div>

Default and advanced steps can both override project-level ASR, VAD, barge-in, and LLM settings for a single turn — see [step settings](#step-settings) below.

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

Default steps can also include any of the [step settings](#step-settings) below.

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

Unlike default steps, they don't define `conditions` or `extracted_entities` — instead they transition by calling transition functions from the prompt.

### Fields

| Field | Description |
|---|---|
| `step_type` | Must be `advanced_step` |
| `name` | Human-readable step name |
| `prompt` | Prompt shown to the model. May call transition functions. |

Advanced steps can also include any of the [step settings](#step-settings) below.

## Step settings

Both default and advanced steps can override project-level ASR, DTMF, VAD, barge-in, and LLM behavior for a single turn. Each settings block below is optional and sits at the top level of the step file — omit a block to inherit the project-level setting.

### ASR biasing

Steps can tune ASR toward specific kinds of user input.

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

Steps can also define DTMF behavior, including:

- `inter_digit_timeout`
- `max_digits`
- `end_key`
- `collect_while_agent_speaking`
- `is_pii`

### ASR override

Override the speech recognition provider or model for this step.

| Field | Description |
|---|---|
| `provider` | ASR provider to use for this step |
| `model` | ASR model to use for this step |

### VAD

Tune voice activity detection — how the platform decides the caller has started and stopped speaking.

| Field | Description |
|---|---|
| `provider` | VAD provider to use for this step |
| `vad_start` | Seconds of speech before the caller is considered to have started |
| `vad_end` | Seconds of silence before the caller is considered to have stopped |
| `speech_threshold` | Sensitivity for detecting speech |
| `silence_threshold` | Sensitivity for detecting silence |

### Barge-in

Control whether the caller can interrupt the agent on this step.

~~~yaml
barge_in:
  is_enabled: false
~~~

Use this to protect a step the caller should hear in full, such as a legal disclaimer.

### LLM

Override the model or its reasoning effort for a single step.

| Field | Description |
|---|---|
| `provider_model_id` | Model to use for this step |
| `reasoning_effort` | One of `unspecified`, `minimal`, `low`, `medium`, `high`, `auto` |

~~~yaml
llm:
  provider_model_id: <model-id>
  reasoning_effort: high
~~~

Raising reasoning effort on a step that has to weigh several conditions can improve reliability; lowering it on a simple collection step reduces latency.

### Clearing a settings block

Removing a block from the step file clears that override on the next push — but only for `asr`, `vad`, `barge_in`, and `llm`. `asr_biasing` and `dtmf_config` deep-merge into their platform-side values instead, so to turn those off set `is_enabled: false` rather than deleting the block.

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

These are deterministic Python steps. They execute directly, with no model interpretation. Use them for:

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
- must have a name that is unique across the whole project, not just within their own flow — a duplicate name in a different flow causes a build error

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

## Validation

- `inter_digit_timeout` and `max_digits` (DTMF configuration) cannot be negative.
- `vad_start` and `vad_end` (VAD) must be finite and non-negative — `poly validate` rejects a negative or infinite value.

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

### A flow function that does not advance the flow

Flow functions must **always advance** the flow. A function that returns without changing step or flow leaves the agent sitting in the same logical place with no clear next state.

| Avoid | Prefer |
|---|---|
| Returning from a flow function without changing step or flow | `flow.goto_step(...)` |
| Leaving navigation implicit | Returning an explicit transition |
| Assuming the model will recover the flow state on its own | Making the next state obvious in code |

!!! danger "A stuck flow is usually a control-flow bug"

    If a flow function does not move the agent forward, the conversation can become stuck in an invalid or confusing state.

### Mixing `conv.exit_flow()` with navigation

Do not create a dedicated **"Anything else?"** step just to wrap up a flow. When the flow is finished, exit it and return the closing prompt there.

Calling `conv.exit_flow()` and then also navigating does not do both — the navigation overrides the exit:

~~~python
# Wrong — the transition wins, the exit is discarded
conv.exit_flow()
return {"transition": {"goto_flow": "Another Flow"}}

# Wrong — same problem
conv.exit_flow()
conv.goto_flow("Another Flow")
~~~

Pick one: exit the flow and return the closing content, **or** navigate to another step or flow. Never both.

### `end_turn=False` while waiting for a reply

`end_turn=False` should only be used when the agent speaks and then immediately performs another action in the **same turn**, without waiting for input.

~~~text
"Your balance is X."
→ immediately call balance_informed
~~~

Using it after the agent asks a question produces awkward control flow, because the question should simply be part of the normal utterance. If the caller is expected to answer, put the full question in the utterance and let the turn end normally.

### Others

- encoding branching logic in prompts rather than Python
- using internal IDs instead of resource names
- putting too much deterministic logic into LLM-driven steps
- reading entity values with `conv.entities` where a prompt reference would do — use `{{entity:entity_name}}` directly in the step prompt

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn how global functions, transition functions, and function steps differ.
    [Open functions](./functions.md)

-   **Topics**

    ---

    See how topics trigger flow entry via `conv.goto_flow` in their actions.
    [Open topics](./topics.md)

-   **Entities**

    ---

    See how structured data collection fits into flow steps and conditions.
    [Open entities](./entities.md)

-   **Resource architecture**

    ---

    Where facts belong in rules and topics versus logic in Python — the broader pattern behind the prompts-vs-code mistake above.
    [Open resource architecture](../../development/resource-architecture.md#common-mistakes)

-   **Return values reference (platform)**

    ---

    All supported function return shapes used in flow transitions — utterance, hangup, goto_flow, and combined dicts.
    [Open return values reference](https://docs.poly.ai/tools/return-values){ target="_blank" rel="noopener" }

-   **Conversation object reference (platform)**

    ---

    Full reference for `conv.goto_flow`, `conv.exit_flow`, `flow.goto_step`, and all other flow navigation methods.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }

</div>
