---
id: gnusto-otr.5
title: Implement critical tool (required object detection)
type: task
priority: 2
created: '2026-01-25T12:04:43.728778-05:00'
updated: '2026-07-14T20:52:31Z'
depends_on:
- gnusto-otr.13
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
