# CHANGELOG


## v0.44.2 (2026-08-17)

### Bug Fixes

- Open poly studio on the current branch ([#241](https://github.com/polyai/adk/pull/241),
  [`fda047c`](https://github.com/polyai/adk/commit/fda047c8ba25834ffb7d4e2e971fb15bde961e53))

## Summary

`poly studio` now opens the Agent Studio web UI on the branch the local project is checked out to,
  instead of always landing on the default branch.

## Motivation

The command built the Studio URL from `studio_base_url` only
  (`https://{domain}/{account}/{project}`), with no branch context, so the browser always opened the
  default branch view — inconsistent with `poly pull`/`push`/`status`, which operate against the
  current branch.

## Changes

- `StudioCommand.open_agent_studio` now builds
  `f"{project.studio_base_url}/home?branchId={project.branch_id}"`, using the already-loaded
  `branch_id` (a feature branch id, or `main`). - `studio_base_url` is left as the bare base — it is
  also consumed by `get_conversation_url`, so the query param is composed in the command rather than
  the property. - Added `StudioCommandTest` covering feature-branch and default-branch URL
  construction.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before: `https://studio.uk.poly.ai/<account>/<project>`

After: `https://studio.uk.poly.ai/<account>/<project>/home?branchId=BRANCH-XXXXXX`

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.8 (1M context) <noreply@anthropic.com>

### Chores

- **tests**: Make the test_project fixture match a real status file
  ([#271](https://github.com/polyai/adk/pull/271),
  [`3bb26e4`](https://github.com/polyai/adk/commit/3bb26e49e74dc4bd53ac310836b0121cc6818e8e))

## Summary

The `test_project` fixture stored values a real status file cannot contain, which made a no-op
  `sync_ids_with_sandbox` look like 10 changed resources. This regenerates the drifted entries from
  a disk read and adds tests so the fixture cannot drift again.

## Motivation

A real status file is written by `save_config` → `to_dict` from live resources, so every stored
  resource matches what reading that same file off disk produces. The fixture had drifted from that
  in four ways:

| Stored | Should be | Where | |---|---|---| | `asr_biasing: null`, `dtmf_config: null` |
  materialized objects | 4 flow steps | | `child_step: null` | `""` | 3 conditions | |
  `condition_type: step_condition` | `no_code_step_condition` | 1 condition | | `description: null`
  | `""` | 2 functions | | key `attr-<name>` | key `<name>` | 4 variant attributes |

Neither path produces those values. `FlowStep.from_projection`
  ([flows.py:401-428](../blob/main/src/poly/resources/flows.py#L401-L428)) always constructs
  `ASRBiasing` and `DTMFConfig`, and #255 already made `description` default to `""`. The fixture
  simply never caught up.

This matters because `sync_ids_with_sandbox` is the only code path that decides what changed by
  comparing whole `Resource` objects — the point #255 makes. `push_project` and `get_diffs` gate on
  the rendered-file hash instead. So stored values that disagree with disk are invisible everywhere
  except that one path, where they surface as spurious writes:

``` no-op sync, before: 4 VariantAttribute created + 4 deleted, 2 Function + 4 FlowStep + 4
  Condition updated no-op sync, after: nothing staged, no commands sent ```

Agent Studio wraps a command batch in a single transaction, so every pointless command is another
  chance to roll back the id repair that was the point of the sync.

It also meant the sync tests could not assert the thing most worth asserting — that a no-op sync
  sends nothing — because it wasn't true.

## Changes

- Regenerate the 6 drifted resource entries from a disk read, and re-key the 4 variant attributes
  onto their own `resource_id`s. - `TestProjectFixtureIntegrityTest` pins both properties: every
  resource is stored under a key equal to its `resource_id`, and every stored resource equals a disk
  read across compared fields. This is what would have caught the drift. -
  `test_no_op_sync_sends_no_commands` asserts an identical sandbox stages nothing. -
  `test_content_change_is_still_detected` is its counterweight, so the no-op assertion cannot pass
  by making sync blind to real changes.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

1042 passed. The three new guard tests were verified against the pre-fix fixture and all three fail
  on it, reporting 13 drifted values:

``` FAILED SyncIdsWithSandboxTest::test_no_op_sync_sends_no_commands FAILED
  TestProjectFixtureIntegrityTest::test_stored_ids_match_their_resource_ids FAILED
  TestProjectFixtureIntegrityTest::test_stored_resources_match_a_disk_read ```

`test_content_change_is_still_detected` passes both before and after, as it should.

`test_stored_resources_match_a_disk_read` asserts its own comparison count against the mapping
  count. An earlier version of this audit keyed relative paths against absolute ones, matched zero
  resources, and reported a clean bill of health — the count assertion makes that failure mode loud
  instead of silent.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes — 1042 passed, 30
  subtests - [x] No breaking changes to the `poly` CLI interface (or migration path documented) -
  [x] Commit messages follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Two commits, so the noise is separable:

1. `chore(tests): normalize test_project fixture JSON formatting` — whitespace only, parsed content
  byte-for-byte identical. Skip it in review. 2. `fix(tests): make the test_project fixture match a
  real status file` — the actual corrections and tests.

Regenerated entries are full serializations, so they also fill in fields that were already
  semantically equal (for example `latency_control: {}` becoming its materialized default). No
  compared field changes value beyond the table above.

### Not addressed

No production code changes here. Worth considering separately: `sync_ids_with_sandbox` remains the
  only path using whole-object comparison, so a future field asymmetry can still cause spurious
  rewrites even with the fixture correct. Aligning it with the `compute_hash()`/`to_yaml_dict()`
  comparison the rest of the codebase uses would remove that class of bug structurally, but it needs
  an equivalence sweep first — a comparison that misses a real update is worse than one that stages
  a redundant write.

---------

Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>


## v0.44.1 (2026-08-14)

### Bug Fixes

- Include X-PolyAI-Email header on audio cache and test run requests
  ([#275](https://github.com/polyai/adk/pull/275),
  [`9a0f98e`](https://github.com/polyai/adk/commit/9a0f98e5e896460246e9601327e525a3bf5d2b33))

## Summary

Several `PlatformAPIHandler` methods built their request headers without forwarding
  `ADK_COMMAND_USER_OVERRIDE`, so those calls skipped the user-email attribution that every other
  request in the file already sends.

## Motivation

The generic `make_request` path (and other handler methods) forward `ADK_COMMAND_USER_OVERRIDE` as
  an `X-PolyAI-Email` header so the platform can attribute requests to the acting user. The
  audio-cache preview/synthesize and test-run listing methods built their headers independently and
  had missed this, so those specific endpoints silently skipped attribution whenever the override
  was set.

## Changes

- Add the `X-PolyAI-Email` header (from `ADK_COMMAND_USER_OVERRIDE`) to the header-building blocks
  in `get_conversation_audio`, `get_audio_cache_file`, `update_audio_cache_file`,
  `update_audio_cache_details`, and `synthesize_audio_cache` in `src/poly/handlers/platform_api.py`
  - Add test coverage in `src/poly/tests/api/platform_api_test.py` asserting the header is sent (or
  correctly absent) across all six header-building methods

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

N/A

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>


## v0.44.0 (2026-08-13)

### Features

- Support test clock (simulated_at) on test cases ([#273](https://github.com/polyai/adk/pull/273),
  [`2ffd8bd`](https://github.com/polyai/adk/commit/2ffd8bd17c8b7b807a3934722d303647fd9c20b2))

## Summary

Adds support for the test clock (`simulated_at`) on test cases. The field already exists on the
  `TestCase` protobuf messages but was dropped at every ADK layer, so a simulated time set in Agent
  Studio was invisible locally and never sent on push.

## Motivation

`simulated_at` pins the agent's notion of "now" for a simulated conversation, which is how
  time-dependent behaviour (out-of-hours routing, relative date resolution, seasonal greetings) is
  made deterministic. Today it can only be set in the Agent Studio UI: `poly pull` silently drops
  it, and there is no way to express it in `test_suite/*.yaml`.

## Changes

- Add optional `simulated_at` to the `TestCase` resource, stored as a canonical UTC ISO 8601 string
  - Read `simulatedAt` from the platform projection in `_read_test_cases_from_projection` (pull) -
  Emit/parse `simulated_at` in `to_yaml_dict` / `from_yaml_dict` - Send `simulated_at` as a protobuf
  `Timestamp` on `Create_TestCase` and `Update_TestCase` (push) - Accept ISO 8601 strings,
  `datetime` objects (ruamel parses unquoted YAML timestamps into one), and protobuf Timestamp JSON;
  normalise everything to UTC and raise a clear `ValueError` on an unparseable value - Document the
  field in `src/poly/docs/tests.md` and `docs/docs/reference/tests.md`

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

New tests in `TestCaseTests` cover UTC normalisation across input forms, YAML round-trip, omission
  when unset, invalid-value errors, create/update proto contents, and reading `simulatedAt` from a
  projection.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (788 passed) - [x] No
  breaking changes to the `poly` CLI interface — `simulated_at` is optional and omitted from YAML
  when unset - [x] Commit messages follow [conventional
  commits](https://www.conventionalcommits.org/)

## Note for reviewers

One behaviour worth a second opinion: `simulated_at` is a proto3 `optional` field, so unlike
  `variant_id` (which is cleared by sending `""`) there is no empty value to send. When a user
  removes `simulated_at` from a YAML file, `build_update_proto` leaves the field unset rather than
  explicitly clearing it — whether the platform treats "unset" as "no change" or "clear" decides if
  removing the field locally actually removes the test clock upstream. Happy to follow up if the
  platform needs an explicit clear signal.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 5 <noreply@anthropic.com>


## v0.43.0 (2026-08-13)

### Features

- Per flow settings ([#260](https://github.com/polyai/adk/pull/260),
  [`a9e0029`](https://github.com/polyai/adk/commit/a9e0029333814020f3bdeef388f29b3f244bd2f3))

## Summary

Consolidates per-step flow config (ASR biasing, DTMF, and the new ASR, VAD, barge-in and LLM
  sections) into a single `FlowSettings` sub-resource, pushed as one `update_step_settings` command
  instead of separate per-section commands. Adds the matching read path, clear path, and a
  status-dict migration.

## Motivation

The platform moved per-step overrides into a nested `FlowStepSettings` block behind a single update
  command, and introduced four new sections (ASR, VAD, barge-in, LLM) the ADK had no way to
  represent. Previously ASR biasing and DTMF were separate sub-resources with their own
  `flow_step_asr_config` / `flow_step_dtmf_config` commands, and the newer sections were
  unsupported.

## Changes

- **New `FlowSettings` sub-resource** grouping all six sections, replacing the separate
  `ASRBiasing`/`DTMFConfig` sub-resources. It is update-only (`update_step_settings`), matching the
  existing `AsrSettings` pattern — `CreateAdvancedStep` has no `settings` field, so settings on a
  new step ride along as an update after the step create. - **New config types** `ASRConfig`,
  `VADConfig`, `BargeInConfig` and `LLMConfig` (with a `ReasoningEffort` enum), each with
  `to_yaml_dict` / `to_proto`. - **Settings stay top-level in step YAML** (`asr_biasing:`,
  `dtmf_config:`, `llm:` …) so existing step files need no rewriting. - **Projection reading**
  handles the camelCase projection shape and maps `reasoningEffort` from its proto ordinal to the
  enum. The step's legacy top-level `asrBiasing`/`dtmfConfig` are only read when there is no
  `settings` block at all: the backend mirrors those on every settings update but never clears them,
  so consulting them per-section would resurrect a section the user had cleared. - **Clearing a
  section** emits `clear_step_settings`. `update_step_settings` merges per section, so a section
  dropped from local YAML would otherwise be read as "not updated" rather than "cleared". Only
  `asr`, `vad`, `bargeIn` and `llm` are sent — the backend's enum rejects anything else, and
  `asr_biasing`/`dtmf` are excluded by design because they deep-merge into the legacy top-level
  mirrors. Section names are translated to the backend's casing (`barge_in` → `bargeIn`); an unknown
  value fails validation for the whole command batch. - **Disabled sections** are omitted from step
  YAML for `asr_biasing` and `dtmf_config`, so disabled reads as absent. `barge_in` is kept even
  when disabled, since it is clearable and an explicit disable has to stay distinguishable from
  having no override. - **Status-dict migration** (`migrated_flow_step_settings`) folds legacy
  top-level keys into `settings`. Without it, a status file written by an older version loads with
  empty settings and reports every advanced step as modified — which also blocks `branch switch`,
  `merge` and `sync ids`, all of which refuse to run with uncommitted changes. - Regenerated the
  test project fixture into the new format and updated the affected tests.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

New coverage:

- `ClearUnusedSettingsFromFlowStepTest` — backend casing (`barge_in` → `bargeIn`), pass-through
  sections, all four clearable sections at once, `asr_biasing`/`dtmf` producing no command,
  unclearable sections not suppressing clearable ones, and the no-op cases (unchanged settings,
  added sections, step missing from remote state). - `FlowSettingsFromProjectionTest` — camelCase
  parsing across all six sections, every `reasoningEffort` ordinal, legacy top-level ignored when a
  settings block exists but read when it does not, and absent settings yielding empty settings
  rather than `None`. - `FlowSettingsSerializationTest` — full six-section YAML round-trip,
  `dtmf_config` as the YAML key, disabled-section handling, and `build_update_proto` setting only
  the sections present. - `MigrateFlowStepSettingsTest` — folding, loading the migrated shape into a
  `FlowStep`, newer settings taking precedence, and steps without legacy keys being left alone.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.42.2 (2026-08-13)

### Bug Fixes

- **sync**: Resolve flow step ids against the synced flow id
  ([#270](https://github.com/polyai/adk/pull/270),
  [`fe795ad`](https://github.com/polyai/adk/commit/fe795ada6aa077fa8824a764633e8ba982233402))

## Summary

`sync_ids_with_sandbox` could send a flow's `startStepId` with the flow id still welded onto the
  front of the step id, which the platform rejects with a validation error saying the start step id
  does not exist. This resolves flow step ids against the flow id the step was actually synced to.

## Motivation

Flow steps are identified locally by a composite `{flow_id}_{step_id}` resource id, and `FlowConfig`
  recovers a bare step id by stripping the `{flow_id}_` prefix off it.

`sync_ids_with_sandbox` built each flow-scoped resource's `ResourceMapping` using the resource's own
  stale, pre-sync `flow_id`. When the sandbox had assigned the flow a different id, the mapping's
  `flow_id` and the step's composite resource id disagreed, so `removeprefix` found no match.
  Because `removeprefix` fails open — returning the string unchanged rather than raising — nothing
  was stripped and no error surfaced locally. `start_step` kept the full composite value and the
  push failed server-side, aborting the whole command batch.

This was hit on a real sync against a live project.

## Changes

- Build a `flow_id_translation` lookup from each local `FlowConfig` id to the id it syncs to, and
  resolve flow-scoped resources' `flow_id` through it instead of trusting the stale local value. -
  Re-point the composite resource id of a flow step that has **no** sandbox counterpart (i.e. added
  on the branch) onto the synced flow id, so the embedded prefix and `flow_id` always agree. Without
  this the same corruption survives for branch-only steps. - Restrict that rewrite to `BaseFlowStep`
  subclasses with a genuinely matching prefix. Flow-scoped functions also carry a `flow_id` but keep
  standalone ids, so prepending a flow id to those would corrupt ids that were previously fine. -
  Add a `SyncIdsWithSandboxTest` suite covering the sync-id paths, which had no direct tests before.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

9 new tests. Both halves of the fix were mutation-tested — each was reverted in turn to confirm the
  relevant tests actually fail without it, rather than passing incidentally:

- start step resolves to a bare step id when the sandbox reassigned the flow id - same, when the
  start step is new on the branch and has no sandbox counterpart - a branch-only step is re-keyed
  onto the sandbox flow id, leaving no step straddling two flow ids - flow-scoped function ids are
  **not** rewritten - two flows reassigned at once do not contaminate each other (one fixture flow
  id is a string prefix of the other, so a substring-based rewrite would move steps under the wrong
  flow) - ids unchanged when sandbox ids already match, plus the two guard clauses

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before, for a flow whose sandbox id differs from the local one:

``` startStepId: "FLOW_CONFIG-abc12345_FLOW_STEPS-6789" # rejected by the platform ```

After:

``` startStepId: "FLOW_STEPS-6789" ```

### Follow-up

Stacked child: #271, which corrects the `test_project` fixture.

An earlier draft of this section claimed a no-op `sync_ids_with_sandbox` emits spurious writes
  because disk-read resources compare unequal to their projection-read counterparts. That claim was
  wrong and did not make it into this description. The churn came from the fixture storing values a
  real status file cannot contain, not from an asymmetry in the resource classes:
  `FlowStep.from_projection` always materializes `asr_biasing`/`dtmf_config`, and #255 already fixed
  the `Function` case. #271 has the detail.

What does remain, addressed in neither PR: `sync_ids_with_sandbox` is still the only path deciding
  what changed by comparing whole `Resource` objects, while `push`/`get_diffs` compare the
  rendered-file hash. That asymmetry is what allowed #255's bug to exist in the first place.

Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>


## v0.42.1 (2026-08-13)

### Bug Fixes

- Fake diff on test_suite ([#272](https://github.com/polyai/adk/pull/272),
  [`998f1d2`](https://github.com/polyai/adk/commit/998f1d2b0d0d7913e73b9a80427e710eac76fb88))

## Summary Integration attributes and sip headers were giving a fake diff due to how the origin is
  being loaded back from disk

## Motivation When loading a project, the previous known remote version was being loaded wrong,
  creating a spurious diff

## Changes - Load the object directly, not putting into the attribute or sip_headers part

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs Before: ``` -sip_headers: - resource_id: TEST_CASES-974954e0 - name:
  sip_headers - headers: {} -integration_attributes: - resource_id: TEST_CASES-974954e0 - name:
  integration_attributes - attributes: {} ``` After: ``` No changes detected. ```


## v0.42.0 (2026-08-13)

### Features

- Branch sync, history, rename, tag/untag, and archive/restore
  ([#247](https://github.com/polyai/adk/pull/247),
  [`948bcac`](https://github.com/polyai/adk/commit/948bcacd98846383c62f31806fc88f8a6c8ba2e5))

## Summary

Adds six `poly branch` subcommands — `sync`, `history`, `rename`, `restore`, `tag`, `untag` — plus
  `branch list --archived`, and teaches `branch create`/`merge`/`current`/`list` about branch
  lineage and the project's deployment mode. Commands the platform only exposes under simplified
  deployments are gated behind the `deployment_simplification` feature flag. Also makes `poly
  deployments list`/`show`/`promote`/`rollback` aware of that same deployment mode.

## Motivation

The platform's simplified deployment model introduces branch lineage (branches can be created from
  other branches), staging tags, and soft-archive/restore with a 30-day window. The ADK CLI had no
  support for any of it, and `poly branch merge` assumed every branch's parent was `main`. Once a
  project moves to simplified deployments, its old `sandbox` deployment history is also frozen in
  place — merges to main go straight to `live` — so the existing `deployments` commands needed to
  stop defaulting to `sandbox`.

## Changes

**New commands**

- `poly branch sync` — merge the parent branch's changes into the current branch, reusing the
  existing merge-conflict UX (`-i`/`--interactive`, `--resolutions`) - `poly branch history
  [--branch-name] [--limit]` — merge history for a branch, 10 entries by default - `poly branch
  rename [new_name]` — rename the current branch - `poly branch restore [branch]` — restore a
  soft-deleted branch from the archive - `poly branch tag` / `poly branch untag` — tag the current
  branch to deploy it to staging, or remove the tag - `poly branch list --archived` — list
  soft-deleted branches instead of active ones

**Changed behaviour**

- `branch create` now respects the project's deployment mode: one active branch in `simple`,
  main-only in `releases`, and branching off a direct child of main (max depth 2) in
  `releases_branches`. This replaces the previous unconditional "branches can only be created from
  main" guard. A new `--from <branch>` flag lets the source branch be named explicitly instead of
  always defaulting to whatever branch is currently checked out; the deployment-mode guards validate
  against the named source, not the current branch. - `branch merge` merges into the branch's actual
  parent instead of always `main`, switches to that parent afterwards, and shows a confirmation plus
  "now live" messaging when merging into main under simplified deployments. Merges into a branch
  other than `main` no longer require a merge message. - `branch current` also prints the parent
  branch, suppressed when the parent is `main` to avoid noise in the common case. `--json` always
  includes `parent_branch`. - `branch list` and the `switch`/`delete` interactive pickers render
  lineage as an indented tree in `releases_branches` mode, and show staging tags. - `branch`
  subcommands are regrouped into lifecycle and inspection groups in `--help`, and stale help
  text/epilogs are corrected. - `deployments list`/`show` default to the `live` environment instead
  of `sandbox` for projects using simplified deployments (`--env` still overrides). `show` no longer
  prints a "No intermediate deployments" placeholder when the included list is empty, since
  post-migration deployments legitimately have none. - `deployments promote` is refused outright for
  projects using simplified deployments — merging to main deploys straight to live, so there is no
  sandbox → pre-release → live ladder left to promote along, and the platform does not reject the
  call itself. - `deployments rollback` targets `live` rather than `sandbox` for projects using
  simplified deployments, since that's the only environment the platform accepts a rollback target
  for.

**Feature-flag gating**

- New `PosthogHandler` and `AgentStudioInterface.feature_flag_enabled`, backing
  `AgentStudioProject.using_simplified_deployments`. - `using_simplified_deployments` now also
  checks convergence: even with the feature flag on, it only reports `True` once the project's
  `live` deployment head is at least as recent as its `sandbox` head (i.e. `live` has caught up and
  sandbox is no longer receiving new deployments). This avoids treating a project as simplified
  mid-migration, while it still has newer sandbox deployments that haven't reached live. - New
  `require_deployment_simplification` helper gates `sync`, `tag`, and `untag` — the three endpoints
  the platform 404s when the flag is off. Previously these surfaced a bare `API error: 404 Client
  Error`; they now exit 1 with an explanatory message in both human and `--json` modes. - New
  `DeploymentMode` enum and `AgentStudioProject.deployment_mode`, read from the project's
  `config.deployment_mode` and defaulting to `releases`.

**Supporting API surface**

`sync_branch`, `get_branch_history`, `rename_branch`, `list_archived_branches`, `restore_branch`,
  `tag_branch`, `untag_branch`, `get_project`, and `create_branch(..., source_branch_id)` across the
  SDK, sync client, and interface. New console renderers for branch trees, archived branches, and
  merge history.

**Other**

- Adds `posthog==7.35.4`. - README `poly branch` section and `poly branch --help` examples updated
  to cover the new commands, including `--from`.

## Follow-ups (tracked separately, not silently dropped)

- The `sandbox` environment does not exist under simplified deployments, but it is still the
  hardcoded default for `diff`, `chat`, and the `rtc` commands, so those return empty results rather
  than an explanation. Fixing that also means introducing a shared environment constant — the
  three-environment literal is currently duplicated at 15+ sites — and renaming
  `sandbox`/`pre-release` to the branches/staging vocabulary the product now uses.

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (1208 passed, 61
  subtests) - [x] No breaking changes to the `poly` CLI interface (or migration path documented) -
  [x] Commit messages follow [conventional commits](https://www.conventionalcommits.org/)


## v0.41.0 (2026-08-12)

### Chores

- **protobuf**: Regenerate for mock call context ([#266](https://github.com/polyai/adk/pull/266),
  [`8fff71b`](https://github.com/polyai/adk/commit/8fff71b2eb6f5a2e4d1b4aa849396c2a8760be49))

The vendored protos under `src/poly/handlers/protobuf/` had drifted well behind the platform protos
  they are generated from. Regenerated wholesale rather than leaving a partial sync.

Companion to poly_core#44868, which does the same for its copy of these protos.

## What arrives

**`testing_pb2`**

* `TestCase` gains `caller_number = 20`, `sip_headers = 21` (`map<string, string>`),
  `integration_attributes = 22` (`google.protobuf.Struct`) * `Create_TestCase` / `Update_TestCase`
  gain `caller_number = 11` * New `SetTestCaseSipHeaders` and `SetTestCaseIntegrationAttributes`
  messages, with entries `452` and `455` in `commands_pb2` * `api_mocks = 19`, which had been
  missing since it shipped

**Also caught up by the same run**, none of it this project's work: `agent_settings`, `artifact`,
  `channels`, `functions`, `knowledge_base`, `snapshot`, `variant`. `webchat_csat_pb2` is new — it
  exists in poly_core's copy of these protos but had never been generated here.

## Provenance

Generated output only, no hand edits.

There is **no proto generation script in this repo** — `scripts/` holds only `sync_runtime_stubs.py`
  — so this reproduces what platform_ui's `apps/agent-stream/generate_protos.sh` does for poly_core:
  protoc 25.5, the same include paths against a poly_core checkout on master (`6d2f8d717a`), then
  the relative-to-absolute import rewrite pointed at `poly.handlers.protobuf` instead of the
  sourcerer_sdk package.

That the process is undocumented and unautomated is the reason for this drift, and is worth fixing
  separately.

## Verification

Constructed the new messages against the generated code:

``` TestCase: '+447700900000' {'x-dnis': '123'} {'retry_count': 2.0, 'tier': 'gold'}

command fields: ['set_test_case_sip_headers', 'set_test_case_integration_attributes'] ```

Full suite: **1008 passed**.

Note for the follow-up: `retry_count` went in as `2` and came back as `2.0`, because
  `google.protobuf.Struct` stores every number as a double. Invisible in the browser, where all
  numbers are doubles anyway, but it will need handling when these values are written to YAML.

## Not in this PR

This changes nothing user-visible on its own — `simulated_at` has been in these protos for a while
  and is still absent from the resource layer. Wiring the new fields into `test_suite.py` is
  [DEVP-580](https://linear.app/poly-ai/issue/DEVP-580).

Closes [DEVP-579](https://linear.app/poly-ai/issue/DEVP-579).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 5 <noreply@anthropic.com>

### Features

- **test-suite**: Support mock call context on test cases
  ([#267](https://github.com/polyai/adk/pull/267),
  [`9a439de`](https://github.com/polyai/adk/commit/9a439defffec0c15cddad42a570fff0a4be8bb06))

## Summary

Adds caller number, SIP headers and integration attributes to the test case resource so `poly pull`
  and `poly push` round-trip them, with docs in `src/poly/docs/tests.md`. Until now the ADK silently
  dropped all three.

**Stacked on #266** — its base should be retargeted to `main` once that merges.

## Motivation

Agent Studio can set mock call context on a test case; the ADK could not see or send it. Pulling a
  project omitted the fields from the YAML and pushing left them untouched on the server.

Closes [DEVP-580](https://linear.app/poly-ai/issue/DEVP-580)

## Changes

- `caller_number` on the `TestCase` resource — a scalar on `Create_TestCase` / `Update_TestCase`.
  Always sent, empty string included, since proto3 has no null and clearing it otherwise would not
  stick - `TestCaseSipHeaders` and `TestCaseIntegrationAttributes` subresources, each with its own
  `set_` command, on the existing `TestCaseTags` pattern - Both subresources are always constructed,
  even when empty — `get_new_updated_deleted_subresources` compares subresources, so an absent one
  cannot differ from the populated one it replaces and clearing a value would never push -
  `from_projection` reads the camelCase projection keys (`callerNumber`, `sipHeaders`,
  `integrationAttributes`) - Type handling so the YAML path matches the platform (see below) -
  `src/poly/docs/tests.md` — a "Mock call context" section with a worked example, per-field notes
  and the quoting rules

## Test strategy

- [x] Added/updated unit tests — 21 new - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested
  against a live Agent Studio project - [ ] N/A

**1029 passed**, ruff clean. Coverage of `test_suite.py` +3.4%.

Four behaviours are mutation-tested — each fails when the code it covers is reverted:

| Test | Reverting | |---|---| | `test_struct_doubles_are_written_back_as_ints` | the float
  normalisation | | `test_clearing_subresources_still_pushes` | guarding the comparison on
  non-emptiness | | `test_sip_header_bools_use_wire_casing` | `_header_value` back to `str()` | |
  `test_validate_rejects_dates_with_an_actionable_message` | the date branch |

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface — additive fields only - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

YAML types unquoted scalars, so it can produce values the Studio UI's text inputs never can. I
  probed every type against the generated protos rather than assuming; `string`, `number`, `float`,
  `bool`, `null`, `list` and nested `map` all round-trip correctly. Four cases did not:

| YAML | Was | Now | |---|---|---| | `x-flag: true` (SIP header) | `"True"` — Python's casing |
  `"true"` | | `x-none:` (SIP header) | `"None"` | `""` | | `expiry: 2026-08-12` (attribute) |
  `ValueError: Unexpected type` | rejected in `validate()` with the path and the quoted form | |
  `caller_number: +447700900000` | `TypeError: bad argument type` | rejected — see below |

A `Struct` also stores every number as a double, so an attribute pushed as `2` returns as `2.0` and
  would write `2.0` back to YAML, giving a spurious diff on every pull after a push. Integral floats
  are folded back to `int`; genuine decimals are untouched.

The caller number one is the subtle one. YAML reads `+447700900000` as the int `447700900000` —
  **dropping the `+`** — and that is indistinguishable from someone writing no `+` at all:

``` caller_number: +447700900000 -> 447700900000 str() -> '447700900000'

caller_number: 447700900000 -> 447700900000 str() -> '447700900000' ```

So `str()` would silently send a different number. It is rejected with a message saying to quote it.
  Caller number is also now trimmed on push, matching the platform entity, where a trailing space
  changes the agent-memory identifier.

## Still missing after this

`severity`, `simulated_at` and `api_mocks` remain unsupported by the resource layer, despite the
  latter two now being in the protos. Those are the same six fields
  [BLD-811](https://linear.app/poly-ai/issue/BLD-811) reports missing from the environment
  comparison renderer — every consumer of the TestCase model except the main form has fallen behind
  by the same set. Worth a follow-up.

---------

Co-authored-by: Claude Opus 5 <noreply@anthropic.com>


## v0.40.0 (2026-08-11)

### Features

- Add `poly fetch` command ([#213](https://github.com/polyai/adk/pull/213),
  [`89841d7`](https://github.com/polyai/adk/commit/89841d7fe0d5f59c282bbb35890fabcdc7f5d116))

## Summary

Adds a new `poly fetch` CLI command that downloads the latest remote project state and updates the
  status file, without writing resource files to disk or merging with local changes. Supports
  `--branch` to switch to an existing branch before fetching.

## Motivation

There's currently no CLI command to load the latest remote state without modifying local files.
  Operations like CI/CD pipelines need to switch to a branch and fetch its state before running
  `push`, `validate`, or `merge` — but today this is only possible via the Python API. `poly fetch`
  fills this gap, making these workflows possible with bash-only CLI calls.

Closes DEVP-247

## Changes

- Added `fetch_project()` method to `AgentStudioProject` — fetches remote state, updates in-memory
  resources and status file, optionally switches branch - Registered `poly fetch` CLI subcommand
  with `--path`, `--branch`/`-b`, `--json`, `--from-projection` (hidden), `--output-json-projection`
  (hidden) - Added 9 unit tests covering: basic fetch, branch switching, non-existent branch error,
  projection passthrough, save_config called, no resource files written

### Example CI usage

```bash # Switch to branch + fetch remote state + push local changes poly fetch -b my-branch --path
  /path/to/project poly push -f --path /path/to/project

# Fetch + validate poly fetch -b my-branch --path /path/to/project poly validate --path
  /path/to/project ```

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.39.0 (2026-08-10)

### Continuous Integration

- Make TruffleHog output actionable and drop the Lob false positive
  ([#263](https://github.com/polyai/adk/pull/263),
  [`8ff6342`](https://github.com/polyai/adk/commit/8ff6342388e830afb5aec1994ee2e564c0b8c2e0))

## What happened

The secret-scanning gate failed on #259 with exactly one line of output:

``` ##[warning]Found verified Lob result 🐷🔑 ```

No file, no line, no match. The actual trigger was a Python test function name —
  [`src/poly/tests/metrics_test.py:321`](https://github.com/polyai/adk/blob/main/src/poly/tests/metrics_test.py#L321):

```python def test_add_duplicate_metric_friendly_error(self, mock_load, mock_create, mock_error):
  ```

That's two separate problems, and this PR fixes both.

## 1. The finding was noise

TruffleHog's Lob detector combines two individually-weak choices:

```go keyPat = regexp.MustCompile(`\b((live|test)_[a-zA-Z0-9_]{35})\b`) // no keyword-proximity gate
  func (s Scanner) Keywords() []string { return []string{"live_", "test_"} } ```

The `Keywords()` prefilter is the pytest naming convention, so **every chunk in our test suite**
  reaches an ungated regex that matches any 40-character `test_*` identifier. It also treats HTTP
  **403 and 422** from `api.lob.com` as "verified" — only 401 counts as invalid — which is how a
  function name got reported as a *verified* secret.

Measured against this repo with TruffleHog 3.96.0 (`--no-verification`, all result types):

| Scope | Findings | After `--exclude-detectors=lob` | |---|---|---| | Working tree | 51 (all Lob) |
  0 | | Full `main` history | 85 (all Lob) | 0 |

Lob is **100% of the finding surface**. `main` already contains 36 more identifiers that match the
  pattern — they only stay quiet because scans are limited to each PR's commit range, so this would
  have recurred on any PR touching those lines. Roughly 4% of test names in the repo land on exactly
  40 characters.

ADK does not use Lob (direct-mail API), so there is no coverage to lose.

### Other detectors were checked, not assumed

Of 870 detectors, 133 lack a keyword-proximity gate and 74 have a prefilter keyword present in this
  repo. Intersecting gives 19 others that are live *and* ungated. All were tested against the source
  tree — **zero matches and zero near-misses**:

``` uri (user:pass@host) 0 twilio AC<32hex> 0 stripe pi_..._secret_ 0 redis:// creds 0 twilio SK<32>
  0 zohocrm 1000.hex.hex 0 ftp:// creds 0 launchdarkly 0 sendgrid SG. 0 mongodb:// creds 0
  salesforce 0 mailchimp <32hex>-usN 0 gemini master-/account- 0 closecrm api_<45> 0 lob (contrast)
  43 ```

Two worth noting: **Twilio** (`AC`+32hex) is the one to watch given our telephony code — clean
  today, but a realistic-shaped dummy SID in a fixture will fire it. **Auth0** looks alarming
  (`\b(ey[a-zA-Z0-9._-]+)\b` with prefilter keywords `token`/`domain`) but `FromData` requires a
  2000–5000 char match paired with an `*.auth0.com` domain, so it's well gated.

## 2. The output was unactionable regardless

The action always passes `--github-actions`, and that printer emits only the detector name and
  verification status:

```go fmt.Printf("::warning file=%s,line=%d,endLine=%d::%s", out.Filename, out.StartLine,
  out.StartLine, message) // message = "Found verified Lob result 🐷🔑" ```

File and line go into annotation *metadata* that never renders in the log, and the match is never
  printed at all. `extra_args` can't remove `--github-actions`, but `--json` outranks it in
  TruffleHog's printer selection, so a diagnostic step re-runs the scan on failure:

``` ────────────────────────────────────────── detector: Lob [verified]

file: src/poly/tests/metrics_test.py

line: 321

commit: 0b99540672d0 by Bill <bill@poly-ai.com>

match: test_add_dup… (40 chars) ```

Only a 12-character prefix is printed — enough to triage, not enough to use. The step exits 0; the
  gate above has already failed the job.

## 3. Also: the scanner version was floating

The action was SHA-pinned, but its `version` input defaulted to `latest` — the failing run logs
  `VERSION: latest`. The pin covered the wrapper, not the binary doing the scanning. Now pinned to
  `v3.96.0`.

## Testing

- YAML validated. - `jq` filter tested against a real TruffleHog JSON result record. - Exclusion
  confirmed to take both the working tree and full `main` history to zero findings. - Diagnostic
  step mirrors the gate's `--exclude-detectors` so the two can't disagree.

## Note for reviewers

This repo is public, and the description above documents which detector is disabled and that
  `--results=verified,unknown` filters out unverifiable detectors (`jwt`, `uri`, `sqlserver`). It's
  all derived from TruffleHog's public source. Happy to trim if anyone would rather that analysis
  live internally.

### Features

- Add example projects load and list commands ([#204](https://github.com/polyai/adk/pull/204),
  [`2f7fed1`](https://github.com/polyai/adk/commit/2f7fed19f163f9ac7f803dffc558d9916b78925b))

## Summary

Add `poly template list` and `poly template load` commands that let users browse and load example
  project templates from the platform.

## Motivation

Closes
  [DEVP-386](https://linear.app/poly-ai/issue/DEVP-386/add-template-selection-and-load-commands-to-adk-cli)

## Changes

- Add `poly template list` command to browse available example project templates, with optional
  `--region` flag - Add `poly template load <name>` command to load a template into the current
  project, with `--force` to skip confirmation and an interactive picker when no name is given

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

``` (polyai-adk) jamesosullivan@JAMES-O-C63L909T4T PROJECT-0Z28NPOM % poly template list --region
  dev Available templates (5):

Retail Customer Service Agent - Order & Shipping Support Tracks orders, handles returns, and
  resolves shipping issues on the call Restaurant Reservation Assistant Takes and changes table
  bookings, answers common questions, and resolves issues on the call Pest Control Field Service
  Assistant Schedules and manages pest control appointments, handles billing questions, and answers
  service FAQs Healthcare Clinic Receptionist Books, cancels, and reschedules appointments, answers
  patient questions, and routes urgent calls to staff Banking Customer Service Virtual Assistant
  Handles banking queries, processes payments, manages cards, and resolves account issues on the
  call

(polyai-adk) jamesosullivan@JAMES-O-C63L909T4T PROJECT-0Z28NPOM % poly template load "Retail
  Customer Service Agent - Order & Shipping Support" --region dev ? Loading 'Retail Customer Service
  Agent - Order & Shipping Support' will overwrite local project resources. Continue? Yes Loaded
  template Retail Customer Service Agent - Order & Shipping Support into
  ws-fd112d8f/PROJECT-0Z28NPOM (polyai-adk) jamesosullivan@JAMES-O-C63L909T4T PROJECT-0Z28NPOM %
  poly push Pushing local changes for ws-fd112d8f/PROJECT-0Z28NPOM... Pushed
  ws-fd112d8f/PROJECT-0Z28NPOM to Agent Studio. (polyai-adk) jamesosullivan@JAMES-O-C63L909T4T
  PROJECT-0Z28NPOM % ```

---------

Co-authored-by: Ruari Phipps <ruari@poly-ai.com>


## v0.38.4 (2026-08-07)

### Bug Fixes

- Read document projection field as content not contents
  ([#264](https://github.com/polyai/adk/pull/264),
  [`0ed2a3e`](https://github.com/polyai/adk/commit/0ed2a3e4f352ac95986ae1afb997c71d4769fe89))

## Summary

Follow-up to #262. The permission check there gates on a `contents` key, but the document projection
  carries the proto field name `content` (see `Document` in `documents_pb2.pyi`). Every entity
  therefore fails the check and `Document.from_projection` returns an empty dict, so no documents
  are pulled at all.

## Changes

- `from_projection` checks for and reads `content` instead of `contents` - Updated the projection
  fixtures in the tests, which had the same typo and so passed against the broken code - Added a
  case covering an empty-but-present `content` (readable, empty document — kept, not skipped)

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude <noreply@anthropic.com>


## v0.38.3 (2026-08-07)

### Bug Fixes

- Skip documents without readable contents ([#262](https://github.com/polyai/adk/pull/262),
  [`4e24a35`](https://github.com/polyai/adk/commit/4e24a35e73d1b148cf122906b187792068ef4a7a))

## Summary

Documents the current user lacks read permission for come back from the platform without a
  `contents` field. `Document.from_projection` now skips those entries instead of creating a
  `Document` with empty content.

## Motivation

Previously, a document missing `contents` in the projection was still materialized locally with an
  empty string, silently masking the fact that the user couldn't actually read it.

## Changes

- `Document.from_projection` skips entities that don't have a `contents` key - Reads the field via
  `document_data["contents"]` directly (only reached once presence is confirmed)

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  conventional commits

## Screenshots / Logs

N/A


## v0.38.2 (2026-08-07)

### Bug Fixes

- Preserve non-ASCII characters when writing RTC JSON files
  ([#261](https://github.com/polyai/adk/pull/261),
  [`5b06dd5`](https://github.com/polyai/adk/commit/5b06dd577f64da76710a05e2c06f57721987c405))

## Summary

`poly rtc pull` writes local `schema.json`/`data.json` files via `json.dump(..., indent=2,
  sort_keys=True)`, which defaults to `ensure_ascii=True`. Every non-ASCII character (e.g. `ô` in
  "Côte") gets escaped to `ô` even though the file is opened with `encoding="utf-8"`. The same issue
  affects `rtc edit`'s editor buffer and `rtc diff`'s console output.

Adds `ensure_ascii=False` to the JSON serialization calls in the RTC pull/edit/diff paths so files
  and terminal output contain the real UTF-8 characters. <img width="531" height="338" alt="image"
  src="https://github.com/user-attachments/assets/cdaf8b42-5d8d-41e8-aa93-69cbbbd9d3e7" />

## Test Strategy

- [x] Unit test added: `JsonIoTests.test_write_json_file_preserves_unicode` in
  `src/poly/tests/utils_test.py` - [x] Full test suite passes locally (`uv run pytest`, 995 passed)
  - [x] `ruff check` / `ruff format --check` clean on changed files


## v0.38.1 (2026-08-06)

### Bug Fixes

- Handle null schema/variables in RTC merge and diff paths
  ([#257](https://github.com/polyai/adk/pull/257),
  [`fa76ae6`](https://github.com/polyai/adk/commit/fa76ae66c1cf2f384ad594d8c4f63fc064008e9f))

## Summary

Fix crash when `poly rtc push` triggers a merge against a remote config with null schema or
  variables.

## Motivation

When a project has no RTC configured, the API returns `{"schema": null, "variables": null}`. The
  merge and diff code paths used `.get("schema", {})`, which returns `None` when the key exists with
  a null value (the default `{}` is only used when the key is absent). This caused `merge_rtc_dicts`
  to crash with `'NoneType' object is not iterable`.

## Changes

- Use `.get("schema") or {}` instead of `.get("schema", {})` in the RTC merge path (`rtc.py`) -
  Apply the same fix in the RTC diff path (`project.py`) - Matches the pattern already used in
  `rtc_pull_env` after the earlier null fix

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

<img width="462" height="68" alt="image"
  src="https://github.com/user-attachments/assets/f0d15c48-6018-416e-a9a9-5f093f182303" />

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>


## v0.38.0 (2026-08-06)

### Features

- Add SIP header overrides to chat ([#256](https://github.com/polyai/adk/pull/256),
  [`bb97864`](https://github.com/polyai/adk/commit/bb978643986582e5426175bb4a4f589d4a96a395))

## Summary

Adds a repeatable `poly chat --sip-header NAME=VALUE` option that simulates SIP headers on chat
  conversations, so agent behaviour that reads `conv.sip_headers` can be exercised without arranging
  a real SIP call.

## Motivation

Testing header-dependent agent logic today requires a real SIP call. This gives developers a quick
  local way to inject agent-visible header values from the chat CLI. Note the option is additive and
  simulates agent-visible values only; it does not reproduce SIP transport or carrier behaviour, and
  header injection depends on server-side chat API support rolling out separately.

## Changes

- Add a repeatable `--sip-header NAME=VALUE` option to the modular chat command - Validate header
  syntax while preserving values that contain `=` - Forward simulated headers through standard and
  draft conversation creation - Document the option

## Test strategy

- [x] Added/updated unit tests (CLI parsing, session forwarding, API payloads) - [ ] Manual CLI
  testing (`poly <command>`) - [ ] Tested against a live Agent Studio project - [ ] N/A (docs,
  config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

`pytest -q` result: 994 passed, 30 subtests passed


## v0.37.3 (2026-08-05)

### Bug Fixes

- Stop id sync rewriting every function in the project
  ([#255](https://github.com/polyai/adk/pull/255),
  [`c2ef04d`](https://github.com/polyai/adk/commit/c2ef04da90de4c1fe927633c3d70768b5eb7c968))

## Summary

`sync_ids_with_sandbox` was rewriting every function in the project on every id sync, because two
  `Function` dataclass fields are populated asymmetrically by `read_local_resource` and
  `from_projection` and both count toward the generated `__eq__`. This makes disk-read and
  projection-read functions compare unequal regardless of content.

## Motivation

`sync_ids_with_sandbox` is the **only** code path that decides what changed by comparing whole
  `Resource` objects (`resource != branch_resource`, `project.py:2850`). `push_project` gates on a
  rendered-file hash first (`project.py:1163-1171`), and `get_diffs` uses that same hash
  short-circuit plus a *text* diff of rendered output (`project.py:1547-1570`). So an asymmetric
  field is invisible everywhere except this one path — which is why this went unnoticed.

The two asymmetric fields were:

| Field | `read_local_resource` | `from_projection` | |---|---|---| | `variable_references` | always
  derives it from code — a dict, initialised to `{}`, never `None` | never sets it → `None` | |
  `description` | `_extract_decorators` returned `None` with no `@func_description` |
  `func["description"]`, which Agent Studio stores as `""` |

This caused a real incident on a customer project. A merge-time id sync — invoked to repair a
  handful of duplicate-name errors after resources were re-created under fresh ADK ids — emitted
  **155 commands, 63 of which were these false positives**: 36 global functions + 25 flow transition
  functions from `variable_references`, and the 2 special functions from `description`. That is
  every function in the project. Not one `create_function` or `delete_function` was in the batch, so
  all 63 kept their ids and were rewritten for no reason.

It matters beyond noise because Agent Studio wraps a command batch in a single transaction, so 63
  pointless commands are 63 extra chances to roll back the id repair that was the point of the sync;
  and it inflates the Agent Studio merge diff far past the corresponding git PR diff, which is what
  made the incident hard to spot.

`variable_references` is marked `compare=False` rather than populated from the projection, because
  it is derived from `code` — which *is* compared — so no real signal is lost. Transition functions
  never push their references at all (see below), so Agent Studio has nothing stored for them and it
  would have left 25 of the 63 false positives in place.

## Changes

- `Function.variable_references` is now `field(default_factory=dict, compare=False)` — excluded from
  the generated `__eq__`. - `Function._extract_decorators` defaults `description` to `""` instead of
  `None`, matching how Agent Studio stores an absent description. Return annotation tightened from
  `Optional[str]` to `str`. - Two regression tests in `src/poly/tests/resources_test.py`, both
  verified to fail without the fix.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

**Round-trip sweep across every resource type.** Build every resource from a real project
  projection, write it out with its own `save()`, read it back through the same path push and sync
  use, and diff the compared dataclass fields. Using `save()` rather than a mocked read is what
  makes multi-resource YAML files work — variant attributes, pronunciations, keyphrases and voice
  config are 180 of the 506 resources and were being silently skipped otherwise.

| Projection | Resources | Equal | Differ | |---|---|---|---| | feature branch | 506 across 24 types
  | 506 | **0** | | main | 507 across 24 types | 507 | **0** |

Before the fix, `Function` was 0/63. A static sweep was attempted first and abandoned as inadequate:
  only 6 of the 34 registered types define both `from_projection` and `read_local_resource` locally
  with a simple constructor call — the rest inherit the generic `YamlResource.read_local_resource`
  or build via helpers.

**Both new tests fail without the fix:**

``` FAILED
  src/poly/tests/resources_test.py::FunctionTests::test_equality_ignores_variable_references FAILED
  src/poly/tests/resources_test.py::FunctionTests::test_missing_description_reads_as_empty_string 2
  failed, 391 deselected ```

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes — 989 passed, 30
  subtests - [x] No breaking changes to the `poly` CLI interface (or migration path documented) -
  [x] Commit messages follow [conventional commits](https://www.conventionalcommits.org/)


## v0.37.2 (2026-08-04)

### Performance Improvements

- Error on merge conflicts instead of dumping every resource
  ([#240](https://github.com/polyai/adk/pull/240),
  [`3933d4f`](https://github.com/polyai/adk/commit/3933d4f7496279bae6141d7e98c9784da9c802c0))

## Summary

Makes `poly diff` / `poly status` error clearly on files with unresolved merge conflict markers
  instead of dumping every resource to scan for them. Removes the last redundant `dump_yaml` from
  the diff read path.

> Stacked on #239 — this PR targets that branch. Retarget to `main` once #239 merges.

## Motivation

`get_diffs` and `project_status` called `read_from_file` on every kept resource purely to run
  `contains_merge_conflict`. For multi-resource types that re-serialized the cached sub-dict
  (`dump_yaml`) — ~892 calls / ~3.4s on a large project — while the check itself is free. It was
  also the wrong mechanism: a file with conflict markers isn't valid YAML/Python, so it can't be
  parsed at all. The intended behaviour is to error, not to attempt a diff.

## Changes

- `resources/resource_utils.py`: add `MergeConflictError(ValueError)` and
  `raise_if_merge_conflicts(files)` (single aggregated, deduped error). - `resources/resource.py`:
  guard the three parse-read points so a conflicted file raises `MergeConflictError` *before*
  parsing — `Resource.read_to_raw` (code/doc resources), `YamlResource._read_yaml_dict` (single-file
  YAML), `MultiResourceYamlResource._get_top_level_data` (multi-resource YAML). Each piggybacks a
  read already performed (no extra I/O). Deliberately **not** added to the raw
  `Resource.read_from_file`, which `pull`'s 3-way text merge relies on. - `project.py`:
  `read_local_resource` re-raises `MergeConflictError` ahead of its generic handler; `get_diffs`
  collects conflicts across the kept/new loops and raises one aggregated error; `project_status`
  catches per-resource and still lists conflicted single-file resources.

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly diff` / `poly status` on a large
  project) - [ ] Tested against a live Agent Studio project - [ ] N/A

New tests: `get_diffs` raises for a conflicted single-file resource, for a conflicted multi-resource
  YAML file, and aggregates multiple conflicted files into one error; `project_status` surfaces a
  conflicted multi-resource file. Existing pull-with-conflict tests still pass unchanged (pull is
  untouched).

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (950 passed) - [x] No
  breaking changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

## Screenshots / Logs

`time poly diff` on a large project (median of 5 warm runs), continuing from #239's baseline:

| | #239 baseline | this PR | |---|---|---| | Wall time | **1.75s** | **0.74s** |

~2.4× faster on top of #239 (and ~5.4× vs. `main`'s 3.97s). Output unchanged (`No changes
  detected.`).

## Behaviour on conflict

All paths surface a clean, actionable CLI error (no traceback) — e.g. `Merge conflict:
  config/entities.yaml — resolve the conflict markers before continuing`. The message is derived
  from the offending path(s) by `MergeConflictError` itself.

- `diff` raises a clear `MergeConflictError` listing every conflicted file (it can't produce a diff
  of an unparseable file). - `status` lists conflicted files under "Files with merge conflicts" —
  including multi-resource YAML files (detected at discovery), whose resources are excluded from the
  new/kept/deleted comparison rather than miscounted as deleted. - `push` raises the same clear
  error when it reads a conflicted resource, so a half-resolved file is never pushed. - `pull`'s
  3-way text merge is unchanged (it reads conflicted files as raw text to re-merge); if it needs to
  *parse* a conflicted local file it raises the same clear error.

---------

Co-authored-by: Claude Opus 4.8 (1M context) <noreply@anthropic.com>


## v0.37.1 (2026-08-04)

### Performance Improvements

- Avoid YAML serialize/reparse roundtrip in multi-resource reads
  ([#239](https://github.com/polyai/adk/pull/239),
  [`59be491`](https://github.com/polyai/adk/commit/59be491a16aa3834f174a9b3e1c921a585fbd767))

## Summary

Removes a redundant YAML serialize→reparse roundtrip from the resource read path. Multi-resource
  reads now use the already-parsed cached dict directly, cutting `poly diff` on a large project from
  ~4.0s to ~1.8s (2.3×, measured with `time poly diff`).

## Motivation

Profiling `poly diff` on a large agent project showed the time dominated by ruamel.yaml (serialize +
  parse). The cause: `MultiResourceYamlResource` caches each file already parsed as a dict, but on
  every resource read it dumped the matching sub-dict back to a YAML string just so the string-based
  name→ID replacement could run, then immediately reparsed that string into a dict. The dict was
  squeezed through a string and reconstituted for no benefit (the loader is `typ="safe"`, so no
  comments/formatting are preserved).

## Changes

- `resource_utils.py`: add `replace_resource_names_with_ids_in_data`, a dict/list-walking equivalent
  of the existing string replacement; factor the shared lookup/replacer into
  `_build_reference_replacer` (behaviour of the two string functions is unchanged). - `resource.py`:
  add a `_read_yaml_dict` read seam. `MultiResourceYamlResource` returns its cached sub-dict via a
  single `_get_matching` seam that both `read_from_file` (string) and `_read_yaml_dict` (dict)
  derive from. Move the generic name→ID replacement into the base `from_pretty_dict` (it now walks
  the dict and returns fresh containers), instead of a whole-string pass in `read_local_resource`. -
  `flows.py`, `test_suite.py`, `phrase_filter.py`, `variant_attributes.py`: the four
  `from_pretty_dict` overrides now call `super().from_pretty_dict()` first so they keep the generic
  replacement. - `languages.py`: `DefaultLanguage` / `AdditionalLanguage` override `_get_matching`
  (their on-disk form is a bare scalar) instead of `read_from_file`, removing the need for a
  special-case flag.

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly diff` on a large project — output
  byte-identical, "No changes detected.") - [x] Tested against a live Agent Studio project - [ ] N/A
  (docs, config, or trivial change)

New unit tests assert the dict-walking replacement matches the old string-path result on nested
  structures, preserves non-string leaves and keys, does not mutate its input, and honours
  flow-scoped mappings.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (946 passed) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

`time poly diff` on a large project (median of 5 warm runs):

| | Before | After | |---|---|---| | Wall time | **3.97s** | **1.75s** |

~2.3× faster; output unchanged (`No changes detected.`).

_(Earlier drafts of this PR quoted cProfile totals, which inflate ruamel's per-call cost; the above
  are real `time poly diff` wall-clock numbers.)_

---------

Co-authored-by: Claude Opus 4.8 (1M context) <noreply@anthropic.com>


## v0.37.0 (2026-08-04)

### Continuous Integration

- Add TruffleHog secret scanning on PRs and pushes to main
  ([#248](https://github.com/polyai/adk/pull/248),
  [`33ad68f`](https://github.com/polyai/adk/commit/33ad68f11d0d277db550a1c6d95f88c1faec0d2f))

## Summary

Adds automated secret scanning so committed credentials get caught on PRs and on direct pushes to
  `main`.

## Motivation

Native GitHub secret scanning/push protection are repo-level metadata settings — they don't travel
  when this repo is forked/copied for integrator engagements, and don't apply to private copies
  without an org-wide GHAS security configuration. A workflow file lives in repo content instead, so
  it copies automatically with the repo regardless of where it ends up.

## Changes

- New `.github/workflows/secret-scanning.yml` running [TruffleHog
  OSS](https://github.com/trufflesecurity/trufflehog) (pinned by commit SHA to `v3.96.0`, not
  `@main`) on `pull_request` and on `push` to `main`. - Uses `--results=verified,unknown` — flags
  confirmed-live secrets plus unverifiable-but-suspicious matches, filtering out ones TruffleHog can
  positively confirm are already dead. - Since a lot of contributors push directly to `main` without
  going through a PR, a failed scan on a `push` event also opens a GitHub issue, assigns the pusher,
  and labels it `secret-leak`/`security`, with instructions to rotate the credential immediately
  (it's already in git history even once removed from `HEAD`).

Out of scope: this detects post-push, it doesn't block the push itself — true prevention needs
  native GitHub push protection or a required-status-check + branch protection setup, which needs
  repo admin access to configure separately.

## Test strategy

- [ ] N/A (docs, config, or trivial change)

Workflow syntax has not been exercised against a live PR in this repo yet — first run against this
  PR itself will be the validation.

## Checklist

- [x] Commit messages follow [conventional commits](https://www.conventionalcommits.org/) - [ ]
  `ruff check .` and `ruff format --check .` pass (no Python changed) - [ ] `pytest` passes (no
  Python changed) - [ ] No breaking changes to the `poly` CLI interface (or migration path
  documented) — N/A

### Features

- Add poly audio-cache CLI commands (DEVP-377) ([#246](https://github.com/polyai/adk/pull/246),
  [`f682c99`](https://github.com/polyai/adk/commit/f682c999c0278cf6dcc4553ff648c1dfc1e28d2f))

## Summary

Adds `poly audio-cache` CLI commands wrapping the Audio Cache public API (poly_core PR #42487) so
  developers can manage an agent's cached TTS audio without hand-rolled HTTP calls.

## Motivation

[DEVP-377: Create ADK CLI commands for voice cache
  API](https://linear.app/poly-ai/issue/DEVP-377/create-adk-cli-commands-for-voice-cache-api)

Closes DEVP-377

## Changes

- `poly audio-cache list` — list cached entries with pagination/sorting - `poly audio-cache
  get-file` — download the cached WAV file - `poly audio-cache update-file` — replace the audio file
  for an entry - `poly audio-cache update-details` — replace audio + voice tuning settings together
  - `poly audio-cache delete` / `bulk-delete` — remove one or many entries - `poly audio-cache
  synthesize` — preview TTS audio without saving to cache - New
  `PlatformAPIHandler`/`AgentStudioInterface` methods for the above, following the existing
  `conversations` command pattern (including binary upload/download support, which is new) -
  `print_audio_cache_entries` table helper in `console.py` - Unit tests for the handler layer
  (`platform_api_test.py`) and CLI layer (`cli_test.py`) - `cli.md` reference docs for the new
  command family

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly audio-cache --help` and all
  subcommand `--help` variants, plus a local file-read/write smoke test) - [ ] Tested against a live
  Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (974 passed) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>


## v0.36.3 (2026-07-29)

### Bug Fixes

- Tolerate transient errors while polling test run status
  ([#244](https://github.com/polyai/adk/pull/244),
  [`5c65ccb`](https://github.com/polyai/adk/commit/5c65ccb5d2aa5b6c9ef177ed8b7694379f4f7482))

## Summary

`poly test run` polls a test run's status in a loop; a single transient network/5xx error from that
  poll used to crash the whole command, even though the run kept executing and completing
  server-side.

## Motivation

Observed a case where `poly test run` errored out mid-poll with `500 Server Error`, but the run
  itself later showed as `completed` via `poly test list` — the CLI gave up on a recoverable,
  transient failure instead of retrying.

## Changes

- `poll_test_run_live` now catches `requests.exceptions.RequestException` around each status poll. -
  Tolerates up to 5 consecutive failed polls (configurable via `max_consecutive_errors`), resetting
  the counter on any successful poll. - If the failure threshold is exceeded, it stops gracefully
  with a warning pointing to `poly test show <test_run_id>` instead of raising.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

New tests in `src/poly/tests/console_test.py` cover: transient-error recovery, error counter reset
  on success, give-up after sustained failures, and the unchanged happy path.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.36.2 (2026-07-29)

### Performance Improvements

- Defer heavy CLI imports to speed up startup ([#243](https://github.com/polyai/adk/pull/243),
  [`6b61d00`](https://github.com/polyai/adk/commit/6b61d00acd7b4ed46c2b4af0238728be03d87104))

## Summary

Defers heavy third-party imports out of CLI module load so `poly` commands don't pay for
  dependencies they don't use. Cuts `import poly.cli` from ~284ms to ~180ms (~37%).

## Motivation

`poly`'s entrypoint imports every command module up front (to register argparse subcommands), so a
  few heavy deps were loaded on *every* invocation regardless of the command: - `prompt_toolkit` +
  `questionary` (~55ms) — interactive prompts, only used by `poly rtc` - `langcodes` (~16ms,
  compiles regex/data tables at import) — language validation only - `jsonschema` (~20ms) —
  experimental-config validation only

A `poly diff`/`status`/`pull` never touches any of these, but paid ~90ms of import cost for them.

## Changes

Moved each import to point-of-use inside the function that needs it: -
  `resources/resource_utils.py`: `langcodes` → inside `is_valid_language_code`. -
  `resources/experimental_config.py`: `jsonschema` → inside `ExperimentalConfig.validate`. -
  `cli_commands/rtc.py`: `questionary`/`requests` → local imports in the five methods that use them.
  - `tests/rtc_test.py`: re-point three mock patches from `poly.cli_commands.rtc.questionary` (no
  longer a module attribute) to `questionary.confirm`.

No behavior change — purely where the imports happen.

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly --help`, `poly diff` — verified
  `prompt_toolkit`/`questionary`/`langcodes`/`jsonschema` no longer load at startup via `python -X
  importtime`) - [ ] Tested against a live Agent Studio project - [ ] N/A

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (937 passed) - [x] No
  breaking changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

## Screenshots / Logs

`python -X importtime -c "import poly.cli"`:

| | Before | After | |---|---|---| | `import poly.cli` cumulative | ~284ms | ~180ms | |
  `prompt_toolkit`/`questionary` | loaded | not loaded | | `langcodes` | loaded | not loaded | |
  `jsonschema` | loaded | not loaded |

Co-authored-by: Claude Opus 4.8 (1M context) <noreply@anthropic.com>


## v0.36.1 (2026-07-28)

### Bug Fixes

- Write empty object instead of null for unset RTC schema/variables
  ([#242](https://github.com/polyai/adk/pull/242),
  [`c58e621`](https://github.com/polyai/adk/commit/c58e621553d167c3bfbb278020a64133fc26e20c))

## Summary

`poly rtc pull` wrote literal `null` into `schema.json`/`data.json` when a project had no RTC
  configured. This now correctly writes `{}`.

## Motivation

The RTC API returns `schema`/`variables` as explicit JSON `null` (not omitted) when a project has no
  RTC configured. `dict.get(key, {})` only substitutes the default when the key is *absent* — since
  the key is present with value `null`, the code got `None` through, which was then written straight
  to disk via `json.dump`, producing literal `null` instead of `{}`.

## Changes

- `src/poly/project.py`: `rtc_pull_env` now uses `config.get("schema") or {}` /
  `config.get("variables") or {}` - `src/poly/cli_commands/rtc.py`: same fix applied to the
  `rtc_edit` command path - Added regression tests in `src/poly/tests/project_test.py`
  (`RtcPullEnvTest`) and `src/poly/tests/rtc_test.py`

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly rtc pull`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<img width="568" height="135" alt="image"
  src="https://github.com/user-attachments/assets/fd561b64-e419-4406-8073-b7bf64b51960" />

Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>


## v0.36.0 (2026-07-24)

### Features

- Add poly rtc pull/push commands ([#215](https://github.com/polyai/adk/pull/215),
  [`493edaa`](https://github.com/polyai/adk/commit/493edaa15440ba22af92ea552899ece9c6e58cbe))

## Summary

Adds `poly rtc pull`, `push`, `edit`, `diff` and `validate` commands to sync Real-Time Configuration
  between local files and Agent Studio, with drift protection, 3-way merge on conflicts, and
  `--include-rtc` integration on existing pull/push.

## Motivation

RTC config is currently only manageable through the Agent Studio UI. This lets teams version-control
  their RTC schema and variables alongside the rest of their agent project, and push changes from
  the CLI — with safeguards against overwriting each other's changes.

## Changes

- poly rtc pull — fetches schema + variables per environment, writes schema.json and data.json to
  real_time_configuration/<env>/ - poly rtc push — reads local files, validates data against schema,
  and uploads to Agent Studio (schema via PUT, variables via PATCH) - poly rtc edit — pulls latest,
  opens in $EDITOR, validates JSON, and pushes back in one step with race detection - poly rtc diff
  — compares local files against remote config, shows field-level changes (added, removed, changed)
  - poly rtc validate — validates local data.json against its schema.json using JSON Schema Draft 7
  - --env sandbox|pre-release|live|all for pull, diff, and validate; --env required for push and
  edit - --schema / --data flags for selective pull/push (mutually exclusive, default does both) -
  --schema flag on edit to edit the schema instead of data variables - --skip-validation on push to
  bypass schema validation - Live push/edit requires --force or interactive confirmation -
  --include-rtc on regular poly pull / poly push to sync RTC alongside normal resources - Drift
  protection — compares lastUpdated from API against stored metadata before pushing - 3-way merge
  when drift is detected — auto-merges non-conflicting field changes (including nested dicts),
  interactive resolution for true conflicts (local/remote/base/edit in $EDITOR) - --no-merge flag to
  disable merge and hard-fail on drift - RTC metadata and base copies stored in .agent_studio_config
  (no extra dotfiles for tracking) - Partial push failure updates metadata so retries don't falsely
  trigger drift - RTC IO logic lives in project.py, CLI/interactive logic in cli_commands/rtc.py -
  Helpers (write_json_file, read_json_file, diff_dicts, merge_rtc_dicts) in utils/json_io.py and
  utils/merge.py - Schema validation (validate_rtc_data) as a static method on AgentStudioProject -
  RTC failures propagate to the overall exit code for CI/automation

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly rtc pull`, `poly rtc push`) - [x]
  Tested against a live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- TODO: add terminal output after manual testing --> ### push / pull <img width="1630"
  height="98" alt="image (18)"
  src="https://github.com/user-attachments/assets/3e30aaeb-73b5-4474-bb5b-990ca9510968" /> <img
  width="1600" height="664" alt="image (17)"
  src="https://github.com/user-attachments/assets/f9ee7e48-75b0-4a69-a258-65cf5aa82438" /> <img
  width="591" height="299" alt="image"
  src="https://github.com/user-attachments/assets/75524385-7137-4cc7-9069-31854a5a9606" />

### rtc pull --data <img width="737" height="97" alt="image"
  src="https://github.com/user-attachments/assets/41254f5c-05d4-4c8e-9529-2ff2bc3d8d05" />

### edit command: <img width="796" height="399" alt="image"
  src="https://github.com/user-attachments/assets/cabd353c-178b-4cf3-b302-64773fc6cd67" /> <img
  width="672" height="151" alt="image"
  src="https://github.com/user-attachments/assets/a323e579-7ef9-438d-a5aa-e9c4ed923348" />

#### edit alidation <img width="651" height="60" alt="image"
  src="https://github.com/user-attachments/assets/960e8217-84dc-4ab4-942b-07a9afe3245a" />

tested with
  [firebirds](https://jupiter.polyai.app/firebirds-us/firebirds-usp/real-time-configuration/sandbox?panel=config-builder):
  <img width="767" height="290" alt="image"
  src="https://github.com/user-attachments/assets/277116a4-de71-40e3-b570-0a8df28fae5c" />

### diff <img width="651" height="125" alt="image"
  src="https://github.com/user-attachments/assets/30490468-48e5-452d-8229-faeac5398621" /> <img
  width="658" height="147" alt="image"
  src="https://github.com/user-attachments/assets/1f48b816-174f-4565-8079-5a03b3ba11ea" /> <img
  width="580" height="96" alt="image"
  src="https://github.com/user-attachments/assets/a1d330e8-19dd-4fdc-aa62-bf1d795fec18" />

### validate <img width="663" height="197" alt="image"
  src="https://github.com/user-attachments/assets/02dd5cbf-a4d6-494d-bbcf-a8820887e5cc" /> <img
  width="616" height="64" alt="image"
  src="https://github.com/user-attachments/assets/d4e84680-f72d-46f5-b858-873fca070e77" /> <img
  width="669" height="241" alt="image"
  src="https://github.com/user-attachments/assets/6fb1e1e3-02ed-47e5-8a34-0d6519312f77" />

**push with validation error** <img width="656" height="86" alt="image"
  src="https://github.com/user-attachments/assets/9801d822-63b6-4301-95e4-6590a63456c2" />

## Ticket and scoop

https://poly-ai.atlassian.net/browse/TYT-1376?search_id=a334215f-41b7-4842-943d-f3d4cadc111b
  https://poly-ai.atlassian.net/browse/TYT-1375

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

Co-authored-by: Copilot Autofix powered by AI <175728472+Copilot@users.noreply.github.com>


## v0.35.0 (2026-07-24)

### Chores

- Add testpaths to pytest config ([#234](https://github.com/polyai/adk/pull/234),
  [`86a9c7e`](https://github.com/polyai/adk/commit/86a9c7ef088bba9d9fe3c01f095d91335d8d4b34))

## Summary

Add `testpaths` to pytest config so bare `uv run pytest` only collects from `src/poly/tests/`.

## Motivation

Running `uv run pytest` without an explicit path caused pytest to collect
  `src/poly/resources/test_suite.py` as a test module (it matches the `test_*.py` pattern). This
  interfered with `TestCase` resource registration and caused 6 tests to fail. Running `uv run
  pytest src/poly/tests/` worked fine, masking the issue in CI.

## Changes

- Add `testpaths = ["src/poly/tests"]` to `[tool.pytest.ini_options]` in `pyproject.toml`

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Features

- Add branch diff, review, and status commands ([#227](https://github.com/polyai/adk/pull/227),
  [`72887f4`](https://github.com/polyai/adk/commit/72887f4b57f987e8b9afc865f226a376c51eabd6))

## Summary

Add `poly branch diff`, `poly branch review`, and `poly branch status` commands that compare a
  branch against its fork-point state, mirroring the UI's branch comparison screen.

## Motivation

The platform now shows branch comparisons relative to the fork point (not latest main), powered by
  `?atSequence=` on the projection endpoint. ADK had no CLI equivalent — `poly diff` compares local
  vs remote, not branch vs fork-point. These commands fill that gap as the "review before merge"
  workflow alongside `branch merge`.

## Changes

- Add `poly branch diff` — prints fork-point diff to terminal (supports `--files`, `--json`) - Add
  `poly branch review` — creates a GitHub Gist of the fork-point diff for sharing - Add `poly branch
  status` — shows new/modified/deleted files on a branch vs fork point, same output format as `poly
  status` with extra branch metadata in the header - Update `get_branches()` across the stack to
  return `dict[str, dict[str, Any]]` (full branch metadata including `parentBranchId`,
  `parentSequence`, `isDiverged`) instead of `dict[str, str]` - Add `branch_id` and `at_sequence`
  params to `fetch_projection()` for fetching historical projections without cache mutation - Add
  `pull_branch_resources()` to sync client and interface layers - Extract
  `_resolve_branch_fork_point()` in project layer, shared by `diff_branch()` and `branch_status()` -
  Refactor `StatusCommand.status()` to use shared helpers from `shared.py` - Fallback: when
  `parentSequence` is null (older branches), compares against latest parent with a warning

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.7 (2026-07-21)

### Bug Fixes

- Use flow_id instead of flow_name in from_projection resource ID construction
  ([#233](https://github.com/polyai/adk/pull/233),
  [`34bdc2c`](https://github.com/polyai/adk/commit/34bdc2c0d9cbfe13a786108adebb8685eeb42641))

## Summary

Fix flow validation regression introduced in v0.34.6 where `poly validate` reports "Start step not
  found" for all flows.

## Motivation

PR #216 introduced `from_projection` methods on `FlowStep` and `FunctionStep` that construct
  resource IDs as `{flow_name}_{step_id}`. However, PR #220 had already changed the convention to
  `{flow_id}_{step_id}`. The merge didn't produce a textual conflict, so the old convention slipped
  through. `FlowConfig.validate` builds expected IDs with `flow_id`, so the lookup fails.

## Changes

- Changed `FlowStep.from_projection` to use `flow_id` instead of `flow_data['name']` for resource ID
  prefix - Changed `FunctionStep.from_projection` to use `flow_id` instead of `flow_data['name']`
  for resource ID prefix - Updated corresponding test assertions

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.6 (2026-07-21)

### Bug Fixes

- Remove unused `# type: ignore` from secret_vault.py types stub
  ([#232](https://github.com/polyai/adk/pull/232),
  [`6a39105`](https://github.com/polyai/adk/commit/6a391052de498db8b75e5526bbc08651776309b5))

## Summary

- Removes the blanket `# type: ignore` directive from `src/poly/types/secret_vault.py`

The `# type: ignore` comment triggers an `unused-type-ignore-comment` warning with `ty`, which
  `agent-deployments` uses as a pre-commit hook. This causes commits that touch
  `_gen/secret_vault.py` to fail:

``` warning[unused-type-ignore-comment]: Unused blanket `type: ignore` directive -->
  agents/.../sticks-n-sushi-ukp/_gen/secret_vault.py:4:1 | 4 | # type: ignore | ^^^^^^^^^^^^^^ ```

This will prevent having to manually delete that line of code every time you initialize a project.

## Test plan

- [x] Verified `ty check src/poly/types/secret_vault.py` passes after the change

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Refactoring

- Clean up project.py, split poly.utils into focused modules and add API handler tests
  ([#214](https://github.com/polyai/adk/pull/214),
  [`e2d6402`](https://github.com/polyai/adk/commit/e2d6402d63af791dfc8cced43e848e332afb476a))

## Summary

Behaviour-preserving cleanup of the two largest maintenance hotspots — `project.py`'s duplicated
  pull logic and 365-line `_clean_resources_before_push`, and the mixed-concern `poly/utils.py` —
  plus a new test suite for the previously untested API handler layer.

## Motivation

`project.py` and `utils.py` had grown organically: the two pull methods shared ~40 duplicated lines
  (acknowledged by an in-code comment), `_clean_resources_before_push` mixed eight distinct concerns
  in one method, and `utils.py` bundled six unrelated utility groups. The handlers layer (~4,200
  lines: platform_api, interface, sync_client, sdk, auth0_handler) had no tests at all, and test
  runs were polluting the `test_project` fixture with a generated `.agent_studio_config`.

## Changes

- Extract `_apply_pulled_resources`, shared by `pull_project` and `pull_project_from_env` (public
  signatures unchanged) - Split `poly/utils.py` into a `poly/utils/` package (`credentials`,
  `merge`, `stub_gen`, `decorators`, `variable_references`, `commands`) with all public names
  re-exported from `poly.utils`, so existing imports keep working - Split
  `_clean_resources_before_push` into eight focused functions in `poly/utils/prepush.py`; the method
  remains as a thin orchestrator with an unchanged contract - Stop tests writing
  `_gen/.agent_studio_config` into the fixture project (mock the `api_handler` property, make the
  prepush webchat step access it lazily, gitignore the file) - Add `src/poly/tests/api/` — 62 unit
  tests for the handler layer (region/URL routing, request headers and error paths, error-code
  mapping, projection parsing, command queue priority ordering, protobuf batch sending, device auth
  flow), all HTTP mocked

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

833 tests + 30 subtests pass. Each commit was verified independently against the full suite. The new
  handler tests also pass with `POLY_ADK_KEY` unset, proving no network access. After a full test
  run, `git status` shows no fixture pollution.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

``` $ uv run pytest src/poly/tests/ -q 833 passed, 30 subtests passed in 7.41s ```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Fable 5 <noreply@anthropic.com>

- Move projection parsing onto resource classes ([#216](https://github.com/polyai/adk/pull/216),
  [`0417794`](https://github.com/polyai/adk/commit/0417794ad8c25fcc0a6e39807d480ec2470baefa))

## Summary

Move projection-parsing logic from `SyncClientHandler` onto each resource class via
  `@register_resource`, and shift the Resources → Commands conversion into `AgentStudioInterface`.

## Motivation

`SyncClientHandler` mixed read (projection parsing) and write (command building) concerns, and owned
  ~700 lines of `_read_*_from_projection` methods that were far from the resource classes they
  construct. Adding a new resource type required editing `sync_client.py`. The
  `SyncClientHandler`/`AgentStudioInterface` split was a remnant of a removed dual-backend feature
  flag.

## Changes

- Each resource class now has a `from_projection()` classmethod registered via
  `@register_resource("name")` decorator - `@register_resource` also populates
  `RESOURCE_NAME_TO_CLASS` / `RESOURCE_CLASS_TO_NAME`, replacing the hardcoded dict in `project.py`
  - `load_resources_from_projection()` is a standalone function in `resource.py` — no API
  dependency, works offline - `SyncClientHandler` returns raw projection dicts;
  `AgentStudioInterface` does the conversion - `queue_resources` (Resources → Commands) with
  priority ordering moved to `AgentStudioInterface` - Shared helpers `parse_latency_control` and
  `parse_safety_filter_config` moved to their respective resource modules

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.5 (2026-07-20)

### Bug Fixes

- Normalize document paths to uppercase to prevent case-sensitivity conflicts
  ([#231](https://github.com/polyai/adk/pull/231),
  [`f26fc38`](https://github.com/polyai/adk/commit/f26fc3885f4e8f54555db1bd4a0615f1ac6a73e9))

## Summary

Normalizes all Document resource paths to uppercase at every entry point to prevent case-sensitivity
  conflicts on macOS's case-insensitive filesystem.

## Motivation

On macOS (case-insensitive APFS), creating a local `context.md` and a remote `CONTEXT.MD` causes the
  system to treat them as different resources despite being the same file on disk. This leads to the
  remote version being incorrectly deleted on push, as `find_new_kept_deleted` uses case-sensitive
  string comparison for file path matching.

`CONTEXT.MD` is the version that the user can see in Studio Assistant

## Changes

- Added `Document.__post_init__` to normalize `self.path` to uppercase on construction - Updated
  `Document.discover_resources()` to uppercase filenames from `os.listdir()` - Updated
  `_read_documents_from_projection()` to use uppercase-normalized path as resource_id - Updated
  `find_new_kept_deleted()` to uppercase the resource_id for new Documents - Updated existing test
  assertions and added `test_path_normalized_to_uppercase`

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

N/A

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.4 (2026-07-13)

### Bug Fixes

- Normalize local multi-resource content before merge
  ([#229](https://github.com/polyai/adk/pull/229),
  [`87adab2`](https://github.com/polyai/adk/commit/87adab29233e7cc5608529ee84b21073c9e1f933))

## Summary

Normalize local multi-resource YAML content through resource classes before the three-way merge on
  pull, preventing false merge conflicts caused by serialization differences.

## Motivation

The three-way merge for multi-resource files (entities, keyphrases, etc.) read local files raw from
  disk, while original and incoming content went through resource objects (`read_local_resource` →
  `save(save_to_cache=True)`). Serialization differences — such as default values (`relative_date:
  false` vs `config: {}`), case normalization (`Boosted` vs `boosted`), or whitespace stripping —
  caused false merge conflicts on pull even when the logical content was identical.

The non-multi-resource path already normalizes local content via `read_local_resource` → `to_pretty`
  (with the comment "Normalise the local resource to ensure formatting differences don't cause
  unnecessary merge conflicts"). The multi-resource path was missing this normalization.

## Changes

- Replaced raw `Resource.read_from_file()` local read in `_update_multi_resource_yaml_resources`
  with `read_local_resource` → `save(save_to_cache=True)`, mirroring how original and incoming
  content are already computed - Falls back to raw read for files not covered by the object-based
  path (e.g. edge cases) - Added test verifying that mixed-case keyphrase levels in local YAML don't
  cause false conflicts on pull

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- **agent-setting**: Agent setting sort ([#230](https://github.com/polyai/adk/pull/230),
  [`6ed879c`](https://github.com/polyai/adk/commit/6ed879cdbb925223d57d40adb96de894c860a4f9))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. --> Fix agent setting sort to prevent merge
  conflicts ## Motivation

<!-- Why is this change needed? Link to an issue if applicable. --> The order of the keys can
  sometimes change causing merge conflicts. Closes #<!-- issue number -->

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

-

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.34.3 (2026-07-09)

### Bug Fixes

- Normalize personality adjectives on pull and send removals on push
  ([#225](https://github.com/polyai/adk/pull/225),
  [`3d327b8`](https://github.com/polyai/adk/commit/3d327b858326ddb637e5fbc027269cfb937f172a))

## Summary

Fix two bugs in personality adjective handling that caused phantom diffs on pull and silent no-ops
  when removing adjectives.

## Motivation

1. Pulling a project could produce spurious diffs because the platform may return `{Friendly:
  false}` or `{}` for the same state — both mean "not enabled" but produced different YAML. 2.
  Removing an adjective from the local YAML and pushing had no effect because `build_update_proto`
  only sent adjectives present in the local dict, never signalling a removal.

## Changes

- `to_yaml_dict` now filters out disabled (`false`) adjectives so pull always writes the same YAML
  regardless of API representation - `build_update_proto` now iterates all `ALLOWED_ADJECTIVES`,
  defaulting missing ones to `false`, so removals are explicitly sent to the platform - Updated and
  added tests for both behaviors

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.2 (2026-07-09)

### Bug Fixes

- Use flow_id instead of flow_name as resource ID prefix for flow steps
  ([#220](https://github.com/polyai/adk/pull/220),
  [`e55fd24`](https://github.com/polyai/adk/commit/e55fd24e324eac32d64a92bfb045237e4336cadd))

## Summary

Flow step resource IDs now use the stable `flow_id` (FlowConfig's resource_id) as their prefix
  instead of the mutable `flow_name`, preventing step_id extraction failures when a flow is renamed
  with a casing change.

## Motivation

When a flow was renamed with only a casing change (e.g. "SMS Flow" → "sms flow"), `clean_name()`
  produced the same folder, so `find_new_kept_deleted` preserved the old resource_id. But
  `removeprefix(f"{flow_name}_")` used the new name against the old resource_id — the prefix didn't
  match, silently producing wrong step_ids.

## Changes

- Added `flow_id` field to `ResourceMapping` dataclass - Changed resource ID construction from
  `{flow_name}_{step_id}` to `{flow_id}_{step_id}` in `sync_client.py`, `project.py`, and `flows.py`
  - Updated all `removeprefix` calls (~8 sites) to strip `flow_id` prefix - Updated
  `FlowConfig.validate` to use `resource_id` for step lookup - Added migration in `run_migrations`
  to re-key existing status dict entries from old to new format - Updated test fixtures and added
  migration tests

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- Add CLI test commands (run, list, show) ([#222](https://github.com/polyai/adk/pull/222),
  [`44ea700`](https://github.com/polyai/adk/commit/44ea700aef035191664a3f0927127754c212c10a))

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Add Document resource type ([#223](https://github.com/polyai/adk/pull/223),
  [`629a554`](https://github.com/polyai/adk/commit/629a554f4c3f57c43d0e2ab68b0cc986e3a48781))

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
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Allow validating experimental config against custom schema
  ([#224](https://github.com/polyai/adk/pull/224),
  [`2a9acc2`](https://github.com/polyai/adk/commit/2a9acc26ecd4d30b86b2796042d6760bb55e2c30))

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


## v0.34.1 (2026-07-09)

### Bug Fixes

- Delete local resources when entire type is absent from incoming on pull
  ([#219](https://github.com/polyai/adk/pull/219),
  [`a3857b0`](https://github.com/polyai/adk/commit/a3857b033e1db9140a51f4dcf63e24d08b126b60))

## Summary

When pulling, resource types present locally but entirely absent from `incoming_resources` were
  silently kept on disk. This fixes that by deleting local files for absent types after the main
  pull loop.

## Motivation

If all resources of a given type (e.g. SMS templates) are deleted remotely,
  `_update_pulled_resources` only iterated types present in `incoming_resources` — so the local
  files for that type survived the pull.

## Changes

- Added cleanup loop in `_update_pulled_resources` for non-multi resource types absent from incoming
  - Added cleanup loop in `_update_multi_resource_yaml_resources` for multi-resource types absent
  from incoming, using `_sort_paths_for_reverse_deletion` and `save_to_cache=True` - Both loops skip
  `_not_loaded_resources` types to avoid spurious deletions

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.34.0 (2026-07-08)

### Features

- Allow validating experimental config against custom schema
  ([#217](https://github.com/polyai/adk/pull/217),
  [`d1033e2`](https://github.com/polyai/adk/commit/d1033e265ca8a37ee1826f5798bcd75a89d76913))

## Summary

Allow overriding the experimental config validation schema via the
  `ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH` environment variable, falling back to the bundled schema.

## Motivation

The bundled `experimental_config_schema.yaml` may not always match the schema expected by a given
  Agent Studio environment. This lets users point validation at a custom schema file without
  modifying the package.

## Changes

- Read `ADK_EXPERIMENTAL_CONFIG_SCHEMA_PATH` env var in `ExperimentalConfig.validate()`; fall back
  to the bundled schema when unset - Use a context manager (`with open(...)`) for the schema file
  handle

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.33.1 (2026-07-08)

### Bug Fixes

- Bump experimental config schema with Soniox ASR ([#218](https://github.com/polyai/adk/pull/218),
  [`bebbbfe`](https://github.com/polyai/adk/commit/bebbbfe5928ee6611f3f7ae6510c3a99d8b206c5))

## Summary

Adds `soniox` as a supported ASR provider in the experimental config schema.

## Motivation

The Soniox speech recognition provider (poly_core #43628) needs to be a valid option in the
  experimental config schema so projects using it pass validation. Agent Studio already accepts
  `soniox` in published configs, so the reverse-synced `experimental_config.json` currently fails
  ADK validation in agent-deployments CI (e.g. PolyAI-LDN/agent-deployments#8033) until the config
  is manually stripped.

## Changes

- Added `soniox` to the ASR provider enum list - Added `soniox: Soniox cloud speech recognition` to
  the provider description enum - Added `soniox: "stt-rt-v5"` to the model documentation

## Test strategy

- [x] Validated the real reverse-synced Corilus `experimental_config.json` (soniox language
  overrides) against the updated schema with `jsonschema.Draft202012Validator`; unknown providers
  are still rejected - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

Co-authored-by: Moaed Yahia <moaedpoly@gmail.com>


## v0.33.0 (2026-07-08)

### Features

- Add Document resource type ([#211](https://github.com/polyai/adk/pull/211),
  [`ebb646d`](https://github.com/polyai/adk/commit/ebb646d2ed50e12cad37ff877b24dd510cf01320))

## Summary

Adds support for Document resources — context files stored as Markdown in `context/` that provide
  background knowledge to the agent via Studio Assistant.

## Motivation

Documents are a new resource type on Agent Studio. This PR adds full ADK support: pull, push, diff,
  status, and discovery.

## Changes

- New `Document` resource class in `src/poly/resources/documents.py` - Register in
  `RESOURCE_NAME_TO_CLASS` and `__init__.py` - Read documents from projection in `SyncClientHandler`
  - Fix: use document path as resource ID (matches server) instead of generated UUID - Add `poly
  docs context` documentation page - Improve `poly docs` listing in `docs.md` to show actual command
  names - Add tests in `resources_test.py` and `project_test.py` - Add test fixture
  (`context/test_document.md` + JSON entry)

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.32.1 (2026-07-06)

### Bug Fixes

- Prevent shell injection from release body in Slack notification workflow
  ([#212](https://github.com/polyai/adk/pull/212),
  [`336f4ff`](https://github.com/polyai/adk/commit/336f4ff09f1a05349bccd165318d6b618be4cd81))

## Summary

Moves `${{ }}` GitHub Actions expressions out of inline bash `run:` blocks and into `env:` variables
  to prevent the release body from being interpreted as shell commands.

## Motivation

The v0.32.0 release triggered ~20 bash parse errors in the Slack notification workflow because the
  release body contained backticks, parentheses, and angle brackets that bash interpreted as command
  substitutions, subshells, and redirections.

## Changes

- Move `github.event.release.body`, `github.event.release.tag_name`,
  `github.event.release.html_url`, `inputs.tag`, and repo URL expressions into `env:` block
  variables - Reference them as `${ENV_VAR}` in the script instead of inline `${{ }}` interpolation

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Refactoring

- Split CLI into per-command-family modules ([#209](https://github.com/polyai/adk/pull/209),
  [`832d294`](https://github.com/polyai/adk/commit/832d29440c3936234880904d65d02ba8323a51a0))

## Summary

Splits the monolithic `cli.py` (~5,760 lines) into a `cli_commands/` package with one module per
  command family, each implementing a `BaseCommand` contract (`add_arguments` + `run`).

## Motivation

`cli.py` had grown to nearly 6K lines with ~60 command handlers in a single class, making it hard to
  navigate, review, and maintain. The split gives each command family its own file with clear
  boundaries.

## Changes

- **New `cli_commands/` package** with 12 modules: - `base.py` — `BaseCommand` ABC + `Parents`
  dataclass - `shared.py` — generic utilities (`load_project`, `read_project_config`,
  `compute_diff`, `parse_from_projection_json`, `format_gist_choice`) - `sync.py` — Pull, Push,
  Status, Revert, Diff, Format, Validate commands - `branch.py` — Branch
  list/create/switch/current/delete/merge + merge helpers - `deployments.py` — Deployments
  list/show/promote/rollback + nested AB-test commands - `project.py` — Project
  list/create/delete/duplicate, Init, Studio commands - `auth.py` — Start, Login commands -
  `chat.py` — Chat command + chat loop helpers - `conversations.py` — Conversations
  list/get/get-audio - `review.py` — Review create/list/delete (GitHub Gist) - `testing.py` — Test
  run/show/list - `utils.py` — Docs, Completion commands - **`cli.py` reduced to ~130 lines** —
  orchestrator with `COMMANDS` list, parser construction, and dispatch - **Tests updated** — all
  patch targets point at the actual command modules (~275 sites across 3 test files) -
  **De-duplicated** `_resolve_included_deployments` (was defined twice identically)

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

All 766 tests pass. `poly --help` shows all 20 commands with identical parser trees. Nested
  subcommands (`branch`, `deployments ab-test`, `project`, `review`, `test`) verified via `--help`.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## v0.32.0 (2026-07-03)

### Features

- Expose projection-to-projection diffing (diff_projections)
  ([#210](https://github.com/polyai/adk/pull/210),
  [`e174d95`](https://github.com/polyai/adk/commit/e174d9555acb7124a49518bdca88e63c84745d3e))

## Summary

Adds `diff_projections(before_projection, after_projection)` — semantic per-file diffing of two
  sourcerer projections with no API calls — by extracting the diff core of
  `diff_remote_named_versions` into a reusable `diff_resource_maps`.

## Motivation

The deployed adk_service (poly_core) is stateless: callers (Glot) fetch projections from sourcerer
  with their own session auth and post them in the request body. To give Glot a branch-vs-main
  `branch_diff` tool with the same semantic, pretty-rendered diffs as `poly diff --before main
  --after <branch>`, adk_service needs a `/diff` endpoint following the `/pull`/`/push` pattern
  (PolyAI-LDN/poly_core#43520) — which needs this projection-based entry point.

## Changes

- `Project.diff_resource_maps(before, after)` — the by-path map building, combined resource
  mappings, `to_pretty` rendering and per-file `get_diff` previously inlined in
  `diff_remote_named_versions`. - `Project.diff_projections(before_projection, after_projection)` —
  builds both resource maps via `SyncClientHandler.load_resources_from_projection` and delegates to
  `diff_resource_maps`. Empty projections are valid. - `diff_remote_named_versions` delegates to the
  extracted core; behavior unchanged (same fetch, same error handling, same no-differences logging).

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

New `DiffProjectionsTest` covers modified / added+deleted / identical / empty-projection cases. Also
  verified end-to-end: installed this branch into a local adk_service and curled the new `/diff`
  endpoint — correct unified diffs for modified + added resources.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

``` $ curl -s -X POST localhost:8199/diff -d '{"before_projection": …, "after_projection": …}' {
  "diffs": { "topics/opening_hours.yaml": "--- original\n+++ updated\n@@ -1,5 +1,5 @@\n name:
  Opening Hours\n ...\n-content: We open at 9am\n+content: We open at 8am\n ...",
  "topics/refunds.yaml": "--- original\n+++ updated\n@@ -0,0 +1,5 @@\n+name: Refunds\n+..." } } ```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Fable 5 <noreply@anthropic.com>


## v0.31.3 (2026-07-02)

### Bug Fixes

- Exclude deleted attributes from new variant create commands
  ([#205](https://github.com/polyai/adk/pull/205),
  [`7b965d3`](https://github.com/polyai/adk/commit/7b965d30e6ae43c201cf3d68b08b5e82c3eec8b6))

## Summary

When creating a new variant in the same push as deleting an attribute, the variant's create proto
  incorrectly included the deleted attribute ID with an empty value, causing the server to reject
  the batch.

## Motivation

`poly push` fails with `ZodValidationError: All attributes must have a value at "attributeValues"`
  when a variant is created in the same batch as an attribute deletion. The `variant_create_variant`
  command references the attribute being deleted because `attribute_ids` was populated from the full
  current state without filtering out deleted attributes.

## Changes

- Filter deleted attribute IDs from `attribute_ids` when building new variant create protos in
  `_clean_resources_before_push` - Add test covering the scenario

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly push`)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before fix: ``` ERROR:poly.handlers.sync_client:Failed to send commands: Error: {'name':
  'ZodValidationError', 'message': '[command 2: variantCreateVariant "Variant 1"
  (VARIANTS-ac00f938)] Validation error: All attributes must have a value at "attributeValues"',
  'details': [{'code': 'custom', 'message': 'All attributes must have a value', 'path':
  ['attributeValues']}]} ```

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.31.2 (2026-07-02)

### Bug Fixes

- Add missing X-Poly-Source header to send_command_batch
  ([#208](https://github.com/polyai/adk/pull/208),
  [`0e44d04`](https://github.com/polyai/adk/commit/0e44d04f777315d755e08b1a8be458b6603f5791))

## Summary - `send_command_batch` builds its own headers dict for the protobuf POST request but was
  missing the `X-Poly-Source: adk` header that every other request includes via the default session
  headers (line 60 of `sdk.py`). - Adds the missing header to the dict at `sdk.py:567`.

## Test plan - [x] Run `uv run pytest src/poly/tests/ -v` to confirm no regressions

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.31.1 (2026-07-02)

### Bug Fixes

- Allow clearing variant_id on test case update ([#207](https://github.com/polyai/adk/pull/207),
  [`d27cb34`](https://github.com/polyai/adk/commit/d27cb34441945e3efc9ba62520d01561dd783b7e))

## Summary

Send empty string instead of omitting `variant_id` in the `Update_TestCase` proto when the variant
  is removed, so the platform can detect the field is being cleared.

## Motivation

When a user removes a variant from a test case and pushes, the `variant_id` field was omitted from
  the protobuf update command (proto3 optional fields with `None` are not serialized). The platform
  therefore didn't know to clear the variant, leaving stale data.

## Changes

- Changed `variant_id=self.variant` to `variant_id=self.variant or ""` in
  `TestCase.build_update_proto()` so the field is always present in the serialized proto

> **Note:** This requires a corresponding platform-side change to accept empty string for
  `variantId` in the `updateTestCase` Zod validation. Without that, the platform will reject the
  command with a min-length validation error.

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before (variant_id absent from command): ``` update_test_case { id: "TEST_CASES-d1a4ef69"

name: "Greeting Test"

scenario: "Hello, what can you help me with?"

language: "en-US"

channel: "chat.polyai" } ```

After (variant_id explicitly set to empty): ``` update_test_case { id: "TEST_CASES-d1a4ef69"

variant_id: ""

### Continuous Integration

- Add Slack release notification workflow ([#206](https://github.com/polyai/adk/pull/206),
  [`1252967`](https://github.com/polyai/adk/commit/12529677502585bb1ff7d260a100b798ad55fb4c))

## Summary

Adds a GitHub Actions workflow that posts a formatted Slack notification on every ADK release, with
  a Claude-generated summary.

## Motivation

Automate release announcements so the team gets notified in Slack whenever a new version is
  published, without manual effort.

## Changes

- New workflow `.github/workflows/slack-release-notification.yaml` - Triggers on `release:
  published` (fired by existing semantic-release workflow) - Collects PRs between previous and
  current tag - Extracts feat title from conventional commit messages - Calls Claude (Sonnet) to
  generate a 2-3 sentence summary from the release body - Posts formatted Slack message with title,
  summary, PR list, and release link - Includes `workflow_dispatch` trigger for testing against
  existing tags

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

### To test

1. Add `SLACK_WEBHOOK_URL` secret pointing at a test channel 2. Run: `gh workflow run
  slack-release-notification.yaml -f tag=v0.31.0`

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.31.0 (2026-07-01)

### Features

- Add CLI test commands (run, list, show) ([#202](https://github.com/polyai/adk/pull/202),
  [`3c3e6ec`](https://github.com/polyai/adk/commit/3c3e6ec06b4ad6d150b29738d74d6a51303438ad))

## Summary

Adds a complete testing workflow to the CLI: trigger tests, watch results live, list past runs, and
  inspect failures — all without leaving the terminal.

## Motivation

Running tests previously required switching to Agent Studio to see results. This brings the full
  test lifecycle into the CLI: trigger, poll, list, and review results.

## Changes

- **`poly test run`**: trigger tests with live polling UI (every 5s), adaptive display (full table
  for ≤20 tests, compact rolling view for >20), `--dry-run` to preview, `--dont-poll` to trigger and
  exit, `--push` to push before running, `--files`/`--tag` for filtering (runs all tests by default)
  - **`poly test list`**: list past test runs with status, pass/fail/error counts, branch, and
  timestamps - **`poly test show <run_id>`**: inspect a completed test run with all results -
  **`poly test show <run_id> <test_case_id>`**: drill into a single test — assertions, function call
  failures, and conversation transcript - All commands support `--json` for machine-readable output
  - Handle all API statuses: `pending`, `in_progress`, `passed`, `failed`, `errored`, `timed_out` -
  Extract `resolve_tests()`, `get_test_run()`, `list_test_runs()`, and `trigger_tests()` on
  `AgentStudioProject` - Add `print_test_run_list`, `print_test_run_summary`, `print_test_detail`,
  and `poll_test_run_live` console helpers - Simplify `get_diffs()` and `revert_changes()`
  signatures — replace `all_files`/`files` with a single `file_paths` param (defaults to all)

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (12 pre-existing
  failures unrelated to this change) - [x] No breaking changes to the `poly` CLI interface (or
  migration path documented) - [x] Commit messages follow [conventional
  commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

### Running tests: With <20 tests (by tag) <img width="446" height="78" alt="Screenshot 2026-06-29
  at 17 48 21" src="https://github.com/user-attachments/assets/c3e71fa7-b6fa-4a94-b51c-27de07f14b49"
  /> With >20 tests (all tests) <img width="753" height="576" alt="Screenshot 2026-06-30 at 18 18
  54" src="https://github.com/user-attachments/assets/f2450674-1a68-4069-b6f9-a3823e740981" />

### View previous runs <img width="741" height="148" alt="Screenshot 2026-06-29 at 17 47 55"
  src="https://github.com/user-attachments/assets/811abffb-b876-4945-95e5-37bc70c7f3b7" />

### View test run <img width="786" height="360" alt="Screenshot 2026-06-29 at 17 47 50"
  src="https://github.com/user-attachments/assets/b79dbbb3-2abc-44b8-a30c-f7c96befc0ed" />

### View specific test in a run <img width="1268" height="310" alt="Screenshot 2026-06-29 at 17 47
  41" src="https://github.com/user-attachments/assets/a2449f03-5b10-4d8b-8f22-f97d7460b165" />

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.30.0 (2026-06-30)

### Features

- Add A/B test management to deployments CLI ([#203](https://github.com/polyai/adk/pull/203),
  [`08461c5`](https://github.com/polyai/adk/commit/08461c56901a962f7449c03bacd71822001f686c))

## Summary

Adds `poly deployments ab-test {start|list|active|update|end}` subcommands for managing A/B tests
  between live and pre-release deployments from the CLI.

## Motivation

A/B tests could previously only be managed through the Agent Studio UI. This adds full CLI support
  so operators can start, monitor, adjust, and end A/B tests from the terminal or scripts.

## Changes

- API client (`platform_api.py`, `interface.py`): 5 new endpoints — create, list, get active, update
  traffic, end test - Project model (`project.py`): convenience methods forwarding to the API layer
  - CLI parser (`cli.py`): `ab-test` sub-subparser under `deployments` with `start`, `list`,
  `active`, `update`, `end` - All flags (`--name`, `--variant`, `--traffic`) are optional
  interactively and required with `--json` - `start` prompts for name (defaulting to UI datetime
  format), pre-release variant picker, and traffic split - `start` validates the variant version
  differs from the current live version - `update` and `end` auto-resolve the active test (only one
  per project) - `end` promotes the variant to live if chosen as the winner - `end` shows
  human-readable deployment labels (hash + message) instead of raw UUIDs - Console display
  (`console.py`): `print_ab_tests` table and `print_ab_test_detail` panel with traffic splits,
  version hashes, and deployment names - Status derived from `ended_at` field (no `status` column in
  the backend model) - 57 new tests covering validation, interactive prompts, HTTP error mapping,
  promotion flow

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs


## v0.29.0 (2026-06-25)

### Features

- Update help info text and poly status ([#201](https://github.com/polyai/adk/pull/201),
  [`0877164`](https://github.com/polyai/adk/commit/0877164d66f2d157dd28dc4ebef6bbbe202ab0e2))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. --> Updates the info text to remind the user
  that they need to change directories to a project folder to continue. Also adds workspace and
  project names to display during the poly status command. ## Motivation

<!-- Why is this change needed? Link to an issue if applicable. -->

Closes #[DEVP-344](https://linear.app/poly-ai/issue/DEVP-344/update-help-text-and-poly-status)

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

- Updates help info text when no project configuration is found - Adds workspace and project names
  to display when "poly status" command is used

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs https://www.loom.com/share/749c074bb76649d6ae6b6fe45abdeb10 <!-- Optional:
  paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.28.1 (2026-06-23)

### Bug Fixes

- Bump experimental config schema with Raven ASR ([#200](https://github.com/polyai/adk/pull/200),
  [`7921f50`](https://github.com/polyai/adk/commit/7921f50c1bc0da430fb900702b80825311e2aec0))

## Summary

Adds `raven` as a supported ASR engine in the experimental config schema.

## Motivation

The Raven Omni speech recognition engine needs to be a valid option in the experimental config
  schema so projects using it pass validation.

## Changes

- Added `raven` to the ASR engine enum list - Added `raven: PolyAI Raven Omni speech recognition` to
  the engine description enum - Added `raven: "raven-omni"` to the model documentation

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.28.0 (2026-06-23)

### Features

- Open agent studio from cli ([#199](https://github.com/polyai/adk/pull/199),
  [`5ad2973`](https://github.com/polyai/adk/commit/5ad2973114767ab34c8826d54d9f4dfd0b0bb723))

## Summary

<!-- What does this PR do? Keep it to 1-3 sentences. --> Adds a new command in the cli "poly studio"
  to open agent studio in the web browser and takes the user to the specific workspace and project.
  ## Motivation

<!-- Why is this change needed? Link to an issue if applicable. --> To make it easier for users to
  access agent studio. Closes #<!-- issue number
  -->[DEVP-326](https://linear.app/poly-ai/issue/DEVP-326)

## Changes

<!-- Bullet list of the key changes. Focus on *what* changed, not *how*. -->

- added new command "poly studio" - created new function to build studio base url

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->
  https://www.loom.com/share/6804c76d2f554a97af38254167f91d10


## v0.27.0 (2026-06-22)

### Features

- Add Project management commands (list, duplicate, delete)
  ([#172](https://github.com/polyai/adk/pull/172),
  [`6974701`](https://github.com/polyai/adk/commit/6974701bab35fedd39c1b26e24a4e12966f983f2))

## Summary

Add `poly project list`, `poly project delete`, and `poly project duplicate` commands using the
  public Agents API endpoints.

## Motivation

The ADK only supported `poly project create`. Users had no way to list, delete, or duplicate
  projects from the CLI.

## Changes

- Add `list_agents`, `get_agents`, `delete_project`, `duplicate_project` to `PlatformAPIHandler` and
  `AgentStudioInterface`, hitting the public `/v1/agents/` endpoints - Handle HTTP 204 No Content in
  `make_request` (required by the DELETE endpoint) - Add `poly project list` — displays agents in a
  table with ID, name, last updated, and branch count - Add `poly project delete` — with `--force`
  flag and interactive confirmation (`auto_enter=False`) - Add `poly project duplicate` — prompts
  for new name and optional ID - All three commands support `--json` mode and interactive
  region/account/agent selection - Use the public `list-agents` endpoint for agent selection so that
  slug-form `agentId` values are passed to the public API (the internal `/adk/v1/` endpoint returns
  `PROJECT-xxx` IDs which the public endpoints don't accept) - Add `print_agents` table helper in
  `console.py` - Add 10 tests across `DeleteProjectTest` and `DuplicateProjectTest`

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly project list`, `poly project delete`,
  `poly project duplicate`) - [x] Tested against a live Agent Studio project - [ ] N/A (docs,
  config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (672 tests) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/)


## v0.26.0 (2026-06-19)

### Documentation

- Fix: Bump experimental config schema ([#198](https://github.com/polyai/adk/pull/198),
  [`eb716c8`](https://github.com/polyai/adk/commit/eb716c8a7e976e6575c94092ee2920ec71da6b3c))

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

### Features

- Send X-Poly-Source header on all API requests ([#196](https://github.com/polyai/adk/pull/196),
  [`e48e963`](https://github.com/polyai/adk/commit/e48e9639bfeb51c5bfa9383834a93fe1e346ba63))

## Summary

Adds the `X-Poly-Source: adk` header to all outbound API requests so the platform can identify
  traffic originating from the ADK CLI.

## Motivation

Enables the platform team to distinguish ADK-originated requests from other API consumers for
  analytics, debugging, and rate-limiting purposes.

## Changes

- Added `X-Poly-Source: adk` header to `PlatformAPIHandler.make_request` (API-key auth path) - Added
  `X-Poly-Source: adk` header to JWT-authenticated endpoints (`push_resource`, `push_function`,
  `publish_agent`) - Added `X-Poly-Source: adk` header to `get_conversation_logs` - Added
  `X-Poly-Source: adk` header to `SourcererSDK` request headers

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.25.11 (2026-06-19)

### Bug Fixes

- Strip strings at YamlResource base level to eliminate phantom diffs
  ([#195](https://github.com/polyai/adk/pull/195),
  [`57a0904`](https://github.com/polyai/adk/commit/57a09045cd1025afa82bcfe62f61b47428eade60))

## Summary

Eliminates phantom `|-` → `|` diffs that persist after `ad push` by stripping whitespace from all
  string values at the `YamlResource` base class level, matching the platform's Zod `.trim()`
  behavior.

## Motivation

After pushing, `ad diff` shows spurious changes like `content: |-` → `content: |` because the
  platform trims all string fields but local YAML files can retain trailing newlines. This causes
  false `is_modified()` hash mismatches and confusing diff output.

## Changes

- Add `_strip_strings()` recursive helper in `resource.py` and wire it into `YamlResource.raw`,
  `compute_hash`, and `to_pretty` - Remove redundant per-resource `.strip()` calls from
  `to_yaml_dict` in `flows.py` and `variant_attributes.py`

## Test strategy

- [x] Added/updated unit tests - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.10 (2026-06-17)

### Bug Fixes

- [docs] bottom-panel loop-backs across docs ([#193](https://github.com/polyai/adk/pull/193),
  [`0f56d55`](https://github.com/polyai/adk/commit/0f56d55369116d32ac04d3e91e7e3d66637404b1))

## Summary

- Replace backward-pointing "Related" / "Next steps" card links with forward-pointing ones across 6
  pages so every bottom panel guides readers deeper into the docs - Fix `examples/index.md` which
  listed no actual examples — now links to all 3 example pages - Fix `reference/branch_merge.md`
  which was a complete navigation dead-end (all 4 links backward)

## Pages changed

| Page | Problem | Fix | |------|---------|-----| | `get-started/what-is-the-adk` | 2 of 3 links
  loop back to `get-started` | Points forward to walkthrough, prerequisites, first-commands | |
  `get-started/prerequisites` | Only link goes back to `get-started` | Points forward to
  `first-commands` | | `tutorials/build-an-agent` | Links back to walkthrough video | Points forward
  to restaurant-booking tutorial + core concepts | | `examples/index` | No example links; 2 of 3
  links backward | Lists all 3 example pages | | `reference/tooling` | Both links backward | Points
  forward to agent_settings, flows, functions | | `reference/branch_merge` | All 4 links backward
  (dead end) | Points forward to tests, tooling + keeps multi-user cross-ref |

## Test plan

- [ ] Run `mkdocs serve` locally and verify bottom-panel "Previous/Next" navigation follows sidebar
  order - [ ] Click through all changed card links and confirm they resolve correctly - [ ] Verify
  no broken links introduced

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>

- Bump experimental config schema ([#194](https://github.com/polyai/adk/pull/194),
  [`2c2de51`](https://github.com/polyai/adk/commit/2c2de51ab638aca69ddbd1adc43d50c5ddfda23a))

## Summary Bump experimental schema to latest version

## Motivation

Keeps up to date

## Changes

- Add latests changes

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.25.9 (2026-06-17)

### Bug Fixes

- Add dataclass-aware YAML field type validation at parse time
  ([#192](https://github.com/polyai/adk/pull/192),
  [`c871f34`](https://github.com/polyai/adk/commit/c871f34fbc94ee284587d6efc35d96f9521e1d19))

## Summary

Adds automatic type validation for YAML resource fields at parse time, catching the colon-space
  footgun where unquoted strings silently parse as dicts.

## Motivation

YAML values with unquoted mid-sentence colons (e.g., `the outcome: either a time slot or...`)
  silently parse as dicts instead of strings. This causes opaque `TypeError: bad argument type for
  built-in operation` from protobuf C code at push time — with no hint about which field or file
  caused it. A confirmed case in `prompt_assertions` burned ~7 push attempts before the user found
  the cause.

Supersedes #191 — moves the detection from `project.py`'s generic error handler down to the YAML
  resource layer with field-level precision.

## Changes

- Add `check_yaml_field_types()` in `resource.py` using `dataclasses.fields()` +
  `typing.get_type_hints()` to introspect declared types and validate `str` / `list[str]` fields
  aren't dicts - Recurses into nested dataclass fields (catches e.g. `TestCaseAssertion.prompts`
  inside `TestCase`) - Hook into `YamlResource.read_local_resource` — all YAML resources get the
  check automatically - Hook into `FlowStep` and `Pronunciation` overriding `read_local_resource`
  methods - 6 unit tests covering str→dict, list[str]→dict, nested recursion, valid passthrough,
  Optional[str] None, and error message content

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Example error output for the confirmed bug (test case with unquoted colon in prompt assertion):

``` ValueError: Error reading resource test_booking at test_suite/test_booking.yaml:
  'assertions.prompts[1]' should be a string but got a dict. ```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.8 (2026-06-15)

### Bug Fixes

- **languages**: Correct update command field for default_language
  ([#190](https://github.com/polyai/adk/pull/190),
  [`ee9fceb`](https://github.com/polyai/adk/commit/ee9fcebf5698d9fd1f641e0d8ebe76dcaf8cf691))

## Summary

Fixes a bug where changing a project's `default_language` via `push` always returned `422 — Protocol
  message Command has no "update_languages_update_default_language" field`. `DefaultLanguage` now
  emits the correct `languages_update_default_language` Command field.

## Motivation

Tracking: https://linear.app/poly-ai/issue/ORCH-309

Surfaced from Glot eval runs (lead-qualification, restaurant-booking,
  multilingual-payment-reminder): authoring an agent in a primary language other than the template
  default (`en-GB`) sent every build into a `languages.yaml` rewrite loop, because the
  default-language update could never push. Adding a locale to `additional_languages` worked;
  changing the default did not.

Root cause: `DefaultLanguage.command_type` already returns the full Command field name
  `languages_update_default_language`, but the base `update_command_type` derives the field as
  `f"update_{command_type}"`, producing the nonexistent `update_languages_update_default_language`.
  `sync_client` then builds `Command(**{update_type: build_update_proto()})` with that bad name and
  the proto rejects it. The payload (`Languages_UpdateDefaultLanguage`) was always correct — only
  the field name was wrong. `AdditionalLanguage` already overrides `create_/delete_command_type` for
  the same reason; `DefaultLanguage` was missing the matching `update_command_type` override.

## Changes

- `DefaultLanguage`: override `update_command_type` to return `languages_update_default_language`
  (no `update_` prefix), mirroring `AdditionalLanguage`. - Add
  `test_update_command_type_is_a_real_command_field`: asserts the field name and constructs the
  `Command` the way `sync_client` does, so a future regression fails loudly.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

New test verified to **fail** without the fix (`update_languages_update_default_language !=
  languages_update_default_language`) and **pass** with it.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (683 passed) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/) (`fix:` → patch)

## Screenshots / Logs

Without the fix: ``` FAILED
  ...::DefaultLanguageTests::test_update_command_type_is_a_real_command_field AssertionError:
  'update_languages_update_default_language' != 'languages_update_default_language' ```

With the fix: ``` 683 passed, 22 warnings, 30 subtests passed in 9.28s ruff check . -> All checks
  passed! ```

Co-authored-by: Claude Opus 4.8 (1M context) <noreply@anthropic.com>


## v0.25.7 (2026-06-12)

### Bug Fixes

- Recursively copy integrations stubs into _gen/ ([#188](https://github.com/polyai/adk/pull/188),
  [`10bc608`](https://github.com/polyai/adk/commit/10bc608892406ccf94a23f8d544e7568c57cbef5))

## Summary

Fix `save_imports` to recursively copy subdirectories from `poly.types` into `_gen/`, so the
  `integrations/` stubs are included.

## Motivation

`save_imports` only iterated top-level `.py` files via `pkg.iterdir()`, skipping the `integrations/`
  subdirectory added in #187. This meant `conv.integrations` had no type hints in Agent Studio.

## Changes

- Add `_copy_types_tree` helper that recursively walks the types package and copies `.py` files
  (including `__init__.py`) into `_gen/` - Replace the flat iteration in `save_imports` with
  `_copy_types_tree`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (682/682) - [x] No
  breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages
  follow [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.6 (2026-06-12)

### Bug Fixes

- Use relative imports in type stubs and add integrations stubs
  ([#187](https://github.com/polyai/adk/pull/187),
  [`b365a46`](https://github.com/polyai/adk/commit/b365a46eac025e14ecc3e9fbdbca17bb30400cf5))

## Summary

Fix type stubs to use relative imports and add integrations stubs.

## Motivation

The stubs updated in #184 used absolute `runtime.` imports. When copied into `_gen/`, the rewriter
  regex didn't catch all forms, causing import errors. Also missing stubs for the integrations
  subpackage.

## Changes

- Replace `from runtime.X import` → `from .X import` in all stubs - Expand `import runtime.X as Y`
  into direct name imports (`from .X import A, B`) - Add integrations stubs: `Integration` base
  class, `Integrations` facade, `OpenTable`, `Tripleseat`

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.5 (2026-06-12)

### Bug Fixes

- Preserve unicode characters in JSON output ([#182](https://github.com/polyai/adk/pull/182),
  [`1b2c099`](https://github.com/polyai/adk/commit/1b2c0998706a89fb79d82d21bc45cc62dcd8f133))

## Summary

Prevents `json.dumps` from escaping Unicode characters (e.g. `'` → `’`) in experimental config and
  formatted JSON output.

## Motivation

When pulling agent configs containing Unicode characters like smart quotes (`'`), the JSON
  serializer escapes them to `\uXXXX` sequences. This makes config files harder to read and creates
  noisy diffs.

## Changes

- Set `ensure_ascii=False` in `ExperimentalConfig.raw` property - Set `ensure_ascii=False` in
  `format_json()` utility

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

```diff - "step_footer": "If the user asks a follow-up question while you are waiting for an answer,
  answer the user’s question first..." + "step_footer": "If the user asks a follow-up question while
  you are waiting for an answer, answer the user's question first..." ```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Chores

- Add sync script and update runtime type stubs ([#184](https://github.com/polyai/adk/pull/184),
  [`4a195ff`](https://github.com/polyai/adk/commit/4a195ff2902c761dd1def8182e3081ad4f7e4d62))

## Summary

Add a script to auto-generate type stubs from `genai_lambda_runtime/python/runtime` and update all
  stubs to match current source.

## Motivation

The type stubs in `src/poly/types/` were manually maintained and had drifted from the runtime
  source. These stubs are copied into `_gen/` during `poly pull` to provide IDE autocomplete in
  Agent Studio. This adds an automated sync script so stubs can be regenerated with a single
  command.

## Changes

- Add `scripts/sync_runtime_stubs.py` — extracts public API signatures from runtime source,
  synthesizes `__init__` for dataclasses, prunes unused imports, derives `__all__` lists, and
  handles `TYPE_CHECKING` imports - Update all 10 existing stubs to match current runtime source -
  Add 5 new stubs: `agentic_dial.py`, `emails.py`, `entity_validator.py`,
  `value_extraction_types.py`, `webchat.py` - New types: `WebchatInterface`, `ChatCallAction`,
  `AgenticDial`, `Destinations`, `OutgoingEmail`, `EntityValidationResult`, entity config types -
  New `Conversation` properties: `webchat`, `translations`, `provider_voice_id`, `integrations` -
  New `Conversation` methods: `goto_csat_flow`, `set_csat_*`, `send_content_template` - Updated
  `Utils.prompt_llm` model list with GPT-4.1/5 and Claude models

Usage: `python scripts/sync_runtime_stubs.py --runtime-path
  /path/to/genai_lambda_runtime/python/runtime`

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.4 (2026-06-12)

### Bug Fixes

- Add global DTMF config to experimental_config schema
  ([#185](https://github.com/polyai/adk/pull/185),
  [`6f09c50`](https://github.com/polyai/adk/commit/6f09c50c60690be484726c5ac0620c857d3f14ac))

## Summary

- Adds `dtmf.global` section to `experimental_config_schema.yaml`, syncing with
  [poly_core#42747](https://github.com/PolyAI-LDN/poly_core/pull/42747) - Global DTMF enables digit
  collection on every turn; step-level DTMF takes precedence when enabled - New properties:
  `is_enabled`, `max_digits`, `end_key`, `collect_while_agent_speaking`

**Jira:** [FDX-3768](https://poly-ai.atlassian.net/browse/FDX-3768)

## Test plan

- [x] Existing `ExperimentalConfigTests` pass (schema validation + invalid config)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Correct GitHub Issues link in README ([#181](https://github.com/polyai/adk/pull/181),
  [`ac93113`](https://github.com/polyai/adk/commit/ac93113d7c49e3711c3196b3cb00959b6b047d30))

## Summary - The GitHub Issues link in README.md pointed to `PolyAI-LDN/adk` which is inaccessible
  to public users - Updated to `PolyAI/adk` to match the actual public repository

## Test plan - [x] Verify the new link resolves to the correct repo

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

- Update README to remove Early Access information ([#151](https://github.com/polyai/adk/pull/151),
  [`d6c61a0`](https://github.com/polyai/adk/commit/d6c61a017943bcb70635126c33dfc539c153bd60))

Removed Early Access section and prerequisites from README. as they both they we're in early access
  and API key needs to be requested from PolyAI

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

Co-authored-by: Aaron Forinton <89849359+AaronForinton@users.noreply.github.com>

### Documentation

- Fix(experimental-config): add payload ([#183](https://github.com/polyai/adk/pull/183),
  [`8067d78`](https://github.com/polyai/adk/commit/8067d78eee7c3c497bf761cf967c7ca8bf922220))

## Summary

This is related to PR #171

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

- Test suite documentation ([#180](https://github.com/polyai/adk/pull/180),
  [`2b2f03a`](https://github.com/polyai/adk/commit/2b2f03ace0c646b34a04fbe5eeac14bb7f1fc5b9))

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>


## v0.25.3 (2026-06-09)

### Bug Fixes

- Persist new test case prompt_assertions and tags on push
  ([#177](https://github.com/polyai/adk/pull/177),
  [`6c0f5e1`](https://github.com/polyai/adk/commit/6c0f5e153a7569e209558f79977402d1ede652b4))

## Summary

A newly-created `TestCase` was pushed with its base fields only — its `prompt_assertions` and `tags`
  were silently dropped, so a `push` → `pull` round-trip lost them (the case came back with a
  `scenario` but no `prompt_assertions`).

## Motivation

Surfaced in Glot, which authors `test_suite/*.yaml` cases, pushes, then runs them: after the
  projection round-trip the cases came back assertion-less, so the runner skipped them. The cases
  only "stuck" on a *second* push, once the case already existed.

Root cause: `TestCase.get_new_updated_deleted_subresources` returns its assertions and tags in the
  **`updated`** bucket even for a brand-new case — they have no create proto and are only settable
  via `set_test_case_assertions` / `set_test_case_tags`. But
  `AgentStudioProject._get_updated_subresources` only forwarded the **`new`** bucket for
  newly-created resources, so the `set_test_case_assertions` / `set_test_case_tags` commands were
  never emitted. The case landed in the projection with no assertions; pull
  (`_read_test_cases_from_projection`) faithfully reconstructed an assertion-less case.

<!-- no tracking issue -->

## Changes

- `_get_updated_subresources`: for newly-created resources, forward the `updated` and `deleted`
  sub-resources too, not just `new`. Creates are already ordered before updates, so
  `Create_TestCase` is followed by `set_test_case_assertions` / `set_test_case_tags`. - This also
  fixes the same latent drop for a new `Function`'s non-default `latency_control`, which is bucketed
  identically. - Adds `GetUpdatedSubresourcesTest.test_new_test_case_emits_assertions_and_tags`
  asserting a brand-new `TestCase` emits its assertions/tags in the `updated` change-set.

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

> Couldn't run `pytest` locally (a `ruamel` namespace-package quirk in my env); the new test targets
  the exact buckets and CI exercises it.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes _(verified via CI — see
  note above)_ - [x] No breaking changes to the `poly` CLI interface (or migration path documented)
  - [x] Commit messages follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before: a freshly-authored `test_suite/<name>.yaml` round-trips (push→pull) with its `scenario` but
  **no `prompt_assertions`**. After: assertions and tags survive the round-trip.


## v0.25.2 (2026-06-09)

### Bug Fixes

- **experimental-config**: Add payload ([#171](https://github.com/polyai/adk/pull/171),
  [`3386677`](https://github.com/polyai/adk/commit/33866777adb80732640cf2260397dedd1f4bbff2))

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


## v0.25.1 (2026-06-09)

### Bug Fixes

- Simplify pronunciation position assignment ([#176](https://github.com/polyai/adk/pull/176),
  [`85a4ae6`](https://github.com/polyai/adk/commit/85a4ae68c4cbc41eb62971242c7958246322859d))

## Summary

Simplifies pronunciation position assignment by removing the workaround for unreliable API position
  data and using the iteration index directly.

## Motivation

The previous code had a `FIXME` noting a Sourcerer SDK bug where multiple entities could share
  position 0. The workaround logic (`position if position == index else index + 1`) was brittle and
  unnecessary — since API positions are unreliable, we should just use the order items are returned
  in.

## Changes

- Removed the `FIXME` comment and position workaround in `_read_pronunciations_from_projection` -
  Position is now set directly from the iteration `index`

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.25.0 (2026-06-08)

### Features

- Add Agent Studio test suite support ([#165](https://github.com/polyai/adk/pull/165),
  [`56e7eac`](https://github.com/polyai/adk/commit/56e7eac6778424699e65acf0843118c9d70512f8))

## Summary

Adds local ADK support for Agent Studio test cases, including YAML resources under `test_suite/`,
  protobuf sync commands, pull/push integration, documentation, and unit tests.

## Motivation

Agent Studio now supports simulated conversation tests with prompt and function-call assertions. The
  ADK needs to read, write, validate, and sync these resources locally so projects can manage tests
  alongside other agent configuration.

## Changes

- Add `TestCase`, `TestCaseAssertion`, `TestCaseTags`, and function-call assertion types in
  `src/poly/resources/test_suite.py` - Register test cases in project resource mapping and sync
  client projection parsing - Update protobuf bindings (including new `testing_pb2`) and command
  types for create/update/delete/assertions/tags - Add `tests.md` documentation and link it from the
  main docs index - Add unit tests in `resources_test.py` and project discovery coverage in
  `project_test.py` - Add sample test cases to the test project
  (`test_suite/greeting_flow_test.yaml`, `test_suite/webchat_smoke_test.yaml`) - Set `__test__ =
  False` on resource classes to avoid pytest collection warnings - Validate test case `language`
  against configured project languages (default + additional) - Validate function call assertion
  names against known global functions

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

```yaml name: Test Weather flow

scenario: Ask for the weather for berlin.

channel: voice

language: es-ES

tags: - weather prompt_assertions: - It gives the weather - It gives the weather for Berlin
  function_call_assertions: - name: get_weather arguments: - parameter_name: city expected_value:
  Berlin value_type: string ```


## v0.24.0 (2026-06-08)

### Features

- Webchat config validation and push support ([#173](https://github.com/polyai/adk/pull/173),
  [`93e52a0`](https://github.com/polyai/adk/commit/93e52a095c317f5326f55ad713877a5ab0dfe805))

## Summary

- Add all-or-nothing validation for webchat config resources (ChatGreeting, ChatSafetyFilters,
  ChatStylePrompt) - On push, new webchat configs enable the webchat channel and are sent as updates
  instead of creates - Add `queue_command` to SyncClientHandler and AgentStudioInterface for queuing
  individual commands

## Motivation

Previously, to enable webchat you had to do it manually on the platform — it couldn't be done
  through ADK. This change allows ADK to enable the webchat channel automatically when webchat
  configs are pushed, and validates that all three config types are present together.

## Changes

- `resource_utils.validate_webchat_siblings()` — validates all three webchat types are present when
  any one is - `ChatGreeting`, `ChatSafetyFilters`, `ChatStylePrompt` — override `validate()` to
  call sibling check - `SyncClientHandler.queue_command()` / `AgentStudioInterface.queue_command()`
  — queue a single command - `utils.create_command_webchat_channel_update_status()` — create
  enable/disable channel command - `project._clean_resources_before_push()` — move new webchat
  configs to pre-push updates and queue enable command

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.23.3 (2026-06-08)

### Bug Fixes

- Skip interactive project_id prompt when --output-json is set
  ([#175](https://github.com/polyai/adk/pull/175),
  [`d8f5eca`](https://github.com/polyai/adk/commit/d8f5eca2b66591dea405f76bb83c239f774f4446))

## Summary

Skip the interactive `project_id` prompt during `poly create` when `--json` is passed, since JSON
  output mode is non-interactive.

## Motivation

When using `poly create --json`, the CLI shouldn't prompt for interactive input — it should let the
  platform generate the project ID automatically.

## Changes

- Added `and not output_json` guard to the `project_id` prompt condition in `cli.py`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly create --json`) - [ ] Tested against
  a live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.23.2 (2026-06-08)

### Bug Fixes

- Restore_function_def_line collapsing body when header has inline comment
  ([#174](https://github.com/polyai/adk/pull/174),
  [`6bba9bc`](https://github.com/polyai/adk/commit/6bba9bc992ebe79213bece45b85087eb6e510154))

## Summary

Fix a bug where `restore_function_def_line` collapsed the function body and subsequent functions
  onto a single line when the function header contained an inline comment (e.g. `): # pragma: no
  cover`).

## Motivation

The end-of-header detection used `line.rstrip().endswith(":")`, which failed on lines like `): #
  pragma: no cover` — the colon is mid-line, not at the end. The loop overshot past the real header,
  collecting body lines and subsequent functions, then joined them all into one line.

## Changes

- Use a regex (`:\s*(#.*)?\s*$`) to detect the header-ending colon, ignoring trailing comments and
  whitespace - Strip trailing newlines from header lines before joining to avoid embedded `\n` in
  the joined string - Ensure two spaces before inline comments in `_format_def_line` (PEP 8) - Add
  tests for inline comment preservation and subsequent function integrity

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

**Before (broken):** ```python def card_utils(conv: Conversation, flow: Flow): # pragma: no cover —
  platform import stub """Stub...""" pass def get_card_keywords(card) -> set: ban = card.number[:6]
  ```

**After (fixed):** ```python def card_utils(conv: Conversation, flow: Flow): # pragma: no cover
  """Stub...""" pass

def get_card_keywords(card) -> set: ban = card.number[:6] ```

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- Feat: translations ([#170](https://github.com/polyai/adk/pull/170),
  [`57c7909`](https://github.com/polyai/adk/commit/57c7909bd4a22e2ffde0b98b6b0b342551d6e864))

## Summary

Relates to PR #152

## Motivation

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

---------

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>


## v0.23.1 (2026-06-03)

### Bug Fixes

- Default language mapping name + projection key for translations
  ([#169](https://github.com/polyai/adk/pull/169),
  [`15526b1`](https://github.com/polyai/adk/commit/15526b180e9846d7f59a7e44bf39c099d3e14ee1))

## Summary

Fixes two bugs that broke translation validation when the default language is changed locally.

## Motivation

Translation validation cross-references configured languages via ResourceMappings. When the default
  language was changed locally, the ResourceMapping still had the old language code (cached from
  pull), so translations appeared to be missing entries for the new language. Separately, the
  projection reader used the wrong key to extract the default language code from the API response.

## Changes

- Re-read default language name from disk for kept resources so the ResourceMapping reflects the
  current value - Fix projection key `defaultLanguage` → `defaultLanguageCode` in
  `SyncClientHandler._read_languages_from_projection`

## Test strategy

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes (662 tests) - [x] Manual
  CLI testing (`poly <command>`) - [x] Tested against a live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.23.0 (2026-05-29)

### Documentation

- Add poly conversations list/get/get-audio ([#167](https://github.com/polyai/adk/pull/167),
  [`4ac9f8b`](https://github.com/polyai/adk/commit/4ac9f8b9389670386d5b508835ba0c11c6069061))

## Summary

This relates to PR #161

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

- Allow disabled non-standard adjectives in personality settings
  ([#168](https://github.com/polyai/adk/pull/168),
  [`8982e41`](https://github.com/polyai/adk/commit/8982e41cbc6b4f1751f42ca96495b523147196da))

## Summary

This relates to PR #163

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

- Clarify poly start is self-serve only; document poly login for enterprise
  ([#166](https://github.com/polyai/adk/pull/166),
  [`69ac46c`](https://github.com/polyai/adk/commit/69ac46cf57e6adc47e950dffd8e4326a78a57626))

## Summary

Following Harry's flag in #agent-development-kit that the May 15 getting-started rewrite was
  misleading for enterprise users: \`poly start\` is hardcoded to \`region=\"studio\"\` and only
  works against the PLG cluster.

This PR splits the auth setup path:

- **Self-serve accounts** ([studio.poly.ai](https://studio.poly.ai)) — \`poly start\` (unchanged) -
  **Enterprise accounts** (\`us-1\`, \`euw-1\`, \`uk-1\`) — \`poly login --region <region>\` is the
  recommended browser-based path; manual API key export is the fallback

### Pages changed - **get-started.md** — Step 2 split into self-serve / enterprise; \`poly login\`
  documented as recommended enterprise path, manual export as fallback; "Already have an agent"
  example covers all three flows - **prerequisites.md** — enterprise bullet mentions \`poly login\`;
  checklist updated; fixed a stale anchor - **index.md** — landing-page snippet and recommended path
  mention \`poly login\` - **reference/cli.md** — added missing \`### poly start\` and \`### poly
  login\` entries (neither command was documented before)

## Test plan - [x] \`mkdocs build --strict\` — no warnings, all cross-page anchors resolve - [ ]
  Mintlify-side fix shipped in parallel

### Features

- Translations ([#152](https://github.com/polyai/adk/pull/152),
  [`49ffdb8`](https://github.com/polyai/adk/commit/49ffdb8b9a0c697d7858f9dbd28fd05161cfdcb1))

## Summary

Add Translations and Languages as new resource types, enabling pull/push/status/diff workflows for
  language configuration and translation strings.

## Motivation

Agent Studio projects need to manage language settings (default + additional languages) and
  translation strings locally. Previously these were not tracked by the CLI, so changes had to be
  made directly in the platform.

## Changes

- **New `Translation` resource** — `MultiResourceYamlResource` stored in `config/translations.yaml`,
  with create/update/delete proto support - **New `DefaultLanguage` and `AdditionalLanguage`
  resources** — two `MultiResourceYamlResource` subclasses sharing `agent_settings/languages.yaml`
  with a flat YAML structure (`default_language: en-GB`, `additional_languages: [fr-FR]`) -
  **`resource_key` ClassVar on `MultiResourceYamlResource`** — replaces hardcoded `"name"` in
  `_find_matching()`, fixing duplicate-on-pull bugs for resources that use a different YAML key
  (e.g. `KeyphraseBoosting` uses `"keyphrase"`) - **Cross-resource validation** — `DefaultLanguage`
  and `AdditionalLanguage` validate no duplicate language codes; `Translation.validate()` checks
  translations exist for all configured languages - **BCP 47 validation** on language codes via
  `langcodes` library - **Updated protos** — regenerated protobuf files - **Registered new resource
  types** in `RESOURCE_NAME_TO_CLASS`, `__init__.py`, and `sync_client.py` - **Removed
  `KeyphraseBoosting._find_matching` override** — now handled by `resource_key` -
  **`variant_attributes.py`** — `discover_resources` uses `resource_key` instead of hardcoded
  `"name"` for consistency

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->


## v0.22.2 (2026-05-28)

### Bug Fixes

- Defer API key lookup until first SourcererSDK HTTP request
  ([#164](https://github.com/polyai/adk/pull/164),
  [`a90be40`](https://github.com/polyai/adk/commit/a90be407bfcc0c88abfed460910d39c6deaaea84))

## Summary

Lazy-initialize the `SourcererSDK` HTTP session so `retrieve_api_key()` runs on the first API
  request, not during `__init__`.

## Motivation

Offline CLI workflows (`poly pull --from-projection`, `poly push --dry-run --output-json-commands`)
  still construct `SyncClientHandler` / `SourcererSDK` even when no HTTP calls are made. Resolving
  credentials in `__init__` caused those flows to fail when `POLY_ADK_KEY` was unset.

## Changes

- Add a lazy `session` property on `SourcererSDK` that builds the `requests.Session` and auth
  headers on first use - Remove eager session creation and `retrieve_api_key()` from
  `SourcererSDK.__init__`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

Manual checks:

- [x] `poly push --from-projection - < proj.json --json --dry-run --output-json-commands` works
  without `POLY_ADK_KEY` when `branch_id` is set in `project.yaml` - [x] `poly push` still
  authenticates and sends when API key is configured - [x] `poly pull` / branch operations still
  work with a valid API key

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass (pre-commit on commit) - [ ] `pytest` passes -
  [x] No breaking changes to the `poly` CLI interface (or migration path documented) - [x] Commit
  messages follow [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

N/A

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.22.1 (2026-05-27)

### Bug Fixes

- Allow disabled non-standard adjectives in personality settings
  ([#163](https://github.com/polyai/adk/pull/163),
  [`1976948`](https://github.com/polyai/adk/commit/19769489ce2d4296cd0e0450f3fc46c27d071a4f))

## Summary

Fixes personality validation to only reject *enabled* invalid adjectives, and filters out
  non-allowed adjectives from the update proto payload.

## Motivation

The platform can return adjectives not in the local allowed set (e.g. deprecated or new adjectives).
  Previously, having any such adjective in the local YAML — even disabled — would block pushes. Now
  disabled non-standard adjectives pass validation and are silently excluded from the update.

## Changes

- `validate()` now only raises on invalid adjectives that are enabled (`True`) -
  `build_update_proto()` filters the adjectives dict to only include allowed keys - Updated error
  message to clarify "Enabled adjectives" - Added tests for disabled invalid adjective validation
  and proto filtering

## Test plan

- [x] Added/updated unit tests (`SettingsPersonalityTests`) - [ ] Manual CLI testing (`poly
  <command>`) - [ ] Tested against a live Agent Studio project

Replicates https://github.com/PolyAI-LDN/local_agent_studio/pull/141

Made with [Cursor](https://cursor.com)

Co-authored-by: Cursor <cursoragent@cursor.com>


## v0.22.0 (2026-05-27)

### Features

- Add poly conversations list/get/get-audio ([#161](https://github.com/polyai/adk/pull/161),
  [`3806a19`](https://github.com/polyai/adk/commit/3806a1998686a6fb2c1cf5c20008d1d8c1034d29))

## Summary

Adds `poly conversations list`, `poly conversations get`, and `poly conversations get-audio`
  commands that use the public Conversations API to list, inspect, and download conversations

## Motivation

Enables users to browse and debug conversations directly from the CLI without needing to open Agent
  Studio in a browser.

Closes #DEVP-181

## Changes

- Added `CONVERSATIONS_URL`, `CONVERSATION_URL`, `CONVERSATION_AUDIO_URL` endpoint constants and
  three new static methods (`list_conversations`, `get_conversation`, `get_conversation_audio`) to
  `PlatformAPIHandler` - Added corresponding passthrough methods to `AgentStudioInterface` - Added
  `conversations` command group to the CLI parser with `list`, `get`, and `get-audio` subcommands -
  Added `print_conversations` (table view) and `print_conversation_detail` (detailed view with
  turns) to console output - Conversation IDs are rendered as clickable Agent Studio links (same
  pattern as `poly chat`) - `shortSummary` JSON string is parsed to extract only the heading -
  `get-audio` downloads WAV binary directly (bypasses `make_request` JSON parsing) - All three
  subcommands support `--json` for machine-readable output (except `get-audio`)

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

`poly conversations list` <img width="978" height="103" alt="Screenshot 2026-05-27 at 16 36 35"
  src="https://github.com/user-attachments/assets/f3a9aae2-fa66-488b-8d67-17ef8a5affac" />

`poly conversations get` <img width="971" height="399" alt="Screenshot 2026-05-27 at 16 37 06"
  src="https://github.com/user-attachments/assets/d76b7677-b27c-4f15-a14b-b04d099f2e65" />

`poly conversations get-audio` <img width="928" height="36" alt="Screenshot 2026-05-27 at 16 37 28"
  src="https://github.com/user-attachments/assets/6f729da0-4c2d-4902-9f69-2b0a9d7319cb" />

### Refactoring

- Replace email param threading with POLY_ADK_EMAIL env var
  ([#156](https://github.com/polyai/adk/pull/156),
  [`63312ef`](https://github.com/polyai/adk/commit/63312efa5824325b44ce9d66c4becd7c0edc6fe9))

## Summary

Replace the `email` parameter that was threaded through the entire call chain (CLI -> project ->
  interface -> sync_client -> SDK) with a single `ADK_COMMAND_USER_OVERRIDE` environment variable
  read once in `SourcererSDK.__init__`.

## Motivation

The email was being passed as a parameter through 5 layers of function calls just to set a header
  and metadata field. Using an env var simplifies the API, removes parameter plumbing, and ensures
  the email header is consistently included on all API requests (including merges, which previously
  didn't get it).

## Changes

- Read `ADK_COMMAND_USER_OVERRIDE` env var in `SourcererSDK.__init__`, set on session headers and
  `send_command_batch` headers - Use `self.email` as default `created_by` in `create_metadata()` -
  Remove `email` param from `queue_resources`, `send_queued_commands`, `send_command_batch`,
  `_stage_commands`, `push_project`, `sync_ids_with_sandbox` - Remove `--email` CLI flag from push
  command - Remove `email` param from `AgentStudioInterface.queue_resources` and `upload_resources`

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.21.1 (2026-05-21)

### Bug Fixes

- Add tab-completion for branch switch and misc CLI fixes
  ([#159](https://github.com/polyai/adk/pull/159),
  [`91c68bb`](https://github.com/polyai/adk/commit/91c68bb8d10c749d958bbd358c1541381102201f))

## Summary

Adds tab-completion support for `poly branch switch` and fixes related CLI issues.

## Motivation

Branch names weren't being tab-completed on the `switch` subcommand, making it harder to quickly
  switch branches. The `_branch_name_completer` was also a classmethod which caused issues with
  argcomplete's expected function signature.

## Changes

- Changed `_branch_name_completer` from `@classmethod` to `@staticmethod` (argcomplete expects a
  plain callable, not a bound method) - Attached `.completer` to the `branch_name` argument on
  `branch switch` for tab-completion - Made `review` subcommand `required=True` so it shows help
  instead of silently doing nothing

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.21.0 (2026-05-21)

### Chores

- Update experimental config schema ([#155](https://github.com/polyai/adk/pull/155),
  [`dd3717c`](https://github.com/polyai/adk/commit/dd3717c8642dafb8645461e96cb8002d2f906b37))

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

### Features

- Add poly login command for multi-region auth ([#158](https://github.com/polyai/adk/pull/158),
  [`d9b5cc5`](https://github.com/polyai/adk/commit/d9b5cc569b87f4255273142f67c6a6462700c0dd))

## Summary

Add a new `poly login` command that allows existing enterprise users to authenticate against any
  region, alongside the existing `poly start` flow for free-tier users.

## Motivation

Enterprise clients need to authenticate against their specific region (us-1, uk-1, euw-1) rather
  than the default studio region. Previously only `poly start` existed, which was hardcoded to the
  studio region.

## Changes

- Add `poly login` command with `--region` flag and interactive region selector - Extract
  `_authenticate_and_save_key` helper from `start` to share auth logic between `start` and `login` -
  Add `REGION_TO_AUTH_DETAILS` mapping in `Auth0Handler` with per-region base URLs and client IDs -
  Validate region in auth methods with clear error messages - `make_request` now takes `base_url`
  directly instead of resolving region internally - Hide dev/staging regions from interactive prompt
  (still accessible via `--region` flag) - Guard against `None` PAT from API response

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly login`) - [x] Tested against a live
  Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)


## v0.20.4 (2026-05-19)

### Performance Improvements

- Speed up read_local_resource by eliminating redundant YAML parsing
  ([#139](https://github.com/polyai/adk/pull/139),
  [`3cbc449`](https://github.com/polyai/adk/commit/3cbc44965db3300cafac0eb26370398f35a39e4f))

## Summary

Optimizes `read_local_resource` by eliminating redundant YAML parse/dump cycles and caching repeated
  `ast.parse` calls. Reduces `poly diff` / `poly status` / `poly push` time by ~15% across all
  projects.

## Motivation

Profiling `poly diff` on large projects revealed two bottlenecks in `read_local_resource`, which is
  called for every resource during diff, status, and push operations: - **YAML double-parse (67% of
  time):** `from_pretty` would load YAML → transform → dump back to string, then
  `read_local_resource` would immediately re-parse that string - **Redundant `ast.parse` (8% of
  time):** `_get_target_function` re-parsed the same Python source multiple times per Function
  resource

## Changes

- Add `from_pretty_dict` to base `YamlResource` as a standardized dict→dict transform hook (mirrors
  existing `to_pretty_dict`), wired into `read_local_resource` for a single-parse path - Override
  `from_pretty_dict` in FlowStep, FlowConfig, VariantAttribute, PhraseFilter for their name→ID
  transformations - Base `read_local_resource` now does: `read_from_file` → string regex →
  `load_yaml` → `from_pretty_dict` → `from_yaml_dict` (one YAML parse, zero dumps) - Subclasses that
  need YAML transforms in `from_pretty` (for `read_to_raw` callers) override it with: `load_yaml` →
  `from_pretty_dict` → `dump_yaml` - Add `@lru_cache` to `Function._get_target_function` to avoid
  redundant `ast.parse` calls - Simplify `Pronunciation.read_local_resource` to pass the dict
  directly instead of dump→re-parse - Simplify `Topic.read_local_resource` to use `super()` and
  validate after

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly diff`) - [x] Tested against a live
  Agent Studio project - [ ] N/A (docs, config, or trivial change)

All 608 existing tests pass. Profiled and benchmarked across 43 projects.

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Benchmarks

Benchmarked `poly diff` (no local changes) across 43 projects:

| Metric | Before | After | Change | |--------|--------|-------|--------| | **Total time (43
  projects)** | 27.56s | 23.55s | **-14.5%** | | Largest project | 4.38s | 3.06s | **-30%** |

Per-resource improvements (profiled on largest project):

| Metric | Before | After | Change | |--------|--------|-------|--------| | `load_yaml` calls | 954
  | 642 | -33% | | `dump_yaml` calls | 570 | 0 | -100% | | `ast.parse` calls | 1,896 | 805 | -58% |
  | Total function calls | 18.8M | 10.3M | -45% |

Savings scale with project size. Small projects (~0.2s) are dominated by import time; large projects
  (1s+) see 20-30% improvement.


## v0.20.3 (2026-05-19)

### Bug Fixes

- Use dynamic key for experimental config ([#154](https://github.com/polyai/adk/pull/154),
  [`e57a8ef`](https://github.com/polyai/adk/commit/e57a8efc00e2fb701db3c90f82d9ba209788daaf))

## Summary

Stop hardcoding `"default"` as the experimental config key — use the actual key from the projection
  dict instead.

## Motivation

Projects with a non-default experimental config identifier fail because
  `_read_experimental_config_from_projection` always looks up `"default"`. This dynamically reads
  the first config entry.

## Changes

- Read the first key-value pair from the experimental configs dict instead of hardcoding `"default"`
  - Use the actual config ID as both the dict key and `resource_id`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.20.2 (2026-05-18)

### Bug Fixes

- Correct merge_branch return type annotations in project.py
  ([#153](https://github.com/polyai/adk/pull/153),
  [`1ff1b59`](https://github.com/polyai/adk/commit/1ff1b59464bf1a3ace5fbbcfa8e174ff06803900))

## Summary

Fixes the return type annotation on `AgentStudioProject.merge_branch()` to match the actual return
  type from the handler layer.

## Motivation

The `project.py` method declared `list[str]` for the conflicts and errors return values, but the
  handlers (`interface.py`, `sync_client.py`) correctly return `list[dict[str, str]]`. This mismatch
  could mislead type checkers and developers.

## Changes

- Updated `merge_branch` return type from `tuple[bool, list[str], list[str]]` to `tuple[bool,
  list[dict[str, str]], list[dict[str, str]]]` - Updated docstring to match

## Test strategy

- [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.20.1 (2026-05-15)

### Bug Fixes

- Handle non-string merge conflict values ([#129](https://github.com/polyai/adk/pull/129),
  [`15c3902`](https://github.com/polyai/adk/commit/15c39027a77335f8890cea8ff06c079882b80398))

## Summary

Branch merge conflicts can contain non-string values (ints, bools, dicts, lists, None) from the
  platform's conflict resolver. Previously the CLI crashed or showed useless output for these types.

## Motivation

The conflict resolution UI called `merge_strings()` on all values regardless of type, crashing on
  dicts/ints/None. Merge values can also be empty or missing entirely, which caused similar
  failures. Non-string conflicts also showed a blank "Needs decision" panel with no values
  displayed.

## Changes

- Fix crash when merge values are empty or None - Gate `merge_strings()` behind a type check — only
  called when theirs/ours are strings; None/missing base falls back to empty string - Show
  non-string values inline in the conflict panel instead of hiding behind "Multiline or long values"
  - Add type-appropriate edit prompts: `confirm` for bools, validated text for ints/floats, JSON
  input for lists - Hide "Edit manually" for dict values (pick a side only) - Extract
  `prompt_typed_edit` and validators into `console.py` - Remove redundant fallback merge logic from
  the interactive handler

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="872" height="322" alt="Screenshot 2026-05-06 at 15 49 49"
  src="https://github.com/user-attachments/assets/0c651da5-dd41-4e07-92ea-57cc7f3cf5f4" />

<!-- Tested with numeric entity min/max conflicts on a live project -->

- Send empty parameters ([#144](https://github.com/polyai/adk/pull/144),
  [`5fe68e5`](https://github.com/polyai/adk/commit/5fe68e5e4ade1a0fed31e02f503fb3c9588e6e3c))

## Summary Send an empty list of parameters when no parameters

## Motivation Couldn't delete function parameters

## Changes - Send parameters for function types that accept it, even when empty

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

<!-- Optional: paste terminal output, screenshots, or before/after diffs if helpful. -->

### Chores

- Remove client ID of unused connections ([#149](https://github.com/polyai/adk/pull/149),
  [`fe0191b`](https://github.com/polyai/adk/commit/fe0191b5c62b99f6b1de3e56c4c9d13e8b5b760a))

## Summary Remove client ID and connection of unused Auth0 Connection

## Motivation Dead code which was confusing

## Changes Remove unused constants

## Test strategy

<!-- How did you verify this works? Check all that apply. -->

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

### Documentation

- Update getting started for poly start ([#147](https://github.com/polyai/adk/pull/147),
  [`86aa472`](https://github.com/polyai/adk/commit/86aa472c663bdf17d3741a784f8a5c8374192dee))

## Summary - Reworks the getting started flow to lead with `poly start` as the primary onboarding
  path — signup, API key generation, and project creation in one command - Manual API key setup via
  env vars kept as an alternative for existing users - Documents the credential file
  (`~/.poly/credentials.json`) and the resolution order (credential file → region env var →
  `POLY_ADK_KEY`) - Addresses Naorin's ask to update docs ahead of `poly start` going to prod

### Pages changed - **get-started.md** — Steps 1–5 (manual signup, find IDs, generate key) collapsed
  into a single `poly start` step - **prerequisites.md** — Option A (`poly start`) / Option B
  (manual) for API key setup, credential resolution order documented - **installation.md** — "Set
  your API key" points at `poly start`, credential file fallback noted

## Test plan - [x] `mkdocs serve` — all three pages render correctly - [ ] Internal links between
  pages resolve (prerequisites ↔ installation ↔ get-started) - [ ] Screenshot/image references still
  work (no images were changed) - [ ] Should be merged after or alongside Ruari's `poly start` PRs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>


## v0.20.0 (2026-05-15)

### Features

- Add `poly start` onboarding command ([#137](https://github.com/polyai/adk/pull/137),
  [`9c714cc`](https://github.com/polyai/adk/commit/9c714cc1db27b70475e8850b51d551521515da44))

## Summary

Adds a new `poly start` command that provides a guided onboarding flow: authenticate via Auth0
  device flow, set up an API key (PAT), and optionally create a first Agent Studio project — all in
  a single command.

## Motivation

New users currently need to manually create an account, obtain an API key, and configure their
  environment before they can use the ADK. `poly start` streamlines this into one interactive flow.

## Changes

- New `poly start` CLI subcommand with `--base-path` option - Auth0 device authorization flow via
  new `Auth0Handler` (`src/poly/handlers/auth0_handler.py`) - Jupiter API support in
  `PlatformAPIHandler` (new base URL map, JWT-based `authorise`, PAT CRUD) - Corresponding
  high-level methods in `AgentStudioInterface` - Welcome banner and branding in `console.py` - Added
  `studio` region default voice ID in `constants.py`

## Test strategy

- [ ] Added/updated unit tests - [x] Manual CLI testing (`poly start`) - [x] Tested against a live
  Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [ ] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs <img width="1824" height="534" alt="Screenshot 2026-05-12 at 18 42 05"
  src="https://github.com/user-attachments/assets/5482321d-a0cc-4e6a-8d58-3d2701e5f823" />


## v0.19.4 (2026-05-15)

### Bug Fixes

- Remove project_id prompt for Studio region ([#148](https://github.com/polyai/adk/pull/148),
  [`7fa88a2`](https://github.com/polyai/adk/commit/7fa88a2abb5d2705c2ed53237a9e3e36cceb9cf8))

## Summary

Removes the default project_id slug generation and skips the project_id prompt entirely for Studio
  (`--region studio`), since project_id must be unique across all projects in the region and
  prompting for it in PLG causes friction.

## Motivation

- `project_id` must be globally unique per region — if the user picks a taken ID, the API errors. We
  can't validate uniqueness client-side. - For PLG (Studio) we expect many projects, so defaulting
  to empty and letting the platform generate the ID avoids collisions. - The default slugified name
  was often not useful and led to conflicts.

## Changes

- Remove default slug generation from `project_name` for the `project_id` field - Skip the
  `project_id` interactive prompt when `--region studio` - Update help text to clarify the platform
  generates the ID if omitted - Fix `is not` → `!=` for string comparison (identity vs equality bug)

## Test strategy

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] N/A (docs, config,
  or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

### Documentation

- Add Discord community page ([#145](https://github.com/polyai/adk/pull/145),
  [`f924a6f`](https://github.com/polyai/adk/commit/f924a6f094dc54d16160984a4fc2782a2193b92b))

## Summary - Adds a new **Community > Discord** page to the ADK docs inviting users to join the
  Discord server (`https://discord.gg/nzGcCt6SE`). - Wires the page into the mkdocs nav between
  Examples and Legal.

## Test plan - [ ] `mkdocs serve` renders the new page correctly - [ ] Discord invite link resolves
  - [ ] Navigation shows the Community section in the right position

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>

- Discord page invisible button and broken icon ([#146](https://github.com/polyai/adk/pull/146),
  [`890fc78`](https://github.com/polyai/adk/commit/890fc78101c9384b6f5cbac3050466ccc3671f54))

## Summary - The `.md-button--primary` class used `--md-primary-fg-color` for its background, which
  resolves to `#fff` in the custom light theme — white button on white page. - The
  `:fontawesome-brands-discord:` inline icon syntax requires the `pymdownx.emoji` extension, which
  isn't enabled — rendered as literal text. - Replaced with a `.discord-btn` class in
  `components.css` using Discord's brand purple (`#5865F2`), and removed the icon reference.

## Test plan - [ ] `mkdocs serve` — button is visible in both light and dark mode - [ ] Button hover
  darkens to `#4752C4` - [ ] Discord invite link still works

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>


## v0.19.3 (2026-05-14)

### Bug Fixes

- Eliminate phantom diffs after poly pull --force ([#138](https://github.com/polyai/adk/pull/138),
  [`94597b4`](https://github.com/polyai/adk/commit/94597b447195c5bb1570fa05d7d9eac76b0df60c))

## Summary

Fixes two serialization bugs that caused `poly diff` to show spurious changes immediately after
  `poly pull --force`.

## Motivation

After a force pull, users expect `poly diff` to show no changes. Instead, it showed blank line
  removals in Python files and `|` → `|-` changes in YAML step prompts.

## Changes

- **function.py**: Preserve blank line between docstring and imports in `make_pretty` so the local
  file matches the remote `.raw` format - **flows.py**: Normalize prompt in `to_yaml_dict()` with
  `.strip()` so remote and local resources produce identical YAML output (both use `|-`) -
  **resources_test.py**: Update `test_to_pretty_import_after_docstring` expected value to include
  the preserved blank line

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Before: `poly pull --force && poly diff` showed 12 phantom diffs (blank line removals in .py files,
  `|` → `|-` in .yaml files). After: `poly pull --force && poly diff` should show no diffs.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

### Documentation

- Add `poly create` project command ([#140](https://github.com/polyai/adk/pull/140),
  [`7b837cb`](https://github.com/polyai/adk/commit/7b837cbab983d6861a76cd525fb5c4211fee66a0))

## Summary

This relates to PR #64

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

Co-authored-by: github-actions[bot] <github-actions[bot]@users.noreply.github.com>

- Deduplicate content and trim bloat across ADK docs
  ([#141](https://github.com/polyai/adk/pull/141),
  [`0ab1be6`](https://github.com/polyai/adk/commit/0ab1be6514460a76651070c3c24ded506168136d))

## Summary

**Deduplication (-340 lines net across 16 files):** - Consolidate API key generation instructions in
  prerequisites.md; other pages cross-reference - Consolidate platform-provisioned notes in
  agent_settings.md; voice/chat/speech pages cross-reference - Move safety filter YAML examples to
  safety_filters.md only - Move state/variable docs from functions.md to variables.md - Replace
  duplicated CLI workflow steps (5 files) with cross-references to cli.md#working-pattern - Shorten
  repeated poly init dropdown descriptions - Remove duplicated project directory tree from
  build-an-agent.md - Trim examples/index.md meta-content - Remove misplaced dev-setup-from-source
  from working-locally.md (already in CONTRIBUTING.md)

**Informational inconsistencies fixed:** - **index.md quickstart** now includes venv setup (was
  contradicting installation.md) - **build-an-agent.md Workflow 2 Step 3** no longer shows a
  separate `poly pull` after `poly init` (poly init pulls automatically) - **prerequisites.md** Git
  marked as optional/recommended, not required — the ADK itself doesn't use git -
  **agent_settings.md** rules reference table now includes `$variable_name` syntax alongside
  `{{vrbl:...}}` (was inconsistent with variables.md and topics.md)

Visual formatting (cards, grids, admonitions) preserved throughout.

## Files changed

| Area | Files | |---|---| | Get started | `index.md`, `get-started.md`, `prerequisites.md`,
  `installation.md` | | Reference | `agent_settings.md`, `voice_settings.md`, `chat_settings.md`,
  `speech_recognition.md`, `functions.md`, `testing.md`, `tooling.md` | | Concepts |
  `working-locally.md`, `multi-user-and-guardrails.md`, `anti-patterns.md` | | Tutorials |
  `build-an-agent.md` | | Examples | `index.md` |

## Test plan

- [ ] Run `mkdocs serve` and verify all cross-reference links resolve - [ ] Spot-check that each
  deduplicated section still has a working link to the canonical content - [ ] Confirm no broken
  anchors (e.g. `cli.md#working-pattern`, `prerequisites.md#generate-api-key`)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 <noreply@anthropic.com>

- Feat: add deployments show subcommand ([#134](https://github.com/polyai/adk/pull/134),
  [`ff15134`](https://github.com/polyai/adk/commit/ff15134b8772ec15f35c306ddbf9b08ee64bd10b))

## Summary

This work relates to PR #125

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


## v0.19.2 (2026-05-12)

### Bug Fixes

- Deepcopy FlowConfig before dummy start step swap ([#136](https://github.com/polyai/adk/pull/136),
  [`1824946`](https://github.com/polyai/adk/commit/18249460733980c29b4040215d2b329d63ec72f5))

## Summary

Prevents `_start_step_temp` suffix from leaking into local state after pushing flows with a
  FunctionStep as start step.

## Motivation

When creating a flow whose start step is a FunctionStep, `_clean_resources_before_push` creates a
  temporary dummy default step and mutates `flow_config.start_step` and `flow_config.steps`
  in-place. After push, `self.resources = new_state` saves this mutated config — persisting the
  `_start_step_temp` suffix into `flow_config.yaml`. Subsequent pushes then fail with "Old start
  step not found".

## Changes

- Use `copy.deepcopy(flow_config)` before the dummy step swap so the original FlowConfig stays clean
  - Only the copy gets the dummy step and temp start_step ID

## Test strategy

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] Manual CLI testing
  (`poly push --dry-run`) - [x] Tested against a live Agent Studio project

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface - [x] Commit messages follow conventional commits

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.19.1 (2026-05-12)

### Bug Fixes

- Normalize local resources during pull merge ([#135](https://github.com/polyai/adk/pull/135),
  [`baa5523`](https://github.com/polyai/adk/commit/baa5523d6b52cdb52d16d2e50201b1ae54b9294d))

## Summary

Fix `_update_pulled_resources` to properly normalize local Function resources before three-way
  merge, preventing `TypeError` from missing `known_parameters`.

## Motivation

The direct `resource_type.read_local_resource()` call in `_update_pulled_resources` bypassed the
  `read_local_resource` wrapper that supplies required kwargs like `known_parameters` for Functions.
  This caused a `TypeError` on push/pull when Function resources existed locally.

## Changes

- Extract `_make_resource_mapping` helper from `_make_resource_mappings` for single-resource use -
  Use `self.read_local_resource()` in `_update_pulled_resources` instead of calling the class method
  directly, so Function/FlowStep/FunctionStep resources get their required kwargs - Re-raise
  `FileNotFoundError` from `read_local_resource` so the existing `except FileNotFoundError` handler
  in `_update_pulled_resources` catches it (previously wrapped in `ValueError`) - Update pull merge
  test expectations to match the canonical `to_pretty` format (extra newline after header when
  content doesn't start with an import)

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly push`)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


## v0.19.0 (2026-05-12)

### Documentation

- Feat: add deployment promote and rollback commands
  ([#133](https://github.com/polyai/adk/pull/133),
  [`7f2df7a`](https://github.com/polyai/adk/commit/7f2df7afdd68fde6cf788571833400684a9f4076))

## Summary

This relates to PR #91

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

- Feat: support per-region API keys via POLY_ADK_KEY_{REGION}
  ([#130](https://github.com/polyai/adk/pull/130),
  [`2d4124b`](https://github.com/polyai/adk/commit/2d4124b7f69342524b8dfad9dbc99e2eafa60c1d))

## Summary

This relates to commit https://github.com/polyai/adk/commit/94cb27b607ffdabcea75896ffbcc01f0406b90c0

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

- Fix: format for multi-resource YAML files ([#131](https://github.com/polyai/adk/pull/131),
  [`482c439`](https://github.com/polyai/adk/commit/482c4396f68f0aaa33a62b1b62835cbd2f4f6bd6))

## Summary

These changes relate to PR #119

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

- Fix: key accounts/projects dicts by ID to prevent duplicate name collisions
  ([#132](https://github.com/polyai/adk/pull/132),
  [`d0e628e`](https://github.com/polyai/adk/commit/d0e628ed5e78e1383d02e1b7945def1d34d90134))

## Summary

This relates to work from commit
  https://github.com/polyai/adk/commit/b71b6a70aaa0939a437da5500f0727a5d6e86d0d

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

- Add `poly create project` command ([#64](https://github.com/polyai/adk/pull/64),
  [`b7276be`](https://github.com/polyai/adk/commit/b7276be1e09292ac19a048214854615253c6419a))

## Summary

Adds a new `poly create project` CLI command that creates a new Agent Studio project under an
  interactively selected account, then initializes it locally. Uses the Agents API (`POST
  /v1/accounts/{accountId}/agents`) for project creation.

<img width="805" height="169" alt="image"
  src="https://github.com/user-attachments/assets/5664b7b6-34fc-4154-9d80-7eafa232c117" /> <img
  width="1137" height="208" alt="image"
  src="https://github.com/user-attachments/assets/dfa70eac-9775-43cc-9127-a9aa4dfce33c" />

## Changes

- Add `create project` subparser with `--region`, `--account_id`, `--name`, `--json` flags - Add
  `AgentStudioCLI.create_project()` with interactive and non-interactive flows - After creation,
  automatically calls `init_project` to set up the local project - Add
  `PlatformAPIHandler.create_project()` — calls `POST /v1/agents` (Agents API) - Add
  `region_to_agents_api_url` mapping and `get_agents_api_url()` for the Agents API base URLs - Add
  `AgentStudioInterface.create_project()` wrapper - Remove dead `_retrieve_api_key()` method - Fix
  duplicate `get_deployments` definitions and indentation issues

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [x] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.18.0 (2026-05-08)

### Features

- Add deployments show subcommand ([#125](https://github.com/polyai/adk/pull/125),
  [`6cfd07d`](https://github.com/polyai/adk/commit/6cfd07d28c5e265a7a47511b7f5db98440781634))

## Summary

Adds `poly deployments show <hash>` subcommand to display detailed metadata for a specific
  deployment and the sandbox deployments included since the previous version in the given
  environment.

## Motivation

When reviewing deployment history, users need to drill into a specific version to see its full
  metadata (deployment ID, artifact version, lambda version, message, etc.) and understand which
  sandbox deployments were bundled into a promotion to pre-release or live.

## Changes

- Add `show` subparser under `deployments` with `hash` positional arg and `--env` flag
  (sandbox/pre-release/live) - Add `deployments_show()` and `_resolve_included_deployments()`
  methods to `AgentStudioCLI` - Add `print_deployment_show()` rich console output function - Add
  comprehensive tests covering error cases, JSON output, cross-env resolution, hash prefix matching,
  and rich output path

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs Default sandbox: <img width="856" height="171" alt="Screenshot 2026-05-01 at
  16 23 20" src="https://github.com/user-attachments/assets/9287f99c-087f-40b9-b556-aff2f78a1556" />
  Live push: <img width="1075" height="238" alt="Screenshot 2026-05-01 at 16 23 13"
  src="https://github.com/user-attachments/assets/68b4205c-c9e3-4767-82ac-a5e3da0d8277" />


## v0.17.0 (2026-05-08)

### Features

- Add deployment promote and rollback commands ([#91](https://github.com/polyai/adk/pull/91),
  [`f20556f`](https://github.com/polyai/adk/commit/f20556f0461901ece39cf231cfde5665928fd9e7))

## Summary

Adds `poly deployments promote` and `poly deployments rollback` subcommands, allowing users to
  promote a deployment to a target environment (pre-release or live) and rollback sandbox to a
  previous deployment version.

## Motivation

Enables deployment lifecycle management directly from the CLI, removing the need to use the Agent
  Studio UI for promotions and rollbacks.

## Changes

- Add `poly deployments promote --from <id> --to <env>` command with `--message`, `--force`, and
  `--dry-run` flags - Add `poly deployments rollback --to <id>` command with `--message` and
  `--force` flags - Add `_resolve_included_deployments` to compute included/reverted deployments
  using sandbox as the linear history source of truth - Promotions show "Included deployments" list,
  rollbacks show "Reverting deployments" list, first-time promotions are labelled as such - Add
  `promote_deployment` and `rollback_deployment` methods to `AgentStudioProject`,
  `AgentStudioInterface`, and `PlatformAPIHandler` - Refactor API URL constants: move `/adk/v1`
  prefix from base URLs into individual route constants - Add new `PROMOTE_URL` and `ROLLBACK_URL`
  endpoint constants using public API paths (`/v1/agents/...`) - Remove `headers` from debug log
  output

## Test strategy

- [x] Added/updated unit tests - [x] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [ ] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [ ] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

## Screenshots / Logs

Promote: <img width="812" height="253" alt="Screenshot 2026-05-01 at 17 11 25"
  src="https://github.com/user-attachments/assets/dd7e1c4a-76c5-45e3-aeb1-9fcfd9de0b69" />

Rollback: <img width="711" height="211" alt="Screenshot 2026-05-01 at 17 22 00"
  src="https://github.com/user-attachments/assets/20687a8d-8f3d-43b7-a674-e2ec292271cd" />


## v0.16.2 (2026-05-05)

### Bug Fixes

- Key accounts/projects dicts by ID to prevent duplicate name collisions
  ([#127](https://github.com/polyai/adk/pull/127),
  [`b71b6a7`](https://github.com/polyai/adk/commit/b71b6a70aaa0939a437da5500f0727a5d6e86d0d))

## Summary

Fix `get_accounts` and `get_projects` to key by ID instead of name, preventing silent data loss when
  accounts or projects share the same name. Also adds error handling when no accounts or projects
  are found.

## Motivation

When two accounts (or projects) had the same display name, the old `name → id` dict would silently
  overwrite one entry. This caused missing options during `poly init` interactive selection.
  Additionally, empty account/project lists would fall through to `questionary.select` with no
  choices, causing an unhelpful crash.

## Changes

- `PlatformAPIHandler.get_accounts` and `get_projects` now return `{id: name}` instead of `{name:
  id}` - `init_project` uses `questionary.Choice` objects to display `"name (id)"` while selecting
  by ID - Added early exit with clear error message when no accounts or projects are found -
  Simplified project name lookup to `projects.get(project_id)` - Updated docstrings in
  `interface.py` and `platform_api.py`

## Test strategy

- [x] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [ ] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---------

Co-authored-by: Claude Opus 4.6 (1M context) <noreply@anthropic.com>


## v0.16.1 (2026-05-01)

### Bug Fixes

- Pass ADK region directly to SourcererSDK for correct API key lookup
  ([#126](https://github.com/polyai/adk/pull/126),
  [`3441444`](https://github.com/polyai/adk/commit/3441444b84728f24702288d8a680850d92eab92e))

## Summary

Pass the ADK region directly to `SourcererSDK` instead of decomposing it into `(region,
  environment)` tuples, fixing incorrect API key lookup for dev/staging environments.

## Motivation

When using `POLY_ADK_KEY_DEV`, the dev environment incorrectly called `retrieve_api_key("us")` (the
  decomposed region) instead of `retrieve_api_key("dev")`, falling back to the generic
  `POLY_ADK_KEY` and ignoring the per-region key.

## Changes

- Removed `region_to_region_env` mapping from `SyncClientHandler` - `SourcererSDK` now takes the ADK
  region directly (`"dev"`, `"us-1"`, etc.) instead of separate `region`/`environment` params -
  `ENVIRONMENT_URLS` keys updated to use ADK region names (`"us-1"` instead of `"us-prod"`) -
  `retrieve_api_key()` now receives the correct region for all environments

## Test strategy

- [ ] Added/updated unit tests - [ ] Manual CLI testing (`poly <command>`) - [ ] Tested against a
  live Agent Studio project - [x] N/A (docs, config, or trivial change)

## Checklist

- [x] `ruff check .` and `ruff format --check .` pass - [x] `pytest` passes - [x] No breaking
  changes to the `poly` CLI interface (or migration path documented) - [x] Commit messages follow
  [conventional commits](https://www.conventionalcommits.org/)


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
