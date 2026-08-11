<!-- BEGIN poly-adk -->
## PolyAI Agent Studio project

This directory is a PolyAI Agent Studio project managed by the `poly` CLI (poly-adk).
The agent's behaviour lives in YAML and Python under `flows/`, `functions/`, `topics/`,
`agent_settings/` and `config/`. Changes reach the agent by being pushed to the Agent
Studio platform, not by deploying this directory.

### Skill

Per-resource reference material lives in the `poly-adk` skill at `.claude/skills/poly-adk/`.
Read `SKILL.md`, then the matching `references/*.md` file, before making non-trivial edits
to a resource type.

### Workflow

| Step | Command |
|---|---|
| Pull remote config into local | `poly pull` |
| Work on a branch | `poly branch create <name>` |
| See what changed | `poly status`, `poly diff` |
| Check before pushing | `poly validate` |
| Publish to the platform | `poly push` |
| Test the agent | `poly chat` |

Run commands from inside the project folder, or pass `--path`. Always run `poly validate`
before `poly push`, and prefer `poly push --dry-run` when the change is large.

### Rules

- **Never edit `_gen/`.** It holds generated stubs and is overwritten on every pull.
- **No deterministic logic in prompts.** Value checks and branching belong in Python
  (function steps, transition functions), which then transition to the right step.
- **State syntax depends on context.** In Python: `conv.state.x`. In prompts, topics and
  SMS templates: `$x` or `{{vrbl:x}}`, never `conv.state.x`.
- **Every function step must advance the conversation**, via `flow.goto_step(...)`,
  `conv.exit_flow()`, or a returned transition.
- **Filenames are derived, not chosen.** Topic and test filenames are the `name` field in
  lowercase snake_case; a mismatch fails validation on pull and push.
- **No hardcoded IDs.** Reference flows, steps, functions and handoffs by name.

### Reference syntax

Usable in prompts, rules, topic actions and other text fields, but never inside a topic's
`content`:

| Syntax | Resolves to |
|---|---|
| `{{fn:name}}` | Global function |
| `{{ft:name}}` | Flow transition function (same flow only) |
| `{{entity:name}}` | Collected entity value |
| `{{attr:name}}` | Variant attribute |
| `{{ho:name}}` | Handoff destination |
| `{{twilio_sms:name}}` | SMS template |
| `{{vrbl:name}}` | State variable |
<!-- END poly-adk -->
