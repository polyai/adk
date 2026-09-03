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
- **kind** (optional): The attribute's type — one of `string`, `number`, `boolean`, `enum`, `object`. Defaults to `string` when omitted.
- **config** (optional): Type-specific configuration. Only `enum` takes one: `config.values` lists the allowed values.
- **values**: Map from **variant name** to value. Must have one entry per variant. Leave a value blank for any kind to mean "not set yet".

Typed values reach the agent as their real type: a `number` attribute arrives as `3`, not `"3"`. A `string` attribute behaves exactly as it always has, which is why untyped attributes need no change.

`values` always holds strings on disk, and `kind` says how to read them — that keeps the file readable by an ADK released before typed attributes, which would fail on a bare `3` or `true`. You can still write values naturally by hand: `max_retries: 3` and `max_retries: "3"` are the same attribute, and `poly pull` rewrites them in the quoted form.

### Blank values at runtime
A blank `string` attribute substitutes an empty string, so `{{attr:name}}` resolves to nothing. A blank attribute of any other kind is left out of the deployed agent entirely, so `{{attr:name}}` stays unresolved and is reported as a configuration gap. Give typed attributes a value for every variant if a prompt depends on them.

### Types Agent Studio shows but does not store
Agent Studio's type picker offers three types with no equivalent here, because the platform stores them as one of the five kinds:

| Agent Studio type | Stored as | Value shape |
|---|---|---|
| Date & time | `string` | `2026-09-03 14:30` |
| Opening hours | `string` | `Mon: 09:00-17:00; Tue: Closed; ...` — all seven days, `Mon` to `Sun`, separated by `; ` |
| Voice | `enum` | A voice ID, from `config.values` |

Agent Studio re-detects "Date & time" and "Opening hours" by matching the value's exact shape, so editing one into a different shape drops the attribute back to a plain text editor in the UI. The value still works. "Voice" is indistinguishable from any other `enum` once saved.

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

### Typed attributes
```yaml
attributes:
  - name: max_retries
    kind: number
    values:
      new_york: "3"
      london: "5"
      tokyo: "3"

  - name: serves_alcohol
    kind: boolean
    values:
      new_york: "true"
      london: "true"
      tokyo: "false"

  - name: tier
    kind: enum
    config:
      values: [basic, premium]
    values:
      new_york: premium
      london: premium
      tokyo: basic

  - name: menu_config
    kind: object
    values:
      new_york: '{"categories":["pizza","pasta"],"currency":"USD"}'
      london: '{"categories":["pizza"],"currency":"GBP"}'
      tokyo: '{"categories":["pasta"],"currency":"JPY"}'
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
- **Feature flags**: `kind: boolean` (`true` / `false`)
- **URLs**: portal link, payment link
- **Environment**: timezone, is_live

## Best practices
- Keep variant names stable; quote them when they contain special characters.
- Set exactly **one** `is_default` variant.
- Provide a value (or a blank one) for every variant in each attribute's `values` map. Validation will fail if a variant is missing.
- Declare a `kind` when the value is not text. A `boolean` attribute is checked at push time and reaches the agent as a real boolean, where a `"True"` string is neither.
- Changing an attribute's `kind` does not convert its existing values — update them in the same change, or the push is rejected.
- Prefer `{{attr:...}}` over hard-coded strings for anything that varies by location/environment.
- Use `|-` for multi-line values (disclaimers, hours, instructions).
