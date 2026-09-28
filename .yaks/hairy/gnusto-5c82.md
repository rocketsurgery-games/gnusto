---
id: gnusto-5c82
title: 'Implement abstraction layer 4.1 cone-of-influence projection: drop vars no guard/goal transitively reads, differential-tested vs kernel'
type: task
priority: 2
created: '2026-09-28T16:34:56Z'
updated: '2026-09-28T16:35:41Z'
parent: gnusto-266.5
depends_on:
- gnusto-266.5.2
labels:
- tooling
---

---
▸ 2026-09-28T16:35:41Z [Joel Webber]
Scoping (not started). Layer 4.1 of the abstraction stack (docs/design/state-graph-kernel.md 4.1). Drop every state variable not transitively read by any transition guard or the goal predicate; the remaining projection is a bisimulation w.r.t. the tracked set, so goal-reachability is preserved exactly. This is the rigorous, computed generalization of kernel.BOOKKEEPING_PROPS (which hand-drops moves/score) and of the old explorers ad-hoc tracked-refs -- but sound this time. Dependency relation comes from the effect model (frotz.effects reads/modifies, now complete per otr.13). Validate with the 266.5.2 harness: differential vs kernel over the corpus must be exact (ok=True), especially the counter game (must not collapse the numeric gate) and the sealed/oneway negatives (must not manufacture reachability). This is where the OLD explorer went wrong (over-projected, false NO), so the corpus counter + sealed + oneway are the key regression probes.
