---
id: gnusto-e96c
title: reachability-quotient.md documents a backward integration that was never landed
type: task
priority: 3
created: '2026-09-14T03:44:11Z'
updated: '2026-09-14T03:44:11Z'
parent: gnusto-otr.14
labels:
- docs
- bug
---

docs/design/reachability-quotient.md has a 'Backward integration' paragraph written in the present tense: 'BackwardAnalyzer._expand_node special-cases a player-location constraint = R ... otherwise it yields a runtime:go achiever whose preconditions are the passability constraints of the required barriers'. That code does not exist. src/frotz/reachability.py has no importers outside tests/frotz/test_reachability.py, and backward.py has no such special case.

This is consistent with the deliberate decision recorded in gnusto-otr.14 -- the shared core was built but NOT wired, to avoid shipping an under-approximation while the directional-exit question is open -- but the doc reads as if it shipped, which will mislead the next session into assuming requires already routes through the room graph.

FIX: mark that section as intended design rather than landed behavior, and name the blocking reason inline (the single-all-open-SCC finding). Cheap now, and worth doing before the wiring lands so the doc does not quietly become true by accident.
