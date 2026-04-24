---
name: poly-adk
description: Use the poly CLI to manage PolyAI voice agents — provides context on commands, resource formats, and workflows. Use when building features or editing agent config.
allowed-tools: Read Grep Glob Bash
---

# Poly ADK

Poly-ADK is a CLI tool for managing PolyAI Agent Studio projects locally. It provides a Git-like workflow for syncing agent configurations between your local filesystem and the Agent Studio platform.

Each project defines an AI voice or webchat agent. Resources in the project (flows, functions, topics, etc.) control the agent's runtime behavior.

## Project Structure

```
<account>/<project>/
├── _gen/                               # Generated stubs - do not edit
├── agent_settings/                     # Agent identity and behavior
│   ├── personality.yaml
│   ├── role.yaml
│   ├── rules.txt
│   └── experimental_config.json        # Optional
├── config/                             # Configuration
│   ├── api_integrations.yaml           # Optional
│   ├── entities.yaml                   # Optional
│   ├── handoffs.yaml                   # Optional
│   ├── sms_templates.yaml              # Optional
│   └── variant_attributes.yaml         # Optional
├── voice/                              # Voice channel settings
│   ├── configuration.yaml              # Greeting, disclaimer, style prompt
│   ├── speech_recognition/
│   │   ├── asr_settings.yaml           # Barge-in, interaction style
│   │   ├── keyphrase_boosting.yaml     # Optional
│   │   └── transcript_corrections.yaml # Optional
│   └── response_control/
│       ├── pronunciations.yaml         # Optional - TTS rules
│       └── phrase_filtering.yaml       # Optional - stop keywords
├── chat/                               # Chat channel settings
│   └── configuration.yaml              # Greeting, style prompt
├── flows/                              # Optional - flow definitions
│   └── {flow_name}/
│       ├── flow_config.yaml
│       ├── steps/
│       │   └── {step_name}.yaml
│       ├── function_steps/
│       │   └── {function_step}.py
│       └── functions/
│           └── {function_name}.py
├── functions/                          # Global functions (shared across flows)
│   ├── start_function.py              # Optional - runs at call start
│   ├── end_function.py                # Optional - runs at call end
│   └── {function_name}.py
├── topics/                             # Knowledge base topics
│   └── {topic_name}.yaml
└── project.yaml                        # Project metadata (region, account_id, project_id)
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `poly init` | Initialize a new project (interactive or with `--region`, `--account_id`, `--project_id`) |
| `poly pull` | Pull remote config into local project (`-f` to force overwrite) |
| `poly push` | Push local changes to Agent Studio (`-f` to force, `--dry-run` to preview, `--skip-validation`) |
| `poly status` | List changed files |
| `poly diff` | Show diffs (optionally for specific files, deployment hashes, or between versions with `--before`/`--after`) |
| `poly revert` | Revert local changes (all by default, or specific files) |
| `poly branch` | Branch management: `list`, `create`, `switch`, `current`, `delete`, `merge` |
| `poly format` | Format resource files (ruff for Python, ruamel.yaml for YAML/JSON) |
| `poly validate` | Validate project configuration locally |
| `poly review` | Diff review page: `create`, `list`, `delete` |
| `poly deployments list` | List deployments with versions and active environments |
| `poly chat` | Interactive chat session with the agent (`-e sandbox/live`, `--channel voice/webchat`, `--metadata`) |
| `poly docs` | Output resource documentation (`poly docs flows functions`, or `--all`) |

## Init and pull project

To start a new project: `poly init` (interactive, or pass `--region`, `--account_id`, `--project_id`).

To pull the latest config from Agent Studio: `poly pull`. Use `-f` to force overwrite local changes.

Switch branches with `poly branch switch {name}`, then `poly pull` to get that branch's latest.

Commands must be run from within the project folder, or use `--path`. Always pass `--json` for machine-readable output. Use `-h` for flag details.

## Branch management

Always create branches from `main`. Use descriptive names (e.g. `add-booking-flow`, `update-hours-topic`).

```
poly branch list --json
poly branch current --json
poly branch create {name} --json   # must be on main
poly branch switch {name} --json
poly branch delete {name} --json
```

## Making edits

Before writing any resource, run `poly docs {resource_type}` to get the exact format, required fields, and examples.

Track and inspect changes as you go:
```
poly status --json       # list changed files
poly diff --json         # show full diff
poly validate --json     # validate locally before pushing
```

## Pushing changes

```
poly push --json                   # push local changes (pulls and merges first)
poly push --dry-run --json         # preview what would be pushed
poly push -f --json                # force overwrite remote
```

If `success` is false and `files_with_conflicts` is non-empty, resolve the conflict markers in the affected files and push again.

## Testing changes

Start a session and send the first message — the session stays open when using `--json`:
```
poly chat --json -m "first message"
```

Continue turn by turn using the `conversation_id` from the response:
```
poly chat --json --conv-id {conversation_id} -m "next message"
```

To explicitly end the session, use: "/exit"
```
poly chat --json --conv-id {conversation_id} -m "/exit"
```

`/exit` closes the session.

Use flags to inspect what the agent is doing each turn:
```
--flows       show active flow and step
--functions   show function/tool calls
--metadata    show flows, functions, and state (all of the above)
```

Test against other environments with `-e sandbox` or `-e live`.

## Merging

Before merging, always show the user the full diff and ask them to confirm:
```
poly diff --before main --after {branch_name} --json
poly branch merge {name} --json
```

Use `poly review create --before main --after {branch_name}` to generate a shareable diff review page if the user wants to review in the browser.

## Resource Reference Syntax

These placeholders are used in prompts, rules, topics, and other text fields:

| Syntax | Resolves to | Usable in |
|--------|-------------|-----------|
| `{{fn:function_name}}` | Global function | Rules, topics (actions), advanced step prompts |
| `{{ft:function_name}}` | Flow transition function | Advanced step prompts (same flow only) |
| `{{entity:entity_name}}` | Collected entity value | Flow step prompts |
| `{{attr:attribute_name}}` | Variant attribute | Rules, prompts, topics, greeting, disclaimer, personality, role |
| `{{twilio_sms:template_name}}` | SMS template | Rules, topics (actions) |
| `{{ho:handoff_name}}` | Handoff destination | Rules |
| `{{vrbl:variable_name}}` | State variable | Prompts, topic actions, SMS templates |

## Resource Documentation

Run `poly docs {resource_type}` (e.g. `poly docs functions flows topics`) or `poly docs --all` to get the exact YAML/Python format, required fields, validation rules, and examples. **Always consult the docs before writing or editing a resource.**

Available resource types: `functions`, `flows`, `topics`, `entities`, `agent_settings`, `handoffs`, `sms`, `variants`, `api_integrations`, `variables`, `voice_settings`, `chat_settings`, `speech_recognition`, `response_control`, `experimental_config`.
