---
title: CLI reference
description: Index of every command provided by the PolyAI ADK CLI, with the flags shared across all of them.
---

# CLI reference

<p class="lead">
The PolyAI ADK is accessed through the <code>poly</code> command.
Use the CLI help output as the first source of truth.
</p>

## Start with help

To see all available commands and options:

~~~bash
poly --help
~~~

Commands are listed under section headers so related ones stay together:

| Section | Commands |
|---|---|
| Getting started | `init`, `start`, `login`, `studio`, `project` |
| Project sync | `pull`, `push`, `status`, `revert`, `format`, `validate`, `diff`, `review`, `branch`, `test`, `rtc`, `chat` |
| Builder API | `deployments`, `conversations`, `audio-cache`, `functions` |
| Other | `docs`, `completion` |

Each command also supports its own help output. For example:

~~~bash
poly push --help
~~~

!!! tip "Use help output as the source of truth"

    The installed CLI is the fastest way to confirm the commands and flags available in your local environment.

## Commands

### Setting up

| Command | Purpose |
|---|---|
| [`poly login`](./cli/login.md) | Sign in to, or sign up for, an Agent Studio account |
| [`poly start`](./cli/start.md) | Create an account and a project in one step |
| [`poly init`](./cli/init.md) | Connect a local folder to an existing project |
| [`poly project`](./cli/project.md) | Create and manage Agent Studio projects |
| [`poly template`](./cli/template.md) | Browse and load example project templates |
| [`poly completion`](./cli/completion.md) | Output a shell completion script |

### Editing and syncing

| Command | Purpose |
|---|---|
| [`poly pull`](./cli/pull.md) | Pull remote configuration into the local project |
| [`poly push`](./cli/push.md) | Push local changes to Agent Studio |
| [`poly status`](./cli/status.md) | List changed files |
| [`poly diff`](./cli/diff.md) | Show local changes in detail |
| [`poly revert`](./cli/revert.md) | Discard local changes |
| [`poly format`](./cli/format.md) | Format resource files |
| [`poly validate`](./cli/validate.md) | Validate the project locally |

### Branches and review

| Command | Purpose |
|---|---|
| [`poly branch`](./cli/branch.md) | Create, switch, inspect, and merge branches |
| [`poly review`](./cli/review.md) | Publish a diff for review |

### Testing and inspection

| Command | Purpose |
|---|---|
| [`poly chat`](./cli/chat.md) | Talk to the agent interactively |
| [`poly test`](./cli/test.md) | Run and inspect simulated conversation tests |
| [`poly conversations`](./cli/conversations.md) | List and inspect real conversations |
| [`poly docs`](./cli/docs.md) | Output resource documentation |

### Deployment and configuration

| Command | Purpose |
|---|---|
| [`poly deployments`](./cli/deployments.md) | List, promote, and roll back deployments |
| [`poly rtc`](./cli/rtc.md) | Manage per-environment Real-Time Configuration |
| [`poly audio-cache`](./cli/audio-cache.md) | Inspect and replace cached TTS audio |
| [`poly studio`](./cli/studio.md) | Open the project in the Agent Studio web app |

## Shared flags

Most commands accept the same four flags:

| Flag | Description |
|---|---|
| `--path PATH` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout, for scripting. See below. |
| `--verbose` | Show full error tracebacks. |
| `--debug` | Display debug logs. |

!!! tip "Run commands from the project folder"

    ADK commands are expected to be run from within your local project directory. If needed, use `--path` to point to a project explicitly.

`poly login`:

1. Prompts for a region if `--region` is not supplied.
2. Opens a browser window for sign-in via the Auth0 device authorization flow.
3. Fetches or creates an API key for your user and saves it to `~/.poly/credentials.json` under the chosen region.

Run `poly login` once per region you need access to — credentials for multiple regions are stored side by side in the credential file.

Examples:

~~~bash
poly login
poly login --region us-1
poly login --region euw-1
poly login --region uk-1
poly login --region studio
~~~

| Flag | Description |
|---|---|
| `--region` | Region to log in to. If omitted, you are prompted to pick one. Choices match the standard region list. |

### `poly project`

Manage Agent Studio projects.

#### `poly project create`

Create a new Agent Studio project under an account, then initialize it locally.

Run with no arguments and `poly project create` walks you through interactive prompts:

1. **Region** — auto-selected if your API key only has access to one.
2. **Account** — auto-selected if there's only one in the region; otherwise pick from a searchable list.
3. **Project name** — free-text name for the new project.
4. **Project ID** — optional slug. Defaults to a slugified version of the name (lowercased, spaces replaced with hyphens, special characters removed). Leave empty to let the platform generate one.

After the project is created in Agent Studio, `poly project create` automatically calls `poly init` to initialize the local project directory.

Examples:

~~~bash
poly project create
poly project create --region us-1 --account_id my-account --name my-project
poly project create --region us-1 --account_id my-account --name "My Project" --id my-project
poly project create --region us-1 --account_id my-account --name my-project --greeting "Hi, how can I help?"
poly project create --base-path /path/to/projects
~~~

| Flag | Description |
|---|---|
| `--region` | Region for the new project. Choices match the standard region list. |
| `--account_id` | Account ID to create the project under. |
| `--name` | Display name for the new project. |
| `--id`, `--project_id` | Optional slug/ID for the project. Defaults to a slugified version of the name. |
| `--greeting` | Initial greeting message for the agent. Defaults to `"Hello, how can I help you?"`. |
| `--voice-id` | Voice ID for the agent. Defaults to a region-specific voice if not supplied. |
| `--base-path` | Base path to initialize the project in. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). Requires `--region`, `--account_id`, and `--name`. |

!!! info "`--json` requires explicit flags for `poly project create`"

    When using `poly project create --json`, you must supply `--region`, `--account_id`, and `--name` explicitly. Interactive prompts are not supported in JSON mode.

#### Error handling

| Situation | Behaviour |
|---|---|
| `--json` used without `--region`, `--account_id`, or `--name` | Exits with `{ "success": false, "error": "..." }` |
| No accessible regions found | Exits with an error |
| No accounts found in the selected region | Exits with an error |
| API error during project creation | Exits with an error; local init is not attempted |
| No project ID returned by the API | Exits with an error; local init is not attempted |

### `poly init`

Initialize a new Agent Studio project locally.

Run with no arguments and `poly init` walks you through interactive dropdowns:

1. **Region** — auto-selected if your API key only has access to one.
2. **Account** — auto-selected if there's only one in the region; otherwise pick from a searchable list. Each entry is shown as `"name (id)"` to disambiguate accounts that share the same display name.
3. **Project** — pick from a searchable list of every project the API key can see. Each entry is shown as `"name (id)"` for the same reason.

If no projects are found in the selected account, `poly init` offers to create one. Accepting the prompt starts the [`poly project create`](#poly-project-create) flow with the region and account already pre-selected.

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
| No accounts found in the region | `No accounts found in the selected region.` |
| No projects found in the account | Prompts to create a new project (interactive) or exits with error (JSON mode). |
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

Manage project branches. `poly branch --help` splits its subcommands into
**Branch lifecycle** (`list`, `create`, `switch`, `current`, `delete`, `merge`)
and **Inspect** (`diff`, `review`, `status`).

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
poly chat --sip-header X-Customer-ID=12345
poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB
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

#### Simulating SIP headers

Use `--sip-header NAME=VALUE` to simulate a SIP header when starting a conversation.

Single header:

~~~bash
poly chat --sip-header X-Customer-ID=12345
~~~

Multiple headers are supported by repeating the flag:

~~~bash
poly chat --sip-header X-Customer-ID=12345 --sip-header X-Language=en-GB
~~~

The values are exposed to project functions through `conv.sip_headers`. This is for
testing agent behaviour only; it does not create a SIP call or reproduce carrier-level
SIP behaviour. SIP headers cannot be changed when resuming an existing conversation.

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
| `--sip-header NAME=VALUE` | Simulate a SIP header at conversation start (repeatable). |
| `--lang` | Set both input and output language. |
| `--input-lang` | Set input language only. |
| `--output-lang` | Set output language only. |
| `--variant` | Name of the variant to use for the chat session. |
| `--functions` | Show function events in output. |
| `--flows` | Show flow metadata in output. |
| `--state` | Show state changes in output. |
| `--metadata` | Show all metadata (equivalent to `--functions --flows --state`). |

### `poly conversations`

List and inspect conversations for the project using the public Conversations API.

`poly conversations` requires a subcommand: `list`, `get`, or `get-audio`.

Examples:

~~~bash
poly conversations list
poly conversations get <conversation_id>
poly conversations get-audio <conversation_id> -o recording.wav
~~~

#### `poly conversations list`

List conversations for the project.

~~~bash
poly conversations list
poly conversations list --limit 20 --offset 10
poly conversations list --json
~~~

| Flag | Description |
|---|---|
| `--limit` | Max number of conversations to return. Defaults to `50`. |
| `--offset` | Number of conversations to skip. Defaults to `0`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

The default table view shows conversation ID (rendered as a clickable Agent Studio link), start time, duration, caller number, channel, variant (when present), handoff status, and a short summary heading.

#### `poly conversations get`

Get detailed information for a specific conversation, including all turns.

~~~bash
poly conversations get <conversation_id>
poly conversations get <conversation_id> --json
~~~

| Argument / Flag | Description |
|---|---|
| `conversation_id` | The conversation ID to look up. Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

The default output shows conversation metadata (channel, language, duration, timestamps, handoff, tags, PolyScore, summary, note) followed by a turn-by-turn transcript.

#### `poly conversations get-audio`

Download the audio recording for a conversation as a WAV file.

~~~bash
poly conversations get-audio <conversation_id>
poly conversations get-audio <conversation_id> --direction user
poly conversations get-audio <conversation_id> --redacted -o redacted.wav
poly conversations get-audio <conversation_id> --json
~~~

| Argument / Flag | Description |
|---|---|
| `conversation_id` | The conversation ID. Required. |
| `--direction` | Audio track to download. Choices: `combined`, `user`, `agent`. Defaults to `combined`. |
| `--redacted` | Download the redacted version of the audio. |
| `-o`, `--output` | Output file path. Defaults to `<conversation_id>.wav`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a JSON summary on stdout instead of the success message (audio is still written to disk). |

### `poly audio-cache`

Manage an agent's cached TTS audio entries using the public Audio Cache API.

`poly audio-cache` requires a subcommand: `list`, `get-file`, `update-file`, `update-details`, `delete`, `bulk-delete`, or `synthesize`.

Examples:

~~~bash
poly audio-cache list
poly audio-cache get-file <entry_id> -o cached.wav
poly audio-cache update-file <entry_id> --file replacement.wav
poly audio-cache synthesize <entry_id> --text "Hello there" -o preview.wav
poly audio-cache delete <entry_id>
poly audio-cache bulk-delete --ids id1,id2,id3
~~~

#### `poly audio-cache list`

List cached TTS audio entries with metadata (transcript, provider, voice, duration, hit count).

~~~bash
poly audio-cache list
poly audio-cache list --limit 20 --offset 10
poly audio-cache list --sort hit_count:desc
~~~

| Flag | Description |
|---|---|
| `--limit` | Max number of entries to return (1-200). Defaults to `50`. |
| `--offset` | Number of entries to skip. Defaults to `0`. |
| `--sort` | Sort expression, e.g. `hit_count:desc` or `duration:asc`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly audio-cache get-file`

Download the cached WAV audio file for a cache entry.

~~~bash
poly audio-cache get-file <entry_id>
poly audio-cache get-file <entry_id> -o cached.wav
~~~

| Argument / Flag | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |
| `-o`, `--output` | Output file path. Defaults to `<entry_id>.wav`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a JSON summary on stdout instead of the success message (audio is still written to disk). |

#### `poly audio-cache update-file`

Replace the audio file for an existing cache entry. Maximum file size is 6MB.

~~~bash
poly audio-cache update-file <entry_id> --file replacement.wav
poly audio-cache update-file <entry_id> --file replacement.wav --filename clip.wav
~~~

| Argument / Flag | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |
| `--file` | Path to the local replacement WAV file. Required. |
| `--filename` | Filename to record for the uploaded audio. Defaults to the local file's basename. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly audio-cache update-details`

Replace both the audio file and voice tuning settings for a cache entry in one call. Maximum file size is 6MB.

~~~bash
poly audio-cache update-details <entry_id> --file replacement.wav --text "Hi there"
poly audio-cache update-details <entry_id> --file replacement.wav --text "Hi" --config '{"stability": 0.5}'
~~~

| Argument / Flag | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |
| `--file` | Path to the local replacement WAV file. Required. |
| `--text` | Transcript text associated with the audio. Required. |
| `--config` | JSON object of provider-specific voice tuning settings (e.g. `stability`, `speed`, `model_id`). Defaults to `{}`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly audio-cache delete`

Permanently delete a cached audio entry and its audio file.

~~~bash
poly audio-cache delete <entry_id>
~~~

| Argument / Flag | Description |
|---|---|
| `entry_id` | The audio cache entry ID. Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly audio-cache bulk-delete`

Delete multiple audio cache entries in a single request. Best-effort — reports which IDs succeeded and which failed, so partial failures can be retried. Maximum 20 IDs per request.

~~~bash
poly audio-cache bulk-delete --ids id1,id2,id3
~~~

| Argument / Flag | Description |
|---|---|
| `--ids` | Comma-separated list of audio cache entry IDs to delete (max 20). Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly audio-cache synthesize`

Generate a TTS audio preview using an existing cache entry's voice and provider configuration, without saving it to the cache.

~~~bash
poly audio-cache synthesize <entry_id> --text "Hello there"
poly audio-cache synthesize <entry_id> --text "Hi" --language en-US -o out.wav
~~~

| Argument / Flag | Description |
|---|---|
| `entry_id` | The audio cache entry ID whose voice/provider config to preview with. Required. |
| `--text` | Text to synthesize. Required. |
| `--config` | JSON object of provider-specific voice tuning settings. Defaults to `{}`. |
| `--language` | BCP-47 language tag, e.g. `en-US`. |
| `-o`, `--output` | Output file path. Defaults to `<entry_id>-preview.wav`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a JSON summary on stdout instead of the success message (audio is still written to disk). |

### `poly functions`

Manage Functions using the public Functions REST API, scoped to the project's current branch.

!!! note

    This is a different mechanism from the local `functions/*.py` files synced by `poly pull` / `poly push` (see [Functions](functions.md)). `poly functions` talks to the Functions REST API directly and does not read or write local function files.

Every subcommand also accepts `--region`, `--project_id` and `--branch_id` directly, so `poly functions` can run headlessly (CI, scripts) without a local project checkout:

~~~bash
poly functions list --region us-1 --project_id abc123 --branch_id main
~~~

All three must be given together — if any one is set, all three are required. With none set, the current local project's region/project/branch are used, as before.

`poly functions --help` splits its subcommands into four sections:

| Section | Subcommands |
|---|---|
| Manage | `list`, `get`, `create`, `update`, `delete`, `duplicate` |
| Run and inspect | `execute`, `references`, `type-definitions` |
| Deploy | `validate`, `deploy`, `deployments` |
| Lifecycle hooks | `start`, `end` |

Examples:

~~~bash
poly functions list
poly functions get <function_id>
poly functions create --name my_func --description "desc" --code-file func.py
poly functions execute <function_id> --args '{"x": 1}'
poly functions deploy
~~~

#### `poly functions list`

List the Functions defined on the current branch.

~~~bash
poly functions list
poly functions list --limit 50 --offset 50
~~~

| Flag | Description |
|---|---|
| `--limit` | Max number of functions to return (1-50). Defaults to `20`. |
| `--offset` | Number of functions to skip. Defaults to `0`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions get`

Show a function's metadata, parameters and code.

~~~bash
poly functions get <function_id>
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions create`

Create a new Function on the current branch from a local code file.

~~~bash
poly functions create --name my_func --description "desc" --code-file func.py
poly functions create --name my_func --description "desc" --code-file func.py \
    --parameters '[{"name": "x", "type": "str", "description": "an x"}]'
~~~

| Flag | Description |
|---|---|
| `--name` | The function name. Required. |
| `--description` | The function description. Required. |
| `--code-file` | Local path to the function's Python source. Required. |
| `--parameters` | JSON list of parameter specs. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

A name collision returns a conflict and is not overridable — pick a different name.

#### `poly functions update`

Update a Function's name, description, code or parameters. At least one field must be supplied.

~~~bash
poly functions update <function_id> --code-file func.py
poly functions update <function_id> --description "new desc"
poly functions update <function_id> --name renamed --force
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `--name` | New function name. |
| `--description` | New function description. |
| `--code-file` | Local path to the replacement Python source. |
| `--parameters` | JSON list of parameter specs. |
| `-f`, `--force` | Override an orphaned-reference conflict, leaving flow steps pointing at nothing. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

If flow steps reference the function in a way the change would break, the command reports the conflicting steps and exits non-zero. Re-run with `--force` to apply it anyway. With `--json`, the conflicting steps are returned under `orphaned_references`.

#### `poly functions delete`

Delete a Function from the current branch.

~~~bash
poly functions delete <function_id>
poly functions delete <function_id> --force
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `-f`, `--force` | Override an orphaned-reference conflict, leaving flow steps pointing at nothing. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions execute`

Execute a Function and print its return value, logs and runtime.

~~~bash
poly functions execute <function_id>
poly functions execute <function_id> --args '{"x": 1}'
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `--args` | JSON object of arguments to pass to the function. Defaults to `{}`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions duplicate`

Copy a Function on the current branch.

~~~bash
poly functions duplicate <function_id>
poly functions duplicate <function_id> --name my_func_copy
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID to copy. Required. |
| `--name` | Name for the copy. Defaults to a server-generated name. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions deploy`

Deploy every draft Function on the current branch.

~~~bash
poly functions deploy
~~~

| Flag | Description |
|---|---|
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions validate`

Check every Function on the current branch for syntax errors and orphaned flow-step references.

~~~bash
poly functions validate
~~~

| Flag | Description |
|---|---|
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions references`

List the flow steps that call a Function. Useful before a rename or delete.

~~~bash
poly functions references <function_id>
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions type-definitions`

Print the `Conversation`/`Flow` type stubs available to a Function, for IDE autocomplete.

~~~bash
poly functions type-definitions <function_id>
poly functions type-definitions <function_id> > stubs.py
~~~

| Argument / Flag | Description |
|---|---|
| `function_id` | The function ID. Required. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions deployments`

Show the deployment history for the project's Functions across environments.

~~~bash
poly functions deployments
~~~

| Flag | Description |
|---|---|
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

#### `poly functions start` / `poly functions end`

Read or replace the branch's `start_function` and `end_function`. Each takes a `get` or `update` subcommand.

~~~bash
poly functions start get
poly functions start update --code-file start.py
poly functions end get
poly functions end update --code-file end.py
~~~

| Argument / Flag | Description |
|---|---|
| `--code-file` | Local path to the replacement source. Required for `update`. |
| `--path` | Base path to the project. Defaults to the current working directory. |
| `--json` | Print a single JSON object on stdout (machine-readable). |

### `poly docs`

Output resource documentation.

Examples:

~~~bash
poly docs flows functions topics
poly docs context
poly docs --all
poly docs --all --output rules.md
~~~

Use `--output` to write the documentation to a local file. This is useful when working with AI coding tools — pass the output file as context to give the agent accurate knowledge of ADK resource types and conventions.

Available resource names include:

| Name | Description |
|---|---|
| `agent_settings` | Personality, role, rules |
| `api_integrations` | External HTTP API definitions |
| `chat_settings` | Chat greeting, style prompt |
| `context` | Context files for agent knowledge |
| `entities` | Structured data collection |
| `experimental_config` | Feature flags |
| `flows` | Multistep processes with steps, functions, conditions |
| `handoffs` | SIP call transfers |
| `functions` | Global and flow functions, decorators, state, metrics |
| `languages` | Default and additional language configuration |
| `tests` | Simulated conversation test cases |
| `safety_filters` | Content moderation settings |
| `sms` | Text message templates |
| `speech_recognition` | ASR settings, keyphrase boosting, transcript corrections |
| `response_control` | Pronunciations, phrase filters |
| `topics` | Knowledge base for RAG |
| `translations` | Localized text strings per language |
| `variants` | Per-variant configuration |
| `voice_settings` | Voice greeting, disclaimer, style prompt |
| `variables` | State variables referenced in code |

### `poly deployments`

Manage deployments for the project.

#### `poly deployments list`

List deployments for the project.

Examples:

~~~bash
poly deployments list
poly deployments list --env live
poly deployments list --details
poly deployments show abc123def
poly deployments show abc123def --env live
~~~

#### `poly deployments list`

List deployments for the project.

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
poly project create --region us-1 --account_id my-account --name my-project --json
poly chat --json -m 'Hello'
poly chat --json --input-file ./script.txt
poly deployments show abc123def --json
poly deployments list --json
poly deployments promote --from <id> --to pre-release --force --json
poly deployments rollback --to <id> --force --json
poly conversations list --json
poly conversations get <conversation_id> --json
poly conversations get-audio <conversation_id> --json
poly audio-cache list --json
poly audio-cache get-file <entry_id> --json
poly audio-cache update-file <entry_id> --file replacement.wav --json
poly audio-cache delete <entry_id> --json
poly audio-cache bulk-delete --ids id1,id2 --json
poly audio-cache synthesize <entry_id> --text "Hello" --json
poly functions list --json
poly functions get <function_id> --json
poly functions create --name my_func --description "desc" --code-file func.py --json
poly functions execute <function_id> --args '{"x": 1}' --json
poly functions validate --json
poly functions deploy --json
~~~

### `--json` contract

When `--json` is used:

- stdout contains exactly one JSON object
- the process exits with code `0` on success and non-zero on failure
- human-readable console messages are suppressed
- error responses always include `{ "success": false, "error": "...", "traceback": "..." }`

The exact top-level keys vary by command — each command's page documents its own output shape.

!!! info "`--interactive` and `--json` cannot be used together"

    `poly branch merge --interactive` requires a terminal for its conflict-resolution prompts and is incompatible with `--json`.

!!! info "`--json` implies `--force` for deployments commands"

    When `--json` is used with `poly deployments promote` or `poly deployments rollback`, the confirmation prompt is automatically skipped (equivalent to passing `--force`).

### Advanced JSON-driven workflows

A few commands support extra flags for piping JSON between invocations instead of hitting the API each time:

| Flag | Commands | Description |
|---|---|---|
| `--from-projection <source>` | `pull`, `push`, `init`, `branch switch` | Supply a projection JSON directly (file path, inline string, or `-` for stdin) instead of fetching it from the API. Useful for offline workflows and integration testing. |
| `--output-json-projection` | `pull`, `init`, `branch switch` | Include the projection in the `--json` output, so it can be captured and fed into another command's `--from-projection`. |
| `--output-json-commands` | `push` | Add a `commands` array to the `--json` output, containing the serialized Agent Studio commands that were staged. Useful for dry-run review and integration testing. |

~~~bash
poly pull --from-projection - < projection.json
poly push --from-projection '{"topics": [...], ...}'
poly pull --json --output-json-projection | jq .projection > proj.json
poly push --json --dry-run --output-json-commands
~~~

## Related pages

- [Working locally](../development/working-locally.md) — the edit, push, and test loop these commands fit into
- [Resource reference](./resources.md) — the resources these commands operate on
