---
id: gnusto-9xf.12
title: 'Fix pool reach-in: should queue hand-dives event'
type: task
priority: 2
created: '2026-01-17T14:06:31.394868-05:00'
updated: '2026-02-08T19:07:11.016128Z'
---

Line 871 in walkthrough: (queue! hand-dives)

In the inner-lair, reaching into the pool should trigger the animated hand to dive in and find the power line. The hand-dives event should be queued automatically by the :reach-in behavior on @pool.
