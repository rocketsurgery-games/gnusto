---
id: gnusto-fa93.12
title: 'Zork I slice 9: Hades — tiny cave, exorcism (bell/book/candle), skull'
type: task
priority: 2
created: '2026-07-13T00:23:40Z'
updated: '2026-07-13T00:28:08Z'
labels:
- conversion
---

---
▸ 2026-07-13T00:28:08Z
Done. Added hades.grue (Tiny-Cave, Entrance-to-Hades, Land-of-Living-Dead; @ghosts barrier+ritual state; deterministic bell-book-candle exorcism: @bell :ring->paralyze, @candles :light [needs @matches], @book :read->banish [LLD-FLAG]; @matches in dam-lobby; @skull treasure; @altar-hole barrier gated on not-holding-coffin) + hades.test.grue (10). Wired temple south-temple down -> tiny-cave via @altar-hole; fixed stale slice-8 'hole impassable' test. Dropped ZIL exorcism timers/RNG. 146 Zork / 626 grue-test / 839 pytest, lint clean. REPL-verified full ritual -> LLD -> skull. Deferred: altar pray->forest teleport. Setup-merge gotcha recurred (matches leaked).
