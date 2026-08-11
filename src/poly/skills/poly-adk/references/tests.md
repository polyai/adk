# Tests

## Overview
Tests are simulated conversations that validate agent behavior in Agent Studio. Each defines a user scenario, the
channel, optional tags, and assertions on the agent's response and function calls.

## Location
`test_suite/`, one file per test: `test_suite/{test_name}.yaml`. Filenames are cleaned to lowercase snake_case
(e.g. `"Greeting flow test"` → `test_suite/greeting_flow_test.yaml`).

## Structure
| Field | Notes |
|---|---|
| `name` (string) | Display name — filename is derived from this |
| `scenario` (string) | Simulated user input that starts the conversation |
| `channel` (string) | `voice` or `webchat` |
| `tags` (list, optional) | Labels for grouping/filtering |
| `variant` (string, optional) | Variant to run against |
| `language` (string) | Language code, e.g. `en-GB` |
| `prompt_assertions` (list, optional) | Expected agent behaviors |
| `function_call_assertions` (list, optional) | Expected function calls + arguments |

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
Natural-language descriptions of what the agent should do/say, evaluated against the simulated conversation. One
assertion per expected behavior; check one thing per line.

## Function call assertions
| Field | Notes |
|---|---|
| `name` | Must be a valid global function in the project |
| `arguments` | List of `{parameter_name, expected_value, value_type}` |
| `value_type` | `string`, `integer`, `number`, or `boolean` |

## Channels
| YAML value | Description |
|---|---|
| `voice` | Voice channel |
| `webchat` | Web chat channel |

## Naming and filenames
`name` can contain spaces/mixed case; filename must match its cleaned version or `pull`/`push` fails validation.

## Validation (on push)
- `channel` must be `voice` or `webchat`.
- `scenario` required, non-empty.
- `language` required and must match a configured project language (default or additional).
- `variant`, if set, must match an existing project variant.
- `function_call_assertions`: function name must match a global function; each `value_type` must be `string`,
  `integer`, `number`, or `boolean`.

## Best practices
- Tag with `smoke` / `regression` to group related tests.
- Write scenarios as realistic user utterances.
- Combine prompt assertions (what's said) with function call assertions (what's done) for end-to-end coverage.
- One test per behavior/flow path.
