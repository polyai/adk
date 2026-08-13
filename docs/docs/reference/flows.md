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

    Steps with more control over callable transition functions, plus optional per-turn overrides.

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

The flow directory name is derived from the flow's `name` field, converted to lowercase snake_case. A flow named `Booking Flow` must live in `flows/booking_flow/`. If the directory name does not match, the ADK will not recognize the flow.

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
| (step settings) | Any of the [step settings](#step-settings) below |

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

These steps support additional controls such as calling transition functions from the prompt, and optional per-turn overrides for ASR, VAD, barge-in, and LLM settings.

### Fields

| Field | Description |
|---|---|
| `step_type` | Must be `advanced_step` |
| `name` | Human-readable step name |
| `prompt` | Prompt shown to the model |
| (step settings) | Any of the [step settings](#step-settings) below |

## Step settings

Steps can override project-level voice and LLM defaults for a single turn. Every section is optional — omit a section to inherit the project default. All settings apply to both default and advanced steps.

~~~yaml
step_type: advanced_step
name: Collect Card Number
asr_biasing:
  is_enabled: true
  numeric: true
  custom_keywords:
  - Acme
dtmf_config:
  is_enabled: true
  max_digits: 4
  end_key: '#'
asr:
  provider: deepgram
  model: nova-3
vad:
  vad_start: 0.2
  vad_end: 0.8
barge_in:
  is_enabled: false
llm:
  provider_model_id: polywhirl-3-5
  reasoning_effort: medium
prompt: Please read out your card number.
~~~

### `asr_biasing`

ASR tuning for the turn.

| Field | Description |
|---|---|
| `is_enabled` | (bool) Whether ASR biasing is enabled |
| `alphanumeric`, `name_spelling`, `numeric`, `party_size`, `precise_date`, `relative_date`, `single_number`, `time`, `yes_no`, `address` | (bool) Whether to tune ASR for that type of input |
| `custom_keywords` | (list[str]) Words to bias towards |

### `dtmf_config`

Keypad input settings.

| Field | Description |
|---|---|
| `is_enabled` | (bool) Whether DTMF collection is enabled |
| `inter_digit_timeout` | (int) How long to wait in seconds between button presses. Cannot be negative |
| `max_digits` | (int) Max number of digits to collect. Cannot be negative |
| `end_key` | (str) When this key is pressed, end collection |
| `collect_while_agent_speaking` | (bool) Allow collection during the agent's speech |
| `is_pii` | (bool) Does user input count as PII |

### `asr`

Speech recognition provider override.

| Field | Description |
|---|---|
| `provider` | (str) ASR provider name |
| `model` | (str) ASR model name |

### `vad`

Voice activity detection override.

| Field | Description |
|---|---|
| `provider` | (str) VAD provider name |
| `vad_start` | (float) Seconds. Must be zero or greater |
| `vad_end` | (float) Seconds. Must be zero or greater |
| `speech_threshold` | (float) |
| `silence_threshold` | (float) |

### `barge_in`

Whether the caller can interrupt the agent.

| Field | Description |
|---|---|
| `is_enabled` | (bool) Whether barge-in is enabled |

### `llm`

Model override for the turn.

| Field | Description |
|---|---|
| `provider_model_id` | (str) Model identifier |
| `reasoning_effort` | (str) One of `unspecified`, `minimal`, `low`, `medium`, `high`, `auto` |

### Removing settings

`asr`, `vad`, `barge_in` and `llm` are removed by deleting the section from the file; the step then inherits the project default again.

`asr_biasing` and `dtmf_config` behave differently — the platform merges them rather than replacing them, so they cannot be removed. Turn them off with `is_enabled: false` instead. A disabled `asr_biasing` or `dtmf_config` is written back out as an absent section, so after a `poly pull` a disabled section will not appear in the file.

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

    Do not encode logic like "If $x == 0 do A, else do B" in prompts. Put that logic in Python and transition to the correct step explicitly.

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

-   **Topics**

    ---

    See how topics trigger flow entry via `conv.goto_flow` in their actions.
    [Open topics](./topics.md)

-   **Entities**

    ---

    See how structured data collection fits into flow steps and conditions.
    [Open entities](./entities.md)

-   **Return values reference (platform)**

    ---

    All supported function return shapes used in flow transitions — utterance, hangup, goto_flow, and combined dicts.
    [Open return values reference](https://docs.poly.ai/tools/return-values){ target="_blank" rel="noopener" }

-   **Conversation object reference (platform)**

    ---

    Full reference for `conv.goto_flow`, `conv.exit_flow`, `flow.goto_step`, and all other flow navigation methods.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }

</div>
