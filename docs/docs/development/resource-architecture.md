---
title: Resource architecture
description: What each ADK resource type is for, when it runs, and how the pieces reference each other.
---

# Resource architecture

<p class="lead">
Each resource type in the ADK has a specific purpose. This page helps you decide where to put new content or logic before you write it.
</p>

Choosing the wrong resource type is one of the most common sources of hard-to-debug agent behavior. The right question is not "how do I add this?" but "what kind of thing is this?"

## The core split

The ADK separates two concerns.

**Knowledge and facts** — information the agent should retrieve and communicate. Lives in topics.

**Behavior and logic** — what the agent should do, when, and how. Lives in rules, flows, and functions.

Keep these separate. Mixing factual content and behavioral instructions in the same resource makes both harder to maintain and harder to reason about.

## The six resource groups

Beneath that split, a project has six kinds of resource. What distinguishes them is less what they contain than **when they run and what invokes them**.

| Group | When it runs | Invoked by |
|---|---|---|
| [Agent behavior](#agent-behavior) | Every turn | Nothing — it is always in the prompt |
| [Knowledge base](#knowledge-base) | When the subject comes up | Retrieval, on relevance to what the caller asked |
| [Functions](#functions) | On demand, or at fixed points in the call | A reference from a prompt, or the platform lifecycle |
| [Flows](#flows) | While the caller is inside the flow | Navigation into the flow, then step by step |
| [Agent configuration](#agent-configuration) | Never on its own | Referenced by name from any of the above |
| [Channel settings](#channel-settings) | Every turn, on the way in and out | Nothing — applied by the platform per channel |

The last two are not peers of the first four. Agent configuration is the leaf layer everything else points at — handoff destinations, SMS templates, and variant attributes exist to be referenced, never to act. Channel settings are never referenced at all; the platform applies them around every turn.

### Agent behavior

`agent_settings/` holds who the agent is and how it always behaves.

| File | Holds |
|---|---|
| `rules.txt` | Global behavioral instructions |
| `personality.yaml` | Tone and manner |
| `role.yaml` | Who the agent is and what it is for |
| `guardrails.yaml` | Checks that constrain what the agent can say or do |

Rules are **always present in the prompt**, on every turn. They are not retrieved and not conditional, which makes them the right home for instructions that are unconditionally true — "always confirm the booking reference before making changes" — and the wrong home for facts, which would consume prompt space even when irrelevant to the current turn.

`personality.yaml` and `role.yaml` are narrower than rules: they accept only `{{attr:}}` and `{{vrbl:}}` references. Behavioral references such as `{{fn:}}` and `{{ho:}}` belong in `rules.txt`.

`guardrails.yaml` covers the same ground as rules from the other side. A rule is an instruction in the prompt, which the model can still be talked out of; a guardrail is a check evaluated against the conversation, with its own action when it trips. That makes them easy to confuse — "never give medical advice" is a plausible entry in either. Write it as a rule first, and add a guardrail when testing shows the rule alone isn't holding. The platform also ships a fixed catalog of guardrails you can only toggle, covering the failure modes no prompt reliably prevents on its own, such as jailbreak attempts.

See [agent settings](../reference/resources/agent_settings.md) and [guardrails](../reference/resources/guardrails.md).

### Knowledge base

`topics/*.yaml` holds subject-specific knowledge, retrieved only when the caller raises that subject.

A topic splits the two halves of the core split into two fields:

~~~yaml
name: Refund policy
enabled: true
content: Refunds are available within 30 days of purchase.
actions: If the caller asks to cancel, use {{ho:cancellations}} to transfer them.
example_queries:
  - Can I get a refund?
  - What is your returns policy?
~~~

`content` is the facts. `actions` is what to do about them. `example_queries` shape retrieval — they are how the platform decides this topic is relevant to what was just said.

Because a topic is retrieved on relevance, it costs nothing when it does not apply. That is the argument for putting subject-specific behavior in a topic's `actions` rather than adding it to `rules.txt`, where it would be present on every turn of every call.

See [topics](../reference/resources/topics.md).

### Functions

Python, for anything that must be deterministic — a comparison, an API call, a routing decision that cannot be left to the model. Every function receives a `conv` object, which is its handle on conversation state.

There are four kinds, distinguished by where they live and what invokes them:

| Kind | Location | Invoked by |
|---|---|---|
| Global | `functions/<name>.py` | `{{fn:name}}` from rules, topics, or advanced step prompts |
| Lifecycle | `functions/start_function.py`, `functions/end_function.py` | The platform, at the start and end of the call |
| Flow transition | `flows/<flow>/functions/<name>.py` | `{{ft:name}}`, within that flow only |
| Function step | `flows/<flow>/function_steps/<name>.py` | Reaching that step in the flow |

A global function is called by the model, so it has to describe itself:

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description("Validate email format.")
@func_parameter("email", "The email address to validate")
def validate_email(conv: Conversation, email: str):
    """Validate email format."""
    return "@" in email and "." in email.split("@")[1]
~~~

!!! warning "Callable functions need their decorators"

    `@func_description` and `@func_parameter` are what tell Agent Studio the function exists and how to call it. Without them the function is created with no parameters and fails when the model tries to use it. Lifecycle functions and function steps do not need them — the platform invokes those directly rather than through the model.

Functions that belong to a flow receive the flow as well, so they can move the conversation:

~~~python
def process_payment(conv: Conversation, flow: Flow):
    """Process payment for the customer."""
    conv.state.payment_success = True
    return "Payment processed"
~~~

`start_function` runs once at call start, before the first caller input. It is the right place for reading SIP headers, setting variant routing, and initializing state the rest of the conversation depends on. It is the wrong place for logic that only applies mid-conversation, or for a slow API call that would delay the greeting.

Stubs under `_gen/` supply the signatures and helpers these functions import. They are generated — do not edit them.

See [functions](../reference/resources/functions.md) and the [conv object reference](https://docs.poly.ai/tools/classes/conv-object){ target="_blank" rel="noopener" }.

### Flows

A flow is a multi-step guided conversation — what you reach for when the agent has to collect specific things in a specific order rather than answer freely.

~~~text
flows/booking/
├── flow_config.yaml          # the flow itself
├── steps/                    # conversational steps
│   └── collect_name.yaml
├── function_steps/           # steps that run code
│   └── process_payment.py
└── functions/                # transition functions, called as {{ft:}}
    └── validate_input.py
~~~

Conversational steps come in two kinds, and the difference is what they are allowed to reference:

- **Default steps** collect entities and move on. They accept `{{entity:}}`, `{{attr:}}`, and `{{vrbl:}}`, and **cannot call functions**.
- **Advanced steps** can call functions, so they also accept `{{fn:}}` and `{{ft:}}`.

A step declares what it collects and where it goes next:

~~~yaml
step_type: default_step
name: collect_name
prompt: What is your name?
extracted_entities:
  - customer_name
conditions:
  - name: has_name
    condition_type: step_condition
    required_entities:
      - customer_name
    child_step: confirm_details
~~~

Entities are defined once in `config/entities.yaml` and collected by whichever steps need them.

Navigation is always explicit. A step advances through its conditions; a function advances the flow in code. A flow function that returns without moving the flow leaves the conversation stuck — see [common flow mistakes](../reference/resources/flows.md#common-mistakes).

See [flows](../reference/resources/flows.md) and [entities](../reference/resources/entities.md).

### Agent configuration

`config/` holds the named values and destinations that everything else points at.

| File | Holds | Referenced as |
|---|---|---|
| `entities.yaml` | Things to collect from the caller | `{{entity:}}` |
| `handoffs.yaml` | Escalation destinations | `{{ho:}}` |
| `sms_templates.yaml` | Reusable message content | `{{twilio_sms:}}` |
| `variant_attributes.yaml` | Per-site or per-location values | `{{attr:}}` |
| `translations.yaml` | Localized strings | `{{tn:}}` |

State variables are the exception: they are not declared in a file but set in code as `conv.state.<name>`, then read back as `{{vrbl:name}}`.

The point of this layer is that changing a transfer destination, an SMS body, or one site's opening hours is a single edit in a single file, however many prompts refer to it.

See [handoffs](../reference/resources/handoffs.md), [SMS templates](../reference/resources/sms.md), [variants](../reference/resources/variants.md), [variables](../reference/resources/variables.md), and [translations](../reference/resources/translations.md).

### Channel settings

`voice/` and `chat/` hold per-channel behavior. Unlike agent configuration, nothing references these by name — the platform applies them automatically to every turn.

Both channels share the same two files:

| File | Holds |
|---|---|
| `configuration.yaml` | Greeting, style prompt, and — voice only — disclaimer messages |
| `safety_filters.yaml` | Per-channel content filtering |

~~~yaml
greeting:
  welcome_message: Hello! Your account shows {{attr:member-status}}. How can I help?
  language_code: en-GB
style_prompt:
  prompt: You are a helpful and professional customer service assistant.
~~~

Voice then adds two pipelines that chat has no need for — one for what the agent hears, one for what it says:

~~~text
voice/
├── configuration.yaml
├── safety_filters.yaml
├── speech_recognition/            # input: what the agent hears
│   ├── asr_settings.yaml
│   ├── keyphrase_boosting.yaml
│   └── transcript_corrections.yaml
└── response_control/              # output: what the agent says
    ├── pronunciations.yaml
    └── phrase_filtering.yaml
~~~

**Speech recognition** shapes the transcript before the agent ever sees it:

- `asr_settings.yaml` — turn-taking behavior, including whether the caller can interrupt (`barge_in`) and the overall `interaction_style`
- `keyphrase_boosting.yaml` — bias recognition toward terms it would otherwise mishear, each set to `default`, `boosted`, or `maximum`
- `transcript_corrections.yaml` — regular expressions that rewrite systematic misrecognitions, such as "at gmail dot com" becoming `@gmail.com`

**Response control** shapes speech on the way out:

- `pronunciations.yaml` — regular expressions that change how text is spoken, so `Dr.` is read as "Doctor" rather than spelled out
- `phrase_filtering.yaml` — patterns the agent must not say, either suppressed or replaced with an alternative

Reach for this group when the agent's *wording* is right but the *audio* is wrong. An account number misheard is a speech recognition problem; a product name mispronounced is a response control problem. Neither is fixed by editing prompts, which is why these are easy to waste time on in the wrong place.

See [voice settings](../reference/resources/voice_settings.md), [chat settings](../reference/resources/chat_settings.md), [speech recognition](../reference/resources/speech_recognition.md), [response control](../reference/resources/response_control.md), and [safety filters](../reference/resources/safety_filters.md).

## Which resource do I reach for?

| You are adding... | Use |
|---|---|
| A new FAQ, policy, or factual answer | Topic (`topics/`) |
| A global behavioral rule (always do X, never do Y) | `agent_settings/rules.txt` |
| Enforcement for a rule the model keeps working around | Guardrail (`agent_settings/guardrails.yaml`) |
| Agent identity and tone | `agent_settings/personality.yaml` and `role.yaml` |
| A multi-step guided conversation | Flow (`flows/`) |
| Structured data collection from the caller | Entity + flow |
| Deterministic branching or routing logic | Function (`functions/`) |
| Call initialization — routing, variant selection, reading SIP headers | `functions/start_function.py` |
| A way to escalate to a human | Handoff (`config/handoffs.yaml`) |
| Reusable SMS message content | SMS template (`config/sms_templates.yaml`) |
| Per-site or per-location configuration | Variant attributes (`config/variant_attributes.yaml`) |
| Wording for another language | Translations (`config/translations.yaml`) |
| The agent's opening line | `voice/configuration.yaml` or `chat/configuration.yaml` |
| A term the agent keeps mishearing | `voice/speech_recognition/keyphrase_boosting.yaml` |
| A word the agent mispronounces | `voice/response_control/pronunciations.yaml` |
| Something the agent must never say | `voice/response_control/phrase_filtering.yaml` |

Rules, topics, and functions are the three that overlap most, so they are the three worth a test.

!!! tip "A useful test"

    If the instruction is always true, it belongs in rules. If it is only relevant when someone asks about a specific subject, it belongs in a topic. If it requires a comparison, calculation, or API call, it belongs in a function.

## Common mistakes

### Putting behavioral logic in topic content

The `content` field of a topic is retrieved by RAG and made available as context. It should contain facts, not instructions.

~~~yaml
# Wrong — behavioral logic in content
content: |-
  If the caller asks to cancel, transfer them to the cancellations queue.

# Right — behavioral logic in actions
actions: |-
  If the caller asks to cancel, use {{ho:cancellations}} to transfer them.
~~~

### Writing prose conditionals in rules or topics

Logic like "if `{{vrbl:caller_number}}` is available, do X; otherwise do Y" is unreliable when the variable is empty. The model cannot reliably detect an empty variable from prompt text alone. Write the branch in Python instead and transition to the correct step or flow explicitly.

Beyond reliability, branching logic buried in a prompt is harder to test, harder to debug, and makes deterministic behavior depend on how the model reads an instruction. Prompts are for collecting information, presenting information, and conversational style; Python is for comparisons, routing, validation, retries, and state-based decisions.

## Resource references

Resources can point at each other by name rather than repeating hard-coded values, using a `{{prefix:name}}` placeholder in prompts, rules, topic content, and message templates. Referencing a resource by name means renaming or editing it updates every place it is used.

| Syntax | Resolves to |
|---|---|
| `{{fn:function_name}}` | [Global function](../reference/resources/functions.md) |
| `{{ft:function_name}}` | [Flow transition function](../reference/resources/flows.md) |
| `{{entity:entity_name}}` | [Collected entity value](../reference/resources/entities.md) |
| `{{attr:attribute_name}}` | [Variant attribute](../reference/resources/variants.md) |
| `{{twilio_sms:template_name}}` | [SMS template](../reference/resources/sms.md) |
| `{{ho:handoff_name}}` | [Handoff destination](../reference/resources/handoffs.md) |
| `{{vrbl:variable_name}}` | [State variable](../reference/resources/variables.md) |
| `{{tn:translation_key}}` | [Translation string](../reference/resources/translations.md) |

Names may contain letters, numbers, underscores, and hyphens.

!!! note "`{{ft:}}` is scoped to its own flow"

    A transition function only resolves within the flow that defines it — the same name in a different flow won't resolve.

Not every field accepts every prefix — see each resource's own page for exactly which ones are valid where. A prefix that isn't accepted in a field fails validation even if the resource itself exists.

### How references are resolved

You write references by **name**; Agent Studio stores them by **resource ID**. The ADK rewrites between the two on every `poly push` and `poly pull`, which is why a reference has to resolve to a real resource before it can be pushed.

`poly validate` and `poly push` both check every reference in the project, and the two failure modes look different:

1. **The prefix is not allowed in that field** — rejected as soon as the file is parsed.
2. **The prefix is allowed but nothing of that name exists** — reported as `Invalid references: <type>: <name>`.

!!! tip "Catch broken references before pushing"

    Run [`poly validate`](../reference/cli/validate.md) to check every reference in the project locally. `poly push` runs the same validation, so a broken reference blocks the push rather than reaching Agent Studio.

## Syncing and permissions

Agent Studio permissions carry over to the ADK: a resource you don't have read access to in Agent Studio won't appear in your local project. `poly pull` omits it silently rather than failing, so a project can look smaller locally than it is on the platform.

## Platform references

The ADK manages these resources; the platform documentation explains how it uses them at runtime.

- [Managed Topics](https://docs.poly.ai/managed-topics/introduction){ target="_blank" rel="noopener" } — how topics are retrieved, ranked, and used, including RAG mechanics and topic types
- [Connected Knowledge](https://docs.poly.ai/connected-knowledge/introduction){ target="_blank" rel="noopener" } — the alternative to Managed Topics for large unstructured content sets
- [Start function](https://docs.poly.ai/tools/start-function){ target="_blank" rel="noopener" } — when the lifecycle hook runs, what it can read, and common initialization patterns
- [Variant management](https://docs.poly.ai/variant-management/introduction){ target="_blank" rel="noopener" } — how variant routing and attribute lookup work
