---
id: gnusto-ntr.31
title: 'Parse-only: text-free sense-act loop (short-circuit + bounded continuation)'
type: feature
priority: 1
created: '2026-07-06T05:13:16Z'
updated: '2026-07-06T05:16:27Z'
labels:
- runtime
- agent
---

Parse-only has been strictly one-shot since fe65e98: it executes the model's whole action batch blindly (no short-circuit on ActionBlocked/Error) then breaks after one iteration, never feeding results/state back. Symptoms: (1) plows through login+password after login is blocked; (2) gives up after one turn, must be told to continue. Full-agent has the feedback loop; parse-only never did.

Give parse-only a text-free sense-act loop (engine still owns ALL text):
- SHORT-CIRCUIT (fork A): stop executing a response's batch at the first blocked/error result; re-plan from the real post-block state.
- FEEDBACK LOOP: append engine results + updated state and re-invoke, using response.needs_player_input as the stop signal (parse-only now honors it AFTER executing).
- BOUNDED CONTINUATION (fork B, aggressive-but-bounded): (a) max_iterations hard cap; (b) rewrite PARSING_ONLY_PROMPT for continuation + stop criteria + scope bound (pursue concrete requested actions incl. obvious prerequisites; set needs_player_input for open-ended exploration/puzzle-solving; don't batch dependent actions); (c) repeated-block guard: same (target,verb,args) blocking twice -> stop.

Scope: parse-only only; full-agent path unchanged. No model-authored text.

---
▸ 2026-07-06T05:16:27Z
Implemented + verified live. process_input parse-only path is now a text-free sense-act loop: (A) short-circuit — the batch stops at the first ActionBlocked/ActionError (raw_results[0]) so the model re-plans from real post-block state; (B) feedback — appends engine results + updated state each iteration and re-invokes, honoring response.needs_player_input AFTER executing as the stop signal; (C) bounds — max_iterations hard cap + repeated-block guard (_action_key seen twice -> stop). Rewrote PARSING_ONLY_PROMPT: continuation semantics, do-prerequisites, don't-batch-dependent-actions, and a scope bound (carry out the concrete request incl. obvious prerequisites; set needs_player_input for open-ended exploration/puzzle-solving — don't try to win the game). Full-agent path untouched. Live --parse-only run of 'sit and log in to work on the paper': single turn did sit-at -> turn-on (self-supplied prerequisite) -> login -> password -> clicked into the paper editor; no fabrication, no 'keep trying' needed. New test_parse_only_loop.py (5 cases: short-circuit, npi-stop, multi-step continuation, repeated-block guard, max_iterations). Suite: 753 passed, 6 skipped.
