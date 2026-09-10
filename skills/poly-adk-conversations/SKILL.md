---
name: poly-adk-conversations
description: >
  This skill should be used when the user wants to "see what happened on a call",
  "review real conversations", "download a call recording", "debug a production call",
  or "add logging/metrics" to a PolyAI agent. Covers poly conversations and instrumenting
  functions with conv.log and metrics. Part of the PolyAI ADK skills suite. Do NOT use
  for simulated test conversations (use poly-adk-testing).
metadata:
  author: PolyAI
  license: Apache-2.0
  version: 0.53.1
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
- The CLI reads individual conversations. Aggregate views — containment, CSAT, handle time, flagged transcripts — live in Agent Studio, not the CLI.

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

1. `poly conversations get <id>` — read the transcript and logs turn by turn.
2. If the wording is right but the *audio* is wrong, it's a channel-settings problem, not a prompt problem: mishearing → `voice/speech_recognition/` (keyphrase boosting, transcript corrections); mispronunciation → `voice/response_control/` (pronunciations). See `poly docs speech_recognition response_control`.
3. Reproduce with `poly chat` (simulate SIP headers, variant, language — see `poly-adk-testing`), then encode the fix's verification as a test case.
