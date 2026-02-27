---
id: gnusto-qpv
title: 'Bug: Objects accessible from any room'
type: bug
priority: 1
created: '2026-01-15T09:01:59.154195-05:00'
updated: '2026-02-08T19:07:10.966168Z'
depends_on:
- gnusto-ntr
labels:
- lh
---

The runtime allows actions on objects regardless of whether they are visible/accessible to the player.

Example: From @terminal-room, (do @slots :examine) succeeds even though @slots is in @large-chamber.

This bypasses game logic - players can interact with objects in rooms they haven't visited.

Fix: The runtime should check is_visible() before dispatching actions. If object is not visible, return blocked with reason 'not-here'.
