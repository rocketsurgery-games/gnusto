---
id: gnusto-3g0.2
title: Filter spurious achievers for specific location targets
type: task
priority: 2
created: '2026-01-24T18:24:11.747644-05:00'
updated: '2026-02-08T19:07:10.99564Z'
---

runtime:drop and runtime:take show as achievers for specific locations like @input-socket because modifies_to contains None (variable value).

When matching achievers for a SPECIFIC target like @input-socket:
- runtime:drop puts things at player's current location (variable)
- This shouldn't match when we want a specific non-player location

Fix: Don't match None values when the target is a specific object ref (not @player).
