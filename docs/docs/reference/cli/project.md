---
title: poly project
description: Reference for the `poly project` command.
---

# `poly project`

Manage Agent Studio projects. `poly project` requires a subcommand.

## `poly project list`

List Agent Studio projects in an account.

Examples:

~~~bash
poly project list
poly project list --region us-1 --account_id my-account
~~~

Run with no arguments and `poly project list` walks you through interactive dropdowns for region and account, auto-selecting either one if there's only a single option.

| Flag | Description |
|---|---|
| `--region` | Region for the Agent Studio project. One of `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |
| `--account_id` | Account ID for the Agent Studio project. |

!!! info "`--json` requires explicit flags for `poly project list`"

    When using `poly project list --json`, you must supply `--region` and `--account_id` explicitly. Interactive prompts are not supported in JSON mode.

`--json` output shape:

~~~json
{
  "success": true,
  "agents": [
    {
      "project_id": "my-project",
      "agent_name": "My Project",
      "updated_at": "2026-08-01T12:00:00Z",
      "branch_count": 3
    }
  ]
}
~~~

## `poly project create`

Create a new Agent Studio project under an account, then initialize it locally.

Examples:

~~~bash
poly project create
poly project create --region us-1 --account_id my-account --name my-project
poly project create --region us-1 --account_id my-account --name "My Project" --id my-project
poly project create --region us-1 --account_id my-account --name my-project --greeting "Hi, how can I help?"
poly project create --base-path /path/to/projects
~~~

Run with no arguments and `poly project create` walks you through interactive prompts to select the project's region and account, then asks for a project name and (outside the `studio` region) an optional project ID.

If left empty, the project ID is auto-generated on the platform. Custom project IDs are only supported for enterprise accounts.

After the project is created in Agent Studio, `poly project create` automatically runs the same local initialization as [`poly init`](./init.md), pulling the new project's configuration into `{base_path}/{account_id}/{project_id}`.

| Flag | Description |
|---|---|
| `--base-path` | Base path to initialize the project. Defaults to the current working directory. |
| `--region` | Region for the new project. One of `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |
| `--account_id` | Account ID to create the project under. |
| `--name` | Display name for the new project. |
| `--id`, `--project_id` | Optional slug/ID for the project. If omitted, the platform generates one. |
| `--greeting` | Initial greeting message for the agent. Defaults to `"Hello, how can I help you?"`. |
| `--voice-id` | Voice ID for the agent. Defaults to a region-specific voice if not supplied. |

!!! info "`--json` requires explicit flags for `poly project create`"

    When using `poly project create --json`, you must supply `--region`, `--account_id`, and `--name` explicitly. Interactive prompts are not supported in JSON mode.

`--json` output shape (identical to [`poly init`](./init.md), since project creation finishes by initializing the project locally):

~~~json
{
  "success": true,
  "root_path": "/path/to/projects/my-account/my-project"
}
~~~

## `poly project delete`

Delete an Agent Studio project.

Examples:

~~~bash
poly project delete
poly project delete --region us-1 --account_id my-account --project_id my-project
~~~

Run with no arguments and `poly project delete` opens an interactive picker to select the project to delete. Any delete requires a confirmation step, which can be skipped with `--force`.

| Flag | Description |
|---|---|
| `--region` | Region of the project. One of `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |
| `--account_id` | Account ID the project exists under. |
| `--project_id` | Project ID to delete. |
| `-f`, `--force` | Skip the confirmation prompt. |

!!! warning "Deletion is permanent"

    Deleting a project cannot be undone.

!!! info "`--json` requires explicit flags for `poly project delete`"

    When using `poly project delete --json`, you must supply `--region`, `--account_id`, and `--project_id` explicitly. Interactive prompts are not supported in JSON mode, and the confirmation step is skipped automatically.

`--json` output shape:

~~~json
{
  "success": true,
  "project_id": "my-project"
}
~~~

## `poly project duplicate`

Duplicate an Agent Studio project into a new project on the same region.

Examples:

~~~bash
poly project duplicate
poly project duplicate --region us-1 --account_id my-account --project_id my-project --name my-copy
~~~

Run with no arguments and `poly project duplicate` walks you through interactive dropdowns for region and account, then a searchable list of projects to duplicate. It then prompts for a name for the copy (defaulting to `"<original name> (copy)"`) and an optional project ID for the copy.

`poly project duplicate` only calls the platform's duplicate API — unlike `poly project create`, it does **not** pull the new project down locally afterwards. Run [`poly init`](./init.md) against the new project ID to work on it locally.

| Flag | Description |
|---|---|
| `--region` | Region of the project. One of `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |
| `--account_id` | Account ID the project exists under. |
| `--project_id` | Project ID to duplicate. |
| `--name` | Name for the duplicated project. |
| `--id`, `--new_project_id` | Optional slug/ID for the new project. If omitted, the platform generates one. |

!!! info "`--json` requires explicit flags for `poly project duplicate`"

    When using `poly project duplicate --json`, you must supply `--region`, `--account_id`, `--project_id`, and `--name` explicitly. Interactive prompts are not supported in JSON mode.

`--json` output shape:

~~~json
{
  "success": true,
  "project_id": "my-copy",
  "agent_name": "my-copy"
}
~~~
