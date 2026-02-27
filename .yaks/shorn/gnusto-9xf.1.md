---
id: gnusto-9xf.1
title: 'Fix navigation: brick-tunnel to infinite corridor'
type: task
priority: 2
created: '2026-01-17T14:05:56.712281-05:00'
updated: '2026-02-08T19:07:11.019168Z'
---

Line 708 in walkthrough: (move! @player @inf-1)

The brick-tunnel area (steam tunnels) doesn't connect to the infinite corridor (inf-1). Need to trace the expected path through the game map:
- brick-tunnel → under-alchemy-lab → alchemy-lab → ...?
- Or via tomb/aero areas?

Check the ZIL source for the canonical path.
