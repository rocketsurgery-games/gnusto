---
id: gnusto-otr.10
title: Implement whatif tool (design exploration)
type: task
priority: 3
created: '2026-01-25T12:05:16.133109-05:00'
updated: '2026-08-28T04:13:53Z'
parent: gnusto-otr
depends_on:
- gnusto-otr.14
- gnusto-otr.15
---

Hypothetical design exploration - what if we change something?

Usage:
```bash
frotz whatif --remove @axe --check victory
frotz whatif --lock @door-to-lair --check "(= (:location @player) @lair)"
```

Returns: Impact analysis - what becomes unreachable with the change.

Implementation notes:
- Temporarily modify the world model
- Re-run reachability analysis
- Compare before/after to show impact
- Useful for testing design changes without editing game files
