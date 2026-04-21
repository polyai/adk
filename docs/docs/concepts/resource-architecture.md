---
title: Resource architecture
description: A decision guide for choosing where to put content and logic when building with the PolyAI ADK.
---

# Resource architecture

<p class="lead">
Each resource type in the ADK has a specific purpose. This page helps you decide where to put new content or logic before you write it.
</p>

Choosing the wrong resource type is one of the most common sources of hard-to-debug agent behavior. The right question is not "how do I add this?" but "what kind of thing is this?"

## The core split

The ADK separates two concerns:

<div class="grid cards" markdown>

-   **Knowledge and facts**

    ---

    Information the agent should retrieve and communicate. Lives in topics.

-   **Behavior and logic**

    ---

    What the agent should do, when, and how. Lives in rules, flows, and functions.

</div>

Keep these separate. Mixing factual content and behavioral instructions in the same resource makes both harder to maintain and harder to reason about.

## Decision table

| You are adding... | Use |
|---|---|
| A new FAQ, policy, or factual answer | Topic (`topics/`) |
| A global behavioral rule (always do X, never do Y) | `agent_settings/rules.txt` |
| Structured data collection from the caller | Entity + flow |
| Deterministic branching or routing logic | Function (`functions/`) |
| Call initialization — routing, variant selection, reading SIP headers | `functions/start_function.py` |
| A multi-step guided conversation | Flow (`flows/`) |
| Reusable SMS message content | SMS template (`sms/`) |
| Per-site or per-location configuration | Variant (`variants/`) |
| Agent identity and tone | `agent_settings/personality.yaml` and `role.yaml` |

## Rules vs topics vs functions

These three resources overlap in ways that create confusion.

**`rules.txt`** is for durable, global behavioral instructions that apply on every turn — for example, "always confirm the booking reference before making changes" or "do not discuss competitor products." Rules are not retrieved via RAG; they are always present in the prompt.

**Topics** are for subject-specific knowledge that should only appear when relevant. The agent retrieves the right topic when the caller asks about that subject. Put factual content and the behavioral instructions for that specific subject area in the topic, not in rules.

**Functions** are for anything that requires a deterministic outcome — checking a value, calling an API, routing to a different flow, or making a decision that must not be left to the model.

!!! tip "A useful test"

    If the instruction is always true, it belongs in rules. If it is only relevant when someone asks about a specific subject, it belongs in a topic. If it requires a comparison, calculation, or API call, it belongs in a function.

## Common mistakes

### Putting behavioral logic in topic content

The `content` field of a topic is retrieved by RAG and made available as context. It should contain facts, not instructions.

~~~yaml
# Wrong — behavioral logic in content
content: |-
  If the caller asks to cancel, transfer them to the cancellations queue.

# Right — behavioral logic in actions
actions: |-
  If the caller asks to cancel, use {{ho:cancellations}} to transfer them.
~~~

### Putting facts in rules

`rules.txt` is not a good place for factual content because it is always present in the prompt, consuming context space even when the information is not relevant to the current turn. Keep facts in topics where they are only retrieved when needed.

### Writing prose conditionals in rules or topics

Logic like "if `{{vrbl:caller_number}}` is available, do X; otherwise do Y" is unreliable when the variable is empty. The model cannot reliably detect an empty variable from prompt text alone. Write the branch in Python instead.

See [checking variable presence in prose](./anti-patterns.md#checking-variable-presence-in-prose) for details.

## Where `start_function` fits

`start_function.py` runs once at call start, before the first user input. It is the right place for:

- reading SIP headers and setting variant routing
- initializing state variables the rest of the conversation depends on
- making a fast API call to preload caller context

It is **not** the right place for logic that only applies mid-conversation, or for slow API calls that would delay the greeting.

## Related pages

<div class="grid cards" markdown>

-   **Anti-patterns**

    ---

    Common mistakes to avoid when building flows, writing prompts, and handling control flow.
    [Open anti-patterns](./anti-patterns.md)

-   **Topics**

    ---

    Full reference for topic structure, content, and actions.
    [Open topics](../reference/topics.md)

-   **Agent settings**

    ---

    Personality, role, and rules — the global prompt layer.
    [Open agent settings](../reference/agent_settings.md)

-   **Functions**

    ---

    Python functions for deterministic logic and lifecycle hooks.
    [Open functions](../reference/functions.md)

-   **Managed Topics (platform)**

    ---

    How topics are retrieved, ranked, and used by the platform — including RAG mechanics and topic types.
    [Open Managed Topics overview](https://docs.poly.ai/managed-topics/introduction)

-   **Start function (platform)**

    ---

    Lifecycle hook reference — when it runs, what it can read, and common initialization patterns.
    [Open start function reference](https://docs.poly.ai/tools/start-function)

-   **Connected Knowledge (platform)**

    ---

    Alternative to Managed Topics for large, unstructured content sets — help articles, PDFs, FAQs.
    [Open Connected Knowledge](https://docs.poly.ai/connected-knowledge/introduction)

-   **Variant management (platform)**

    ---

    Per-site configuration using variant attributes — how routing and attribute lookup work.
    [Open variant management](https://docs.poly.ai/variant-management/introduction)

</div>
