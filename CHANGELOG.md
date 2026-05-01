# CHANGELOG


## v0.16.0 (2026-05-01)

### Bug Fixes

- Format for multi-resource YAML files ([#119](https://github.com/polyai/adk/pull/119),
  [`cbc96fc`](https://github.com/polyai/adk/commit/cbc96fcd199883ddfe0506cfaa1bd604c78e5879))

## Summary

Fix formatting for `MultiResourceYamlResource` types and refactor YAML/JSON formatting utilities.

## Motivation

`_format_resources` treated multi-resource virtual paths as literal file paths, causing format to
  fail for any `MultiResourceYamlResource` (entities, handoffs, etc.). The YAML dump pipeline also
  had redundant recursive walks and created a new YAML resolver instance on every string value.

## Changes

- Fix `_format_resources` to format multi-resource YAML at the whole-file level instead of per
  virtual sub-path - Fix `format_files` to match on the true `.yaml` path, not just the virtual
  sub-path - Only write files that actually changed after formatting - Consolidate
  `_quote_keys_for_yaml` + `set_block_style_for_multiline_strings` into single-pass
  `_prepare_yaml_data` - Cache YAML resolver at module level instead of creating a new instance per
  call - Collapse `format_yaml` / `format_yaml_python` into one function - Rename
  `format_json_python` → `format_json` - Fix `ExperimentalConfig.raw` JSON indent 4→2

## Test strategy

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (545 tests) - [ ] Manual
  CLI testing (`poly format`) - [ ] Tested against a live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- [small docs update] show clear error when POLY_ADK_KEY is not set
  ([#124](https://github.com/polyai/adk/pull/124),
  [`47b2db1`](https://github.com/polyai/adk/commit/47b2db1baaa0b46f513c5631c19c73637a242227))

## Summary

PR #110 (very small change)

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

---------

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

### Features

- Support per-region API keys via POLY_ADK_KEY_{REGION} for the incoming PAT change
  ([#123](https://github.com/polyai/adk/pull/123),
  [`94cb27b`](https://github.com/polyai/adk/commit/94cb27b607ffdabcea75896ffbcc01f0406b90c0))

## Summary

- `retrieve_api_key()` now accepts an optional `account_id` parameter - When provided, tries
  `POLY_ADK_KEY_{SUFFIX}` first (e.g. `POLY_ADK_KEY_US`), then falls back to `POLY_ADK_KEY` - This
  adds support for PAT which are incoming.

## Test plan

- [x] Lint passes (`ruff check`) - [x] Format passes (`ruff format --check`) - [x] All 552 tests
  pass - [x] Manual: set `POLY_ADK_KEY_US=<key>` and run `poly init` - [x] Manual: update
  POLY_ADK_KEY_US=<key>` to fail and set `POLY_ADK_KEY` — should fall back gracefully - [x] Manual:
  unset both — should show the existing error message

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.15.3 (2026-05-01)

### Bug Fixes

- Show clear error when POLY_ADK_KEY is not set ([#110](https://github.com/polyai/adk/pull/110),
  [`b066753`](https://github.com/polyai/adk/commit/b0667534c82468ab69c83f664c0146afda48a50c))

## Summary - Running `poly init` without `POLY_ADK_KEY` set now shows `POLY_ADK_KEY environment
  variable is not set. Export your API key with: export POLY_ADK_KEY=<your-api-key>` instead of the
  misleading "No accessible regions found for your API key." - Adds early env var check in
  `init_project` before any API calls - Fixes `_retrieve_api_key` in both `PlatformAPIHandler` and
  `SyncClientHandler` to raise immediately when the key is missing (previously `os.getenv()`
  silently returned `None`)

## Test plan - [x] Lint passes (`ruff check`) - [x] Format passes (`ruff format --check`) - [x] All
  500 tests pass - [x] Manual: run `unset POLY_ADK_KEY && poly init` and verify the new error
  message <img width="569" height="48" alt="image"
  src="https://github.com/user-attachments/assets/9d227ac8-c847-49ac-a4c8-39843d7ab3e3" />

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- Lead with bare poly init, treat ID flags as escape hatch
  ([#122](https://github.com/polyai/adk/pull/122),
  [`25bda57`](https://github.com/polyai/adk/commit/25bda579ec5960d56992a363f3c39ffb53d32865))

## Summary

Customer onboarding feedback from Naorin: users hit \`poly init --account_id <account_id>
  --project_id <project_id>\` in the docs and don't know what to fill in. They should just be able
  to run \`poly init\` — the CLI walks them through dropdowns to pick the project. Updates the docs
  across index, get-started, tutorials, anti-patterns, and CLI reference to lead with the bare form
  and present the flag form as a script/CI escape hatch.

## Motivation

Naorin (in #docs):

> they should just be able to do poly init

Onboarding session at a customer office got stuck on this exact question.

## Verification

Cross-checked against \`src/poly/cli.py:1231-1330\` — \`init_project\` with no arguments:

1. Calls \`get_accessible_regions()\` and either auto-selects (one region) or prompts via
  \`questionary.select\`. 2. Calls \`get_accounts(region)\` and either auto-selects (one account) or
  prompts with a searchable dropdown. 3. Calls \`get_projects(region, account_id)\` and prompts with
  a searchable dropdown.

Verified live during PR #114 testing — \`poly init\` against my workspace auto-selected
  region+account and would have surfaced the project dropdown if I hadn't been running
  non-interactively. The flag form remains required for \`--json\` mode (see \`reference/cli.md\`
  JSON output section).

## Changes

- **\`index.md\`** — "Three commands" snippet now uses bare \`poly init\`. -
  **\`get-started/first-commands.md\`** — leads with \`poly init\`, adds a numbered list describing
  the dropdown flow; flag form moves to a "Skip the prompts" tip. -
  **\`get-started/get-started.md\`** — Step 6 and the "Already have an agent" section both updated.
  - **\`tutorials/build-an-agent.md\`** — Step 1 same treatment. The AI-agent workflow section keeps
  the explicit flag form because that flow runs unattended. -
  **\`tutorials/restaurant-booking-agent.md\`** — Initialize section same treatment. -
  **\`concepts/anti-patterns.md\`** — "Right" example uses bare \`poly init\`. -
  **\`reference/cli.md\`** — \`poly init\` section restructured: dropdown flow documented first,
  flag form positioned as a script/CI escape hatch. Examples reordered (bare \`poly init\` first,
  progressively more flags). The JSON-mode requirement at line 486 already reads correctly.

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (\`poly <command>\`) — \`poly init\`
  interactive flow verified during PR #114 walkthrough - [ ] Tested against a live Agent Studio
  project - [x] N/A (docs, config, or trivial change)

\`mkdocs build --strict\` passes.

## Checklist

- [ ] \`ruff check .\` and \`ruff format --check .\` pass - [ ] \`pytest\` passes - [x] No breaking
  changes to the \`poly\` CLI interface - [x] Commit messages follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.15.2 (2026-04-30)

### Bug Fixes

- Cross-platform path handling + add Windows CI ([#121](https://github.com/polyai/adk/pull/121),
  [`e70e937`](https://github.com/polyai/adk/commit/e70e9371e9a2a1cf629e055b5332c6499f89daf9))

## Summary - Fixes cross-platform bugs in production code where `file_path.split(os.sep)` failed on
  Windows because paths containing forward slashes weren't normalized first — adds
  `os.path.normpath()` before splitting - Normalizes topic names in `migration_utils.py` to always
  use `/` regardless of OS - Adds a `test-windows` CI job (`continue-on-error: true`) to catch
  platform-specific bugs - Updates test assertions to use `os.path.join()` instead of hardcoded
  forward-slash paths

## Production code changes | File | Fix | |---|---| | `src/poly/resources/function.py` |
  `os.path.normpath()` before `split(os.sep)` in `get_function_type()` and `read_local_resource()` |
  | `src/poly/resources/flows.py` | Same in `FlowStep` condition matching and
  `FunctionStep.read_local_resource()` | | `src/poly/resources/resource_utils.py` | Same in
  `get_flow_name_from_path()` | | `src/poly/migration_utils.py` | `os.path.relpath` returns
  OS-native separators; normalize to `/` for topic names |

## Test changes | File | Fix | |---|---| | `src/poly/tests/project_test.py` | `os.path.join()` in
  `get_diffs` assertions | | `src/poly/tests/resources_test.py` | `os.path.join()` for mock dict
  keys and file_path args; skip Unix-specific path test on Windows |

## Test plan - [x] CI passes on Ubuntu, Windows, and coverage

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.15.1 (2026-04-30)

### Bug Fixes

- Handle Windows drive-letter paths in multi-resource path parsing
  ([#120](https://github.com/polyai/adk/pull/120),
  [`1e6059f`](https://github.com/polyai/adk/commit/1e6059fba9c8a3d8d24a4c68abd234fcc331b3a1))

## Summary

On Windows, `poly validate`, `poly push`, and `poly status` fail with:

``` File not found: C:users\billlewis\...\voice\configuration.yaml ```

Note the missing `\` after `C:`.

### Root cause

`_parse_multi_resource_path` splits a path with `os.sep` then reassembles it with `os.path.join`. On
  Windows, `os.path.join('C:', 'users', ...)` produces a **drive-relative** path — `C:users\...` —
  not an absolute one.

```python >>> import ntpath >>> ntpath.join('C:', 'users', 'bill') 'C:users\\bill' # wrong —
  drive-relative

>>> ntpath.join('C:\\', 'users', 'bill') 'C:\\users\\bill' # correct — absolute ```

### Fix

Append `os.sep` to bare drive letters before joining:

```diff base_parts = parts[: yaml_idx + 1] + if base_parts[0].endswith(":"): + base_parts[0] +=
  os.sep yaml_file_path = ( ```

**Before:** `C:users\billlewis\project\voice\configuration.yaml` (broken) **After:**
  `C:\users\billlewis\project\voice\configuration.yaml` (correct)

## Test plan - [x] 7 new tests in `ParseMultiResourcePathTests` — Windows drive letters, Unix
  absolute paths, relative paths, error cases - [x] Full test suite passes (547 tests)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Continuous Integration

- Fix coverage comment for fork PRs ([#118](https://github.com/polyai/adk/pull/118),
  [`1c0f288`](https://github.com/polyai/adk/commit/1c0f28847b81b28f6672dc22cecf0fc15adac105))

## Summary

Split the coverage workflow into two so the PR comment can be posted with write permissions, even on
  fork PRs.

## Motivation

Fork PRs run with a read-only `GITHUB_TOKEN`, so the "Post coverage comment" step fails with a 403.
  The `workflow_run` event runs in the base repo's context and has full write access.

## Changes

- Removed PR comment and minimize steps from `coverage.yml`; it now only generates coverage data and
  uploads it as an artifact - Added `coverage-comment.yml` triggered by `workflow_run` to download
  the artifact and post/minimize comments with write permissions - Dropped `pull-requests: write`
  from `coverage.yml` since it no longer needs it

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

### Documentation

- Add standalone Branch merging reference page ([#114](https://github.com/polyai/adk/pull/114),
  [`f5509cd`](https://github.com/polyai/adk/commit/f5509cd4ec467f767fe6cdf2c595201a09a9ddf5))

## Summary

`poly branch merge` is rich enough to warrant its own page — conflict tables, `--interactive` flow,
  `--resolutions` JSON format, post-merge behavior, troubleshooting. This PR pulls that content out
  of `cli.md` into `reference/branch_merge.md` and threads cross-links into every other page that
  mentions branch merging.

## Motivation

Follow-up to #113. The merge story was buried five levels deep in `cli.md` and several other docs
  were either silent on the CLI path (`concepts/working-locally.md`,
  `get-started/what-is-the-adk.md`, `examples/venue-specific-goodbye.md`) or actively wrong about it
  ("branch merges still happen in Agent Studio"). A dedicated page makes it discoverable and gives
  the rest of the docs something to link to.

Also addresses the request to add inter-doc links throughout the ADK docs — every page that mentions
  branch merging now links into the new reference.

## Changes

### New page - `reference/branch_merge.md` — standalone reference covering: when to use, basic
  usage, argument table, conflict tables, `--interactive` flow with editor tip, `--resolutions`
  source forms (file / inline / stdin), JSON schema with example, combining flags, post-merge
  behavior, Agent Studio UI alternative, troubleshooting matrix, related-pages grid.

### CLI reference slim-down - `reference/cli.md` — `#### poly branch merge` keeps the three
  top-level examples and a stub link; the deep-dive content moves to the new page.

### Cross-links and stale-claim fixes - `concepts/working-locally.md` — platform-sync card and
  workflow step now mention `poly branch merge`. - `concepts/multi-user-and-guardrails.md` —
  workflow step and guardrails list updated; "branch merges still happen in Agent Studio" was wrong.
  - `get-started/what-is-the-adk.md` — intro paragraph reflects the CLI merge path. -
  `get-started/first-commands.md` — branch-chat troubleshooting links to the new page. -
  `examples/venue-specific-goodbye.md` — variant-resolution callout links to the new page. -
  `tutorials/build-an-agent.md` and `tutorials/restaurant-booking-agent.md` — merge callouts link to
  the new page for the conflict-resolution flow.

### Nav - `docs/mkdocs.yml` — adds `Branch merging: reference/branch_merge.md` to the Reference
  section.

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

`mkdocs build --strict` passes — every internal link resolves. Content cross-checked against
  `branch_merge_parser` in `src/poly/cli.py:628-657` and `merge_branch` in
  `src/poly/project.py:2662`.

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Align tutorials and CLI reference with actual ADK surface
  ([#113](https://github.com/polyai/adk/pull/113),
  [`2da9111`](https://github.com/polyai/adk/commit/2da91112f570275fa0f3ac9f4141116c2db988e7))

## Summary

Audit fixes against `src/poly/cli.py` and `src/poly/project.py`. Several places in the tutorials and
  CLI reference described behavior that does not match the code — most visibly Naorin's flag that
  `build-an-agent.md` claims "there is no `poly merge` command" when `poly branch merge` exists.

## Motivation

- Naorin flagged `poly merge` references in `build-an-agent.md` step 7 and step 13. The audit found
  a third occurrence and the same staleness in `restaurant-booking-agent.md`. - A wider sweep of
  recent merges turned up several `cli.md` examples that no longer parse against the real argparse
  definitions.

Closes Naorin's `#docs` thread on the `poly merge` references.

## Changes

### Tutorials - **`build-an-agent.md`** L290 / L313 / L489: replace "there is no `poly merge`
  command" with the real story — `poly branch merge '<commit message>'` (CLI) or merge in Agent
  Studio. Reword the "main branch of your sandbox" claim about `poly chat`; the real default is
  `--environment branch` (current branch), falling back to sandbox on `main`. -
  **`restaurant-booking-agent.md`** L604 / L608: same fixes.

### CLI reference (`reference/cli.md`) - `poly diff file1.yaml` → `poly diff --files file1.yaml`
  (the positional is `hash`, not a path). - `poly revert --all` → `poly revert` (no `--all` flag
  exists; bare invocation reverts everything). - `poly format file1.py` → `poly format --files
  <path>`. - `poly review` examples now use the required `create` subcommand. Bare `poly review` is
  a no-op — the dispatch only handles `create`/`list`/`delete`. - `poly revert --json --all` → `poly
  revert --json` in the JSON examples.

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

Verified each corrected command against `poly <command> --help` output and the argparse definitions
  in `src/poly/cli.py`. `mkdocs build --strict` passes.

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Fix safety filters page rendering ([#112](https://github.com/polyai/adk/pull/112),
  [`641a99f`](https://github.com/polyai/adk/commit/641a99f4ee7d671ee6e9c3c25bfde6ac56cc7499))

## Summary

Closes the `<p class="lead">` tag at the top of `docs/docs/reference/safety_filters.md`. The closing
  `</p>` was lost during the merge of #111, which caused mkdocs-material to treat the rest of the
  file as raw HTML and skip markdown rendering — the page shipped without styling.

## Motivation

The page on the live docs site rendered as unstyled plain text. Every other reference page closes
  the lead `<p>` (e.g.
  [agent_settings.md](https://github.com/polyai/adk/blob/main/docs/docs/reference/agent_settings.md),
  [voice_settings.md](https://github.com/polyai/adk/blob/main/docs/docs/reference/voice_settings.md))
  — this brings safety_filters in line.

## Changes

- Add closing `</p>` after the lead paragraph in `docs/docs/reference/safety_filters.md`.

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

Verified locally with `mkdocs build --strict`: lead paragraph now closes correctly, 3 grid card
  blocks and 10 H2 headings render in the output HTML.

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>

- Safety Filters docs rollout ([#111](https://github.com/polyai/adk/pull/111),
  [`01272b0`](https://github.com/polyai/adk/commit/01272b0edec1a7cd7f3538c6ec64b0b92ea4a5d5))

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
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

---------

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

Co-authored-by: Claude Opus 4.7 (1M context) <noreply@anthropic.com>


## v0.15.0 (2026-04-28)

### Documentation

- Store project name on init and clean up on API errors
  ([#108](https://github.com/polyai/adk/pull/108),
  [`3f1b1b3`](https://github.com/polyai/adk/commit/3f1b1b35a8f97154487f88e408d37ad1c5315eb5))

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

### Features

- Safety Filter support ([#79](https://github.com/polyai/adk/pull/79),
  [`ed8ed04`](https://github.com/polyai/adk/commit/ed8ed045d22456dc79302a31e51d0ed2523dc27e))

## Summary

This PR implements safety filter support for ADK, across three areas (General, Voice, Chat). In
  Agent Studio, Content Safety Filters can be applied separately to * General Configuration * Voice
  Channel Settings * Chat Channel Settings

This resource is implemented with a single shared base class `_BaseSafetyFilters` (itself extending
  YamlResource) that holds all the shared logic and three concrete subclasses:

- GeneralSafetyFilters - ChannelSafetyFilters - class to handle filters derived from specific
  channels. - VoiceSafetyFilters and ChatSafetyFilters - inherits from ChannelSafetyFilters,
  specifying their own channel-specific directories and projection paths.

Category data is handled by the _SafetyFilterCategory dataclass (with to_dict, from_dict, to_proto)
  and module-level helpers that translate between the three vocabularies: internal
  (enabled/precision), YAML/UI (enabled/level), and Azure projection (isActive/precision in
  camelCase keys).

ADK format uses `.yaml` to represent as thus: ``` enabled: true

categories: violence: enabled: true level: strict hate: enabled: true level: lenient sexual:
  enabled: true level: medium self_harm: enabled: false level: medium ``` NB: Channel settings have
  a global 'enabled' flag, while General settings do not.

## Motivation

Motivation is to improve parity with Agent Studio via UI.

## Changes * Safety Filters Resource implemented including method to update protos. * Sync client
  updated to read safety filters from projection data (General, Voice, Chat). * Tests written to
  handle YAML round trip and other edge cases.

## Test strategy

Added unit tests, and conducted extensive testing with an AS project.

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

QA - Validation test cases

incorrect category name: <img width="1232" height="40" alt="Screenshot 2026-04-27 at 13 16 35"
  src="https://github.com/user-attachments/assets/17fa46ff-6986-431f-a183-23788f0f004f" /> wrong
  values: <img width="1103" height="35" alt="Screenshot 2026-04-27 at 13 14 07"
  src="https://github.com/user-attachments/assets/f8f55bad-1b2b-4f71-abf8-3d482bcad898" /> missing
  field: <img width="943" height="38" alt="Screenshot 2026-04-27 at 13 15 14"
  src="https://github.com/user-attachments/assets/3709f1f1-216b-4b93-8b8c-c9e58835fc4e" /> not
  boolean for enabled: <img width="1033" height="37" alt="Screenshot 2026-04-27 at 13 15 50"
  src="https://github.com/user-attachments/assets/7c38c0f1-5d1a-483f-bb34-f6c3932abd83" /> missing
  top level enabled: <img width="649" height="37" alt="Screenshot 2026-04-27 at 13 17 10"
  src="https://github.com/user-attachments/assets/bcc4fa62-78dc-424d-81e3-ff6b19144297" />


## v0.14.0 (2026-04-24)

### Features

- Store project name on init and clean up on API errors
  ([#66](https://github.com/polyai/adk/pull/66),
  [`5d5ee5f`](https://github.com/polyai/adk/commit/5d5ee5fe0ba4fc1790f9e91ac37e9a1dd7471658))

## Summary

- Stores the human-readable project name in `project.yaml` on init, - Cleans up partially created
  directories when the API returns an error (e.g. 403 Forbidden, 404 not found).

## Motivation - Project name was discarded during init — now persisted for downstream use. - When
  initialising with an invalid or inaccessible project/account ID, empty directories were left
  behind.

## Changes

- Added `project_name` field to `AgentStudioProject` dataclass, persisted in `project.yaml` and
  status file - On interactive init, the selected project name is captured; on non-interactive init
  (`--project_id`), the name is resolved via `get_projects()` reverse lookup - Wrapped
  `init_project` call in error handling that cleans up `account_id/project_id` directories on
  `HTTPError` or `SourcererAPIError` - Friendly error messages for `FORBIDDEN` and
  `DEPLOYMENT_NOT_FOUND` error codes

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

```yaml project_id: test-bot

account_id: oliver-eisenberg-ws

region: us-1

project_name: New Project ```

```bash ❯ poly init --account_id oliver-eisenberg-ws --project_id non_existant --region us-1 --json
  { "success": false, "error": "Project 'non_existant' not found in account 'oliver-eisenberg-ws'."
  } ❯ ls oliver-eisenberg-ws las-dev-usp ```

```bash ❯ poly init --account_id fake-ws --project_id non_existant --region us-1 Initialising
  project... Initializing project fake-ws/non_existant... Error: Forbidden: you do not have
  permission to access project 'non_existant' in account 'fake-ws'. ```

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.13.1 (2026-04-24)

### Bug Fixes

- Normalise local content on pull ([#102](https://github.com/polyai/adk/pull/102),
  [`43dcd5d`](https://github.com/polyai/adk/commit/43dcd5d5839803e0be10e2d7619a5e7b21d95407))

## Summary

Fixes issue where YAML formatting could cause irrelevant merge conflicts

## Motivation

When pulling, local YAML files could trigger conflicts purely due to formatting discrepancies

## Changes

- **`project.py`** — normalise the local resource through `read_local_resource` + `to_pretty` before
  feeding it into the three-way merge, so local and incoming content use the same canonical
  serialisation; falls back to raw file content if the resource can't be parsed - **`flows.py`** —
  strip whitespace from the parsed `prompt` field. As this is stripped on the platform.

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

- Only end call on explicit end events or in interactive mode
  ([#105](https://github.com/polyai/adk/pull/105),
  [`332d404`](https://github.com/polyai/adk/commit/332d404093573fffbe8f977b79f6086d9b093d89))

## Summary

Fixes `end_chat` being called after every turn in `--json` mode, which was terminating the
  conversation and breaking `--conv-id` resumption.

## Motivation

`poly chat --json --conv-id <id> -m "..."` is the pattern for programmatic turn-by-turn
  conversations. The previous condition (`if not conversation_ended`) fired even in JSON mode when
  input was exhausted, killing the session after each turn.

Closes #<!-- issue number -->

## Changes

- Added `end_call` flag, set only on `/exit` or `/restart` - `finally` now uses `if end_call or (not
  conversation_ended and not output_json)` — `end_chat` skipped in JSON mode unless explicitly
  triggered

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.13.0 (2026-04-24)

### Features

- Clean KB topic names ([#94](https://github.com/polyai/adk/pull/94),
  [`19c3650`](https://github.com/polyai/adk/commit/19c36506fce6219f63728ccd5e5259bdd592251b))

## Summary Topic filenames now use `clean_name()` (e.g. `topics/topic_1.yaml`) with the real name
  stored inside the YAML, matching the flow step pattern. This prevents topics with `/` in their
  name from being created as nested directories. Existing projects are auto-migrated on load.

## Motivation

Topic names containing `/` (e.g. `"Billing/Refunds"`) were being used directly as filenames, causing
  `os.path.join("topics", "Billing/Refunds.yaml")` to create nested folder structures instead of a
  single file.

## Changes

- **`topic.py`**: `file_path` uses `clean_name()`, `to_yaml_dict()` includes `name` field, new
  `read_local_resource()` override reads name from YAML and validates it matches the filename (with
  legacy fallback for old-format files) - **`project.py`**: Added `Topic` to the
  `find_new_kept_deleted` block that reads resource names from YAML content for newly discovered
  files; added `_migration_flags` field to track applied migrations, persisted via
  `to_dict`/`from_dict`/`from_status_dict`; fresh pulls start with all flags set (no migration
  needed) - **`migration_utils.py`** (new): Migration framework with `MigrationFlag` enum,
  `run_migrations()` dispatcher, and `migrate_legacy_topic_files()` — renames old `Topic Name.yaml`
  files to `topic_name.yaml` and injects the `name` key into the YAML content -
  **`migration_test.py`** (new): Tests for the legacy topic file migration — rename, skip
  already-migrated, in-place update for clean names, mixed files - **Test fixtures**: Renamed topic
  fixtures to clean names, added `name` field, updated all path assertions

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Copilot Autofix powered by AI <175728472+Copilot@users.noreply.github.com>


## v0.12.1 (2026-04-24)

### Bug Fixes

- Read disclaimer enabled correctly ([#104](https://github.com/polyai/adk/pull/104),
  [`e141fa8`](https://github.com/polyai/adk/commit/e141fa8165149e4a8ac2399438b9ccbf653065d0))

## Summary

Fixes the voice disclaimer `enabled` field always reading as `False` due to a wrong key name when
  parsing the API projection response.

## Motivation

The Agent Studio API returns voice disclaimer data with camelCase keys (`isEnabled`,
  `languageCode`), but the code was reading `enabled` instead of `isEnabled`. This caused the
  disclaimer to always be treated as disabled regardless of its actual state on the platform.

Closes #<!-- issue number -->

## Changes

- Fix key name mismatch in `_read_agent_settings_from_projection`: read `isEnabled` instead of
  `enabled` for voice disclaimer

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

### Documentation

- Feat: Add branch merge command with interactive conflict resolution
  ([#103](https://github.com/polyai/adk/pull/103),
  [`d1f5ca5`](https://github.com/polyai/adk/commit/d1f5ca558fcd51800a8f4be14fe00f9f3011afa2))

## Summary

This PR relates to https://github.com/polyai/adk/pull/89

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>


## v0.12.0 (2026-04-23)

### Documentation

- Address gaps identified through live AI-agent development session
  ([#92](https://github.com/polyai/adk/pull/92),
  [`921ad8b`](https://github.com/polyai/adk/commit/921ad8b77cdd49a884b1ca960214788bd4573347))

Covers a set of documentation gaps surfaced during a real deployment session using Claude Code with
  the ADK. Changes span existing reference pages, concepts, and a new Examples section.

Existing page edits: - concepts/multi-user-and-guardrails: add disambiguating note distinguishing
  structural guardrails from content-safety features; document push normalization and the re-pull
  requirement; explain synthetic merge-conflict paths; note that branch merges have no CLI command
  and happen in Agent Studio - concepts/anti-patterns: add new entry for prose conditionals on
  variable presence, with before/after example; add to quick-reference table - reference/variables:
  note that variables referenced via {{vrbl:}} in YAML appear as new diff entries on first push
  (expected behavior) - reference/topics: add filename conventions subsection (title case, spaces
  safe, no hard limit) - reference/functions: add conv object reference cross-link to platform docs
  in Related pages - reference/agent_settings: note that adjectives outside the allowed list go in
  custom; clarify that role value:other requires non-empty custom

New pages: - concepts/resource-architecture: decision guide for choosing between topics, rules,
  functions, entities, and flows; decision table and explanation of common mistakes -
  examples/confirm-caller-id-before-sms: stash caller_number, confirm last four digits, send SMS or
  ask for number - examples/venue-specific-goodbye: return utterance+hangup from function to prevent
  LLM filler before disconnect - examples/sms-or-transfer-fallback: offer SMS link or transfer, with
  per-environment sender number pattern

nav: add Resource architecture to Core concepts; add Examples section

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

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Address QA audit from new tutorials — poly chat, variables, validate etc
  ([#95](https://github.com/polyai/adk/pull/95),
  [`d5ea6e2`](https://github.com/polyai/adk/commit/d5ea6e2e8626ddb86a54ac63eea8bf2a2356db1f))

## Summary

- Fix poly chat tutorial contradiction: restaurant-booking-agent.md now correctly shows poly chat
  --environment sandbox after merging, matching build-an-agent.md - Add variables/ to project
  structure diagrams in both tutorials - Document variables/ in poly status as virtual (no files on
  disk) with info callout - Add troubleshooting section to first-commands.md: phantom variables/
  entries and poly branch switch --force workaround - Add poly validate warning in build-an-agent.md
  for platform-generated functions that fail local signature checking, with --skip-validation escape
  hatch - Document relative_date round-trip behavior in restaurant tutorial entities section - Fix
  poly init --help region example: eu-west-1 (invalid) -> us-1 (valid)

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

- Document VS Code/Cursor ADK extension as a first-class IDE route
  ([#99](https://github.com/polyai/adk/pull/99),
  [`889446b`](https://github.com/polyai/adk/commit/889446b706106d78717606d283839b9ed05e7779))

Adds the PolyAI ADK extension for VS Code and Cursor (published on Open VSX) as a first-class
  tooling option, alongside Claude Code as an alternative coding-agent path. Reworks the reference
  tooling page with install instructions from https://open-vsx.org/extension/PolyAI/adk-extension,
  and updates prose in the walkthrough video, what-is-the-adk, working-locally, and build-an-agent
  pages so the IDE route is sustainable without requiring an AI coding agent.

- Feat: Add 'studio' region and filter region selection based on permissions
  ([#93](https://github.com/polyai/adk/pull/93),
  [`6235fa1`](https://github.com/polyai/adk/commit/6235fa1388e77b8db2c4899fc50b85e636cb87b6))

## Summary

This PR contains the work from https://github.com/polyai/adk/pull/82

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Fix command regressions from #95 — diff --files, revert, review…
  ([#96](https://github.com/polyai/adk/pull/96),
  [`73bc904`](https://github.com/polyai/adk/commit/73bc90477d9cd865e4cd7fe498b9e46f0b82209e))

## Summary Three command forms in `build-an-agent.md` were broken by #95, plus two smaller fixes
  carried forward:

- `poly diff <file>` → `poly diff --files <file>` (positional arg is a version hash, not a path) -
  `poly revert --all` → `poly revert` (no `--all` flag) - `poly review` / `poly review --before` →
  `poly review create` / `poly review create --before` (requires subcommand) - Correct `poly push`
  "No changes" admonition in `cli.md`: exit code is 0, not non-zero - Add "poly status shows
  platform-generated functions as modified" section to `first-commands.md`

## Files changed - `docs/docs/tutorials/build-an-agent.md` - `docs/docs/reference/cli.md` -
  `docs/docs/get-started/first-commands.md` ## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Fix install blocker and correct two testing notes ([#97](https://github.com/polyai/adk/pull/97),
  [`05a7980`](https://github.com/polyai/adk/commit/05a7980f96f8c6cab582ee754bfb888f2c5b56e7))

- installation.md: revert to Python 3.14 (polyai-adk requires >=3.14; 3.13 broke installation); keep
  PYTHONWARNINGS=ignore escape hatch for SyntaxWarning noise - sms-or-transfer-fallback.md: remove
  incorrect --channel voice suggestion; caller_number is empty regardless of channel in poly chat;
  show mock-via-start_function pattern instead - venue-specific-goodbye.md: add callout that
  --variant resolves against the deployed environment; branch must be merged before variant names
  exist in sandbox

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

- Make tutorial appropriate for AS Lite ([#101](https://github.com/polyai/adk/pull/101),
  [`353dfef`](https://github.com/polyai/adk/commit/353dfeff31c7cd7c568f04e2432e5b2d2e5efa94))

## Summary

Tutorial was not working because of UI-based limitations around SMS and handoff. I've added response
  control and pronunciation rules (and tested them) in AS Lite

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

- Promote poly init, clarify ingress modes, and document personality Other correctly
  ([#100](https://github.com/polyai/adk/pull/100),
  [`7c2f98b`](https://github.com/polyai/adk/commit/7c2f98b58b4d6bcfe292535588a5ff4fc3b41350))

Three related docs fixes. (1) Gives poly init a front-page moment: adds a three-command quickstart
  block under the front-page hero, makes poly init the lead section of First commands, and updates
  the Recommended path and Installation next-step so install → init → explore reads as one flow. (2)
  Sweeps the didactic flow for the three ingress modes (IDE, Claude Code, full terminal): the
  Installation page now points at the VS Code/Cursor extension at install time, and the
  build-an-agent tutorial clarifies that running the CLI workflow inside an IDE is still the CLI
  workflow. (3) Rewrites the personality section of the restaurant-booking tutorial so the Other
  adjective and the custom field are explained accurately — Other is a mutex switch over the six
  preset adjectives, and custom works independently of it (unlike Role, where custom is gated on
  value: other).

- Swap walkthrough video, tighten wording ([#98](https://github.com/polyai/adk/pull/98),
  [`73f5bbc`](https://github.com/polyai/adk/commit/73f5bbcc2baf1ace201d83b1173bcfee0b2549b6))

Removes phrasing that implied the Agent Studio UI is never needed (merging, deploying, and
  monitoring still happen there), swaps the walkthrough video for https://vimeo.com/1185280299, and
  tightens a few confusing wordings across the get-started and tutorial pages.

### Features

- Add branch merge command with interactive conflict resolution
  ([#89](https://github.com/polyai/adk/pull/89),
  [`3da279b`](https://github.com/polyai/adk/commit/3da279beddf0cf42a5c4d4d996deb76fe05029a8))

## Summary

Add `poly branch merge` command that merges a branch into main via the CLI, with support for
  interactive conflict resolution using a three-way merge workflow.

## Motivation

Branch merging previously required navigating to the Agent Studio web UI. This brings the full merge
  workflow into the CLI, including viewing conflicts, auto-merging clean changes, and resolving
  conflicts interactively (pick a side, edit in editor).

## Changes

- New `poly branch merge <message>` subcommand with `--interactive`/`-i` flag for conflict
  resolution - Interactive mode: Rich-formatted conflict table showing auto-mergeability status,
  questionary-driven resolution (auto-merge, pick main/branch/base, edit in editor) - Refactored
  `--debug` flag into a shared argparse parent across all subcommands - `project.merge_branch()` now
  returns raw conflict/error dicts instead of pre-formatted strings - `sdk.merge_branch()` computes
  `expectedBranchLastKnownSequence` internally - Fixed `merge_strings` to ensure newlines before
  conflict markers - Force-pull after branch switch to ensure local state is up to date

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots: <img width="1662" height="1078" alt="0e2e870c8cfd4468b3a3acdfecdeffbb"
  src="https://github.com/user-attachments/assets/4a1f5676-50e1-4dfe-8040-9678322f0574" /> <img
  width="1662" height="1078" alt="02b3ca30285d433ab92c0142cc920fa8"
  src="https://github.com/user-attachments/assets/aade926a-38c3-44de-b04b-de2ee8d07443" />


## v0.11.0 (2026-04-21)

### Documentation

- Feat(cli): deployment history and version-scoped diff/review
  ([#90](https://github.com/polyai/adk/pull/90),
  [`bf0939d`](https://github.com/polyai/adk/commit/bf0939dbe776fc1055ba4b494ebba305b7e54fa9))

## Summary

This covers the work from https://github.com/polyai/adk/pull/39

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

### Features

- Add 'studio' region and filter region selection based on permissions
  ([#82](https://github.com/polyai/adk/pull/82),
  [`d4af195`](https://github.com/polyai/adk/commit/d4af1955780253994c99a2a09f85dd093d0fd295))

## Summary

Updates `poly init` to only display regions the user's API key has access to, and adds the `studio`
  region.

## Motivation

Previously, `poly init` showed all hardcoded regions regardless of whether the user had access. This
  change probes regions concurrently and filters the list. Additionally, `studio` was not available
  as a region.

## Changes

- Added `get_accessible_regions()` to `PlatformAPIHandler` that concurrently probes regions via
  `get_accounts()` and returns only accessible ones - Added `get_accessible_regions()` to
  `AgentStudioInterface` as the public interface - Updated `init_project()` in `cli.py` to fetch and
  display only accessible regions (with a loading spinner), with an error message if none are found
  - Added `"studio"` region pointing to `https://api.studio.poly.ai/adk/v1`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="385" height="85" alt="Screenshot 2026-04-21 at 11 20 47"
  src="https://github.com/user-attachments/assets/77e51284-951c-43be-aad6-a7da0439fb2f" />


## v0.10.0 (2026-04-17)

### Features

- **cli**: Deployment history and version-scoped diff/review
  ([#39](https://github.com/polyai/adk/pull/39),
  [`0730d06`](https://github.com/polyai/adk/commit/0730d06fb80206af8a14c67fbea59036e250cd38))

## Summary Adds **`poly deployments`**, extends **`diff`** / **`review`** with hash and **`--before`
  / `--after` / `--files`**, updates. Updates **`review`** to be **`review create`** to be similar
  with **`branch`** commands

## Motivation Improves visibility into deployed versions and makes comparing local vs remote or
  named versions consistent in the CLI.

## Changes - **`poly deployments`** with `--env`, pagination, `--hash`, `--oneline`, `--json`; Rich
  output with sandbox / pre-release / live badges. - **`get_deployments`** (API + project):
  `client_env`, list return shape, tuple with active hashes on **`AgentStudioProject`**. - **`poly
  diff` / `poly review`**: optional hash, `--files`, `--before` / `--after`; **`--delete`** on
  review; shared diff computation. - **`poly review`** logic moved to `poly review create` - **`poly
  revert`** / **`poly format`**: CLI shape updates to be consistent (`--all` removed; format uses
  **`--files`**).

## Test strategy - [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x]
  Tested against a live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist - [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="671" height="79" alt="Screenshot 2026-03-27 at 14 23 31"
  src="https://github.com/user-attachments/assets/fd6f9b1b-de45-4f5c-82b1-cd2394e473ba" />

`--details` <img width="547" height="511" alt="Screenshot 2026-03-27 at 15 35 14"
  src="https://github.com/user-attachments/assets/d3983a66-df51-4c43-a142-bd28f42fa2a2" />

`--env` <img width="624" height="32" alt="Screenshot 2026-03-27 at 15 35 27"
  src="https://github.com/user-attachments/assets/dfc2aab6-0206-45f8-a3ae-6387f09f196c" />


## v0.9.1 (2026-04-17)

### Bug Fixes

- Don't show diff for reordered entities ([#87](https://github.com/polyai/adk/pull/87),
  [`2a0ff85`](https://github.com/polyai/adk/commit/2a0ff85a4c5bbbc6bd408a76a10c1458467a0dbe))

## Summary

Fix spurious diffs after push caused by `extracted_entities` list ordering differences between local
  YAML and the platform.

## Motivation

After pushing, `poly diff` shows reordering-only changes to `extracted_entities` in flow steps. The
  platform returns entity IDs in a different order than local YAML, producing false diffs with no
  meaningful content change.

## Changes

- Sort `extracted_entities` in `FlowStep.to_yaml_dict()` so both local and remote representations
  use a consistent alphabetical order

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Documentation

- Add missing warnings for key ADK footguns and workflow gaps
  ([#86](https://github.com/polyai/adk/pull/86),
  [`4391333`](https://github.com/polyai/adk/commit/4391333b2e37e45daf5b639b2124ba9942cc5b78))

## Summary

Addresses the documentation gaps identified from a real end-to-end AI-agent workflow build (Bella
  Vista reservation assistant) that caused significant lost time. Each change adds a targeted note
  or warning where the docs were silent on a real failure mode.

## Motivation

A systematic audit against a live implementation identified six gaps where the docs' silence or
  vagueness caused actual blockers — not theoretical ones. Several required digging through source
  code to resolve.

## Changes

**Gap 1 — No local runtime** - `testing.md`: prominent warning that there is no `poly serve` or
  local simulator; all execution is in Agent Studio Sandbox - `what-is-the-adk.md`: clarify the ADK
  manages config files and does not execute agents

**Gap 2 — API keys are workspace-scoped** - `prerequisites.md`: warning that `poly init` lists all
  projects visible to the key; seeing unexpected projects means the wrong key is in use; also
  removes a garbled duplicate section from a previous edit

**Gap 3 — Platform-provisioned resources cannot be created via ADK** - `voice_settings.md`,
  `chat_settings.md`, `agent_settings.md`, `speech_recognition.md`: note on each page that
  greeting/style prompt/disclaimer/personality/role/ASR settings are provisioned by Agent Studio on
  project init and can only be _updated_, not created; pushing them into a project without a
  matching `.agent_studio_config` entry fails with `NotImplementedError: Create operation not
  supported`

**Gap 4 — Don't copy project directories** - `anti-patterns.md`: new section explaining why copying
  a project directory to a different project causes push failures (`.agent_studio_config` IDs,
  platform-provisioned resources); correct approach is `poly init` + `poly pull`

**Gap 6 — No `poly merge` command** - `tutorials/build-an-agent.md`: note at Workflow 1 Step 10 and
  Workflow 2 Step 7 that merging requires the Agent Studio web UI; there is no CLI command

**Minor gaps** - `tutorials/build-an-agent.md`: mark `chat/` as optional in the project structure
  diagram - `tutorials/build-an-agent.md`: add tip in AI-agent Workflow 2 Step 3 to run `poly docs
  --all` immediately after `poly pull`, before generating any files — without it, a coding agent has
  no schema context and will hallucinate resource structure

## What was not addressed

- `poly merge` CLI command — this is a code change, not a doc change; documented as a known gap -
  Gap 5 (branch `--environment` 404) — `cli.md` already partially covers branch environment
  behavior; the failure mode may be platform-specific and is not clearly reproducible

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

> **Note:** `prerequisites.md` is also touched by #85 (tab rename). Whichever merges second will
  need a quick rebase.

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Add onboarding page and wire into get-started nav ([#78](https://github.com/polyai/adk/pull/78),
  [`b0654b5`](https://github.com/polyai/adk/commit/b0654b5aba2e3bcf61719d8ebb940b425fe83243))

## Summary

Adds a new `get-started/agent-wizard.md` page at the top of the Get Started section, before any ADK
  content. Covers two user paths: new users building their first agent via Agent Wizard, and
  existing Agent Studio users pulling down an existing project.

## Motivation

Users arriving at the ADK docs without an existing agent had no clear entry point. Agent Wizard is
  the fastest way to create one, but there was no documentation connecting the two products.

Closes #

## Changes

- New page `docs/docs/get-started/agent-wizard.md` — new user onboarding via Agent Wizard, including
  the concrete `poly init --account_id ... --project_id ...` + `poly pull` handoff to local
  development - `mkdocs.yml` — new page added as first item in Get Started nav - `index.md` — hero
  card updated to surface Agent Wizard as the entry point for users without an agent -
  `what-is-the-adk.md` — next steps now includes a card pointing to the Agent Wizard page

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Add agent-wizard-build.png to docs/docs/assets/ before merging -->

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Feat: non-interactive scripted input, conversation resume, pre-chat push, and JSON output for poly
  chat ([#83](https://github.com/polyai/adk/pull/83),
  [`1209129`](https://github.com/polyai/adk/commit/12091292dcd9576fae56d2d89969537fff322e50))

## Summary

This is the work from https://github.com/polyai/adk/pull/69

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Fix API key provisioning — self-generated, not provided by contact
  ([#84](https://github.com/polyai/adk/pull/84),
  [`a1c9250`](https://github.com/polyai/adk/commit/a1c92509825bc60c649cfb3b6c18516d11cf017e))

## Summary

Corrects the inaccurate claim that both workspace access and the API key are provided by a PolyAI
  contact. The API key is self-generated by the user inside Agent Studio.

## Motivation

The docs stated "Both are provided by your PolyAI contact" — this is wrong for the API key. It also
  meant the Getting Started flow sent users to Prerequisites for an API key *after* they'd already
  been told to run `poly pull`, which requires the key.

## Changes

- `access-and-waitlist.md`: distinguish workspace access (from contact) vs API key (self-generated
  in Agent Studio) - `prerequisites.md`: update checklist item from "obtained from your PolyAI
  contact" to "generated in Agent Studio" - `get-started.md`: add **Step 5 — Generate an API key**
  (with `POLY_ADK_KEY` env var export) between finding account/project IDs and pulling; renumber
  Steps 5–6 → 6–7; replace the misplaced "Next step → Prerequisites" CTA with "Next step →
  Installation"

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Improve first-steps get-started page ([#88](https://github.com/polyai/adk/pull/88),
  [`cb99c5b`](https://github.com/polyai/adk/commit/cb99c5b4cfb5f30a6d516832b1e75d111238e141))

## Summary - Adds missing screenshots (`agent-studio-login.png`, `go-back-to-key.png`) for the
  get-started flow - Moves sign-up instructional text above the screenshot for better reading order

## Test plan - [x] Verify images render correctly in the docs site - [x] Check that the get-started
  page reads logically top to bottom

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Rename API Keys tab, add key-gen image to get-started, remove orphaned docs workflow page
  ([#85](https://github.com/polyai/adk/pull/85),
  [`22d50b4`](https://github.com/polyai/adk/commit/22d50b4515adad1c90f659dd8bab0298a94f98f1))

## Summary

Three clean-up fixes to the get-started docs: correct a stale UI label, fill a missing screenshot in
  the new-user flow, and remove a stranded duplicate page.

## Motivation

- The "Data Access" tab was renamed to "API Keys" in Agent Studio — the docs still used the old
  name. - The get-started new-user flow jumped from "find your IDs" to "poly pull" without showing
  how to generate an API key, which is required for `poly pull` to work. - `development/docs.md`
  (nav label: "Docs workflow") was an older, partial version of the AI-agent workflow that
  `tutorials/build-an-agent.md` covers fully. Keeping it as a lone page under a "Development"
  section with a mismatched title caused confusion.

## Changes

- `prerequisites.md`: "Data Access" tab → "API Keys", button label → "+ API key", image alt text
  updated - `installation.md`: image alt text updated to match - `get-started.md`: add Step 5 —
  Generate an API key (with screenshot and `POLY_ADK_KEY` export), renumber old Steps 5–6 to 6–7,
  fix the bottom "Next step" card to point forward to Installation rather than back to Prerequisites
  - `development/docs.md`: deleted — content fully covered by Workflow 2 in
  `tutorials/build-an-agent.md` - `mkdocs.yml`: remove the now-empty Development nav section

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

> **Note:** This PR overlaps with #84 on `prerequisites.md` and `get-started.md`. One will need a
  rebase after the other merges.

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>


## v0.9.0 (2026-04-16)

### Documentation

- Allow specifying lang code in chat requests ([#81](https://github.com/polyai/adk/pull/81),
  [`e6d8f3f`](https://github.com/polyai/adk/commit/e6d8f3f3ae460fd6cdd04113a5ae897d6d2b4ec8))

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
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

### Features

- Non-interactive scripted input, conversation resume, pre-chat push, and JSON output for `poly
  chat` ([#69](https://github.com/polyai/adk/pull/69),
  [`7a1ae59`](https://github.com/polyai/adk/commit/7a1ae5961f629cd2b0d8fa02991ef306a12392e9))

## Summary

Extends `poly chat` with four new capabilities: push before chatting (`--push`), scripted/file-based
  message input (`-m`/`--input-file`), resuming an existing conversation (`--conv-id`), and
  structured JSON output (`--json`). Interactive mode is fully unchanged.

## Motivation

Makes `poly chat` usable in automated testing pipelines and CI scripts without a human at the
  terminal. `--push` removes the manual push step before testing a branch.

## Changes

- `--push`: pushes the project before creating the chat session so local changes are live before
  testing - `--message`/`-m` (repeatable): supply utterances non-interactively, e.g. `-m "Hello" -m
  "Goodbye"` - `--input-file FILE`: reads messages line-by-line from a file; use `-` for stdin -
  `--conv-id`: resumes an existing conversation by ID, skipping session creation entirely -
  `--json`: emits a single JSON object `{"conversations": [...]}` when the session ends; each
  conversation contains `conversation_id`, `url`, and `turns` (greeting is `turns[0]` with `"input":
  null`); restarts produce multiple entries in the array - `_run_chat_loop` now returns `(restart,
  conversation_dict)` so the caller accumulates conversations across restarts before printing -
  Clean error message when `--input-file` path does not exist - Updated `chat_parser` help text with
  examples for all new flags

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

Co-authored-by: Copilot <175728472+Copilot@users.noreply.github.com>


## v0.8.5 (2026-04-15)

### Bug Fixes

- Allow specifying lang code in chat requests ([#80](https://github.com/polyai/adk/pull/80),
  [`b9070b9`](https://github.com/polyai/adk/commit/b9070b900ac43cbc471617aca29467852ad0cd18))

## Summary

Adds `--lang`, `--input-lang`, and `--output-lang` flags to `poly chat`, allowing users to specify
  language codes for ASR (input) and TTS (output) when starting or continuing a chat session.

## Motivation

Users chatting against multilingual agents need a way to specify the expected input/output language
  without relying on the project default. This exposes the existing `asr_lang_code` /
  `tts_lang_code` API fields via the CLI.

## Changes

- Added `--lang`, `--input-lang`, `--output-lang` arguments to the `chat` subcommand in `cli.py` -
  `--lang` sets both input and output lang; `--input-lang`/`--output-lang` override individually -
  Threaded `input_lang` / `output_lang` through `AgentStudioProject.create_chat_session`,
  `send_message`, `AgentStudioInterface`, and `PlatformAPIHandler` for both standard and
  draft/branch chat flows - Maps `input_lang` → `asr_lang_code` and `output_lang` → `tts_lang_code`
  in API request payloads

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="1596" height="214" alt="Screenshot 2026-04-15 at 12 05 11"
  src="https://github.com/user-attachments/assets/721b5ee0-5cec-4b4e-b5ca-194df29a732a" />

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Chores

- Add docs team to CODEOWNERS ([#77](https://github.com/polyai/adk/pull/77),
  [`7c01266`](https://github.com/polyai/adk/commit/7c012668aabb544c8e8a4b508918551ee003713e))

## Summary Create docs team as a code owner so we can loosen PR approval policies when only
  targeting documentation.

## Motivation Our docs team is getting slowed down needing engineering approval for minor doc
  changes.

### Documentation

- Adk branch create --env flag to specify source env for new branch
  ([#57](https://github.com/polyai/adk/pull/57),
  [`2de96af`](https://github.com/polyai/adk/commit/2de96af5affd2ca2ac4f6095436289c81067be22))

## Summary

This PR is related to https://github.com/polyai/adk/pull/56

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

Co-authored-by: Ruari Phipps <ruari@poly-ai.com>

- Chore: Update experimental config ([#74](https://github.com/polyai/adk/pull/74),
  [`838f437`](https://github.com/polyai/adk/commit/838f437746fb3ff38da2c4783effcd6bd4892b9f))

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
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Fix: `--debug` flag to `poly review` command that enables DEBUG-level
  ([#76](https://github.com/polyai/adk/pull/76),
  [`165f81c`](https://github.com/polyai/adk/commit/165f81cb4e550d62c7657acd7599e4874ba4dba6))

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Fix: Raise proper error message for invalid format functions
  ([#72](https://github.com/polyai/adk/pull/72),
  [`15830a2`](https://github.com/polyai/adk/commit/15830a2e02e9366f1fd8918cd607ddb873a19b6f))

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
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>


## v0.8.4 (2026-04-14)

### Bug Fixes

- Don't delete or fail to update conditions when their parent step…
  ([#71](https://github.com/polyai/adk/pull/71),
  [`85c6aea`](https://github.com/polyai/adk/commit/85c6aea87f2af72a877159aad6a63cb4df894dab))

## Summary

Fixes two bugs in `_clean_resources_before_push` that caused push failures when a flow step with
  conditions was deleted.

## Motivation

When a FlowStep is deleted, Agent Studio automatically deletes its child Conditions server-side.
  This caused two issues: 1. Explicitly including the condition in `deleted_resources` would result
  in a double-delete error. 2. If a condition was also being *updated* (e.g. re-pointed to a new
  step), the update request would fail because the platform had already deleted the condition when
  the step was removed.

## Changes

- Strip conditions from `deleted_resources` when their parent `FlowStep` is being deleted (platform
  handles the cascade) - Promote affected conditions from `updated_resources` to `new_resources`
  when their original `child_step` is being deleted in the same push

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Copilot Autofix powered by AI <175728472+Copilot@users.noreply.github.com>


## v0.8.3 (2026-04-14)

### Bug Fixes

- Empty diff entries caused a 422 error from the GitHub Gists API
  ([#75](https://github.com/polyai/adk/pull/75),
  [`6ffa08f`](https://github.com/polyai/adk/commit/6ffa08f49c419edc7db1240642e117600d4c3c0c))

## Summary - Add `--debug` flag to `poly review` command that enables DEBUG-level logging for easier
  troubleshooting - Fix bug where empty diff entries caused a 422 error from the GitHub Gists API
  (`missing_field: files`)

## Test plan - [x] Run `poly review --debug` and verify debug logs appear - [x] Run `poly review`
  without `--debug` and verify only warnings are shown - [x] Verify that projects with empty diffs
  no longer trigger a 422 gist creation error

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Update experimental config ([#73](https://github.com/polyai/adk/pull/73),
  [`10840e5`](https://github.com/polyai/adk/commit/10840e5e4f46891f33955eef71832142801d715a))

## Summary Update experimental config

## Motivation Get new features

## Changes Update to latest

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


## v0.8.2 (2026-04-10)

### Bug Fixes

- Allow ?query ending for API operations ([#70](https://github.com/polyai/adk/pull/70),
  [`4199800`](https://github.com/polyai/adk/commit/419980010c63e3e4b6b1a780ff26d4f80e552cbd))

## Summary Update validation regex to allow API operation with ?query ending <!-- What does this PR
  do? Keep it to 1-3 sentences. -->

## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.8.1 (2026-04-10)

### Bug Fixes

- Raise proper error message for invalid format functions
  ([#68](https://github.com/polyai/adk/pull/68),
  [`5222f3e`](https://github.com/polyai/adk/commit/5222f3ec56da9821c0de54b648f9561e442b7d4f))

## Summary

Fixes two related issues: untyped or unsupported function parameters now raise a clear `ValueError`
  instead of crashing with `AttributeError`, and merge-conflicted files are correctly excluded from
  `modified_files` in `project_status` and handled without crashing in `get_diffs`. Also surfaces
  all CLI errors as structured JSON when `--json` is set.

## Motivation

In v0.6.x, functions with untyped parameters (e.g. `def f(conv, booking_ref)`) caused
  `_extract_decorators` to crash with `AttributeError: 'NoneType' has no attribute 'id'`.
  Separately, files with merge conflicts were being passed to `read_local_resource`, which would now
  raise rather than silently fail. Both issues needed to be fixed together for `poly status` and
  `poly diff` to be reliable after a branch pull with conflicts.

Closes #<!-- issue number -->

## Changes

- `_extract_decorators`: guard `arg.annotation` access before reading `.id`; raise `ValueError` with
  a distinct message for missing vs unsupported type annotations; remove the `try/except
  SyntaxError` wrapper so errors propagate to the user - `resource.py`: rename `get_status` →
  `is_modified`, removing merge conflict detection from the resource itself - `project_status`:
  check for merge conflicts on raw file content before calling `read_local_resource`; conflicted
  files now appear only in `files_with_conflicts`, not also in `modified_files` - `get_diffs`: same
  conflict-before-parse pattern; shows diff of conflict markers vs original; fix
  `type(resource_type)` key bug and missing second arg to `get_diff` - `cli.py`: wrap the command
  dispatch in `try/except`; when `--json` is set, errors are returned as `{"success": false,
  "error": "...", "traceback": "..."}` instead of raising - `src/poly/docs/functions.md`: note that
  all parameters must have a supported type annotation

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

### Documentation

- Feat: add poly branch delete command ([#67](https://github.com/polyai/adk/pull/67),
  [`285327b`](https://github.com/polyai/adk/commit/285327bdad9869eaed8fae4f43472226e465adfe))

## Summary

This PR is related to https://github.com/polyai/adk/pull/63

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Fix prerequisites around API key generation ([#59](https://github.com/polyai/adk/pull/59),
  [`4fea771`](https://github.com/polyai/adk/commit/4fea771354c28164884d4fbfd2df4c15e50c3e37))

## Summary

This PR relates to https://github.com/polyai/adk/pull/45 and updates API key generation info

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


## v0.8.0 (2026-04-08)

### Features

- Add `poly branch delete` command ([#63](https://github.com/polyai/adk/pull/63),
  [`463a663`](https://github.com/polyai/adk/commit/463a66379a4c8506102f75193461320e07b2ae2a))

## Summary

Adds `poly branch delete` — an interactive command for deleting branches, following the same UX
  pattern as `poly review delete`.

## Motivation

Branch deletion was already implemented in the backend (`project.delete_branch()`) but not exposed
  through the CLI.

## Changes

- Added `delete` subcommand to `poly branch` with optional `branch_name` argument - Interactive
  checkbox selection (via questionary) when no branch name is provided - Direct deletion mode when
  branch name is passed as argument - JSON output mode support (`--json`) - Filters out `main`
  branch (cannot be deleted) - 16 new unit tests covering all code paths

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

<img width="1532" height="560" alt="image"
  src="https://github.com/user-attachments/assets/3336c7d5-ac70-4c5c-99e9-ddb27ff147a0" /> <img
  width="1348" height="122" alt="image"
  src="https://github.com/user-attachments/assets/1c7f31fc-4de3-4ec3-bc55-aba98799d870" /> <img
  width="650" height="57" alt="image"
  src="https://github.com/user-attachments/assets/702fbdaf-1b14-49f8-b607-b7404f39e898" />

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (431 tests) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

Co-authored-by: Ruari Phipps <ruari@poly-ai.com>


## v0.7.3 (2026-04-02)

### Bug Fixes

- Suppress verbose error logging and API key leak on HTTP errors
  ([#61](https://github.com/polyai/adk/pull/61),
  [`8e54b2d`](https://github.com/polyai/adk/commit/8e54b2d76590f20f998542ec71ef81a7b71d4e2f))

## Summary - Downgrade `logger.exception` to `logger.debug` in `PlatformAPIHandler.make_request` so
  failed API calls no longer dump full tracebacks to stderr by default - Change `raise e` to bare
  `raise` for cleaner traceback if verbose mode is used

## Context When running `poly review --before x --after y` and getting a 403, users saw the full
  `ERROR:poly.handlers.platform_api:Error in request...` log (including the API key in headers) plus
  the traceback, before the clean error message. Now only the clean `Error: API request failed: 403
  ...` message is shown, since `handle_exception()` in `console.py` already formats `HTTPError`
  nicely.

## Test plan - [x] Run `poly review --before draft --after pre-release` against a project with
  insufficient permissions — verify only the clean error line is shown - [x] Run the same with
  `--verbose` — verify the debug log appears with request details (minus headers) - [x] `uv run
  pytest src/poly/tests/ -v` passes (415 tests)

<img width="1659" height="396" alt="image"
  src="https://github.com/user-attachments/assets/c00ce1ea-6a39-4916-b60b-e2e6580cd76f" />

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.7.2 (2026-04-02)

### Bug Fixes

- Standardise gist naming with Poly ADK prefix ([#62](https://github.com/polyai/adk/pull/62),
  [`01992e4`](https://github.com/polyai/adk/commit/01992e4d22cc1171d13f2a762b987b7a05aa024e))

## Summary - Add "Poly ADK: " prefix to the gist description for local → remote reviews, matching
  the existing format used by `--before`/`--after` reviews

## Context When using `poly review --before x --after y`, the gist description was `"Poly ADK:
  project: x → y"`. But `poly review` (local → remote) produced `"project: local → remote"` without
  the prefix. Now both use the same `"Poly ADK: "` prefix for consistency.

## Test plan - [x] Run `poly review` (local → remote) and verify the gist description starts with
  "Poly ADK: " - [x] Run `poly review --before x --after y` and verify the format is unchanged

<img width="908" height="74" alt="image"
  src="https://github.com/user-attachments/assets/7d97e433-7b39-4308-8e88-0ba756dbe015" />

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.7.1 (2026-04-01)

### Bug Fixes

- Match API integration operations by name when resource_id absent
  ([#60](https://github.com/polyai/adk/pull/60),
  [`a3a56ab`](https://github.com/polyai/adk/commit/a3a56ab240f5d1883d12a4bafcc5f0be52fc9f17))

## Summary

Fix a bug where `poly push` always issued a delete + create for every API integration operation
  instead of computing the true diff.

## Motivation

`ApiIntegrationOperation.to_yaml_dict()` intentionally omits `resource_id`, so operations loaded
  from YAML always have `resource_id = ""`. The previous diff logic in
  `get_new_updated_deleted_subresources` matched operations by `resource_id` only — meaning every
  local op was treated as new (create) and every remote op as deleted, regardless of whether
  anything had actually changed.

A secondary bug meant multiple new operations all keyed on `""` in `new_subresources`, so only the
  last one survived and only 1 of N creates was ever emitted.

## Changes

- Match operations by `resource_id` when present; fall back to **name-based matching** for
  YAML-loaded ops (no ID stored) - Carry the remote `resource_id` forward when matched by name so
  update commands target the correct remote resource - Generate a fresh UUID eagerly for genuinely
  new ops to avoid key collisions in `new_subresources`

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly push --dry-run --debug`) - [x] Tested
  against a live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface - [x] Commit messages follow [conventional
  commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

### Documentation

- Fix: use Python 3.13 in docs CI ([#58](https://github.com/polyai/adk/pull/58),
  [`c4cc68b`](https://github.com/polyai/adk/commit/c4cc68b4aab5a87c779242aed075f767e0b4320e))

docs/pyproject.toml: relax requires-python from >=3.14 to >=3.11 .github/workflows/build-docs.yaml:
  pin to python 3.13 (latest stable)

Python 3.14 is pre-release and not available on GitHub Actions runners, causing setup-python to fall
  back to 3.11 which then fails the >=3.14 constraint. mkdocs has no dependency on 3.14.

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

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

- Improve clarity, active language, and add Google Analytics
  ([#43](https://github.com/polyai/adk/pull/43),
  [`a721bca`](https://github.com/polyai/adk/commit/a721bcab21dd6f11dcecf1b451b571c8a12cbb9a))

## Summary

- **Remove AI-isms**: replaced "trust the model", "the agent does the heavy lifting", "composable",
  and similar LLM-adjacent framing with plain, concrete language - **Active language throughout**:
  rewrote passive constructions and vague headers ("What it enables" → "What you can do with the
  ADK"; "Before you continue" → "Checklist") - **Remove internal history**: deleted the "Local Agent
  Studio" provenance paragraph from `what-is-the-adk.md` — not useful for external developers -
  **Prerequisites improvements**: added Python 3.14+ install guidance (Homebrew, pyenv, python.org),
  the official `uv` install command (`astral.sh`), and a proper checklist - **Installation
  cleanup**: removed the "Running tests" section (it belongs in `testing.md`, not install) -
  **Testing page**: added `uv run pytest` as the canonical invocation - **Build-an-agent tutorial**:
  removed the empty Summary table, clarified AI-agent workflow steps with concrete task headings -
  **Tooling page**: VS Code extension URL is now a proper hyperlink - **Consistency**: fixed
  "Pre-requisites" → "Prerequisites" across index and access pages; import line note in
  `functions.md` now explains the consequence of modifying it

## Test plan

- [x] Review rendered docs for visual regressions - [x] Confirm all internal links still resolve -
  [x] Read through get-started flow end-to-end

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

Co-authored-by: Aaron Forinton <aaron.forinton@googlemail.com>


## v0.7.0 (2026-04-01)

### Chores

- Migrate docs dependencies to pyproject.toml ([#55](https://github.com/polyai/adk/pull/55),
  [`13716d0`](https://github.com/polyai/adk/commit/13716d0005713d20e7a45a0b9306e576fb111671))

- Move documentation dependencies from `requirements.txt` to `pyproject.toml` - Create new
  `docs/pyproject.toml` with mkdocs and related packages - Delete `docs/requirements.txt` - Update
  CI workflows to install dependencies using `pip install .` instead of `pip install -r
  requirements.txt`

This consolidates dependency management and follows modern Python packaging standards.

---------

Co-authored-by: Claude Sonnet 4.6 <noreply@anthropic.com>

### Features

- Adk branch create --env flag to specify source env for new branch
  ([#56](https://github.com/polyai/adk/pull/56),
  [`e9dd3b9`](https://github.com/polyai/adk/commit/e9dd3b93e6246b577a0826dd2e77b73aa1578516))

## Summary

Adds a `--env` flag to `poly branch create` that sources a new branch from a live or pre-release
  deployment snapshot instead of sandbox main.

Additional points: - Specifying `sandbox` as env arg will default to existing behaviour (sandbox
  being the default 'base'). - Branch creation is also followed by push, to leave a 'clean slate'
  for any hotfix changes required. - `--force` flag will force overwrite of any local changes on
  `main` (restrictions still apply for creating new branch from main only).

## Motivation

The motivation is to facilitate hotfixes to main live environment, bypassing any subsequent changes
  in testing environments. This should be used with caution and usual protocol to be followed with
  pushing the change.

## Changes

- project.py: added pull_project_from_env(env, format) method to class AgentStudioProject. - cli.py:
  add `--env/--environment` (choices: sandbox, pre-release, live) and `--force/-f` to `branch
  create` - cli.py: when --env live/pre-release is set, pull from that environment before creating
  the branch and push immediately after

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [ ] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


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
