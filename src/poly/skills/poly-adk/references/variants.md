# Variants

## Purpose
Variant attributes provide per-variant configuration (location, environment, tenant). The platform picks a
variant at runtime; the agent reads that variant's attributes so prompts/behavior vary without separate code or
deployments.

## Location
`config/variant_attributes.yaml`

## Structure
Two top-level keys:

**`variants`** — list of variants
| Field | Notes |
|---|---|
| `name` (required) | Unique identifier (location/environment/tenant); used as the key in `values` |
| `is_default` (optional) | Exactly one variant must have `is_default: true` — used when no variant resolves at runtime |

**`attributes`** — list of attributes
| Field | Notes |
|---|---|
| `name` | Attribute identifier (snake_case), e.g. `greeting_name`, `support_phone_number` |
| `values` | Map from variant name → string value; one entry per variant; `""`, single-line, or multi-line (`\|-`) |

## Example
```yaml
variants:
  - name: new_york
    is_default: true
  - name: london
  - name: tokyo

attributes:
  - name: office_phone
    values:
      new_york: "+12125551234"
      london: "+442071234567"
      tokyo: "+81312345678"
  - name: office_hours
    values:
      new_york: "9am - 5pm EST"
      london: "9am - 5pm GMT"
      tokyo: "9am - 5pm JST"
  - name: greeting_name
    values:
      new_york: "New York Office"
      london: "London Office"
      tokyo: "Tokyo Office"
  - name: custom_disclaimer
    values:
      new_york: |-
        This call is recorded for quality assurance.
        You may request a copy of this recording.
      london: |-
        This call may be recorded in accordance with UK regulations.
      tokyo: ""
```
Quote variant names with special characters (e.g. `&`, parentheses).

## Usage
**In prompts/resource files** — `{{attr:attribute_name}}` in: flow step prompts, topic actions (not content or
example_queries), rules.txt, greeting (`welcome_message`), disclaimer, personality `custom`, role `custom`.

**In Python**:
```python
phone = conv.variant.office_phone
hours = conv.variant.office_hours
```

## Typical attribute types
- Branding: greeting name, company name
- Contact: phone numbers, addresses, office hours
- IDs: location_id, region code
- Feature flags: `"True"` / `"False"` strings, checked in Python
- URLs: portal link, payment link
- Environment: timezone, is_live

## Best practices
- Keep variant names stable; quote special characters.
- Exactly one `is_default` variant.
- Provide a value (or `""`) for every variant in every attribute's `values` map — missing one fails validation.
- Prefer `{{attr:...}}` over hardcoded strings for anything location/environment-specific.
- Use `|-` for multi-line values (disclaimers, hours, instructions).
