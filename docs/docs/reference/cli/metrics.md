---
title: poly metrics
description: Reference for the `poly metrics` command.
---

# `poly metrics`

Manage the custom metrics defined for a project, which functions access and write via `conv.write_metric(...)`, and read metric values — Poly Score included — through the Data API. `poly metrics` requires a subcommand.

Two kinds of subcommand live here. `list`, `export`, `add`, `edit` and `import` manage **definitions**. `available`, `query` and `score` read **values**: they call the Data API for the project's live conversation data, need no push, and page with `--limit` / `--offset` (the API allows 100 requests a minute per key).

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

## `poly metrics available`

Show every metric the project can query: built-in metrics such as `poly_score`, `duration` and `handoff`, plus the custom metrics defined in the project. These are the names `poly metrics query` and the `--filter` flags accept (case-insensitive).

Examples:

~~~bash
poly metrics available
poly metrics available --json
~~~

`--json` output shape:

~~~json
{
  "metrics": [
    { "name": "poly_score", "description": "...", "type": "float", "values": null }
  ],
  "total": 0
}
~~~

## `poly metrics query`

Aggregate one metric over a time window, optionally bucketed by interval and grouped by dimension. Backed by the Data API's aggregate endpoint, which is marked experimental by the service.

Examples:

~~~bash
poly metrics query poly_score --agg avg --from 2026-09-01 --to 2026-09-30
poly metrics query duration --agg avg --agg p95 --interval daily --by channel
poly metrics query CSAT --agg avg --filter channel eq VOICE-SIP --having avg gte 4
poly metrics query poly_score --agg conversation_count --by value_string --json
~~~

The table has one row per bucket and group: a `bucket` column when `--interval` is set, one column per `--by` dimension, then one column per `--agg`. Rows are sorted by bucket ascending, then by `--sort`.

| Argument | Description |
|---|---|
| `metric` | **Required.** Metric name from `poly metrics available` (case-insensitive). |

| Flag | Description |
|---|---|
| `--agg` | Aggregation to compute: `sum`, `avg`, `min`, `max`, `p50`, `p95`, `p99`, `conversation_count`, `distinct_count`. Repeatable. Defaults to `avg` and `conversation_count`. |
| `--from` | Inclusive window start, `YYYY-MM-DD` or an ISO 8601 datetime. Defaults to no lower bound. |
| `--to` | Exclusive window end. A bare date includes the whole of that day. |
| `--interval` | Time bucket: `hourly`, `daily`, `weekly`, `monthly`. Omit for one total. |
| `--timezone` | IANA timezone for hourly and daily buckets, e.g. `Europe/London`. |
| `--by` | Group by `project_id`, `channel`, `deployment_id`, `variant_id`, `client_env`, `experiment_id`, `experiment_version_id` or, for a string metric, `value_string`. Repeatable. |
| `--filter METRIC OP VALUE` | Only count conversations where the condition holds. `OP` is `eq`, `gt`, `gte`, `lt`, `lte`, `in`, `ex`, `exists`; `in`/`ex` take a comma-separated list. Repeatable. |
| `--any` | Match conversations that satisfy any `--filter` instead of all. |
| `--having AGG OP VALUE` | Keep only buckets where the aggregate passes the threshold, e.g. `--having avg gte 4`. Repeatable. |
| `--channel` | Restrict to a channel: `VOICE-SIP`, `CHAT`, `WEBCHAT`, `SMS`, `RCS`. Repeatable. |
| `--env` | Restrict to an environment: `test`, `sandbox`, `pre-release` (Staging), `live`, `scenarios`. Repeatable. |
| `--deployment`, `--variant` | Restrict to deployment or variant IDs. Repeatable. |
| `--sort FIELD[:asc\|desc]` | Secondary sort on a `--by` dimension or an aggregation. |
| `--limit`, `--offset` | Rows per page (1 to 100, default 20) and rows to skip (up to 1000). |

`--json` output shape:

~~~json
{
  "columns": ["bucket", "channel", "avg", "conversation_count"],
  "rows": [["2026-09-01T00:00:00Z", "VOICE-SIP", 4.21, 318]],
  "limit": 20,
  "offset": 0
}
~~~

## `poly metrics score`

Poly Score for the project: a one-line headline (conversation-weighted average and total count over the window) above the bucketed table. Shortcut for `poly metrics query poly_score --agg avg --agg conversation_count`, defaulting to the last 7 days bucketed daily.

Examples:

~~~bash
poly metrics score
poly metrics score --interval weekly --from 2026-09-01
poly metrics score --by channel --env live
poly metrics score --json
~~~

| Flag | Description |
|---|---|
| `--from`, `--to` | Window bounds as for `query`. Defaults to the last 7 days. |
| `--interval` | Time bucket. Defaults to `daily`. |
| `--timezone` | IANA timezone for hourly and daily buckets. |
| `--by` | Group by a dimension, as for `query`. Repeatable. |
| `--channel`, `--env` | Restrict to channels or environments, as for `query`. Repeatable. |
| `--limit`, `--offset` | Rows per page and rows to skip. |

`--json` output shape:

~~~json
{
  "columns": ["bucket", "avg", "conversation_count"],
  "rows": [["2026-09-28T00:00:00Z", 4.35, 290]],
  "limit": 20,
  "offset": 0,
  "summary": { "average": 4.3, "conversations": 2012, "text": "Poly Score from 2026-09-28 to 2026-10-04: 4.3 average over 2,012 conversations." }
}
~~~

!!! info "Permissions"
    `available`, `query` and `score` need an API key with read permission on conversations. They return no PII, so PII read permission is not required.

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
