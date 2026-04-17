---
title: Build an agent with the ADK
description: Follow the end-to-end workflow for going from a blank Agent Studio project to a production-ready voice agent with the PolyAI ADK.
---

This guide walks through how to go from a blank slate to a production-ready voice agent using **Agent Studio**, the **PolyAI ADK**, and optionally a coding tool such as **Claude Code**.

There are two common ways to build with the ADK:

| Workflow | Description |
|---|---|
| **CLI workflow** | The hands-on developer path. You run the commands yourself, edit files locally, and push changes back to Agent Studio. |
| **AI-agent workflow** | You provide a brief; a coding tool uses the ADK to generate and push the project files on your behalf. |

<div class="grid cards" markdown>

-   **You provide context**

    ---

    Gather the requirements, business rules, API information, and reference material.

-   **The agent or developer builds**

    ---

    Using the ADK, the project files are created, edited, validated, and prepared locally.

-   **Agent Studio hosts and deploys**

    ---

    The generated work is pushed back into Agent Studio, where it can be reviewed, merged, and deployed.

</div>

## Architecture at a glance

| Role | Responsibility |
|---|---|
| **You** | Provide requirements, project context, and business rules |
| **PolyAI ADK** | Connect the local project to Agent Studio and manage sync, validation, and tooling |
| **Coding agent** | Optionally generate and update files using the ADK |
| **Agent Studio** | Host, preview, review, merge, and deploy the agent |

## Local project structure

When an Agent Studio project is linked locally, it follows this general structure:

~~~text
<account>/<project>/
├── agent_settings/
│   ├── personality.yaml
│   ├── role.yaml
│   ├── rules.txt
│   └── experimental_config.json
├── config/
│   ├── entities.yaml
│   ├── handoffs.yaml
│   ├── sms_templates.yaml
│   └── variant_attributes.yaml
├── voice/
│   ├── configuration.yaml
│   ├── speech_recognition/
│   │   ├── asr_settings.yaml
│   │   ├── keyphrase_boosting.yaml
│   │   └── transcript_corrections.yaml
│   └── response_control/
│       ├── pronunciations.yaml
│       └── phrase_filtering.yaml
├── chat/                               # Optional - chat channel settings
│   └── configuration.yaml
├── flows/
│   └── {flow_name}/
│       ├── flow_config.yaml
│       ├── steps/
│       │   └── {step_name}.yaml
│       ├── function_steps/
│       │   └── {function_step}.py
│       └── functions/
│           └── {function_name}.py
├── functions/
│   ├── start_function.py
│   ├── end_function.py
│   └── {function_name}.py
├── topics/
│   └── {topic_name}.yaml
└── project.yaml
~~~

This structure mirrors the parts of the agent that Agent Studio understands: settings, flows, functions, topics, channel configuration, and supporting resources.

## Workflow 1 - CLI workflow

The CLI workflow is the manual developer path. You use the ADK directly, edit the project locally, and push changes back to Agent Studio.

### Step 1 - Initialize your project

Link a local folder to an existing Agent Studio project. The agent must already exist in Agent Studio.

~~~bash
poly init
poly init --region <region> --account_id <account_id> --project_id <project_id>
~~~

This creates the local project structure and writes the metadata needed to connect the folder to Agent Studio.

### Step 2 - Pull remote config and set up the environment

Pull the current configuration into your local project.

~~~bash
poly pull
poly pull -f
~~~

At this point, configure any API keys or environment variables needed for the project.

!!! note "Run commands from the project folder"

    All CLI commands should be run from within the local project folder, unless you explicitly use the relevant path flag.

### Step 3 - Run the agent locally

Start an interactive chat session to confirm the connection works and inspect runtime behavior.

!!! warning "Chat runs against main on Sandbox"

    `poly chat` connects to the **main branch** of your Sandbox environment in Agent Studio — not your local files, and not your current feature branch. At this stage it is useful for confirming the connection works. To chat against your own changes, push and merge your branch in Agent Studio first.

~~~bash
poly chat
poly chat --environment sandbox --channel voice
poly chat --functions --flows --state
~~~

### Step 4 - Review the docs and understand the SDK

Use the CLI docs command to inspect the available resources and learn how they fit together.

~~~bash
poly docs --all
poly docs flows functions topics
~~~

Resource-specific documentation is available in the reference section:
[agent settings](../reference/agent_settings.md),
[voice settings](../reference/voice_settings.md),
[chat settings](../reference/chat_settings.md),
[flows](../reference/flows.md),
[functions](../reference/functions.md),
[topics](../reference/topics.md),
[entities](../reference/entities.md),
[handoffs](../reference/handoffs.md),
[variants](../reference/variants.md),
[SMS templates](../reference/sms.md),
[variables](../reference/variables.md),
[speech recognition](../reference/speech_recognition.md),
[response control](../reference/response_control.md), and
[experimental config](../reference/experimental_config.md).

### Step 5 - Customize the agent

This is the core build phase. Create a branch, edit resources locally, track changes, and push them back.

!!! tip "Read the anti-patterns page first"

    Before editing, review the [common anti-patterns](../concepts/anti-patterns.md) to avoid flow control bugs, logging noise, and prompt logic mistakes that are easy to introduce but hard to debug.

#### Branching

~~~bash
poly branch create my-feature
poly branch switch my-feature
poly branch current
poly branch list
~~~

#### Functions

Create or modify backend functions the agent calls at runtime. See the [functions reference](../reference/functions.md) for the full API.

Typical locations include:

- global functions under the functions directory
- lifecycle hooks such as start and end functions
- flow-scoped functions
- function steps inside flows

#### Topics

Add or edit [knowledge-base topics](../reference/topics.md) used for retrieval.

#### Agent settings

Update the [personality, role, and rules](../reference/agent_settings.md) that define the agent’s global behavior.

#### Flows

Build [conversation flows](../reference/flows.md), including prompts, step transitions, [entities](../reference/entities.md), and function steps.

#### Channel-specific settings

Adjust greeting messages, disclaimers, and style prompts for [voice](../reference/voice_settings.md) and [chat](../reference/chat_settings.md).

#### Handoffs, SMS, and variants

Define [escalation paths](../reference/handoffs.md), [SMS templates](../reference/sms.md), and [per-variant configuration](../reference/variants.md).

#### ASR and response control

Tune [speech recognition](../reference/speech_recognition.md) and control [TTS behavior](../reference/response_control.md).

#### Experimental config

Enable or tune [experimental features](../reference/experimental_config.md) where needed.

### Step 6 - Track and validate changes

Inspect the local changes before pushing.

~~~bash
poly status
poly diff
poly diff <file>
poly validate
poly format
poly revert --all
poly revert <file>
~~~

### Step 7 - Push changes

Push the local changes back to Agent Studio.

~~~bash
poly push
poly push --dry-run
poly push -f
poly push --skip-validation
~~~

### Step 8 - Test against sandbox

Once your branch is merged in Agent Studio, test the agent by chatting with it against the Sandbox environment.

!!! warning "Merge before chatting"

    `poly chat` connects to the **main branch** of your Sandbox — not your feature branch. Push your changes with `poly push`, merge the branch in Agent Studio, then run `poly chat`.

~~~bash
poly chat --environment sandbox
poly chat --environment sandbox --functions --flows
~~~

### Step 9 - Iterate on quality

Review, refine, and test again. You can also use the review command to share diffs with teammates.

~~~bash
poly review
poly review --before main --after my-feature
~~~

Make test calls, inspect transcripts, refine prompts, flows, and functions, and then re-push.

### Step 10 - Deploy to production

Once the changes are pushed and validated, merge the branch in Agent Studio and deploy the project.

!!! note "Merging requires the Agent Studio web UI"
    There is no `poly merge` command. To merge a branch, open the project in Agent Studio, switch to the branch, and merge it through the interface. After merging, run `poly chat --environment sandbox` to test.

### Step 11 - Monitor performance

Use Agent Studio analytics to monitor containment, CSAT, handle time, and flagged transcripts. Pull changes back locally as needed and continue iterating.

## Workflow 2 - AI-agent workflow

The AI-agent workflow uses a coding tool such as **Claude Code** to run the same development loop on your behalf.

<div class="grid cards" markdown>

-   **You provide the brief**

    ---

    Requirements, business rules, integrations, and API documentation.

-   **The coding tool generates the project**

    ---

    It uses the ADK to read documentation, generate files, and push the result.

-   **You review and deploy**

    ---

    Agent Studio remains the place where the work is checked, merged, and deployed.

</div>

!!! info "No manual flow-building required"

    In this workflow, the coding tool generates the project files. Agent Studio is where the output is reviewed, tested, and deployed.

### Step 1 - Gather requirements

Collect the project context before you begin.

Include anything the coding tool will need to produce a working agent:

- API endpoint URLs
- business rules
- use-case descriptions
- internal notes or emails
- reference material
- links to API documentation

The more complete and structured your input is, the less correction the output requires.

!!! tip "Front-load the context"

    Gather everything up front. Providing context piecemeal produces piecemeal output.

### Step 2 - Create a new project in Agent Studio

Open **Agent Studio** and create a brand-new project.

The project starts empty:

- no knowledge base
- no flows
- no configuration

That blank starting point is intentional. The coding tool populates the project in later steps.

!!! note "Think of Agent Studio as the deployment target"

    Agent Studio is where the project lives, but the coding tool generates the actual content.

### Step 3 - Start the coding tool via the CLI

Open your terminal and start the coding tool.

At this stage:

- the ADK must already be installed
- the Agent Studio project must already exist
- the coding tool should initialize and link the project using the ADK

~~~bash
poly init --region <region> --account_id <account_id> --project_id <project_id>
poly pull
~~~

The ADK acts as the bridge between your local environment and Agent Studio. It lets the coding tool read from and write back to the project.

!!! tip "Run `poly docs --all` before generating any files"
    Immediately after pulling, run `poly docs --all` to produce a complete resource reference. Without it, a coding agent has no schema context for resource structure and field names, and will hallucinate them. This should be the first thing the coding tool does after `poly pull`.

### Step 4 - Give the coding tool its context

Provide the coding tool with the information you gathered earlier.

Include:

- project-specific requirements
- the URL to the business’s public API documentation
- relevant internal context
- useful patterns or best practices from previous projects

Use the docs command to generate a reference file the coding tool can read:

~~~bash
poly docs --all
~~~

### Step 5 - Generate the project files

Once the context is in place, the coding tool generates the project files.

This produces the assets the agent needs, including:

<div class="grid cards" markdown>

-   **Conversation flows**

    ---

    Dialog logic and routing for the agent.

-   **Callable functions**

    ---

    Backend functions used during calls.

-   **Knowledge base entries**

    ---

    Information the agent can reference when answering questions.

-   **API integrations**

    ---

    Both real API connections and mock endpoints for testing.

</div>

The generated files follow ADK structure and are ready to push to Agent Studio.

### Step 6 - Push to Agent Studio

Once the files are generated, use the ADK to push them to Agent Studio.

A new branch is created in the project so the generated work can be reviewed safely before anything goes live.

When you switch to that branch in Agent Studio, you should see the generated changes, such as:

- updated greeting messages
- new knowledge base entries
- a built tracking flow
- real and mock API integrations

!!! tip "Use the branch review step"

    The branch-based workflow makes it possible to inspect what was generated before merging it into the main project.

### Step 7 - Review, merge, and deploy

Review the generated work inside Agent Studio.

Check that the key parts of the agent look correct:

- flows
- functions
- knowledge base entries
- API integrations

Once everything looks right:

1. merge the branch into the main project through the Agent Studio web UI — there is no `poly merge` command
2. deploy the project

At that point, the agent is live.

## CLI command overview

| Command | Description |
|---|---|
| **poly init** | Initialize a new project locally |
| **poly pull** | Pull remote config into the local project |
| **poly push** | Push local changes to Agent Studio |
| **poly status** | List changed files |
| **poly diff** | Show diffs |
| **poly revert** | Revert local changes |
| **poly branch** | Branch management |
| **poly format** | Format resource files |
| **poly validate** | Validate project configuration locally |
| **poly review** | Create a diff review page |
| **poly chat** | Start an interactive session with the agent |
| **poly docs** | Output resource documentation |

## The overall loop

1. create or connect a project
2. build locally using the ADK
3. push to Agent Studio
4. review, merge, and deploy

## Next steps

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    Explore the available ADK commands and options.

    [Open CLI reference](../reference/cli.md)

-   **Walkthrough video**

    ---

    See the workflow demonstrated in video form.

    [Open the walkthrough video](../get-started/walkthrough-video.md)

</div>