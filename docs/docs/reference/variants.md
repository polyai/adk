---
title: Variants
description: Use variant attributes to change agent behavior and content by location, environment, or tenant.
---

# Variants

<p class="lead">
Variant attributes provide per-variant configuration so prompts and behavior can change by location, environment, or tenant without separate code or deployments.
</p>

At runtime, the platform selects a variant, and the agent reads the attributes associated with that variant.

## Location

Variant attributes are defined in:

~~~text
config/variant_attributes.yaml
~~~

## What the file contains

The file has two top-level keys:

- `variants`
- `attributes`

## Variants

The `variants` section defines the available variants.

Each variant includes:

| Field | Required | Description |
|---|---|---|
| `name` | Yes | Unique identifier for the variant |
| `is_default` | No | Marks the fallback variant used when no variant is resolved at runtime |

Exactly one variant should have `is_default: true`.

## Attributes

The `attributes` section defines the values that vary by variant.

Each attribute includes:

| Field | Description |
|---|---|
| `name` | Attribute identifier, ideally in snake_case |
| `values` | Map from variant name to string value |

Every attribute must provide a value for every defined variant, even if that value is an empty string.

## Example

~~~yaml
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
~~~

## Why variants are useful

Variants let one agent behave differently in different contexts without duplicating the whole project.

<div class="grid cards" markdown>

-   **Branding**

    ---

    Change names, labels, or brand-specific wording.

-   **Contact details**

    ---

    Swap phone numbers, addresses, and office hours.

-   **Environment-specific behavior**

    ---

    Store values such as region codes, timezones, or flags.

-   **Multi-tenant setups**

    ---

    Reuse the same logic with tenant-specific values.

</div>

## Using variant attributes in prompts and resource files

Use `{{attr:attribute_name}}` in supported text fields such as:

- flow step prompts
- topic actions
- rules
- greeting messages
- disclaimer messages
- personality `custom`
- role `custom`

### Example

~~~text
Our office number is {{attr:office_phone}}. We're open {{attr:office_hours}}.
~~~

## Using variant attributes in Python

In code, variant values are read from `conv.variant`:

~~~python
phone = conv.variant.office_phone
hours = conv.variant.office_hours
~~~

Use the same attribute names that are defined in `variant_attributes.yaml`.

## Typical attribute types

Common uses include:

| Category | Examples |
|---|---|
| Branding | greeting name, company name |
| Contact | phone numbers, addresses, office hours |
| IDs | location ID, region code |
| Feature flags | `"True"` / `"False"` strings, checked in Python |
| URLs | portal links, payment links |
| Environment | timezone, `is_live` |

## Important formatting notes

- variant names with special characters should be quoted
- multi-line values should use `|-`
- every variant must have a value for every attribute

!!! warning "Missing values will fail validation"

    If a variant is missing from an attribute’s `values` map, validation will fail.

## Best practices

- keep variant names stable over time
- set exactly one default variant
- provide a value or `""` for every variant in every attribute
- prefer `{{attr:...}}` over hard-coded strings when values vary by location or environment
- use multi-line YAML for disclaimers, instructions, or longer text values

## Related pages

<div class="grid cards" markdown>

-   **Topics**

    ---

    See how variant attributes are used in topic actions.
    [Open topics](./topics.md)

-   **Voice settings**

    ---

    Use variant attributes in greetings and disclaimers.
    [Open voice settings](./voice_settings.md)

</div>