---
title: Tests
description: Write and manage simulated conversation test cases in the PolyAI ADK, and understand how testing fits into the local workflow.
---

# Tests

<p class="lead">
Agent Studio test cases are simulated conversations that run your agent end-to-end in the sandbox environment. They are managed locally as YAML files under <code>test_suite/</code> and pushed to Agent Studio with <code>poly push</code>.
</p>

Each test case describes a scenario for a simulated user and a set of assertions to evaluate against the resulting conversation. Then, the tests run inside Agent Studio against the pushed branch.

## Where tests fit in the workflow

Tests sit between validation and merge in the standard [CLI working pattern](./cli.md#working-pattern). Edit locally, validate with `poly validate`, push, then trigger and inspect the test suite with `poly test`.

<div class="grid cards" markdown>

-   **Validation**

    ---

    Use `poly validate` to check project configuration before pushing.

-   **Simulated conversations**

    ---

    Define test cases under `test_suite/` and run them with `poly test run`.

-   **Interactive review**

    ---

    Use `poly chat`, `poly test show`, and Agent Studio to spot-check behavior on the pushed branch.

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
| `tags` | No | List of strings used to group, filter, or schedule tests. Usable with `poly test run --tag`. |
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
4. trigger and monitor the suite with `poly test run`

`poly push` creates, updates, or deletes test cases on Agent Studio to match local state, including `prompt_assertions` and `tags`. Use `poly test run` to trigger execution and `poly test show` / `poly test list` to inspect results — all without leaving the terminal.

!!! tip "Tests are branch-scoped"

    Tests are pushed to the current branch and run against that branch's agent. Use a branch per scenario when iterating on flows or topics so test results map cleanly to the change under review.

## Running tests from the CLI

The `poly test` command group covers the full testing lifecycle.

### `poly test run`

Trigger a test run against the current branch. Runs all tests by default.

~~~bash
poly test run
poly test run --tag smoke
poly test run --files test_suite/greeting_flow_test.yaml
poly test run --dry-run
poly test run --dont-poll
poly test run --push
~~~

After triggering, the CLI polls for results every 5 seconds and displays a live-updating table. For projects with 20 or fewer tests the full table is shown; for larger suites a compact rolling view is used instead. Both views update in place until the run completes.

| Flag | Description |
|---|---|
| `--files` | One or more specific test YAML files to run. |
| `--tag` | Run only tests that carry the specified tag(s). Multiple tags are OR-matched. |
| `--dry-run` | Preview which tests would run without triggering them. |
| `--dont-poll` | Trigger the run and exit immediately. Use `poly test show <run_id>` to check results later. |
| `--push` | Push the project before running tests. Equivalent to running `poly push` then `poly test run`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Machine-readable JSON output. |

When `--dont-poll` is used, the CLI prints the run ID and a `poly test show` command to retrieve results:

~~~text
Use poly test show <run_id> to check the status of the test run.
~~~

### `poly test list`

List past test runs for the current project and branch.

~~~bash
poly test list
poly test list --limit 20
poly test list --offset 10
~~~

The table shows run ID, start time, status, total/passed/failed/error counts, and who triggered the run.

| Flag | Description |
|---|---|
| `--limit` | Number of runs to return. Defaults to `10`. |
| `--offset` | Number of runs to skip. Defaults to `0`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Machine-readable JSON output. |

### `poly test show`

Inspect a completed test run or drill into a single test case.

~~~bash
poly test show <run_id>
poly test show <run_id> <test_case_id>
~~~

`poly test show <run_id>` prints a summary of the run (status, counts, timestamps) followed by a table of all individual test results.

`poly test show <run_id> <test_case_id>` drills into a single test — showing assertion results, any function call failures, and the full conversation transcript turn-by-turn.

| Argument | Description |
|---|---|
| `run_id` | The test run ID. Required. |
| `test_case_id` | Optional. If supplied, shows detailed results for that specific test case. |

| Flag | Description |
|---|---|
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Machine-readable JSON output. |

## Test run statuses

The CLI handles the full set of Agent Studio test run and test case statuses:

| Status | Meaning |
|---|---|
| `pending` | Queued, not yet started |
| `in_progress` | Currently running |
| `passed` | All assertions passed |
| `failed` | One or more assertions failed |
| `errored` | The test encountered an error |
| `timed_out` | The test run exceeded the time limit |

After a run completes, `poly test run` prints a summary of failures (assertion reasons, function call failures, and conversation IDs) and exits with a non-zero status code when any test failed or errored.

## JSON output

All `poly test` subcommands support `--json` for machine-readable output.

| Command | Key fields |
|---|---|
| `poly test run --json` | `success`, `test_run` (triggered run details); with `--dry-run`: `test_count`, `tests` |
| `poly test list --json` | `success`, `test_runs` |
| `poly test show <run_id> --json` | `success`, `test_run` |
| `poly test show <run_id> <test_case_id> --json` | `success`, `test` |

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
- use `tags` consistently (`smoke`, `regression`, `<flow_name>`) so suites can be filtered with `--tag`
- cover error paths, not only success cases
- add a webchat and a voice variant of any critical path that runs on both channels
- validate as part of the normal edit loop, not just before merge
- combine the suite with `poly chat` and interactive review in Agent Studio when behavior depends on the full conversation flow

## Related pages

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    `poly validate`, `poly push`, `poly chat`, and `poly test` — the commands used in the test workflow.
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
