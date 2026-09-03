---
name: poly-adk-rtc
description: >
  This skill should be used when the user wants to "change real-time configuration",
  "update RTC", "edit per-environment config", or work with the real_time_configuration/
  directory of a PolyAI ADK project. Covers poly rtc pull/push/edit/diff/validate, drift
  protection, and the live-environment hazard. Part of the PolyAI ADK skills suite.
  Do NOT use for resources that deploy through branches (use poly-adk-workflow).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.53.1
  requires:
    bins:
      - poly
    install: "uv tool install polyai-adk"
---

# Real-Time Configuration (RTC)

Load `poly-adk-workflow` first for the resource workflow RTC sits *outside* of. RTC is per-environment configuration that takes effect **without a deployment** — it is not branched, not versioned with resources, and not promoted through the sandbox → pre-release → live ladder. You pull and push it per environment, and there is no promotion between environments: changing a value everywhere means pushing to each one.

**`poly rtc push --env live` writes straight to production, effective immediately — no branch, review, or promotion step.** Never push to `live` (or `pre-release`) unless the user explicitly asks. Verify in `sandbox` first.

## Local layout

Each environment holds a **schema** (`schema.json`, the shape) and **data** (`data.json`, the values):

```text
real_time_configuration/
├── draft_and_sandbox/     # the sandbox environment (note the directory name)
│   ├── schema.json
│   └── data.json
├── pre_release/
└── live/
```

## The cycle

```bash
poly rtc pull                  # all environments by default (--env to narrow)
# edit schema.json / data.json
poly rtc diff                  # local vs remote, per environment
poly rtc validate              # data.json against schema.json
poly rtc push --env sandbox    # --env is REQUIRED on push — no default, so no wrong-env accidents
```

- `--schema` / `--data` on pull and push operate on just one half (mutually exclusive).
- `poly rtc push` runs the same validation as `poly rtc validate` unless `--skip-validation`.
- `poly rtc edit --env <env>` does pull → open in `$EDITOR` → validate → push in one step. It is inherently interactive (no `--json`), so as an agent prefer the pull/edit-files/push cycle.

## Drift protection

Each `poly rtc pull` stores a base copy. On push, if the remote moved since your last pull (usually someone editing in the Agent Studio UI), the config has **drifted**. Default behavior is a three-way merge — **per key**, unlike resource files which merge per line: a key changed on one side applies cleanly; a key changed differently on both sides is a conflict and aborts the push.

- `--no-merge` — fail on any drift instead of merging.
- `--force` — skip the drift check and overwrite the remote. Confirm with the user first; someone's UI edits may be on the other side.
- **Drift protection only works if you pulled first** — push without a prior pull and the check is silently skipped. Always `poly rtc pull` before editing.
