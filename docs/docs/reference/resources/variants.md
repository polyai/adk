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

## Attributes

The `attributes` section defines the values that vary by variant.

Each attribute includes:

| Field | Description |
|---|---|
| `name` | Attribute identifier, ideally in snake_case |
| `kind` | Optional. The attribute's type: `string` (default), `number`, `boolean`, `enum`, or `object` |
| `config` | Optional. Type-specific configuration. Only `enum` takes one: `config.values` lists the allowed values |
| `values` | Map from variant name to value |

Every attribute must provide a value for every defined variant, even if that value is blank.

## Attribute types

An attribute with no `kind` is a string attribute, which is how every attribute behaved before types existed — existing files need no change.

Declaring a `kind` does two things: values are checked against it when you push, so a typo is caught at authoring time rather than on a live call, and the agent receives the value in its real type. A `number` attribute arrives as `3`, not `"3"`, and a `boolean` as `true`, not `"True"`.

| `kind` | Written in `values` as | Example |
|---|---|---|
| `string` | Text | `London Office` |
| `number` | A number | `"3"`, `"2.5"` |
| `boolean` | `"true"` or `"false"` | `"true"` |
| `enum` | One of `config.values` | `premium` |
| `object` | A JSON object or array | `'{"currency":"USD"}'` |

A blank value is allowed for every kind and means the attribute is not set for that variant yet.

!!! note "Values are stored as text"

    `values` always holds strings on disk, and `kind` says how to read them. That keeps the file readable by an ADK released before typed attributes, which would otherwise fail on a bare `3` or `true`.

    You can still write values naturally by hand — `max_retries: 3` and `max_retries: "3"` are the same attribute, and neither shows as a change against the other. `poly pull` rewrites them in the quoted form.

Changing an attribute's `kind` does not convert its existing values. Update the values in the same change, or the push is rejected with the variants whose values no longer fit.

### Blank values at runtime

A blank value behaves differently depending on the kind, and the difference only shows up on a live call:

- A blank **`string`** attribute substitutes an empty string, so `{{attr:name}}` resolves to nothing.
- A blank attribute of **any other kind** is left out of the deployed agent entirely, so `{{attr:name}}` stays unresolved and is reported as a configuration gap.

If a prompt depends on a typed attribute, give it a value for every variant rather than leaving one blank.

### Types that Agent Studio shows but does not store

Agent Studio's type picker offers three types that have no equivalent here, because the platform stores them as one of the five kinds above:

| Agent Studio type | Stored as | Value shape in `values` |
|---|---|---|
| Date & time | `string` | `2026-09-03 14:30` |
| Opening hours | `string` | `Mon: 09:00-17:00; Tue: 09:00-17:00; Wed: Closed; Thu: ...` — all seven days, `Mon` to `Sun`, separated by `; ` |
| Voice | `enum` | A voice ID, from `config.values` |

They are editor choices, not stored types. Agent Studio re-detects "Date & time" and "Opening hours" by matching the value's exact shape, so editing one of those values here into a different shape silently drops the attribute back to a plain text editor in the UI. The value itself still works. "Voice" is indistinguishable from any other `enum` once saved.

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
- [topic](./topics.md) actions (not in `content` or `example_queries`)
- rules (`rules.txt`)
- persona (`persona.txt`)
- greeting (`welcome_message`)
- disclaimer message

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

To switch the active variant at runtime, call:

~~~python
conv.set_variant("london")
~~~

## Typical attribute types

Common uses include:

| Category | Examples |
|---|---|
| Branding | greeting name, company name |
| Contact | phone numbers, addresses, office hours |
| IDs | location ID, region code |
| Feature flags | `kind: boolean` (`true` / `false`) |
| URLs | portal links, payment links |
| Environment | timezone, `is_live` |

## Important formatting notes

- variant names with special characters should be quoted
- multi-line values should use `|-`

## Validation

- Exactly one variant must have `is_default: true` — validation fails if zero or more than one variant is marked default.
- Every variant must have a value in every attribute's `values` map — a missing variant fails validation.
- Every value must match its attribute's declared `kind` — a value of the wrong type fails validation, naming the variant it came from.
- An `enum` attribute must declare a non-empty `config.values` list, with no duplicates.

## Best practices

- keep variant names stable over time
- set exactly one default variant
- provide a value, or a blank one, for every variant in every attribute
- declare a `kind` whenever the value is not text, so mistakes surface at push time
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

-   **Variant management (platform)**

    ---

    How variants are routed at runtime — SIP header routing, default selection, and `conv.variant` access.
    [Open variant management](https://docs.poly.ai/variant-management/introduction){ target="_blank" rel="noopener" }

</div>