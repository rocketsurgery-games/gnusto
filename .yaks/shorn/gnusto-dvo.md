---
id: gnusto-dvo
title: 'Frotz Phase 4: Output and visualization'
type: task
priority: 3
created: '2026-01-20T18:45:30.578773-05:00'
updated: '2026-02-08T19:07:11.071778Z'
depends_on:
- gnusto-44o
- gnusto-7yr
---

Generate useful output from the state space analysis:

1. **Winnability verdict**: yes/no with proof
   - If yes: "Victory reachable in N steps, M equivalence classes explored"
   - If no: "Dead-end found at state S, reached via path P"

2. **Dead-end analysis**: For each dead-end state:
   - The path that leads there
   - What properties are "stuck" (can't change to needed values)
   - Suggested fix (if determinable)

3. **Winning path**: Shortest sequence of actions to victory
   - Could be used for automated testing / walkthrough generation

4. **Puzzle dependency graph**: Derived from state space structure
   - Similar to Ron Gilbert's puzzle dependency charts
   - Shows which puzzles unlock which others
   - Visualizes the "diamond pattern" of parallel puzzles

Output formats:
- Human-readable text report
- JSON for tooling
- Graphviz DOT for visualization

Depends on: Phase 3 state space exploration
See docs/frotz-design.md for context.
