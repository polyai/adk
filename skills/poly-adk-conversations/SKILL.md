---
name: poly-adk-conversations
description: >
  This skill should be used when the user wants to "see what happened on a call",
  "review real conversations", "download a call recording", "debug a production call",
  "what was our Poly Score last week", "find calls where callers said X", "how many
  conversations handed off", or "add logging/metrics" to a PolyAI agent. Covers
  poly conversations, poly transcripts, reading metric values with poly metrics, and
  instrumenting functions with conv.log and metrics. Part of the PolyAI ADK skills suite.
  Do NOT use for simulated test conversations (use poly-adk-testing).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.64.0
  requires:
    bins:
      - poly
    install: "uv tool install polyai-adk"
---

# Reviewing Real Conversations

Load `poly-adk-workflow` first for the build loop this feeds back into. Once an agent handles real calls, the question becomes "what happened on that call?" — and answering it depends on instrumentation added *while building*. Logs and metrics are not available retroactively.

## Inspecting conversations

```bash
poly conversations list                        # recent conversations: ID, start, duration, caller, channel, variant, handoff, summary
poly conversations list --limit 20 --offset 10
poly conversations get <conversation_id>       # full metadata + turn-by-turn transcript
poly conversations get-audio <conversation_id> -o recording.wav
```

- `get` includes channel, language, duration, handoff, tags, PolyScore, summary, and every turn — use `--json` when analyzing programmatically.
- `get-audio` downloads the WAV for a voice call; `--direction user|agent|combined` picks the track, `--redacted` fetches the redacted version.
- For aggregate numbers (Poly Score over time, handoff rate, CSAT), searching by metric values, or searching what callers said, use the Data API commands below rather than paging through `list`.

## Reading metrics and transcripts

These commands read the project's conversation data through the Data API. They need no push and work on live traffic. Every one of them accepts `--json`, `--from DATE` / `--to DATE` (a bare date for `--to` includes the whole day), and pages with `--limit` (max 100) / `--offset` — never loop to fetch everything, the API allows 100 requests a minute per key.

```bash
poly metrics available                                   # which metrics you can read: built-in (poly_score, duration, handoff, …) plus custom
poly metrics score                                       # Poly Score: headline average + daily table, last 7 days
poly metrics score --interval weekly --by channel        # weekly, split by channel
poly metrics query <metric> --agg avg --agg p95 --interval daily --by channel --filter handoff eq true
poly conversations search --filter poly_score lt 3 --env live --field call_summary
poly transcripts search "cancel my booking" --context 2  # what callers said, with surrounding turns
poly transcripts get <conversation_id>                   # full transcript with timestamps
```

- `poly metrics list` is **definitions** (the custom metrics the project declares). `poly metrics available` is **what you can query**, built-ins included. Metric names are case-insensitive; take them from `available` before filtering or aggregating.
- `--filter METRIC OP VALUE` is repeatable; `OP` is `eq gt gte lt lte in ex contains not_contains exists` (`in`/`ex` take a comma-separated list). `--any` turns the filters into OR. On `conversations search`, `METRIC` may also be `conversation_id` (fetch specific conversations' metrics) or `CUSTOM_SCORE_<id>` (an AI Score, 1 to 5).
- `metrics query` output is a table: `bucket` (when `--interval` is set), the `--by` dimensions, then one column per `--agg`. `--having avg lt 3` keeps only buckets past a threshold.
- Transcripts and the free-text fields (`call_summary`, the `poly_score_*_summary` reasoning) are PII. `transcripts search`/`get` return 403 without PII read permission on the key; `conversations search` succeeds but leaves those fields out and the CLI says so. Tell the user to grant PII read on the API key in Agent Studio; do not retry.
- Restrict to real traffic with `--env live`; test calls and sandbox runs skew every average.

**Worked example — "what was our Poly Score last week, and which channel is dragging it down?"**

```bash
poly metrics score --from 2026-09-28 --to 2026-10-04 --by channel --env live
```

Read the headline line for the overall average, then compare the `avg` column per `channel` row. To see the worst conversations behind a low channel:

```bash
poly conversations search --from 2026-09-28 --to 2026-10-04 --filter poly_score lt 3 --channel VOICE-SIP --env live --field call_summary --sort duration:desc
poly transcripts get <conversation_id>     # pick an ID from the table
```

**Worked example — "are callers asking for a human, and where?"**

```bash
poly transcripts search "speak to a human" --from 2026-09-01 --context 1
```

Each result is one conversation with the matching turn and a turn either side. To quantify it rather than read it, count the handoffs in the same window and bucket by day:

```bash
poly metrics query handoff --agg conversation_count --from 2026-09-01 --interval daily --filter handoff eq true
```

A phrase that keeps appearing in `transcripts search` is a candidate for a new `test_suite/` case (see `poly-adk-testing`) or a flow change.

Treat what you find as input to development: a surprising real conversation is the raw material for the next `test_suite/` case (see `poly-adk-testing`). What callers actually say is reliably different from what you imagined.

## Instrumenting functions

See `poly docs functions` for the full `conv.log` and metrics APIs.

**Logging** — record meaningful outcomes, not every step:

```python
conv.log.info("Booking confirmed", reference=booking_ref)
conv.log.warning("Availability API slow, using cached slots")
conv.log.error("Payment provider returned 500")
```

Log around the things that can fail — API calls, validation, any branch you'd want to explain later. **Never swallow an external failure silently**: a bare `except` with no log turns a broken integration into a mysteriously unhelpful agent with nothing in the transcript to explain it.

**Metrics** — count outcomes you'll aggregate across calls (flow completions, handoffs fired, API fallbacks). The common mistake is inflation: a metric emitted in a loop or on every turn counts nothing useful. Use `write_once=True` for once-per-conversation events, and emit on the outcome you actually want to count.

The test for both: would this line help answer a question you can imagine being asked — "how often do callers abandon at payment?", "did that transfer actually fire?" If not, it's noise.

## When debugging a specific call

1. `poly conversations get <id>` — read the metadata, logs and transcript; `poly transcripts get <id>` for the timestamped transcript alone. If you only have a phrase the caller used, find the ID with `poly transcripts search "<phrase>"`.
2. If the wording is right but the *audio* is wrong, it's a channel-settings problem, not a prompt problem: mishearing → `voice/speech_recognition/` (keyphrase boosting, transcript corrections); mispronunciation → `voice/response_control/` (pronunciations). See `poly docs speech_recognition response_control`.
3. Reproduce with `poly chat` (simulate SIP headers, variant, language — see `poly-adk-testing`), then encode the fix's verification as a test case.
