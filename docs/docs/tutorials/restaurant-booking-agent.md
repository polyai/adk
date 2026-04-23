---
title: Build a restaurant booking agent
description: A complete walkthrough building a voice agent that takes table reservations — covering flows, entities, functions, and topics.
---

# Build a restaurant booking agent

<p class="lead">
This tutorial builds a complete voice agent for a restaurant. By the end you will have a working agent that greets callers, collects a reservation, and confirms the details.
</p>

You will use the ADK to define the agent, iterate on it, and push it for testing. Merging and deployment still happen in Agent Studio.

## What you will build

The agent handles calls to **Maison**, a fictional restaurant. When a caller asks to make a reservation, the agent:

1. Enters a booking flow and collects the caller's name, party size, and preferred date and time
2. Confirms the details back to the caller
3. Stores the booking on the conversation state

## What you will learn

This tutorial covers:

- creating an empty project in Agent Studio
- initializing a local project and pulling its configuration
- working on a branch
- defining entities for structured data collection
- building a multi-step flow with default steps and a function step
- writing a start function and a booking function
- triggering a flow from a topic
- tuning speech recognition with keyphrase boosting and transcript corrections
- adjusting spoken output with pronunciation rules
- previewing changes with `poly status` and `poly diff`
- pushing and testing with `poly chat`

## Prerequisites

Before you start:

- you have Python 3.14 or later installed
- you have `uv` installed
- you have installed the ADK: `pip install polyai-adk`
- you have a PolyAI API key exported as `POLY_ADK_KEY`
- **you have created an empty project in Agent Studio** — the ADK cannot create projects, it can only sync them. Open Agent Studio, create a new project, and make a note of its **account ID** and **project ID**. You will need both to initialize the local project.

!!! tip "Finding your account ID and project ID"

    Both IDs are visible in the Agent Studio project URL (e.g. `https://studio.poly.ai/<account_id>/<project_id>/...`) and on the project's settings page.

Verify the CLI is available:

~~~bash
poly --version
~~~

## Part 1 — Set up the project

### Initialize

Create a directory and run `poly init` inside it, passing the account ID and project ID you noted above:

~~~bash
mkdir maison && cd maison
poly init --region <region> --account_id <account_id> --project_id <project_id>
~~~

Replace `<region>` with the region your Agent Studio tenant lives in (see `poly init --help` for valid values), and `<account_id>` / `<project_id>` with the values from your empty project.

~~~text
Initializing project <account_id>/<project_id>...
✓ Project initialized at /Users/yourname/maison/<account_id>/<project_id>
~~~

If you prefer to pick values interactively, run `poly init` with no flags — you will be prompted for each one in turn. You can navigate with the arrow keys or start typing to filter the list.

!!! info "`poly init` creates a subdirectory"

    The project is created at `{cwd}/{account_id}/{project_id}`, not directly in your current directory. After init completes, change into the project directory before running any other commands:

    ~~~bash
    cd <account_id>/<project_id>
    ~~~

`poly init` also pulls the current configuration from Agent Studio automatically. There is no need to run `poly pull` separately.

Your project directory now contains the initial configuration as YAML and Python files:

~~~text
<account_id>/<project_id>/
├── project.yaml
├── _gen/
├── agent_settings/
│   ├── personality.yaml
│   ├── role.yaml
│   └── rules.txt
├── config/
│   └── handoffs.yaml
├── variables/                          # Virtual — no files on disk
└── voice/
    ├── configuration.yaml
    └── speech_recognition/
        └── asr_settings.yaml
~~~

The `_gen/` directory contains auto-generated platform code. Do not edit it — it is overwritten on every pull.

Files like `config/entities.yaml`, `flows/`, and `topics/` are only created when you add those resources to the project. You will create them in this tutorial.

### Create a working branch

It is good practice to make changes on a branch. Create one now:

~~~bash
poly branch create booking-flow
~~~

~~~text
Branch 'booking-flow' created (ID: BRANCH-XXXXXXXX)
~~~

You are now on the `booking-flow` branch. Any changes you push will go to that branch in Agent Studio, leaving `main` (and Sandbox) untouched.

!!! tip "Check which branch you are on"

    Run `poly status` at any time to see your current branch, region, and when the project was last pulled.

## Part 2 — Define the agent

### Personality

Open `agent_settings/personality.yaml`. Adjust the adjectives to suit the Maison brand:

~~~yaml
adjectives:
  Polite: true
  Calm: true
  Kind: true
custom: ""
~~~

The file has two fields:

- **`adjectives`** — a map of preset tonal traits. Each is set to `true` or `false`; every selected trait is combined into the agent's personality.
- **`custom`** — a free-text description that can extend or replace the adjectives. It accepts `{{attr:...}}` and `{{vrbl:...}}` references, so the personality can vary per [variant](../reference/variants.md) or per call.

!!! info "Allowed adjective values"

    `adjectives` keys must come from a fixed set: `Polite`, `Calm`, `Kind`, `Funny`, `Energetic`, `Thoughtful`, and `Other`. Any other key causes `poly push` to fail with a validation error.

!!! tip "How `Other` works"

    `Other` is the "none of the above" switch. When you set `Other: true`, every other adjective must be `false` (or omitted) — combining `Other: true` with any other adjective set to `true` fails validation with:

    ~~~text
    Other adjective can only be set if no other adjectives are selected.
    ~~~

    Use `Other: true` together with the `custom` field when the six presets do not capture the tone you want and you would rather describe the personality entirely in free form. You do **not** need `Other: true` just to use `custom` — `custom` can always be added on top of preset adjectives to refine them further.

### Role

Open `agent_settings/role.yaml` and describe what the agent is:

~~~yaml
value: Restaurant Reservations Agent
additional_info: Takes table reservations for Maison restaurant
custom: ""
~~~

### Rules

Open `agent_settings/rules.txt`. Rules give the agent standing instructions that apply across every turn. Add the following:

~~~text
You are the reservations agent for Maison, an upscale French restaurant.
Always be warm and welcoming.
When a caller wants to make a reservation, use {{fn:start_booking_flow}} to begin the booking process.
Never tell the caller their reservation is confirmed until the booking flow has completed.
~~~

`{{fn:start_booking_flow}}` references a global function you will define later. The model uses these references to understand when to call them.

!!! warning "`{{fn:...}}` only works for global functions"

    Only functions in the top-level `functions/` directory can be referenced with `{{fn:...}}` in rules and topics. Flow function steps (files inside `flows/{name}/function_steps/`) are called automatically by the flow — they cannot be referenced this way.

## Part 3 — Define the entities

Entities are the structured data values the agent can collect from a caller. Create `config/entities.yaml`:

~~~yaml
entities:
  - name: customer_name
    description: The caller's full name for the reservation
    entity_type: name_config
    config: {}

  - name: party_size
    description: Number of guests for the reservation, between 1 and 20
    entity_type: numeric
    config:
      has_decimal: false
      has_range: true
      min: 1
      max: 20

  - name: reservation_date
    description: The date the caller wants to dine, such as "Friday" or "the 15th"
    entity_type: date
    config:
      relative_date: true

  - name: reservation_time
    description: The time the caller wants to dine, such as "7pm" or "half past seven"
    entity_type: time
    config:
      enabled: true
      start_time: "12:00"
      end_time: "22:00"
~~~

These four entities will be collected across the steps of the booking flow.

!!! info "`relative_date` and round-trips"

    The `relative_date: true` field is valid and is sent to the platform on push. However, date entity config may not be returned by the platform on pull, so after a `poly pull` you may see `config: {}` for the `reservation_date` entity. This is a known platform behavior and does not affect how the entity works at runtime.

!!! info "Automatic ASR biasing"

    When a default step lists these entities in `extracted_entities`, the platform automatically configures speech recognition to be more accurate for that kind of input — dates, times, numbers, and names.

## Part 4 — Build the booking flow

Flows live under `flows/`. Each flow gets its own directory. The directory name must be the snake_case version of the flow's `name` field — so a flow named `Booking Flow` must live in `flows/booking_flow/`.

Create the directory structure:

~~~bash
mkdir -p flows/booking_flow/steps
mkdir -p flows/booking_flow/function_steps
~~~

### Flow configuration

Create `flows/booking_flow/flow_config.yaml`:

~~~yaml
name: Booking Flow
description: Collects reservation details and confirms a table booking
start_step: Collect Name
~~~

### Step 1 — Collect name

Create `flows/booking_flow/steps/collect_name.yaml`:

~~~yaml
step_type: default_step
name: Collect Name
prompt: |
  ## Collect the caller's name

  Ask the caller for the name the reservation should be under. Be warm and conversational.
  Do not repeat the question if the caller has already given a name.

  Collected so far: {{entity:customer_name}}
conditions:
  - name: has_name
    condition_type: step_condition
    description: Caller has provided their name
    required_entities:
      - customer_name
    child_step: Collect Party Size
extracted_entities:
  - customer_name
~~~

### Step 2 — Collect party size

Create `flows/booking_flow/steps/collect_party_size.yaml`:

~~~yaml
step_type: default_step
name: Collect Party Size
prompt: |
  ## Collect party size

  Ask how many guests will be dining. The restaurant accepts between 1 and 20 guests.
  If the caller gives a number outside that range, explain politely and ask again.

  Name on reservation: {{entity:customer_name}}
  Party size so far: {{entity:party_size}}
conditions:
  - name: has_party_size
    condition_type: step_condition
    description: Caller has given a valid party size
    required_entities:
      - customer_name
      - party_size
    child_step: Collect Date
extracted_entities:
  - party_size
~~~

### Step 3 — Collect date and time

Create `flows/booking_flow/steps/collect_date.yaml`:

~~~yaml
step_type: default_step
name: Collect Date
prompt: |
  ## Collect reservation date and time

  Ask the caller when they would like to dine. Collect both the date and the time.
  Maison is open for lunch from noon and for dinner until 10pm.

  Party: {{entity:customer_name}}, {{entity:party_size}} guests
  Date collected: {{entity:reservation_date}}
  Time collected: {{entity:reservation_time}}
conditions:
  - name: has_date_and_time
    condition_type: step_condition
    description: Caller has given both date and time
    required_entities:
      - customer_name
      - party_size
      - reservation_date
      - reservation_time
    child_step: confirm_booking
extracted_entities:
  - reservation_date
  - reservation_time
~~~

`child_step: confirm_booking` uses the Python filename (without `.py`) rather than a step name — that is the convention for pointing to a function step.

### Step 4 — Confirm booking (function step)

Function steps are deterministic Python. They run without model interpretation. Create `flows/booking_flow/function_steps/confirm_booking.py`:

~~~python
from _gen import *  # <AUTO GENERATED>


def confirm_booking(conv: Conversation, flow: Flow):
    """Confirm the reservation and store the details."""
    name = conv.entities.customer_name.value if conv.entities.customer_name else "Guest"
    size = conv.entities.party_size.value if conv.entities.party_size else "?"
    date = conv.entities.reservation_date.value if conv.entities.reservation_date else "?"
    time = conv.entities.reservation_time.value if conv.entities.reservation_time else "?"

    # Store the confirmed details in conversation state
    conv.state.booking_confirmed = True

    # Exit the flow and return a context string for the model
    conv.exit_flow()
    return f"Booking confirmed: table for {size} under {name} on {date} at {time}."
~~~

After this function runs, the model receives the returned context string and uses it to continue the conversation.

## Part 5 — Add a global function to enter the flow

Global functions live in the top-level `functions/` directory. Create `functions/start_booking_flow.py`:

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description("Start the table reservation process for Maison restaurant")
def start_booking_flow(conv: Conversation):
    """Enter the booking flow."""
    conv.goto_flow("Booking Flow")
~~~

This is what `{{fn:start_booking_flow}}` in your rules resolves to. When the model decides to call it, the agent enters the booking flow at its start step.

## Part 6 — Add a start function

The start function runs once at the beginning of every call, before the first user input. Use it to initialize state.

!!! warning "`start_function.py` may already exist"

    Projects built via Quick Agent Setup in Agent Studio often ship with a pre-populated `start_function.py` containing significant initialization logic. If the file already exists, add your initialization code to it rather than replacing it.

Create or update `functions/start_function.py`:

~~~python
from _gen import *  # <AUTO GENERATED>


def start_function(conv: Conversation):
    """Initialize conversation state at call start."""
    conv.state.booking_confirmed = False
~~~

## Part 7 — Add a topic

Topics tell the agent what kinds of caller utterances map to which actions. Create `topics/Make a Reservation.yaml`:

~~~yaml
enabled: true
content: The caller wants to make a table reservation at Maison restaurant.
example_queries:
  - I'd like to book a table
  - Can I make a reservation?
  - Do you have any tables available on Saturday?
  - I want to reserve a table for four
actions: Use {{fn:start_booking_flow}} to begin collecting the reservation details.
~~~

The model uses `content` and `example_queries` to understand when this topic applies, and `actions` to know what to do.

## Part 8 — Tune speech recognition

Voice agents listen on a noisy channel, and domain-specific vocabulary is usually the first thing ASR gets wrong. The ADK exposes two speech-recognition resources that do not require any code: **keyphrase boosting** and **transcript corrections**. Both live under `voice/speech_recognition/`.

### Keyphrase boosting

Create `voice/speech_recognition/keyphrase_boosting.yaml`:

~~~yaml
keyphrases:
  - keyphrase: Maison
    level: maximum
  - keyphrase: reservation
    level: boosted
  - keyphrase: party of
    level: boosted
~~~

The recognizer biases toward these phrases when it is uncertain. Boost the brand name at `maximum` so the agent never mis-hears it, and apply lighter boosts to the phrases that disambiguate booking intent.

### Transcript corrections

Spoken times and numbers often come through in forms that are hard to parse. Create `voice/speech_recognition/transcript_corrections.yaml`:

~~~yaml
corrections:
  - name: Time normalization
    description: Collapse common spoken time forms
    regular_expressions:
      - regular_expression: half past (\d{1,2})
        replacement: \1:30
        replacement_type: partial
      - regular_expression: quarter past (\d{1,2})
        replacement: \1:15
        replacement_type: partial
      - regular_expression: quarter to (\d{1,2})
        replacement: \1:45
        replacement_type: partial
~~~

These rules are applied after the recognizer returns text but before the model sees it. They only touch the transcript — the caller's audio is unaffected.

See the [speech recognition reference](../reference/speech_recognition.md) for the full field list, interaction styles, and barge-in settings.

## Part 9 — Adjust how the agent speaks

Response control sits on the other side of the conversation: it shapes what the agent says before TTS. For a French-brand restaurant, the most common issue is pronunciation. Create `voice/response_control/pronunciations.yaml`:

~~~yaml
pronunciations:
  - regex: "\\bMaison\\b"
    replacement: May-zon
    case_sensitive: false
    description: Ensure the restaurant name is spoken in the intended French style
~~~

You can add entries for any word or phrase the TTS mispronounces. See the [response control reference](../reference/response_control.md) for the full field list, including phrase filtering.

## Part 10 — Review your changes

Before pushing, check what has changed:

~~~bash
poly status
~~~

~~~text
╭─────────────── Project Status ────────────────╮
│  Region          <region>                      │
│  Account ID      <account_id>                  │
│  Project ID      <project_id>                  │
│  Last Pulled     2026-04-21T09:15:00           │
│  Current Branch  booking-flow                  │
╰───────────────────────────────────────────────╯
~~~

~~~text

New files:
  /Users/yourname/maison/<account_id>/<project_id>/config/entities.yaml
  /Users/yourname/maison/<account_id>/<project_id>/flows/booking_flow/flow_config.yaml
  /Users/yourname/maison/<account_id>/<project_id>/flows/booking_flow/steps/collect_name.yaml
  /Users/yourname/maison/<account_id>/<project_id>/flows/booking_flow/steps/collect_party_size.yaml
  /Users/yourname/maison/<account_id>/<project_id>/flows/booking_flow/steps/collect_date.yaml
  /Users/yourname/maison/<account_id>/<project_id>/flows/booking_flow/function_steps/confirm_booking.py
  /Users/yourname/maison/<account_id>/<project_id>/functions/start_booking_flow.py
  /Users/yourname/maison/<account_id>/<project_id>/functions/start_function.py
  /Users/yourname/maison/<account_id>/<project_id>/topics/Make a Reservation.yaml
  /Users/yourname/maison/<account_id>/<project_id>/voice/speech_recognition/keyphrase_boosting.yaml
  /Users/yourname/maison/<account_id>/<project_id>/voice/speech_recognition/transcript_corrections.yaml
  /Users/yourname/maison/<account_id>/<project_id>/voice/response_control/pronunciations.yaml
  /Users/yourname/maison/<account_id>/<project_id>/variables/booking_confirmed
~~~

!!! info "Variables in `poly status`"

    The `variables/` entries appear because the ADK scans your function code for `conv.state.*` assignments and tracks each one as a variable. These entries are virtual — they do not correspond to files on disk and are not something you need to create or manage. This is expected output.

To see the exact content difference for any file, run `poly diff`:

~~~bash
poly diff
~~~

This shows a unified diff of all local changes against the remote state, useful for reviewing before you push and for producing a diff for a code review.

## Part 11 — Push to Agent Studio

Push the changes to your branch in Agent Studio:

~~~bash
poly push
~~~

~~~text
Pushing local changes for <account_id>/<project_id>...
Pushed <account_id>/<project_id> to Agent Studio.
~~~

The agent is now deployed to the `booking-flow` branch. Sandbox remains on `main` and is unaffected.

## Part 12 — Merge and test

`poly chat` connects to the **main branch** of your sandbox — not a feature branch. To test the booking flow, merge `booking-flow` to `main` in the Agent Studio UI first.

!!! note "Merging requires Agent Studio"

    There is no `poly merge` command. Open your project in Agent Studio, switch to the `booking-flow` branch, and merge it through the interface. Once merged, the changes are live in sandbox.

After merging, run `poly chat` against the sandbox environment:

~~~bash
poly chat --environment sandbox
~~~

~~~text
Starting chat for <account_id>/<project_id> (sandbox)...
Type your message. Press Ctrl+C to exit.

Agent: Welcome to Maison. How can I help you today?

You: I'd like to book a table for this Saturday

Agent: Of course! I'd be happy to help with that. Could I take the name for the reservation?

You: It's under Sarah Chen

Agent: Thank you, Sarah. And how many guests will be dining?

You: Just two of us

Agent: Perfect. And what time were you thinking for Saturday?

You: Around 7:30 in the evening

Agent: Wonderful. Let me confirm that — a table for 2 under Sarah Chen this Saturday at 7:30pm. Does that sound right?

You: Yes, that's perfect

Agent: Your reservation is confirmed. We look forward to welcoming you to Maison on Saturday. Is there anything else I can help you with?
~~~

!!! tip "Useful chat flags"

    - `poly chat --state` — prints `conv.state` after each turn so you can verify values are being set correctly
    - `poly chat --functions` — shows which functions the model called each turn
    - `poly chat --push` — pushes your latest changes before starting the session, useful during rapid iteration

!!! warning "`poly chat --push` can create conflict markers"

    If the remote state has diverged from your local copy, `poly chat --push` may write merge-conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) directly into your YAML files. If this happens, open the affected file, resolve the conflict by hand, and push again before continuing.

## Part 13 — After the merge

After merging in Agent Studio, switch back to `main` locally:

~~~bash
poly branch switch main
poly pull
~~~

Pulling after a merge keeps your local copy in sync with the normalized remote state.

!!! info "YAML key order changes after a round-trip"

    After a push and pull, the platform returns YAML with keys in alphabetical order. Fields you wrote in logical order (such as `name:` before `description:`) will be reordered. This is cosmetic and does not affect behavior, but `poly diff` will show changes after the first round-trip even when the content is the same.

## What to explore next

This tutorial covered a single flow with four steps. From here you can extend the agent in several directions.

**Multi-location support with variants**: If Maison has multiple locations, use `config/variant_attributes.yaml` to define per-location phone numbers, opening hours, and capacity limits. The agent reads the right values for each location at runtime using `{{attr:...}}` in prompts and `conv.variant.attribute_name` in code.

**Handling cancellations**: Add a second topic and flow for callers who want to cancel or modify a reservation. The flow structure is similar — collect a name or reference, confirm the record, then update state.

**External API calls**: Replace the stub booking logic in `confirm_booking.py` with a real HTTP call to your reservation system. Function steps are the right place for this — they run deterministically and can store results in `conv.state` for the model to reference.

**Richer error paths**: Add an explicit error step to the flow for when the booking cannot be completed. Route to it from `confirm_booking.py` using `flow.goto_step("Error")` and return a context string explaining what happened.

**SMS confirmations and call handoffs**: Both are supported by the ADK. See [SMS templates](../reference/sms.md) to send a confirmation when a booking is made, and [handoffs](../reference/handoffs.md) to transfer a caller to a human for special requests. Both resources are ADK-only — they do not have a matching editor in the Agent Studio UI, and template references to them (`{{twilio_sms:...}}`, `{{ho:...}}`) must live in files you manage through `poly push`.

## Related pages

<div class="grid cards" markdown>

-   **Flows**

    ---

    Full reference for flow configuration, step types, and conditions.
    [Open flows](../reference/flows.md)

-   **Entities**

    ---

    All entity types and their configuration fields.
    [Open entities](../reference/entities.md)

-   **Functions**

    ---

    How global functions, transition functions, and function steps differ.
    [Open functions](../reference/functions.md)

-   **Topics**

    ---

    How topics connect caller intent to agent actions.
    [Open topics](../reference/topics.md)

-   **Speech recognition**

    ---

    Keyphrase boosting, transcript corrections, and ASR settings.
    [Open speech recognition](../reference/speech_recognition.md)

-   **Response control**

    ---

    Pronunciations and phrase filtering for spoken output.
    [Open response control](../reference/response_control.md)

-   **Variants**

    ---

    Per-location configuration without duplicating your project.
    [Open variants](../reference/variants.md)

</div>
