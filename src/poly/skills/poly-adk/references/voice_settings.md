# Voice Settings

## Overview
Configures the agent's behavior on the voice channel, in `voice/configuration.yaml`.

## Greeting
| Field | Notes |
|---|---|
| `welcome_message` (required) | Greeting text; supports `{{attr:...}}` and `{{vrbl:...}}` |
| `language_code` (required) | BCP-47 code, e.g. `en-GB`, `en-US` |

```yaml
greeting:
  welcome_message: Hello! Welcome to our service. How can I assist you today?
  language_code: en-GB
```

## Style prompt
Voice-specific phrasing/verbosity/tone guidance — separate from personality.
| Field | Notes |
|---|---|
| `prompt` | Free-text style instructions; no resource references allowed |

```yaml
style_prompt:
  prompt: You are a helpful and professional customer service assistant. Use natural, conversational phrasing.
```

## Disclaimer message
Optional message played before the greeting (e.g. "This call may be recorded").
| Field | Notes |
|---|---|
| `message` | Disclaimer text; supports `{{attr:...}}` and `{{vrbl:...}}` |
| `enabled` | Boolean toggle |
| `language_code` | BCP-47 code |

## Full example
```yaml
greeting:
  welcome_message: Hello! Welcome to our service. Your account shows {{attr:member_status}}. How can I assist you today?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional customer service assistant.
disclaimer_messages:
  message: This conversation may be recorded for quality assurance.
  enabled: true
  language_code: en-GB
```

See also: `references/speech_recognition.md`, `references/response_control.md`.
