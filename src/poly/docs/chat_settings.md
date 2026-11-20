# Chat Settings

## Overview

Chat settings configure the agent's behavior on the web chat channel. They are defined in `chat/configuration.yaml`.

## Location
`chat/configuration.yaml`

## Language model

The model that runs the agent in web chat, in `llm`.

### Fields
- **name** (str): The model's name, as `poly library llm` lists it. It must work in web chat. A
  model whose name can't be resolved by that region's list is pulled as `model_id` instead.

### Example
```yaml
llm:
  name: GPT-4.1 mini
```

## Greeting

The first message the agent sends when a chat session starts.

### Fields
- **welcome_message**: Text of the greeting. Can be empty. Supports `{{attr:...}}` and `{{vrbl:...}}` references.
- **language_code** (required): BCP-47 language code (e.g. `en-GB`, `en-US`).

### Example
```yaml
greeting:
  welcome_message: Hi there! How can I help you today?
  language_code: en-GB
```

## Style Prompt

Channel-specific instructions that shape how the agent writes. Separate from personality - use this for chat-specific guidance (e.g. "keep responses concise", "use bullet points for lists").

### Fields
- **prompt**: Free-text style instructions. No resource references allowed.

### Example
```yaml
style_prompt:
  prompt: You are a helpful and professional web chat assistant. Keep responses concise and use formatting where appropriate.
```

## Full `chat/configuration.yaml` example
```yaml
llm:
  name: GPT-4.1 mini
greeting:
  welcome_message: Hi! How can I help you today?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional web chat assistant. Keep responses concise.
```
