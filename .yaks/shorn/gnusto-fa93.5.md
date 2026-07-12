---
id: gnusto-fa93.5
title: 'Zork I slice 3: cellar + troll room (first combat)'
type: task
priority: 2
created: '2026-07-12T17:25:14Z'
updated: '2026-07-12T17:31:33Z'
labels:
- conversion
---

---
▸ 2026-07-12T17:31:33Z
Done. Added cellar.grue (Cellar + Troll Room, both :lit false/dark; deterministic troll combat: :strength 2, armed blow decrements, 0=dead+drop axe+open passages; troll is its own :via barrier for E/W exits; cellar :on-enter slams+bars the trap door; axe held-then-dropped) and cellar.test.grue (10 tests). Updated house-interior trap-door (:touched, locked-from-above when below). Engine fix: _do_go now merges room :on-enter OUTPUT (arrival narration was dropped). Noted strict behavior arity (attack needs nil arg). 61 Zork tests, 541 grue-test, 833 pytest, lint clean. REPL-verified full entrance: descend->slam->troll duel->axe drops->east opens. Dungeon darkness exercises the grue for real (lamp mandatory).
