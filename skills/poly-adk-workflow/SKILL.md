---
name: poly-adk-workflow
description: >
  This skill should be used when the user wants to "build an agent", "update an agent",
  "create a PolyAI project", "push changes to Agent Studio", or work with the PolyAI ADK
  (`poly`) in any way. Entrypoint for the PolyAI ADK skills suite — covers setup, project
  structure, resource choice, and the core edit/validate/push/test/merge workflow, and
  routes to the task-specific skills (testing, branching, conversations, rtc).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.53.1
  requires:
    bins:
      - poly
    install: "uv tool install polyai-adk"
---

# PolyAI ADK workflow

The PolyAI ADK (`poly`) is a CLI for building dialog agents on the Agent Studio platform. It gives you a Git-like local workflow: agent resources (flows, functions, topics, entities, settings) live on disk as YAML, text, and Python files, and you `pull`, `push`, `branch`, and `merge` them against the platform.

Use `poly <command> --help` as the source of truth for flags. Almost every command accepts `--json` (a single JSON object on stdout, exit code 0 on success) — prefer it when you need to parse output.

## Task-specific skills

This skill covers setup and the core loop. Load the matching skill when the task goes deeper:

| Task | Skill |
|---|---|
| Testing the agent — scripted chat, running the test suite, writing test cases | `poly-adk-testing` |
| Merge conflicts, branch management, sharing reviews | `poly-adk-branching` |
| Inspecting real conversations, logging and metrics | `poly-adk-conversations` |
| Per-environment real-time configuration | `poly-adk-rtc` |

## 1. Installing and updating

Assume `poly` is installed. If a command fails because it isn't:

- **Install** → `uv tool install polyai-adk` (install `uv` first if needed: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Update to latest** → `uv tool upgrade polyai-adk`

## 2. Authentication

Assume the user is already logged in — do not check credentials up front. Only if a command fails with an authentication error, ask the user to run `poly login` — it opens a browser to sign in, so they must complete it themselves. Regions: `studio` for self-serve accounts, `us-1` / `euw-1` / `uk-1` for enterprise workspaces. On a fresh machine, `poly setup` runs sign-in plus shell completion, AI skills, and project setup in one command.

Credentials are resolved in this order: `~/.poly/credentials.json` (written by `poly login`), then a region-scoped env var (`POLY_ADK_KEY_US` / `POLY_ADK_KEY_EUW` / `POLY_ADK_KEY_UK` / `POLY_ADK_KEY_STUDIO`), then `POLY_ADK_KEY` — useful when debugging why the CLI is using the wrong account or region.

## 3. Load the resource documentation

Before creating or editing any resource, load the built-in docs — they define each resource type's exact schema, valid values, and conventions:

```bash
poly docs # For the top level overview of all resource types
poly docs {resource name} # For a specific resource type, e.g. flows, functions, topics, etc.
poly docs flows functions topics # For multiple resource types at once
```

Read the relevant sections before writing files. Do not guess at resource schemas — `poly docs` is authoritative for the installed version.

### Choosing the right resource type

The three that overlap most are rules, topics, and functions. The test: if an instruction is **always true**, it belongs in `agent_settings/rules.txt`; if it's only relevant **when a subject comes up**, it belongs in a topic; if it needs a **comparison, calculation, or API call**, it belongs in a Python function. Prompts are for collecting and presenting information; Python is for branching, routing, and validation — never write "if X then Y" conditionals in prompt text.

Resources reference each other by name with `{{prefix:name}}` placeholders (`{{fn:}}` functions, `{{entity:}}` entities, `{{ho:}}` handoffs, `{{attr:}}` variant attributes, `{{vrbl:}}` state variables, `{{twilio_sms:}}` SMS templates, `{{tn:}}` translations). `poly validate` checks every reference resolves.

## 4. Set up or connect a project

```bash
poly project create   # create a new Agent Studio project and pull it locally
poly init             # connect to an existing project (interactive pickers)
poly template list    # optional: start from a pre-built template
poly template load <name>
```

Projects land in a `<account_id>/<project_id>/` directory. **Run all `poly` commands from inside the project directory**, or pass `--path`.

A project looks like:

```text
<account>/<project>/
├── _gen/                    # Generated stubs — NEVER edit
├── agent_settings/          # persona.txt, rules.txt, guardrails, languages
├── config/                  # entities, handoffs, sms_templates, api_integrations, variants, translations
├── context/                 # background docs for Studio Assistant
├── voice/                   # voice channel config, speech_recognition/, response_control/
├── chat/                    # webchat channel config
├── flows/                   # multi-step guided conversations
├── functions/               # Python functions (deterministic logic, lifecycle hooks)
├── topics/                  # knowledge base entries
├── test_suite/              # simulated conversation tests
├── real_time_configuration/ # per-environment RTC (see poly-adk-rtc)
└── project.yaml             # project metadata
```

## 5. The core development loop

**You cannot work on `main`.** Every change goes on a branch. The branch you are on determines what `poly push` writes to and what `poly chat` talks to.

```bash
poly pull                        # 1. start from the latest state on main
poly branch create <name>        # 2. create + switch to a branch (keeps local edits)
# 3. edit resource files on disk
poly status                      # 4. see unpushed local changes
poly diff                        #    inspect them in detail
poly validate                    # 5. catch structural errors locally, before pushing
poly push                        # 6. push to the branch
poly chat --push                 # 7. test interactively (see poly-adk-testing)
poly test run                    #    and/or run the simulated test suite
# 8. iterate: repeat 3–7
poly branch diff                 # 9. review everything on the branch since creation
poly branch merge '<message>'    # 10. merge into main (deploys to sandbox automatically)
```

Key distinctions:

- `poly status` / `poly diff` show **unpushed local edits**; `poly branch status` / `poly branch diff` show **everything on the branch** since it was created. Use the branch-level commands before merging.
- `poly revert` discards local changes; `poly format` normalizes resource files.
- `poly pull` three-way merges rather than overwriting, and `poly branch merge` can conflict — if either reports conflicts, load `poly-adk-branching` for the resolution workflow.

## 6. Testing

Four layers, catching different problems — load `poly-adk-testing` for the details of each:

| Command | Catches | Runs against |
|---|---|---|
| `poly validate` | Invalid resources, missing values, broken references | Local files |
| `poly chat` | Conversational behavior, judged by reading | Last **pushed** state |
| `poly test run` | Regressions, repeatably | Last **pushed** state |
| `poly conversations` | What happened on real calls | Live traffic |

`poly chat` and `poly test run` run against the last pushed state, **not** local files — push first, or use `poly chat --push` / `poly test run --push`.

## 7. Deployment

Merging into `main` deploys to `sandbox` automatically. From there, promotion is one step at a time up the ladder — `sandbox` → `pre-release` → `live`:

```bash
poly deployments promote --from sandbox --to pre-release --dry-run
poly deployments list             # what is deployed where
```

**Never promote to `pre-release` or `live` unless the user explicitly asks** — `live` is production. Use `--dry-run` first to preview, and re-run tests against each environment after promoting. See `poly deployments --help` for the full surface, including rollback.

## Rules and gotchas

- Never edit anything under `_gen/` — generated stubs.
- Never work on `main`; check `poly branch current` if unsure.
- Run `poly validate` before every push — push runs the same validation and rejects what validate rejects.
- Python functions callable by the model need `@func_description` and `@func_parameter` decorators; without them the platform creates the function with no parameters and calls fail at runtime. Lifecycle functions and function steps don't need them.
- Keep resource names stable — resources reference each other by name (`{{prefix:name}}` syntax).
- Keep branches small and focused; pull before starting work so conflicts stay small.
- The web UI edits the same branches — someone may change the branch in Agent Studio while you work; `poly pull` reconciles.
