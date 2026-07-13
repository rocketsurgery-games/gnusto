---
id: gnusto-0bf7.8
title: '''unknown'' reason sentinel leaks into player output/debug for blocked event
  results'
type: task
priority: 2
created: '2026-07-13T04:24:38Z'
updated: '2026-07-13T04:26:06Z'
labels:
- bug
---

---
▸ 2026-07-13T04:24:45Z
Found via the grue-death playthrough. _eval_blocked forces reason='unknown' (reason codes deprecated). A blocked EVENT fires as a runtime.ActionResult (not the repl ActionBlocked type), so in _blocks_from_results it falls through the ActionBlocked branch to the success-like path, which emits result.reason as prose -> the player sees a spurious 'unknown' line before the real death text (which correctly comes from context['description']). Same sentinel shows as 'description: unknown' in the compact debug formatter. Fix: don't emit the 'unknown' sentinel as text (guard reason != 'unknown') in _blocks_from_results and the two debug spots.

---
▸ 2026-07-13T04:26:06Z
FIXED. Guarded reason != 'unknown' in _blocks_from_results (player output) and the two _format_compact_debug spots (ActionDone + event ActionResult). Regression test test_blocked_event_reason_sentinel_not_leaked in tests/gnusto/test_parse_only_blocks.py. Verified via harness: the grue death now prints only 'Oh, no! ... grue!' with no leading 'unknown'. 814 pytest green.
