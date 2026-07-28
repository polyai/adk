---
title: SMS link with transfer fallback
description: Send an SMS with a link, and transfer to a live agent if SMS cannot be sent or the caller prefers to speak to someone.
---

# SMS link with transfer fallback

A common pattern in voice agents: offer to send the caller a link by SMS, but transfer to a live agent if SMS isn't an option or the caller asks for it. The decision lives in a function so it is deterministic — not subject to LLM interpretation.

## Files involved

~~~text
functions/start_function.py           ← stash caller_number
functions/send_link_or_transfer.py    ← SMS or handoff decision
config/sms_templates.yaml             ← SMS template (alongside other templates)
config/handoffs.yaml                  ← transfer destination (alongside other handoffs)
topics/Get Booking Link.yaml          ← triggers the pattern
~~~

## send_link_or_transfer.py

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller has been offered the booking link by SMS or by speaking to an agent. "
    "wants_sms: True if they want the link by text, False if they want to speak to someone."
)
@func_parameter("wants_sms", "True if the caller wants the SMS link, False if they want to speak to an agent")
def send_link_or_transfer(conv: Conversation, wants_sms: bool):
    if wants_sms:
        to_number = conv.state.caller_number
        if not to_number:
            return (
                "Tell the caller we were unable to send the SMS because we do not have their number. "
                "Offer to transfer them to an agent instead or ask for a number to send to."
            )
        conv.send_sms_template(to_number=to_number, template="booking_link")
        return "Tell the caller the link has been sent and ask if there is anything else you can help with."
    else:
        conv.call_handoff(
            destination="agent_queue",
            reason="caller_requested_agent",
            utterance="Let me connect you with a member of the team now.",
        )
~~~

## Get Booking Link.yaml

~~~yaml
enabled: true
example_queries:
  - Can you send me a link to book?
  - How do I book online?
  - I want to make a reservation online
  - Send me a booking link
  - Can I speak to someone about booking?
content: |-
  Bookings can be made online at book.example.com, or by speaking with a team member.
actions: |-
  Ask the caller if they would like the link sent by text message, or if they would prefer to speak to someone.
  Use {{fn:send_link_or_transfer}} once they respond.
~~~

!!! warning "Testing via `poly chat`: `caller_number` will be empty"

    `conv.state.caller_number` is populated from inbound caller ID, which is only available on a real voice call. When testing with `poly chat`, `caller_number` is always empty regardless of `--channel` — `wants_sms: True` will always hit the "unable to send" branch.

    To exercise the SMS path locally, mock the value in `start_function.py`:

    ~~~python
    conv.state.caller_number = "+15551234567"  # remove before deploying
    ~~~

## config/handoffs.yaml

The `destination` value passed to `conv.call_handoff` must match the `name` of a handoff defined in `config/handoffs.yaml`. All handoffs are defined in a single file under the `handoffs` key.

~~~yaml
handoffs:
  - name: agent_queue
    description: Transfer to live agent queue
    is_default: true
    sip_config:
      method: refer
      phone_number: "+441234567890"
~~~

See the [handoffs reference](../reference/handoffs.md) for all SIP method options and field details.

## Per-environment sender number

If the sender number differs between environments, the simplest approach is to configure `env_phone_numbers` directly in `config/sms_templates.yaml` — no code required:

~~~yaml
sms_templates:
  - name: booking_link
    text: "Here's your booking link: https://book.example.com"
    env_phone_numbers:
      sandbox: "+441111111111"
      pre_release: "+442222222222"
      live: "+443333333333"
~~~

The platform selects the right number automatically when `conv.send_sms_template()` is called. See the [SMS setup reference](https://docs.poly.ai/sms/introduction){ target="_blank" rel="noopener" } for full template configuration options.

If you need more control — for example, when using `conv.send_sms()` to send free-form content rather than a template — you can read `conv.env` directly:

~~~python
ENV_SENDER_NUMBERS = {
    "sandbox": "+441111111111",
    "pre-release": "+442222222222",
    "live": "+443333333333",
}

def send_link_or_transfer(conv: Conversation, wants_sms: bool):
    if wants_sms:
        from_number = ENV_SENDER_NUMBERS.get(conv.env, ENV_SENDER_NUMBERS["sandbox"])
        conv.send_sms(
            to_number=conv.state.caller_number,
            from_number=from_number,
            content="Here's your booking link: https://book.example.com",
        )
        return "Tell the caller the link has been sent."
    ...
~~~

!!! tip "Use secrets for sender numbers in production"

    Avoid hardcoding phone numbers in function code. Store them as [secrets](https://docs.poly.ai/secrets/introduction){ target="_blank" rel="noopener" } and retrieve with `conv.utils.get_secret("sms_sender_live")`.

## Related pages

<div class="grid cards" markdown>

-   **SMS templates**

    ---

    Structure and variable substitution for SMS templates.
    [Open SMS templates](../reference/sms.md)

-   **Handoffs**

    ---

    Configure transfer destinations used by `conv.call_handoff`.
    [Open handoffs](../reference/handoffs.md)

-   **Functions**

    ---

    Return values, conv API, and function structure.
    [Open functions](../reference/functions.md)

-   **Conversation object reference**

    ---

    Full reference for `conv.send_sms_template`, `conv.call_handoff`, `conv.env`, and all other `conv` attributes.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }

-   **Secrets (platform)**

    ---

    Store sensitive values like sender numbers and retrieve them at runtime with `conv.utils.get_secret`.
    [Open secrets reference](https://docs.poly.ai/secrets/introduction){ target="_blank" rel="noopener" }

-   **SMS setup (platform)**

    ---

    Configuring SMS channels, sender numbers, and template structure.
    [Open SMS setup](https://docs.poly.ai/sms/introduction){ target="_blank" rel="noopener" }

</div>
