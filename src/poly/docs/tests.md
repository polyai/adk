# Tests

## Overview

Tests are simulated conversations used to validate agent behaviour in Agent Studio. Each test case defines a user scenario, the channel to run on, optional tags, and assertions that check the agent's response and function calls.

## Location

`test_suite/`. One file per test case: `test_suite/{test_name}.yaml`.

File names are cleaned to lowercase snake_case. For example, a test named `"Greeting flow test"` is stored as `test_suite/greeting_flow_test.yaml`.

## Structure

Each test case has these fields:

- **name** (string): Display name of the test. The filename is derived from this (cleaned to snake_case).
- **scenario** (string): The simulated user input that starts the conversation.
- **channel** (string): Channel to run on — `voice` or `webchat`.
- **tags** (list, optional): Labels for grouping and filtering tests.
- **variant** (string, optional): Variant name to run the test against.
- **language** (string): Language code for the test run, e.g. `en-GB`.
- **simulated_at** (string, optional): Test clock — the point in time the conversation is simulated at, as an ISO 8601 datetime (e.g. `2026-01-15T09:30:00Z`). Values are normalised to UTC. Omit it to run against the real clock.
- **caller_number** (string, optional): The number the simulated call arrives from.
- **sip_headers** (map, optional): SIP headers a carrier would send with an inbound call.
- **integration_attributes** (map, optional): Attributes a channel or connector passes in.
- **api_mocks** (map, optional): Mock responses for API integration operations, so the simulation runner returns these instead of calling the real API.
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

## Test clock

`simulated_at` pins the agent's notion of "now" for the simulated conversation, so time-dependent behaviour — out-of-hours routing, "tomorrow" date resolution, a seasonal greeting — can be tested deterministically instead of depending on when the suite happens to run.

```yaml
name: Out of hours test
scenario: Ask to speak to an agent.
channel: voice
language: en-GB
simulated_at: 2026-01-15T22:30:00Z
prompt_assertions:
- The agent explains the contact centre is closed
```

Values are parsed as ISO 8601 and normalised to UTC, so `2026-01-15T22:30:00+00:00` and `2026-01-15T23:30:00+01:00` both round-trip as `2026-01-15T22:30:00Z`. A value without an offset is treated as UTC. Removing the field and pushing clears the test clock on the platform.

## Mock call context

A real conversation arrives carrying more than the user's words: the number it came from, the SIP headers a carrier attached, the attributes a channel passed in. Three optional fields simulate that, so a flow that branches on any of it can be tested without placing a real call.

```yaml
name: VIP caller routing
scenario: Ask to speak to someone about my order.
channel: voice
language: en-GB
caller_number: "+447700900000"
sip_headers:
  x-dnis: "441234567890"
  x-call-id: abc-123
integration_attributes:
  tier: gold
  retry_count: 2
  vip: true
  account:
    region: uk
```

### caller_number

The number the call arrives from, always text. The agent reads it as `conv.caller_number`.

Leave it out to simulate a withheld or anonymous number — a real production case worth testing, so no format validation is applied beyond trimming surrounding whitespace.

**Quote it.** YAML reads an unquoted number as an integer *and drops a leading `+`*, so `+447700900000` and `447700900000` become the same value:

```yaml
caller_number: +447700900000     # becomes 447700900000 — the + is lost
caller_number: "+447700900000"   # correct
```

`push` rejects an unquoted number rather than converting it, because the two cases are indistinguishable once YAML has parsed them and silently sending a different number would make the test lie.

### sip_headers

Headers a carrier would send with an inbound call. The agent reads them as `conv.sip_headers`.

Header names are case-sensitive — match exactly what your telephony integration sends. Values are always text on the wire, so a YAML `true` is sent as `"true"` and a number as its digits. Quote anything you want preserved exactly.

Headers can be set on a `webchat` test, but a real webchat conversation never receives them, so the test covers a state production cannot reach.

### integration_attributes

Attributes a channel or connector passes in. The agent reads them as `conv.integration_attributes`.

Unlike SIP headers, these **keep their type** through to the agent, so a flow branching on `retry_count > 2` sees a number rather than the text `"2"`. Text, numbers, `true`/`false`, `null`, lists and nested maps are all supported.

Types come from YAML, which means quoting matters:

| YAML | Reaches the agent as |
|------|----------------------|
| `retry_count: 2` | number |
| `retry_count: "2"` | text |
| `vip: true` | boolean |
| `vip: "true"` | text |
| `expiry: "2026-08-12"` | text |

Dates must be quoted. An unquoted `expiry: 2026-08-12` is a YAML date, which the agent cannot receive, and `push` rejects it rather than guessing what you meant.

## API mocks

A flow that branches on an API integration's response — a booking that's available vs. full, a lookup that succeeds vs. errors — needs that response to be deterministic to test reliably. `api_mocks` intercepts calls to a named integration operation during simulation and returns the mocked response instead of calling the real API.

Mocks are keyed by integration name, then operation name, then a list of response rules tried in order:

```yaml
name: Slot negotiation retries once then succeeds
scenario: Book a table for 4 at 7pm.
channel: voice
language: en-GB
api_mocks:
  reservations_api:
    check_availability:
    - respond:
        status: 503
      repeat: 1
    - respond:
        status: 200
        body:
          available: true
          table_id: 42
        headers:
          content-type: application/json
prompt_assertions:
- The agent retries and confirms the booking
```

Each rule has:

- **respond**: The response to return.
  - **status**: HTTP status code (100–599).
  - **body** (optional): Response body. Keeps its type through to the flow, same rules as `integration_attributes` — quote dates, and only text, numbers, `true`/`false`, `null`, lists and nested maps are supported.
  - **headers** (optional): Response headers, always sent as text.
- **repeat** (optional): How many times to return this response before moving to the next rule in the list. Omit it to respond once. Set it to `-1` to respond with this rule forever — only valid on the last rule in a list. `0` and other negative values are rejected. Once a list's rules are exhausted (no trailing `-1` rule), further calls to that operation fall through to the real API.

The integration name must match an existing `api_integration` resource in the project; `push` rejects an unknown one. Operation names aren't cross-checked against the integration's configured operations at push time — instead, renaming or deleting the underlying operation automatically cascades to any mocks that reference it, the same way the platform handles the rest of the integration/operations relationship.

## Prompt assertions

Prompt assertions are natural-language descriptions of what the agent should do or say in response to the scenario. They are evaluated by the test runner against the simulated conversation.

- One assertion per expected behaviour.
- Keep assertions focused — check one thing per line where possible.

## Function call assertions

Function call assertions verify that the agent invoked a specific function with expected arguments.

Each function call assertion has:

- **name**: Function name - must be a valid global function in the project.
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

## Validation

On `push`, each test case is validated:

- **channel** must be `voice` or `webchat`.
- **scenario** is required (cannot be empty).
- **language** is required and must match a configured project language (default or additional).
- **variant**, if specified, must match an existing variant in the project.
- **function_call_assertions**: each function name must match a global function (`functions/`) or a flow function (`flows/<flow>/functions/`) in the project, and each argument's `value_type` must be one of `string`, `integer`, `number`, or `boolean`.
- **integration_attributes**: values must be text, numbers, `true`/`false`, `null`, lists or nested maps. An unquoted date is rejected with the quoted form to use instead, and keys must be text.
- **api_mocks**: the integration name must match an existing `api_integration` resource; each operation must have at least one response rule; each rule's `status` must be a valid HTTP status code (100–599); `body`, if set, follows the same type rules as `integration_attributes`; `repeat`, if set, must be a positive integer or `-1` (respond forever), and `-1` is only allowed on the last rule for an operation.

## Best practices

- Use tags like `smoke` or `regression` to group related tests.
- Write scenarios as realistic user utterances.
- Set mock call context only where the flow reads it. A test that carries headers no node inspects is noise.
- Combine prompt assertions (what the agent says) with function call assertions (what the agent does) for end-to-end coverage.
- Keep one test focused on one behaviour or flow path.
