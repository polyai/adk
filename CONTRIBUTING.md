# Contributing to ADK

Contributions are welcome! Please ensure all tests pass before submitting a pull request.

## Development Setup

### Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) (`brew install uv`)

### Getting Started

```bash
git clone https://github.com/PolyAI/adk.git
cd adk
uv venv
uv pip install -e ".[dev]"
uv run pre-commit install
```

To try your changes with plain `poly` commands (e.g. `poly --help`), activate the environment
with `source .venv/bin/activate`. Otherwise prefix commands with `uv run` (`uv run poly --help`,
`uv run pytest`); scripts, CI and coding agents always use `uv run`.

## Running Tests

```bash
uv run pytest src/poly/tests/
```

Test files are located in `src/poly/tests/`.

## Project Structure and Rules

[`AGENTS.md`](AGENTS.md) describes where code goes (CLI → project → interface → API), the
conventions reviewers enforce, and what a PR needs to include. [`REVIEW.md`](REVIEW.md) is the
review checklist. Both apply whether you write the code yourself or with an AI coding agent.

## Code Style

The project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting, enforced via pre-commit hooks.

- **Line length**: 100 characters
- **Formatting**: `uv run ruff format .`
- **Linting**: `uv run ruff check .` (auto-fix with `uv run ruff check . --fix`)

## Pull Requests

PRs are squash-merged, so the PR title becomes the commit on `main`. It must follow
[conventional commits](https://www.conventionalcommits.org/), and its type decides the release:

| Title prefix | Release | Example |
|---|---|---|
| `fix:`, `perf:` | Patch (2.0.4 → 2.0.5) | `fix: handle missing config file` |
| `feat:` | Minor (2.0.4 → 2.1.0) | `feat: add poly export command` |
| `feat!:` / `BREAKING CHANGE:` | Major (2.0.4 → 3.0.0) | `feat!: redesign resource schema` |
| `chore:`, `docs:`, `ci:`, `build:`, `refactor:`, `style:`, `test:` | No release | `docs: update README` |

Use `feat:` for anything a user can see, including changes to command output or to files written
to disk. A user-facing change under a non-releasing type won't be released.

- Fill in the [PR template](.github/PULL_REQUEST_TEMPLATE.md).
- PR titles and descriptions are public and become release notes. Don't include ticket IDs,
  internal client or project names, or internal tools. Link a ticket in a PR comment instead.
- Merge stacked PRs bottom-up, retargeting each to `main` after the one below it merges.
- Once your PR is approved and CI is green, merge it yourself if you have write access, or ask
  the reviewer to.

### Updating dependencies

When you add or change dependencies:

- **License check** — CI allows only MIT, Apache, BSD, MPL. Run locally: `uv run licensecheck --zero`. Packages with missing PyPI license metadata are in `[tool.licensecheck]` `ignore_packages` in `pyproject.toml`; add new ones there after verifying the license.
- **Attribution** — Regenerate `licenses.json` with `uv run pip-licenses` and commit it. CI checks that it’s up to date.

## Releases

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) to automate versioning and publishing. Version bumps are determined from conventional commit messages (see above).

When a commit is merged to `main`, the release workflow automatically:

1. Determines the next version from commit history
2. Updates the version in `pyproject.toml` and in every `skills/*/SKILL.md`
3. Writes `CHANGELOG.md`
4. Creates a git tag and GitHub Release and publishes to PyPI

Don't edit any of these by hand. Adding a new user skill under `skills/` means adding it to
`version_variables` in `pyproject.toml`.

## Tooling

The repo works with any coding agent. The rules live in `AGENTS.md` (repo-wide, with more
specific ones in `src/poly/resources/`, `src/poly/cli_commands/` and the docs reference folders),
which both GitHub Copilot and Claude Code read. Keep Claude Code up to date: older versions
don't read `AGENTS.md`. The repo deliberately has no `CLAUDE.md`, so add rules to `AGENTS.md`.

Shared contributor skills live in `.claude/skills/`: `ci-check`, `review-pr`, `write-tests`,
`add-resource-type` and `open-pr`. Both tools load skills from there. `.claude/settings.json`
holds Claude Code permissions.
