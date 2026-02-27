---
id: gnusto-7l2.20
title: Microwave :set-timer fails with string comparison error
type: bug
priority: 1
created: '2026-01-13T18:18:34.477801-05:00'
updated: '2026-02-08T19:07:10.970629Z'
labels:
- lh
---

When calling (do @microwave :set-timer 180), the behavior fails with:
Error evaluating behavior: '>' not supported between instances of 'str' and 'int'

The ?value binding is receiving a string "180" instead of an integer 180.
This prevents the microwave timer from being set.

Repro: (do @microwave :set-timer 180)
