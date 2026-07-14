---
id: gnusto-otr.3
title: Implement blockers tool (progress blocker detection)
type: task
priority: 2
created: '2026-01-25T12:04:31.556131-05:00'
updated: '2026-07-14T20:52:31Z'
depends_on:
- gnusto-otr.13
---

Identify what's preventing progress from a given state.

Usage:
```bash
frotz blockers --goal "(>= (:count @frob) 2)"
frotz blockers --from state.json --goal victory
```

Returns: Unsatisfied preconditions, missing items, locked paths.

Implementation notes:
- Start from a state (current or loaded from file)
- Find goal state via backward analysis
- Identify which preconditions are not met
- Suggest actions to unblock
