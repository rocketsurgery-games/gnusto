---
id: gnusto-81s
title: Add CONTAINED location abstraction
type: feature
priority: 3
created: '2026-01-23T20:45:10.367448-05:00'
updated: '2026-02-08T19:07:11.070045Z'
---

Current HELD abstraction only distinguishes {held by player, not held}.

For some puzzles we need finer distinction:
- HELD: in @player inventory
- CONTAINED: inside a container (e.g., axe in cabinet)
- DROPPED: on the floor/in a room

Example: Axe puzzle - need to know if axe is still in cabinet vs already taken.

With pure HELD abstraction, axe in cabinet and axe on floor are both 'not held' and exploration can't tell if cabinet was broken.

Possible approach: Add CONTAINED_OR_HELD abstraction that tracks whether object is reachable (in player or in accessible container at player location).
