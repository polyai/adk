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

Run with no arguments and `poly init` walks you through interactive dropdowns:

1. **Region** — auto-selected if your API key only has access to one.
2. **Account** — auto-selected if there's only one in the region; otherwise pick from a searchable list.
3. **Project** — pick from a searchable list of every project the API key can see.

After selection, `poly init` creates the project directory at `{base_path}/{account_id}/{project_id}` and immediately pulls the current configuration from Agent Studio. Change into the project directory before running any other commands.

The human-readable project name is stored in `project.yaml` alongside the `project_id`, `account_id`, and `region`:

~~~yaml
project_id: my-project
account_id: my-workspace
region: us-1
project_name: My Project
~~~

Pass any combination of `--region`, `--account_id`, and `--project_id` to skip the matching prompt. This is the form to use in scripts and CI.

Examples:

~~~bash
poly init
poly init --account_id 123 --project_id my_project
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format
~~~

#### Error handling

If the account or project ID is invalid or inaccessible, `poly init` returns a descriptive error and cleans up any partially created directories so no empty folders are left behind.

| Situation | Error message |
|---|---|
| `POLY_ADK_KEY` not set | `POLY_ADK_KEY environment variable is not set. Export your API key with: export POLY_ADK_KEY=<your-api-key>` |
| Project not found | `Project '<project_id>' not found in account '<account_id>'.` |
| Permission denied | `Forbidden: you do not have permission to access project '<project_id>' in account '<account_id>'.` |

When using `--json`, the response includes `{ "success": false, "error": "..." }` with the same message.

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

| Flag | Description |
|---|---|
| `--dry-run` | Run all validation and diff steps without sending changes to Agent Studio. |
| `--skip-validation` | Bypass local validation. Use sparingly — for example, when a platform-generated resource fails a strict ADK check but is known to be valid on the platform. |
| `--force`, `-f` | Force the push even when the local project diverges from the remote in unexpected ways. |
| `--format` | Run [`poly format`](#poly-format) over the project before pushing. |

!!! info "Call Link URL in chat output may be malformed"

    Each chat session prints a Call Link URL for viewing the conversation in Agent Studio. On some deployments this URL has a doubled hostname (for example, `https://studio.studio.poly.ai/…`), which produces a 404. The conversation is still recorded — open Agent Studio directly and navigate to the conversation from there.

!!! info "`poly push` reports an error message when there is nothing to push"

    If there are no local changes, `poly push` prints `Error: Failed to push` and `No changes detected`. The exit code is 0, so CI scripts that check return codes are not affected. The message is misleading but the command has not actually failed.

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
poly diff --files file1.yaml
poly diff --before main --after my-feature
~~~

### `poly revert`

Revert local changes.

Examples:

~~~bash
poly revert
poly revert file1.yaml file2.yaml
~~~

`poly revert` with no arguments reverts every change in the working tree; pass file paths to revert only those files.

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
poly branch merge 'Merge feature branch'
poly branch merge 'Merge feature branch' --interactive
poly branch delete
poly branch delete my-feature
~~~

#### `poly branch merge`

Merge the current branch into `main` via the CLI. A merge message is required.

~~~bash
poly branch merge 'Merge message'
poly branch merge 'Merge message' --interactive
poly branch merge 'Merge message' --resolutions resolutions.json
~~~

For the full merge workflow — conflict tables, `--interactive` flow, the `--resolutions` JSON format, post-merge behavior, and troubleshooting — see the dedicated [Branch merging reference](./branch_merge.md).

#### `poly branch delete`

Interactively select and delete one or more branches. The `main` branch cannot be deleted.

- Run without arguments to open an interactive checkbox prompt for selecting branches to delete.
- Pass a branch name directly to skip the interactive prompt and delete that branch after confirmation.

~~~bash
poly branch delete
poly branch delete my-feature
~~~

!!! warning "`poly branch delete` requires a TTY and may fail with a 404"

    `poly branch delete` opens an interactive confirmation prompt and must be run in a terminal. In non-interactive environments (scripts, CI), it throws `[Errno 22] Invalid argument`.

    On some projects, the delete command hits the same platform endpoint as branch chat and returns a 404 after the confirmation. If this happens, delete the branch through the Agent Studio UI instead.

#### `poly branch create`

Creates a new branch. By default the branch is sourced from the project's `main` branch (the sandbox environment).

| Flag | Description |
|---|---|
| `--env`, `--environment` | Source the new branch from a deployed environment snapshot instead of `main`. Choices: `sandbox`, `pre-release`, `live`. |
| `--force`, `-f` | Force branch creation even if there are uncommitted local changes on main. |

When `--env live` or `--env pre-release` is specified:

- the version of the deployed environment is pulled into your local workspace
- a branch is created from that snapshot
- the version is immediately pushed to the new branch, leaving a clean slate for hotfix changes
- the command can only be run from `main`
- if there are local changes, the command will fail unless `--force` is also passed

!!! warning "Use `--env live` with caution"

    Branching from a live deployment snapshot will overwrite your local project with the live state. Merging this branch back to main may roll back changes that were introduced after the snapshot was taken.

!!! info "Only one active branch is allowed at a time"

    Agent Studio supports one non-main branch per project. Attempting to create a second branch while one already exists returns an error. Merge or delete the existing branch in Agent Studio before creating a new one.

### `poly format`

Format project resources.

Examples:

~~~bash
poly format
poly format --check
poly format --files src/functions/booking.py
~~~

### `poly validate`

Validate project configuration locally.

~~~bash
poly validate
~~~

### `poly review`

Create a GitHub Gist of Agent Studio project changes to share with others.

`poly review` requires a subcommand: `create`, `list`, or `delete`. Use `poly review create` to compare your local changes against the remote project, or pass `--before` and `--after` to compare two remote branches or versions. Add `--verbose` for full error tracebacks while troubleshooting.

Examples:

~~~bash
poly review create
poly review create --before main --after feature-branch
poly review create --verbose
~~~

#### `poly review list`

Interactively select a review gist and open it in the browser.

~~~bash
poly review list
poly review list --json
~~~

#### `poly review delete`

Interactively select and delete review gists. Use `--id` to delete a specific gist directly without an interactive prompt.

~~~bash
poly review delete
poly review delete --id GIST_ID
poly review delete --json
~~~

### `poly chat`

Start an interactive chat session with your agent, or run scripted/automated conversations.

Examples:

~~~bash
poly chat
poly chat --environment live
poly chat --channel webchat
poly chat --metadata
poly chat --lang fr-FR
poly chat --input-lang en-US --output-lang fr-FR
~~~

#### Non-interactive (scripted) mode

Supply messages directly on the command line or from a file to run `poly chat` without a human at the terminal. This is useful for automated testing pipelines and CI scripts.

**Inline messages** — use `-m`/`--message` (repeatable):

~~~bash
poly chat -m 'Hello' -m 'What can you help with?'
~~~

**File-based input** — use `--input-file`:

~~~bash
poly chat --input-file ./script.txt
echo -e 'Hello\nGoodbye' | poly chat --input-file -
~~~

Each line of the file is sent as a separate message. Use `-` to read from stdin.

If the file path does not exist, `poly chat` exits with an error.

#### Resuming an existing conversation

Use `--conversation-id` (or `--conv-id`) to resume an existing conversation by its ID instead of creating a new session:

~~~bash
poly chat --conv-id <conversation_id>
poly chat --conv-id <conversation_id> -m 'Follow-up message'
~~~

#### Pushing before chatting

Use `--push` to push the local project to Agent Studio before starting the chat session. This ensures local changes are live before testing without requiring a separate `poly push` step:

~~~bash
poly chat --push
poly chat --push -m 'Hello'
~~~

If the push fails, the command exits without starting the chat session.

#### Language flags

Use language flags to specify the expected input and output language when chatting against multilingual agents. If not specified, the project default is used.

| Flag | Description |
|---|---|
| `--lang` | Sets both input and output language (e.g. `en-US`, `fr-FR`). |
| `--input-lang` | Sets the input language (ASR) only. Overrides `--lang` for input. |
| `--output-lang` | Sets the output language (TTS) only. Overrides `--lang` for output. |

`--input-lang` and `--output-lang` take precedence over `--lang` when both are supplied.

#### `poly chat` flags summary

| Flag | Description |
|---|---|
| `--push` | Push the project before starting the chat session. |
| `-m`, `--message MSG` | Send a message non-interactively (repeatable). |
| `--input-file FILE` | Read messages line-by-line from a file (`-` for stdin). |
| `--conversation-id`, `--conv-id` | Resume an existing conversation by ID. |
| `--json` | Emit a single JSON object when the session ends (see below). |
| `--environment` | Target environment. Choices: `branch`, `sandbox`, `pre-release`, `live`. Defaults to `branch`. `branch` chats against the last **pushed** state of your current branch (not local uncommitted changes); on main it falls back to `sandbox`. Use `--push` to push local changes before chatting. |
| `--channel` | Channel to use (e.g. `webchat`, `voice`). |
| `--lang` | Set both input and output language. |
| `--input-lang` | Set input language only. |
| `--output-lang` | Set output language only. |
| `--variant` | Name of the variant to use for the chat session. |
| `--functions` | Show function events in output. |
| `--flows` | Show flow metadata in output. |
| `--state` | Show state changes in output. |
| `--metadata` | Show all metadata (equivalent to `--functions --flows --state`). |

### `poly docs`

Output resource documentation.

Examples:

~~~bash
poly docs flows functions topics
poly docs --all
poly docs --all --output rules.md
~~~

Use `--output` to write the documentation to a local file. This is useful when working with AI coding tools — pass the output file as context to give the agent accurate knowledge of ADK resource types and conventions.

### `poly deployments`

Manage deployments for the project.

#### `poly deployments list`

List deployments for the project.

Examples:

~~~bash
poly deployments list
poly deployments list --env live
poly deployments list --details
~~~

| Flag | Description |
|---|---|
| `--env` | Environment to list deployments for. Choices: `sandbox`, `pre-release`, `live`. Defaults to `sandbox`. |
| `--details` | Show additional deployment details. |
| `--verbose` | Show full error tracebacks for debugging. |

!!! tip "Use `--details` for readable output"

    The default tabular view may wrap long URLs across multiple rows, making it unreadable in narrow terminals. `--details` produces a vertical layout that is easier to read.

#### `poly deployments promote`

Promote a deployment to the next environment (`pre-release` or `live`), removing the need to use the Agent Studio UI.

Examples:

~~~bash
poly deployments promote --from <deployment_id> --to pre-release
poly deployments promote --from sandbox --to live --message "Release notes here"
poly deployments promote --from <deployment_id> --to pre-release --dry-run
poly deployments promote --from <deployment_id> --to live --force
~~~

| Flag | Description |
|---|---|
| `--from` | ID or environment name of the deployment to promote. Required. |
| `--to` | Target environment. Choices: `pre-release`, `live`. Required. |
| `--message`, `-m` | Optional message to include with the promotion (e.g. release notes or changelog). If not specified, the existing deployment message is used. |
| `--force` | Skip the confirmation prompt. When used without `--message`, the existing deployment message is kept. This is the default in non-interactive mode (e.g. when `--json` is used). |
| `--dry-run` | Show what would be promoted without actually promoting. Displays the deployment hash, target environment, and changes included. |
| `--verbose` | Show full error tracebacks for debugging. |

When promoting to `live`, the command searches for the deployment in `pre-release` and uses sandbox as the linear history source for computing included changes. When promoting to `pre-release`, the command searches sandbox.

The output includes:

- the deployment hash being promoted
- whether it is a first-time promotion to that environment
- a list of **included deployments** (changes being promoted) or **reverting deployments** (when promoting to an older version)

Without `--force`, the command prompts for confirmation before proceeding and optionally allows you to enter or override the deployment message interactively.

#### `poly deployments rollback`

Roll back sandbox to a previous deployment version.

Examples:

~~~bash
poly deployments rollback --to <deployment_id>
poly deployments rollback --to <deployment_id> --message "Rolling back due to regression"
poly deployments rollback --to <deployment_id> --dry-run
poly deployments rollback --to <deployment_id> --force
~~~

| Flag | Description |
|---|---|
| `--to` | ID or environment name of the deployment to roll back to. Required. |
| `--message`, `-m` | Optional message to include with the rollback. If not specified, the existing deployment message is used. |
| `--force` | Skip the confirmation prompt. This is the default in non-interactive mode (e.g. when `--json` is used). |
| `--dry-run` | Show what would be rolled back without actually rolling back. Displays the target deployment and the deployments that would be reverted. |
| `--verbose` | Show full error tracebacks for debugging. |

The output includes a list of **reverting deployments** — the versions that will be undone when the rollback completes.

Without `--force`, the command prompts for confirmation before proceeding.

## Machine-readable JSON output

All core subcommands accept a `--json` flag that switches stdout to a single JSON object. This is designed for scripting, CI pipelines, and any integration that needs stable, parseable output rather than human-readable console text.

~~~bash
poly status --json
poly push --json
poly pull --json
poly validate --json
poly diff --json
poly revert --json
poly branch list --json
poly branch create my-feature --json
poly branch switch my-feature --json
poly branch current --json
poly branch delete --json
poly branch delete my-feature --json
poly branch merge 'Merge message' --json
poly format --json
poly init --region us-1 --account_id 123 --project_id my_project --json
poly chat --json -m 'Hello'
poly chat --json --input-file ./script.txt
poly deployments list --json
poly deployments promote --from <id> --to pre-release --force --json
poly deployments rollback --to <id> --force --json
~~~

When `--json` is used:

- stdout contains exactly one JSON object
- the process exits with code `0` on success and non-zero on failure
- human-readable console messages are suppressed

!!! info "`--interactive` and `--json` cannot be used together"

    `poly branch merge --interactive` requires a terminal for its conflict-resolution prompts and is incompatible with `--json`.

!!! info "`--json` implies `--force` for deployments commands"

    When `--json` is used with `poly deployments promote` or `poly deployments rollback`, the confirmation prompt is automatically skipped (equivalent to passing `--force`).

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
| `poly branch merge --json` | `success`; on conflict: `conflicts`, `errors` |
| `poly format --json` | `success`, `check_only`, `format_errors`, `affected`, `ty_ran`, `ty_returncode`, `ty_timed_out` |
| `poly init --json` | `success`, `root_path` |
| `poly chat --json` | `conversations` (array); optional `push` (when `--push` is used) |
| `poly deployments promote --json` | `success`, `from_hash`, `to_env`, `message`, `included_deployments`; `dry_run` when `--dry-run` is used |
| `poly deployments rollback --json` | `success`, `target_hash`, `message`, `reverted_deployments`; `dry_run` when `--dry-run` is used |

For `poly branch delete --json`, when a branch that was the current branch is deleted, the response also includes `"switched_to": "main"`.

For `poly branch merge --json`, a successful merge returns `{ "success": true }`. When conflicts or errors are present, the response includes `"conflicts"` and `"errors"` arrays containing the raw conflict and error objects from the platform.

Error responses always include `{ "success": false, "error": "...", "traceback": "..." }`.

!!! info "`init` with `--json` requires explicit flags"

    When using `poly init --json`, you must supply `--region`, `--account_id`, and `--project_id` explicitly. Interactive prompts are not supported in JSON mode.

#### `poly chat --json` output shape

When `--json` is used with `poly chat`, the command emits a single JSON object when the session ends:

~~~json
{
  "conversations": [
    {
      "conversation_id": "conv-123",
      "url": "https://...",
      "turns": [
        { "input": null, "response": "Hello! How can I help?", "conversation_ended": false },
        { "input": "What are your hours?", "response": "We are open 9am–5pm.", "conversation_ended": false }
      ]
    }
  ]
}
~~~

- `conversations` is an array because `/restart` in scripted input produces multiple entries.
- `turns[0]` is always the agent greeting, with `"input": null`.
- If `--push` is also supplied, the output includes a `push` key: `{ "push": { "success": true, "message": "..." } }`.
- If `--functions`, `--flows`, or `--state` are also set, the relevant metadata fields are included in each turn.

#### `poly deployments promote --json` output shape

~~~json
{
  "success": true,
  "from_hash": "abc123456xyz",
  "to_env": "pre-release",
  "message": "Release notes here",
  "included_deployments": [...]
}
~~~

On dry run, `"dry_run": true` is added and `"success"` reflects the pre-flight state without any changes being made. On error, `"success": false` and `"error": "..."` are returned.

#### `poly deployments rollback --json` output shape

~~~json
{
  "success": true,
  "target_hash": "def789012xyz",
  "message": "Rolling back due to regression",
  "reverted_deployments": [...]
}
~~~

On dry run, `"dry_run": true` is added. On error, `"success": false` and `"error": "..."` are returned.

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
9. merge the branch with `poly branch merge '<message>'`
10. promote to pre-release or live with `poly deployments promote`

!!! info "Run commands from the project folder"

    ADK commands are expected to be run from within your local project directory. If needed, use the <code>--path</code> flag to point to a project explicitly.

## Related pages

<div class="grid cards" markdown>

-   **Build an agent**

    ---

    See how the CLI fits into a real workflow.
    [Open the tutorial](../tutorials/build-an-agent.md)

-   **Branch merging**

    ---

    Conflict resolution, `--interactive` flow, and `--resolutions` JSON for `poly branch merge`.
    [Open branch merging](./branch_merge.md)

-   **Testing**

    ---

    Learn how to run tests for the project.
    [Open testing](./testing.md)

-   **Working locally**

    ---

    How the CLI fits into the daily edit/push/test loop.
    [Open working locally](../concepts/working-locally.md)

</div>
