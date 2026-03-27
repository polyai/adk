---
title: Testing
description: Run tests and validate project changes when working with the PolyAI ADK.
---

# Testing

<p class="lead">
Testing helps confirm that your project changes behave as expected before they are pushed, reviewed, or merged.
</p>

In the ADK workflow, testing usually sits alongside validation and manual review in Agent Studio.

## Run the test suite

Run tests with:

~~~bash
pytest
~~~

Test files are located in:

~~~text
src/poly/tests/
~~~

## What testing is for

Testing is useful when you want to:

- check that code changes behave as expected
- catch regressions before pushing
- validate function logic outside the runtime conversation loop
- support safer review and collaboration

<div class="grid cards" markdown>

-   **Automated tests**

    ---

    Use `pytest` to run the project's test suite locally.

-   **Validation**

    ---

    Use `poly validate` to check project configuration before pushing.

-   **Runtime review**

    ---

    Use Agent Studio and `poly chat` to test behavior interactively.

</div>

## Testing in the workflow

A typical development loop looks like this:

1. edit files locally
2. inspect changes with `poly status` and `poly diff`
3. run `poly validate`
4. run `pytest` where relevant
5. push changes with `poly push`
6. test the branch in Agent Studio

!!! tip "Validation and testing are complementary"

    `poly validate` checks configuration correctness. `pytest` checks code behavior. They solve different problems and are both useful.

## What to test

The exact tests will depend on the kind of work you are doing, but common areas include:

- function logic
- state transitions
- API integration helpers
- formatting or normalization utilities
- project-specific edge cases

## Best practices

- run tests before pushing substantial changes
- keep tests focused and readable
- use validation as part of the normal workflow, not just before merge
- test important error paths, not only success cases
- combine automated testing with interactive review when behavior depends on conversation flow

## Related pages

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    See the commands used during the local development workflow.
    [Open CLI reference](./cli.md)

-   **Build an agent**

    ---

    See how testing fits into the end-to-end workflow.
    [Open build an agent](../tutorials/build-an-agent.md)

</div>