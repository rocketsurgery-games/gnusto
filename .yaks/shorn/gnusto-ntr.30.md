---
id: gnusto-ntr.30
title: Default model 404s (Sonnet 4 retired); LLM errors are swallowed silently
type: bug
priority: 1
created: '2026-07-04T17:51:13Z'
updated: '2026-07-04T17:54:57Z'
labels:
- runtime
- agent
- bug
---

ntr.28 restored the pre-c6a885c default anthropic/claude-sonnet-4-20250514, but that model now 404s (not_found) on the current API key — Sonnet 4 has been superseded by Sonnet 4.5. Probe on this account: claude-sonnet-4-5-20250929 OK, claude-sonnet-4-5 OK, claude-opus-4-5 OK, claude-haiku-4-5-20251001 OK; claude-sonnet-4-20250514 and claude-sonnet-4-0 FAIL. Compounding UX bug: GameSession.process_input catches the LLM exception and RETURNS an '[LLM error: ...]' string but never emits it via on_blocks, so the TUI/CLI show nothing (only LiteLLM's stderr hint). Fixes: (1) default -> claude-sonnet-4-5-20250929; update 'sonnet' alias, add 'opus'; (2) emit a SystemMessage(level=error) through on_blocks in the error path so failures are visible in TUI/CLI/web; (3) docs model IDs.

---
▸ 2026-07-04T17:54:57Z
Fixed, verified live. (1) Default model -> claude-sonnet-4-5-20250929 (Sonnet 4 retired/404 on this key); 'sonnet' alias updated, added 'opus' (claude-opus-4-5). (2) process_input now emits a SystemMessage(level=error) via on_blocks on LLM failure, so errors show in TUI/CLI/web instead of being swallowed. (3) Two structured-output schema fixes surfaced once errors were visible on Sonnet 4.5: every object now sets additionalProperties:false, and the deploy/beat enums use a scalar string type (nullable-union+enum was rejected). Added test_llm_schema.py (schema invariants). Live TUI run of the multi-step login now sequences correctly AND narrates faithfully: it relayed the 'turn on the computer first' block honestly ('screen remains dark'), then self-corrected (turn-on -> login -> password) and narrated real engine output. Suite: 746 passed, 6 skipped.
