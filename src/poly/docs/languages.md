# Languages

## Purpose

Languages configure which languages your agent supports. A project has one default language and zero or more additional languages. Language configuration drives translation validation — every configured language must have entries in each translation key.

## Location

`agent_settings/languages.yaml`.

## Structure

- **default_language**: The primary language code (BCP 47 format, e.g. `en-GB`).
- **additional_languages**: List of additional language codes the agent supports.

## Example
```yaml
default_language: en-GB
additional_languages:
  - fr-FR
  - de-DE
```

## Validation

- Default language code is required and must be a valid BCP 47 language tag.
- Additional language codes must be valid BCP 47 language tags.
- A language code cannot appear as both the default and an additional language.
- Duplicate additional language codes are not allowed.

## Best practices
- Set the default language to the primary language of your user base.
- Add additional languages only when you have translations ready for all translation keys.
- Use standard BCP 47 codes with region subtags (e.g. `en-GB`, `fr-FR`) for consistency.
