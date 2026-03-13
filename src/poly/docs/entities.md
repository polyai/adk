# Entities

## Purpose

Entities define structured data the agent can collect from the user (e.g. date of birth, phone number, choice from a list). They are used in flow steps via `extracted_entities` (what to collect) and `required_entities` (what must be collected before a condition can trigger).
They can also be referenced in executed python code.

## Location

`config/entities.yaml`. Entities are listed under the `entities` key.

## Structure

Each entity has:
- **name**: Identifier (snake_case). Used in prompts as `{{entity:entity_name}}`.
- **description**: What the entity represents (shown to the LLM to guide extraction).
- **entity_type**: One of the types below.
- **config**: Type-specific settings.

## Entity types and config

| Type | Config fields | Description |
|------|---------------|-------------|
| **numeric** | `has_decimal`, `has_range`, `min`, `max` | Numbers (e.g. account number, quantity) |
| **alphanumeric** | `enabled`, `validation_type`, `regular_expression` | Mixed text (e.g. booking reference) |
| **enum** | `options` (list of values) | Fixed set of choices |
| **date** | `relative_date` | Calendar dates |
| **phone_number** | `enabled`, `country_codes` | Phone numbers with country validation |
| **time** | `enabled`, `start_time`, `end_time` | Times or time ranges |
| **address** | `{}` | Physical addresses |
| **free_text** | `{}` | Unstructured text input |
| **name_config** | `{}` | Person names |

## Usage

- **In flow prompts**: `{{entity:entity_name}}` to reference the collected value.
- **In function steps**: `conv.entities.entity_name.value` to read; check with `if conv.entities.entity_name: ...`.
- **In default step conditions**: `required_entities` gates a condition — it only triggers once all listed entities are collected.
- **In default steps**: `extracted_entities` tells the agent which entities to collect in that step. ASR biasing is automatically configured based on entity types.

## Example
```yaml
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
```
