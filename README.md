![PolyAI](logo.png)

# Agent Development Kit (ADK)

[![PyPI version](https://img.shields.io/pypi/v/polyai-adk)](https://pypi.org/project/polyai-adk/)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Develop with Claude Code](https://img.shields.io/badge/Develop%20with-Claude%20Code-DC9E63?logo=claude)](https://claude.ai/download)

A CLI and Python package for managing [Agent Studio](https://studio.us.poly.ai) projects locally. It provides a Git-like workflow for synchronizing project configurations between your local filesystem and the Agent Studio platform.

**[Documentation](https://polyai.github.io/adk/)**

## Prerequisites

You must have access to a workspace in PolyAI Agent Studio before using this tool. Access and an API key are provided by your PolyAI contact. To request access to the PolyAI platform, reach out to [developers@poly-ai.com](mailto:developers@poly-ai.com).

## Installation

```bash
pip install polyai-adk
```

Once installed, use the `poly` command to manage your projects:

```bash
poly init       # Initialize a project (interactive)
poly pull       # Pull latest configuration
poly push       # Push local changes
poly status     # View project status
poly diff       # View local changes
poly branch     # Manage branches
poly format     # Format resources
poly validate   # Validate configuration
poly review     # Create a review gist
```

## Usage
![PolyAI](logo.png)

# Agent Development Kit (ADK)

[![PyPI version](https://img.shields.io/pypi/v/polyai-adk)](https://pypi.org/project/polyai-adk/)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Develop with Claude Code](https://img.shields.io/badge/Develop%20with-Claude%20Code-DC9E63?logo=claude)](https://claude.ai/download)

A CLI and Python package for managing [Agent Studio](https://studio.us.poly.ai) projects locally. It provides a Git-like workflow for synchronizing project configurations between your local filesystem and the Agent Studio platform.

**Documentation:** https://polyai.github.io/adk/

## Early Access

⚠️ **The PolyAI ADK is currently in Early Access.**

Changes may be pushed frequently while the platform evolves. If you encounter issues, please ensure you are running the **latest version** of the ADK before reporting them.

[Request access to the PolyAI ADK](https://fehky.share-eu1.hsforms.com/2oSGLpUctRvyqXcb6K44DAQ)

Once approved, the PolyAI team will provide the credentials required to use the ADK.

## Prerequisites

Before using the ADK you must:

- have access to a **PolyAI Agent Studio workspace**
- obtain an **ADK API key** from the PolyAI team

Access to both is granted through the Early Access Program.

Store your API key as an environment variable named: `POLY_ADK_KEY`

For example:

```bash
export POLY_ADK_KEY=<your-key>
```

Any standard method for setting environment variables on your system is acceptable.

## Usage

Install the ADK from PyPI:

```bash
pip install polyai-adk
```

Once installed, the `poly` CLI command becomes available.

```bash
poly init       # Initialize a project (interactive)
poly pull       # Pull latest configuration
poly push       # Push local changes
poly status     # View project status
poly diff       # View local changes
poly branch     # Manage branches
poly format     # Format resources
poly validate   # Validate configuration
poly review     # Create a review gist
```

Run:

```bash
poly --help
```

to see all available commands.

Each command also supports `--help` for detailed syntax:

```bash
poly push --help
```

## Commands

Run `poly --help` to see all available commands and options. Each command also supports `--help` for detailed syntax (e.g. `poly push --help`).

### `poly init`

Initialize a new Agent Studio project locally. Runs interactively by default, prompting for region, account, and project. You can also pass these directly:

```bash
poly init
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format   # format resources after init
```

### `poly pull`

Pull the latest project configuration from Agent Studio:

```bash
poly pull
poly pull --force     # overwrite all local changes
poly pull --format    # format resources after pulling
```

### `poly push`

Push local changes to Agent Studio:

```bash
poly push
poly push --dry-run          # preview what would be pushed
poly push --skip-validation  # skip local validation before pushing
poly push --force            # overwrite remote changes
poly push --format           # format resources before pushing
```

### `poly status`

View changed, new, and deleted files in your project:

```bash
poly status
```

### `poly diff`

Show diffs between your local project and the remote version:

```bash
poly diff              # all changes
poly diff file1.yaml   # specific files
```

### `poly revert`

Revert local changes:

```bash
poly revert --all                  # revert everything
poly revert file1.yaml file2.yaml  # revert specific files
```

### `poly branch`

Manage branches (default branch is `main`):

```bash
poly branch list
poly branch current
poly branch create my-feature
poly branch switch my-feature
poly branch switch my-feature --force  # discard uncommitted changes
```

### `poly format`

Format project resources (Python via ruff, YAML/JSON via in-process formatting). Use `--check` to only report files that would change; use `--ty` to also run type checking.

```bash
poly format              # all resources
poly format file1.py     # specific files
poly format --check      # check only, no writes
```

### `poly validate`

Validate project configuration locally:

```bash
poly validate
```

### `poly review`

Create a GitHub gist for reviewing changes, similar to a pull request:

```bash
poly review                                      # local vs remote
poly review --before main --after feature-branch  # compare branches
poly review --delete                              # delete all review gists
```

### `poly chat`

Start an interactive chat session with your agent:

```bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --metadata   # show functions, flows, and state each turn
```

## Bugs & Feature Requests

Please report bugs or request features via the [GitHub Issues](https://github.com/PolyAI-LDN/adk/issues) page.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and contribution guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
