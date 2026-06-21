---
id: gnusto-a07e.4
title: Locale master plates for cross-visible rooms
type: feature
priority: 2
created: '2026-06-21T20:30:08Z'
updated: '2026-06-21T20:30:08Z'
depends_on:
- gnusto-a07e.1
- gnusto-a07e.2
labels:
- render
---

Break the cyclic room-visibility graph by clustering mutually-visible rooms into a LOCALE with one prompt-only master plate (a root). Probe result: a cluster-master plate of the 2nd-floor hallway baked in the cross-visibility (elevators, stairs, kitchen-through-doorway); kitchen-ref off it inherited the doorway layout+palette, while prompt-only kitchen was a different room.

- Declare a locale -> master-plate key (prompt-only root) in Grue.
- Each room in the locale :refs its plate (the room that IS the locale, e.g. the hallway, can BE the plate).
- M5 crop is only an opportunistic free shortcut when a room is a literal sub-rectangle of the plate; NOT required and not a cycle-breaker.
- Plays through a07e.1 (deps/lint) + a07e.2 (ordered gen).

Update docs/render.md.
