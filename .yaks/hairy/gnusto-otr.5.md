---
id: gnusto-otr.5
title: Implement critical tool (required object detection)
type: task
priority: 2
created: '2026-01-25T12:04:43.728778-05:00'
updated: '2026-02-08T19:07:10.993072Z'
---

Identify which objects/states are required (no alternatives) to reach a goal.

Usage:
```bash
frotz critical --goal victory
frotz critical --goal "(= (:location @player) @lair)"
```

Returns: List of required objects/states with no alternative paths.

Implementation notes:
- Analyze all paths to goal
- Find objects/states that appear in ALL paths (chokepoints)
- Distinguish required items from optional helpers
