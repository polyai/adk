---
title: Build a restaurant booking agent
description: A complete walkthrough building a voice agent that takes table reservations — covering flows, entities, functions, topics, SMS, and testing.
---

# Build a restaurant booking agent

<p class="lead">
This tutorial builds a complete voice agent for a restaurant. By the end you will have a working agent that greets callers, collects a reservation, confirms the details, and sends an SMS confirmation.
</p>

You will use the ADK to define, iterate on, and test the agent entirely from your terminal.

## What you will build

The agent handles calls to **Maison**, a fictional restaurant. When a caller asks to make a reservation, the agent:

1. Enters a booking flow and collects the caller's name, party size, and preferred date and time
2. Confirms the details back to the caller
3. Stores the booking and sends an SMS confirmation
4. Offers to transfer to the host team if the caller has any special requests

## What you will learn

This tutorial covers:

- initializing a project and pulling its configuration
- working on a branch
- defining entities for structured data collection
- building a multi-step flow with default steps and a function step
- writing a start function and a booking function
- triggering a flow from a topic
- configuring an SMS template
- previewing changes with `poly status` and `poly diff`
- pushing and testing with `poly chat`

## Prerequisites

Before you start:

- you have Python 3.14 or later installed
- you have `uv` installed
- you have installed the ADK: `pip install polyai-adk`
- you have a PolyAI API key and access to an Agent Studio project

Verify the CLI is available:

~~~bash
poly --version
~~~

## Part 1 — Set up the project

### Initialize

Create a directory for your project and run `poly init` inside it:

~~~bash
mkdir maison && cd maison
poly init
~~~

`poly init` is interactive. It prompts you to select your region, account, and project in turn. Use the arrow keys to navigate, or start typing to filter the list.

~~~text
? Select Region  us-1
? Select Account  acme-corp
? Select Project  maison-reservations

Initializing project acme-corp/maison-reservations...
✓ Project initialized at ~/projects/maison
~~~

This creates a `project.yaml` file in your directory:

~~~yaml
project_id: maison-reservations
account_id: acme-corp
region: us-1
~~~

### Pull the current configuration

Pull the project's current state from Agent Studio:

~~~bash
poly pull
~~~

~~~text
Pulling project acme-corp/maison-reservations...
✓ Pulled acme-corp/maison-reservations
~~~

Your directory now contains the full project configuration as YAML and Python files. The structure looks like this:

~~~text
maison/
├── project.yaml
├── agent_settings/
│   ├── personality.yaml
│   ├── role.yaml
│   └── rules.txt
├── config/
│   ├── entities.yaml
│   ├── handoffs.yaml
│   ├── sms_templates.yaml
│   └── variant_attributes.yaml
├── flows/
├── functions/
├── topics/
└── _gen/
~~~

The `_gen/` directory contains auto-generated platform code. Do not edit it — it is overwritten on every pull.

### Create a working branch

It is good practice to make changes on a branch. Create one now:

~~~bash
poly branch create booking-flow
~~~

~~~text
✓ Created and switched to new branch 'booking-flow'.
~~~

You are now on the `booking-flow` branch. Any changes you push will go to that branch in Agent Studio, leaving `main` (and Sandbox) untouched.

!!! tip "Check which branch you are on"

    Run `poly status` at any time to see your current branch, region, and when the project was last pulled.

## Part 2 — Define the agent

### Personality

Open `agent_settings/personality.yaml`. Adjust the adjectives to suit the Maison brand:

~~~yaml
adjectives:
  Warm: true
  Attentive: true
  Professional: true
custom: ""
~~~

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
If a caller has special requests or accessibility needs, offer to transfer them to the host team using {{ho:host_team}}.
Never tell the caller their reservation is confirmed until the booking flow has completed.
~~~

Notice `{{fn:...}}` and `{{ho:...}}` — these reference functions and handoffs you will define later. The model uses these references to understand when to call them.

## Part 3 — Define the entities

Entities are the structured data values the agent can collect from a caller. Open `config/entities.yaml` and replace its contents with:

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

!!! info "Automatic ASR biasing"

    When a default step lists these entities in `extracted_entities`, the platform automatically configures speech recognition to be more accurate for that kind of input — dates, times, numbers, and names.

## Part 4 — Build the booking flow

Flows live under `flows/`. Each flow gets its own directory. Create the directory structure for the booking flow:

~~~bash
mkdir -p flows/booking/steps
mkdir -p flows/booking/function_steps
mkdir -p flows/booking/functions
~~~

### Flow configuration

Create `flows/booking/flow_config.yaml`:

~~~yaml
name: Booking Flow
description: Collects reservation details and confirms a table booking
start_step: Collect Name
~~~

### Step 1 — Collect name

Create `flows/booking/steps/collect_name.yaml`:

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

Create `flows/booking/steps/collect_party_size.yaml`:

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

Create `flows/booking/steps/collect_date.yaml`:

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

Notice that `child_step: confirm_booking` uses the Python filename (without `.py`) rather than a step name — that is the convention for pointing to a function step.

### Step 4 — Confirm booking (function step)

Function steps are deterministic Python. They run without model interpretation. Create `flows/booking/function_steps/confirm_booking.py`:

~~~python
from _gen import *  # <AUTO GENERATED>


def confirm_booking(conv: Conversation, flow: Flow):
    """Confirm the reservation and send an SMS."""
    name = conv.entities.customer_name.value if conv.entities.customer_name else "Guest"
    size = conv.entities.party_size.value if conv.entities.party_size else "?"
    date = conv.entities.reservation_date.value if conv.entities.reservation_date else "?"
    time = conv.entities.reservation_time.value if conv.entities.reservation_time else "?"

    # Store the confirmed details in conversation state
    conv.state.booking_name = name
    conv.state.booking_size = str(size)
    conv.state.booking_date = str(date)
    conv.state.booking_time = str(time)
    conv.state.booking_confirmed = True

    # Exit the flow and return a context string for the model
    conv.exit_flow()
    return (
        f"Booking confirmed: table for {size} under {name} on {date} at {time}. "
        "Offer to send the caller an SMS confirmation."
    )
~~~

After this function runs, the model receives the returned context string and uses it to continue the conversation — in this case, it will offer to send the SMS.

## Part 5 — Add a global function to enter the flow

Global functions live in the top-level `functions/` directory. Create `functions/start_booking_flow.py`:

~~~python
from _gen import *  # <AUTO GENERATED>


@func_description("Start the table reservation process for Maison restaurant")
def start_booking_flow(conv: Conversation):
    """Enter the booking flow."""
    conv.goto_flow("Booking Flow")
~~~

This function is what `{{fn:start_booking_flow}}` in your rules resolves to. When the model decides to call it, the agent enters the booking flow at its start step.

## Part 6 — Add a start function

The start function runs once at the beginning of every call, before the first user input. Use it to initialize state. Create `functions/start_function.py`:

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

## Part 8 — Add an SMS template

When the booking is confirmed, the agent will offer to send an SMS with the details. Define the template in `config/sms_templates.yaml`:

~~~yaml
sms_templates:
  - name: booking_confirmation
    text: >-
      Hi {{vrbl:booking_name}}, your table for {{vrbl:booking_size}} at Maison
      is confirmed for {{vrbl:booking_date}} at {{vrbl:booking_time}}.
      We look forward to seeing you.
    env_phone_numbers:
      sandbox: ""
      pre_release: ""
      live: "+15551234567"
~~~

The `{{vrbl:...}}` placeholders pull from `conv.state` values that were set in the `confirm_booking` function step.

Reference the template in `agent_settings/rules.txt` by adding:

~~~text
After a booking is confirmed, offer to send an SMS confirmation using {{twilio_sms:booking_confirmation}}.
~~~

## Part 9 — Add a handoff

If a caller has special requests, the agent should be able to transfer them to the host team. Define the handoff in `config/handoffs.yaml`:

~~~yaml
handoffs:
  - name: host_team
    description: Transfer to the Maison host team for special requests and accessibility needs
    is_default: false
    sip_config:
      method: refer
      phone_number: "+15559876543"
~~~

## Part 10 — Review your changes

Before pushing, check what has changed:

~~~bash
poly status
~~~

~~~text
╭─────────────── Project Status ────────────────╮
│  Region          us-1                          │
│  Account ID      acme-corp             │
│  Project ID      maison-reservations              │
│  Last Pulled     2026-04-21T09:15:00           │
│  Current Branch  booking-flow                  │
╰───────────────────────────────────────────────╯

New files:
  flows/booking/flow_config.yaml
  flows/booking/steps/collect_name.yaml
  flows/booking/steps/collect_party_size.yaml
  flows/booking/steps/collect_date.yaml
  flows/booking/function_steps/confirm_booking.py
  functions/start_booking_flow.py
  functions/start_function.py
  topics/Make a Reservation.yaml
~~~

To see the exact content difference for any file, run `poly diff`:

~~~bash
poly diff
~~~

This shows a unified diff of all local changes against the remote state. It is useful for reviewing before you push, and for producing a diff for a code review.

## Part 11 — Push to Agent Studio

Push the changes to your branch in Agent Studio:

~~~bash
poly push
~~~

~~~text
Pushing local changes for acme-corp/maison-reservations...
✓ Pushed acme-corp/maison-reservations to Agent Studio.
~~~

The agent is now deployed to the `booking-flow` branch. Sandbox remains on `main` and is unaffected.

## Part 12 — Test with poly chat

Test the agent against your branch:

~~~bash
poly chat
~~~

Because you are on the `booking-flow` branch (not `main`), `poly chat` connects to the branch's deployed state by default.

~~~text
Starting chat for acme-corp/maison-reservations branch=booking-flow...
Type your message. Press Ctrl+C to exit.

Agent: Welcome to Maison. How can I help you today?

You: I'd like to book a table for this Saturday

Agent: Of course! I'd be happy to help with that. Could I take the name for the reservation?

You: It's under Sarah Chen

Agent: Thank you, Sarah. And how many guests will be dining?

You: Just two of us

Agent: Perfect. And what time were you thinking for Saturday?

You: Around 7:30 in the evening

Agent: Wonderful. Let me confirm that for you — a table for 2 under Sarah Chen this Saturday at 7:30pm. Does that sound right?

You: Yes, that's perfect

Agent: Your reservation is confirmed. Would you like me to send you an SMS confirmation?

You: Please

Agent: Done — you'll receive a confirmation shortly. We look forward to welcoming you to Maison on Saturday. Is there anything else I can help you with?
~~~

!!! tip "Useful chat flags"

    - `poly chat --show-state` — prints `conv.state` after each turn so you can verify values are being set correctly
    - `poly chat --show-functions` — shows which functions the model called each turn
    - `poly chat --push` — pushes your latest changes before starting the session, useful during rapid iteration

## Part 13 — Merge to main

When you are happy with the agent on the branch, merge it to `main` in Agent Studio. The ADK does not have a `poly merge` command — merging happens in the Agent Studio UI.

After merging, switch back to `main` locally:

~~~bash
poly branch switch main
poly pull
~~~

Pulling after a merge keeps your local copy in sync with the normalized remote state.

## What to explore next

This tutorial covered a single flow with four steps. From here you can extend the agent in several directions.

**Multi-location support with variants**: If Maison has multiple locations, you can use `config/variant_attributes.yaml` to define per-location phone numbers, opening hours, and capacity limits. The agent then reads the right values for each location at runtime using `{{attr:...}}` in prompts and `conv.variant.attribute_name` in code.

**Handling no-shows and cancellations**: Add a second topic and flow for callers who want to cancel or modify a reservation. The confirmation flow is similar — collect a name or reference, confirm the record, then update state.

**External API calls**: Replace the stub booking logic in `confirm_booking.py` with a real HTTP call to your reservation system. Function steps are the right place for this — they run deterministically and can store results in `conv.state` for the model to reference.

**Richer error paths**: Add an explicit error step to the flow for when the booking cannot be completed — for example, when the requested time is unavailable. Route to it from `confirm_booking.py` using `flow.goto_step("Error")` and return a context string explaining what happened.

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

-   **SMS templates**

    ---

    Defining reusable SMS messages and populating them with state variables.
    [Open SMS templates](../reference/sms.md)

-   **Variants**

    ---

    Per-location configuration without duplicating your project.
    [Open variants](../reference/variants.md)

</div>
