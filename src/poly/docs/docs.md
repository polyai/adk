# Poly ADK

## Overview

Poly-ADK is a CLI tool and Python package for managing PolyAI Agent Studio projects locally. It provides a Git-like workflow for synchronizing agent configurations between your local filesystem and the Agent Studio platform, so agent development fits into your existing build and review cycles.

Each project defines an AI voice or webchat agent. Resources in the project (flows, functions, topics, etc.) control the agent's runtime behavior.

## Project Structure

```
<account>/<project>/
├── _gen/                               # Generated stubs - do not edit
├── agent_settings/                     # Agent identity and behavior
│   ├── personality.yaml
│   ├── role.yaml
│   ├── rules.txt
│   ├── safety_filters.yaml
│   └── experimental_config.json        # Optional
├── config/                             # Configuration
│   ├── api_integrations.yaml           # Optional
│   ├── entities.yaml                   # Optional
│   ├── handoffs.yaml                   # Optional
│   ├── sms_templates.yaml              # Optional
│   └── variant_attributes.yaml         # Optional
├── voice/                              # Voice channel settings
│   ├── configuration.yaml              # Greeting, disclaimer, style prompt
│   ├── safety_filters.yaml             # Optional
│   ├── speech_recognition/
│   │   ├── asr_settings.yaml           # Barge-in, interaction style
│   │   ├── keyphrase_boosting.yaml     # Optional
│   │   └── transcript_corrections.yaml # Optional
│   └── response_control/
│       ├── pronunciations.yaml         # Optional - TTS rules
│       └── phrase_filtering.yaml       # Optional - stop keywords
├── chat/                               # Chat channel settings
│   ├── configuration.yaml              # Greeting, style prompt
│   └── safety_filters.yaml             # Optional
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
| `poly diff` | Show full diffs (optionally for specific files, deployment hashes or between versions with `--before`/`--after`) |
| `poly revert` | Revert local changes (all by default, or specific files) |
| `poly branch` | Branch management: `list`, `create`, `switch`, `current` |
| `poly format` | Format resource files (all or `--files` for specific files) |
| `poly validate` | Validate project configuration locally |
| `poly review` | Diff review page: `create` (local vs remote, version hash, or `--before`/`--after`), `list`, `delete` |
| `poly deployments` | Manage deployments (`list`, with `--env`, `--limit`, `--offset`, `--hash`, `--details`) |
| `poly chat` | Interactive chat session with the agent (`--environment`, `--channel`, `--functions`, `--flows`, `--state`) |
| `poly docs` | Output resource documentation (`poly docs flows functions topics`, or `--all` for everything) |

Use `poly -h` and `poly {command} -h` for more detailed information

## CLI Workflow

The standard CLI workflow is the following:
1. (If not already) Initialise the agent on the local machine using `poly init`. The Agent must exist on Agent Studio first. This will create the project in `account_id/project_id`
2. Get latest version of project using `poly pull`. To override all local changes use the `--force` flag.
3. Start a new branch `poly branch create {name}`. This must be done from the `main` branch. You can navigate between branches using `poly branch switch {name}` and check your current branch using `poly branch current` and existing branches with `poly branch list`
4. Edit files locally, use `poly diff` and `poly status` to track changes.
5. Validate your changes are valid with Agent Studio using `poly validate`
6. Push changes with `poly push`
7. Test and chat with your agent using `poly chat`
8. (Optional) Once ready, use `poly review` and compare your changes to `main`/`sandbox` to generate a GitHub Gist to share with a reviewer. A GitHub environment token is required for this step.
9. Merge your changes on Agent Studio by navigating to your branch and pressing "merge"

If work is done to your branch on the Agent Studio UI that you wish to pull into your local version, you can use `poly pull`. This will merge those changes with yours and show merge markers if a merge conflict occurs.

Commands also must be run from within your project folder. If you are not within your project folder, you can specify where your project is using the `--path` flag

## Resource Reference Syntax

These placeholders can be used in prompts, rules, topics, and other text fields to reference project resources:

| Syntax | Resolves to | Usable in |
|--------|-------------|-----------|
| `{{fn:function_name}}` | Global function | Rules, topics (actions), advanced step prompts |
| `{{ft:function_name}}` | Flow transition function | Advanced step prompts (same flow only) |
| `{{entity:entity_name}}` | Collected entity value | Flow step prompts |
| `{{attr:attribute_name}}` | Variant attribute | Rules, prompts, topics (actions), greeting, disclaimer, personality, role |
| `{{twilio_sms:template_name}}` | SMS template | Rules, topics (actions) |
| `{{ho:handoff_name}}` | Handoff destination | Rules |
| `{{vrbl:variable_name}}` (preferred) / `$variable_name` | State variable (interchangeable; `{{vrbl:...}}` is validated) | Prompts, topic actions, SMS templates |

## Documentation

Resource-specific documentation is available via `poly docs {resource} [resource ...]` or `poly docs --all`. Docs can also be read directly from `src/poly/docs/`:

- [Agent Settings](agent_settings.md) - personality, role, rules
- [Voice Settings](voice_settings.md) - voice greeting, disclaimer, style prompt
- [Chat Settings](chat_settings.md) - chat greeting, style prompt
- [Flows](flows.md) - multistep processes with steps, functions, conditions
- [Functions](functions.md) - global and flow functions, decorators, state, metrics
- [Topics](topics.md) - knowledge base for RAG
- [API Integrations](api_integrations.md) — external HTTP API definitions
- [Entities](entities.md) - structured data collection
- [Handoffs](handoffs.md) - SIP call transfers
- [Variants](variants.md) - per-variant configuration
- [SMS Templates](sms.md) - text message templates
- [Variables](variables.md) - state variables referenced in code
- [Speech Recognition](speech_recognition.md) - ASR settings, keyphrase boosting, transcript corrections
- [Response Control](response_control.md) - pronunciations, phrase filters
- [Safety Filters](safety_filters.md) - content moderation settings (violence, hate, sexual, self-harm)
- [Experimental Config](experimental_config.md) - feature flags
