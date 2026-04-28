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

`poly init` creates the project directory at `{base_path}/{account_id}/{project_id}` and immediately pulls the current configuration from Agent Studio. After it completes, change into the project directory before running any other commands.

The human-readable project name is stored in `project.yaml` alongside the `project_id`, `account_id`, and `region`:

~~~yaml
project_id: my-project
account_id: my-workspace
region: us-1
project_name: My Project
~~~

Examples:

~~~bash
poly init
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format
~~~

#### Error handling

If the account or project ID is invalid or inaccessible, `poly init` returns a descriptive error and cleans up any partially created directories so no empty folders are left behind.

| Situation | Error message |
|---|---|
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

!!! tip "Use `--details` for readable output"

    The default tabular view may wrap long URLs across multiple rows, making it unreadable in narrow terminals. `--details` produces a vertical layout that is easier to read.

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
~~~

When `--json` is used:

- stdout contains exactly one JSON object
- the process exits with code `0` on success and non-zero on failure
- human-readable console messages are suppressed

!!! info "`--interactive` and `--json` cannot be used together"

    `poly branch merge --interactive` requires a terminal for its conflict-resolution prompts and is incompatible with `--json`.

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
