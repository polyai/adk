# Chat Settings

## Overview

Chat settings configure the agent's behavior on the web chat channel. They are defined in `chat/configuration.yaml`.

## Location
`chat/configuration.yaml`

## Greeting

The first message the agent sends when a chat session starts.

### Fields
- **welcome_message** (required): Text of the greeting. Supports `{{attr:...}}` and `{{vrbl:...}}` references.
- **language_code** (required): BCP-47 language code (e.g. `en-GB`, `en-US`).

### Example
```yaml
greeting:
  welcome_message: Hi there! How can I help you today?
  language_code: en-GB
```

## Style Prompt

Channel-specific instructions that shape how the agent writes. Separate from personality — use this for chat-specific guidance (e.g. "keep responses concise", "use bullet points for lists").

### Fields
- **prompt**: Free-text style instructions. No resource references allowed.

### Example
```yaml
style_prompt:
  prompt: You are a helpful and professional web chat assistant. Keep responses concise and use formatting where appropriate.
```

## Full `chat/configuration.yaml` example
```yaml
greeting:
  welcome_message: Hi! How can I help you today?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional web chat assistant. Keep responses concise.
```
