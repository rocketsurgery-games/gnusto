---
id: gnusto-9xf.9
title: Fix nitrogen flask multiple use / refill
type: task
priority: 2
created: '2026-01-17T14:06:18.947412-05:00'
updated: '2026-02-08T19:07:11.016992Z'
---

Lines 854, 856 in walkthrough: (move! @nitrogen @flask) to 'refill'

Freezing the slime curtain requires 3 pours of nitrogen. Currently we have to teleport nitrogen back into flask after each pour. Either:
1. Flask should have multiple uses (3 charges)
2. Nitrogen should allow multiple pours before empty
3. Or there's a refill mechanism

Check ZIL for intended behavior.
