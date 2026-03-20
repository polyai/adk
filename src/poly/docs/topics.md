# Topics

## Overview

Topics are the agent's knowledge base, queried via RAG (retrieval-augmented generation). When a user's input matches a topic, the agent retrieves the topic's content and follows its actions.

## Location

`topics/`. One file per topic: `topics/{Topic Name}.yaml`.

## Structure

Each topic has four fields:

- **enabled** (bool): Whether the topic is active. Default: `true`.
- **example_queries**: List of example user inputs that should trigger this topic.
- **content**: Factual information retrieved via RAG. No function calls or `$variables` allowed here.
- **actions**: Behavioral instructions for the agent when the topic is triggered. This is where you use references.

## Example
```yaml
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
```

## Example queries
- Maximum **20 queries**.
- Cover different ways a user might ask about the same thing.
- Don't try to cover every minor variation — the model generalizes.

## Content
- Factual information only. This is what gets retrieved via RAG.
- **No** `{{fn:...}}`, `{{ft:...}}`, `$variable`, or `{{attr:...}}` references in content.
- Use multi-line (`|-`) for longer content.

## Actions
- Behavioral instructions: what to say, when to call functions, how to branch.
- **This is the only place** where you can use references in a topic:
  - `{{fn:function_name}}` — call a global function
  - `{{fn:function_name}}('arg')` — call with an argument
  - `{{attr:attribute_name}}` — variant attribute
  - `{{twilio_sms:template_name}}` — SMS template
  - `{{ho:handoff_name}}` — handoff
  - `$variable` — state variable
- **Branching**: Use markdown headers (`##`, `###`) for conditional sections.
- Keep actions clear and scannable; avoid one long paragraph with mixed conditions.

## Best practices
- Don't prompt the model to `"Say: '...'"` (hurts multilingual support); use `"Tell the user that ..."`.
- Prefer structured actions with `## Conditional Branch` sections over a single dense paragraph.
- Keep content and actions separate — content is facts, actions is behavior.
- One topic per subject area. If a topic is getting too large, split it.
- Disable topics with `enabled: false` rather than deleting them during development.
