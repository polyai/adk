# CHANGELOG


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
