---
id: gnusto-fa93.14
title: 'Zork I slice 11: coal mine pt2 — machine, dumbwaiter, diamond (+ lit? into
  open containers)'
type: task
priority: 2
created: '2026-07-13T01:04:28Z'
updated: '2026-07-13T01:08:48Z'
labels:
- runtime
---

---
▸ 2026-07-13T01:08:48Z
Done. Added coal-mine-2.grue (Timber-Room, Lower-Shaft, Machine-Room; @narrow-squeeze empty-handed gate; @basket dumbwaiter [:lower/:raise, contents ride along]; @machine lidded container + @machine-switch [:turn @screwdriver, closed+coal->diamond, else slag]; @diamond treasure) + coal-mine-2.test.grue (8). Engine: added accessible-in to builtins.grue so lit? sees light in OPEN containers (lit torch in open basket lights the dark lower shaft) + pytest + docs/grue.md. 168 Zork/648 grue-test/840 pytest, lint clean. REPL-verified full puzzle. Coal mine complete; frontier down to 7 (all surface + river).
