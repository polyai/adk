---
title: Working locally
description: Understand how the PolyAI ADK maps Agent Studio projects onto a local development workflow.
---

With the ADK, you work on Agent Studio projects from your local machine instead of exclusively through the browser.

Your local filesystem becomes your primary editing surface. You can:

- edit agent resources directly
- review changes with Git-style workflows
- validate changes before pushing
- work in **VS Code** or **Cursor** with the [PolyAI ADK extension](../reference/tooling.md#polyai-adk-extension-for-vs-code-and-cursor), or pair the ADK with [AI coding agents](../reference/tooling.md#claude-code) such as **Claude Code**
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

    Agent Studio remains the source of deployment and preview. Branches can be merged with [`poly branch merge`](../reference/branch_merge.md) from the CLI or through the Agent Studio UI.

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
│   ├── safety_filters.yaml             # Optional
│   └── experimental_config.json        # Optional
├── config/                             # Configuration
│   ├── entities.yaml                   # Optional
│   ├── handoffs.yaml                   # Optional
│   ├── sms_templates.yaml              # Optional
│   └── variant_attributes.yaml         # Optional
├── voice/                              # Voice channel settings
│   ├── configuration.yaml
│   ├── safety_filters.yaml             # Optional
│   ├── speech_recognition/
│   └── response_control/
├── chat/                               # Chat channel settings
│   ├── configuration.yaml
│   └── safety_filters.yaml             # Optional
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

1. initialize the local project with [`poly init`](../reference/cli.md#poly-init) if it is not already present
2. pull the latest project configuration with [`poly pull`](../reference/cli.md#poly-pull)
3. create a branch with [`poly branch create {name}`](../reference/cli.md#poly-branch-create)
4. edit files locally
5. inspect changes with [`poly diff`](../reference/cli.md#poly-diff) and [`poly status`](../reference/cli.md#poly-status)
6. validate locally with [`poly validate`](../reference/cli.md#poly-validate)
7. push changes with [`poly push`](../reference/cli.md#poly-push)
8. optionally generate a review gist with [`poly review create`](../reference/cli.md#poly-review)
9. merge the branch with [`poly branch merge`](../reference/branch_merge.md) or in Agent Studio
10. test by chatting with the agent using [`poly chat`](../reference/cli.md#poly-chat) — by default this connects to your current branch's pushed state. Use [`poly push`](../reference/cli.md#poly-push) first, or `poly chat --push` to push and start the session in one step. On the main branch it falls back to Sandbox.

!!! tip "Run commands from the project folder"

    ADK commands are expected to be run from within the local project directory. If needed, use the `--path` flag to point to a project explicitly.

## Resource reference syntax

Many ADK resources support references to other resources or values.

These placeholders are used in prompts, rules, topic actions, and related text fields:

| Syntax | Resolves to | Common use |
|---|---|---|
| `{{fn:function_name}}` | [Global function](../reference/functions.md) | Rules, topic actions, advanced step prompts |
| `{{ft:function_name}}` | [Flow transition function](../reference/flows.md) | Advanced step prompts within the same flow |
| `{{entity:entity_name}}` | [Collected entity value](../reference/entities.md) | Flow prompts |
| `{{attr:attribute_name}}` | [Variant attribute](../reference/variants.md) | Rules, prompts, greetings, personality, role |
| `{{twilio_sms:template_name}}` | [SMS template](../reference/sms.md) | Rules, topic actions |
| `{{ho:handoff_name}}` | [Handoff destination](../reference/handoffs.md) | Rules |
| `{{vrbl:variable_name}}` | [State variable](../reference/variables.md) | Prompts, topic actions, SMS templates |

These references let settings, prompts, and behaviors point to resources by name rather than repeating hard-coded values.

!!! tip "A Git-like workflow for Agent Studio"

    Think of the ADK as a synchronization layer between your local files and the Agent Studio platform.

## Development setup from source

If you are contributing to the ADK itself or working directly from the repository, you can set it up locally from source instead.

~~~bash
git clone https://github.com/polyai/adk.git
cd adk
uv venv --python=3.14 --seed
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
~~~

This installs the project in editable mode and enables the repository's development hooks. To run the test suite:

~~~bash
pytest
~~~

Test files are located in `src/poly/tests/`.

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
