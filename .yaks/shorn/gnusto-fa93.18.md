---
id: gnusto-fa93.18
title: 'Zork I slice 15: endgame — trophy-case scoring, map, Stone Barrow victory'
type: task
priority: 2
created: '2026-07-13T02:23:54Z'
updated: '2026-07-13T02:31:16Z'
labels:
- conversion
---

---
▸ 2026-07-13T02:31:16Z
Done. Added endgame.grue (all-treasures-deposited? via recursive inside? over the 19 treasures; endgame-watch start-event reveals @map + whispers; @barrow-path barrier; @stone-barrow + @barrow-door + @stone-barrow-interior [on-enter emits (victory true)]) + endgame.test.grue (5). Updated zork1.grue victory (= loc @player @stone-barrow-interior) + :start-events + player :endgame-announced; white-house sw/in -> stone-barrow via @barrow-path. CONVERSION COMPLETE & WINNABLE: 208 Zork/688 grue-test/840 pytest, lint clean, frotz map zero dangling refs. REPL-verified full deposit->barrow->*** VICTORY! ***. Learning: DSL victory? is a result predicate needing (victory true) context; victory? false unusable. Remaining: LLM playthrough + fold lessons into translate-zil skill.
