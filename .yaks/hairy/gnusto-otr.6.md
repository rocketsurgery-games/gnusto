---
id: gnusto-otr.6
title: Implement depgraph tool (dependency visualization)
type: task
priority: 3
created: '2026-01-25T12:04:50.16293-05:00'
updated: '2026-07-14T20:52:31Z'
depends_on:
- gnusto-otr.13
---

Visualize constraint/dependency relationships for game design insight.

Usage:
```bash
frotz depgraph --goal "(>= (:count @frob) 2)" -o deps.dot
frotz depgraph --object @axe
```

Output: DOT file showing dependency graph.

Features:
- Show critical path in different color
- Highlight parallel opportunities (independent subgraphs)
- Object-centric view: what does this object enable/require?
