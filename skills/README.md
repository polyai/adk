# PolyAI ADK Skills

Agent skills for building [Agent Studio](https://studio.poly.ai) dialog agents with the [PolyAI ADK](https://polyai.github.io/adk/). They teach any coding agent — Claude Code, Cursor, Codex, or others — the `poly` CLI workflow: pull a project, edit resources on a branch, validate, push, test, and merge.

Install into your coding agent via [`npx skills`](https://github.com/vercel-labs/skills):

```bash
npx -y skills add https://github.com/polyai/adk -y
```

## Skills

| Skill | Description |
|-------|-------------|
| `poly-adk-workflow` | **Entrypoint** — install and auth, project setup, resource-choice guidance, the core edit → validate → push → test → merge loop |
| `poly-adk-testing` | Verification — `poly validate`, scripted `poly chat`, the `test_suite/` simulated conversation tests, running functions in isolation |
| `poly-adk-branching` | Branch management, the three-way merge model, non-interactive conflict resolution, review gists |
| `poly-adk-conversations` | Inspecting real calls with `poly conversations`, instrumenting functions with `conv.log` and metrics |
| `poly-adk-rtc` | Per-environment Real-Time Configuration — pull/push cycle, drift protection, live-environment safety |

`poly-adk-workflow` is the always-relevant entrypoint; the others load on demand for their task and point back to it. Resource schemas are deliberately **not** duplicated in the skills — the `poly docs` command ships them with the installed CLI, so they can never drift from the release in use.

## Versioning

Each skill's `metadata.version` tracks the `polyai-adk` release it was written against. Update the skills alongside CLI releases that change command surfaces or workflows.
