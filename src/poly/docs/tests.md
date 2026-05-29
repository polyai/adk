# Tests

## Overview

Tests are simulated conversations used to validate agent behaviour in Agent Studio. Each test case defines a user scenario, the channel to run on, optional tags, and assertions that check the agent's response and function calls.

## Location

`tests/`. One file per test case: `tests/{test_name}.yaml`.

File names are cleaned to lowercase snake_case. For example, a test named `"Greeting flow test"` is stored as `tests/greeting_flow_test.yaml`.

## Structure

Each test case has these fields:

- **name** (string): Display name of the test. The filename is derived from this (cleaned to snake_case).
- **scenario** (string): The simulated user input that starts the conversation.
- **channel** (string): Channel to run on — `voice` or `webchat`.
- **tags** (list, optional): Labels for grouping and filtering tests.
- **variant** (string, optional): Variant name to run the test against.
- **language** (string, optional): Language code for the test run, e.g. `en-GB`.
- **prompt_assertions** (list, optional): Expected behaviours in the agent's response.
- **function_call_assertions** (list, optional): Expected function calls and argument values.

## Example

```yaml
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
- name: test_function
  arguments:
  - parameter_name: param1
    expected_value: hello
    value_type: string
```

## Prompt assertions

Prompt assertions are natural-language descriptions of what the agent should do or say in response to the scenario. They are evaluated by the test runner against the simulated conversation.

- One assertion per expected behaviour.
- Keep assertions focused — check one thing per line where possible.

## Function call assertions

Function call assertions verify that the agent invoked a specific function with expected arguments.

Each function call assertion has:

- **name**: Function name (global function name, not resource ID).
- **arguments**: List of parameter assertions, each with:
  - **parameter_name**: Function parameter to check.
  - **expected_value**: Expected value for that parameter.
  - **value_type**: Type of the value — `string`, `integer`, `number`, or `boolean`.

## Channels

| YAML value | Description |
|------------|-------------|
| `voice` | Voice channel |
| `webchat` | Web chat channel |

## Naming and filenames

- The `name` field is the canonical test name and can contain spaces and mixed case.
- The filename must match the cleaned version of `name` — a mismatch raises a validation error on `pull` or `push`.

## Best practices

- Use tags like `smoke` or `regression` to group related tests.
- Write scenarios as realistic user utterances.
- Combine prompt assertions (what the agent says) with function call assertions (what the agent does) for end-to-end coverage.
- Keep one test focused on one behaviour or flow path.
