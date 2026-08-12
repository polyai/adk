# Languages

## Purpose
Configure which languages the agent supports. One default language, zero or more additional languages. Drives
translation validation — every configured language must have entries in each translation key.

## Location
`agent_settings/languages.yaml`

## Structure
| Field | Notes |
|---|---|
| `default_language` | Primary language code (BCP 47, e.g. `en-GB`) |
| `additional_languages` | List of additional language codes |

```yaml
default_language: en-GB
additional_languages:
  - fr-FR
  - de-DE
```

## Validation
- Default language required, must be valid BCP 47.
- Additional codes must be valid BCP 47.
- A code cannot appear as both default and additional.
- No duplicate additional codes.

## Best practices
Set default to the primary user-base language; add additional languages only once translations are ready for all
keys; use standard BCP 47 codes with region subtags.
