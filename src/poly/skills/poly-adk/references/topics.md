# Topics

## Overview
Topics are the agent's knowledge base, queried via RAG. When user input matches a topic, the agent retrieves its
content and follows its actions.

## Location
`topics/`, one file per topic: `topics/{topic_name}.yaml`. Filenames are cleaned to lowercase snake_case (e.g.
`"Opening Hours & Locations"` → `topics/opening_hours_locations.yaml`).

## Structure
| Field | Notes |
|---|---|
| `name` (string) | Canonical display name — filename is derived from this |
| `enabled` (bool) | Default `true` |
| `example_queries` | List of example user inputs that should trigger this topic |
| `content` | Factual info retrieved via RAG — **no** function calls or variable references |
| `actions` | Behavioral instructions when triggered — references allowed here |

```yaml
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
```

## Naming and filenames
- `name` can contain spaces, punctuation, mixed case.
- The filename must match the cleaned (lowercase snake_case) version of `name` — mismatch raises a validation
  error on `pull`/`push`.

## Example queries
- Max **20**.
- Cover different phrasings of the same underlying question.
- Don't try to cover every minor variation — the model generalizes.

## Content
- Facts only — this is what's retrieved via RAG.
- **No** `{{fn:...}}`, `{{ft:...}}`, `$variable`, or `{{attr:...}}` references.
- Use `|-` for multi-line content.

## Actions
References allowed **only here**, not in `content` or `example_queries`:
- `{{fn:function_name}}` / `{{fn:function_name}}('arg')` — call a global function, with/without an argument
- `{{attr:attribute_name}}` — variant attribute
- `{{twilio_sms:template_name}}` — SMS template
- `{{ho:handoff_name}}` — handoff
- `$variable` — state variable

Use markdown headers (`##`, `###`) for conditional branches; keep actions scannable rather than one dense
paragraph.

## Best practices
- Don't prompt `"Say: '...'"` — hurts multilingual support; use `"Tell the user that ..."` instead.
- Prefer structured `## Conditional Branch` sections over one dense paragraph.
- Keep content (facts) and actions (behavior) separate.
- One topic per subject area — split when a topic gets too large.
- Disable with `enabled: false` rather than deleting during development.
