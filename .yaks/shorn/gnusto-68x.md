---
id: gnusto-68x
title: Floor waxer never starts patrolling - waxer-moves event not initially queued
type: bug
priority: 2
created: '2026-01-15T18:14:14.750511-05:00'
updated: '2026-02-08T19:07:11.024987Z'
labels:
- LH
---

The floor waxer's patrol event (waxer-moves) is never initially queued. The event re-queues itself after each move, but there's no trigger to start the patrol in the first place.

Looking at maintenance-man.grue:
- waxer-moves event re-queues itself at line 394
- But nothing ever calls (queue! waxer-moves) initially

The waxer should start patrolling when the player first enters the infinite corridor area. Without this, the waxer stays stationary at @inf-2 indefinitely.

Expected behavior: Waxer should patrol inf-1 through inf-5
Actual behavior: Waxer stays at inf-2 forever
