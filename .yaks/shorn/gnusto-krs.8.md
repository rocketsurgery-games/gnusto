---
id: gnusto-krs.8
title: Convert LH globals to object properties
type: task
priority: 2
created: '2026-01-17T17:54:26.592481-05:00'
updated: '2026-02-08T19:07:11.014107Z'
---

Convert all Lurking Horror globals to properties on appropriate objects.

COMPLETED:
✅ Microwave: timer, temp → @microwave

REMAINING:
- Hacker: hacker-trade, lair-cnt, hacker-help, food-hint, comp-cnt → @hacker
- Elevator: elevator-loc, elevator-direction, elevator-stopped, etc → @elevator
- Lair: lair-flag, slime-cnt, nitrogen-cnt, hv-cnt, end-cnt → various
- Steam tunnels: seen-pit, brick-wall-broken, valve-turns, on-cable, rats-anger
- Maintenance: maint-attack-count, seen-mm-slip, waxer-patrol-started
- Alchemy: prof-dead, prof-mad, prof-seen-note, left-alchemy, lab-bench-moved, etc
- Urchins: urchin-freed
- Yuggoth: yuggoth-count, freeze-count, remembered-student
- Brown building: flier-count
- Aero: padlock-on
- CS building: door-warning, username, logged-in

Pattern established: use (:prop @obj) for reads, (set @obj :prop val) for writes
