---
id: gnusto-163b
title: 'Zork winnability blocker: gold coffin trapped in Temple (altar pray-teleport
  unimplemented)'
type: task
priority: 1
created: '2026-07-13T20:56:02Z'
updated: '2026-07-13T20:57:51Z'
labels:
- bug
---

---
▸ 2026-07-13T20:56:12Z
Found by the play-grue sub-agent driving the full game. The gold coffin (a required treasure per endgame.grue all-treasures-deposited?) is trapped in the Temple: the only temple exit that leaves the complex is South Temple -> down -> Tiny Cave via @altar-hole, which hard-refuses the coffin ('You haven''t a prayer of getting the coffin down there.'), and the rope descent into the Torch Room is one-way. The canonical escape -- PRAY at the altar to teleport to the forest (ZIL V-PRAY / 1actions PRAY at SOUTH-TEMPLE -> GOTO FOREST-1, carrying everything) -- was left deferred ('needs the forest slice'). The forest exists now, so implement it. Fix: add :pray to @altar teleporting @player to @forest-1 (held items, incl. coffin, ride along); keep the altar-hole coffin gate (intended). Also update the deferred comments in temple.grue / hades.grue.

---
▸ 2026-07-13T20:57:51Z
FIXED. Added :pray to @altar (temple.grue): at the South Temple it teleports @player to @forest-1 with the canonical trumpet/'deep in the woods' message; held items (incl. the coffin) ride along since their location is the player, not the room. Kept the altar-hole coffin gate (intended). Updated the deferred comments in temple.grue/hades.grue. Grue tests: altar-hole refuses coffin + pray whisks you (and coffin) to the forest. Verified end-to-end in the repl (Egypt->temple->altar->pray->forest-1 with coffin held). 693 grue-test + 817 pytest green, frotz lint clean.
