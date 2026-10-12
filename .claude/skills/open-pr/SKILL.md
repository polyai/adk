---
name: open-pr
description: Prepare and open a pull request on the polyai-adk repo, with checks run, the right conventional-commit title, the repo's PR template filled in and no internal references. Use when asked to open, create or raise a PR for ADK changes.
metadata:
  internal: true
---

# Open an ADK pull request

The PR title and description are public and become the release notes, so they matter as much
as the code.

## 1. Check the branch

- Work on a branch named `<type>/<short-description>`, never `main`.
- Run the `ci-check` skill and fix any failures.
- Run the `review-pr` skill on the local branch and fix any blocking findings.

## 2. Choose the title

Format: `<type>[(scope)][!]: <what changed, in plain words>`. Pick the type from what a user would
notice:

| The change | Type |
|---|---|
| Anything a user can see: new command or flag, changed output, new on-disk shape | `feat:` |
| A bug fix with no new surface | `fix:` |
| Faster, same behaviour | `perf:` |
| Breaks existing usage | add `!`, e.g. `feat!:` |
| Docs only | `docs:` |
| CI, tooling, refactors, tests, internal-only changes | `ci:`, `chore:`, `refactor:`, `test:` |

A user-visible change under a non-releasing type never ships a release, so when in doubt between
`feat` and something else, it's `feat`.

## 3. Write the description

- Read `.github/PULL_REQUEST_TEMPLATE.md` and fill in its sections only, without adding new ones.
  **Changes** covers the whole PR, and **Test strategy** says what was run and what was tried by
  hand.
- Remove before posting:
  - ticket IDs (Linear `ABC-123` style or any other tracker), from the title and body
  - real client or project names, account or project IDs
  - internal repos, services, tools, Slack channels, local paths

  Describe the problem generically instead.
- Don't mention version numbers. Releases are automatic.

## 4. Open it

- Show the title and description to the user and wait for their go-ahead.
- `gh pr create --draft --title "<title>" --body-file <file>`
- If there's a related ticket, post it separately: `gh pr comment <number> --body "<ticket link>"`.
- For stacked PRs, base each on the PR below it, and say in the description which PR to merge first.
