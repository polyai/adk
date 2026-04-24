# Flows

## Purpose
Flows choreograph multi-step processes. The LLM only sees the current step's prompt and tools. Prefer one task per step; do branching and conditionals in Python via transitions.

## Entering a flow
- **From code**: `conv.goto_flow('Flow Name')` (enters at configured Start Step).
- **Via return**: `return {"transition": {"goto_flow": "Flow Name", "goto_step": "Step Name"}}`.
- **Within a flow**: `flow.goto_step("Step Name")` in flow functions only.

To make a flow reachable from general conversation, create a topic as its entry point:
  topics/new_flow.yaml       → actions: "Call {{fn:start_my_flow}}"
  functions/start_new_flow.py → conv.goto_flow("New Flow")

## File structure
```
flows/
└── {flow_name}/                    # lowercase, snake_case
    ├── flow_config.yaml
    ├── steps/
    │   └── {step_name}.yaml        # default or advanced steps
    ├── function_steps/
    │   └── {function_step}.py      # deterministic Python steps
    └── functions/
        └── {function_name}.py      # transition functions (called from advanced steps)
```

Directory and file names are cleaned to lowercase snake_case.

## Flow config (`flow_config.yaml`)
Information about the flow.

Fields:
- **name**: Human-readable flow name
- **description** (required): What this flow does
- **start_step** (required): Name of the step to enter when the flow is triggered. Must match a real step name.

Example:
```yaml
name: Example Flow
description: Handles the booking process
start_step: Collect Details
```

## Flow Steps
A step represents the agent's current position in the flow. There are 3 types of steps: default steps (no code), advanced steps, and function steps.

### Default Steps (`steps/*.yaml`)
These steps use only LLM logic to process data and transition to other steps. They can define conditions for how to do this.
They cannot reference transition functions in their prompt.

ASR biasing is automatically set up based on the entities requested.

Fields:
- **step_type**: `default_step`
- **name**: Human-readable step name
- **conditions**: List of conditions to transition to other steps
- **extracted_entities**: Entities to extract in this step (from `config/entities.yaml`)
- **prompt**: Instructions for the LLM; use `{{entity:entity_name}}` for entity values. Cannot call functions

#### Conditions
These define how the agent can transition out of one default node. They can transition to any other node and also be made to exit the flow.

Example:
- **condition_type**: `step_condition` (go to another step) or `exit_flow_condition` (exit flow)
- **description**: When this condition applies
- **child_step**: Next step - **only for step_condition**; omit for exit_flow_condition
- **required_entities**: Entities that must be collected before this condition can trigger

**child_step rules:**
- **Default step**/**Advance step** → use its `name:` (e.g. `Collect Date of Birth`)
- **Function step** → use Python filename without `.py`, snake_case (e.g. `process_cancellation`).

### Advanced Steps (`steps/*.yaml`)
A step with more advanced options, such as custom ASR and DTMF rules and the ability to call transition functions in the prompt.

Fields:
- **step_type**: `advanced_step`
- **name**: Human-readable step name
- **asr_biasing**: ASR settings for the turn
  **is_enabled** Boolean if ASR settings are enabled
  ASR settings, each is a boolean of whether to tune ASR for that type of input
  **alphanumeric**
  **name_spelling**
  **numeric**
  **party_size**
  **precise_date**
  **relative_date**
  **single_number**
  **time**
  **yes_no**
  **address**
  **custom_keywords**: [] List of words to bias for
- **dtmf_config**:
  **is_enabled** Boolean if ASR settings are enabled
  **inter_digit_timeout** (int) How long to wait in seconds between button presses
  **max_digits** (int) Max number of digits to collect
  **end_key** (str) When key is pressed, end collection
  **collect_while_agent_speaking** (bool) Allow collection during agents speech
  **is_pii** (bool) Does user input count as PII
- **prompt**: Instructions for the LLM; Can call functions


### Step prompts
Tips:
- **Prompts**: for collecting input, presenting info, conversation. **Python**: for comparisons, if/else, routing on state.
- **No deterministic logic in prompts**: no "If $x == 0 do A" in prompts. Do value checks and routing in Python and transition to the right step.
- **State in prompts**: use `$variable`, not `conv.state.variable`. No `$var.attribute`; stringify in Python and reference a single state string.
- **Flow function reference**: `{{ft:flow_function}}` in advanced step prompts only.

### Function Steps (`function_steps/*.py`)

Function steps are deterministic Python steps in the flow. They execute code without LLM involvement, making them ideal for API calls, data validation, and routing logic. They are best used in conjunction with default steps.

Unlike regular functions, function steps cannot have additional parameters and cannot set a description.

For more information, look at the `functions` docs.

**Signature**: `def function_name(conv: Conversation, flow: Flow):`

Tips:
- **Entities**: Read using `conv.entities.entity_name.value`; check with `if conv.entities.entity_name: ...`
- **State**: `conv.state.variable_name = value` (use `$variable_name` in prompts)
- **Flow control**: Must call `flow.goto_step('Step Name', 'Reason')` or `conv.exit_flow()`
- **Return**: Optional string used as LLM context (what happened and what to tell the user)
- **Errors**: try/except; log; `flow.goto_step('error_step', 'Reason')` and return context string
- **Logging/metrics**: `conv.log.info/warning/error(...)`, `conv.write_metric("NAME", value)`

## Transition functions (`functions/*.py`)

Transition functions can be called in `advanced_step`s. They can be used to transition the agent to other steps.
Unlike function steps, you can define a custom set of parameters for them and give them a description that the LLM uses to judge when to call them.

These can be referenced using `{{ft:flow_function}}` and can only be called within the same flow.

Tips:
Logic that is reused between flow functions is best put in global functions, which can be imported or called with `conv.functions.my_global_function(...)`.
Keep logic here simple, so it's easy to view at a glance what the function is doing.

For more information, look at the `functions` docs.

## Best practices
- **No "Anything else?" step**: when the flow is done, `conv.exit_flow()` and return the "anything else?" prompt from the function.
- **Hard-coded utterances**: put them in `utterances.py` and return from the caller (e.g. start_function); don't add a flow function only to return one phrase.
- **Prompts:** Use markdown headers, clear order of operations, validation/edge cases, voice-friendly phrasing ("read digit by digit"), and clear "Once X, then Y" transitions.
- **Concepts:** Linear (A->B->C), branching, loops (back to earlier steps), exit_flow_condition for leaving the flow, required_entities and extracted_entities for collection and gating

## Common mistakes
- **Flow functions must always advance**: use `flow.goto_step(...)` or return a transition; don't leave the flow stuck on the same step with no navigation.
- **No deterministic logic in prompts**: don't encode branching in prompts (e.g. "If $x == 0 do A, else B"). Do value checks and routing in Python and transition to the right step.
- **No hardcoded IDs**: use resource names, not internal IDs.
- **Don't read entities in default step code**: entity values are available in prompts via `{{entity:entity_name}}`.
- **Function steps must control flow**: every function step must call `flow.goto_step(...)` or `conv.exit_flow()` and return LLM context. Keep complex logic in function steps, not prompts.
- **`end_turn=False`**: use only when the agent must immediately call a function after speaking (no user reply). Don't use it just to add a question after an utterance; put the question in the utterance.
- **Don't mix exit and navigation**: use **either** `conv.exit_flow()` and return content **or** a transition/goto, not both. `conv.goto_flow(...)` after `conv.exit_flow()` will override the exit.

## Design principles
1. Start with a single path, then add branching
2. Add a confirmation step before function steps that change state
3. Add steps/conditions for errors and failures
4. One clear purpose per step; meaningful step names
5. Test the full path from start to exit
