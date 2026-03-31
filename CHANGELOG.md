# CHANGELOG


## v0.6.2 (2026-03-31)

### Bug Fixes

- **API Integration**: Generate API integration IDs in server-expected format
  ([#53](https://github.com/polyai/adk/pull/53),
  [`c82e7dc`](https://github.com/polyai/adk/commit/c82e7dc625a1b9f7a027c39dc17abc1e47c34980))

## Summary - `generate_uuid` was building API integration IDs using the resource name key
  (`api_integration` → `API_INTEGRATION-<hex>`), but the server validates against a regex that
  expects `API-INTEGRATION-<UPPERCASE_HEX>` - Fix uses `resource_id_prefix` from the resource class
  (when defined) with uppercase hex, matching the server's expected format (e.g.
  `API-INTEGRATION-2861A95D`) - Other resource types are unaffected — the fallback path is unchanged

## Test plan - [x] Existing `ApiIntegrationTest` suite passes (`uv run pytest src/poly/tests/ -v -k
  api_integration`) - [x] Push a new API integration and verify it is accepted by the server without
  a `ZodValidationError`

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Auto-update from feat(cli): machine-readable --json, projection-based pull/push, and serialized
  push commands ([#46](https://github.com/polyai/adk/pull/46),
  [`dee84ef`](https://github.com/polyai/adk/commit/dee84ef3ad0d901496c74eea8fa0a1354d2976f8))

## Summary

This PR is related to https://github.com/polyai/adk/pull/41

## Motivation

This is the first trial run of the docs auto-update workflow that was added to
  https://github.com/polyai/adk/pull/35

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

---------

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>


## v0.6.1 (2026-03-30)

### Bug Fixes

- Update poly review --delete to interactive select-and-delete flow
  ([#47](https://github.com/polyai/adk/pull/47),
  [`9ea826a`](https://github.com/polyai/adk/commit/9ea826aba9837073172dd28bffc3c2e22a9684c9))

## Summary - Updates gist description format from `Diff for account/project` to `project: local →
  remote` / `project: before → after` - Replaces `poly review --delete` bulk-delete with a
  `questionary.checkbox` prompt so users can select individual gists to delete - Adds `poly review
  --list` to interactively select and open a gist in the browser - Adds `list_diff_gists()` and
  `delete_gist()` helpers to `GitHubAPIHandler`; refactors `delete_diff_gists()` to use them - Exits
  gracefully with a warning if no gists exist or none are selected - Adds `--json` flag for
  outputting results using JSON - Adds unit tests for gist commands in `tests/review_test.py` -
  Converts `poly review list` and `poly review delete` from a positional `action` argument to proper
  argparse subparsers, so each subcommand owns only its relevant flags (`--id` now only appears
  under `poly review delete --help`) - Applies the same refactor to `poly branch` (`list`, `create`,
  `switch`, `current`), so `--force`, `--format`, `--from-projection` etc. only appear under `poly
  branch switch --help` for standardisation

## Test plan - [x] Run `poly review` to create one or more review gists - [x] Run `poly review
  --delete` and verify the checkbox menu appears listing gists by description - [x] Select a subset
  and confirm only those are deleted - [x] Run again with no gists present and confirm "No review
  gists found." message - [x] Press Ctrl-C / select nothing and confirm "No gists selected.
  Exiting." warning - [x] Run `poly review --list` and confirm a select menu appears; selecting a
  gist opens it in the browser

<img width="942" height="413" alt="image"
  src="https://github.com/user-attachments/assets/abace417-edc0-4d5f-ac87-fa20832e0bb6" /> <img
  width="711" height="62" alt="image"
  src="https://github.com/user-attachments/assets/44a03254-03cc-4265-8ed0-9d590313df5b" /> <img
  width="637" height="72" alt="image"
  src="https://github.com/user-attachments/assets/91ef9899-9666-479f-94ec-9084e488253e" /> <img
  width="664" height="215" alt="image"
  src="https://github.com/user-attachments/assets/b57168a2-999e-4450-a166-42e92a429ee0" /> <img
  width="341" height="75" alt="image"
  src="https://github.com/user-attachments/assets/19b83928-5a20-4e05-a51a-73c549383db2" />

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

Co-authored-by: Ruari Phipps <ruari@poly-ai.com>


## v0.6.0 (2026-03-27)

### Features

- Add resource caching and progress spinner for init/pull/branch
  ([#50](https://github.com/polyai/adk/pull/50),
  [`2d4fc0a`](https://github.com/polyai/adk/commit/2d4fc0ae78c348d0cc9269d7f0749c83a06adedd))

## Summary

Batch `MultiResourceYamlResource` writes during `poly init` so each YAML file is written once
  instead of once per resource, and add a progress spinner to `init`, `pull`, and `branch switch` so
  the CLI doesn't appear stuck on large projects.

Also edited CONTRIBUTING.md to edit the clone url - changed org to PolyAI.

## Motivation

`poly init` is very slow on projects with many pronunciations (or other multi-resource YAML types)
  because `save()` rewrites the full YAML file for every single item. On large projects like pacden,
  the process appears stuck with no output. The `save_to_cache` + `write_cache_to_file` pattern
  already exists for `poly pull` — this reuses it for `init` and adds a progress spinner across all
  three commands.

## Changes

- Use `save_to_cache=True` for all `MultiResourceYamlResource` saves during `init_project()`, then
  flush to disk once via `write_cache_to_file()` - Add an optional `on_save(current, total)`
  callback to `init_project()`, `pull_project()`, `_update_multi_resource_yaml_resources()`,
  `_update_pulled_resources()`, and `switch_branch()` for progress reporting - Wire up
  `console.status()` spinners in `cli.py` for `init`, `pull`, and `branch switch`, using
  `nullcontext` to skip the spinner in `--json` mode - Progress counter includes both multi-resource
  (per batch total) and non-multi-resource types for an accurate total

- CONTRIBUTING.md to edit the clone url - changed org from PolyAI-LDN to PolyAI.

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (361 tests, 0 failures)
  - [x] No breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit
  messages follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs Before: <img width="1683" height="1066" alt="Screenshot 2026-03-25 at 10 04
  14 PM" src="https://github.com/user-attachments/assets/0dd22d4d-7c3a-4342-9dd4-3d6d1ec4c2ff" />

After: <img width="1693" height="322" alt="Screenshot 2026-03-25 at 10 04 01 PM"
  src="https://github.com/user-attachments/assets/b1f8441f-498c-40a3-bc3c-e7093c56c0a5" />


## v0.5.1 (2026-03-27)

### Bug Fixes

- Display branch name instead of branch id ([#45](https://github.com/polyai/adk/pull/45),
  [`5a54240`](https://github.com/polyai/adk/commit/5a54240418d1848d195af23e87b3cb7005462d4b))

## Summary Display new branch name in CLI when the tool switches branch

## Motivation On push when creating a new branch, users would be shown branch ID not new branch name

## Changes

- Change logger level for some logs to hide on usual CLI usage - Make it more clear when a branch id
  is used in logs - When branch_id changes, output this in CLI with new branch name - Update auto
  branch name to exclude `sdk-user`

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="428" height="126" alt="Screenshot 2026-03-26 at 15 54 24"
  src="https://github.com/user-attachments/assets/39a17de0-7395-4f0c-9cd2-898043cc322c" />

---------

Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>


## v0.5.0 (2026-03-26)

### Features

- **cli**: Machine-readable --json, projection-based pull/push, and serialized push commands
  ([#41](https://github.com/polyai/adk/pull/41),
  [`cb91e2a`](https://github.com/polyai/adk/commit/cb91e2abffe97dfdbc6e3db8770f16a369f6da29))

## Summary

Adds a global-style `--json` mode across `poly` subcommands so stdout is a single JSON object for
  scripting and CI. Introduces `--from-projection` / optional projection output for `init` and
  `pull`, and `--output-json-commands` on `push` to include the queued Agent Studio commands (as
  dicts). Moves console helpers under `poly.output` and adds `json_output` helpers (including
  protobuf → JSON via `MessageToDict`).

## Motivation

Operators and automation need stable, parseable CLI output and the ability to drive pull/push from a
  captured projection (without hitting the projection API). Exposing staged push commands supports
  dry-run review and integration testing.

Closes #23

## Changes

- Wire `json_parent` (`--json`) into relevant subparsers; many code paths now emit structured JSON
  and exit with non-zero on failure where appropriate. - Add `--from-projection` (JSON string or `-`
  for stdin) to `pull` and `push`; `SyncClientHandler.pull_resources` uses an inline projection when
  provided instead of fetching. - Add `--output-json-projection` on `init` / `pull` (and related
  flows) to include the projection in JSON output when requested. - Add `--output-json-commands` on
  `push` to append serialized commands to the JSON payload; `push_project` returns `(success,
  message, commands)`. - `pull_project` returns `(files_with_conflicts, projection)`;
  `pull_resources` returns `(resources, projection)`. - New `poly/output/json_output.py`
  (`json_print`, `commands_to_dicts`); relocate `console.py` to `poly/output/console.py` and update
  imports. - Update `project_test` mocks/expectations for new return shapes; `uv.lock` updated for
  dependencies.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

**Note for reviewers:** The **CLI** remains backward compatible (new flags only).
  **`AgentStudioProject.pull_project` / `push_project`** (and `pull_resources` on the handler)
  **change return types** vs `main`; any direct Python callers must be updated to unpack the new
  tuples and optional `projection_json` argument.

## Screenshots / Logs

<!-- Optional: example `poly status --json`, `poly push --dry-run --output-json-commands`, `poly
  pull --from-projection - < proj.json` -->

---------

Co-authored-by: Oliver Eisenberg <Oliver.Eisenberg@Poly-AI.com>

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.4.1 (2026-03-26)

### Bug Fixes

- Error on merges ([#44](https://github.com/polyai/adk/pull/44),
  [`b3d8d62`](https://github.com/polyai/adk/commit/b3d8d62b8b36e476f7027691d0d18da33edf9a74))

## Summary Fix issue where merges were marked as successful when there is an internal API error

## Motivation

This error breaks pipelines that rely on this output

Closes #<!-- issue number -->

## Changes

- Make success response more explicit instead of relying on errors/conflicts lists

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Guard uv.lock checkout in coverage workflow ([#42](https://github.com/polyai/adk/pull/42),
  [`2383405`](https://github.com/polyai/adk/commit/238340568a8bdbe8ece9612f94d7bd7664154fad))

## Summary

- Prevent coverage CI from failing when `uv.lock` is absent on a branch - Wrap both `git checkout --
  uv.lock` calls with a conditional `git rev-parse --verify` check before and after the base branch
  checkout step

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

### Chores

- Add pytest-cov and coverage to dev dependencies ([#36](https://github.com/polyai/adk/pull/36),
  [`649ccb7`](https://github.com/polyai/adk/commit/649ccb7d10f3ce59ba9e0f0094bf93b3c90736a7))

## Summary - Adds `pytest-cov>=6.0.0` and `coverage>=7.0.0` to the `[dev]` optional dependencies in
  `pyproject.toml`

## Test plan - [x] Run `uv pip install -e ".[dev]"` and verify `pytest-cov` and `coverage` install
  successfully <img width="557" height="135" alt="image"
  src="https://github.com/user-attachments/assets/9e669897-c974-4e37-a2a3-8a3c6ed37c3a" />

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Fix formatting issues ([#40](https://github.com/polyai/adk/pull/40),
  [`eafff58`](https://github.com/polyai/adk/commit/eafff58ab877a65d3fd204a850bcb7489083a1fa))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. -->

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.4.0 (2026-03-25)

### Bug Fixes

- Update API key reference in auto-update-docs workflow
  ([#38](https://github.com/polyai/adk/pull/38),
  [`d9de6fe`](https://github.com/polyai/adk/commit/d9de6fe84cbf70b42262e78f92058325c6b9167c))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. -->

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

---------

Co-authored-by: Benjamin Levin <bplevin36@gmail.com>

### Documentation

- Agentic docs-update workflow ([#35](https://github.com/polyai/adk/pull/35),
  [`b330cc6`](https://github.com/polyai/adk/commit/b330cc6e4e75c0d138b3c2b2bc06e5be3827d40d))

## Summary

Adds a GitHub Actions workflow that automatically keeps the docs in sync with the codebase. Every
  time a PR is merged to main that touches \`src/\`, the workflow diffs what changed, sends the diff
  and all current docs to Claude, and opens a new PR with any suggested updates for human review
  before they are merged.

## Motivation

The docs are fully hand-maintained today. Any new CLI flag, changed command behaviour, new resource
  type, or schema change requires a manual docs PR — and that update often doesn't happen. This
  automates the detection and drafting of those updates.

## Changes

- **\`.github/workflows/auto-update-docs.yaml\`** — triggers on push to main when \`src/\` changes,
  runs the agent script, opens a docs PR if anything was updated -
  **\`docs/scripts/update_docs.py\`** — gets the git diff, reads all current markdown files
  (reference pages first), calls Claude with both, and writes back any files Claude says need
  updating. PR body written to \`/tmp/pr_summary.md\` for the workflow to use

## Test strategy

- [x] N/A (docs, config, or trivial change)

> The \`build-docs.yaml\` workflow runs \`mkdocs build --strict\` on every PR — that is the
  validation gate for the docs side. The agent workflow is triggered by source code merges, not this
  PR, so it will not self-test. To test manually: merge a code PR touching \`src/\` and check the
  Actions tab for the \`Auto-update docs\` run.

## Checklist

- [x] No breaking changes to the \`poly\` CLI interface - [x] Commit messages follow [conventional
  commits](https://www.conventionalcommits.org/)

## Setup required

One secret must be added before the workflow will do anything:

**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value | |---|---| | \`ANTHROPIC_API_KEY\` | Anthropic API key (personal or shared team key)
  |

\`GITHUB_TOKEN\` (used to open the docs PR) is provided automatically by GitHub — no setup needed.

## How it works

1. Engineer merges a PR that changes \`src/\` 2. \`auto-update-docs\` workflow fires and diffs
  \`HEAD~1..HEAD\` 3. Claude reads the diff and all 32 docs pages (reference pages first),
  identifies anything stale 4. Script writes updated files to disk; PR body written to
  \`/tmp/pr_summary.md\` 5. Workflow opens a PR: \`docs: auto-update from <sha>\` 6. Engineer
  reviews, edits if needed, and merges

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Removing the em-dashes from the docs ([#33](https://github.com/polyai/adk/pull/33),
  [`e643138`](https://github.com/polyai/adk/commit/e643138294465a84ab9be9128b360b324bb0205b))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. -->

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Update licensing ([#30](https://github.com/polyai/adk/pull/30),
  [`0a2bd75`](https://github.com/polyai/adk/commit/0a2bd75ab3e383ad07703dbf4f107663a3ddbf0c))

## Summary

Update licensing page to point to `licenses.json`. Also include missing MLP license text Fixes
  deployment for docs

## Motivation

Use `licenses.json` as the one source of truth, to avoid having to maintain two lists

## Changes

- Update main license info, remove table and point to licenses.json - Remove GNU license text - Add
  MLP license text - Update docs build and deploy steps to point to the correct place

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Aaron Forinton <89849359+AaronForinton@users.noreply.github.com>

- Update tooling info ([#32](https://github.com/polyai/adk/pull/32),
  [`1e322e6`](https://github.com/polyai/adk/commit/1e322e61ecd61520defe86144a3b4cf9592269f6))

## Summary

Documents the poly docs --output flag and the rules file workflow for AI coding tools across the CLI
  reference and Build an agent tutorial.

## Motivation

Discussions in Slack

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Features

- Add API Integrations ([#31](https://github.com/polyai/adk/pull/31),
  [`f856884`](https://github.com/polyai/adk/commit/f856884da1f11ede25aba539fab16d25e8dcfb9f))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. --> - Adds support for creating API
  Integrations using `yaml` files. - API Secrets are still managed by the UI - Updates docs

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Aligns with Agent Studio features

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

- API Integrations yaml file can be created in the `/config` dir.

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.3.3 (2026-03-19)

### Bug Fixes

- Fix merge for multiresourceyaml resources (#122) ([#28](https://github.com/polyai/adk/pull/28),
  [`054d552`](https://github.com/polyai/adk/commit/054d55282ef5933f51b1f783ac70440d17c1481b))

## Summary Fix incorrect merge behaviour for `MultiResourceYamlResource` types by performing the
  3-way merge at the file level rather than per-resource.

## Motivation `MultiResourceYamlResource` types (e.g. entities) store multiple resources in a single
  YAML file. The previous code performed the 3-way merge per-resource and then wrote each resource
  individually, which meant the common ancestor used for the merge was wrong and resources from the
  same file would overwrite each other. It would also crash. <img width="415" height="133"
  alt="image (1)"

src="https://github.com/user-attachments/assets/388eff5f-2185-4a5b-ab5f-0b32f866452d" />

## Changes - Before the merge loop, serialise the original resources into a file-level cache to use
  as the common ancestor - Skip the per-resource string merge for `MultiResourceYamlResource` types
  during the main loop; instead accumulate them into the cache - After the main loop, perform the
  3-way merge at the file level and write the result - Gate `write_cache_to_file` behind `force`
  mode, since non-force mode now handles writing via the file-level merge loop

## Test strategy - [x] Added/updated unit tests - [x] Manual CLI testing (`poly pull`) - [x] Tested
  against a live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist - [ ] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/) - [ ] ## Screenshots / Logs
  <img width="1291" height="582" alt="Screenshot 2026-03-13 at 18 57 34"
  src="https://github.com/user-attachments/assets/44a0cf5d-7024-42c4-8b51-8b2b3fc1b267" />

---------

Co-authored-by: Copilot Autofix powered by AI <175728472+Copilot@users.noreply.github.com>


## v0.3.2 (2026-03-18)

### Bug Fixes

- Add missing variable referencing sms ([#29](https://github.com/polyai/adk/pull/29),
  [`c1469f7`](https://github.com/polyai/adk/commit/c1469f786803f58f6b591c9dfe844b52e113cde3))

## Summary SMS text should be able to reference variables, add this with validation

## Changes

- Have variable swap for SMS templates - Add validations

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.3.1 (2026-03-17)

### Bug Fixes

- Reference variables even if commented out ([#21](https://github.com/polyai/adk/pull/21),
  [`4298d09`](https://github.com/polyai/adk/commit/4298d09f00357046547b3f01473a875228d7a117))

## Summary AS allows references even if commented out. Align here

## Changes - Don't remove comments when searching for variables

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.3.0 (2026-03-16)

### Features

- Add shell completion for bash, zsh, and fish ([#22](https://github.com/polyai/adk/pull/22),
  [`2c563ff`](https://github.com/polyai/adk/commit/2c563ffa77fcc01567dcb18b9c832f296acb2415))

## Summary

Adds a `poly completion <shell>` command that prints a shell completion script, enabling tab
  completion for all `poly`/`adk` commands, subcommands, and flags.

## Motivation

Shell completion is a standard ergonomic feature for any CLI tool — especially one with 12+
  subcommands and numerous flags. Without it, users must remember exact command names and flags,
  slowing down daily use. Every major comparable CLI (Google ADK, AWS AgentCore, `gh`, `kubectl`)
  ships with completion support.

## Changes

- Add `argcomplete>=3.0.0` dependency (Apache 2.0 — passes license checks) - Call
  `argcomplete.autocomplete(parser)` in `main()` — this is the hook that makes tab completion work
  at runtime; it exits immediately when not in a completion context, so there is zero overhead for
  normal CLI usage - Add `completion` subparser with `bash`, `zsh`, `fish` choices and per-shell
  installation instructions in the help text - Add `AgentStudioCLI.print_completion()` classmethod -
  Both `poly` and `adk` entry points are registered in the generated scripts

## Usage

```bash # Bash — add to ~/.bashrc or ~/.bash_profile eval "$(poly completion bash)"

# Zsh — add to ~/.zshrc eval "$(poly completion zsh)"

# Fish — add to ~/.config/fish/completions/poly.fish poly completion fish | source ```

## Test strategy

- [x] Added unit tests for all three shells and invalid shell rejection - [ ] Manual CLI testing
  (`poly <command>`) - [ ] Tested against a live Agent Studio project - [ ] N/A (docs, config, or
  trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.2.3 (2026-03-16)

### Bug Fixes

- Read ASR and DTMF if not included ([#20](https://github.com/polyai/adk/pull/20),
  [`bc5add7`](https://github.com/polyai/adk/commit/bc5add7c31d3decaad5e1bd568c12c4dfdddfe75))

## Summary If ASR and DTMF not included, still read them as defaults

## Motivation Would error if created without these fields

## Changes - Filter on None not empty dicts

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.2.2 (2026-03-13)

### Bug Fixes

- Bump version manually with wording update ([#19](https://github.com/polyai/adk/pull/19),
  [`680fd6d`](https://github.com/polyai/adk/commit/680fd6db386389fca1368e6d2770c302c63b03b6))

## Summary Should bump and release version to 0.2.2

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.2.1 (2026-03-13)

### Bug Fixes

- Remove old docs files ([#16](https://github.com/polyai/adk/pull/16),
  [`1038e5e`](https://github.com/polyai/adk/commit/1038e5ebfad53b9d3b17ae1637c0b65dcf0bba29))

## Summary

Remove old docs files and prompt bulid

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Continuous Integration

- Build before pushing ([#15](https://github.com/polyai/adk/pull/15),
  [`bff82df`](https://github.com/polyai/adk/commit/bff82df58c2883fd2daab69addc00513d02042e6))

## Summary Build before pushing, delete any existing egg

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Bump manually ([#18](https://github.com/polyai/adk/pull/18),
  [`041a8f2`](https://github.com/polyai/adk/commit/041a8f2ee2d4f4549c6b00c670ae9dd993f7a78b))

## Summary Bump manually

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Fix release ([#17](https://github.com/polyai/adk/pull/17),
  [`bbce7d8`](https://github.com/polyai/adk/commit/bbce7d877b8a70dd6ae9478c854e99728db374d9))

## Summary Re-add semantic release into pyproject.toml

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Features

- Copy across recent updates/fixes ([#12](https://github.com/polyai/adk/pull/12),
  [`088b596`](https://github.com/polyai/adk/commit/088b596098737922cf9cf2c89bc6cff84bd87343))

## Summary - Use questionary instead of simple_term_menu so it's compatible on windows - Match flow
  step validation to platform - Add ci steps for license checks - Fix creating new flow with
  function step as start step

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.1.1 (2026-03-13)

### Bug Fixes

- Fix docs command ([#13](https://github.com/polyai/adk/pull/13),
  [`6428293`](https://github.com/polyai/adk/commit/6428293a834b72bff6e6e90faba448962f4e8d1f))

## Summary

Relocate docs for website into root of repo Return initial docs included for the `poly docs` command

## Motivation `poly docs` not working

## Changes - Move folder into root of repo - Readd initial docs - Update Github actions to point to
  current docs

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Continuous Integration

- Add PR title validation for conventional commits ([#11](https://github.com/polyai/adk/pull/11),
  [`8cce472`](https://github.com/polyai/adk/commit/8cce4728265114ec2ccdfa14b5cd039af93545cc))

## Summary

Adds a CI job that validates PR titles follow the conventional commits format defined in
  CONTRIBUTING.md.

## Motivation

PR titles that don't follow conventional commits break semantic-release versioning since it parses
  commit messages (squash-merged from PR titles) to determine version bumps.

## Changes

- Added `pr-title` job to `.github/workflows/ci.yml` that runs only on `pull_request` events -
  Validates titles match `<type>[optional scope][!]: <description>` where type is one of: `feat`,
  `fix`, `chore`, `docs`, `ci`, `build`, `perf`, `refactor`, `style`, `test` - Uses environment
  variable for the PR title (not direct interpolation) to prevent script injection

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Example failure output: ``` ::error::PR title does not follow conventional commits format.

Expected: <type>[optional scope][!]: <description>

Types: feat, fix, chore, docs, ci, build, perf, refactor, style, test

Examples: feat: add poly export command fix(cli): handle missing config file feat!: redesign
  resource schema

See CONTRIBUTING.md for details. ```

- Update docs workflow and limit Release ([#14](https://github.com/polyai/adk/pull/14),
  [`1313749`](https://github.com/polyai/adk/commit/1313749b644b3dd4bc0f881232c13b402c031e7b))

## Summary Update docs workflow and limit release

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Documentation

- Add CONTRIBUTING.md and rename Local Agent Studio to ADK
  ([#7](https://github.com/polyai/adk/pull/7),
  [`0ed7729`](https://github.com/polyai/adk/commit/0ed7729936c22aded9b3680436fd1269521e7225))

## Summary

Add a dedicated CONTRIBUTING.md with dev setup and contribution guidelines extracted from the
  README. Rename all references from "Local Agent Studio" / "local_agent_studio" to "ADK" across the
  codebase.

## Motivation

The README was getting long with dev setup details mixed in, and the old project name was still
  referenced in many places.

## Changes

- Created `CONTRIBUTING.md` with dev setup, project structure, code style, commit conventions, and
  tooling sections - Replaced README dev setup and contributing sections with a link to
  `CONTRIBUTING.md` - Replaced broken dynamic Python version badge with a static `Python 3.14` badge
  - Updated all `local_agent_studio` GitHub URLs to `adk` - Renamed "Local Agent Studio" to "ADK" in
  docstrings, comments, error messages, and docs across 9 files

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

- Enhance README with ADK usage and early access info ([#10](https://github.com/polyai/adk/pull/10),
  [`f8b303d`](https://github.com/polyai/adk/commit/f8b303d79e32b6c5dd2119a37f2e27edae460c99))

Updated README to include ADK usage instructions and prerequisites.

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. -->

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Move Releases section from README to CONTRIBUTING.md ([#8](https://github.com/polyai/adk/pull/8),
  [`cc4e45d`](https://github.com/polyai/adk/commit/cc4e45d78a6743712f644b2159f7e26752e8e1cd))

## Summary

Move the Releases section from README.md into CONTRIBUTING.md to keep the README focused on usage.

## Motivation

Release workflow details are contributor-facing information and belong alongside dev setup and
  commit conventions in CONTRIBUTING.md.

## Changes

- Removed Releases section from README.md - Added Releases section to CONTRIBUTING.md (before
  Tooling)

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.1.0 (2026-03-13)

### Continuous Integration

- Remove build command ([#6](https://github.com/polyai/adk/pull/6),
  [`a5a4ed9`](https://github.com/polyai/adk/commit/a5a4ed982979e1d2d25093fb46ed3a0e940ad74a))

## Summary Remove build command as semantic release already builds

## Motivation Running build twice causes an issue

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Features

- Clean codebase
  ([`ff2fa71`](https://github.com/polyai/adk/commit/ff2fa713fbd5fddf9c55851223daada6285620b0))

feat: clean codebase
