---
title: Custom metrics
description: Define and manage the custom metrics an agent writes to, with poly metrics list, add, edit, export, and import.
---

# Custom metrics

Custom metrics are the named counters and values a project records against its conversations — how often a booking completed, what reason a caller gave, whether a handoff fired. They come in two halves:

- **The definition** — the metric's name, type, and description, managed with `poly metrics`.
- **The value** — written during a call from function code with `conv.write_metric(...)`, covered in [observability](./observability.md).

This page is about the first half. A definition on its own records nothing; a metric only becomes useful once a function writes to it.

Metrics are defined per project. They are not branched, not stored in the local resource tree, and not promoted through the deployment ladder — `poly metrics add` and `poly metrics edit` take effect for the whole project straight away, with no push step.

!!! warning "Metric changes apply immediately and to every environment"

    There is no branch to review the change on and no sandbox copy to try it in first. Editing a metric that live calls are already writing to changes it everywhere at once.

## What a metric holds

| Field | Description |
|---|---|
| Name | `SCREAMING_SNAKE_CASE` identifier, matching what `conv.write_metric` writes to. Fixed once created. |
| Type | `string`, `int`, `bool`, or `float`. Fixed once created. |
| Description | What the metric records, for whoever reads it later. |
| API | Marks the metric as an API metric. |
| Active | Whether the metric is in use. |
| Expected values | For `string` metrics, the set of values to expect. |

Name and type cannot be changed after creation, so they are worth getting right first time. Everything else can be edited later.

## Working with metrics

~~~bash
poly metrics list                                   # see what already exists
poly metrics add --name BOOKING_CONFIRMED --type bool
poly metrics edit BOOKING_CONFIRMED --description 'Caller completed a booking'
~~~

Run `poly metrics list` before adding anything. Metrics accumulate, and the common failure is a second near-duplicate of a metric that already exists under a slightly different name.

Omitting the flags on `add` or `edit` drops into an interactive prompt instead — useful when you are creating a metric by hand rather than scripting it.

!!! tip "Define the metric before instrumenting the function"

    Adding the metric first means the name is settled before it is hard-coded into a function. Renaming later means editing every `conv.write_metric` call that used the old name, because the name itself cannot be edited.

## Retiring a metric

There is no delete. To retire a metric, deactivate it:

~~~bash
poly metrics edit BOOKING_CONFIRMED --active false
~~~

This keeps the historical data and the definition intact, which is what you want for a metric that has already been written to — deleting it would orphan everything recorded against it.

## Moving metrics between projects

`export` and `import` are the way to carry a metric set from one project to another, or to keep a copy in version control alongside the agent:

~~~bash
poly metrics export metrics.yaml     # from the source project
poly metrics import metrics.yaml     # from the target project
~~~

The file is keyed by metric name:

~~~yaml
BOOKING_CONFIRMED:
  type: bool
  description: Caller completed a booking
CALL_REASON:
  type: string
  description: Reason the caller gave
~~~

Import only ever creates. A metric already present in the target project is skipped rather than updated, and a metric that exists remotely but is missing from the file is reported and left alone. That makes import safe to re-run, but it also means it is not a sync — editing an exported file and re-importing it will not change the metrics that already exist.

Use `--dry-run` first to see what a file would create before it creates it:

~~~bash
poly metrics import metrics.yaml --dry-run
~~~

Every flag for these commands is in the [CLI reference](../reference/cli/metrics.md).

## Related pages

- [Observability](./observability.md) — writing metrics and logs from function code, and inspecting real calls
- [Functions](../reference/resources/functions.md) — the `conv.write_metric` API these definitions back
