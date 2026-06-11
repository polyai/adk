# Translations

## Purpose

Translations define localized text strings for your agent across multiple languages. Each translation has a key and a set of language-specific values, enabling the agent to respond in the user's configured language.

## Location

`config/translations.yaml`. Translations are listed under the `translations` key.

## Structure

Each translation has:
- **name**: Translation key identifier (e.g. `greeting`, `farewell`).
- **translations**: Map of language codes to localized text strings.

## Example
```yaml
translations:
  - name: greeting
    translations:
      en-GB: Hello, how can I help you?
      fr-FR: Bonjour, comment puis-je vous aider?
  - name: farewell
    translations:
      en-GB: Goodbye, have a nice day!
      fr-FR: Au revoir, bonne journée!
```

## Validation

- Translation name cannot be empty.
- Each translation must have at least one language entry.
- If languages are configured (see [Languages](languages.md)), every configured language (default + additional) must have an entry in each translation. Missing languages will cause a validation error.

## Best practices
- Use descriptive translation keys that indicate purpose (e.g. `greeting`, `error_not_found`).
- Ensure all configured languages have entries for every translation key.
- Keep translation values consistent in tone and meaning across languages.
