---
id: gnusto-otr.8
title: Implement complexity tool (puzzle metrics)
type: task
priority: 3
created: '2026-01-25T12:05:02.468976-05:00'
updated: '2026-02-08T19:07:11.066649Z'
---

Compute metrics to quantify puzzle complexity for design comparison.

Usage:
```bash
frotz complexity --goal "(= (:rmung @emergency-cabinet) true)"
```

Metrics:
- Depth: minimum steps required
- Breadth: number of alternative paths
- Dependencies: prerequisite count
- Branching factor: average choices per step

Use to compare complexity across puzzles in a game.
