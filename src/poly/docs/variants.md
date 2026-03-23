# Variants

## Purpose

Variant attributes provide per-variant configuration (per location, environment, or tenant). The platform chooses a variant at runtime; the agent reads attributes for that variant so prompts and behavior can vary without separate code or deployments.

## Location

`config/variant_attributes.yaml`

## Structure

The file has two top-level keys:

### `variants` - List of variants
- **name** (required): Unique identifier (e.g. a location name, environment, or tenant). Used as the key in attribute `values`.
- **is_default** (optional): Exactly one variant must have `is_default: true`. Used when no variant is resolved at runtime.

### `attributes` - List of attributes
- **name**: Attribute identifier (snake_case recommended), e.g. `greeting_name`, `support_phone_number`.
- **values**: Map from **variant name** to string value. Must have one entry per variant. Values can be `""`, a single line, or multi-line (`|-`).

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

Ensure the YAML is formatted correctly, for example variant names with special characters (e.g. `&`, parentheses) must be quoted.

## Usage

### In prompts and resource files
Use `{{attr:attribute_name}}` in:
- Flow step prompts
- Topic actions (not in content or example_queries)
- Rules (`rules.txt`)
- Greeting (`welcome_message`)
- Disclaimer message
- Personality (`custom`)
- Role (`custom`)

```
Our office number is {{attr:office_phone}}. We're open {{attr:office_hours}}.
```

### In Python
```python
phone = conv.variant.office_phone
hours = conv.variant.office_hours
```

Use the same attribute names as defined in `variant_attributes.yaml`.

## Typical attribute types
- **Branding**: greeting name, company name
- **Contact**: phone numbers, addresses, office hours
- **IDs**: location_id, region code
- **Feature flags**: `"True"` / `"False"` strings (check in Python)
- **URLs**: portal link, payment link
- **Environment**: timezone, is_live

## Best practices
- Keep variant names stable; quote them when they contain special characters.
- Set exactly **one** `is_default` variant.
- Provide a value (or `""`) for every variant in each attribute's `values` map. Validation will fail if a variant is missing.
- Prefer `{{attr:...}}` over hard-coded strings for anything that varies by location/environment.
- Use `|-` for multi-line values (disclaimers, hours, instructions).
