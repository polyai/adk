![PolyAI](logo.png)

# Agent Development Kit (ADK)

[![PyPI version](https://img.shields.io/pypi/v/polyai-adk)](https://pypi.org/project/polyai-adk/)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue)](https://www.python.org/downloads/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Develop with Claude Code](https://img.shields.io/badge/Develop%20with-Claude%20Code-DC9E63?logo=claude)](https://claude.ai/download)

A CLI and Python package for managing [Agent Studio](https://studio.us.poly.ai) projects locally. It provides a Git-like workflow for synchronizing project configurations between your local filesystem and the Agent Studio platform.

**[Documentation](https://polyai.github.io/adk/)**

## Installation

```bash
pip install polyai-adk
```

Once installed, use the `poly` command to manage your projects:

```bash
poly start      # Create an account, access token and new project
poly init       # Initialize a project
poly project    # Manage poly projects
poly pull       # Pull latest configuration
poly push       # Push local changes
poly status     # View project status
poly diff       # View local changes
poly branch     # Manage branches
poly format     # Format resources
poly validate   # Validate configuration
poly review     # Create a review gist
poly deployments  # Manage deployments
poly docs       # Output reference documentation
```

## Usage

Install the ADK from PyPI:

```bash
pip install polyai-adk
```

Once installed, the `poly` CLI command becomes available.

```bash
poly init         # Initialize a project (interactive)
poly pull         # Pull latest configuration
poly push         # Push local changes
poly status       # View project status
poly diff         # View local changes
poly branch       # Manage branches
poly format       # Format resources
poly validate     # Validate configuration
poly review       # Create a review gist
poly deployments  # List deployment history
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

Show diffs between your local project and the remote version, or between two named versions:

```bash
poly diff                              # local vs remote (all changes)
poly diff --files file1.yaml           # specific files only
poly diff abc1234                      # version hash vs its predecessor
poly diff --before hash1 --after hash2 # compare two specific versions
```

### `poly revert`

Revert local changes:

```bash
poly revert                        # revert all changes
poly revert file1.yaml file2.yaml  # revert specific files
```

### `poly branch`

Manage branches (default branch is `main`):

```bash
poly branch list                       # active branches
poly branch list --archived            # soft-deleted branches
poly branch current
poly branch create my-feature
poly branch create my-hotfix --from my-feature  # branch from another branch instead of the current one
poly branch switch my-feature
poly branch switch my-feature --force  # discard uncommitted changes
poly branch rename my-feature-v2       # rename the current branch
poly branch merge 'Merge my-feature'   # merge into the parent branch
poly branch sync                       # pull the parent branch's changes in
poly branch history                    # merge history for the current branch
poly branch delete                     # soft-delete, restorable for 30 days
poly branch restore my-feature-id      # restore a soft-deleted branch
```

Projects using simplified deployments can also stage a branch:

```bash
poly branch tag                        # tag the current branch, deploying it to staging
poly branch untag                      # remove the tag
```

`poly branch sync`, `tag`, and `untag` are only available on projects with simplified deployments
enabled; they exit with an error otherwise.

### `poly format`

Format project resources (Python via ruff, YAML/JSON via in-process formatting). Use `--check` to only report files that would change; use `--ty` to also run type checking.

```bash
poly format                        # all resources
poly format --files file1.py       # specific files
poly format --check                # check only, no writes
```

### `poly validate`

Validate project configuration locally:

```bash
poly validate
```

### `poly review`

Create a GitHub gist for reviewing changes, similar to a pull request:

```bash
poly review create                                        # local vs remote
poly review create abc1234                                # version hash vs its predecessor
poly review create --before hash1 --after hash2           # compare two specific versions
poly review create --before main --after feature-branch   # compare branches
poly review list                                          # list existing review gists
poly review delete                                        # delete all review gists
```

### `poly deployments`

List deployment history for the project:

```bash
poly deployments                          # last 10 sandbox deployments
poly deployments --env live               # live environment
poly deployments --limit 20 --offset 10   # pagination
poly deployments --hash abc1234           # start from a specific version
poly deployments --details                # full metadata per deployment
```

### `poly chat`

Start an interactive chat session with your agent:

```bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --metadata   # show functions, flows, and state each turn

# Simulate one SIP header
poly chat --sip-header X-Customer-ID=12345
# Simulate multiple SIP headers
poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB
```

`--sip-header NAME=VALUE` is repeatable and simulates headers exposed to project
functions through `conv.sip_headers`. It does not create a SIP call or reproduce
carrier-level SIP behaviour.

### `poly sip-trunks`

Manage account-level SIP trunks and route dialled extensions to agents. The account and
region are inferred from project metadata unless `--account-id` and `--region` are supplied.

Place the declarative configuration in the account directory, alongside project folders:

```text
pod-point-uk/
├── sip-trunks.yaml
└── pod-ukp/
    └── project.yaml
```

For a new trunk, start with the fields you control. The trunk ID and hostname do not exist
until the API creates the trunk:

```yaml
- name: Primary carrier
  sip_cidr: [203.0.113.0/24]
  rtp_cidr: [198.51.100.0/24]
  encrypted: true
  inbound_auth:
    type: digest
    username: carrier-user
  extensions:
    - extension: "1000"
      agent_id: pod-ukp
      client_env: live
```

```bash
poly sip-trunks manage
poly sip-trunks manage --yes                    # apply without confirmation
poly sip-trunks manage --rotate-auth <trunk_id>
poly sip-trunks manage --file ../sip-trunks.yaml
poly sip-trunks list                         # display a summary table
poly sip-trunks list --output                # write account-level sip-trunks.yaml
poly sip-trunks list --output export.yaml
poly sip-trunks get <trunk_id>
poly sip-trunks delete <trunk_id>             # confirm before deleting
poly sip-trunks delete <trunk_id> --yes       # delete without prompting
```

`manage` creates or updates entries in the YAML and prints every managed trunk's generated
hostname when it changes. Before writing, it validates the complete file, displays a diff,
and asks for confirmation. Use `--yes` for trusted automation; `--json` also requires
`--yes` when changes exist. When everything already matches, it prints `Nothing changed.`
After a new trunk is created successfully, `manage` adds its generated `id` (the trunk ID)
and `hostname` to the same YAML entry. It also saves the digest `realm` returned by the API.
These fields are informational and ignored when constructing API writes. Formatting and
comments are preserved, while creation and update timestamps are intentionally omitted.
Entries omitted from the file are not deleted; use `delete` explicitly for trunks. When an
`extensions` list is present, it is authoritative: removing an entry schedules that
extension for deletion in the confirmation diff. Omitting the entire `extensions` key
leaves the trunk's extensions unmanaged. The older `sip_trunks:` wrapper remains readable
for migration.

`list` displays a table by default. With `--output`, it exports trunk IDs, hostnames,
CIDRs, authentication state, and extensions in the same schema consumed by `manage`.
Existing files are protected unless `--force` is used.
API responses never contain SIP passwords or tokens, so exported files do not contain
secrets. `inbound_auth.type` is `digest`, `token`, or `none`. `manage` securely prompts
when a secret is required to create a trunk or change its authentication. Normal updates
never resend existing credentials; use `--rotate-auth <trunk_id>` to rotate them explicitly.
`delete` asks for confirmation by default and prints a concise success message. Use `--yes`
to skip confirmation; deletion with `--json` requires `--yes`. Use `--json` for
machine-readable output.

The account region is not stored in `sip-trunks.yaml`. ADK reads it from the current
project or from project directories immediately below the account directory. If no project
metadata is available, pass `--region`; inconsistent project regions are rejected.

### `poly docs`

Output ADK documentation
```bash
poly docs
poly docs -all
poly docs {documentation (e.g topics)}
poly docs --output doc_file.md
```

## Bugs & Feature Requests

Please report bugs or request features via the [GitHub Issues](https://github.com/PolyAI/adk/issues) page.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and contribution guidelines.

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
