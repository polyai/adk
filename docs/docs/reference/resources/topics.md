---
title: Topics
description: Define knowledge-base topics that the agent can retrieve and act on through RAG.
---

# Topics

<p class="lead">
Topics are the agent's knowledge base. They are queried through retrieval-augmented generation (RAG), and when a user's input matches a topic, the agent retrieves its content and follows its actions.
</p>

Topics are how you teach the agent facts and guidance about specific subject areas without putting everything into flows or rules.

## Location

Topics live in the `topics/` directory.

Each topic is stored as its own YAML file:

~~~text
topics/{Topic Name}.yaml
~~~

The filename is derived from the topic's `name` field, cleaned to lowercase snake_case — a topic named `Opening Hours & Locations` is stored as `topics/opening_hours_locations.yaml`.

## What a topic contains

Each topic has five main fields:

| Field | Description |
|---|---|
| `name` | The display name of the topic. This is the canonical name — the filename is derived from it. Can contain spaces, punctuation, and mixed case. |
| `enabled` | Whether the topic is active. Default: `true`. |
| `example_queries` | Example user inputs that should retrieve the topic. |
| `content` | Factual information retrieved by RAG. |
| `actions` | Behavioral instructions the agent should follow when the topic is matched. |

## Example

~~~yaml
name: Opening Hours & Locations
enabled: true
example_queries:
  - What are your opening hours?
  - When are you open?
  - Are you open on weekends?
  - What time do you close?
content: |-
  The office is open Monday to Friday from 9am to 5pm.
  Weekend hours are Saturday 10am to 2pm. Closed on Sundays.
actions: |-
  Tell the user the opening hours from the content above.

  ## If the user asks about a specific location
  Check the location using {{attr:office_location}} and provide the hours for that location.

  ## If the user wants to speak to someone
  Use {{fn:transfer_to_agent}} to connect them with a representative.
~~~

## How topics work

A topic combines two kinds of information:

<div class="grid cards" markdown>

-   **Content**

    ---

    The factual material that the agent retrieves through RAG.

-   **Actions**

    ---

    The behavioral instructions that tell the agent what to do with that content.

</div>

This split is important: content is for facts, actions are for behavior.

## Example queries

`example_queries` help the system understand when a topic should be retrieved.

### Good example queries should:

- cover different ways a user might ask about the same subject
- reflect realistic user phrasing
- stay focused on one subject area

### Limits and guidance

- use no more than **20** example queries
- cover meaningful variation, not every minor wording change

## Content

The `content` field contains factual information only.

This is the material that gets retrieved via RAG and made available to the agent when the topic is matched.

### Content rules

- keep it factual
- do not trigger behavior from content — no [`{{fn:...}}`](./functions.md)/[`{{ft:...}}`](./functions.md) function calls, no [`{{twilio_sms:...}}`](./sms.md) sends, no [`{{ho:...}}`](./handoffs.md) handoffs
- references to factual resources are fine — [`{{attr:...}}`](./variants.md), [`{{tn:...}}`](./translations.md), and [`{{vrbl:...}}`/`$variable`](./variables.md) just substitute a value, so they're safe to use in content
- use multi-line YAML (`|-`) for longer content

## Actions

The `actions` field tells the agent how to behave when the topic is matched.

This is the only place inside a topic where you should use references and behavior-oriented instructions.

### Supported references in actions

| Syntax | Meaning |
|---|---|
| `{{fn:function_name}}` | Call a [global function](./functions.md) |
| `{{fn:function_name}}('arg')` | Call a [global function](./functions.md) with an argument |
| `{{attr:attribute_name}}` | Read a [variant attribute](./variants.md) |
| `{{twilio_sms:template_name}}` | Reference an [SMS template](./sms.md) |
| `{{ho:handoff_name}}` | Reference a [handoff](./handoffs.md) |
| `{{tn:translation_key}}` | Reference a [translation](./translations.md) |
| `$variable` | Reference a [state variable](./variables.md) |

### Writing good actions

Actions should be:

- clear
- scannable
- structured
- behavior-oriented

Use markdown headers like `##` and `###` to break up branches or conditions.

### Prefer

- structured conditional sections
- plain instructions like “Tell the user that...”
- clear points where a function should be called

### Avoid

- dense paragraphs mixing facts and behavior
- `"Say: '...'"` phrasing
- putting factual content into actions

## Validation

- The filename must match the cleaned version of `name` — a mismatch raises a validation error on `pull` or `push`.

## Best practices

- keep content and actions separate
- use one topic per subject area
- split large topics when they become too broad
- prefer structured `##` branches in actions
- disable topics with `enabled: false` during development instead of deleting them

!!! tip "Tell, don't script"

    Prefer instructions like "Tell the user that ..." over hard-coded dialog such as `Say: '...'`. This lets the agent vary phrasing naturally, especially across languages.

## Related pages

<div class="grid cards" markdown>

-   **Functions**

    ---

    Learn how global functions referenced in topic actions are defined.
    [Open functions](./functions.md)

-   **Flows**

    ---

    See how topics hand off to structured processes using `conv.goto_flow`.
    [Open flows](./flows.md)

-   **Variants**

    ---

    See how variant attributes can be referenced from topic actions.
    [Open variants](./variants.md)

-   **Managed Topics (platform)**

    ---

    How topics are retrieved, ranked, and injected — RAG mechanics, topic types, and retrieval tuning.
    [Open Managed Topics overview](https://docs.poly.ai/managed-topics/introduction){ target="_blank" rel="noopener" }

</div>
