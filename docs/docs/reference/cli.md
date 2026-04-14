---
title: CLI reference
description: Reference for the core commands provided by the PolyAI ADK CLI.
---

<p class="lead">
The PolyAI ADK is accessed through the <code>poly</code> command.
Use the CLI help output as the first source of truth.
</p>

## Start with help

To see all available commands and options:

~~~bash
poly --help
~~~

Each command also supports its own help output. For example:

~~~bash
poly push --help
~~~

!!! tip "Use help output as the source of truth"

    The installed CLI is the fastest way to confirm the commands and flags available in your local environment.

## Core commands

### `poly init`

Initialize a new Agent Studio project locally.

Examples:

~~~bash
poly init
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format
~~~

### `poly pull`

Pull the latest project configuration from Agent Studio.

Examples:

~~~bash
poly pull
poly pull --force
poly pull --format
~~~

If the branch you are currently on no longer exists in Agent Studio, `poly pull` automatically switches to the `main` branch and displays a warning message with the new branch name.

When using JSON output (`--json`), the response includes `new_branch_name` and `new_branch_id` fields if a branch switch occurred.

### `poly push`

Push local changes to Agent Studio.

Examples:

~~~bash
poly push
poly push --dry-run
poly push --skip-validation
poly push --force
poly push --format
~~~

When pushing creates a new branch (for example, when pushing to Agent Studio for the first time on a branch), the CLI displays a message with the new branch name.

When using JSON output (`--json`), the response includes `new_branch_name` and `new_branch_id` fields if a new branch was created.

### `poly status`

View changed, new, and deleted files in your project.

~~~bash
poly status
~~~

### `poly diff`

Show differences between the local project and the remote version.

Examples:

~~~bash
poly diff
poly diff file1.yaml
~~~

### `poly revert`

Revert local changes.

Examples:

~~~bash
poly revert --all
poly revert file1.yaml file2.yaml
~~~

### `poly branch`

Manage project branches.

Examples:

~~~bash
poly branch list
poly branch current
poly branch create my-feature
poly branch create my-hotfix --env live
poly branch create my-hotfix --env live --force
poly branch switch my-feature
poly branch switch my-feature --force
poly branch delete
poly branch delete my-feature
~~~

#### `poly branch delete`

Interactively select and delete one or more branches. The `main` branch cannot be deleted.

- Run without arguments to open an interactive checkbox prompt for selecting branches to delete.
- Pass a branch name directly to skip the interactive prompt and delete that branch after confirmation.

~~~bash
poly branch delete
poly branch delete my-feature
~~~

#### `poly branch create`

Creates a new branch. By default the branch is sourced from sandbox main.

| Flag | Description |
|---|---|
| `--env`, `--environment` | Source the new branch from a deployment snapshot instead of sandbox main. Choices: `sandbox`, `pre-release`, `live`. |
| `--force`, `-f` | Force branch creation even if there are uncommitted local changes on main. |

When `--env live` or `--env pre-release` is specified:

- the version of the deployed environment is pulled into your local workspace
- a branch is created from that snapshot
- the version is immediately pushed to the new branch, leaving a clean slate for hotfix changes
- the command can only be run from `main`
- if there are local changes, the command will fail unless `--force` is also passed

!!! warning "Use `--env live` with caution"

    Branching from a live deployment snapshot will overwrite your local project with the live state. Merging this branch back to main may roll back changes that were introduced after the snapshot was taken.

### `poly format`

Format project resources.

Examples:

~~~bash
poly format
poly format file1.py
~~~

### `poly validate`

Validate project configuration locally.

~~~bash
poly validate
~~~

### `poly review`

Create a GitHub Gist of Agent Studio project changes to share with others.

Running `poly review` without a subcommand creates a new gist comparing local changes against the remote project. Use `--before` and `--after` to compare two remote branches or versions.

Examples:

~~~bash
poly review
poly review --before main --after feature-branch
~~~

#### `poly review list`

Interactively select a review gist and open it in the browser.

~~~bash
poly review list
poly review list --json
~~~
<<<<<<< docs/auto-update-e9dd3b9

#### `poly review delete`

Interactively select and delete review gists. Use `--id` to delete a specific gist directly without an interactive prompt.

~~~bash
poly review delete
poly review delete --id GIST_ID
poly review delete --json
~~~

### `poly chat`

=======

#### `poly review delete`

Interactively select and delete review gists. Use `--id` to delete a specific gist directly without an interactive prompt.

~~~bash
poly review delete
poly review delete --id GIST_ID
poly review delete --json
~~~

### `poly chat`

>>>>>>> main
Start an interactive chat session with your agent.

Examples:

~~~bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --metadata
~~~

### `poly docs`

Output resource documentation.

Examples:

~~~bash
poly docs flows functions topics
poly docs --all
poly docs --all --output rules.md
~~~

Use `--output` to write the documentation to a local file. This is useful when working with AI coding tools — pass the output file as context to give the agent accurate knowledge of ADK resource types and conventions.

## Machine-readable JSON output

All core subcommands accept a `--json` flag that switches stdout to a single JSON object. This is designed for scripting, CI pipelines, and any integration that needs stable, parseable output rather than human-readable console text.

~~~bash
poly status --json
poly push --json
poly pull --json
poly validate --json
poly diff --json
poly revert --json --all
poly branch list --json
poly branch create my-feature --json
poly branch switch my-feature --json
poly branch current --json
poly branch delete --json
poly branch delete my-feature --json
poly format --json
poly init --region us-1 --account_id 123 --project_id my_project --json
~~~

When `--json` is used:

- stdout contains exactly one JSON object
- the process exits with code `0` on success and non-zero on failure
- human-readable console messages are suppressed

### JSON output shapes

The exact fields vary by command. Common fields include:

| Command | Key fields |
|---|---|
| `poly status --json` | `files_with_conflicts`, `modified_files`, `new_files`, `deleted_files` |
| `poly push --json` | `success`, `message`, `dry_run` |
| `poly pull --json` | `success`, `files_with_conflicts` |
| `poly validate --json` | `valid`, `errors` |
| `poly diff --json` | `diffs` |
| `poly revert --json` | `success`, `files_reverted` |
| `poly branch list --json` | `current_branch`, `branches` |
| `poly branch create --json` | `success`, `new_branch_id`, `branch_name` |
| `poly branch switch --json` | `success`, `switched_to`, `dry_run` |
| `poly branch current --json` | `current_branch` |
| `poly branch delete --json` | `success`, `deleted` |
| `poly format --json` | `success`, `check_only`, `format_errors`, `affected`, `ty_ran`, `ty_returncode`, `ty_timed_out` |
| `poly init --json` | `success`, `root_path` |

For `poly branch delete --json`, when a branch that was the current branch is deleted, the response also includes `"switched_to": "main"`.

Error responses always include `{ "success": false, "error": "...", "traceback": "..." }`.

!!! info "`init` with `--json` requires explicit flags"

    When using `poly init --json`, you must supply `--region`, `--account_id`, and `--project_id` explicitly. Interactive prompts are not supported in JSON mode.

### `poly push --output-json-commands`

Adds a `commands` array to the JSON output of `poly push`, containing the serialized Agent Studio commands that were staged. Useful for dry-run review and integration testing.

~~~bash
poly push --json --dry-run --output-json-commands
~~~

The output will include a `commands` key with each command serialized from its protobuf representation.

### Driving pull/push from a captured projection

The `--from-projection` flag on `pull`, `push`, `init`, and `branch switch` lets you supply a projection JSON directly (as a string or via stdin with `-`) instead of fetching it from the API. This is useful for offline workflows and integration testing.

~~~bash
poly pull --from-projection - < projection.json
poly push --from-projection '{"topics": [...], ...}'
cat projection.json | poly pull --from-projection -
~~~

The `--output-json-projection` flag on `pull`, `init`, and `branch switch` includes the projection in the JSON output when `--json` is also set. This lets you capture a projection from one command and feed it into another.

~~~bash
poly pull --json --output-json-projection | jq .projection > proj.json
poly push --from-projection - < proj.json
~~~


## Working pattern

A typical CLI workflow looks like this:

1. initialize or pull a project locally
2. create or switch to a branch
3. edit files
4. inspect changes with `poly status` and `poly diff`
5. validate with `poly validate`
6. push with `poly push`
7. optionally review with `poly review`
8. test or chat with the agent using `poly chat`

!!! info "Run commands from the project folder"

    ADK commands are expected to be run from within your local project directory. If needed, use the <code>--path</code> flag to point to a project explicitly.

## Related pages

<div class="grid cards" markdown>

-   **Build an agent**

    ---

    See how the CLI fits into a real workflow.
    [Open the tutorial](../tutorials/build-an-agent.md)

-   **Testing**

    ---

    Learn how to run tests for the project.
    [Open testing](./testing.md)

</div>
