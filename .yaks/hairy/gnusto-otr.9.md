---
id: gnusto-otr.9
title: Implement statediff tool (debugging tool)
type: task
priority: 3
created: '2026-01-25T12:05:08.995484-05:00'
updated: '2026-02-08T19:07:11.066389Z'
---

Compare two states to understand what changed - useful for debugging.

Usage:
```bash
frotz statediff state1.json state2.json
frotz statediff --before "(do @player :take @key)"
```

Returns: List of state differences (changed properties, locations, etc.)

Implementation notes:
- Support loading states from JSON files
- Support showing state before/after an action
- Filter to show only meaningful changes (ignore irrelevant state)
