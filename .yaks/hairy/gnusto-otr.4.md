---
id: gnusto-otr.4
title: Implement deadends tool (unwinnable state detection)
type: task
priority: 2
created: '2026-01-25T12:04:37.48706-05:00'
updated: '2026-07-14T20:52:31Z'
depends_on:
- gnusto-otr.14
- gnusto-otr.15
---

Detect whether a state is unwinnable (soft-lock detection).

Usage:
```bash
frotz deadends --check "(= (:location @axe) @abyss)"
frotz deadends --from state.json
```

Returns: Yes/No + which victory conditions become unreachable.

Implementation notes:
- Given a state, check if any victory path exists
- If no path, identify which required state transitions are no longer possible
- Important for soft-lock prevention during game design
