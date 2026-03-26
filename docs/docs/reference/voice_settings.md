---
title: Voice settings
description: Configure how the agent behaves on the voice channel, including greetings, style guidance, and disclaimers.
---

# Voice settings

<p class="lead">
Voice settings configure how the agent behaves on the voice channel.
They are defined in <code>voice/configuration.yaml</code>.
</p>

Voice settings control what the agent says at the start of a call and how it should sound throughout the conversation.

## Location

~~~text
voice/configuration.yaml
~~~

## What voice settings control

<div class="grid cards" markdown>

-   **Greeting**

    ---

    The first message the agent speaks when a call starts.

-   **Style prompt**

    ---

    Channel-specific instructions that shape how the agent speaks.

-   **Disclaimer message**

    ---

    An optional message played before the greeting, such as a recording notice.

</div>

## Greeting

The greeting is the first message the agent speaks when a call starts.

### Fields

| Field | Required | Description |
|---|---|---|
| `welcome_message` | Yes | Text of the greeting. Supports `{{attr:...}}` and `{{vrbl:...}}` references. |
| `language_code` | Yes | BCP-47 language code, for example `en-GB` or `en-US`. |

### Example

~~~yaml
greeting:
  welcome_message: Hello! Welcome to our service. How can I assist you today?
  language_code: en-GB
~~~

## Style prompt

The style prompt contains channel-specific instructions that shape how the agent speaks.

Use this for voice-specific guidance such as:

- phrasing
- verbosity
- spoken tone
- conversational pacing

This is separate from the agent's broader personality. Use it to shape how the agent should sound specifically on phone calls.

### Fields

| Field | Required | Description |
|---|---|---|
| `prompt` | No | Free-text style instructions. Resource references are not allowed. |

### Example

~~~yaml
style_prompt:
  prompt: You are a helpful and professional customer service assistant. Use natural, conversational phrasing.
~~~

!!! tip "Keep voice guidance channel-specific"

    Use the style prompt for voice-specific speaking guidance. Use agent settings for the broader identity, role, and behavioral rules that apply across the agent.

## Disclaimer message

A disclaimer message is an optional notice played at the start of a call before the greeting.

Typical examples include:

- recording notices
- compliance messages
- service disclaimers

### Fields

| Field | Required | Description |
|---|---|---|
| `message` | No | Disclaimer text. Supports `{{attr:...}}` and `{{vrbl:...}}` references. |
| `enabled` | No | Whether the disclaimer is played. |
| `language_code` | No | BCP-47 language code for the disclaimer. |

### Example

~~~yaml
disclaimer_messages:
  message: This conversation may be recorded for quality assurance.
  enabled: true
  language_code: en-GB
~~~

## Full example

~~~yaml
greeting:
  welcome_message: Hello! Welcome to our service. Your account shows {{attr:member_status}}. How can I assist you today?
  language_code: en-GB

style_prompt:
  prompt: You are a helpful and professional customer service assistant.

disclaimer_messages:
  message: This conversation may be recorded for quality assurance.
  enabled: true
  language_code: en-GB
~~~

## Related voice resources

<div class="grid cards" markdown>

-   **Speech recognition**

    ---

    Configure ASR settings, keyphrase boosting, and transcript corrections.
    [Open speech recognition](./speech_recognition.md)

-   **Response control**

    ---

    Configure pronunciations and phrase filtering before output is spoken.
    [Open response control](./response_control.md)

</div>