# Agent Development Kit (ADK) — Claude Code Configuration

## Project Overview

ADK (`polyai-adk`) is a Python CLI tool for managing PolyAI Agent Studio projects locally. It provides a Git-like workflow (`pull`, `push`, `status`, `diff`, `branch`, etc.) to sync voice agent configurations (functions, flows, entities, topics, agent settings) between the local filesystem and the Agent Studio Platform. Resources are stored as YAML and Python files.

## Tech Stack

- **Language**: Python 3.14+
- **Package manager**: `uv` (with `uv.lock`)
- **Build system**: setuptools via `pyproject.toml`
- **Linter/formatter**: ruff 0.14.2
- **Testing**: pytest with unittest.TestCase classes
- **Pre-commit**: ruff-check + ruff-format hooks

## Development Setup

Always activate the virtual environment before running Python, pytest, ruff, or the CLI:

```bash
source .venv/bin/activate
```

Install in editable mode (with dev dependencies):

```bash
uv pip install -e ".[dev]"
```

## Key Commands

| Task | Command |
|---|---|
| Run tests | `uv run pytest src/poly/tests/ -v` |
| Lint | `ruff check .` |
| Lint + fix | `ruff check . --fix` |
| Format | `ruff format .` |
| Format check | `ruff format --check .` |
| Install | `uv pip install -e ".[dev]"` |
| CLI help | `poly --help` |

## Project Structure

```
src/poly/                  # Main package
├── cli.py                 # CLI entrypoint (argparse)
├── project.py             # Core AgentStudioProject logic
├── console.py             # Rich-based output/display
├── constants.py           # Permissions, file name constants
├── utils.py
├── resources/             # Resource type implementations
│   ├── resource.py        # Base Resource/YamlResource classes
│   ├── resource_utils.py  # ruamel.yaml helpers
│   ├── flows.py, function.py, entities.py, topic.py
│   ├── agent_settings.py, handoff.py, sms.py
│   └── experimental_config.py, variant_attributes.py
├── handlers/              # API communication
│   ├── interface.py       # AgentStudioInterface (high-level)
│   ├── platform_api.py    # SyncClientHandler (low-level)
│   └── protobuf/          # Generated — DO NOT EDIT
├── types/                 # Generated — DO NOT EDIT
└── tests/
    ├── project_test.py, resources_test.py, utils_test.py
    ├── testing_utils.py
    └── test_projects/     # Fixture projects for tests
```

## Code Style Rules

- **Line length**: 100 characters
- **Type hints**: Required on all function parameters and return types
- **Docstrings**: Required on all classes and public methods
- **Imports**: Use absolute imports from the `poly` package
- **Naming**: PEP 8 conventions
- **Logging**: Use `logging.getLogger(__name__)`, never `print()`
- **Errors**: Use `ValueError` for validation (auto-formatted with file paths), `PlatformAPIError` for API failures
- **YAML**: Use `ruamel.yaml` via `resource_utils` — preserve comments and ordering

## Generated Files — Do Not Edit

- `src/poly/handlers/protobuf/` — generated protobuf files. Never edit directly.
- `src/poly/types/` — generated type definitions. Never edit directly.

Exclude both directories from linting and review.

## Version Bumping Policy

Version lives in `pyproject.toml`. An auto-tool bumps patch on every push to main. Only bump manually when needed:

- **Patch** (auto): Bug fixes, small non-breaking features
- **Minor** (manual): Changes to output format, CLI behavior, or feature additions
- **Major** (manual): Complete rework or breaking changes

## Git Conventions

- Use **conventional commits**: `feat:`, `fix:`, `refactor:`, `test:`, `chore:`, `docs:`
- PR template is at `.github/PULL_REQUEST_TEMPLATE.md` — always fill it in

## Adding a New Resource Type

1. Create resource class in `src/poly/resources/` inheriting `YamlResource` or `Resource`
2. Register in `RESOURCE_NAME_TO_CLASS` in `project.py`
3. Add `_read_<type>_from_projection` in `SyncClientHandler` + call from `_load_resources()`
4. Add tests in `src/poly/tests/resources_test.py`

## Testing Conventions

- Test files go in `src/poly/tests/`
- Use `unittest.TestCase` classes
- Test files mirror source structure (e.g., `resources_test.py` for resources)
- Use `test_projects/` fixtures for integration-style tests
- All tests must pass before opening a PR

## CI Pipeline

On every PR and push to `main`, CI runs:
1. `ruff check .` (lint)
2. `ruff format --check .` (format check)
3. `uv run pytest src/poly/tests/ -v` (tests)

## Subagents

Project subagents are defined in `.claude/agents/`. Delegate to them instead of doing their work inline.

| Agent | When to use |
|---|---|
| `ci-check` | Before pushing or opening a PR — validates lint, format, and tests pass |
| `pr-reviewer` | Before pushing a PR — self-review against the project checklist to catch issues early |
| `resource-scaffolder` | When adding a new resource type — scaffolds all required files and registrations |
| `test-writer` | After writing or changing code — writes readable tests and ensures coverage doesn't drop |

### Workflow

- After implementing a feature or fix, delegate to **test-writer** to add tests
- Before pushing a PR, always delegate to **pr-reviewer** to self-review against the project checklist
- Before pushing, delegate to **ci-check** to validate lint, format, and tests pass
- When adding a new resource type, delegate to **resource-scaffolder** instead of doing it manually

### Design Tokens

### Font Sizes
| Token | px | Usage |
|-------|----|-------|
| `header.extraLarge` | 40px | H1 page titles |
| `header.large` | 24px | H2 section titles |
| `header.medium` | 18px | H3 card titles |
| `header.regular` | 16px | H4 sub-headings |
| `header.small` | 12px | H5 labels, eyebrows |
| `body.regular` | 14px | Default body copy |
| `body.small` | 12px | Helper text, captions |

### Font Weights
| Token | Value |
|-------|-------|
| `light` | 200 |
| `normal` | 300 |
| `regular` | 400 |
| `medium` | 500 |
| `semibold` | 600 |
| `bold` | 700 |
