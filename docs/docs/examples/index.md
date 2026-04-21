---
title: Examples
description: Focused examples for common PolyAI ADK patterns and workflows.
---

This section contains small, focused examples that can be copied, adapted, and reused when building with the **PolyAI ADK**.

Examples are intended to show practical patterns rather than explain every concept in depth.

## What examples are for

Use examples when you want to:

- see a pattern in a compact form
- copy a starting point into a project
- compare one implementation approach with another
- understand how a resource is typically structured

Examples work best alongside the conceptual and reference documentation.

<div class="grid cards" markdown>

-   **Concepts**

    ---

    Learn how a feature or workflow works before applying it.
    [Open core concepts](../concepts/working-locally.md)

-   **Reference**

    ---

    Look up the exact fields, structures, and command behavior.
    [Open CLI reference](../reference/cli.md)

-   **Tutorials**

    ---

    Follow a complete workflow from start to finish.
    [Open tutorials](../tutorials/build-an-agent.md)

</div>

## Available examples

<div class="grid cards" markdown>

-   **Confirm caller ID before sending SMS**

    ---

    Stash `caller_number` at call start, confirm the last four digits, then send an SMS — or ask if the number is not available.
    [Open example](./confirm-caller-id-before-sms.md)

-   **Venue-specific goodbye with clean hangup**

    ---

    Return a location-specific closing utterance from a function and hang up without the LLM adding its own filler first.
    [Open example](./venue-specific-goodbye.md)

-   **SMS link with transfer fallback**

    ---

    Offer an SMS link and transfer to a live agent if the caller prefers — with per-environment sender number support.
    [Open example](./sms-or-transfer-fallback.md)

</div>

!!! info "Examples are intentionally small"

    A good example should be easy to scan, easy to copy, and easy to adapt. Larger workflows belong in tutorials.

## Suggested next step

If you are looking for a full end-to-end workflow, start with the tutorial instead.

<div class="grid cards" markdown>

-   **Build an agent with the ADK**

    ---

    Follow the main tutorial for the complete workflow from setup to deployment.
    [Open the tutorial](../tutorials/build-an-agent.md)

</div>