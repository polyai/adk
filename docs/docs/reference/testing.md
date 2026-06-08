---
title: Testing
description: Validate and test project changes when working with the PolyAI ADK.
---

# Testing

<p class="lead">
The ADK supports two complementary approaches to testing: local code validation and unit tests, and Agent Studio simulated conversation test cases that run against your agent in the sandbox.
</p>

## Agent Studio test cases

Agent Studio supports simulated conversation tests that run your agent end-to-end in the sandbox environment. These test cases are managed locally as YAML files under `test_suite/` and pushed to Agent Studio with `poly push`.

See the [Tests reference](./tests.md) for the full documentation on writing, structuring, and validating Agent Studio test cases.

## Local validation and manual testing

!!! warning "There is no local runtime"
    The ADK does not execute your agent on your local machine. There is no `poly serve` command or local simulator. All agent execution happens inside Agent Studio's sandbox environment. To test runtime behavior, push your changes and use `poly chat`, or test interactively through Agent Studio.

In the ADK workflow, local testing usually sits alongside validation and manual review in Agent Studio.

### What local testing is for

Local testing is useful when you want to:

- check that code changes behave as expected
- catch regressions before pushing
- validate function logic outside the runtime conversation loop
- support safer review and collaboration

<div class="grid cards" markdown>

-   **Validation**

    ---

    Use `poly validate` to check project configuration before pushing.

-   **Runtime review**

    ---

    Use Agent Studio and `poly chat` to test behavior interactively.

</div>

### Testing in the workflow

Testing sits between validation and merge in the standard [CLI workflow](./cli.md#working-pattern). Edit locally, validate with `poly validate`, push, then test the branch in Agent Studio or with `poly chat`.

### What to test locally

- function logic and return values
- state transitions across turns
- API integration helpers
- formatting or normalization utilities
- project-specific edge cases

### Best practices

- validate as part of the normal workflow, not just before merge
- test important error paths, not only success cases
- combine `poly chat` with interactive review when behavior depends on conversation flow
- use Agent Studio test cases for repeatable end-to-end scenario coverage

## Related pages

<div class="grid cards" markdown>

-   **Tests**

    ---

    Write and manage Agent Studio simulated conversation test cases.
    [Open tests reference](./tests.md)

-   **CLI reference**

    ---

    See the commands used during the local development workflow.
    [Open CLI reference](./cli.md)

-   **Build an agent**

    ---

    See how testing fits into the end-to-end workflow.
    [Open build an agent](../tutorials/build-an-agent.md)

</div>
