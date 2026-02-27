---
id: gnusto-gv2.7.4
title: Navigation abstraction for subproblems
type: task
priority: 2
created: '2026-01-24T10:44:14.486461-05:00'
updated: '2026-02-08T19:07:10.996817Z'
---

Currently subproblems assume player is already at the target location. Need strategy for handling navigation:
- Abstract as 'always reachable' (not true for gated paths)
- Include player location in state refs (explodes state space)
- Create separate reachability subproblems
- Use barrier analysis to determine safe abstractions
