---
id: gnusto-otr.7
title: Implement solutions tool (alternative path finding)
type: task
priority: 3
created: '2026-01-25T12:04:56.594422-05:00'
updated: '2026-07-14T20:52:32Z'
depends_on:
- gnusto-otr.14
- gnusto-otr.15
---

Find multiple winning/goal paths to show design alternatives.

Usage:
```bash
frotz solutions --goal victory --max 5
```

Returns: Multiple distinct paths to the goal, showing how they differ.

Implementation notes:
- Use k-shortest-paths or path enumeration
- Deduplicate paths that differ only in irrelevant actions
- Highlight where paths diverge (choice points)
