# Contributing to ADK

Contributions are welcome! Please ensure all tests pass before submitting a pull request.

## Development Setup

### Prerequisites

- Python 3.14 or higher
- [uv](https://github.com/astral-sh/uv) (`brew install uv`)

### Getting Started

```bash
git clone https://github.com/PolyAI-LDN/adk.git
cd adk
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
pre-commit install
```

## Running Tests

```bash
pytest
```

Test files are located in `src/poly/tests/`.

## Project Structure

- `src/poly/cli.py` - CLI interface
- `src/poly/project.py` - Core project management
- `src/poly/resources/` - Resource type implementations
- `src/poly/handlers/` - API handler implementations
- `src/poly/tests/` - Test suite
- `src/poly/types/` - Python type definitions for the Agent Studio runtime

## Code Style

The project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting, enforced via pre-commit hooks.

- **Line length**: 100 characters
- **Formatting**: `ruff format .`
- **Linting**: `ruff check .` (auto-fix with `ruff check . --fix`)

## Commit Conventions

We use [conventional commits](https://www.conventionalcommits.org/):

| Commit prefix | Version bump | Example |
|---|---|---|
| `fix:` | Patch (2.0.4 → 2.0.5) | `fix: handle missing config file` |
| `feat:` | Minor (2.0.4 → 2.1.0) | `feat: add poly export command` |
| `feat!:` / `BREAKING CHANGE:` | Major (2.0.4 → 3.0.0) | `feat!: redesign resource schema` |
| `chore:`, `docs:`, `ci:` | No release | `docs: update README` |

### Updating dependencies

When you add or change dependencies:

- **License check** — CI allows only MIT, Apache, BSD, MPL. Run locally: `uv run licensecheck --zero`. Packages with missing PyPI license metadata are in `[tool.licensecheck]` `ignore_packages` in `pyproject.toml`; add new ones there after verifying the license.
- **Attribution** — Regenerate `licenses.json` with `uv run pip-licenses` and commit it. CI checks that it’s up to date.

## Releases

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) to automate versioning and publishing. Version bumps are determined from conventional commit messages (see above).

When a commit is merged to `main`, the release workflow automatically:

1. Determines the next version from commit history
2. Updates the version in `pyproject.toml`
3. Creates a git tag and GitHub Release

## Tooling

We recommend using [Claude Code](https://claude.ai/download) for development. The repo includes a `.claude/` directory with project-specific instructions and permissions pre-configured.
