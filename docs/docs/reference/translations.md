---
title: Translations
description: Define localized text strings that an agent can use across its configured languages.
---

# Translations

<p class="lead">
Translations define localized text strings for your agent. Each translation has a key and a set of language-specific values, so the agent can respond in the user's configured language.
</p>

Translations are paired with [languages](./languages.md): every translation key must include an entry for the default language and for each additional language the project supports.

## Location

Translations are defined in:

~~~text
config/translations.yaml
~~~

Translations are listed under the `translations` key. The file is optional.

## What a translation contains

| Field | Description |
|---|---|
| `name` | Translation key identifier. Referenced in rules, topics, and flows as `{{tr:name}}`. |
| `translations` | Map of BCP 47 language codes to localized text strings. |

## Example

~~~yaml
translations:
  - name: greeting
    translations:
      en-GB: Hello, how can I help you?
      fr-FR: Bonjour, comment puis-je vous aider?
  - name: farewell
    translations:
      en-GB: Goodbye, have a nice day!
      fr-FR: Au revoir, bonne journée!
~~~

## Validation

- `name` is required and cannot be empty.
- Each translation must have at least one language entry.
- If `agent_settings/languages.yaml` is present, every configured language (default + additional) must have an entry in each translation. Missing languages cause a validation error.
- Duplicate translation names are not allowed.

## Referencing translations

Translations are referenced by name in rules, topics, and flow prompts:

~~~text
{{tr:greeting}}
~~~

At runtime, the platform resolves the reference to the localized string for the current conversation language.

## Best practices

- use descriptive translation keys that indicate purpose (e.g. `greeting`, `error_not_found`, `confirmation_prompt`)
- ensure every configured language has an entry for every translation key before pushing
- keep translation values consistent in tone and meaning across languages
- prefer translation references over hard-coded strings in prompts when an agent supports more than one language

!!! warning "Translation keys are shared across channels"

    A translation key resolves to the same value on voice and chat. Use [SMS templates](./sms.md) when you need channel-specific copy.

## Related pages

<div class="grid cards" markdown>

-   **Languages**

    ---

    Configure the default and additional languages that translations must cover.
    [Open languages](./languages.md)

-   **Agent settings**

    ---

    See how translations fit alongside other agent configuration.
    [Open agent settings](./agent_settings.md)

-   **SMS templates**

    ---

    Reusable SMS bodies, complementary to translations for channel-specific copy.
    [Open SMS templates](./sms.md)

</div>
