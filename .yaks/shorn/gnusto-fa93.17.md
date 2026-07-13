---
id: gnusto-fa93.17
title: 'Zork I slice 14: forest/surface (fills surface exits, egg nest, songbird,
  grating)'
type: task
priority: 2
created: '2026-07-13T02:20:09Z'
updated: '2026-07-13T02:23:24Z'
labels:
- conversion
---

---
▸ 2026-07-13T02:23:24Z
Done. Added forest.grue (FOREST-1/2/3, MOUNTAINS, PATH, UP-A-TREE, GRATING-CLEARING, CLEARING; @nest homes @egg; @songbird scenery; @bauble treasure; @leaves reveals grate) + forest.test.grue (15). Heavy use of :blocked message exits. Updated @grate (maze.grue) for reveal + open-from-below; added @canary :wind (thief.grue) -> bauble in forest. MILESTONE: frotz map = zero dangling refs; all 108 rooms connected. Surface<->maze grating loop REPL-verified. 204 Zork/684 grue-test/840 pytest, lint clean. Only endgame (scoring + barrow victory) left.
