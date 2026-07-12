---
id: gnusto-fa93.8
title: 'Zork I slice 6: the thief + Treasure Room loot (deterministic lair)'
type: task
priority: 2
created: '2026-07-12T18:51:05Z'
updated: '2026-07-12T18:57:59Z'
labels:
- conversion
---

---
▸ 2026-07-12T18:57:59Z
Done. Added thief.grue (deterministic stationary thief in Treasure Room: STRENGTH 5, armed-blow duel, engross-then-strike via :give a treasure [-3 dmg vs -2]; egg puzzle: thief opens fragile egg intact, self-open breaks canary; large-bag loot + stiletto drop on death; chalice guarded until dead; egg/canary objects w/ egg in @nest dangling for forest slice) + thief.test.grue (17 tests). Original wandering/random behavior documented in code header; richer version -> fa93.9. Fixed maze treasure-room to :lit false (ZIL CANT-HAVE-ONBIT). Testing gotcha found: per-test :setup MERGES after group :setup (not replace) -> corrected grue-testing skill. 105 Zork / 585 grue-test / 833 pytest, lint clean. REPL-verified: give egg -> kill thief -> reclaim chalice + bag.
