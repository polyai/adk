---
title: Observability
description: Instrument an agent with logs and metrics so conversations can be understood after the fact, and inspect real calls with poly conversations.
---

# Observability

Once an agent is handling real calls, the question stops being "does this work?" and becomes "what happened on that call?" Answering it depends on having instrumented the agent beforehand — logs and metrics you added deliberately, rather than whatever happened to be printed.

## Logging

Use `conv.log` to record meaningful outcomes, not every step the code takes:

~~~python
conv.log.info("Booking confirmed", reference=booking_ref)
conv.log.warning("Availability API slow, using cached slots")
conv.log.error("Payment provider returned 500")
~~~

Good logging explains the *shape* of a call — which paths it took, which external calls succeeded, where it went wrong. Log around the things that can fail: API calls, validation, and any branch whose outcome you would want to explain later.

**Never swallow an external failure silently.** A bare `except` with no log turns a broken integration into a mysteriously unhelpful agent, and there is nothing in the transcript to explain it.

## Metrics

Metrics count things you want to aggregate across calls — how often a flow completes, how often a handoff fires, how often an API falls back.

The common mistake is emitting the same metric repeatedly. A metric written inside a loop, or on every turn, inflates the count and tells you nothing:

| Avoid | Prefer |
|---|---|
| Writing the same metric repeatedly in a loop | `write_once=True` when an event should be recorded once per conversation |
| Emitting a metric every turn without a clear reason | Emitting on the outcome you actually want to count |

See the [functions reference](../reference/resources/functions.md) for the `conv.log` and metrics APIs.

!!! tip "Instrument for the question you will ask later"

    The useful test is whether a log line or metric would help you answer a question you can imagine being asked — "how often do callers abandon at payment?", "did that transfer actually fire?" If it would not, it is noise.

## Inspecting real conversations

`poly conversations` reads what actually happened on real calls:

~~~bash
poly conversations list
poly conversations get <conversation_id>
poly conversations get-audio <conversation_id> -o recording.wav
~~~

`list` pages through recent conversations, `get` returns the full turn-by-turn detail, and `get-audio` downloads the recording for a voice call.

This is where you find out what callers actually say, as opposed to what you imagined they would. Treat it as an input to development rather than an end in itself — a surprising real conversation is the raw material for the next test case.

Agent Studio provides the aggregate view — containment, CSAT, handle time, and flagged transcripts — which the CLI does not.

## How this fits the workflow

Instrumentation is something you add while building, and it only pays off later. Logs and metrics you did not add are not available retroactively, so the time to think about them is while you are writing the function, not while you are debugging a call from last week.

- [Simulated conversation tests](./testing.md#simulated-conversation-tests) — turning a surprising real conversation into a repeatable test case
- [Environments and deployment](./environments-and-deployment.md) — which environment a conversation came from
- Every flag for these commands is in the [CLI reference](../reference/cli/conversations.md)
