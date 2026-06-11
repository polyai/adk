---
title: Languages
description: Configure the default language and additional languages that a PolyAI agent supports.
---

# Languages

<p class="lead">
Languages configure which languages your agent supports. A project has one default language and zero or more additional languages.
</p>

Language configuration drives translation validation — every configured language must have an entry in each translation key.

## Location

Languages are defined in:

~~~text
agent_settings/languages.yaml
~~~

The file is optional. When absent, the project runs as a single-language agent in the platform default.

## What languages contains

| Field | Description |
|---|---|
| `default_language` | The primary language code in BCP 47 format (e.g. `en-GB`). |
| `additional_languages` | List of additional language codes the agent supports. |

## Example

~~~yaml
default_language: en-GB
additional_languages:
  - fr-FR
  - de-DE
~~~

## Validation

- `default_language` is required and must be a valid BCP 47 language tag.
- Each entry in `additional_languages` must be a valid BCP 47 language tag.
- A language code cannot appear as both the default and an additional language.
- Duplicate additional language codes are not allowed.

!!! tip "Use region subtags"

    Use standard BCP 47 codes with region subtags (e.g. `en-GB`, `fr-FR`, `de-DE`) so downstream voice and TTS configuration can resolve unambiguously.

## Best practices

- set the default language to the primary language of your user base
- add additional languages only when translations are ready for every translation key
- keep BCP 47 codes consistent across `languages.yaml`, `translations.yaml`, and voice settings

## Related pages

<div class="grid cards" markdown>

-   **Translations**

    ---

    Define the localized text strings used for each configured language.
    [Open translations](./translations.md)

-   **Agent settings**

    ---

    See how `languages.yaml` fits alongside personality, role, and rules.
    [Open agent settings](./agent_settings.md)

-   **Voice settings**

    ---

    Configure per-language voice and TTS behaviour for multilingual agents.
    [Open voice settings](./voice_settings.md)

</div>
