---
name: ci-check
description: Run the same checks as the ADK's GitHub CI (PR title, lint, format, licences, licenses.json, skill versions, tests) locally and report pass/fail. Use before pushing a branch or opening a pull request in the polyai-adk repo.
metadata:
  internal: true
---

# Run the ADK CI checks locally

Run every step, even after one fails, then report a summary. All commands run from the repo root
through `uv run`; don't activate the venv.

1. **PR title.** Take the intended PR title (ask if it isn't known) and check it matches
   `^(feat|fix|chore|docs|ci|build|perf|refactor|style|test)(\(.+\))?!?: .+`. Check that the
   type is right too: anything a user can see is `feat:`. See the release table in `AGENTS.md`.
2. **Lint:** `uv run ruff check .`
3. **Format:** `uv run ruff format --check .`
4. **Licences:** `uv run licensecheck --zero`
5. **licenses.json is current:** `uv run pip-licenses && git diff --exit-code licenses.json`.
   A diff here means it needs committing.
6. **User skill versions:** `uv run python scripts/validate_skills.py`
7. **Tests:** `uv run pytest src/poly/tests/`

CI also runs the tests on Windows. Point out new code that could break there: hard-coded `/`
path joins, `open()` without `encoding="utf-8"`, shell-specific commands, or file permission
assumptions.

## Report

- One line per step: pass or fail.
- For each failure, the relevant error output (trim long logs).
- A final verdict: ready to push, or what to fix first.
