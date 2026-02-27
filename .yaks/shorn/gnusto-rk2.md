---
id: gnusto-rk2
title: Elevator call buttons not visible on elevator floors
type: bug
priority: 2
created: '2026-01-15T18:09:43.747925-05:00'
updated: '2026-02-08T19:07:11.025271Z'
labels:
- LH
---

The elevator call buttons (@up-button, @down-button) in elevator.grue have :location nil with the comment 'Global object, present on floors with up capability'. However, having nil location means they're never visible to the player.

The buttons need to either:
1. Be true global objects (:location @global) that check current floor in their behaviors
2. Have per-floor button instances
3. Use a pseudo-location mechanism for floor-specific visibility

Currently, the player cannot call the elevator because they can't see or interact with the call buttons.
