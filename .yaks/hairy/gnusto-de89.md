---
id: gnusto-de89
title: 'Layer 4.1: cone-of-influence projection (first proven abstraction layer)'
type: task
priority: 2
created: '2026-09-14T03:43:51Z'
updated: '2026-09-14T03:43:51Z'
parent: gnusto-266.5
depends_on:
- gnusto-266.5.2
labels:
- tooling
---

Land section 4.1 of docs/design/state-graph-kernel.md: the first PROVEN abstraction layer over the concrete kernel.

WHAT: drop every state variable not transitively read by a transition guard or by the goal predicate. SOUND because an untracked variable cannot influence any tracked transition or the goal -- it is a bisimulation w.r.t. the tracked set. This is the rigorous version of the old explorer's 'tracked refs', and the fix for where it went wrong (it projected too aggressively and collapsed non-bisimilar states -> false NO; see gnusto-otr.12 defect B).

WHY FIRST: it is not merely an optimization, it is what makes the state space finite at all. The engine writes @player:moves on every successful action, so the raw concrete space is infinite. kernel.BOOKKEEPING_PROPS is the hand-coded degenerate case that this layer generalizes.

INPUT: frotz.effects now gives a complete reads/modifies relation (gnusto-otr.13), so the dependency closure is computable statically: seed with the vars read by the goal, then close under 'vars read by any guard of a behavior that modifies a var already in the set', to fixpoint.

ACCEPTANCE:
1. A written soundness argument in the design doc (the bisimulation obligation, discharged).
2. differential() against the kernel over all 8 corpus games in tests/frotz/corpus.py reports ZERO unsound disagreements. Over-approximation is allowed; a false NO is not.
3. BOOKKEEPING_PROPS falls out as a computed result rather than a hand-coded constant.
4. Measured state-count reduction on Mini, and on as much of Zork as finishes (baseline: 2000-state cap in ~42s without finishing).
