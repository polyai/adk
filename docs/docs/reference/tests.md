---
title: Tests
description: Write and manage simulated conversation test cases in the PolyAI ADK, and understand how testing fits into the local workflow.
---

# Tests

<p class="lead">
Agent Studio test cases are simulated conversations that run your agent end-to-end in the sandbox environment. They are managed locally as YAML files under <code>test_suite/</code> and pushed to Agent Studio with <code>poly push</code>.
</p>

Each test case describes a scenario for a simulated user and a set of assertions to evaluate against the resulting conversation. Tests run inside Agent Studio against the pushed branch — the ADK does not execute them locally.

!!! warning "There is no local runtime"

    The ADK does not execute your agent on your local machine. There is no `poly serve` command or local simulator. All agent execution happens inside Agent Studio's sandbox environment. To test runtime behavior, push your changes and use `poly chat`, or test interactively through Agent Studio.

## Where tests fit in the workflow

Tests sit between validation and merge in the standard [CLI working pattern](./cli.md#working-pattern). Edit locally, validate with `poly validate`, push, then run the suite from Agent Studio or chat against the branch with `poly chat`.

<div class="grid cards" markdown>

-   **Validation**

    ---

    Use `poly validate` to check project configuration before pushing.

-   **Simulated conversations**

    ---

    Define test cases under `test_suite/` and run them in Agent Studio.

-   **Interactive review**

    ---

    Use `poly chat` and Agent Studio to spot-check behavior on the pushed branch.

</div>

## Location

Test cases are defined as one YAML file per test under:

~~~text
test_suite/
├── greeting_flow_test.yaml
└── webchat_smoke_test.yaml
~~~

The directory is optional. Create it only when you have test cases to define.

!!! info "Filename must match the test name"

    The filename (without `.yaml`) must match the normalized form of the `name` field: lowercased, with punctuation replaced by underscores. `Greeting flow test` becomes `greeting_flow_test.yaml`. `poly push` rejects mismatched names.

## What a test case contains

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Human-readable test name. Must match the filename when normalized. |
| `scenario` | Yes | Natural-language description of what the simulated user does. Drives the simulator turn-by-turn. |
| `channel` | Yes | `voice` or `webchat`. |
| `language` | Yes | BCP 47 language tag (e.g. `en-GB`). Must be a configured language in the project. |
| `variant` | No | Name of a variant from `config/variant_attributes.yaml`. Defaults to the project default variant. |
| `tags` | No | List of strings used to group, filter, or schedule tests in Agent Studio. |
| `prompt_assertions` | No | List of natural-language statements that must hold about the agent's behavior. Each is evaluated by an LLM judge. |
| `function_call_assertions` | No | List of expected function calls and their argument values. |

At least one of `prompt_assertions` or `function_call_assertions` should be set — a test with no assertions runs but cannot pass or fail.

## Prompt assertions

Each prompt assertion is a free-text statement evaluated against the full conversation by an LLM judge. Write them as observable behaviors, not internal reasoning.

~~~yaml
prompt_assertions:
  - The agent confirms the caller's booking reference before continuing
  - The agent does not ask for the caller's date of birth
~~~

## Function call assertions

Each function call assertion checks that a global function was called and, optionally, with specific argument values.

| Field | Description |
|---|---|
| `name` | Global function name. Must match a function in `functions/`. |
| `arguments` | List of argument assertions. May be empty to check only that the function was called. |

Argument assertion fields:

| Field | Description |
|---|---|
| `parameter_name` | Parameter as defined on the function. |
| `expected_value` | Expected value, expressed as a string. |
| `value_type` | One of `string`, `integer`, `number`, `boolean`. |

~~~yaml
function_call_assertions:
  - name: lookup_booking
    arguments:
      - parameter_name: booking_reference
        expected_value: "ABC123"
        value_type: string
      - parameter_name: party_size
        expected_value: "4"
        value_type: integer
~~~

Only function name and argument values are asserted. The function does not have to be the only call in the conversation, and the order of calls is not checked.

## Example

~~~yaml
name: Greeting flow test
scenario: Ask for help with booking.
channel: voice
language: en-GB
tags:
  - booking
  - smoke
prompt_assertions:
  - The agent offers to help with booking
function_call_assertions:
  - name: lookup_booking
    arguments:
      - parameter_name: booking_reference
        expected_value: "ABC123"
        value_type: string
~~~

A minimal webchat smoke test with only a prompt assertion:

~~~yaml
name: Webchat smoke test
scenario: Say hello on webchat.
channel: webchat
language: en-GB
tags:
  - smoke
prompt_assertions:
  - The agent greets the user
~~~

## Validation

`poly validate` checks each test case:

- `channel` must be `voice` or `webchat`
- `scenario` is required and non-empty
- `language` is required and must be one of the project's configured languages (`default_language` or `additional_languages`)
- `variant`, if set, must reference a variant declared in `config/variant_attributes.yaml`
- each `function_call_assertions[*].name` must match a global function under `functions/`
- each argument's `value_type` must be one of `string`, `integer`, `number`, `boolean`
- the filename must match the normalized `name`

Validation runs automatically as part of `poly push`.

## Push and run

Test cases follow the standard ADK lifecycle:

1. edit YAML files under `test_suite/` locally
2. validate with `poly validate`
3. push with `poly push` to sync to Agent Studio
4. run the suite from Agent Studio against the pushed branch

`poly push` creates, updates, or deletes test cases on Agent Studio to match local state, including `prompt_assertions` and `tags`. There is no `poly test` command — execution happens in Agent Studio.

!!! tip "Tests are branch-scoped"

    Tests are pushed to the current branch and run against that branch's agent. Use a branch per scenario when iterating on flows or topics so test results map cleanly to the change under review.

## What to cover

Good coverage of a project usually includes:

- the happy path of every flow and major topic
- key error paths — missing booking, invalid input, unavailable slot
- function call shape — confirm the agent calls the right function with the right arguments for each branch of logic
- state transitions across turns — confirm later turns reference earlier user input
- behavior on the channels your project actually ships on (voice, webchat, or both)

## Best practices

- write `scenario` as a short, concrete user goal — "Ask to cancel a booking with reference ABC123" — not a script
- prefer prompt assertions for behavior, function call assertions for integration correctness
- keep each test case focused on one outcome; split combined scenarios into multiple files
- use `tags` consistently (`smoke`, `regression`, `<flow_name>`) so suites can be filtered in Agent Studio
- cover error paths, not only success cases
- add a webchat and a voice variant of any critical path that runs on both channels
- validate as part of the normal edit loop, not just before merge
- combine the suite with `poly chat` and interactive review in Agent Studio when behavior depends on the full conversation flow

## Related pages

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    `poly validate`, `poly push`, and `poly chat` — the commands used in the test workflow.
    [Open CLI reference](./cli.md)

-   **Functions**

    ---

    Reference for the global functions named in function call assertions.
    [Open functions](./functions.md)

-   **Variants**

    ---

    Define the variants referenced by the `variant` field.
    [Open variants](./variants.md)

-   **Languages**

    ---

    Configure the languages a test case can target.
    [Open languages](./languages.md)

-   **Working locally**

    ---

    How tests fit into the daily edit / validate / push loop.
    [Open working locally](../concepts/working-locally.md)

</div>
