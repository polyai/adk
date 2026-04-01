---
title: Common anti-patterns
description: Avoid common mistakes when building flows, writing prompts, and handling control flow in the PolyAI ADK.
---

This page collects common implementation mistakes that make agents harder to predict, harder to maintain, or more likely to behave incorrectly at runtime.

The general rule is simple: keep prompts focused on conversation, keep Python focused on deterministic logic, and make control flow explicit.

## Flow navigation

Flow functions must **always advance** the flow.

A flow function should never leave the agent sitting in the same logical place without a clear next step.

### Avoid

- returning from a flow function without changing step or flow
- leaving navigation implicit
- assuming the model will somehow recover the flow state on its own

### Prefer

- `flow.goto_step(...)`
- returning an explicit transition
- making the next state obvious in code

!!! danger "A stuck flow is usually a control-flow bug"

    If a flow function does not move the agent forward, the conversation can become stuck in an invalid or confusing state.

## Metrics and logging

Metrics and logs should capture important events, not generate noise.

### Avoid

- writing the same metric repeatedly in a loop
- emitting metrics every turn without a clear reason
- swallowing external API failures silently

### Prefer

- `write_once=True` when an event should only be recorded once
- logging meaningful outcomes around API calls and validation failures
- using `conv.log.info(...)`, `conv.log.warning(...)`, and `conv.log.error(...)` to make important behavior visible

!!! tip "Good logging explains the shape of the call"

    Logs and metrics should help you understand what happened in the conversation, not bury you in repetitive trivia.

## Logic in prompts vs code

Do not put deterministic branching logic into prompts or YAML instructions.

Prompts are for conversational behavior. Python is for comparisons, routing, validation, and state-driven decisions.

### Wrong

Encoding branching logic in prompts, for example:

~~~text
If $x == 0 do A, else do B.
~~~

### Right

Implement the check in Python and transition to the correct step or flow explicitly.

### Why this matters

When branching logic is buried in prompts:

- behavior becomes harder to test and verify
- routing becomes harder to debug
- deterministic behavior becomes dependent on how the model interprets the instruction

<div class="grid cards" markdown>

-   **Prompts**

    ---

    Use prompts for collecting information, presenting information, and guiding conversational style.

-   **Python**

    ---

    Use Python for comparisons, routing, validation, retries, and state-based decisions.

</div>

## “Anything else?” and exiting flows

Do not create a dedicated **“Anything else?”** step just to wrap up a flow.

When the flow is finished, exit the flow and return the appropriate closing prompt there.

### Avoid

- adding a special cleanup step whose only purpose is to ask whether the user needs anything else
- calling `conv.exit_flow()` and then also navigating somewhere else

### Wrong

~~~python
conv.exit_flow()
return {"transition": {"goto_flow": "Another Flow"}}
~~~

or

~~~python
conv.exit_flow()
conv.goto_flow("Another Flow")
~~~

In both cases, the navigation overrides the exit.

### Right

Use **one** of these approaches:

- exit the flow and return the closing content
- navigate to another step or flow

Do not do both.

!!! warning "Exit and navigation are mutually exclusive"

    If you call `conv.exit_flow()` and then also transition elsewhere, the transition wins.

## `end_turn=False`

`end_turn=False` is easy to misuse.

It should only be used when the agent speaks and then immediately performs another action in the **same turn**, without waiting for user input.

### Wrong

Using `end_turn: False` after the agent asks a question and is waiting for a reply.

That produces awkward control flow, because the question should simply be part of the normal utterance.

### Right

Use `end_turn: False` only when the agent must continue immediately, for example:

- the agent says something
- then immediately calls a function in the same turn

Example pattern:

~~~text
“Your balance is X.”
→ immediately call `balance_informed`
~~~

If the user is expected to answer, put the full question in the utterance and let the turn end normally.

## Quick reference

| Anti-pattern | Better approach |
|---|---|
| Flow function returns without navigation | Always call `flow.goto_step(...)` or return a transition |
| Metric written repeatedly in a loop | Use `write_once=True` where appropriate |
| Branching logic in prompts | Put routing logic in Python |
| Dedicated “Anything else?” step | Exit the flow and return the closing prompt directly |
| `conv.exit_flow()` plus navigation | Choose exit **or** transition, not both |
| `end_turn=False` while waiting for a user answer | Only use it when the agent continues immediately in the same turn |

## Design principle

- make control flow explicit
- keep prompts conversational
- keep code deterministic
- prefer simple, testable paths over clever prompt tricks
  
