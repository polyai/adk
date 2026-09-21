---
title: Environments and deployment
description: How merged changes move through sandbox, pre-release, and live, and how to promote and roll back deployments with the PolyAI ADK.
---

# Environments and deployment

A project has three environments. Merged changes enter at `sandbox` and you promote them upwards.

| Environment | What it holds |
|---|---|
| `sandbox` | Everything merged into `main`, deployed automatically. Where you develop and test without affecting production. |
| `pre-release` | A candidate promoted from sandbox, for final checks. |
| `live` | Production. |

## Deploying your changes

Merging your branch updates `main`, which is deployed automatically to `sandbox`. No separate command is needed — see [merging changes](./branches-push-pull.md#merging-changes) for the merge itself.

Once you are happy with the changes to your agent, you promote them upwards with `poly deployments promote`:

~~~bash
poly deployments promote --from sandbox --to pre-release
poly deployments promote --from pre-release --to live
~~~

Promotion is a step at a time. `--to pre-release` promotes from sandbox and `--to live` promotes from pre-release, so nothing reaches production without having existed in pre-release first. You can promote whatever is currently active in an environment, or name a specific version if you need to.

Because a promotion moves an existing version rather than building a new one, what you verified in sandbox is what arrives in live.

`poly deployments list` and `poly deployments show` tell you what is deployed where, and `poly deployments rollback` returns an environment to an earlier version.

## Verify at each step

Each environment is a chance to check the change again before it goes further. `poly chat` and `poly test run` can both target a deployed environment rather than your branch, so the same tests you ran before merging can run against sandbox and again against pre-release. See [testing](./testing.md).

!!! tip "Promote with a dry run first"

    `poly deployments promote --dry-run` shows the version, the target environment, and the changes included, without promoting anything.

## Real-time configuration

Some configuration is managed per environment and takes effect without a deployment, outside this ladder entirely. That is handled by `poly rtc` — see [real-time configuration](./real-time-configuration.md).

Every flag for these commands is in the [CLI reference](../reference/cli/deployments.md).
