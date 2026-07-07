---
id: gnusto-7256.1
title: 'P1: unified block-construction path + fix ordered-stream bug'
type: task
priority: 1
created: '2026-07-07T21:51:39Z'
updated: '2026-07-07T21:58:44Z'
labels:
- runtime
- render
---

Collapse the two drifting formatters into ONE 'raw engine results -> List[ContentBlock]' path, and derive the LLM-facing text by flattening those blocks (blocks_to_text). Fix the ordered-stream bug: render every text-bearing channel (output narrate/say, reason, and context message/description/response/hint/transition) IN ORDER across all results, deleting the fragile 'if not blocks' fallback in _blocks_from_results. Keep the ntr.28 examine->Focus enrichment. This handles TODAY's grue conventions (pre-migration) so it fixes the compulsion page drop + the never-rendered :transition/:hint immediately. Route full-agent's _eval_and_format text and parse-only's render blocks through the same construction.

---
▸ 2026-07-07T21:58:44Z
Done. _blocks_from_results is now THE single construction path (raw results -> ordered player-facing block stream); _blocks_to_text flattens it for the LLM. _eval_and_format derives LLM text from that flatten + a (blocked)/(error) status marker the player never sees; deleted the parallel _format_action_result. Fixed the ordered-stream bug: every text channel (output narrate/say, reason, ordered TEXT_CONTEXT_KEYS = message/description/response/hint/transition) renders in order across ALL results, no 'if not blocks' fallback. Fixes the compulsion page drop + never-rendered :transition/:hint. Verified: live parse-only examine renders once and in order; 757 passed, 6 skipped. New tests: multi-result ordering (compulsion repro), canonical context-key order, hint rendering, blocks_to_text flatten.
