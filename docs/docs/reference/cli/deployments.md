---
title: poly deployments
description: Reference for the `poly deployments` command.
---

# `poly deployments`

Manage deployments for the project. `poly deployments` requires a subcommand.

## `poly deployments list`

List deployments for the project.

Examples:

~~~bash
poly deployments list
poly deployments list --env live
poly deployments list --details
poly deployments list --limit 10
~~~

By default shows all deployments. Pass `--limit` to cap the number of entries shown. Long listings are automatically paged through the system pager when stdout is a TTY; output piped to a file or another command is never paged.

| Flag | Description |
|---|---|
| `--env`, `-e` | Environment to list. Choices: `sandbox`, `pre-release`, `live`. Defaults to `live` for projects using simplified deployments, otherwise `sandbox`. |
| `--limit` | Maximum number of versions to show. Shows all by default. |
| `--offset` | Number of versions to skip. Defaults to `0`. |
| `--hash` | Hash of the version to start listing from. Overrides `--offset`. |
| `--details` | Output each deployment with detailed information. |

!!! tip "Use `--details` for readable output"

    The default tabular view may wrap long URLs across multiple rows, making it unreadable in narrow terminals. `--details` produces a vertical layout that is easier to read.

`--json` output shape:

~~~json
{
  "versions": [],
  "active_deployment_hashes": {}
}
~~~

## `poly deployments show`

Show detailed metadata and included deployments for a specific version.

Examples:

~~~bash
poly deployments show abc123def
poly deployments show abc123def --env live
~~~

| Argument | Description |
|---|---|
| `hash` | Version hash (or prefix) of the deployment to show. |

| Flag | Description |
|---|---|
| `--env`, `-e` | Environment to query. Choices: `sandbox`, `pre-release`, `live`. Defaults to `sandbox`|

Sandbox is the source of truth for the linear version history — pre-release and live promotions carry the same version hashes forward.

When you set an `--env` other than sandbox, it shows the included deployments between that deployment and the previous one. Use this for auditing what changes were included.

`--json` output shape:

~~~json
{
  "success": true,
  "deployment": {},
  "active_deployment_hashes": {},
  "included_deployments": [],
  "is_rollback": false
}
~~~

## `poly deployments promote`

Promote a deployment to the next environment (`pre-release` or `live`).

Deployments must go up the chain. `sandbox` -> `pre-release` -> `live`

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
| `--dry-run` | Show what would be promoted without actually promoting. Displays the deployment hash, target environment, and included changes. |

When promoting to `live`, the command searches for the deployment in `pre-release` and uses sandbox as the linear history source for computing included changes. When promoting to `pre-release`, it searches sandbox.

Without `--force`, the command prompts for confirmation before proceeding and optionally allows you to enter or override the deployment message interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "to_env": "pre-release",
  "from_hash": "abc123def...",
  "message": "",
  "included_deployments": []
}
~~~

Adds `"dry_run": true` instead of pushing changes when `--dry-run` is passed.

## `poly deployments rollback`

Roll back to a previous deployment version in the `sandbox` environment.

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

Without `--force`, the command prompts for confirmation before proceeding.

`--json` output shape:

~~~json
{
  "success": true,
  "target_hash": "abc123def...",
  "message": "",
  "reverted_deployments": []
}
~~~

Adds `"dry_run": true` instead of rolling back when `--dry-run` is passed.

## `poly deployments ab-test`

Manage A/B tests for live deployments, on the classic deployment model — projects using simplified deployments use [`poly deployments experiment`](#poly-deployments-experiment) instead. `poly deployments ab-test` requires a subcommand.

`ab-test end` is the one exception and works on either deployment model: experiments and classic A/B tests share the same underlying record, so a test started before a project adopted simplified deployments can still be left active afterward, with no other way to close it out.

### `poly deployments ab-test start`

Start a new A/B test against the current live deployment. The variant must be a `pre-release` deployment with a version different from the current live deployment.

Examples:

~~~bash
poly deployments ab-test start --name 'v2 test' --variant-version <hash> --traffic 50
~~~

| Flag | Description |
|---|---|
| `--name`, `-n` | Name/label for the A/B test. If omitted, prompts interactively. |
| `--variant-version` | Version hash of the pre-release variant. If omitted, prompts interactively. |
| `--traffic` | Percentage of traffic to route to the variant (0-100). Defaults to 50 interactively. |

!!! info "All flags are required with `--json`"

    `--name`, `--variant-version`, and `--traffic` must all be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "ab_test": {}
}
~~~

### `poly deployments ab-test list`

List A/B tests for the project.

Examples:

~~~bash
poly deployments ab-test list
poly deployments ab-test list --limit 20
~~~

| Flag | Description |
|---|---|
| `--limit` | Number of A/B tests to show. Defaults to `10`. |

`--json` output shape:

~~~json
{
  "success": true,
  "ab_tests": []
}
~~~

### `poly deployments ab-test active`

Show the currently active A/B test, if any.

Examples:

~~~bash
poly deployments ab-test active
~~~

`--json` output shape:

~~~json
{
  "success": true,
  "ab_test": null
}
~~~

### `poly deployments ab-test update`

Update the traffic split for the active A/B test.

Examples:

~~~bash
poly deployments ab-test update --traffic 30
~~~

| Flag | Description |
|---|---|
| `--traffic` | New percentage of traffic to route to the variant (0-100). Prompts if omitted. |

!!! info "`--traffic` is required with `--json`"

    `--traffic` must be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "ab_test": {}
}
~~~

Adds `"unchanged": true` instead of updating when `--traffic` matches the current split.

### `poly deployments ab-test end`

End the active A/B test and choose which deployment wins. If the variant wins, it is automatically promoted to `live`. Works on either deployment model — see [`poly deployments ab-test`](#poly-deployments-ab-test) above.

Examples:

~~~bash
poly deployments ab-test end --chosen-version <hash>
poly deployments ab-test end
~~~

| Flag | Description |
|---|---|
| `--chosen-version` | Version hash of the deployment to keep as winner. If omitted, an interactive prompt shows the control and variant deployments for selection. |

!!! info "`--chosen-version` is required with `--json`"

    `--chosen-version` must be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "ab_test": {},
  "promoted": false
}
~~~

If promoting the winning variant to `live` fails after the test has already ended, `"promoted"` is `false` and a `"promote_error"` key is added instead.

## `poly deployments experiment`

Manage experiments for projects using the simplified deployment model, testing a top-level branch against the current live version. Only one experiment can run at a time, with a single variant, today. `poly deployments experiment` requires a subcommand.

### `poly deployments experiment start`

Start a new experiment against the current live version. `main` is always the implicit control.

Examples:

~~~bash
poly deployments experiment start --name 'v2 test' --branch my-branch --traffic 50
~~~

The variant must be a top-level branch (a direct child of `main`) that isn't diverged from it — sync a stale branch with its parent first.

| Flag | Description |
|---|---|
| `--name`, `-n` | Name/label for the experiment. If omitted, prompts interactively. |
| `--branch` | Name of the top-level branch to test as the variant. If omitted, prompts interactively. |
| `--traffic` | Percentage of traffic to route to the variant (1-99). Defaults to 50 interactively. |

!!! info "All flags are required with `--json`"

    `--name`, `--branch`, and `--traffic` must all be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "experiment": {}
}
~~~

### `poly deployments experiment list`

List experiments for the project.

Examples:

~~~bash
poly deployments experiment list
poly deployments experiment list --limit 20
poly deployments experiment list --offset 10
~~~

| Flag | Description |
|---|---|
| `--limit` | Number of experiments to show. Defaults to `10`. |
| `--offset` | Number of experiments to skip before showing results. |

`--json` output shape:

~~~json
{
  "success": true,
  "experiments": []
}
~~~

### `poly deployments experiment active`

Show the currently active experiment, if any.

Examples:

~~~bash
poly deployments experiment active
~~~

`--json` output shape:

~~~json
{
  "success": true,
  "experiment": null
}
~~~

### `poly deployments experiment update`

Update the name and/or traffic split for the active experiment. At least one of `--name` or `--traffic` must be given.

Examples:

~~~bash
poly deployments experiment update --traffic 30
poly deployments experiment update --name 'v3 test'
~~~

| Flag | Description |
|---|---|
| `--name`, `-n` | New name for the experiment. |
| `--traffic` | New percentage of traffic to route to the variant (1-99). Prompts if omitted. |

!!! info "At least one of `--name` or `--traffic` is required with `--json`"

    One of them must be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "experiment": {}
}
~~~

### `poly deployments experiment end`

End the active experiment and choose which branch wins. Unlike [`poly deployments ab-test end`](#poly-deployments-ab-test-end), the platform redeploys the winning branch to `live` automatically — no separate promotion step.

Examples:

~~~bash
poly deployments experiment end --chosen-branch my-branch
poly deployments experiment end
~~~

| Flag | Description |
|---|---|
| `--chosen-branch` | Name of the branch to keep as winner. If omitted, an interactive prompt shows the control and variant branches for selection. |

!!! info "`--chosen-branch` is required with `--json`"

    `--chosen-branch` must be passed explicitly when using `--json`, since interactive prompts aren't available non-interactively.

`--json` output shape:

~~~json
{
  "success": true,
  "experiment": {}
}
~~~

## Related pages

- [Environments and deployment](../../development/environments-and-deployment.md) — the sandbox → pre-release → live ladder these commands move a project through
