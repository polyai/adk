---
title: Entities
description: Define structured data that the agent can collect and use during a conversation.
---

# Entities

<p class="lead">
Entities define structured data that the agent can collect from the user, such as a date of birth, phone number, or choice from a list.
</p>

Entities are used in flow steps to control what the agent should collect and what must be present before a condition can trigger. They can also be read in executed Python code.

## Location

Entities are defined in:

~~~text
config/entities.yaml
~~~

Entities are listed under the `entities` key.

## What an entity contains

Each entity has four main parts:

| Field | Description |
|---|---|
| `name` | Identifier for the entity, typically in snake_case. Used in prompts as `{{entity:entity_name}}`. |
| `description` | Explains what the entity represents. This is shown to the model to guide extraction. |
| `entity_type` | The type of entity being collected. |
| `config` | Type-specific settings for that entity. |

## Entity types

| Type | Config fields | Description |
|---|---|---|
| `numeric` | `has_decimal`, `has_range`, `min`, `max` | Numbers such as account numbers or quantities |
| `alphanumeric` | `enabled`, `validation_type`, `regular_expression` | Mixed text such as booking references |
| `enum` | `options` | A fixed set of choices |
| `date` | `relative_date` | Calendar dates |
| `phone_number` | `enabled`, `country_codes` | Phone numbers with country validation |
| `time` | `enabled`, `start_time`, `end_time` | Times or time ranges |
| `address` | `{}` | Physical addresses |
| `free_text` | `{}` | Unstructured text input |
| `name_config` | `{}` | Person names |

## How entities are used

<div class="grid cards" markdown>

-   **In flow prompts**

    ---

    Use `{{entity:entity_name}}` to reference a collected value.

-   **In function steps**

    ---

    Read values using `conv.entities.entity_name.value`.

-   **In default step conditions**

    ---

    Use `required_entities` to gate a condition until the listed entities have been collected.

-   **In default steps**

    ---

    Use `extracted_entities` to tell the agent which entities to collect in that step.

</div>

## In prompts

You can reference a collected entity value in prompts using:

~~~text
{{entity:entity_name}}
~~~

This allows a later step to reuse information that has already been collected.

## In code

In function steps or related Python code, entity values can be read like this:

~~~python
conv.entities.entity_name.value
~~~

Before reading a value, check that the entity exists:

~~~python
if conv.entities.entity_name:
    ...
~~~

## In flow conditions

Entities are important in default flow steps:

- `extracted_entities` tells the agent what to collect in the current step
- `required_entities` tells a condition what must already be available before it can trigger

This allows flows to wait until the necessary information has been gathered before progressing.

!!! info "Automatic ASR biasing"

    When entities are requested in a default step, ASR biasing is automatically configured based on the entity types being collected.

## Example

~~~yaml
entities:
  - name: date_of_birth
    description: The customer's date of birth
    entity_type: date
    config:
      relative_date: false

  - name: party_size
    description: Number of guests for the reservation
    entity_type: numeric
    config:
      has_decimal: false
      min: 1
      max: 20

  - name: meal_preference
    description: The customer's preferred meal type
    entity_type: enum
    config:
      options:
        - vegetarian
        - vegan
        - standard
        - halal
~~~

## Best practices

- use clear, descriptive snake_case names
- keep descriptions specific enough to guide extraction well
- choose the most precise entity type available
- use `required_entities` to control when a step condition is allowed to fire
- use `extracted_entities` to make collection explicit in default steps

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    Learn how entities fit into default steps, conditions, and step transitions.
    [Open flows](./flows.md)

-   **Variables**

    ---

    Compare collected entities with state variables used elsewhere in the project.
    [Open variables](./variables.md)

-   **Conversation object reference (platform)**

    ---

    Full reference for `conv.entities` — accessing collected values, checking presence, and entity object shape.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }

</div>