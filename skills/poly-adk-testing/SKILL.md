---
name: poly-adk-testing
description: >
  This skill should be used when the user wants to "test the agent", "chat with the agent",
  "run the test suite", "write a test case", "check why a test failed", or "run a function"
  built with the PolyAI ADK. Covers poly validate, scripted poly chat, the test_suite/
  simulated conversation tests, and executing functions in isolation. Part of the PolyAI
  ADK skills suite. Do NOT use for inspecting real production calls (use
  poly-adk-conversations) or the general build workflow (use poly-adk-workflow).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.53.1
  requires:
    bins:
      - poly
    install: "uv tool install polyai-adk"
---

# Testing a PolyAI Agent

Load `poly-adk-workflow` first for the overall build loop these commands fit into.

Four layers of verification, catching different problems:

| Command | Catches | Runs against |
|---|---|---|
| `poly validate` | Invalid resources, missing values, broken references | Local files |
| `poly chat` | Conversational behavior, judged by reading | Last **pushed** state |
| `poly test run` | Regressions, repeatably | Last **pushed** state |
| `poly conversations` | What happened on real calls (see `poly-adk-conversations`) | Live traffic |

**`poly chat` and `poly test run` run against the last pushed state, not local files.** Push first, or pass `--push` to push-and-run in one step. Both target the current branch by default; `-e sandbox|pre-release|live` targets a deployed environment instead.

## 1. Validate while editing

`poly validate` checks local files without contacting the platform — malformed resources, missing required values, and `{{prefix:name}}` references that don't resolve. Run it as you edit, not just before pushing; `poly push` runs the same validation and rejects anything validate rejects.

## 2. Chat with the agent

As an agent, always use the non-interactive modes:

```bash
poly chat --push -m 'Hello' -m 'I want to book a table' --json
poly chat --input-file ./script.txt          # one message per line; - for stdin
poly chat --metadata                          # show function calls, active flow/step, and state changes per turn
poly chat --conv-id <id> -m 'Follow-up'       # resume an existing conversation
```

Useful flags for reproducing specific situations:

- `--channel voice|webchat` — which channel's settings apply (default `voice`)
- `--sip-header X-Customer-ID=12345` — simulate SIP headers, exposed to project functions via `conv.sip_headers` (repeatable; test-only, no real SIP call)
- `--variant <name>` — chat as a specific variant
- `--lang` / `--input-lang` / `--output-lang` — multilingual agents

With `--json`, output is a `conversations` array with per-turn detail mirroring the `--functions`/`--flows`/`--state` flags you enabled.

Chat is for judging whether a conversation *feels* right. Anything worth checking twice belongs in the test suite instead.

## 3. Simulated conversation tests

Test cases live in `test_suite/` and assert what the agent should say and which functions it should call. They are the only repeatable layer — the thing that stops a fixed bug coming back. Run `poly docs tests` for the file format and available assertions before writing cases.

```bash
poly test run                    # all tests, polls until complete, non-zero exit on failure
poly test run --tag smoke        # only tagged tests (multiple tags OR-match)
poly test run --files test_suite/greeting_flow_test.yaml
poly test run --dry-run          # preview which tests would run
poly test run --dont-poll        # trigger and exit; check later with poly test show
poly test list                   # past runs
poly test show <run_id>                    # run summary + per-test table
poly test show <run_id> <test_case_id>     # assertion results, function failures, full transcript
```

Statuses: `pending`, `in_progress`, `passed`, `failed` (assertion failed), `errored`, `timed_out`. After a run, failures are summarized with assertion reasons and conversation IDs.

Write cases for the paths that are tedious to reach by hand — an unavailable API, a caller changing their mind, variant-specific behavior. For the API case, `api_mocks` forces a named API integration operation to return a fixed response so the test is deterministic (see `poly docs tests`).

## 4. Execute a function in isolation

To debug one function without a conversation:

```bash
poly functions execute <function_name> --args '{"x": 1}' --json   # returns body, logs, runtime
poly functions validate                                            # syntax errors + orphaned flow-step references
```

Limitations: builds a fresh `conv` from the branch config — no live caller, `conv.state` starts empty and is not persisted, and `conv.say`/`conv.goto_flow`/`conv.call_handoff` have no channel to act on. Covers global functions only, not flow transition functions or function steps. There is no way to attach to a real call.

Both subcommands accept `--region --project_id --branch_id` (all three together) to run headlessly without a local checkout.

## Where each layer fits

Validation and chat belong in the edit loop; the test suite belongs before merging; and after promoting to an environment, re-run chat and tests against it with `-e`. A surprising real conversation found via `poly-adk-conversations` is the raw material for the next test case.
