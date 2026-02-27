---
id: gnusto-9xf.10
title: Fix professor death event after ritual escape
type: task
priority: 2
created: '2026-01-17T14:06:31.023706-05:00'
updated: '2026-02-08T19:07:11.016748Z'
---

Lines 779-780 in walkthrough: (set! prof-dead true) (move! @ring @alchemy-lab)

After escaping through the trapdoor, the professor's death event should fire and leave the ring behind in the alchemy lab. Currently we set this state manually.
