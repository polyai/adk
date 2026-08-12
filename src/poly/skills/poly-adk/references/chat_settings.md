# Chat Settings

## Overview
Configures the agent's behavior on the web chat channel, in `chat/configuration.yaml`.

## Greeting
| Field | Notes |
|---|---|
| `welcome_message` (required) | Greeting text; supports `{{attr:...}}` and `{{vrbl:...}}` |
| `language_code` (required) | BCP-47 code, e.g. `en-GB`, `en-US` |

```yaml
greeting:
  welcome_message: Hi there! How can I help you today?
  language_code: en-GB
```

## Style prompt
Chat-specific guidance (e.g. "keep responses concise", "use bullet points for lists").
| Field | Notes |
|---|---|
| `prompt` | Free-text style instructions; no resource references allowed |

## Full example
```yaml
greeting:
  welcome_message: Hi! How can I help you today?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional web chat assistant. Keep responses concise.
```
