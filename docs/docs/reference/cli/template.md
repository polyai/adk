---
title: poly template
description: Reference for the `poly template` command.
---

# `poly template`

Browse and load example project templates. `poly template` requires a subcommand:

Examples:

~~~bash
poly template list
poly template load restaurant-booking
~~~

## `poly template list`

List the example templates available for a region.

Examples:

~~~bash
poly template list
poly template list --region us-1
~~~

| Flag | Description |
|---|---|
| `--region` | Region to query for templates. Defaults to the current project's region. Choices: `us-1`, `euw-1`, `uk-1`, `studio`, `staging`, `dev`. |

`--json` output shape:

~~~json
{
  "success": true,
  "templates": []
}
~~~

## `poly template load`

Load a template into the current project. Omit the name to get an interactive picker.

Examples:

~~~bash
poly template load
poly template load restaurant-booking
poly template load restaurant-booking --force
~~~

| Argument | Description |
|---|---|
| `template_name` | Name of the template to load. If omitted, an interactive picker is shown. |

| Flag | Description |
|---|---|
| `--region` | Region to load the template from. Defaults to the current project's region. |
| `--force`, `-f` | Skip the confirmation prompt. |

!!! info "`--json` requires `template_name`"

    The interactive picker isn't available with `--json`. Omitting `template_name` fails with an error instead of prompting.

!!! warning "Loading a template overwrites local resources"

    `poly template load` replaces your local project resources with the template contents. Push or back up any local work you want to keep before loading.

Template resources are written to disk without updating the tracked state, so the loaded change will appear as changes to your project and will need to be pushed up to affect the remote state.

`poly project create` offers to load a template once a new project exists, so you do not need to run this separately when starting from scratch.

`--json` output shape:

~~~json
{
  "success": true,
  "template": "restaurant-booking"
}
~~~
