# Entities

## Purpose
Entities define structured data the agent can collect (date of birth, phone number, choice from a list). Used in
flow steps via `extracted_entities` (what to collect) and `required_entities` (what must be collected before a
condition triggers). Can also be referenced in executed Python.

## Location
`config/entities.yaml`, listed under the `entities` key.

## Structure
| Field | Notes |
|---|---|
| `name` | Identifier (snake_case); used in prompts as `{{entity:entity_name}}` |
| `description` | What the entity represents, shown to the LLM to guide extraction |
| `entity_type` | One of the types below |
| `config` | Type-specific settings |

## Entity types and config
| Type | Config fields | Description |
|---|---|---|
| `numeric` | `has_decimal`, `has_range`, `min`, `max` | Numbers (account number, quantity) |
| `alphanumeric` | `enabled`, `validation_type`, `regular_expression` | Mixed text (booking reference) |
| `enum` | `options` (list) | Fixed set of choices |
| `date` | `relative_date` | Calendar dates |
| `phone_number` | `enabled`, `country_codes` | Phone numbers with country validation |
| `time` | `enabled`, `start_time`, `end_time` | Times or time ranges |
| `address` | `{}` | Physical addresses |
| `free_text` | `{}` | Unstructured text |
| `name_config` | `{}` | Person names |

## Usage
- In flow prompts: `{{entity:entity_name}}` for the collected value.
- In function steps: `conv.entities.entity_name.value` to read; `if conv.entities.entity_name:` to check.
- In default step conditions: `required_entities` gates a condition — triggers only once all listed entities are
  collected.
- In default steps: `extracted_entities` tells the agent what to collect; ASR biasing auto-configures from entity
  types.

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
