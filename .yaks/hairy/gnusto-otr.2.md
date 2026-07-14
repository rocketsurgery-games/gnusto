---
id: gnusto-otr.2
title: Implement requires tool (precondition analysis)
type: task
priority: 2
created: '2026-01-25T12:04:25.300867-05:00'
updated: '2026-07-14T20:52:31Z'
depends_on:
- gnusto-otr.13
---

Backward constraint tree showing what must be true to achieve a goal state.

Usage:
```bash
frotz requires "(= (:location @axe) @player)"
frotz requires "(not (= (:location @maintenance-man) @floor-waxer))"
```

Returns: Backward constraint tree showing dependencies and alternative paths.

Implementation notes:
- Build on existing backward.py constraint analysis
- Format output as readable tree or DOT graph
- Show bottlenecks (single required states)
