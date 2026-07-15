---
id: gnusto-266.5
title: 'State-graph kernel restart: concrete reference oracle + layered sound abstraction'
type: task
priority: 2
created: '2026-07-15T03:32:22Z'
updated: '2026-07-15T03:32:33Z'
labels:
- tooling
---

---
▸ 2026-07-15T03:32:33Z
Ground-up restart of winnability/reachability analysis (supersedes explorer.py + deferred/). Built the reference KERNEL: src/frotz/kernel.py (concrete BFS oracle over the exact state graph) + games/mini/ (hand-enumerable fixture) + tests/frotz/test_kernel.py (5 tests) + docs/design/state-graph-kernel.md (the formal LTS, the layered sound-abstraction stack, correctness methodology).

Two lessons the kernel surfaced immediately: (1) 'fully concrete' is INFINITE -- the engine's move counter (@player:moves) grows unbounded, so the first sound reduction (cone-of-influence: drop vars no guard/goal reads) is mandatory just to be finite; kernel.BOOKKEEPING_PROPS is the hand-coded degenerate case. (2) permissive actions manufacture explosion -- allowing put into non-containers blew the 2-room game past 100k states; put must target containers/surfaces (matching the effect model). Scale post-fix: Mini=20 states instant; Zork hits a 2000-state cap in ~42s without finishing -> motivates the layers.

Abstraction stack (each = sound transformer + differential test vs kernel): 4.1 cone-of-influence projection (the rigorous 'tracked refs'; fixes the old over-aggressive collapse), 4.2 value-domain/numeric-interval abstraction (ties to 266.3, l8k, 81s), 4.3 reversibility/independence quotient (otr.14, reachability.py), 4.4 residual concrete search. Next proposed increment: a differential-test harness (kernel vs a layer over a corpus of tiny games), then land 4.1 as the first proven layer. explorer.py/deferred stay until parity, then hard-cutover.
