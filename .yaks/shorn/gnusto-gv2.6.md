---
id: gnusto-gv2.6
title: Constraint-based state clustering
type: task
priority: 2
created: '2026-01-21T12:25:25.429736-05:00'
updated: '2026-02-08T19:07:11.002595Z'
---

Cluster game states by which puzzle-relevant constraints are satisfied. This reduces state graph complexity while preserving puzzle structure.

Proven on testgame: 21 states → 6 clusters (71% reduction), graph directly reveals puzzle progression.

Key insight: States with same satisfied constraints have similar successor sets (same puzzle-advancing actions available).

Open questions:
- How to automatically select good clustering constraints (currently manual)
- Scalability: 2^n clusters for n constraints; need hierarchical or selective approach
- Property abstraction: 'value | unknown' sufficient for now, may need refinement
