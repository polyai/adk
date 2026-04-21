---
title: Venue-specific goodbye with clean hangup
description: End the call with a location-specific closing message without the LLM injecting its own filler before the disconnect.
---

# Venue-specific goodbye with clean hangup

When the agent needs to say a specific goodbye and then hang up, a common mistake is relying on the LLM to produce the closing utterance. The LLM may add its own filler ("Thank you for calling, goodbye!") before the function executes, resulting in two closing statements — or the wrong one playing.

The fix is to return the closing utterance directly from a function, combined with `hangup: True`. The function controls exactly what is said and when the call ends.

## The problem

~~~yaml
# In a topic action — don't do this for goodbyes
actions: |-
  Thank the caller and say goodbye.
  Use {{fn:hang_up_call}} to end the call.
~~~

The LLM speaks its own goodbye first, then the function executes. You end up with two closing statements.

## The solution

Return the utterance and hangup from the function itself. The function speaks the closing message and ends the call atomically — no LLM turn in between.

## Files involved

~~~text
functions/goodbye_and_hang_up.py    ← closing utterance + hangup
variants/                           ← per-site closing messages (optional)
topics/Goodbye.yaml                 ← triggers the function
~~~

## goodbye_and_hang_up.py

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description(
    "Called when the caller is ready to end the call. "
    "Speaks the closing message and hangs up."
)
def goodbye_and_hang_up(conv: Conversation):
    # Use a variant attribute for site-specific closings, or a plain string for a single site.
    closing = conv.variant.closing_message if conv.variant else "Thanks for calling. Goodbye!"
    return {
        "utterance": closing,
        "hangup": True,
    }
~~~

## Goodbye.yaml

~~~yaml
enabled: true
example_queries:
  - Goodbye
  - That's all I need
  - Thanks, bye
  - I'm done
  - No, nothing else
content: ""
actions: |-
  Use {{fn:goodbye_and_hang_up}} to close the call.
  Do not say anything before calling the function.
~~~

!!! tip "The 'do not say anything' instruction"

    Including "Do not say anything before calling the function" in the topic action suppresses the LLM's tendency to add its own closing line before the function fires. The utterance in the function return value is what the caller hears.

## Variant attribute for site-specific closing messages

If different locations need different goodbyes, define a `closing_message` attribute in each variant:

~~~yaml
# variants/london.yaml
attributes:
  closing_message: "Thanks for calling the London store. Goodbye!"

# variants/new_york.yaml
attributes:
  closing_message: "Thanks for calling the New York store. Have a great day!"
~~~

Then access it in the function via `conv.variant.closing_message` as shown above.

## Related pages

<div class="grid cards" markdown>

-   **Functions reference**

    ---

    Return values, utterance, hangup, and control flow.
    [Open functions](../reference/functions.md)

-   **Variants**

    ---

    Per-site configuration using variant attributes.
    [Open variants](../reference/variants.md)

-   **Return values reference (platform)**

    ---

    All supported return shapes — `utterance`, `hangup`, combined dicts, and transition objects.
    [Open return values reference](https://docs.poly.ai/tools/return-values)

-   **Variant management (platform)**

    ---

    How variant attributes are defined, routed, and accessed via `conv.variant`.
    [Open variant management](https://docs.poly.ai/variant-management/introduction)

</div>
