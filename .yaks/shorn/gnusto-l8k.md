---
id: gnusto-l8k
title: Add queue countdown abstraction to domains
type: feature
priority: 2
created: '2026-01-23T20:44:52.344186-05:00'
updated: '2026-02-08T19:07:10.997871Z'
---

Queue countdowns (e.g., waxer-moves timer) create many distinct states with values 0,1,2,3,4,5...

Add abstraction option to collapse queue values to:
- PENDING: countdown > 0 (will fire eventually)
- NOT_PENDING: countdown = None (not queued)
- FIRING: countdown = 0 (fires this turn)

Current behavior: Tracking queue(waxer-moves) with CONCRETE domain times out because each countdown value creates a distinct state.

Note: Waxer exploration currently works WITHOUT queue tracking because we track loc(@floor-waxer) and see the RESULT of queue processing. But other puzzles may need queue abstraction.
