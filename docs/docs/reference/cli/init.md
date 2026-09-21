---
title: poly init
description: Reference for the `poly init` command.
---

# `poly init`

Initialize a new Agent Studio project locally.

Examples:

~~~bash
poly init
poly init --account_id 123 --project_id my_project
poly init --region us-1 --account_id 123 --project_id my_project
poly init --base-path /path/to/projects
poly init --format
~~~

Run with no arguments and `poly init` walks you through interactive dropdowns:

1. **Region** — auto-selected if your API key only has access to one.
2. **Account** — auto-selected if there's only one in the region; otherwise pick from a searchable list. Each entry is shown as `"name (id)"` to disambiguate accounts that share the same display name.
3. **Project** — pick from a searchable list of every project the API key can see. Each entry is shown as `"name (id)"` for the same reason.

If no projects are found in the selected account, `poly init` offers to create one. Accepting the prompt starts the [`poly project create`](./project.md#poly-project-create) flow with the region and account already pre-selected.

After selection, `poly init` creates the project directory at `{base_path}/{account_id}/{project_id}` and immediately pulls the current configuration from Agent Studio. Change into the project directory before running any other commands.

The human-readable project name is stored in `project.yaml` alongside the `project_id`, `account_id`, and `region`:

~~~yaml
project_id: my-project
account_id: my-workspace
region: us-1
project_name: My Project
~~~

Pass any combination of `--region`, `--account_id`, and `--project_id` to skip the matching prompt. This is the form to use in scripts and CI.

| Flag | Description |
|---|---|
| `--base-path` | Base path to initialize the project. Defaults to the current working directory. |
| `--region` | Region for the Agent Studio project. One of `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |
| `--account_id` | Account ID for the Agent Studio project. |
| `--project_id` | Project ID for the Agent Studio project. |
| `--format` | Format resources after init. |

!!! info "`--json` requires explicit flags for `poly init`"

    When using `poly init --json`, you must supply `--region`, `--account_id`, and `--project_id` explicitly. Interactive prompts are not supported in JSON mode.

`--json` output shape:

~~~json
{
  "success": true,
  "root_path": "/path/to/projects/my-workspace/my-project"
}
~~~
