---
id: gnusto-gv2.7
title: Hierarchical clustering for large state spaces
type: task
priority: 3
created: '2026-01-21T12:25:31.905744-05:00'
updated: '2026-02-08T19:07:11.07141Z'
---

## Status: ACTIVE - Subproblem decomposition

Hierarchical analysis of state space through subproblem isolation:
1. Define isolated subproblems with custom setup and goal conditions
2. Explore each subproblem independently with small state counts
3. Chain subproblems together by making goal of one be precondition of next

## Progress
- Created src/frotz/subproblem.py with Subproblem/SubproblemResult classes
- Added state_goal support for custom goal predicates on state dicts
- DOT visualization with victory path highlighting
- Tested on LH endgame (25 states) and plug prep (48 states)

## Issues Found
1. Goal checking is post-hoc, no early termination during exploration
2. State key format inconsistency (@obj:location vs LocationRef string repr)
3. Plug prep has unreachable defeat states (possible game logic bug)
4. No abstraction of navigation (assumes player already at location)
5. Monotonic state like cut-count bloats state space unnecessarily

## Next Steps
- Continue iterating backwards through LH precondition chain
- Address state key standardization
- Consider navigation abstraction strategies
