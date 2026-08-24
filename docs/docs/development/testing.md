---
title: Testing
description: The ways to verify an agent with the PolyAI ADK — validation, interactive chat, simulated conversation tests, and inspecting real conversations.
---

# Testing

There are four ways to check an agent, and they catch different kinds of problem. Most of the time you want more than one.

| Approach | Catches | Runs against |
|---|---|---|
| `poly validate` | Structural mistakes — invalid resources, missing values, broken references | Local files |
| `poly chat` | Conversational behavior you need to judge by reading | A deployed branch or environment |
| `poly test run` | Regressions, repeatably | A deployed branch or environment |
| `poly conversations` | What actually happened on real calls | Live traffic |

## Validate before anything else

`poly validate` checks the project on disk without contacting the platform. It is the fastest feedback you can get, and it catches the errors that would otherwise block a push — malformed resources, missing required values, and references that point at something that does not exist.

Run it while you edit, not just before pushing. `poly push` runs the same validation, so anything validate rejects would have stopped the push anyway.

## Chat with the agent

`poly chat` opens an interactive session. Use it when the question is "does this conversation feel right?" — a judgement you have to make by reading, not something an assertion can capture.

Chat runs against the **last pushed state**, not your working directory, so push before you chat or pass `--push` to do both. By default it targets your current branch; you can point it at a deployed environment instead.

This is the right tool for exploring a change and the wrong tool for confirming it stays working. Anything you find worth checking twice should become a test case.

## Simulated conversation tests

Test cases live in `test_suite/` and describe a conversation along with assertions about what the agent should say and which functions it should call. They are the only approach here that is repeatable, so they are what stops a fixed bug coming back.

~~~bash
poly test run
poly test list
poly test show <run_id>
~~~

Like `poly chat`, tests run against the last pushed state rather than your local files.

For the test-case format, the available assertions, and worked examples, see the [tests reference](../reference/resources/tests.md). For every `poly test` flag, see the [CLI reference](../reference/cli/test.md).

!!! tip "Cover the paths you cannot easily reach by hand"

    Interactive chat is good at the common path and bad at the awkward ones — an unavailable API, a caller who changes their mind, a variant that only applies to one site. Those are worth encoding as test cases precisely because reaching them manually is tedious.


## How this fits the workflow

Validation and chat belong in the edit loop, tests belong before you merge, and conversation inspection happens after release and feeds back into the next change.

Deployed environments matter here too — you can chat against and run tests against `sandbox`, `pre-release`, or `live`, so a change can be verified again after each promotion. See [environments and deployment](./environments-and-deployment.md).

Every flag for these commands is in the [CLI reference](../reference/cli.md).
