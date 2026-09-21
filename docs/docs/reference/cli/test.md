---
title: poly test
description: Reference for the `poly test` command.
---

# `poly test`

The `poly test` command group covers the full testing lifecycle.

## `poly test run`

Trigger a test run against the current branch. Runs all tests by default.

Examples:

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

When `--dont-poll` is used, the CLI prints the run ID and a `poly test show` command to retrieve results:

~~~text
Use poly test show <run_id> to check the status of the test run.
~~~

`--json` output shape:

~~~json
{
  "success": true,
  "test_run": { "id": "...", "test_case_count": 12, "...": "..." }
}
~~~

With `--dry-run --json`, the shape is different — no run is triggered:

~~~json
{
  "success": true,
  "test_count": 12,
  "tests": [{ "resource_id": "...", "name": "..." }]
}
~~~

!!! info "`--push` on `--json` output"

    `--push --json` adds a `"push": {"success": true, "message": "..."}` key to the output before the run is triggered. If the push fails, that key is printed alone (with `"success": false` and an `"error"` key) and the command exits non-zero without triggering a run.

## `poly test list`

List past test runs for the current project and branch.

Examples:

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

`--json` output shape:

~~~json
{
  "success": true,
  "test_runs": { "testRuns": [{ "id": "...", "status": "...", "...": "..." }] }
}
~~~

## `poly test show`

Inspect a completed test run or drill into a single test case.

Examples:

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

`--json` output shape (run-level, no `test_case_id`):

~~~json
{
  "success": true,
  "test_run": { "id": "...", "status": "...", "testHistory": [] }
}
~~~

`--json` output shape (with `test_case_id`):

~~~json
{
  "success": true,
  "test": { "testCaseId": "...", "status": "...", "results": {} }
}
~~~


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

For the `test_suite/` file format, assertions, and worked examples, see the [tests reference](../resources/tests.md).

## Related pages

- [Testing](../../development/testing.md) — how `poly test run` fits alongside `poly validate` and `poly chat` in the development loop
