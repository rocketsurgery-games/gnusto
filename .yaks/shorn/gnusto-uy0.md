---
id: gnusto-uy0
title: 'Frotz Phase 2: Relevance analysis (victory slice)'
type: task
priority: 2
created: '2026-01-20T18:45:14.153103-05:00'
updated: '2026-02-08T19:07:11.003999Z'
depends_on:
- gnusto-44o
- gnusto-c7k
---

Starting from victory/defeat conditions, compute the transitive closure of puzzle-relevant properties.

Algorithm:
1. Parse victory condition, identify directly referenced properties
2. For each property P in the relevant set:
   - Find behaviors that can modify P (from Phase 1)
   - Find properties those behaviors read (preconditions)
   - Add those properties to the relevant set
3. Iterate until fixed point

Result: Minimal set of properties that affect winnability.

This dramatically reduces the state space - most properties (room descriptions, static flags, etc.) will be excluded.

Depends on: Phase 1 effect analysis
See docs/frotz-design.md for context.
