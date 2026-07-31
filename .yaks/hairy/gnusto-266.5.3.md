---
id: gnusto-266.5.3
title: 'Stronger differential check mode B: bisimulation verification of the abstraction
  map (per-corpus-game)'
type: task
priority: 3
created: '2026-07-31T03:45:50Z'
updated: '2026-07-31T03:46:04Z'
labels:
- tooling
depends_on:
- gnusto-266.5.2
---

---
▸ 2026-07-31T03:46:04Z
Comparison mode B (deferred; mode A first per user). WHAT: verify the abstraction map alpha: S_concrete -> S_abstract is a BISIMULATION on each tiny corpus game, not just that goal-reachability agrees. A bisimulation requires two directions: (1) every concrete transition s->s' has an abstract image alpha(s)->alpha(s') (the abstraction does not DROP behavior); (2) every abstract transition A->A' has a concrete witness s->s' with alpha(s)=A, alpha(s')=A' (the abstraction does not INVENT behavior). 'Abstract image' = where a concrete state/edge lands after applying alpha. If both hold, concrete and abstract are behaviorally indistinguishable, so ANY reachability/temporal query agrees exactly -- the strongest soundness guarantee. Mode A (multi-goal reachability) only spot-checks reachability of chosen predicates and can miss a collapse that merges non-bisimilar states when no probed goal separates them. B is the gold standard esp. for the 4.3 reversibility quotient. Implement as: build kernel concrete graph, build abstract graph, check the two simulation conditions via the quotient map.
