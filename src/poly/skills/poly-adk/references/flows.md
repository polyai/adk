# Flows

## Purpose
Flows choreograph multi-step processes. The LLM only sees the current step's prompt and tools. Prefer one task per
step; do branching and conditionals in Python via transitions, not in prompts.

## Entering a flow
- **From code**: `conv.goto_flow('Flow Name')` (enters at the configured Start Step).
- **Via return**: `return {"transition": {"goto_flow": "Flow Name", "goto_step": "Step Name"}}`.
- **Within a flow**: `flow.goto_step("Step Name")` — flow functions only.

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
| Field | Notes |
|---|---|
| `name` | Human-readable flow name |
| `description` (required) | What this flow does |
| `start_step` (required) | Step to enter on trigger; must match a real step name |

```yaml
name: Example Flow
description: Handles the booking process
start_step: Collect Details
```

## Flow steps
Three types: default steps (no code), advanced steps, and function steps.

### Default steps (`steps/*.yaml`)
LLM-only logic. Cannot reference transition functions. ASR biasing is auto-configured from requested entities.

| Field | Notes |
|---|---|
| `step_type` | `default_step` |
| `name` | Human-readable step name |
| `conditions` | List of conditions to transition out (see below) |
| `extracted_entities` | Entities to extract this step (from `config/entities.yaml`) |
| `prompt` | Instructions for the LLM; use `{{entity:entity_name}}`; cannot call functions |

**Conditions**
| Field | Notes |
|---|---|
| `condition_type` | `step_condition` (go to another step) or `exit_flow_condition` (exit flow) |
| `description` | When this condition applies |
| `child_step` | Next step — only for `step_condition`; omit for `exit_flow_condition` |
| `required_entities` | Entities that must be collected before this condition can trigger |

`child_step` rules: for a default/advanced step use its `name:`; for a function step use the Python filename
without `.py`, in snake_case.

### Advanced steps (`steps/*.yaml`)
Adds custom ASR/DTMF rules and the ability to call transition functions from the prompt.

| Field | Notes |
|---|---|
| `step_type` | `advanced_step` |
| `name` | Human-readable step name |
| `asr_biasing.is_enabled` | Boolean |
| `asr_biasing.{alphanumeric, name_spelling, numeric, party_size, precise_date, relative_date, single_number, time, yes_no, address}` | Booleans — tune ASR for that input type |
| `asr_biasing.custom_keywords` | List of words to bias for |
| `dtmf_config.is_enabled` | Boolean |
| `dtmf_config.inter_digit_timeout` | Seconds between key presses |
| `dtmf_config.max_digits` | Max digits to collect |
| `dtmf_config.end_key` | Key that ends collection |
| `dtmf_config.collect_while_agent_speaking` | Boolean |
| `dtmf_config.is_pii` | Boolean — does input count as PII |
| `prompt` | Instructions; can call functions via `{{ft:flow_function}}` |

### Function steps (`function_steps/*.py`)
Deterministic Python — no LLM. Best for API calls, validation, and routing. Cannot have extra parameters or a
description (unlike transition functions).

**Signature**: `def function_name(conv: Conversation, flow: Flow):`

- Read entities: `conv.entities.entity_name.value`; check with `if conv.entities.entity_name:`
- State: `conv.state.variable_name = value` (reference as `$variable_name` in prompts)
- Must call `flow.goto_step('Step Name', 'Reason')` or `conv.exit_flow()`
- Return: optional string used as LLM context (what happened, what to tell the user)
- Errors: try/except; log; `flow.goto_step('error_step', 'Reason')`, return a context string
- Logging/metrics: `conv.log.info/warning/error(...)`, `conv.write_metric("NAME", value)`

## Transition functions (`functions/*.py`)
Called from `advanced_step` prompts via `{{ft:flow_function}}`; same flow only. Unlike function steps, they can
define custom parameters and a description that the LLM uses to decide when to call them. Put logic reused across
functions into global functions and call via `conv.functions.my_global_function(...)`. Keep flow functions simple.

## Best practices
- No "Anything else?" step — `conv.exit_flow()` and return that prompt as context from the function instead.
- Hard-coded utterances go in `utterances.py`, returned from the caller (e.g. `start_function`) — don't add a
  flow function just to return one phrase.
- Prompts: markdown headers, clear order of operations, validation/edge cases, voice-friendly phrasing ("read
  digit by digit"), and explicit "Once X, then Y" transitions.
- Concepts: linear (A→B→C), branching, loops (back to earlier steps), `exit_flow_condition` to leave the flow,
  `required_entities`/`extracted_entities` for collection and gating.

## Common mistakes
- Flow functions must always advance — use `flow.goto_step(...)` or a transition; never leave the flow stuck.
- No deterministic logic in prompts — do value checks/branching in Python, then transition.
- No hardcoded IDs — use resource names.
- Don't read entities in default-step code — entity values are only available in prompts via `{{entity:...}}`.
- Function steps must control flow — every one must call `flow.goto_step(...)` or `conv.exit_flow()` and return
  LLM context. Keep complex logic here, not in prompts.
- `end_turn=False` only when the agent must immediately call a function after speaking with no user reply — don't
  use it just to add a question after an utterance; put the question in the utterance.
- Don't mix exit and navigation — `conv.exit_flow()` **or** a transition/`goto_flow`, not both; a later
  `goto_flow` overrides an earlier `exit_flow`.

## Design principles
1. Start with a single path, then add branching.
2. Add a confirmation step before function steps that change state.
3. Add steps/conditions for errors and failures.
4. One clear purpose per step; meaningful step names.
5. Test the full path from start to exit.
