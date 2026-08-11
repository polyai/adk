---
name: poly-adk
description: Use whenever working with a PolyAI Agent Studio project managed by the poly-adk CLI — creating, editing, reviewing, or debugging flows, topics, functions, entities, variants, tests, rules, handoffs, SMS templates, API integrations, safety filters, or any other resource under an account/project folder. Also use when running poly init/pull/push/status/diff/validate/branch/review/chat/deployments, or when resolving {{fn:}}/{{ft:}}/{{attr:}}/{{entity:}}/{{ho:}}/{{twilio_sms:}}/{{vrbl:}} reference syntax. Trigger this even if the user only pastes YAML/Python from flows/, topics/, functions/, or project.yaml, or mentions a project by account/project name, without saying "poly-adk" explicitly.
---

# Poly ADK

Poly-ADK is a CLI and Python package for managing PolyAI Agent Studio projects locally — a Git-like workflow for
syncing agent configuration (flows, topics, functions, entities, settings) between the local filesystem and the
Agent Studio platform.

## Project structure

```
<account>/<project>/
├── _gen/                       # Generated stubs - never edit
├── agent_settings/              # personality.yaml, role.yaml, rules.txt, safety_filters.yaml, experimental_config.json
├── config/                      # api_integrations.yaml, entities.yaml, handoffs.yaml, sms_templates.yaml,
│                                 # translations.yaml, variant_attributes.yaml
├── voice/                       # configuration.yaml, safety_filters.yaml, speech_recognition/, response_control/
├── chat/                        # configuration.yaml, safety_filters.yaml
├── context/                     # {document_name}.md — background docs, not read at runtime
├── flows/{flow_name}/           # flow_config.yaml, steps/, function_steps/, functions/
├── functions/                   # global functions, start_function.py, end_function.py
├── topics/{topic_name}.yaml     # RAG knowledge base
├── test_suite/{test_name}.yaml  # simulated conversation tests
└── project.yaml                 # region, account_id, project_id
```

## CLI commands

| Command | Description |
|---|---|
| `poly init` | Initialize a project (interactive or `--region --account_id --project_id`); the agent must already exist on Agent Studio |
| `poly pull` | Pull remote config into local (`-f` force overwrite) |
| `poly push` | Push local changes (`-f` force, `--dry-run`, `--skip-validation`) |
| `poly status` | List changed files |
| `poly diff` | Show diffs (files, deployment hashes, or `--before`/`--after`) |
| `poly revert` | Revert local changes (all, or specific files) |
| `poly branch` | `list` / `create` / `switch` / `current` |
| `poly format` | Format resource files (all or `--files`) |
| `poly validate` | Validate project config locally |
| `poly review` | Diff review page: `create` / `list` / `delete` — needs a GitHub token |
| `poly deployments` | `list` (`--env --limit --offset --hash --details`) |
| `poly chat` | Interactive chat with the agent (`--environment --channel --functions --flows --state`) |
| `poly docs` | `poly docs {resource}` or `--all` — dumps resource docs identical to this skill's reference files. `--claude-code` reinstalls this skill and the project's CLAUDE.md section |

Run `poly -h` / `poly {command} -h` for details. Commands must run from inside the project folder, or pass `--path`.

## Standard workflow

1. `poly init` (agent must already exist on Agent Studio) → creates `account_id/project_id`
2. `poly pull` (`-f`/`--force` to override all local changes)
3. `poly branch create {name}` from `main`. Navigate with `switch`, check with `current`/`list`
4. Edit files locally; track with `poly status` / `poly diff`
5. `poly validate`
6. `poly push`
7. `poly chat` to test
8. (Optional) `poly review create` vs `main`/`sandbox` → shareable GitHub Gist for reviewers
9. Merge the branch on the Agent Studio UI

If Agent Studio UI changes are made on your branch, `poly pull` merges them in (shows merge markers on conflict).

## Resource reference syntax

Used inside prompts, rules, topics, greetings, and other text fields — **never** inside topic `content`.

| Syntax | Resolves to | Usable in |
|---|---|---|
| `{{fn:function_name}}` | Global function | Rules, topics (actions), advanced step prompts |
| `{{ft:function_name}}` | Flow transition function | Advanced step prompts, same flow only |
| `{{entity:entity_name}}` | Collected entity value | Flow step prompts |
| `{{attr:attribute_name}}` | Variant attribute | Rules, prompts, topics (actions), greeting, disclaimer, personality, role |
| `{{twilio_sms:template_name}}` | SMS template | Rules, topics (actions) |
| `{{ho:handoff_name}}` | Handoff destination | Rules |
| `{{vrbl:variable_name}}` (preferred) / `$variable_name` | State variable | Prompts, topic actions, SMS templates |

## Rules that apply across every resource

- **No deterministic logic in prompts.** Never write "If $x == 0 do A else B" in a prompt. Do value checks and
  branching in Python (function steps / transition functions), then transition to the right step.
- **State syntax differs by context.** In Python: `conv.state.x = value` / `conv.state.x`. In prompts/topics/SMS:
  `$x` or `{{vrbl:x}}` — never `conv.state.x`, and never `$x.attribute` (stringify complex objects in Python first).
- **Flow control must always advance.** Every function step and flow function must end by calling
  `flow.goto_step(...)` or `conv.exit_flow()`, or by returning a transition. Never leave the agent stuck with no
  navigation.
- **Don't mix exit and navigation.** Use either `conv.exit_flow()` + returned content, or a transition/`goto_flow`
  — not both in the same return; a later `goto_flow` overrides an earlier `exit_flow`.
- **No hardcoded IDs.** Reference flows/steps/functions/handoffs by their resource name, not internal IDs.
- **Filenames are derived, not chosen.** Topic and test filenames are the `name` field cleaned to lowercase
  snake_case; a mismatch fails validation on `pull`/`push`.
- **No "Anything else?" step.** End a flow with `conv.exit_flow()` and return that prompt as context from the
  function instead of adding a dedicated step for it.

## Reference files

Read the relevant file below before making non-trivial edits to that resource type — each has full field lists,
validation rules, and examples.

| Resource | File | Read this when... |
|---|---|---|
| Flows | `references/flows.md` | Writing/editing flow_config.yaml, steps, function_steps, or flow functions |
| Functions | `references/functions.md` | Writing global/flow functions, start/end functions, decorators, state, metrics |
| Topics | `references/topics.md` | Writing the RAG knowledge base |
| Entities | `references/entities.md` | Defining structured data to collect (dates, enums, phone numbers, etc.) |
| Variants | `references/variants.md` | Per-location/environment config via `{{attr:...}}` |
| Tests | `references/tests.md` | Writing test_suite/*.yaml simulated conversations |
| Agent Settings | `references/agent_settings.md` | personality.yaml, role.yaml, rules.txt |
| Voice Settings | `references/voice_settings.md` | voice/configuration.yaml (greeting, style, disclaimer) |
| Chat Settings | `references/chat_settings.md` | chat/configuration.yaml |
| Speech Recognition | `references/speech_recognition.md` | asr_settings.yaml, keyphrase_boosting.yaml, transcript_corrections.yaml |
| Response Control | `references/response_control.md` | pronunciations.yaml, phrase_filtering.yaml |
| Safety Filters | `references/safety_filters.md` | Any of the three safety_filters.yaml files |
| Handoffs | `references/handoffs.md` | SIP call transfer config |
| API Integrations | `references/api_integrations.md` | Defining/calling external HTTP APIs via `conv.api.*` |
| SMS Templates | `references/sms_templates.md` | Outbound text message templates |
| Translations | `references/translations.md` | Localized text strings per language |
| Languages | `references/languages.md` | Default/additional language config |
| Variables | `references/variables.md` | How `conv.state` variables are discovered and referenced |
| Experimental Config | `references/experimental_config.md` | agent_settings/experimental_config.json feature flags |
| Context | `references/context.md` | context/*.md background docs (non-runtime) |
