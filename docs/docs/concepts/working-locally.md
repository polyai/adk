---
title: Working locally
description: Understand how the PolyAI ADK maps Agent Studio projects onto a local development workflow.
---

With the ADK, you work on Agent Studio projects from your local machine instead of exclusively through the browser.

Your local filesystem becomes your primary editing surface. You can:

- edit agent resources directly
- review changes with Git-style workflows
- validate changes before pushing
- use AI coding tools such as **Cursor** or **Claude Code**
- test and iterate before merging in Agent Studio

<div class="grid cards" markdown>

-   **Local files**

    ---

    Agent configuration lives on disk in a structured project directory.

-   **CLI workflow**

    ---

    Pull, edit, validate, push, and review changes using the `poly` CLI.

-   **Platform sync**

    ---

    Agent Studio remains the source of deployment, preview, and branch merging.

-   **Developer tooling**

    ---

    The local workflow works naturally with editors, terminals, and AI-assisted coding tools.

</div>

## What a local project contains

Each local ADK project represents an Agent Studio project.

A project can define a voice or webchat agent, and its runtime behavior is controlled by resources such as flows, functions, topics, settings, and configuration files.

A typical project structure looks like this:

~~~text
<account>/<project>/
├── _gen/                               # Generated stubs - do not edit
├── agent_settings/                     # Agent identity and behavior
│   ├── personality.yaml
│   ├── role.yaml
│   ├── rules.txt
│   └── experimental_config.json        # Optional
├── config/                             # Configuration
│   ├── entities.yaml                   # Optional
│   ├── handoffs.yaml                   # Optional
│   ├── sms_templates.yaml              # Optional
│   └── variant_attributes.yaml         # Optional
├── voice/                              # Voice channel settings
│   ├── configuration.yaml
│   ├── speech_recognition/
│   └── response_control/
├── chat/                               # Chat channel settings
│   └── configuration.yaml
├── flows/                              # Optional - flow definitions
├── functions/                          # Global functions
├── topics/                             # Knowledge base topics
└── project.yaml                        # Project metadata
~~~

!!! info "Generated files"

    Files under `_gen/` are generated stubs and should not be edited directly.

## How local work maps to Agent Studio

The ADK does not replace Agent Studio. It acts as the local development layer around it.

A typical flow looks like this:

1. initialize or pull a project locally
2. create or switch to a branch
3. edit resources on disk
4. validate and inspect changes
5. push changes back to Agent Studio
6. test and review the branch in Agent Studio
7. merge when ready

This means the local filesystem becomes your main editing surface, while Agent Studio remains the place where work is previewed, reviewed, and deployed.

## Standard CLI workflow

The standard workflow is:

1. initialize the local project with `poly init` if it is not already present
2. pull the latest project configuration with `poly pull`
3. create a branch with `poly branch create {name}`
4. edit files locally
5. inspect changes with `poly diff` and `poly status`
6. validate locally with `poly validate`
7. push changes with `poly push`
8. test and chat with the agent using `poly chat`
9. optionally generate a review gist with `poly review`
10. merge the branch in Agent Studio

!!! tip "Run commands from the project folder"

    ADK commands are expected to be run from within the local project directory. If needed, use the `--path` flag to point to a project explicitly.

## Resource reference syntax

Many ADK resources support references to other resources or values.

These placeholders are used in prompts, rules, topic actions, and related text fields:

| Syntax | Resolves to | Common use |
|---|---|---|
| `{{fn:function_name}}` | Global function | Rules, topic actions, advanced step prompts |
| `{{ft:function_name}}` | Flow transition function | Advanced step prompts within the same flow |
| `{{entity:entity_name}}` | Collected entity value | Flow prompts |
| `{{attr:attribute_name}}` | Variant attribute | Rules, prompts, greetings, personality, role |
| `{{twilio_sms:template_name}}` | SMS template | Rules, topic actions |
| `{{ho:handoff_name}}` | Handoff destination | Rules |
| `{{vrbl:variable_name}}` | State variable | Prompts, topic actions, SMS templates |

These references let settings, prompts, and behaviors point to resources by name rather than repeating hard-coded values.

!!! tip "A Git-like workflow for Agent Studio"

    Think of the ADK as a synchronization layer between your local files and the Agent Studio platform.

## Development setup from source

To contribute to the ADK or work directly from the repository:

~~~bash
git clone https://github.com/polyai/adk.git
cd adk
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
~~~

This installs the project in editable mode and registers the development hooks.

## Related pages

<div class="grid cards" markdown>

-   **CLI reference**

    ---

    Review the main ADK commands and their purpose.
    [Open CLI reference](../reference/cli.md)

-   **Multi-user workflows and guardrails**

    ---

    Learn how branching, validation, and review fit into collaborative work.
    [Open multi-user workflows and guardrails](./multi-user-and-guardrails.md)

</div>