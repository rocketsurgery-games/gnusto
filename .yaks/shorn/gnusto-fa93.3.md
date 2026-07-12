---
id: gnusto-fa93.3
title: 'Zork I slice 2: house interior (kitchen/living room/attic + window + trap
  door + lamp/sword)'
type: task
priority: 2
created: '2026-07-12T16:29:10Z'
updated: '2026-07-12T16:35:30Z'
labels:
- conversion
---

---
▸ 2026-07-12T16:35:30Z
Done. Added house-interior.grue (Kitchen/Attic/Living Room + kitchen-window barrier, kitchen-table/sandwich-bag/lunch/garlic/bottle/water, trophy-case, rug+trap-door reveal mechanic, wooden-door nailed, lamp on/off, sword, attic-table/knife/rope, chimney/stairs scenery) and house-interior.test.grue (24 tests). Wired east-of-house west/in -> kitchen via window in white-house.grue. 46/46 grue-test, lint clean. REPL smoke-tested full critical path W-of-house -> behind house -> open window -> kitchen -> living room -> take lamp/sword -> move rug -> open trap door. Deferred: lantern battery drain, sword glow, trophy-case scoring, wooden-door MAGIC-FLAG opening, and DARKNESS enforcement (attic unlit but not enforced) -- darkness/grue is the next major mechanic and needs engine support + user design discussion before the underground slice.
