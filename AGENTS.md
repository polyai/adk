# PolyAI ADK

`polyai-adk` is the `poly` CLI: a git-like workflow (`pull`, `push`, `branch`, `diff`, …) for
building PolyAI Agent Studio agents locally as YAML and Python files. These rules apply to every
coding agent and reviewer working in this repo. Review-specific guidance is in `REVIEW.md`, which
repeats the rules below that matter in review: when you change one of those rules, update both.

## Commands

Run everything through `uv run`; don't activate the venv first.

| Task | Command |
|---|---|
| Install (with dev extras) | `uv pip install -e ".[dev]"` |
| Tests | `uv run pytest src/poly/tests/` |
| Coverage | `uv run pytest src/poly/tests/ --cov=poly --cov-report=term-missing` |
| Lint / format | `uv run ruff check .` / `uv run ruff format .` |
| Licence check | `uv run licensecheck --zero` |
| Regenerate `licenses.json` | `uv run pip-licenses` |
| Validate user skills | `uv run python scripts/validate_skills.py` |

CI runs all of these on every PR, with tests on Ubuntu **and Windows**, plus a check that the PR
title is a conventional commit. The `ci-check` skill runs the same set locally.

## Layering

```
cli_commands/        →  AgentStudioProject (project.py)  →  AgentStudioInterface  →  PlatformAPIHandler / sdk
user interaction        logic and validation                 API facade               HTTP / protobuf
```

- **Anything that acts on a project is a method on `AgentStudioProject`**, so it can be done
  programmatically as `project.<method>()`. Tests and other tools build on the project directly,
  without going through the CLI. That includes reads: if a command needs project data, add a
  project method, even one that only forwards to the interface.
- **`project.py` owns the logic and validation:** API calls, file I/O, merging, and checking
  inputs (raise `ValueError` with a clear message). Validating there gives programmatic callers
  the same checks as the CLI.
- **`cli_commands/` owns user interaction:** argument parsing, prompts and confirmations, `--json`
  versus human output, and exit codes. Project methods never print, prompt or exit; they return
  data or raise, and the command decides how to show it.
- **Exception:** commands that run before a project exists (`login`, `apikey`, `setup`, `init`,
  `project list` / `create`) may call `AgentStudioInterface` directly. Some project-scoped commands that
  still do (`audio_cache.py`, `functions.py`, `conversations.py`) are leftovers to fix, not
  patterns to copy.
- New HTTP calls go through `PlatformAPIHandler.make_request`. If it lacks something you need,
  extend it.

## Where things go

| Path | What belongs there |
|---|---|
| `src/poly/cli.py` | Thin dispatcher that registers command classes. No logic. |
| `src/poly/cli_commands/` | One module per command family. See `src/poly/cli_commands/AGENTS.md`. |
| `src/poly/project.py` | `AgentStudioProject`: everything a command needs, scoped to one local project. |
| `src/poly/resources/` | One module per resource type that appears in the project projection. See `src/poly/resources/AGENTS.md`. |
| `src/poly/handlers/` | API clients: `interface.py` (facade), `platform_api.py` (REST), `sdk.py` (protobuf command queue), auth, GitHub, PostHog. |
| `src/poly/output/` | Terminal output (`console.py`) and `--json` output (`json_output.py`). |
| `src/poly/call/`, `src/poly/auth/` | Voice calls over WebRTC (the optional `[call]` extra), and the login device flow. |
| `src/poly/utils/` | Shared helpers: merge, credentials, JSON I/O, decorators, pre-push checks. |
| `src/poly/docs/` | Resource docs shipped in the wheel and served by `poly docs`. |
| `src/poly/tests/` | Tests, plus fixture projects in `test_projects/`. |
| `docs/docs/` | The public docs site (mkdocs). |
| `skills/` | **User-facing** agent skills, installed into users' projects by `poly setup` / `poly update`. |
| `.claude/skills/` | **Contributor** skills for working on this repo (`ci-check`, `review-pr`, `write-tests`, `add-resource-type`, `open-pr`). Marked `metadata.internal: true` so `poly setup` never installs them. |

Generated, never edit by hand: `src/poly/handlers/protobuf/` and `src/poly/types/`.

## Conventions

- **Reuse before writing.** Use `make_request`, `load_yaml` / `dump_yaml` (`resources/resource_utils.py`),
  each resource's `discover_resources`, `load_project` (`cli_commands/shared.py`) and
  `json_print`. Don't add a parallel helper.
- **Match sibling commands.** Same flag names (`--json`, `--path`, `--force`), and `--json`
  skips confirmation prompts. Most commands are scoped to a project, and regions are written `us-1` /
  `euw-1` / `uk-1`. Use the existing name for a concept; don't invent a new one.
- **Delete, don't shim.** When a platform field or behaviour is removed, delete it from the ADK.
  Don't keep back-compat paths or code nothing uses.
- **Validate locally.** Anything the platform would reject on push should fail in
  `poly validate` / pre-push first. A pull followed by a push must round-trip with no changes.
- **Guard side effects.** Deletes touch only files the ADK owns. Anything that reaches `live`
  says so in its prompt and help text.
- **Code style:** 100-char lines, type hints and docstrings on public functions, absolute
  `poly.` imports, `ValueError` for validation and `SourcererAPIError` (`handlers/sdk.py`) for
  API failures. User output goes through `output/console.py` or `json_print` in the CLI layer,
  diagnostics through `logging.getLogger(__name__)`, and never a bare `print`.
- **Comments explain why, briefly.** No narration of the change, and no stray files (scratch
  scripts, `BUILD.bazel`, editor settings) in the diff.

## Tests

- Add to the existing test file and class for the area (e.g. `resources_test.py`, `cli_test.py`,
  `tests/api/`, `tests/call/`). Create a new file or class only when nothing fits.
- When a resource gains a field or a new resource type is added, add it to
  `src/poly/tests/test_projects/test_project/` too.
- Prefer real objects and the fixture projects over mocks, and mock only at the API boundary.

## Docs and skills

A user-facing change updates, in the same PR:
- `docs/docs/`: the command page in `reference/cli/` and any `development/` guide that covers it.
  Pages in `reference/cli/` and `reference/resources/` follow the `AGENTS.md` in those directories.
- `src/poly/docs/`, when a resource's YAML shape changes (it backs `poly docs`).
- `skills/`, when a command, flag or workflow that a skill mentions changes.

Docs are public. Don't name real customers, projects or internal tools.

## Dependencies

Run `uv run licensecheck --zero` and `uv run pip-licenses`, and commit `licenses.json`. Heavy or
platform-specific dependencies go in an optional extra (like `[call]`), not the base install.

## Pull requests and releases

Every merge to `main` can release. The PR title becomes the squash commit, the version bump and
the public release note.

| Title type | Release |
|---|---|
| `feat:` | Minor. Anything a user can see, including output or on-disk changes. |
| `fix:`, `perf:` | Patch |
| `feat!:` or a `BREAKING CHANGE:` footer | Major |
| `chore:`, `docs:`, `ci:`, `build:`, `refactor:`, `style:`, `test:` | No release |

- **Never edit version numbers by hand.** semantic-release sets `pyproject.toml`'s version,
  stamps every `skills/*/SKILL.md` `version:` and writes `CHANGELOG.md`. Adding a user skill
  means adding it to `version_variables` in `pyproject.toml`.
- Fill in `.github/PULL_REQUEST_TEMPLATE.md`, using its sections only.
- **No ticket IDs** (Linear or otherwise) in the PR title or description. Link the ticket in a PR
  comment instead.
- No internal client names, project IDs, internal repos, services or tooling anywhere in a PR.
  The repo is public.
- Stacked PRs merge bottom-up. Retarget each one to `main` after the PR below it merges.
- One concern per PR. Small related fixes are fine; structural refactors get their own PR.
