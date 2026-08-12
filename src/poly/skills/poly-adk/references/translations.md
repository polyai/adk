# Translations

## Purpose
Localized text strings across languages. Each has a key and language-specific values so the agent can respond in
the user's configured language.

## Location
`config/translations.yaml`, listed under the `translations` key.

## Structure
| Field | Notes |
|---|---|
| `name` | Translation key identifier (e.g. `greeting`, `farewell`) |
| `translations` | Map of language code → localized text |

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
- `name` cannot be empty.
- Each translation needs at least one language entry.
- If languages are configured (see `references/languages.md`), every configured language (default + additional)
  must have an entry in each translation, or validation fails.

## Best practices
Descriptive keys (`greeting`, `error_not_found`); every configured language covered for every key; consistent
tone/meaning across languages.
