---
title: Confirm caller ID before sending SMS
description: Stash the caller's number at call start, compare the last four digits for confirmation, then send an SMS — or ask for the number if it isn't available.
---

# Confirm caller ID before sending SMS

This pattern covers a very common voice + SMS flow: the agent has the caller's number from the inbound call, confirms the last four digits with the caller, and sends an SMS to that number. If the caller's number is not available (for example, in a chat session), the agent asks for it instead.

## Files involved

~~~text
functions/start_function.py       ← stash caller_number at call start
functions/caller_number_confirmed.py  ← check presence, compare last four
sms/booking_link.yaml             ← the SMS template
topics/Send Booking Link.yaml     ← topic that triggers the flow
~~~

## start_function.py

Stash the raw `caller_number` at call start so it is available throughout the conversation.

~~~python
from _gen import *  # <AUTO GENERATED>


def start_function(conv: Conversation):
    conv.state.caller_number = conv.caller_number
    return str()
~~~

## caller_number_confirmed.py

Called when the caller has confirmed (or declined) sending the SMS. Branches on whether `caller_number` is present, then validates the last-four match before sending.

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called after the caller confirms or provides a number for us to send the SMS to. "
    "confirmed: True if they confirmed the number on file, False if they want to use a different one. "
    "provided_number: the number they provided if confirmed is False."
)
@func_parameter("confirmed", "Whether the caller confirmed the number on file")
@func_parameter("provided_number", "The number the caller provided, if they did not confirm the number on file")
def caller_number_confirmed(conv: Conversation, confirmed: bool, provided_number: str = ""):
    if confirmed and conv.state.caller_number:
        to_number = conv.state.caller_number
    elif provided_number:
        to_number = provided_number
    else:
        return "Ask the caller to provide the number where we should send the link."

    conv.send_sms_template(to_number=to_number, template="booking_link")
    return "Tell the caller the link has been sent and ask if there is anything else you can help with."
~~~

## Send Booking Link.yaml

~~~yaml
enabled: true
example_queries:
  - Can you send me the booking link?
  - Can you text me a link?
  - Send me the details by text
  - I'd like a link to book online
content: |-
  The booking link is available by SMS.
actions: |-
  ## If the caller's number is available
  Tell the caller you can send the link to the number ending in the last four digits of $caller_number.
  Ask them to confirm or provide a different number.
  Use {{fn:caller_number_confirmed}} once they respond.

  ## If the caller's number is not available
  Ask the caller for the number where we should send the link.
  Use {{fn:caller_number_confirmed}} with confirmed=False and the number they provide.
~~~

!!! warning "Prose conditionals and empty variables"

    The topic actions above use a natural-language conditional on `$caller_number`. This works when the variable is populated, but can behave unreliably if the variable is always empty (for example, in chat). If you need strict branching, move the presence check into `caller_number_confirmed` and call it unconditionally from the topic action.

## SMS template (sms/booking_link.yaml)

~~~yaml
name: booking_link
content: "Here's your booking link: https://book.example.com"
~~~

## Related pages

<div class="grid cards" markdown>

-   **SMS templates**

    ---

    Reference for SMS template structure and variable substitution.
    [Open SMS templates](../reference/sms.md)

-   **Variables**

    ---

    How `conv.state` variables are discovered and referenced.
    [Open variables](../reference/variables.md)

-   **Anti-patterns**

    ---

    Why prose conditionals on variable presence are unreliable.
    [Open anti-patterns](../concepts/anti-patterns.md)

-   **Conversation object reference**

    ---

    Full reference for `conv.caller_number`, `conv.send_sms_template`, and all other `conv` attributes.
    [Open conv object reference](https://docs.poly.ai/tools/classes/conv-object)

-   **Start function (platform)**

    ---

    When start function runs, what it can access, and how to use it for initialization.
    [Open start function reference](https://docs.poly.ai/tools/start-function)

-   **SMS setup (platform)**

    ---

    Configuring SMS channels, sender numbers, and template structure.
    [Open SMS setup](https://docs.poly.ai/sms/introduction)

</div>
