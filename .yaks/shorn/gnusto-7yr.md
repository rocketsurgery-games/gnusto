---
id: gnusto-7yr
title: 'Frotz Phase 3: State space exploration with quotient'
type: task
priority: 2
created: '2026-01-20T18:45:22.15361-05:00'
updated: '2026-02-08T19:07:11.003705Z'
depends_on:
- gnusto-44o
- gnusto-uy0
---

BFS/DFS through the game state space, using only puzzle-relevant properties for state identity.

Implementation:
1. Define state as: values of puzzle-relevant properties only
2. Hash function for visited-set membership
3. Action enumeration: for each state, generate all valid (do @obj :verb ...) actions
4. BFS/DFS with:
   - Visited set (by hash)
   - Parent pointers (for path reconstruction)
   - Victory/defeat checks at each state

Key insight: Two states that agree on puzzle-relevant properties are equivalent (bisimilar). We only need to explore one representative per equivalence class.

Output:
- Reachability graph (on equivalence classes)
- "Victory reachable: yes/no"
- If no: counterexample trace showing dead-end path
- If yes: shortest winning path

Depends on: Phase 2 relevance analysis
See docs/frotz-design.md for context.
