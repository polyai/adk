---
title: Working locally
description: Understand how the PolyAI ADK maps Agent Studio projects onto a local development workflow.
---

# Working locally

With the ADK, you work on Agent Studio projects from your local machine instead of exclusively through the browser.

Your local filesystem becomes your primary editing surface. You can:

- edit agent resources directly
- review changes with Git-style workflows
- validate changes before pushing
- work in **VS Code** or **Cursor** with the [PolyAI ADK extension](../tooling/tooling.md#polyai-adk-extension-for-vs-code-and-cursor), or pair the ADK with [AI coding agents](../tooling/tooling.md#claude-code) such as **Claude Code**
- test and iterate before merging in Agent Studio

## What a local project contains

Each local ADK project represents an Agent Studio project.

A project can define a voice or webchat agent, and its runtime behavior is controlled by resources such as flows, functions, topics, settings, and configuration files.

A typical project structure looks like this:

~~~text
<account>/<project>/
├── _gen/                               # Generated stubs - do not edit
├── agent_settings/                     # Agent identity and behavior
│   ├── languages.yaml                  # Optional
│   ├── personality.yaml
│   ├── role.yaml
│   ├── rules.txt
│   ├── safety_filters.yaml             # Optional
│   └── experimental_config.json        # Optional
├── config/                             # Configuration
│   ├── entities.yaml                   # Optional
│   ├── handoffs.yaml                   # Optional
│   ├── sms_templates.yaml              # Optional
│   ├── translations.yaml               # Optional
│   └── variant_attributes.yaml         # Optional
├── context/                            # Optional - document context files
│   └── {document_name}.md
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
├── test_suite/                         # Optional - simulated conversation tests
├── real_time_configuration/            # Optional - per-environment RTC
└── project.yaml                        # Project metadata
~~~

!!! info "Generated files"

    Files under `_gen/` are generated stubs and should not be edited directly.

## The development workflow

The ADK does not replace Agent Studio. It acts as the local development layer around it: your local filesystem becomes the main editing surface, while Agent Studio remains the place where work is previewed, reviewed, and deployed.

A typical cycle looks like this:

1. **Start on `main`** and pull the latest state — `poly pull`
2. **Create a branch** — `poly branch create <branch_name>`. You cannot work on `main`; every change is made on a branch.
3. **Edit resources** on disk, in whichever editor you prefer
4. **Inspect your local edits** — `poly status` and `poly diff`
5. **Validate** — `poly validate`
6. **Push to the branch** — `poly push`
7. **Test the agent** — `poly chat` to talk to it, or `poly test run` for the simulated conversation tests in `test_suite/`
8. **Iterate** — repeat steps 3–7
9. **Review the whole branch** — `poly branch status` and `poly branch diff` show every change since the branch was created; share them with `poly branch review` if you want a second pair of eyes
10. **Merge** — [`poly branch merge`](../reference/cli/branch.md#poly-branch-merge) `'<message>'`

!!! tip "File-level and branch-level inspection are different"

    `poly status` and `poly diff` show the edits you have not pushed yet. `poly branch status` and `poly branch diff` show everything on the branch since you created it, including changes you have already pushed.

Both `poly chat` and `poly test run` run against the last pushed state, so push before you test — or use `poly chat --push` and `poly test run --push` to do both in one step.

!!! tip "Run commands from the project folder"

    ADK commands are expected to be run from within the local project directory. If needed, use the `--path` flag to point to a project explicitly.

## Deploying your changes

Merging your branch updates `main`, which is deployed automatically to the `sandbox` environment. From there you promote up through `pre-release` to `live` — see [environments and deployment](./environments-and-deployment.md).