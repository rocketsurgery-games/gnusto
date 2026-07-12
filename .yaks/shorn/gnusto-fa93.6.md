---
id: gnusto-fa93.6
title: 'Zork I slice 4: EW passage, Round Room, chasm/Gallery loop'
type: task
priority: 2
created: '2026-07-12T17:35:56Z'
updated: '2026-07-12T17:39:20Z'
labels:
- conversion
---

---
▸ 2026-07-12T17:39:20Z
Done. Added round-room.grue (EW-Passage, Round Room, Chasm, NS-Passage, East-of-Chasm, Gallery [lit], Studio; painting treasure w/ :treasure/:value/:tvalue + mung; @crack scenery) and round-room.test.grue (17 tests). Added chimney :through (UP-CHIMNEY constraint: lantern + <=1 other item) to house-interior. Closes the treasure-escape loop Studio->Kitchen. 78 Zork tests, lint clean. REPL-verified: descend -> east-of-chasm -> gallery -> take painting -> studio -> climb chimney with lamp+painting -> back in kitchen. Established treasure-tagging convention for the scoring slice. Dangling exits (loud-room/dam/reservoir/temple/maze) for later slices.
