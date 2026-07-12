---
id: gnusto-0bf7.2
title: Bare 'wait' over-expands into many turns
type: task
priority: 3
created: '2026-07-11T14:37:34Z'
updated: '2026-07-12T00:33:37Z'
labels:
- harness
---

The bounded multi-step loop is good: 'wait for the elevator' correctly expanded to 4 waits and short-circuited the instant the doors opened. But a bare 'wait' (no 'until...' qualifier) also expanded to ~9 waits -- the model treats every wait as 'wait until something changes.' A qualifier-free wait should probably be a single turn. Tune the parse/loop prompt so unqualified waits do not auto-repeat.
