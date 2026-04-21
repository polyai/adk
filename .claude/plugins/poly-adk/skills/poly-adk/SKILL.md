---
name: poly-adk
description: How to use the poly CLI to manage PolyAI voice agents — commands, resource formats, and workflows. Use when building features or editing agent config.
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

Use `poly -h` and `poly {command} -h` for detailed flags.

## CLI Workflow

1. Initialise: `poly init` (agent must exist on Agent Studio first)
2. Pull latest: `poly pull` (`--force` to overwrite local changes)
3. Create branch: `poly branch create {name}` (must be on `main`)
4. Edit files locally, track with `poly status` and `poly diff`
5. Validate: `poly validate`
6. Push: `poly push`
7. Test: `poly chat`
8. Review: `poly review create` (generates a GitHub Gist diff)
9. Merge on Agent Studio UI

Switch branches with `poly branch switch {name}`. Pull remote branch changes with `poly pull` (3-way merge, shows conflict markers if needed).

Commands must be run from within the project folder, or use `--path` to specify location.

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

Before writing or editing any resource, read its documentation using `poly docs {resource_type}` or by reading the doc file directly from `src/poly/docs/`:

| Resource | Doc file | Summary |
|----------|----------|---------|
| Functions | `src/poly/docs/functions.md` | Global and flow functions, `@func_description`/`@func_parameter` decorators, state, metrics |
| Flows | `src/poly/docs/flows.md` | Multistep processes with steps, conditions, transition functions |
| Topics | `src/poly/docs/topics.md` | Knowledge base for RAG |
| Entities | `src/poly/docs/entities.md` | Structured data collection (numeric, enum, date, phone, etc.) |
| Agent Settings | `src/poly/docs/agent_settings.md` | Personality, role, rules |
| Handoffs | `src/poly/docs/handoffs.md` | SIP call transfers |
| SMS Templates | `src/poly/docs/sms.md` | Text message templates |
| Variants | `src/poly/docs/variants.md` | Per-variant configuration (attributes) |
| API Integrations | `src/poly/docs/api_integrations.md` | External HTTP API definitions |
| Variables | `src/poly/docs/variables.md` | State variables referenced in code |
| Voice Settings | `src/poly/docs/voice_settings.md` | Voice greeting, disclaimer, style prompt |
| Chat Settings | `src/poly/docs/chat_settings.md` | Chat greeting, style prompt |
| Speech Recognition | `src/poly/docs/speech_recognition.md` | ASR settings, keyphrase boosting, transcript corrections |
| Response Control | `src/poly/docs/response_control.md` | Pronunciations, phrase filters |
| Experimental Config | `src/poly/docs/experimental_config.md` | Feature flags |

**Always read the relevant doc file before creating or modifying a resource.** The docs contain the exact YAML/Python format, required fields, validation rules, and examples.
