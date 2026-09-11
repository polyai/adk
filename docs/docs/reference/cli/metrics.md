---
title: poly metrics
description: Reference for the `poly metrics` command.
---

# `poly metrics`

Manage the custom metrics defined for a project, which functions access and write via `conv.write_metric(...)`. `poly metrics` requires a subcommand.

Metrics are defined per project, not per branch or environment. Creating, editing, or importing a metric takes effect immediately for the whole project; there is no push step and nothing is written to the local resource tree.

A metric has a name in `SCREAMING_SNAKE_CASE`, a type (`string`, `int`, `bool`, or `float`), an optional description, an `api` flag marking it as an API metric, and an `active` flag. String metrics can also carry a list of expected values.

## `poly metrics list`

Show every custom metric in a table, with a count of active and inactive metrics.

Examples:

~~~bash
poly metrics list
poly metrics list --json
~~~

`--json` output shape:

~~~json
[
  {
    "name": "BOOKING_CONFIRMED",
    "type": "bool",
    "active": true,
    "api": false,
    "description": "Caller completed a booking"
  }
]
~~~

## `poly metrics export`

Export every metric definition as YAML, to a file or to stdout.

Examples:

To YAML:
~~~bash
poly metrics export metrics.yaml
~~~
To stdout:
~~~bash
poly metrics export
~~~

The YAML is keyed by metric name, and is the same shape [`poly metrics import`](#poly-metrics-import) reads:

~~~yaml
BOOKING_CONFIRMED:
  type: bool
  description: Caller completed a booking
~~~

| Argument | Description |
|---|---|
| `file` | Output file path. Prints to stdout when omitted. |

`--json` output shape:

~~~json
{
  "BOOKING_CONFIRMED": {
    "type": "bool",
    "description": "Caller completed a booking"
  }
}
~~~

## `poly metrics add`

Create a new metric. Any required field left off the command line is prompted for interactively.

Examples:

~~~bash
poly metrics add --name BOOKING_CONFIRMED --type bool
poly metrics add --name CALL_REASON --type string --expected-values booking cancellation enquiry
poly metrics add
~~~

| Flag | Description |
|---|---|
| `--name` | Metric name. Prompted for when omitted. |
| `--type` | Metric value type. Choices: `string`, `int`, `bool`, `float`. Prompted for when omitted. |
| `--description` | Description of what the metric records. |
| `--api` | Mark the metric as an API metric. |
| `--expected-values` | Space-separated list of expected values. Only valid for `string` metrics. |

!!! info "`--json` requires `--name` and `--type`"

    Interactive prompts are unavailable in JSON mode, so `poly metrics add --json` fails unless both flags are supplied.

`--json` output shape:

~~~json
{
  "success": true,
  "metric": {
    "name": "BOOKING_CONFIRMED",
    "type": "bool"
  }
}
~~~

## `poly metrics edit`

Update an existing metric. Passing no flags opens an interactive picker showing the metric's current values, so you can choose which fields to change.

Examples:

~~~bash
poly metrics edit BOOKING_CONFIRMED --description 'Caller completed a booking'
poly metrics edit BOOKING_CONFIRMED --active false
poly metrics edit CALL_REASON --expected-values booking cancellation
poly metrics edit BOOKING_CONFIRMED
~~~

A metric's name and type cannot be changed after creation.

| Argument | Description |
|---|---|
| `name` | **Required.** Name of the metric to edit. |

| Flag | Description |
|---|---|
| `--description` | New description for the metric. |
| `--api` | Set the API flag. Takes `true`/`false`; omit the value to set `true`. |
| `--active` | Set the active state. Takes `true`/`false`; omit the value to set `true`. |
| `--expected-values` | Space-separated list of expected values. Only valid for `string` metrics. |

!!! info "`--json` needs at least one flag"

    The interactive picker cannot run in JSON mode, so `poly metrics edit --json` fails unless at least one field flag is passed.

`--json` output shape:

~~~json
{
  "success": true,
  "metric": {
    "name": "BOOKING_CONFIRMED",
    "active": false
  }
}
~~~

## `poly metrics import`

Bulk-create metrics from a YAML file in the format [`poly metrics export`](#poly-metrics-export) produces. Metrics that already exist are skipped rather than updated.

Examples:

~~~bash
poly metrics import metrics.yaml
poly metrics import metrics.yaml --dry-run
~~~

Import only ever adds. A metric that exists remotely but is absent from the file is reported and left alone — importing a trimmed-down file is not a way to delete metrics.

| Argument | Description |
|---|---|
| `file` | **Required.** Path to the YAML file to import. |

| Flag | Description |
|---|---|
| `--dry-run` | Report what would be created and skipped without making changes. |

`--json` output shape:

~~~json
{
  "success": true,
  "metadata": {
    "created": ["BOOKING_CONFIRMED"],
    "ignored": ["CALL_REASON"]
  },
  "remote_only": ["LEGACY_METRIC"]
}
~~~

With `--dry-run`, the output is `{"dry_run": true, "would_create": [], "would_skip": [], "remote_only": []}` instead.

## Related pages

- [Custom metrics](../../development/custom-metrics.md) — how defining metrics fits alongside writing them from function code
